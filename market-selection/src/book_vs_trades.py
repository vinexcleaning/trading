"""Validate the reconstructed book against an INDEPENDENT source: the trades.

Why this is needed. Treating `delta` as an absolute size gives 0% crossed
books, which looks like a clean answer -- but ~50% of the values are negative,
and under that reading a negative wipes the whole level. Aggressively emptying
the book keeps it uncrossed almost by construction. That is a way of hiding
the error, not fixing it.

The trade tape is independent of the book feed. A trade at price P at time T
must be consistent with the book at T: for a YES buy the ask should be at or
below P, and in practice most trades happen AT the touch.

So: reconstruct under each interpretation, and for every trade ask whether the
reconstructed touch is consistent. The interpretation that matches the trades
is the correct one. If NEITHER matches, the capture is lossy and the archive
cannot support continuous book work.
"""
import glob
import json
import os
import statistics as st
import sys
from bisect import bisect_right
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common"))
import bookreplay as BR  # noqa: E402

STAMP = "2026-06-01T12"
TAPE = os.path.join(os.path.dirname(__file__), "..", "data",
                    "tape_pmxt_window", "trades_2026-06-01.jsonl")
TICKERS = ["KXBTCD-26JUN0109-T72099.99", "KXCS2GAME-26JUN010700DCPHA-DC"]


def states(tab, mode):
    """[(ts, best_yes_bid, yes_ask)] after every message."""
    et = tab.column("event_type").to_pylist()
    tr = tab.column("timestamp_received").to_pylist()
    px = tab.column("price").to_pylist()
    dl = tab.column("delta").to_pylist()
    sd = tab.column("side").to_pylist()
    yb = tab.column("yes_bids").to_pylist()
    nb = tab.column("no_bids").to_pylist()
    yes, no = {}, {}
    started = False
    out = []
    for i in range(len(et)):
        if et[i] == "orderbook_snapshot":
            yes, no = {}, {}
            for p, s in BR.levels(yb[i]):
                if s > 0:
                    yes[round(p, 1)] = s
            for p, s in BR.levels(nb[i]):
                if s > 0:
                    no[round(p, 1)] = s
            started = True
        elif started and px[i] is not None and dl[i] is not None:
            p = round(float(px[i]) * 100.0, 1)
            book = yes if sd[i] == "yes" else no
            v = (book.get(p, 0.0) + float(dl[i])) if mode == "add" else float(dl[i])
            if v <= 0:
                book.pop(p, None)
            else:
                book[p] = v
        else:
            continue
        bb = max(yes) if yes else None
        nbid = max(no) if no else None
        out.append((tr[i], bb, (100.0 - nbid) if nbid is not None else None))
    return out


def main():
    print(f"loading book {STAMP} ...", flush=True)
    t = BR.load_hour(STAMP)
    print("loading trades ...", flush=True)
    tr_by = {tk: [] for tk in TICKERS}
    with open(TAPE, encoding="utf-8") as fh:
        for line in fh:
            hit = None
            for tk in TICKERS:
                if tk in line:
                    hit = tk
                    break
            if hit is None:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("ticker") != hit:
                continue
            try:
                ts = datetime.fromisoformat(
                    d["created_time"].replace("Z", "+00:00"))
                p = float(d["yes_price_dollars"]) * 100
            except (KeyError, ValueError, TypeError):
                continue
            tr_by[hit].append((ts, p, d.get("taker_outcome_side")))
    for tk in TICKERS:
        tr_by[tk].sort()
        print(f"  {tk[:44]:44s} {len(tr_by[tk]):>6,} trades in the day")

    for tk in TICKERS:
        tab = BR.for_ticker(t, tk)
        if tab.num_rows == 0:
            continue
        print(f"\n{'='*68}\n{tk}\n{'='*68}")
        # restrict trades to the hour the book file covers
        st_ = states(tab, "add")
        if not st_:
            print("  no states")
            continue
        t0, t1 = st_[0][0], st_[-1][0]
        trs = [x for x in tr_by[tk] if t0 <= x[0] <= t1]
        print(f"  book covers {t0:%H:%M:%S}..{t1:%H:%M:%S}, "
              f"{len(trs):,} trades inside it")
        if len(trs) < 30:
            print("  too few trades to validate")
            continue
        for mode in ("add", "set"):
            sq = states(tab, mode)
            times = [s[0] for s in sq]
            at_touch = inside = outside = nobook = 0
            gaps = []
            for ts, p, side in trs:
                j = bisect_right(times, ts) - 1
                if j < 0:
                    nobook += 1
                    continue
                _, bb, ask = sq[j]
                if bb is None or ask is None:
                    nobook += 1
                    continue
                if abs(p - bb) < 0.51 or abs(p - ask) < 0.51:
                    at_touch += 1
                elif bb - 0.51 <= p <= ask + 0.51:
                    inside += 1
                else:
                    outside += 1
                    gaps.append(min(abs(p - bb), abs(p - ask)))
            n = at_touch + inside + outside
            print(f"\n  mode={mode}: {n:,} trades matched to a two-sided book "
                  f"({nobook:,} had no book)")
            if n:
                print(f"    AT the touch      {at_touch:>7,} ({100*at_touch/n:5.1f}%)")
                print(f"    inside the spread {inside:>7,} ({100*inside/n:5.1f}%)")
                print(f"    OUTSIDE the book  {outside:>7,} ({100*outside/n:5.1f}%)"
                      + (f"   median miss {st.median(gaps):.1f}c" if gaps else ""))

    print(f"\n{'='*68}\nVERDICT\n{'='*68}")
    print("  A correct reconstruction puts most trades AT the touch and almost")
    print("  none outside the book. Whichever mode does that is right.")
    print("  If BOTH leave many trades outside, the capture is lossy and the")
    print("  archive cannot support continuous book reconstruction.")


if __name__ == "__main__":
    main()
