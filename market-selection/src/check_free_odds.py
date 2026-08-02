"""Is there a FREE bookmaker line to benchmark Kalshi against, per family?

This decides whether a family is testable at all, and it is the single most
important thing dimension D does not capture.

LEDGER T012 is the template: Kalshi was shown to be the sharp line on tennis
(r=0.9878, MAD 1.95c vs a 2.44c round-trip cost) by comparing it to the Betfair
close. That comparison was only possible because tennis-data.co.uk publishes
closing odds for free. Without a sharp reference you cannot tell "our model
disagrees with Kalshi" from "our model is wrong", and every prior study in this
project that skipped the reference produced a retraction.

So: for each candidate family, does a free closing line exist?
"""
import json
import os

import requests

UA = {"User-Agent": "Mozilla/5.0 (market-selection-research/1.0)"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
CORE = "https://sports.core.api.espn.com/v2/sports"

out = {}


def get(url, params=None):
    try:
        return requests.get(url, params=params, headers=UA, timeout=45)
    except requests.RequestException as e:
        print("  ERR", type(e).__name__, str(e)[:80])
        return None


print("=== ESPN core API: does it expose odds? ===")
for sport, league in [("baseball", "mlb"), ("basketball", "nba"),
                      ("soccer", "usa.1"), ("soccer", "mex.1")]:
    r = get(f"{CORE}/{sport}/leagues/{league}/events")
    if r is None or r.status_code != 200:
        print(f"  {league:8s} events: http {getattr(r,'status_code','ERR')}")
        continue
    items = r.json().get("items", [])
    print(f"  {league:8s} events: {len(items)}")
    if not items:
        continue
    ref = items[0]["$ref"].split("?")[0]
    eid = ref.rstrip("/").split("/")[-1]
    odds_url = f"{ref}/competitions/{eid}/odds"
    ro = get(odds_url)
    code = getattr(ro, "status_code", "ERR")
    n = 0
    provs = []
    if ro is not None and ro.status_code == 200:
        d = ro.json()
        n = d.get("count", 0)
        for it in d.get("items", [])[:4]:
            p = (it.get("provider") or {}).get("name")
            away = (it.get("awayTeamOdds") or {}).get("moneyLine")
            home = (it.get("homeTeamOdds") or {}).get("moneyLine")
            provs.append({"provider": p, "details": it.get("details"),
                          "overUnder": it.get("overUnder"),
                          "awayML": away, "homeML": home})
    print(f"           odds: http {code}  providers {n}")
    for p in provs:
        print(f"             {p}")
    out[league] = {"odds_http": code, "n_providers": n, "sample": provs}

print("\n=== other free odds sources ===")
checks = [
    ("football-data.co.uk MEX (Liga MX)", "https://www.football-data.co.uk/new/MEX.csv"),
    ("football-data.co.uk USA (MLS)", "https://www.football-data.co.uk/new/USA.csv"),
    ("football-data.co.uk JPN (J-League)", "https://www.football-data.co.uk/new/JPN.csv"),
    ("football-data.co.uk KOR", "https://www.football-data.co.uk/new/KOR.csv"),
    ("football-data.co.uk ARG", "https://www.football-data.co.uk/new/ARG.csv"),
    ("football-data.co.uk BRA", "https://www.football-data.co.uk/new/BRA.csv"),
    ("tennis-data.co.uk index", "http://www.tennis-data.co.uk/alldata.php"),
]
for name, url in checks:
    r = get(url)
    code = getattr(r, "status_code", "ERR")
    size = len(r.content) if r is not None else 0
    head = ""
    if r is not None and r.status_code == 200 and url.endswith(".csv"):
        first = r.text.split("\n", 1)[0]
        cols = first.split(",")
        odds_cols = [c for c in cols if any(k in c.upper() for k in
                                            ("PSC", "PS", "MAX", "AVG", "B365", "BFE"))]
        head = f"cols={len(cols)} odds_cols={len(odds_cols)} {odds_cols[:8]}"
        rows = r.text.count("\n") - 1
        head += f" rows={rows}"
    print(f"  {name:38s} http={code} bytes={size} {head}")
    out[name] = {"http": code, "bytes": size, "detail": head}

with open(os.path.join(REP, "free_odds.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, default=str)
print("\nwrote reports/free_odds.json")
