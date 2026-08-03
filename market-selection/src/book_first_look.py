"""First look at the order-book archive: prove the replay works, then survey.

Three things, in order:
  1. reconstruct ONE market and show the actual ladder -- if the machinery is
     wrong, everything after it is worthless
  2. validate the reconstruction: crossed books, bad levels, snapshot count
  3. survey one hour: which markets have real two-sided depth, and how does
     the book behave between trades
"""
import os
import statistics as st
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common"))
import bookreplay as BR  # noqa: E402

STAMP = "2026-06-01T12"


def main():
    print(f"loading {STAMP} ...", flush=True)
    t = BR.load_hour(STAMP)
    print(f"  {t.num_rows:,} rows")
    tick = t.column("market_ticker").to_pylist()
    et = t.column("event_type").to_pylist()
    cnt = Counter(tick)
    snaps = Counter(tick[i] for i in range(len(tick))
                    if et[i] == "orderbook_snapshot")
    print(f"  {len(cnt):,} distinct tickers")

    # markets with a snapshot (replayable) and lots of traffic
    cand = [(n, tk) for tk, n in cnt.items() if snaps.get(tk, 0) >= 1]
    cand.sort(reverse=True)
    print(f"  {len(cand):,} tickers have >=1 snapshot (replayable)")
    print("\n  busiest replayable markets this hour:")
    for n, tk in cand[:10]:
        print(f"    {tk[:50]:50s} {n:>8,} msgs  {snaps[tk]:>3} snapshots")

    # ---------- 1. reconstruct one market
    target = cand[0][1]
    print(f"\n{'='*70}\n1. REPLAY: {target}\n{'='*70}")
    states = list(BR.replay(t, target))
    print(f"  {len(states):,} book states reconstructed")
    if not states:
        print("  NOTHING REPLAYED -- the machinery is broken, stop here")
        return
    _, b = states[-1]
    print(f"  final book: {b.n_snap} snapshots + {b.n_delta:,} deltas applied")
    ok, why = b.is_valid()
    print(f"  validity: {ok} ({why})")
    yb, ya = b.touch()
    print(f"\n  TOUCH: yes_bid {yb}c   yes_ask {ya}c   spread {b.spread()}c")
    print(f"  levels: {len(b.yes)} on the YES ladder, {len(b.no)} on the NO ladder")
    print("\n  top of the YES bid ladder (buy YES here):")
    for p in sorted(b.yes, reverse=True)[:6]:
        print(f"    {p:6.1f}c  x {b.yes[p]:>10,.0f}")
    print("  top of the NO bid ladder (buy NO here; YES ask = 100 - price):")
    for p in sorted(b.no, reverse=True)[:6]:
        print(f"    {p:6.1f}c  x {b.no[p]:>10,.0f}   (= YES ask {100-p:.1f}c)")

    # ---------- 2. validate across many markets
    print(f"\n{'='*70}\n2. VALIDATION across the busiest 40 replayable markets\n{'='*70}")
    bad = Counter()
    stats = []
    for n, tk in cand[:40]:
        last = None
        crossed = 0
        checked = 0
        for _, bk in BR.replay(t, tk):
            last = bk
            checked += 1
            if checked % 200 == 0:
                v, w = bk.is_valid()
                if not v:
                    bad[w.split(":")[0]] += 1
                    if "crossed" in w:
                        crossed += 1
        if last is None:
            continue
        v, w = last.is_valid()
        if not v:
            bad[w.split(":")[0]] += 1
        yb, ya = last.touch()
        stats.append({"ticker": tk, "msgs": n, "levels_yes": len(last.yes),
                      "levels_no": len(last.no), "bid": yb, "ask": ya,
                      "spread": last.spread(),
                      "depth5": last.depth_within(5)})
    print(f"  validated {len(stats)} markets; problems: {dict(bad) or 'NONE'}")
    two = [s for s in stats if s["spread"] is not None]
    print(f"  two-sided at the end of the hour: {len(two)} of {len(stats)}")
    if two:
        sp = sorted(s["spread"] for s in two)
        dp = sorted(s["depth5"] for s in two)
        print(f"  spread : median {sp[len(sp)//2]:.1f}c  "
              f"p90 {sp[int(len(sp)*.9)]:.1f}c")
        print(f"  depth within 5c: median {dp[len(dp)//2]:,.0f}  "
              f"max {dp[-1]:,.0f} contracts")

    print(f"\n  {'ticker':46s} {'msgs':>8s} {'lv':>5s} {'bid':>6s} {'ask':>6s} "
          f"{'spr':>5s} {'depth5c':>10s}")
    for s in stats[:18]:
        print(f"  {s['ticker'][:46]:46s} {s['msgs']:>8,} "
              f"{s['levels_yes']+s['levels_no']:>5d} "
              f"{str(s['bid']):>6s} {str(s['ask']):>6s} "
              f"{str(s['spread']):>5s} {s['depth5']:>10,.0f}")

    # ---------- 3. what the book does that trades cannot show
    print(f"\n{'='*70}\n3. WHAT ONLY THE BOOK SHOWS\n{'='*70}")
    tk = target
    seq = []
    for ts, bk in BR.replay(t, tk):
        b_, a_ = bk.touch()
        if b_ is not None and a_ is not None:
            seq.append((ts, b_, a_, bk.depth_within(0)))
    print(f"  {tk}")
    print(f"  two-sided states: {len(seq):,} of {len(states):,}")
    if len(seq) > 10:
        moves = sum(1 for i in range(1, len(seq))
                    if seq[i][1] != seq[i - 1][1] or seq[i][2] != seq[i - 1][2])
        span = (seq[-1][0] - seq[0][0]).total_seconds()
        print(f"  touch CHANGED {moves:,} times in {span/60:.1f} minutes "
              f"= one quote change every {span/max(moves,1):.2f}s")
        sp = [a - b for _, b, a, _ in seq]
        print(f"  spread over the hour: median {st.median(sp):.1f}c  "
              f"min {min(sp):.1f}  max {max(sp):.1f}")
        d0 = [d for *_, d in seq]
        print(f"  size AT the touch: median {st.median(d0):,.0f}  "
              f"min {min(d0):,.0f}  max {max(d0):,.0f}")
        print("\n  This is the thing trades cannot tell you: the quote moves")
        print("  constantly whether or not anyone trades, and the size at the")
        print("  touch swings by orders of magnitude within the hour.")


if __name__ == "__main__":
    main()
