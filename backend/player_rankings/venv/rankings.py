import requests
import pandas as pd
from bs4 import BeautifulSoup
import time

YEAR = 2026

# expected number of games by seed
expected_games = {
    1:4.5, 2:3.8, 3:3.3, 4:3.0,
    5:2.6, 6:2.4, 7:2.1, 8:2.0,
    9:1.9, 10:1.8, 11:1.7, 12:1.6,
    13:1.3, 14:1.2, 15:1.1, 16:1.0
}

players = []

def get_tournament_teams():

    url = f"https://www.sports-reference.com/cbb/postseason/men/{YEAR}-ncaa.html"
    r = requests.get(url)
    soup = BeautifulSoup(r.text,"lxml")

    teams = []

    for row in soup.select("table tbody tr"):
        cols = row.find_all("td")

        if len(cols) > 0:
            try:
                seed = int(cols[0].text)
                team_link = cols[1].find("a")["href"]
                team = team_link.split("/")[3]

                teams.append((seed,team))
            except:
                pass

    return teams


def scrape_team(seed,team):

    url = f"https://www.sports-reference.com/cbb/schools/{team}/{YEAR}.html"
    r = requests.get(url)
    soup = BeautifulSoup(r.text,"lxml")

    table = soup.find("table",{"id":"per_game_stats"})
    rows = table.find("tbody").find_all("tr")

    for row in rows:

        cols = row.find_all("td")

        if len(cols) == 0:
            continue

        try:

            player = cols[0].text
            mpg = float(cols[2].text)
            rpg = float(cols[13].text)
            apg = float(cols[14].text)
            ppg = float(cols[19].text)

            fantasy_avg = ppg + rpg + apg
            projection = fantasy_avg * expected_games.get(seed,2)

            players.append({
                "player":player,
                "team":team,
                "seed":seed,
                "ppg":ppg,
                "rpg":rpg,
                "apg":apg,
                "mpg":mpg,
                "fantasy_avg":fantasy_avg,
                "projected_total":projection
            })

        except:
            pass


teams = get_tournament_teams()

for seed,team in teams:

    print("Scraping",team)

    scrape_team(seed,team)

    time.sleep(1)


df = pd.DataFrame(players)

# remove low-minute players
df = df[df["mpg"] > 18]

# ranking
df = df.sort_values("projected_total",ascending=False)

df.reset_index(drop=True,inplace=True)

df.to_csv("march_madness_draft_board.csv",index=False)

print(df.head(40))