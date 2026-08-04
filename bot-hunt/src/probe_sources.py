"""STEP 3 (started early, because it gates STEP 2's ranking) — verify every
candidate free data source by FETCHING it.

Two prior sessions in this repo listed sources that turned out to be 404 or
403. One source is known to lie with a 200: football-data.co.uk returns the
WRONG COUNTRY'S FILE for codes it does not carry (COL is Poland, KOR is Norway,
CHL is China, byte-identical by sha256). So every download here is hashed and
every tabular file has its own content column checked.

Nothing in this file is a data source *decision*. It is the measurement that a
decision can be made from.

Output: reports/sources_probe.json
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parent.parent / "reports"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0 Safari/537.36")}

# (key, url, kind). kind drives the content check.
SOURCES = [
    # --- reference PRICES (the mechanism the extractor corpus surfaced:
    #     fair value comes from a sharper venue, not from a domain model) ---
    ("espn_odds_mlb", "https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/events", "espn"),
    ("espn_scoreboard_mlb", "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard", "json"),
    ("espn_scoreboard_ligamx", "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard", "json"),
    ("espn_scoreboard_argprim", "https://site.api.espn.com/apis/site/v2/sports/soccer/arg.1/scoreboard", "json"),
    ("espn_scoreboard_brasileirao", "https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1/scoreboard", "json"),
    ("espn_scoreboard_tennis", "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard", "json"),
    ("espn_scoreboard_lol", "https://site.api.espn.com/apis/site/v2/sports/esports/lol/scoreboard", "json"),
    ("espn_scoreboard_nba", "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard", "json"),

    # historic de-viggable closing lines
    ("fd_mex", "https://www.football-data.co.uk/new/MEX.csv", "csv_country"),
    ("fd_arg", "https://www.football-data.co.uk/new/ARG.csv", "csv_country"),
    ("fd_bra", "https://www.football-data.co.uk/new/BRA.csv", "csv_country"),
    ("fd_usa", "https://www.football-data.co.uk/new/USA.csv", "csv_country"),
    ("fd_col_TRAP", "https://www.football-data.co.uk/new/COL.csv", "csv_country"),
    ("fd_pol_TRAP", "https://www.football-data.co.uk/new/POL.csv", "csv_country"),
    ("fd_jpn", "https://www.football-data.co.uk/new/JPN.csv", "csv_country"),
    ("fd_kor_TRAP", "https://www.football-data.co.uk/new/KOR.csv", "csv_country"),
    ("fd_nor_TRAP", "https://www.football-data.co.uk/new/NOR.csv", "csv_country"),
    ("tennis_data_index", "https://www.tennis-data.co.uk/alldata.php", "html"),

    # --- esports: the family whose free data layer market-selection recorded
    #     as collapsed. Re-checked because the one publicly reconciled live
    #     P&L found anywhere runs on Polymarket ESPORTS. ---
    ("oracles_elixir", "https://oracleselixir-downloadable-match-data.s3-us-west-2.amazonaws.com/2026_LoL_esports_match_data_from_OraclesElixir.csv", "csv"),
    ("hltv", "https://www.hltv.org/matches", "html"),
    ("vlr_api", "https://vlrggapi.vercel.app/match?q=upcoming", "json"),
    ("bo3gg", "https://bo3.gg/matches", "html"),
    ("leaguepedia", "https://lol.fandom.com/api.php?action=cargoquery&tables=MatchSchedule&fields=Team1,Team2,DateTime_UTC&limit=20&format=json", "json"),
    ("pandascore_free", "https://api.pandascore.co/lol/matches/upcoming", "json"),
    ("liquipedia_lol", "https://liquipedia.net/leagueoflegends/api.php?action=parse&page=Liquipedia:Matches&format=json", "json"),
    ("grid_gg", "https://api.grid.gg/", "html"),

    # --- odds aggregators / sharp books, free tiers ---
    ("the_odds_api_sports", "https://api.the-odds-api.com/v4/sports/", "json"),
    ("pinnacle_guest", "https://guest.api.arcadia.pinnacle.com/0.1/sports", "json"),
    ("oddsapi_esports", "https://api.the-odds-api.com/v4/sports/esports_lol/odds/?regions=eu&markets=h2h", "json"),

    # --- domain data for the families already shortlisted by the prior pass ---
    ("mlb_statsapi", "https://statsapi.mlb.com/api/v1/schedule?sportId=1", "json"),
    ("statcast_probe", "https://baseballsavant.mlb.com/statcast_search/csv?all=true&hfPT=&hfAB=&player_type=batter&game_date_gt=2026-08-01&game_date_lt=2026-08-01&type=details", "csv"),
    ("nws_points", "https://api.weather.gov/points/40.7128,-74.0060", "json"),
    ("clubelo", "http://api.clubelo.com/2026-08-01", "csv"),

    # --- order-book archives (the only route to a real L2 backtest) ---
    ("pmxt_root", "https://r2v2.pmxt.dev/", "html"),
    ("pmxt_archive_root", "https://archive.pmxt.dev/", "html"),
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def probe(key: str, url: str, kind: str) -> dict:
    t0 = time.time()
    rec = {"key": key, "url": url, "kind": kind}
    try:
        r = requests.get(url, headers=UA, timeout=45)
    except requests.RequestException as exc:
        rec.update(status=None, error=f"{type(exc).__name__}: {exc}",
                   seconds=round(time.time() - t0, 2))
        return rec
    body = r.content or b""
    rec.update(status=r.status_code, bytes=len(body), sha256=sha(body)[:16],
               content_type=r.headers.get("Content-Type", "")[:60],
               seconds=round(time.time() - t0, 2))
    if r.status_code != 200:
        rec["snippet"] = body[:200].decode("utf-8", "replace")
        return rec

    if kind in ("csv", "csv_country"):
        try:
            text = body.decode("utf-8", "replace")
            lines = text.splitlines()
            rec["rows"] = max(0, len(lines) - 1)
            header = lines[0].split(",") if lines else []
            rec["cols"] = len(header)
            rec["header"] = header[:14]
            if kind == "csv_country":
                # THE TRAP: a 200 with the wrong country's data. Read the
                # actual League/Div column values rather than trusting the URL.
                idx = None
                for cand in ("League", "Div", "Country"):
                    if cand in header:
                        idx = header.index(cand)
                        rec["league_col"] = cand
                        break
                if idx is not None:
                    vals = defaultdict(int)
                    for ln in lines[1:2000]:
                        parts = ln.split(",")
                        if len(parts) > idx:
                            vals[parts[idx].strip()] += 1
                    rec["league_values"] = sorted(vals.items(),
                                                  key=lambda x: -x[1])[:5]
        except Exception as exc:  # noqa: BLE001
            rec["parse_error"] = f"{type(exc).__name__}: {exc}"
    elif kind == "json":
        try:
            d = r.json()
            rec["json_type"] = type(d).__name__
            if isinstance(d, dict):
                rec["json_keys"] = list(d.keys())[:12]
                for k in ("events", "data", "matches", "results", "sports"):
                    if isinstance(d.get(k), list):
                        rec["n_items"] = len(d[k])
                        break
            elif isinstance(d, list):
                rec["n_items"] = len(d)
        except ValueError:
            rec["parse_error"] = "not json"
            rec["snippet"] = body[:200].decode("utf-8", "replace")
    elif kind == "espn":
        try:
            d = r.json()
            rec["n_items"] = d.get("count")
            rec["json_keys"] = list(d.keys())[:10]
        except ValueError:
            rec["parse_error"] = "not json"
    elif kind == "html":
        text = body.decode("utf-8", "replace")
        rec["text_chars"] = len(re.sub(r"<[^>]+>", " ", text))
        rec["title"] = (re.search(r"<title[^>]*>(.*?)</title>", text,
                                  re.S | re.I) or [None, ""])[1].strip()[:80]
    return rec


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    out = []
    for key, url, kind in SOURCES:
        if only and key not in only:
            continue
        rec = probe(key, url, kind)
        out.append(rec)
        st = rec.get("status")
        flag = "OK " if st == 200 else "!! "
        extra = ""
        if rec.get("league_values"):
            extra = f"  league={rec['league_values'][:2]}"
        elif rec.get("n_items") is not None:
            extra = f"  items={rec['n_items']}"
        elif rec.get("rows") is not None:
            extra = f"  rows={rec['rows']} cols={rec.get('cols')}"
        elif rec.get("text_chars") is not None:
            extra = f"  text={rec['text_chars']}  title={rec.get('title','')!r}"
        print(f"{flag}{key:24} {str(st):>5} {rec.get('bytes', 0):>9} B "
              f"{rec.get('sha256','')}{extra}")
        if rec.get("error"):
            print(f"      {rec['error'][:150]}")
    (OUT / "sources_probe.json").write_text(json.dumps(out, indent=1),
                                            encoding="utf-8")
    n_ok = sum(1 for r in out if r.get("status") == 200)
    print(f"\n{n_ok}/{len(out)} returned 200 -> reports/sources_probe.json")

    # The trap check, stated as a result rather than assumed.
    by_sha = defaultdict(list)
    for r in out:
        if r.get("status") == 200 and r.get("sha256"):
            by_sha[r["sha256"]].append(r["key"])
    dupes = {s: k for s, k in by_sha.items() if len(k) > 1}
    if dupes:
        print("\n!! BYTE-IDENTICAL RESPONSES FROM DIFFERENT URLS:")
        for s, keys in dupes.items():
            print(f"   {s}  {keys}")
    else:
        print("\nno two probed URLs returned byte-identical bodies")


if __name__ == "__main__":
    main()
