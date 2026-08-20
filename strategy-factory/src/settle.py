"""FETCH SETTLEMENT OUTCOMES — the thing the recorder does not capture.

⚠ THE GAP THIS CLOSES, AND IT WAS NOT OBVIOUS UNTIL SCREENING WAS ATTEMPTED.

The recorder sweeps OPEN markets. When a market closes it simply stops appearing
in the sweep, so the tape holds every price a market ever had and **never holds
how it turned out.** No screening of any kind is possible without that, and it
is not recoverable later at leisure: Kalshi's window is ~69 days and a closed
market 404s.

Kalshi does publish it. `/markets?status=settled` returns `result` ("yes"/"no")
and `expiration_value`, so this is a fetch rather than a problem.

SCOPE: only the families a LIVE spec actually names. An exchange-wide settled
sweep is dominated by the two parlay families exactly as the open sweep is -
the first page of 1,000 settled markets was 1,000 `KXMVECROSSCATEGORY` rows -
so asking per series is both cheaper and honest about what is being screened.

    py -3 strategy-factory/src/settle.py
    py -3 strategy-factory/src/settle.py --series KXBTCD,KXETHD
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "bot-hunt" / "src"))
sys.path.insert(0, str(ROOT / "src"))
import venues as V  # noqa: E402

DB = ROOT / "data" / "settled.db"

SCHEMA = """
create table if not exists settled (
  ticker text primary key, series text, event_ticker text,
  result text, expiration_value text, close_utc text,
  last_price_c real, fetched_utc text);
create index if not exists ix_s on settled(series, close_utc);
create table if not exists fetch_log (
  series text, fetched_utc text, n_rows integer, http_ok integer, note text);
"""


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=120.0)
    c.execute("pragma journal_mode=WAL")
    c.executescript(SCHEMA)
    return c


def spec_series():
    """Every concrete Kalshi series named by a LIVE spec.

    Wildcard families (`*tier_a_economics`) are expanded from the tier list and
    the category census, so a spec that says "all economics families" is
    screened against the families we actually record rather than silently
    skipped.
    """
    import spec as SP
    tiers = json.loads((ROOT / "data" / "tiers.json").read_text(encoding="utf-8"))
    shape = json.loads((ROOT / "data" / "shape.json").read_text(encoding="utf-8"))
    per = shape["per_series"]
    tier_a = tiers["tier_a"]
    out, wild = set(), {}
    for _, s in SP.load_all():
        if "_parse_error" in s or s.get("status", "LIVE") != "LIVE":
            continue
        for f in s.get("families") or []:
            if not f.startswith("*"):
                out.add(f)
                continue
            key = f.lower()
            if "all_tier_a" in key:
                sel = list(tier_a)
            else:
                # match the category name embedded in the wildcard
                sel = []
                for ser in tier_a:
                    cat = (per.get(ser, {}).get("category") or "").lower()
                    if cat and cat.split()[0] in key:
                        sel.append(ser)
                if "no_maker_fee" in key and not sel:
                    sel = list(tier_a)
            wild[f] = len(sel)
            out.update(sel)
    return sorted(out), wild


#: WARNING - A CAP THAT IS NOT LOGGED IS A CAP THAT LIES.
#:
#: v1 used max_pages=8 and SIX families came back at exactly 8,000 rows -
#: KXBTC, KXBTCD, KXETHD, KXSOLD, KXSOLE and KXNASDAQ100U, the highest-volume
#: crypto and index ladders. Every one was truncated by MY OWN pagination, and
#: nothing said so: the fetch log recorded "8000 rows" as though that were the
#: answer rather than the ceiling. Walked properly, KXBTCD alone has 13,588.
#: The crypto screening sample was bounded by my code, not by the exchange.
#:
#: It was caught only because a stray background query printed a column of
#: suspiciously round numbers. That is luck, not process. So the ceiling is now
#: high AND `fetch` records when it is reached - a family that hits it is
#: reported as TRUNCATED, never silently accepted as complete.
MAX_PAGES = 200


def fetch(c, series, since_ts):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows, ok, note = [], 1, None
    try:
        for m in V.k_paginate("/markets",
                              {"series_ticker": series, "status": "settled",
                               "limit": 1000, "min_close_ts": since_ts},
                              "markets", max_pages=MAX_PAGES):
            tk = m.get("ticker")
            if not tk:
                continue
            rows.append((tk, V.series_of(tk), m.get("event_ticker"),
                         m.get("result"), str(m.get("expiration_value")),
                         m.get("close_time"),
                         (V.fnum(m.get("last_price_dollars")) or 0) * 100.0,
                         ts))
    except Exception as exc:                                   # noqa: BLE001
        ok, note = 0, str(exc)[:200]
    if len(rows) >= MAX_PAGES * 1000:
        note = ("HIT THE PAGE CEILING at %d rows - TRUNCATED, this count is a "
                "floor and not an answer" % len(rows))
        ok = 0
    if rows:
        c.executemany("insert or replace into settled values "
                      "(?,?,?,?,?,?,?,?)", rows)
    c.execute("insert into fetch_log values (?,?,?,?,?)",
              (series, ts, len(rows), ok, note))
    c.commit()
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="")
    ap.add_argument("--since", default="2026-08-17T00:00:00Z",
                    help="only markets closing after this")
    args = ap.parse_args()
    since_ts = int(time.mktime(time.strptime(args.since, "%Y-%m-%dT%H:%M:%SZ")))

    if args.series:
        sers = [s.strip() for s in args.series.split(",") if s.strip()]
        wild = {}
    else:
        sers, wild = spec_series()
    print("fetching settlements for %d series named by LIVE specs" % len(sers),
          flush=True)
    if wild:
        print("  wildcard families expanded: %s"
              % ", ".join("%s->%d" % (k, v) for k, v in sorted(wild.items())),
              flush=True)

    c = connect()
    tot = 0
    t0 = time.time()
    for i, s in enumerate(sers, 1):
        tot += fetch(c, s, since_ts)
        if i % 20 == 0:
            print("  %d/%d series, %d settled rows, %.0fs"
                  % (i, len(sers), tot, time.time() - t0), flush=True)
    n_yes = c.execute("select count(*) from settled where result='yes'").fetchone()[0]
    n_no = c.execute("select count(*) from settled where result='no'").fetchone()[0]
    n_other = c.execute("select count(*) from settled where result not in "
                        "('yes','no')").fetchone()[0]
    print("\nsettled rows on file: %d  (yes %d / no %d / other %d)"
          % (tot, n_yes, n_no, n_other))
    if n_other:
        print("  WARNING: %d rows have a result that is neither yes nor no. Those are "
              "NOT counted as either and are reported separately - a market "
              "that voided is not a market that lost." % n_other)
    c.close()


if __name__ == "__main__":
    main()
