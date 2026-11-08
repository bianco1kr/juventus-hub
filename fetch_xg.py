"""Hämtar xG-data för Juventus från Understat och sparar xg.json.
Misslyckas hämtningen avslutas skriptet utan fel och xg.json lämnas orörd."""
import json, re, gzip, sys, datetime, urllib.request

SEASON = 2026  # säsongens startår (2026/27)
UA = {"User-Agent": "Mozilla/5.0 (juventus-hub hobby project)", "Accept-Encoding": "gzip"}


def fetch(url, extra=None):
    req = urllib.request.Request(url, headers={**UA, **(extra or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def from_xhr():
    url = f"https://understat.com/getLeagueData/Serie_A/{SEASON}"
    txt = fetch(url, {"X-Requested-With": "XMLHttpRequest",
                      "Referer": f"https://understat.com/league/Serie_A/{SEASON}"})
    d = json.loads(txt)
    return d["teams"], d["players"], d["dates"]


def from_html():
    html = fetch(f"https://understat.com/league/Serie_A/{SEASON}")

    def grab(name):
        m = re.search(name + r"\s*=\s*JSON\.parse\('(.+?)'\)", html)
        return json.loads(m.group(1).encode().decode("unicode_escape"))

    return grab("teamsData"), grab("playersData"), grab("datesData")


try:
    try:
        teams, players, dates = from_xhr()
    except Exception as e:
        print("XHR misslyckades, provar HTML:", e)
        teams, players, dates = from_html()

    juve = next(t for t in teams.values() if "Juventus" in t["title"])
    hist = juve["history"]
    n = len(hist) or 1

    out = {
        "updated": datetime.datetime.utcnow().isoformat() + "Z",
        "source": "understat.com",
        "season": f"{SEASON}/{str(SEASON + 1)[2:]}",
        "team": {
            "games": len(hist),
            "xG": round(sum(float(h["xG"]) for h in hist), 2),
            "xGA": round(sum(float(h["xGA"]) for h in hist), 2),
            "goals": sum(int(h["scored"]) for h in hist),
            "conceded": sum(int(h["missed"]) for h in hist),
            "xGperMatch": round(sum(float(h["xG"]) for h in hist) / n, 2),
        },
        "matches": [
            {
                "date": d["datetime"],
                "home": d["h"]["title"], "away": d["a"]["title"],
                "goals": [d["goals"]["h"], d["goals"]["a"]],
                "xG": [d["xG"]["h"], d["xG"]["a"]],
            }
            for d in dates
            if d["isResult"] and (d["h"]["title"] == juve["title"] or d["a"]["title"] == juve["title"])
        ],
        "players": sorted(
            [
                {
                    "name": p["player_name"], "pos": p["position"], "games": p["games"],
                    "minutes": p["time"], "goals": p["goals"], "xG": p["xG"],
                    "assists": p["assists"], "xA": p["xA"], "shots": p["shots"],
                    "npxG": p["npxG"], "keyPasses": p["key_passes"],
                }
                for p in players if "Juventus" in p["team_title"]
            ],
            key=lambda p: -float(p["xG"]),
        ),
    }
    with open("xg.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("xG klart:", len(out["players"]), "spelare,", len(out["matches"]), "matcher")
except Exception as e:
    print("xG-hämtning hoppades över:", e)
    sys.exit(0)
