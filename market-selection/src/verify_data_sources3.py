"""TASK 3, round three — domain data for the families that actually survived.

Rounds 1 and 2 probed the obvious sources. The preliminary kill-switch pass
named the families that matter, and several of them are ones nobody thinks
about when they think "sports data": NPB (Japanese baseball), KBO (Korean
baseball), Liga MX, MLS, boxing, Valorant, and the PGA/LPGA/Korn Ferry golf
tours. Those are where dimension D is genuinely uncertain, so they get probed
directly rather than assumed.

Everything is verified by fetching and parsing. A link is not evidence.
"""
import csv
import io
import json
import os
import time

import requests

BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")

SRC = [
    # ---- Japanese / Korean baseball (KXNPBGAME, KXNPBTOTAL, KXKBOGAME)
    ("npb", "NPB official site", "https://npb.jp/bis/2026/stats/", "text"),
    ("npb", "npb repo search", "https://api.github.com/search/repositories?q=NPB+baseball+data&sort=updated&per_page=8", "json"),
    ("npb", "pybaseball NPB?", "https://api.github.com/search/repositories?q=japanese+baseball+scraper&sort=updated&per_page=8", "json"),
    ("kbo", "KBO official", "https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx", "text"),
    ("kbo", "kbo data repo search", "https://api.github.com/search/repositories?q=KBO+baseball+data&sort=updated&per_page=8", "json"),

    # ---- soccer beyond Europe (KXLIGAMXGAME, KXMLSGAME, KXUSLGAME, KXCLUBFGAME)
    ("soccer", "openfootball MLS", "https://raw.githubusercontent.com/openfootball/football.json/master/2024-25/mls.json", "json"),
    ("soccer", "football-data.co.uk MX?", "https://www.football-data.co.uk/new/MEX.csv", "csv"),
    ("soccer", "football-data.co.uk USA (MLS)", "https://www.football-data.co.uk/new/USA.csv", "csv"),
    ("soccer", "api.football-data.org MLS", "https://api.football-data.org/v4/competitions/2145/matches", "json"),
    ("soccer", "understat league list", "https://understat.com/league/La_liga", "text"),
    ("soccer", "ClubElo ratings API", "http://api.clubelo.com/2026-08-01", "csv"),
    ("soccer", "openligadb", "https://api.openligadb.de/getmatchdata/bl1/2025", "json"),

    # ---- golf (KXPGATOUR, KXLPGATOUR, KXKFTOUR, KXPGATOP5/10/20)
    ("golf", "PGA Tour stats repo search", "https://api.github.com/search/repositories?q=pga+tour+data+scraper&sort=updated&per_page=8", "json"),
    ("golf", "DataGolf (free endpoint?)", "https://feeds.datagolf.com/preds/get-dg-rankings?file_format=json", "json"),
    ("golf", "ESPN golf leaderboard", "https://site.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard", "json"),
    ("golf", "ESPN golf scoreboard", "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard", "json"),

    # ---- esports (KXLOLGAME, KXVALORANTGAME, KXCS2GAME)
    ("esports", "Leaguepedia scoreboard games", "https://lol.fandom.com/api.php?action=cargoquery&tables=ScoreboardGames&fields=Tournament,Team1,Team2,Winner,DateTime_UTC,Gamelength&limit=20&format=json&order_by=DateTime_UTC%20DESC", "json"),
    ("esports", "vlr.gg valorant (unofficial api)", "https://vlrggapi.vercel.app/match?q=results", "json"),
    ("esports", "Liquipedia valorant api", "https://liquipedia.net/valorant/api.php?action=parse&page=Main_Page&format=json", "json"),
    ("esports", "OpenDota (dota, as a control)", "https://api.opendota.com/api/proMatches", "json"),

    # ---- ESPN generic (settlement source for 631 Kalshi series)
    ("espn", "ESPN MLB scoreboard", "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard", "json"),
    ("espn", "ESPN NBA scoreboard", "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard", "json"),
    ("espn", "ESPN tennis scoreboard", "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard", "json"),
    ("espn", "ESPN soccer MLS scoreboard", "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard", "json"),
    ("espn", "ESPN boxing scoreboard", "https://site.api.espn.com/apis/site/v2/sports/boxing/scoreboard", "json"),

    # ---- tennis, the surviving options
    ("tennis", "MatchCharting overview stats", "https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-m-stats-Overview.csv", "csv"),
    ("tennis", "tennisabstract", "https://www.tennisabstract.com/", "text"),
    ("tennis", "ultimatetennisstatistics", "https://www.ultimatetennisstatistics.com/rankingsTable", "text"),
]


def probe(fam, name, url, kind):
    rec = {"family": fam, "name": name, "url": url}
    try:
        r = requests.get(url, headers=BROWSER, timeout=50)
    except Exception as e:  # noqa: BLE001
        rec.update(status="ERROR", err=f"{type(e).__name__}: {str(e)[:110]}")
        return rec
    rec["http"] = r.status_code
    rec["bytes"] = len(r.content)
    if r.status_code != 200:
        rec["status"] = "DEAD"
        return rec
    try:
        if kind == "csv":
            rows = list(csv.reader(io.StringIO(r.text)))
            rec["n_rows"] = max(len(rows) - 1, 0)
            rec["n_columns"] = len(rows[0]) if rows else 0
            rec["columns"] = rows[0][:20] if rows else []
            rec["status"] = "OK" if rec["n_rows"] > 0 and rec["n_columns"] > 1 else "SUSPECT"
        elif kind == "json":
            d = r.json()
            rec["status"] = "OK"
            if isinstance(d, list):
                rec["n_items"] = len(d)
                if d and isinstance(d[0], dict):
                    rec["item_keys"] = sorted(d[0])[:16]
            else:
                rec["json_keys"] = sorted(d)[:16]
                cq = d.get("cargoquery")
                if cq is not None:
                    rec["n_items"] = len(cq)
                    if cq:
                        rec["sample"] = cq[0]
                ev = d.get("events")
                if ev is not None:
                    rec["n_items"] = len(ev)
                    if ev:
                        rec["sample_event"] = str(ev[0].get("name"))[:70]
                if "total_count" in d:
                    rec["total_count"] = d["total_count"]
                    rec["repos"] = [(x["full_name"], x["pushed_at"][:10],
                                     x["stargazers_count"])
                                    for x in d.get("items", [])[:6]]
        else:
            rec["status"] = "OK" if len(r.text) > 800 else "SUSPECT"
            rec["snippet"] = " ".join(r.text.split())[:150]
    except Exception as e:  # noqa: BLE001
        rec.update(status="UNPARSEABLE", err=f"{type(e).__name__}: {str(e)[:100]}")
    return rec


def main():
    out = []
    for fam, name, url, kind in SRC:
        rec = probe(fam, name, url, kind)
        out.append(rec)
        print(f"{fam:9s} {rec.get('status','?'):11s} {str(rec.get('http','-')):>4s} "
              f"{str(rec.get('bytes','-')):>9s}  {name}")
        for k in ("n_rows", "n_columns", "n_items", "total_count", "repos",
                  "columns", "item_keys", "sample_event", "err"):
            if k in rec:
                print(f"{'':10s} {k}={str(rec[k])[:175]}")
        time.sleep(0.4)
    with open(os.path.join(REP, "data_sources_probe3.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(f"\n{sum(r.get('status')=='OK' for r in out)}/{len(out)} OK")


if __name__ == "__main__":
    main()
