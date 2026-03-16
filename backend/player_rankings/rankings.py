import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import sys

# ── Config ────────────────────────────────────────────────────────────────────
SEASON_YEAR = 2026
OUTPUT_FILE = "march_madness_draft_board.csv"
BREAKDOWN_FILE = "march_madness_seed_breakdown.csv"
SLEEP = 3  # seconds between requests — bump to 5 if you get blocked

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Expected games per seed (historical averages)
EXPECTED_GAMES = {
    1:  4.056,
    2:  3.269,
    3:  2.744,
    4:  2.487,
    5:  2.056,
    6:  1.994,
    7:  1.869,
    8:  1.669,
    9:  1.556,
    10: 1.569,
    11: 1.606,
    12: 1.494,
    13: 1.244,
    14: 1.156,
    15: 1.094,
    16: 1.012,
}

# ── 2026 NCAA Tournament Bracket ──────────────────────────────────────────────
# Hardcoded from the official bracket (announced March 15, 2026).
# Format: (seed, sports-reference school slug)
# Slugs verified against https://www.sports-reference.com/cbb/schools/

TOURNAMENT_TEAMS = [
    # EAST REGION
    (1,  "duke"),
    (2,  "connecticut"),
    (3,  "michigan-state"),
    (4,  "kansas"),
    (5,  "st-johns-ny"),
    (6,  "louisville"),
    (7,  "ucla"),
    (8,  "ohio-state"),
    (9,  "texas-christian"),       # TCU
    (10, "central-florida"),       # UCF
    (11, "south-florida"),
    (12, "northern-iowa"),
    (13, "california-baptist"),
    (14, "north-dakota-state"),
    (15, "furman"),
    (16, "siena"),

    # WEST REGION
    (1,  "arizona"),
    (2,  "purdue"),
    (3,  "gonzaga"),
    (4,  "arkansas"),
    (5,  "wisconsin"),
    (6,  "brigham-young"),         # BYU
    (7,  "miami-fl"),
    (8,  "villanova"),
    (9,  "utah-state"),
    (10, "missouri"),
    (11, "texas"),                 # First Four vs NC State
    (11, "north-carolina-state"),  # First Four vs Texas
    (12, "high-point"),
    (13, "hawaii"),
    (14, "kennesaw-state"),
    (15, "queens-nc"),
    (16, "long-island-university"), # LIU

    # MIDWEST REGION
    (1,  "michigan"),
    (2,  "iowa-state"),
    (3,  "virginia"),
    (4,  "alabama"),
    (5,  "texas-tech"),
    (6,  "tennessee"),
    (7,  "kentucky"),
    (8,  "georgia"),
    (9,  "saint-louis"),
    (10, "santa-clara"),
    (11, "miami-oh"),              # First Four vs SMU
    (11, "southern-methodist"),    # SMU — First Four vs Miami OH
    (12, "akron"),
    (13, "hofstra"),
    (14, "wright-state"),
    (15, "tennessee-state"),
    (16, "maryland-baltimore-county"),  # UMBC — First Four vs Howard
    (16, "howard"),                     # First Four vs UMBC

    # SOUTH REGION
    (1,  "florida"),
    (2,  "houston"),
    (3,  "illinois"),
    (4,  "nebraska"),
    (5,  "vanderbilt"),
    (6,  "north-carolina"),
    (7,  "saint-marys-ca"),
    (8,  "clemson"),
    (9,  "iowa"),
    (10, "texas-am"),
    (11, "virginia-commonwealth"),  # VCU
    (12, "mcneese-state"),
    (13, "troy"),
    (14, "pennsylvania"),           # Penn
    (15, "idaho"),
    (16, "prairie-view"),           # First Four vs Lehigh
    (16, "lehigh"),                 # First Four vs Prairie View
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            print(f"  [WARN] HTTP {r.status_code} for {url}")
            return None
        if len(r.text) < 2000:
            print(f"  [WARN] Response too short ({len(r.text)} chars) — possible bot block")
            return None
        # KEY FIX: Sports-reference wraps most stat tables in HTML comments
        # so they aren't visible to basic scrapers. Strip the comment tags
        # so BeautifulSoup can actually find the tables.
        html = r.text.replace("<!--", "").replace("-->", "")
        return BeautifulSoup(html, "lxml")
    except requests.RequestException as e:
        print(f"  [ERROR] {e}")
        return None


def get_stat(row, data_stat: str) -> float:
    cell = row.find("td", {"data-stat": data_stat})
    if cell is None or cell.text.strip() in ("", "-"):
        raise ValueError(f"missing {data_stat}")
    return float(cell.text.strip())


# ── Scrape one team ───────────────────────────────────────────────────────────

def scrape_team(seed: int, slug: str) -> list[dict]:
    # Try the newer /men/ path first, then the legacy path
    soup = None
    for url in [
        f"https://www.sports-reference.com/cbb/schools/{slug}/men/{SEASON_YEAR}.html",
        f"https://www.sports-reference.com/cbb/schools/{slug}/{SEASON_YEAR}.html",
    ]:
        soup = fetch(url)
        if soup:
            break

    if soup is None:
        print(f"  [SKIP] Could not load page for '{slug}' — check slug spelling")
        return []

    # Try all known SR per-game table IDs
    table = (
        soup.find("table", {"id": "players_per_game"}) or
        soup.find("table", {"id": "per_game"}) or
        soup.find("table", {"id": "per_game_stats"})
    )

    if table is None:
        ids = [t.get("id") for t in soup.find_all("table")]
        print(f"  [SKIP] No per-game table for '{slug}'. Tables on page: {ids}")
        return []

    expected_g = EXPECTED_GAMES.get(seed, 2.0)
    players = []

    for row in table.find("tbody").find_all("tr"):
        # Skip in-table header rows
        if row.get("class") and "thead" in row.get("class", []):
            continue

        name_cell = (
            row.find("td", {"data-stat": "name_display"}) or
            row.find("td", {"data-stat": "player"}) or
            row.find("th", {"data-stat": "player"})
        )
        if not name_cell:
            continue

        player_name = name_cell.text.strip()
        if not player_name or player_name.lower() == "player":
            continue

        try:
            mpg = get_stat(row, "mp_per_g")
            ppg = get_stat(row, "pts_per_g")
            rpg = get_stat(row, "trb_per_g")
            apg = get_stat(row, "ast_per_g")
        except ValueError:
            continue  # skip DNP / incomplete rows

        fantasy_avg = ppg + rpg + apg

        players.append({
            "player":          player_name,
            "team":            slug,
            "seed":            seed,
            "expected_games":  expected_g,
            "mpg":             mpg,
            "ppg":             ppg,
            "rpg":             rpg,
            "apg":             apg,
            "fantasy_avg":     round(fantasy_avg, 2),
            "projected_total": round(fantasy_avg * expected_g, 2),
        })

    return players


# ── Per-seed breakdown ────────────────────────────────────────────────────────

def build_seed_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for seed, group in df.groupby("seed"):
        best_idx = group["projected_total"].idxmax()
        rows.append({
            "seed":                   seed,
            "expected_games":         group["expected_games"].iloc[0],
            "num_players":            len(group),
            "avg_fantasy_avg":        round(group["fantasy_avg"].mean(), 2),
            "avg_projected_total":    round(group["projected_total"].mean(), 2),
            "top_player":             group.loc[best_idx, "player"],
            "top_player_team":        group.loc[best_idx, "team"],
            "top_player_projection":  group.loc[best_idx, "projected_total"],
        })
    return pd.DataFrame(rows).sort_values("seed").reset_index(drop=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_players: list[dict] = []
    failed: list[str] = []

    total = len(TOURNAMENT_TEAMS)
    for i, (seed, slug) in enumerate(TOURNAMENT_TEAMS, 1):
        print(f"[{i:>2}/{total}] seed {seed:>2}  {slug}")
        players = scrape_team(seed, slug)

        if players:
            print(f"         → {len(players)} players")
            all_players.extend(players)
        else:
            failed.append(f"seed {seed} / {slug}")

        time.sleep(SLEEP)

    if not all_players:
        print("\n[FATAL] No data collected.")
        print("  SR is likely blocking your IP or the slugs need fixing.")
        print("  Try increasing SLEEP to 5-6 seconds, or wait 15 min and retry.")
        sys.exit(1)

    # Draft board
    df = (
        pd.DataFrame(all_players)
        .sort_values("projected_total", ascending=False)
        .reset_index(drop=True)
    )
    df.index += 1
    df.index.name = "rank"
    df.to_csv(OUTPUT_FILE)
    print(f"\n✓ Draft board saved → {OUTPUT_FILE}  ({len(df)} players)")

    # Seed breakdown
    breakdown = build_seed_breakdown(df)
    breakdown.to_csv(BREAKDOWN_FILE, index=False)
    print(f"✓ Seed breakdown saved → {BREAKDOWN_FILE}")

    # Report failures
    if failed:
        print(f"\n[WARN] {len(failed)} team(s) returned no data:")
        for f in failed:
            print(f"  - {f}")
        print("  Fix slugs at: https://www.sports-reference.com/cbb/schools/")

    # Preview
    print(f"\nTop 10 projected players:")
    cols = ["player", "team", "seed", "ppg", "rpg", "apg", "projected_total"]
    print(df[cols].head(10).to_string())


if __name__ == "__main__":
    main()