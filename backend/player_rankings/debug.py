import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

url = "https://www.sports-reference.com/cbb/schools/duke/men/2026.html"
r = requests.get(url, headers=HEADERS, timeout=15)
html = r.text.replace("<!--", "").replace("-->", "")
soup = BeautifulSoup(html, "lxml")

table = soup.find("table", {"id": "players_per_game"})
print(f"Table found: {table is not None}")

rows = table.find("tbody").find_all("tr")
print(f"Total rows: {len(rows)}")
print()

for i, row in enumerate(rows[:5]):
    print(f"--- Row {i} ---")
    print(f"  classes: {row.get('class')}")

    # Check all th and td cells
    ths = row.find_all("th")
    tds = row.find_all("td")
    print(f"  <th> cells: {[(t.get('data-stat'), t.text.strip()[:20]) for t in ths]}")
    print(f"  <td> cells (first 6): {[(t.get('data-stat'), t.text.strip()[:20]) for t in tds[:6]]}")

    # Try to find player name cell
    name_td = row.find("td", {"data-stat": "player"})
    name_th = row.find("th", {"data-stat": "player"})
    print(f"  player <td>: {name_td}")
    print(f"  player <th>: {name_th}")

    # Try to find stats
    for stat in ["mp_per_g", "pts_per_g", "trb_per_g", "ast_per_g"]:
        cell = row.find("td", {"data-stat": stat})
        print(f"  {stat}: {cell.text.strip() if cell else 'NOT FOUND'}")
    print()