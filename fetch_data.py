"""Hämtar Juventus-data från football-data.org och sparar data.json.
Kräver miljövariabeln FOOTBALL_DATA_TOKEN. Inga extra paket behövs."""
import os, json, time, datetime, urllib.request

BASE = "https://api.football-data.org/v4"
TOKEN = os.environ["FOOTBALL_DATA_TOKEN"]


def get(path):
    req = urllib.request.Request(BASE + path, headers={"X-Auth-Token": TOKEN})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    time.sleep(7)  # gratisnivån tillåter 10 anrop/min
    return data


def safe(path):
    try:
        return get(path)
    except Exception as e:  # t.ex. 403 för data som kräver betalplan
        print("Hoppar över", path, e)
        return None


teams = get("/competitions/SA/teams")["teams"]
juve = next(t for t in teams if "Juventus" in t["name"])

matches = get(f"/teams/{juve['id']}/matches?competitions=SA")["matches"]
standings = safe("/competitions/SA/standings")
scorers = safe("/competitions/SA/scorers?limit=20")


def row(m):
    return {
        "date": m["utcDate"],
        "status": m["status"],
        "home": m["homeTeam"]["shortName"] or m["homeTeam"]["name"],
        "away": m["awayTeam"]["shortName"] or m["awayTeam"]["name"],
        "homeGoals": m["score"]["fullTime"]["home"],
        "awayGoals": m["score"]["fullTime"]["away"],
        "juveHome": m["homeTeam"]["id"] == juve["id"],
    }


table = []
if standings:
    table = [
        {
            "pos": r["position"], "team": r["team"]["shortName"],
            "played": r["playedGames"], "points": r["points"],
            "gf": r["goalsFor"], "ga": r["goalsAgainst"],
        }
        for r in standings["standings"][0]["table"]
    ]

out = {
    "updated": datetime.datetime.utcnow().isoformat() + "Z",
    "attribution": "Football data provided by the Football-Data.org API",
    "matches": [row(m) for m in matches],
    "table": table,
    "scorers": [
        {"name": s["player"]["name"], "team": s["team"]["shortName"], "goals": s["goals"]}
        for s in (scorers["scorers"] if scorers else [])
    ],
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("Klart:", len(out["matches"]), "matcher")
