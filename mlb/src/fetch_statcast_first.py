"""Download FIRST-INNING Statcast pitches, 2017-2026.

Why first innings only: the full feed is ~3,000 pitches a day, about 5M over a
decade. Filtering to inning 1 at the source (`hfInn=1|`) cuts it roughly 9x to
something that downloads in a sensible time and is exactly what the RFI model
needs.

What this buys over the current model. Right now the pitcher feature is "what
fraction of his past starts allowed a first-inning run" -- a binary outcome
rate on a handful of starts, which is mostly noise. Statcast gives the
underlying quality: expected wOBA on contact, hard-hit rate, strikeout and
walk rates, all measured on hundreds of pitches rather than a dozen games.
That is the difference between "he gave up a run in 4 of 12 starts" and "he
allows hard contact at the 80th percentile".

Resumable per (season, month). Content-validated: a chunk counts only if it
parses and carries the columns the features need.
"""
import csv
import io
import json
import os
import sys
import time
from collections import Counter
from datetime import date

import requests

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "statcast")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
URL = "https://baseballsavant.mlb.com/statcast_search/csv"
NEED = ["game_pk", "game_date", "inning", "pitcher", "batter", "events",
        "description", "estimated_woba_using_speedangle", "launch_speed",
        "release_speed", "stand", "p_throws", "at_bat_number", "pitch_number"]
SEASONS = range(2017, 2027)
MONTHS = [(3, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 10)]


def fetch(y, m0, m1, tries=4):
    lo = date(y, m0, 1).isoformat()
    hi = (date(y, m1, 31) if m1 in (3, 5, 7, 8, 10, 12)
          else date(y, m1, 30)).isoformat()
    params = {
        "all": "true", "hfInn": "1|", "hfSea": f"{y}|",
        "game_date_gt": lo, "game_date_lt": hi,
        "type": "details", "player_type": "pitcher",
    }
    for i in range(tries):
        try:
            r = requests.get(URL, params=params, headers=UA, timeout=300)
        except requests.RequestException as e:
            print(f"    net {type(e).__name__}, retry {i+1}", flush=True)
            time.sleep(20 * (i + 1))
            continue
        if r.status_code != 200 or len(r.content) < 500:
            print(f"    http {r.status_code} bytes {len(r.content)}, "
                  f"retry {i+1}", flush=True)
            time.sleep(25 * (i + 1))
            continue
        return r.text
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    prog_p = os.path.join(OUT, "_progress.json")
    prog = json.load(open(prog_p)) if os.path.exists(prog_p) else {}
    stats = Counter()
    for y in SEASONS:
        for m0, m1 in MONTHS:
            key = f"{y}-{m0:02d}"
            path = os.path.join(OUT, f"first_{key}.csv")
            if prog.get(key) == "done" and os.path.exists(path):
                continue
            t0 = time.time()
            txt = fetch(y, m0, m1)
            if txt is None:
                print(f"  {key}: FAILED", flush=True)
                stats["fail"] += 1
                continue
            rows = list(csv.reader(io.StringIO(txt)))
            if len(rows) < 2:
                prog[key] = "done"
                stats["empty"] += 1
                continue
            hdr = rows[0]
            missing = [c for c in NEED if c not in hdr]
            if missing:
                print(f"  {key}: MISSING COLUMNS {missing}", flush=True)
                stats["bad_schema"] += 1
                continue
            ii = hdr.index("inning")
            body = [r for r in rows[1:] if len(r) > ii and r[ii] == "1"]
            with open(path, "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(hdr)
                w.writerows(body)
            prog[key] = "done"
            json.dump(prog, open(prog_p, "w"))
            stats["chunks"] += 1
            stats["pitches"] += len(body)
            print(f"  {key}: {len(body):>7,} first-inning pitches "
                  f"({time.time()-t0:.0f}s)", flush=True)
            time.sleep(2)
    print(f"\nDONE {dict(stats)}")
    tot = 0
    for f in sorted(os.listdir(OUT)):
        if f.endswith(".csv"):
            with open(os.path.join(OUT, f), encoding="utf-8") as fh:
                tot += sum(1 for _ in fh) - 1
    print(f"first-inning pitches on disk: {tot:,}")


if __name__ == "__main__":
    main()
