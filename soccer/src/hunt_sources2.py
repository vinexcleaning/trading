"""TASK 2 follow-up: how deep is ESPN's back-catalogue, and do the
xG/Elo sources actually cover OUR leagues?

Three things worth settling:
  1. ESPN reports 21-31 seasons per league. Is the historical event list
     actually retrievable, or is `seasons` a menu with nothing behind it?
  2. StatsBomb open-data has 80 competitions -- but which? It is famously
     Europe-heavy, and the leagues we care about are not European.
  3. ClubElo answered for a Liga MX club. Does it really rate these leagues,
     or did it return an empty stub?
"""
import csv
import io
import json
import os
from collections import Counter

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
out = {}


def get(u, p=None):
    try:
        return requests.get(u, params=p, headers=UA, timeout=45)
    except requests.RequestException as e:
        print("   ERR", type(e).__name__, str(e)[:60])
        return None


print("=== 1. ESPN historical depth: matches per past season ===")
depth = {}
for lg in ["mex.1", "arg.1", "bra.1", "col.1", "usa.1"]:
    row = {}
    for yr in (2026, 2024, 2022, 2019, 2015):
        r = get(f"{SITE}/{lg}/scoreboard",
                {"dates": f"{yr}0301-{yr}0308", "limit": 400})
        n = len(r.json().get("events", [])) if r is not None and r.status_code == 200 else None
        row[yr] = n
    depth[lg] = row
    print(f"  {lg:8s} matches in a sample week: {row}")
out["espn_history"] = depth

print("\n=== 2. StatsBomb open data: which competitions? ===")
r = get("https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json")
if r is not None and r.status_code == 200:
    comps = r.json()
    names = sorted({(c.get("country_name"), c.get("competition_name"))
                    for c in comps})
    print(f"  {len(comps)} competition-seasons, "
          f"{len(names)} distinct country/competition pairs:")
    for cn, nm in names:
        print(f"    {str(cn)[:22]:22s} {nm}")
    ours = [x for x in names if str(x[0]).lower() in
            ("mexico", "argentina", "brazil", "colombia", "united states")]
    print(f"\n  covering OUR leagues: {ours if ours else 'NONE'}")
    out["statsbomb"] = {"n": len(comps), "pairs": [list(x) for x in names],
                        "ours": [list(x) for x in ours]}

print("\n=== 3. ClubElo: does it rate these leagues? ===")
r = get("http://api.clubelo.com/2026-08-02")
if r is not None and r.status_code == 200:
    rows = list(csv.reader(io.StringIO(r.text)))
    hdr, body = rows[0], rows[1:]
    ci = hdr.index("Country")
    countries = Counter(x[ci] for x in body if len(x) > ci)
    print(f"  {len(body)} clubs across {len(countries)} countries")
    for c in ("MEX", "ARG", "BRA", "COL", "USA"):
        print(f"    {c}: {countries.get(c, 0)} clubs")
    print(f"  top countries: {countries.most_common(10)}")
    out["clubelo"] = {"n_clubs": len(body), "by_country": dict(countries)}
    # is a specific Liga MX club really rated?
    r2 = get("http://api.clubelo.com/Toluca")
    if r2 is not None and r2.status_code == 200:
        rr = list(csv.reader(io.StringIO(r2.text)))
        print(f"  /Toluca -> {len(rr)-1} history rows; sample: "
              f"{rr[1] if len(rr) > 1 else 'EMPTY'}")

print("\n=== 4. Understat: which leagues does it actually carry? ===")
r = get("https://understat.com/")
if r is not None and r.status_code == 200:
    txt = r.text
    found = [lg for lg in ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1",
                           "RFPL", "Liga_MX", "MLS", "Brasileirao"]
             if lg in txt]
    print(f"  league links present on the homepage: {found}")
    out["understat_leagues"] = found

print("\n=== 5. community scrapers for OUR leagues ===")
for q in ["liga mx data", "liga mx scraper", "brasileirao dataset",
          "argentina primera datos futbol", "soccerdata liga mx"]:
    r = get("https://api.github.com/search/repositories",
            {"q": q, "sort": "updated", "per_page": 6})
    if r is None or r.status_code != 200:
        continue
    d = r.json()
    print(f"\n  {q!r}: {d.get('total_count')} repos")
    for x in d.get("items", [])[:6]:
        print(f"    {x['full_name'][:44]:44s} pushed={x['pushed_at'][:10]} "
              f"stars={x['stargazers_count']:4d} size={x['size']}KB")

with open(os.path.join(REP, "hunt_sources2.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, default=str)
print("\nwrote reports/hunt_sources2.json")
