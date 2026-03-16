"""
backtest.py — Tests the fantasy projection model against last year's (2025)
actual NCAA tournament results.

Steps:
1. Scrape 2024-25 season per-game stats for every 2025 tournament team
2. Generate pre-tournament projections (same model as rankings.py)
3. Scrape actual 2025 tournament game logs to get real fantasy totals
4. Correlate projected vs actual scores
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import sys
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

SEASON_YEAR = 2025
SLEEP = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

EXPECTED_GAMES = {
    1:  4.056, 2:  3.269, 3:  2.744, 4:  2.487,
    5:  2.056, 6:  1.994, 7:  1.869, 8:  1.669,
    9:  1.556, 10: 1.569, 11: 1.606, 12: 1.494,
    13: 1.244, 14: 1.156, 15: 1.094, 16: 1.012,
}

# 2025 tournament teams — hardcoded bracket
# (seed, sr_slug)
TOURNAMENT_TEAMS_2025 = [
    # EAST
    (1,  "duke"),
    (2,  "alabama"),
    (3,  "wisconsin"),
    (4,  "arizona"),
    (5,  "oregon"),
    (6,  "byu"),
    (7,  "saint-marys-ca"),
    (8,  "mississippi-state"),
    (9,  "baylor"),
    (10, "vanderbilt"),
    (11, "vcu"),
    (11, "american"),
    (12, "liberty"),
    (13, "akron"),
    (14, "montana"),
    (15, "robert-morris"),
    (16, "american"),    # placeholder — first four
    (16, "mount-st-marys"),

    # WEST
    (1,  "auburn"),
    (2,  "michigan-state"),
    (3,  "iowa-state"),
    (4,  "texas-am"),
    (5,  "michigan"),
    (6,  "ole-miss"),
    (7,  "marquette"),
    (8,  "louisville"),
    (9,  "creighton"),
    (10, "new-mexico"),
    (11, "north-carolina"),
    (12, "ucf"),
    (13, "yale"),
    (14, "lipscomb"),
    (15, "bryant"),
    (16, "alabama-state"),

    # SOUTH
    (1,  "houston"),
    (2,  "tennessee"),
    (3,  "kentucky"),
    (4,  "purdue"),
    (5,  "clemson"),
    (6,  "illinois"),
    (7,  "ucla"),
    (8,  "gonzaga"),
    (9,  "georgia"),
    (10, "utah-state"),
    (11, "drake"),
    (11, "texas"),
    (12, "mcneese-state"),
    (13, "high-point"),
    (14, "troy"),
    (15, "wofford"),
    (16, "siena"),
    (16, "iona"),

    # MIDWEST
    (1,  "florida"),
    (2,  "st-johns-ny"),
    (3,  "texas-tech"),
    (4,  "maryland"),
    (5,  "memphis"),
    (6,  "missouri"),
    (7,  "kansas"),
    (8,  "connecticut"),
    (9,  "oklahoma"),
    (10, "arkansas"),
    (11, "virginia-commonwealth"),
    (12, "colorado-state"),
    (13, "grand-canyon"),
    (14, "north-iowa"),
    (15, "nevada-las-vegas"),
    (16, "norfolk-state"),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        if len(r.text) < 2000:
            return None
        html = r.text.replace("<!--", "").replace("-->", "")
        return BeautifulSoup(html, "lxml")
    except:
        return None


def get_stat(row, data_stat):
    cell = row.find("td", {"data-stat": data_stat})
    if cell is None or cell.text.strip() in ("", "-"):
        raise ValueError(f"missing {data_stat}")
    return float(cell.text.strip())


# ── Step 1: scrape pre-tournament season stats ────────────────────────────────

def scrape_season_stats(teams):
    all_players = []
    total = len(teams)
    for i, (seed, slug) in enumerate(teams, 1):
        print(f"  [{i:>2}/{total}] {slug}")
        soup = None
        for url in [
            f"https://www.sports-reference.com/cbb/schools/{slug}/men/{SEASON_YEAR}.html",
            f"https://www.sports-reference.com/cbb/schools/{slug}/{SEASON_YEAR}.html",
        ]:
            soup = fetch(url)
            if soup:
                break

        if not soup:
            print(f"    [SKIP] could not load {slug}")
            time.sleep(SLEEP)
            continue

        table = (
            soup.find("table", {"id": "players_per_game"}) or
            soup.find("table", {"id": "per_game"}) or
            soup.find("table", {"id": "per_game_stats"})
        )
        if not table:
            print(f"    [SKIP] no per-game table for {slug}")
            time.sleep(SLEEP)
            continue

        expected_g = EXPECTED_GAMES.get(seed, 2.0)

        for row in table.find("tbody").find_all("tr"):
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
                continue

            fantasy_avg = ppg + rpg + apg
            all_players.append({
                "player":          player_name,
                "team":            slug,
                "seed":            seed,
                "expected_games":  expected_g,
                "ppg": ppg, "rpg": rpg, "apg": apg, "mpg": mpg,
                "fantasy_avg":     round(fantasy_avg, 2),
                "projected_total": round(fantasy_avg * expected_g, 2),
            })

        time.sleep(SLEEP)

    return pd.DataFrame(all_players)


# ── Step 2: scrape actual tournament game logs ────────────────────────────────

def scrape_actual_tournament_stats(teams):
    """
    Scrape each team's 2025 tournament game logs from SR.
    SR has per-game logs per player; we filter to NCAA tournament games only.
    """
    all_actuals = []
    total = len(teams)
    seen_slugs = set()

    for i, (seed, slug) in enumerate(teams, 1):
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        print(f"  [{i:>2}/{total}] {slug} tournament games")

        # SR game logs are at /cbb/schools/{slug}/men/{year}-gamelogs.html
        for url in [
            f"https://www.sports-reference.com/cbb/schools/{slug}/men/{SEASON_YEAR}-gamelogs.html",
            f"https://www.sports-reference.com/cbb/schools/{slug}/{SEASON_YEAR}-gamelogs.html",
        ]:
            soup = fetch(url)
            if soup:
                break
        else:
            print(f"    [SKIP] no gamelogs for {slug}")
            time.sleep(SLEEP)
            continue

        # The gamelog table shows each game; we want rows where game_season contains "NCAA"
        # SR marks tournament games in the schedule — look for "NCAA" in the notes/game_type column
        table = soup.find("table", {"id": "sgl-basic"}) or soup.find("table", {"id": "gamelog"})
        if not table:
            # Try schedule table to identify tournament game dates
            print(f"    [SKIP] no gamelog table for {slug}")
            time.sleep(SLEEP)
            continue

        # Get NCAA tournament game dates from this team's schedule
        ncaa_dates = set()
        sched_table = soup.find("table", {"id": "schedule"})
        if sched_table:
            for row in sched_table.find("tbody").find_all("tr"):
                game_type = row.find("td", {"data-stat": "game_season"})
                date_cell = row.find("td", {"data-stat": "date_game"})
                if game_type and "NCAA" in game_type.text and date_cell:
                    ncaa_dates.add(date_cell.text.strip())

        time.sleep(SLEEP)

    # Alternative: use the team tournament stats page directly
    # SR has /cbb/schools/{slug}/men/{year}-schedule.html
    # Actually, the cleanest approach is the NCAA tournament results page per team
    return scrape_tournament_results_per_team(teams)


def scrape_tournament_results_per_team(teams):
    """
    For each team, scrape their tournament-specific player stats.
    SR has a per-player tournament stats section on the school's postseason page.
    The 2025 tournament results page: /cbb/postseason/men/2025-ncaa.html
    has individual game box scores linked — we scrape those.
    """
    print("\n  Fetching 2025 tournament box scores from SR...")

    # Get the bracket page to find all game links
    url = "https://www.sports-reference.com/cbb/postseason/men/2025-ncaa.html"
    soup = fetch(url)
    if not soup:
        print("  [FAIL] Could not load 2025 bracket page")
        return pd.DataFrame()

    # Find all box score links
    game_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/cbb/boxscores/" in href and href.endswith(".html"):
            full = "https://www.sports-reference.com" + href
            if full not in game_links:
                game_links.append(full)

    print(f"  Found {len(game_links)} tournament game links")

    # Scrape each box score
    player_totals = {}  # player_name -> {pts, trb, ast, games}

    for i, link in enumerate(game_links, 1):
        print(f"  Box score {i}/{len(game_links)}: {link.split('/')[-1]}")
        soup = fetch(link)
        if not soup:
            time.sleep(SLEEP)
            continue

        # Each box score has two team tables: basic box score
        for table in soup.find_all("table", id=lambda x: x and "box-" in x and "basic" in x):
            for row in table.find("tbody").find_all("tr"):
                if row.get("class") and "thead" in row.get("class", []):
                    continue
                name_cell = row.find("th", {"data-stat": "player"})
                if not name_cell:
                    continue
                player = name_cell.text.strip()
                if not player or player in ("Reserves", "Team Totals"):
                    continue
                try:
                    pts = float(row.find("td", {"data-stat": "pts"}).text.strip() or 0)
                    trb = float(row.find("td", {"data-stat": "trb"}).text.strip() or 0)
                    ast = float(row.find("td", {"data-stat": "ast"}).text.strip() or 0)
                except:
                    continue

                if player not in player_totals:
                    player_totals[player] = {"pts": 0, "trb": 0, "ast": 0, "games": 0}
                player_totals[player]["pts"]   += pts
                player_totals[player]["trb"]   += trb
                player_totals[player]["ast"]   += ast
                player_totals[player]["games"] += 1

        time.sleep(SLEEP)

    if not player_totals:
        return pd.DataFrame()

    rows = []
    for player, stats in player_totals.items():
        rows.append({
            "player":        player,
            "actual_pts":    stats["pts"],
            "actual_trb":    stats["trb"],
            "actual_ast":    stats["ast"],
            "actual_games":  stats["games"],
            "actual_total":  stats["pts"] + stats["trb"] + stats["ast"],
        })
    return pd.DataFrame(rows)


# ── Step 3: correlate ─────────────────────────────────────────────────────────

def run_backtest():
    print("=" * 60)
    print("STEP 1: Scraping 2024-25 season stats...")
    print("=" * 60)
    proj_df = scrape_season_stats(TOURNAMENT_TEAMS_2025)

    if proj_df.empty:
        print("[FATAL] No season stats collected.")
        sys.exit(1)

    print(f"\nCollected stats for {len(proj_df)} players across {proj_df['team'].nunique()} teams")

    print("\n" + "=" * 60)
    print("STEP 2: Scraping actual 2025 tournament box scores...")
    print("=" * 60)
    actual_df = scrape_tournament_results_per_team(TOURNAMENT_TEAMS_2025)

    if actual_df.empty:
        print("[FATAL] No tournament actuals collected.")
        sys.exit(1)

    print(f"\nCollected actuals for {len(actual_df)} players")

    # ── Merge on player name ──
    # Names won't match perfectly, so we do a case-insensitive strip merge
    proj_df["player_key"]   = proj_df["player"].str.strip().str.lower()
    actual_df["player_key"] = actual_df["player"].str.strip().str.lower()

    merged = proj_df.merge(actual_df, on="player_key", how="inner", suffixes=("_proj", "_actual"))
    print(f"\nMatched {len(merged)} players between projections and actuals")

    if len(merged) < 10:
        print("[WARN] Very few matches — name format may differ between SR pages")
        print("Sample projected names:", proj_df["player"].head(5).tolist())
        print("Sample actual names:",    actual_df["player"].head(5).tolist())

    # ── Correlation ──
    r, p = stats.pearsonr(merged["projected_total"], merged["actual_total"])
    rho, p_spearman = stats.spearmanr(merged["projected_total"], merged["actual_total"])

    print("\n" + "=" * 60)
    print("BACKTEST RESULTS (2025 NCAA Tournament)")
    print("=" * 60)
    print(f"  Players matched:       {len(merged)}")
    print(f"  Pearson r:             {r:.3f}  (p={p:.4f})")
    print(f"  Spearman rho:          {rho:.3f}  (p={p_spearman:.4f})")
    print()
    if r >= 0.7:
        print("  ✓ Strong correlation — model is a solid predictor")
    elif r >= 0.5:
        print("  ~ Moderate correlation — model has signal but noise is significant")
    elif r >= 0.3:
        print("  ~ Weak correlation — model has some signal but limited predictive value")
    else:
        print("  ✗ Poor correlation — model does not predict tournament performance well")

    print()
    print("  Interpretation guide:")
    print("  Pearson r measures LINEAR correlation (projection vs actual total)")
    print("  Spearman rho measures RANK correlation (did high-ranked players finish high)")
    print("  Both matter for draft decisions.")

    # ── Save results ──
    out = merged[["player_proj", "team", "seed", "projected_total",
                  "actual_total", "actual_games"]].copy()
    out.columns = ["player", "team", "seed", "projected_total", "actual_total", "actual_games"]
    out["error"] = out["projected_total"] - out["actual_total"]
    out = out.sort_values("actual_total", ascending=False).reset_index(drop=True)
    out.index += 1
    out.index.name = "actual_rank"
    out.to_csv("backtest_2025.csv")
    print(f"\n  Full results saved → backtest_2025.csv")

    # ── Biggest misses ──
    out["abs_error"] = out["error"].abs()
    print("\n  Biggest over-projections (model was too optimistic):")
    print(out.nlargest(5, "error")[["player", "team", "seed", "projected_total", "actual_total", "error"]].to_string())
    print("\n  Biggest under-projections (model missed sleepers):")
    print(out.nsmallest(5, "error")[["player", "team", "seed", "projected_total", "actual_total", "error"]].to_string())


if __name__ == "__main__":
    run_backtest()