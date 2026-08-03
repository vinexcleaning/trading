"""Is `delta` a CHANGE in resting size, or the NEW ABSOLUTE size?

The replay produced a crossed book (yes_bid 99c against a yes_ask of 22c),
which cannot exist -- you could sell both sides and collect 177c to pay out
100c. So one of my assumptions is wrong, and the obvious candidate is the
meaning of `delta`.

Kalshi's documentation says it is a change. Documentation has been wrong twice
in this project, so this decides it by replaying the SAME market under both
interpretations and asking which one produces a book that is never crossed.

A third possibility is also tested: that the capture drops messages, in which
case NEITHER interpretation stays valid and the archive can only be trusted
close to a snapshot.
"""
import os
import sys
from collections import Counter, defaultdict

import pyarrow.compute as pc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common"))
import bookreplay as BR  # noqa: E402

STAMP = "2026-06-01T12"
TICKERS = ["KXBTCD-26JUN0109-T72099.99",
           "KXITFWMATCH-26JUN01KOVRIC-RIC",
           "KXCS2GAME-26JUN010700DCPHA-DC"]


def run(tab, mode):
    """mode 'add' -> book[p] += delta ; mode 'set' -> book[p] = delta"""
    et = tab.column("event_type").to_pylist()
    tr = tab.column("timestamp_received").to_pylist()
    px = tab.column("price").to_pylist()
    dl = tab.column("delta").to_pylist()
    sd = tab.column("side").to_pylist()
    yb = tab.column("yes_bids").to_pylist()
    nb = tab.column("no_bids").to_pylist()
    yes, no = {}, {}
    started = False
    crossed = 0
    checked = 0
    neg = 0
    first_cross_at = None
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
            if mode == "add":
                v = book.get(p, 0.0) + float(dl[i])
            else:
                v = float(dl[i])
            if v <= 0:
                book.pop(p, None)
                if v < 0:
                    neg += 1
            else:
                book[p] = v
        else:
            continue
        if not started or not yes or not no:
            continue
        checked += 1
        bb, nbid = max(yes), max(no)
        if bb + nbid > 100.0:           # crossed / arbitrageable
            crossed += 1
            if first_cross_at is None:
                first_cross_at = i
    return {"checked": checked, "crossed": crossed,
            "pct_crossed": 100.0 * crossed / max(checked, 1),
            "neg_sizes": neg, "first_cross_row": first_cross_at,
            "n_levels": len(yes) + len(no)}


def main():
    print(f"loading {STAMP} ...", flush=True)
    t = BR.load_hour(STAMP)
    print(f"  {t.num_rows:,} rows\n")
    for tk in TICKERS:
        tab = BR.for_ticker(t, tk)
        if tab.num_rows == 0:
            print(f"{tk}: not present")
            continue
        et = Counter(tab.column("event_type").to_pylist())
        print(f"{tk}")
        print(f"  {tab.num_rows:,} msgs  {dict(et)}")
        for mode in ("add", "set"):
            r = run(tab, mode)
            print(f"    mode={mode:4s} crossed {r['crossed']:>7,} of "
                  f"{r['checked']:>7,} states ({r['pct_crossed']:5.1f}%)  "
                  f"neg-size events {r['neg_sizes']:>6,}  "
                  f"first cross at row {r['first_cross_row']}")
        print()

    print("=" * 68)
    print("INTERPRETATION")
    print("=" * 68)
    print("  The mode with ~0% crossed states is the correct semantics.")
    print("  If BOTH cross heavily, the capture is dropping messages and the")
    print("  book can only be trusted for a short window after each snapshot")
    print("  -- which would make this archive far less useful than hoped, and")
    print("  that is a finding worth reporting rather than working around.")


if __name__ == "__main__":
    main()
