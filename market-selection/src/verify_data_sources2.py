"""TASK 3, round two — retry the sources that failed, with corrected access.

Round one's failures split into two kinds, and the distinction matters:
  - genuinely gone (the repo is deleted): nothing to retry
  - my access was wrong (bad URL, missing header, geo-block): retry properly

Reporting a live source as dead is as damaging as the reverse, so every
round-one failure gets a second, better-informed attempt before it is written
up as unavailable.
"""
import csv
import io
import json
import os
import time

import requests

BROWSER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}
NBA = dict(BROWSER, Referer="https://www.nba.com/",
           Origin="https://www.nba.com", **{"x-nba-stats-origin": "stats",
                                            "x-nba-stats-token": "true"})
REP = os.path.join(os.path.dirname(__file__), "..", "reports")

RETRIES = [
    # round-1 status, family, name, url, headers, kind, why it failed before
    ("tennis", "Sackmann tennis_atp (org root)", "https://api.github.com/users/JeffSackmann/repos?per_page=100", BROWSER, "json", "repo 404 - check whether the ACCOUNT still exists"),
    ("tennis", "tennis-data.co.uk 2026 ATP", "http://www.tennis-data.co.uk/2026/ausopen.zip", BROWSER, "head", "root 300 multiple choices"),
    ("tennis", "tennis-data.co.uk index", "http://www.tennis-data.co.uk/alldata.php", BROWSER, "text", "find the real file names"),
    ("tennis", "tennis_atp mirror (search)", "https://api.github.com/search/repositories?q=tennis_atp+sackmann&per_page=5", BROWSER, "json", "is there a surviving fork?"),
    ("tennis", "MatchCharting matches csv", "https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-m-matches.csv", BROWSER, "csv", "repo alive - what is in it"),
    ("esports", "Oracle's Elixir 2026 (alt path)", "https://oracleselixir-downloadable-match-data.s3.us-west-2.amazonaws.com/2026_LoL_esports_match_data_from_OraclesElixir.csv", BROWSER, "head", "404 - region in hostname changed"),
    ("esports", "Oracle's Elixir 2025", "https://oracleselixir-downloadable-match-data.s3.us-west-2.amazonaws.com/2025_LoL_esports_match_data_from_OraclesElixir.csv", BROWSER, "head", "does any year work?"),
    ("basketball", "stats.nba.com scoreboard", "https://stats.nba.com/stats/scoreboardv2?GameDate=2026-08-01&LeagueID=00&DayOffset=0", NBA, "json", "timeout - needs referer/origin headers"),
    ("crypto", "Binance klines (data-api host)", "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=5", BROWSER, "json", "451 geo-block on api.binance.com"),
    ("crypto", "Kraken OHLC BTCUSD", "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1", BROWSER, "json", "alternative to Binance"),
    ("politics", "538 approval csv (raw check)", "https://projects.fivethirtyeight.com/polls/data/president_approval_polls.csv", BROWSER, "csv", "parsed as 55 rows / 0 cols - suspicious"),
    ("esports", "HLTV results", "https://www.hltv.org/results", BROWSER, "text", "200 but 0 bytes - Cloudflare"),
    ("soccer", "FBref (worldfootballR source)", "https://fbref.com/en/comps/9/Premier-League-Stats", BROWSER, "text", "not probed in round 1"),
    ("soccer", "understat", "https://understat.com/league/EPL", BROWSER, "text", "not probed in round 1"),
    ("baseball", "MLB StatsAPI live feed", "https://statsapi.mlb.com/api/v1.1/game/775296/feed/live", BROWSER, "json", "how deep is the free live feed"),
]


def probe(family, name, url, headers, kind, why):
    rec = {"family": family, "name": name, "url": url, "why_retried": why}
    try:
        if kind == "head":
            r = requests.get(url, headers=headers, timeout=45, stream=True)
            body = next(r.iter_content(8192), b"")
            rec["bytes"] = int(r.headers.get("content-length") or len(body))
            r.close()
        else:
            r = requests.get(url, headers=headers, timeout=60)
            body = r.content
            rec["bytes"] = len(body)
    except Exception as e:  # noqa: BLE001
        rec.update(status="ERROR", err=f"{type(e).__name__}: {str(e)[:130]}")
        return rec
    rec["http"] = r.status_code
    if r.status_code != 200:
        rec["status"] = "DEAD"
        rec["snippet"] = body[:150].decode("utf-8", "replace")
        return rec
    try:
        if kind == "csv":
            txt = body.decode("utf-8", "replace")
            rows = list(csv.reader(io.StringIO(txt)))
            rec["n_rows"] = max(len(rows) - 1, 0)
            rec["n_columns"] = len(rows[0]) if rows else 0
            rec["columns"] = rows[0][:24] if rows else []
            rec["status"] = "OK" if rec["n_rows"] > 0 and rec["n_columns"] > 1 else "SUSPECT"
        elif kind == "json":
            d = json.loads(body)
            rec["status"] = "OK"
            if isinstance(d, list):
                rec["n_items"] = len(d)
                if d and isinstance(d[0], dict):
                    rec["sample"] = {k: str(v)[:40] for k, v in
                                     list(d[0].items())[:6]}
            else:
                rec["json_keys"] = sorted(d.keys())[:20]
                if "resultSets" in d:
                    rec["n_resultsets"] = len(d["resultSets"])
                if "items" in d:
                    rec["n_items"] = len(d["items"])
                if "total_count" in d:
                    rec["total_count"] = d["total_count"]
                    rec["repos"] = [x["full_name"] for x in d.get("items", [])[:5]]
        else:
            txt = body.decode("utf-8", "replace")
            rec["status"] = "OK" if len(txt) > 500 else "SUSPECT"
            rec["snippet"] = " ".join(txt.split())[:220]
    except Exception as e:  # noqa: BLE001
        rec.update(status="UNPARSEABLE", err=f"{type(e).__name__}: {str(e)[:110]}")
    return rec


def main():
    out = []
    for fam, name, url, hdr, kind, why in RETRIES:
        rec = probe(fam, name, url, hdr, kind, why)
        out.append(rec)
        print(f"{fam:11s} {rec.get('status','?'):11s} {str(rec.get('http','-')):>4s} "
              f"{str(rec.get('bytes','-')):>9s}  {name}")
        for k in ("n_rows", "n_columns", "n_items", "total_count", "repos",
                  "n_resultsets", "err", "snippet", "columns", "sample"):
            if k in rec:
                print(f"{'':12s} {k} = {str(rec[k])[:190]}")
        time.sleep(0.5)
    with open(os.path.join(REP, "data_sources_probe2.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(f"\n{sum(r.get('status')=='OK' for r in out)}/{len(out)} recovered")


if __name__ == "__main__":
    main()
