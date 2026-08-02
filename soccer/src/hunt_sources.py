"""TASK 2: domain data for the shortlisted leagues, VERIFIED BY PULLING.

Every row in the output came from an HTTP response parsed in this run. A link
is not evidence (LEDGER T003).

The football-data.co.uk trap is handled explicitly: that site returns HTTP 200
with ANOTHER COUNTRY'S file for codes it does not carry. COL == POL == BOL
(Poland), KOR == NOR (Norway), CHL == CHI == CHN (China), byte-identical by
sha256. Every file is hashed AND its League column read before it is counted.
"""
import csv
import hashlib
import io
import json
import os
import time
from collections import Counter

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
CORE = "https://sports.core.api.espn.com/v2/sports/soccer/leagues"
LEAGUES = ["mex.1", "arg.1", "bra.1", "col.1", "usa.1"]

out = {}


def get(url, params=None, timeout=45):
    try:
        return requests.get(url, params=params, headers=UA, timeout=timeout)
    except requests.RequestException as e:
        print(f"    ERR {type(e).__name__}: {str(e)[:70]}")
        return None


print("=" * 70)
print("A. football-data.co.uk -- hashed, League column verified")
print("=" * 70)
FD = "https://www.football-data.co.uk/new/{}.csv"
hashes = {}
fd_rows = []
for code in ["MEX", "ARG", "BRA", "USA", "COL", "PER", "ECU", "URY", "CHL",
             "JPN", "KOR", "CHN", "POL", "NOR"]:
    r = get(FD.format(code))
    if r is None or r.status_code != 200 or len(r.content) < 2000:
        print(f"  {code:4s} DEAD http={getattr(r,'status_code','ERR')}")
        fd_rows.append({"code": code, "status": "DEAD"})
        continue
    h = hashlib.sha256(r.content).hexdigest()[:16]
    dup = hashes.get(h)
    hashes.setdefault(h, code)
    rows = list(csv.reader(io.StringIO(r.text)))
    hdr, body = rows[0], rows[1:]
    li = hdr.index("League") if "League" in hdr else None
    di = hdr.index("Date") if "Date" in hdr else None
    leagues = sorted({x[li] for x in body if li is not None and len(x) > li})
    dates = [x[di] for x in body if di is not None and len(x) > di and x[di]]
    pi = hdr.index("PSCH") if "PSCH" in hdr else None
    withp = sum(1 for x in body if pi is not None and len(x) > pi and x[pi].strip())
    status = f"DUPLICATE_OF_{dup}" if dup else "OK"
    print(f"  {code:4s} {status:16s} rows={len(body):5d} pinnacle={withp:5d} "
          f"leagues={leagues[:2]} {dates[0] if dates else ''}..{dates[-1] if dates else ''}")
    fd_rows.append({"code": code, "status": status, "sha256_16": h,
                    "rows": len(body), "with_pinnacle": withp,
                    "leagues": leagues, "cols": len(hdr),
                    "date_first": dates[0] if dates else None,
                    "date_last": dates[-1] if dates else None})
out["football_data"] = fd_rows

print("\n" + "=" * 70)
print("B. ESPN -- what else is in the free API")
print("=" * 70)
espn = {}
for lg in LEAGUES:
    row = {}
    r = get(f"{SITE}/{lg}/teams")
    n = len((r.json().get("sports", [{}])[0].get("leagues", [{}])[0]
             .get("teams", []))) if r is not None and r.status_code == 200 else None
    row["teams"] = n
    r = get(f"{SITE}/{lg}/standings")
    row["standings_http"] = getattr(r, "status_code", None)
    r = get(f"{CORE}/{lg}/seasons")
    row["seasons"] = (r.json().get("count")
                      if r is not None and r.status_code == 200 else None)
    r = get(f"{CORE}/{lg}/events", {"limit": 1})
    row["core_events_count"] = (r.json().get("count")
                                if r is not None and r.status_code == 200 else None)
    print(f"  {lg:8s} teams={row['teams']} standings={row['standings_http']} "
          f"seasons={row['seasons']} core_events={row['core_events_count']}")
    espn[lg] = row
    time.sleep(0.2)
out["espn"] = espn

print("\n  --- ESPN injuries / news / squad endpoints ---")
r = get(f"{SITE}/mex.1/teams")
tid = None
if r is not None and r.status_code == 200:
    ts = (r.json().get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", []))
    if ts:
        tid = ts[0]["team"]["id"]
        print(f"  sample team id={tid} {ts[0]['team'].get('displayName')}")
for name, u in [
    ("team injuries (core)", f"{CORE}/mex.1/teams/{tid}/injuries" if tid else None),
    ("team roster (site)", f"{SITE}/mex.1/teams/{tid}/roster" if tid else None),
    ("team detail (site)", f"{SITE}/mex.1/teams/{tid}" if tid else None),
    ("news", f"{SITE}/mex.1/news"),
]:
    if not u:
        continue
    r = get(u)
    detail = ""
    if r is not None and r.status_code == 200:
        try:
            d = r.json()
            if isinstance(d, dict):
                detail = f"keys={sorted(d)[:8]} count={d.get('count')}"
        except ValueError:
            detail = "non-json"
    print(f"    {name:22s} http={getattr(r,'status_code','ERR')} "
          f"bytes={len(r.content) if r is not None else 0} {detail}")
    out[f"espn_{name}"] = {"http": getattr(r, "status_code", None), "detail": detail}

print("\n" + "=" * 70)
print("C. other public sources")
print("=" * 70)
CHECKS = [
    ("StatsBomb open competitions", "https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json", "json"),
    ("Understat EPL (big-5 only?)", "https://understat.com/league/EPL", "text"),
    ("FBref Liga MX", "https://fbref.com/en/comps/31/Liga-MX-Stats", "text"),
    ("Transfermarkt Liga MX", "https://www.transfermarkt.com/liga-mx-apertura/startseite/wettbewerb/MEXA", "text"),
    ("API-Football (no key)", "https://v3.football.api-sports.io/leagues", "json"),
    ("openligadb (DE only)", "https://api.openligadb.de/getavailableleagues", "json"),
    ("ClubElo Liga MX club", "http://api.clubelo.com/Toluca", "csv"),
    ("ClubElo all clubs today", "http://api.clubelo.com/2026-08-02", "csv"),
    ("Wikipedia 2026 Liga MX", "https://en.wikipedia.org/api/rest_v1/page/summary/2026%E2%80%9327_Liga_MX_season", "json"),
    ("football-json (openfootball)", "https://api.github.com/repos/openfootball/football.json", "json"),
    ("soccerdata pkg", "https://api.github.com/repos/probberechts/soccerdata", "json"),
    ("worldfootballR", "https://api.github.com/repos/JaseZiv/worldfootballR", "json"),
]
for name, url, kind in CHECKS:
    r = get(url)
    if r is None:
        out[name] = {"status": "ERROR"}
        continue
    d = {"http": r.status_code, "bytes": len(r.content)}
    extra = ""
    if r.status_code == 200:
        try:
            if kind == "json":
                j = r.json()
                if isinstance(j, list):
                    d["n_items"] = len(j)
                    extra = f"items={len(j)}"
                    if j and isinstance(j[0], dict):
                        comps = Counter(x.get("competition_name") for x in j
                                        if isinstance(x, dict))
                        if comps:
                            extra += f" comps={list(comps)[:6]}"
                else:
                    d["keys"] = sorted(j)[:10]
                    extra = f"keys={sorted(j)[:8]}"
                    for k in ("pushed_at", "stargazers_count"):
                        if k in j:
                            extra += f" {k}={j[k]}"
            elif kind == "csv":
                rows = list(csv.reader(io.StringIO(r.text)))
                d["rows"] = len(rows) - 1
                extra = f"rows={len(rows)-1} cols={rows[0][:6] if rows else []}"
            else:
                extra = " ".join(r.text.split())[:90]
        except Exception as e:  # noqa: BLE001
            extra = f"parse-fail {type(e).__name__}"
    print(f"  {name:32s} http={r.status_code} bytes={len(r.content):8d} {extra[:100]}")
    out[name] = d

with open(os.path.join(REP, "hunt_sources.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, default=str)
print("\nwrote reports/hunt_sources.json")
