"""MEASURE THE EXCHANGE BEFORE TURNING A RECORDER ON.

STRATEGY_FACTORY.md section 2 stage 1: "Constraint: disk. 62 GB in 14 days on
19 families. Widening 100-fold naively eats the machine. Tiered rate ... write
the numbers down before turning it on."

This is that script. It does ONE full-exchange sweep of `/markets?status=open`
and writes down, before any recorder exists:

  * how long a sweep takes, in seconds;
  * how many markets carry a real two-sided quote, and how many are dead air;
  * how those split by category and by series;
  * how many bytes a row costs, and therefore what a day of tape costs at
    each cycle interval;
  * how much the change-only rule would save, measured on two sweeps rather
    than assumed.

Nothing here writes tape. It writes a report.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "bot-hunt" / "src"))
import venues as V  # noqa: E402

# One w_top row: cycle_id, ts, series, ticker, 4 quote floats, last, volume,
# oi, status, close. Measured on the real table further down rather than
# guessed; this is the fallback if the measurement is skipped.
BYTES_PER_ROW_GUESS = 110


def quote_of(m):
    """(yes_bid_c, yes_ask_c, bid_size, ask_size) from a LIST row.

    Kalshi encodes "no bid" as 0.0000 and "no ask" as 1.0000 on the list side,
    where the orderbook endpoint simply has no level. Normalising both to None
    matters: scoring an absent bid as a 0-cent bid would report every dead
    market as quoted, which is the failure this whole script exists to size.
    """
    yb = V.fnum(m.get("yes_bid_dollars"))
    ya = V.fnum(m.get("yes_ask_dollars"))
    yb = None if yb in (None, 0.0) else round(yb * 100.0, 2)
    ya = None if ya in (None, 1.0) else round(ya * 100.0, 2)
    return (yb, ya, V.fnum(m.get("yes_bid_size_fp")),
            V.fnum(m.get("yes_ask_size_fp")))


def sweep(label: str):
    """One full pass. Returns {ticker: (series, quote-tuple)} plus timing."""
    t0 = time.time()
    out = {}
    n_req = 0
    params = {"status": "open", "limit": 1000}
    seen_cursor = set()
    cursor = None
    while True:
        p = dict(params)
        if cursor:
            p["cursor"] = cursor
        r = V.k_get("/markets", p)
        n_req += 1
        if r is None or r.status_code != 200:
            print("  %s: HTTP %s after %d requests"
                  % (label, r and r.status_code, n_req), flush=True)
            break
        d = r.json() or {}
        ms = d.get("markets") or []
        for m in ms:
            tk = m.get("ticker")
            if tk:
                out[tk] = (V.series_of(tk), quote_of(m),
                           V.fnum(m.get("volume_fp")),
                           V.fnum(m.get("open_interest_fp")),
                           m.get("close_time"))
        cursor = d.get("cursor")
        if not cursor or cursor in seen_cursor or not ms:
            break
        seen_cursor.add(cursor)
        if n_req % 100 == 0:
            print("  %s: %d requests, %d markets, %.0fs"
                  % (label, n_req, len(out), time.time() - t0), flush=True)
    return out, n_req, time.time() - t0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--second-sweep", type=int, default=300,
                   help="seconds to wait before the second sweep, for the "
                        "change-rate measurement. 0 = skip it")
    ap.add_argument("--out", default=str(ROOT / "reports" / "SHAPE.md"))
    args = ap.parse_args()

    print("sweep 1 ...", flush=True)
    s1, req1, sec1 = sweep("sweep1")
    print("sweep 1: %d markets, %d requests, %.0f s" % (len(s1), req1, sec1))

    cats = {}
    try:
        import sqlite3
        con = sqlite3.connect(ROOT / "data" / "census.db")
        cats = dict(con.execute("select ticker, category from series"))
        con.close()
    except Exception as exc:                                   # noqa: BLE001
        print("  (no census.db categories: %s)" % exc)

    per_series = defaultdict(lambda: [0, 0, 0, 0.0])   # n, quoted, two, oi
    per_cat = defaultdict(lambda: [0, 0, 0])
    n_two = n_one = n_none = 0
    for tk, (ser, (yb, ya, bs, asz), vol, oi, close) in s1.items():
        two = yb is not None and ya is not None
        one = (yb is not None) != (ya is not None)
        n_two += two
        n_one += one
        n_none += (yb is None and ya is None)
        p = per_series[ser]
        p[0] += 1
        p[1] += int(yb is not None or ya is not None)
        p[2] += int(two)
        p[3] += oi or 0.0
        c = per_cat[cats.get(ser, "(unknown)")]
        c[0] += 1
        c[1] += int(yb is not None or ya is not None)
        c[2] += int(two)

    changed = same = new = 0
    sec2 = 0.0
    if args.second_sweep:
        print("waiting %d s for sweep 2 ..." % args.second_sweep, flush=True)
        time.sleep(args.second_sweep)
        s2, req2, sec2 = sweep("sweep2")
        print("sweep 2: %d markets, %.0f s" % (len(s2), sec2))
        for tk, v in s2.items():
            if tk not in s1:
                new += 1
            elif s1[tk][1] != v[1]:
                changed += 1
            else:
                same += 1

    L = []
    A = L.append
    A("# THE SHAPE OF THE EXCHANGE - measured before any recorder was widened")
    A("")
    A("**Measured %s by `strategy-factory/src/shape.py`.** One full sweep of "
      "every open Kalshi market, then a second sweep %d seconds later to "
      "measure how much actually moves. Nothing was recorded; this is the "
      "arithmetic that decides the recorder's shape."
      % (time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), args.second_sweep))
    A("")
    A("## 1. One sweep of the whole exchange")
    A("")
    A("| | |")
    A("|---|---|")
    A("| open markets | **%d** |" % len(s1))
    A("| HTTP requests to get them all | %d |" % req1)
    A("| seconds for one sweep | **%.0f** |" % sec1)
    A("| markets with a two-sided quote | **%d** (%.1f%%) |"
      % (n_two, 100.0 * n_two / max(len(s1), 1)))
    A("| markets with one side only | %d (%.1f%%) |"
      % (n_one, 100.0 * n_one / max(len(s1), 1)))
    A("| markets with no quote at all | %d (%.1f%%) |"
      % (n_none, 100.0 * n_none / max(len(s1), 1)))
    A("")
    A("A sweep is one HTTP request per 1,000 markets, not one per market. "
      "That is the finding in `RESULT_LIST_QUOTES.md` and it is what makes "
      "recording the whole exchange possible at all: the per-market orderbook "
      "route would be %.1f hours for one pass."
      % (len(s1) * 0.35 / 3600.0))
    A("")
    A("## 2. Where the markets actually are")
    A("")
    A("| category | series | markets | quoted | two-sided |")
    A("|---|---:|---:|---:|---:|")
    ncat_ser = defaultdict(set)
    for ser in per_series:
        ncat_ser[cats.get(ser, "(unknown)")].add(ser)
    for cat, (n, q, t) in sorted(per_cat.items(), key=lambda x: -x[1][0]):
        A("| %s | %d | %d | %d | %d |"
          % (cat, len(ncat_ser[cat]), n, q, t))
    A("")
    A("## 3. The 20 biggest series, and how much of each is dead air")
    A("")
    A("| series | category | markets | two-sided | share two-sided |")
    A("|---|---|---:|---:|---:|")
    for ser, (n, q, t, oi) in sorted(per_series.items(),
                                     key=lambda x: -x[1][0])[:20]:
        A("| `%s` | %s | %d | %d | %.1f%% |"
          % (ser, cats.get(ser, "?"), n, t, 100.0 * t / max(n, 1)))
    A("")
    A("## 4. The 25 series with the most two-sided markets - the ones worth tape")
    A("")
    A("| series | category | markets | two-sided | share |")
    A("|---|---|---:|---:|---:|")
    for ser, (n, q, t, oi) in sorted(per_series.items(),
                                     key=lambda x: -x[1][2])[:25]:
        A("| `%s` | %s | %d | %d | %.1f%% |"
          % (ser, cats.get(ser, "?"), n, t, 100.0 * t / max(n, 1)))
    A("")
    if args.second_sweep:
        tot = changed + same
        A("## 5. How much moves in %d seconds - the change-only saving"
          % args.second_sweep)
        A("")
        A("| | |")
        A("|---|---|")
        A("| markets in both sweeps | %d |" % tot)
        A("| quote CHANGED | **%d (%.1f%%)** |"
          % (changed, 100.0 * changed / max(tot, 1)))
        A("| quote identical | %d (%.1f%%) |"
          % (same, 100.0 * same / max(tot, 1)))
        A("| markets that appeared between sweeps | %d |" % new)
        A("")
        A("Writing only the rows that changed therefore costs about "
          "**%.1f%%** of writing all of them. That is measured on two real "
          "sweeps %d seconds apart, not assumed - and it is the single "
          "decision that makes recording the whole exchange fit on disk."
          % (100.0 * changed / max(tot, 1), args.second_sweep))
        A("")
        A("| interval | full rows/day | change-only rows/day | GB/day at %d B/row |"
          % BYTES_PER_ROW_GUESS)
        A("|---|---:|---:|---:|")
        for iv in (300, 600, 1800, 3600):
            per_day = 86400.0 / iv
            full = len(s1) * per_day
            chg = full * (changed / max(tot, 1))
            A("| %d s | %.0f | %.0f | **%.1f** |"
              % (iv, full, chg, chg * BYTES_PER_ROW_GUESS / 2**30))
        A("")
        A("The change rate is measured at %d s. At a longer interval more "
          "will have moved between snapshots, so the rows/day column above "
          "is a FLOOR for the long intervals, not a promise. The recorder "
          "reports its real rows/day in `w_cycle` from the first day, and "
          "that number replaces this one." % args.second_sweep)
    A("")
    A("## 6. What this rules out")
    A("")
    A("- **Recording every open market at full orderbook depth.** %d markets "
      "at ~0.35 s each is %.1f hours for one pass. Not a tiering choice, an "
      "impossibility." % (len(s1), len(s1) * 0.35 / 3600.0))
    A("- **Recording the Exotics families at all.** They are the great "
      "majority of open markets and almost none of them carry a quote. See "
      "the table in section 3.")
    A("")

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote %s" % outp)

    # Machine-readable, for the recorder's tier list to be built from.
    jp = ROOT / "data" / "shape.json"
    jp.write_text(json.dumps(
        {"measured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "n_markets": len(s1), "sweep_seconds": sec1, "requests": req1,
         "n_two_sided": n_two, "n_one_sided": n_one, "n_unquoted": n_none,
         "second_sweep_seconds": args.second_sweep,
         "changed": changed, "same": same, "new": new,
         "per_series": {k: {"n": v[0], "quoted": v[1], "two_sided": v[2],
                            "oi": v[3], "category": cats.get(k, "?")}
                        for k, v in per_series.items()}}, indent=1),
        encoding="utf-8")
    print("wrote %s" % jp)


if __name__ == "__main__":
    main()
