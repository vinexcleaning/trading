"""TASK 3 / dimension D — free domain data, VERIFIED BY FETCHING.

"A prior study assumed a data source existed and it was 404; another assumed a
tool was set up and it was not. Verify by actually fetching, not by finding a
link." (LEDGER T003: Sackmann's upstream repos are gone and the whole tennis
project runs on a frozen mirror.)

So this hits every candidate and records what actually came back: status, bytes,
content-type, a content fingerprint, and for tabular sources the real column
names and row count. A source is reported as available only if its content
parsed. Nothing here is taken from documentation.

Read-only. Public endpoints. No credentials.
"""
import csv
import io
import json
import os
import sys
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (market-selection-research/1.0)"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")

# (family, name, url, kind)  kind: csv | json | head | text
SOURCES = [
    # ---------------- tennis
    ("tennis", "Sackmann tennis_atp matches 2026", "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_2026.csv", "csv"),
    ("tennis", "Sackmann tennis_atp matches 2025", "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_2025.csv", "csv"),
    ("tennis", "Sackmann tennis_wta matches 2026", "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_2026.csv", "csv"),
    ("tennis", "Sackmann ATP repo API", "https://api.github.com/repos/JeffSackmann/tennis_atp", "json"),
    ("tennis", "Sackmann WTA repo API", "https://api.github.com/repos/JeffSackmann/tennis_wta", "json"),
    ("tennis", "Sackmann MatchChartingProject repo API", "https://api.github.com/repos/JeffSackmann/tennis_MatchChartingProject", "json"),
    ("tennis", "Sackmann Challenger/Futures 2026", "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_qual_chall_2026.csv", "csv"),
    ("tennis", "tennis-data.co.uk 2026 ATP odds", "http://www.tennis-data.co.uk/2026/2026.zip", "head"),

    # ---------------- soccer
    ("soccer", "football-data.co.uk E0 2526", "https://www.football-data.co.uk/mmz4281/2526/E0.csv", "csv"),
    ("soccer", "openfootball repo API", "https://api.github.com/repos/openfootball/football.json", "json"),
    ("soccer", "StatsBomb open-data repo API", "https://api.github.com/repos/statsbomb/open-data", "json"),
    ("soccer", "StatsBomb competitions.json", "https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json", "json"),
    ("soccer", "api.football-data.org v4 (no key)", "https://api.football-data.org/v4/competitions", "json"),

    # ---------------- baseball
    ("baseball", "MLB StatsAPI schedule", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-08-01", "json"),
    ("baseball", "MLB StatsAPI teams", "https://statsapi.mlb.com/api/v1/teams?sportId=1", "json"),
    ("baseball", "Baseball Savant statcast CSV", "https://baseballsavant.mlb.com/statcast_search/csv?all=true&game_date_gt=2026-07-30&game_date_lt=2026-07-30&type=details", "csv"),
    ("baseball", "Retrosheet", "https://www.retrosheet.org/gamelogs/gl2025.zip", "head"),
    ("baseball", "pybaseball repo API", "https://api.github.com/repos/jldbc/pybaseball", "json"),

    # ---------------- basketball
    ("basketball", "nba_api repo API", "https://api.github.com/repos/swar/nba_api", "json"),
    ("basketball", "stats.nba.com scoreboard", "https://stats.nba.com/stats/scoreboardv2?GameDate=2026-08-01&LeagueID=00&DayOffset=0", "json"),

    # ---------------- american football
    ("nfl", "nflverse pbp repo API", "https://api.github.com/repos/nflverse/nflverse-data", "json"),
    ("nfl", "nflverse schedules csv", "https://github.com/nflverse/nfldata/raw/master/data/games.csv", "csv"),

    # ---------------- crypto
    ("crypto", "Binance klines BTCUSDT", "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=5", "json"),
    ("crypto", "Coinbase BTC-USD candles", "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60", "json"),
    ("crypto", "Deribit BTC instruments", "https://www.deribit.com/api/v2/public/get_instruments?currency=BTC&kind=option", "json"),

    # ---------------- weather
    ("weather", "NWS API stations obs (KNYC)", "https://api.weather.gov/stations/KNYC/observations/latest", "json"),
    ("weather", "NWS gridpoint forecast NYC", "https://api.weather.gov/points/40.7128,-74.0060", "json"),
    ("weather", "NOAA GHCN daily readme", "https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt", "text"),

    # ---------------- esports
    ("esports", "Oracle's Elixir LoL match data", "https://oracleselixir-downloadable-match-data.s3-us-west-2.amazonaws.com/2026_LoL_esports_match_data_from_OraclesElixir.csv", "head"),
    ("esports", "Leaguepedia cargo API", "https://lol.fandom.com/api.php?action=cargoquery&tables=MatchSchedule&fields=Team1,Team2,DateTime_UTC&limit=5&format=json", "json"),
    ("esports", "HLTV (CS2) results page", "https://www.hltv.org/results", "head"),

    # ---------------- politics / economics
    ("politics", "FiveThirtyEight polls repo API", "https://api.github.com/repos/fivethirtyeight/data", "json"),
    ("politics", "538 president approval csv", "https://projects.fivethirtyeight.com/polls/data/president_approval_polls.csv", "csv"),
    ("economics", "FRED series (no key)", "https://api.stlouisfed.org/fred/series?series_id=CPIAUCSL", "head"),
    ("economics", "BLS CPI public API", "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0", "json"),
    ("economics", "US Treasury yield curve", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all?type=daily_treasury_yield_curve&field_tdr_date_value=2026&page&_format=csv", "csv"),
]


def probe(family, name, url, kind):
    rec = {"family": family, "name": name, "url": url, "kind": kind}
    t0 = time.time()
    try:
        if kind == "head":
            r = requests.get(url, headers=UA, timeout=45, stream=True)
            body = next(r.iter_content(4096), b"")
            r.close()
        else:
            r = requests.get(url, headers=UA, timeout=60)
            body = r.content
    except Exception as e:  # noqa: BLE001
        rec.update(status="ERROR", err=f"{type(e).__name__}: {str(e)[:140]}")
        return rec
    rec["http"] = r.status_code
    rec["ms"] = int((time.time() - t0) * 1000)
    rec["content_type"] = (r.headers.get("content-type") or "")[:60]
    rec["bytes"] = len(body) if kind != "head" else int(r.headers.get("content-length") or 0)

    if r.status_code != 200:
        rec["status"] = "DEAD"
        rec["snippet"] = body[:160].decode("utf-8", "replace")
        return rec

    try:
        if kind == "csv":
            txt = body.decode("utf-8", "replace")
            rows = list(csv.reader(io.StringIO(txt)))
            if not rows:
                rec.update(status="EMPTY")
                return rec
            rec["columns"] = rows[0][:28]
            rec["n_columns"] = len(rows[0])
            rec["n_rows"] = len(rows) - 1
            rec["status"] = "OK" if len(rows) > 1 else "EMPTY"
            if len(rows) > 1:
                rec["sample_row"] = rows[1][:12]
        elif kind == "json":
            d = json.loads(body)
            rec["status"] = "OK"
            if isinstance(d, dict):
                rec["json_keys"] = sorted(d.keys())[:22]
                for k in ("pushed_at", "updated_at", "stargazers_count",
                          "size", "default_branch", "archived"):
                    if k in d:
                        rec[k] = d[k]
            elif isinstance(d, list):
                rec["n_items"] = len(d)
                if d and isinstance(d[0], dict):
                    rec["item_keys"] = sorted(d[0].keys())[:22]
                rec["status"] = "OK" if d else "EMPTY"
        else:
            rec["status"] = "OK" if rec["bytes"] else "EMPTY"
            rec["snippet"] = body[:180].decode("utf-8", "replace").replace("\n", " ")
    except Exception as e:  # noqa: BLE001
        rec.update(status="UNPARSEABLE", err=f"{type(e).__name__}: {str(e)[:120]}")
    return rec


def main():
    out = []
    print(f"{'family':11s} {'status':12s} {'http':>4s} {'bytes':>10s}  name")
    for fam, name, url, kind in SOURCES:
        rec = probe(fam, name, url, kind)
        out.append(rec)
        print(f"{fam:11s} {rec.get('status','?'):12s} "
              f"{str(rec.get('http','-')):>4s} {str(rec.get('bytes','-')):>10s}  {name}")
        extra = []
        if "n_rows" in rec:
            extra.append(f"rows={rec['n_rows']} cols={rec['n_columns']}")
        if "n_items" in rec:
            extra.append(f"items={rec['n_items']}")
        if "pushed_at" in rec:
            extra.append(f"last_push={rec['pushed_at']}")
        if "archived" in rec:
            extra.append(f"archived={rec['archived']}")
        if rec.get("err"):
            extra.append(rec["err"])
        if extra:
            print(f"{'':11s} {'':12s} {'':4s} {'':>10s}    -> {'; '.join(extra)}")
        time.sleep(0.4)

    with open(os.path.join(REP, "data_sources_probe.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    ok = sum(r.get("status") == "OK" for r in out)
    print(f"\n{ok}/{len(out)} sources returned parseable content")
    print("wrote reports/data_sources_probe.json")


if __name__ == "__main__":
    sys.exit(main())
