"""One-shot depth probe across the top N families by trades/day.

The continuous recorder covers 85 families. The tape shows ~1,800 series
trading. Without this, every family outside the recorder's 85 would be killed
by OMISSION rather than by measurement -- which is not a kill, it is a gap, and
writing it up as a kill would be dishonest.

This is a SNAPSHOT, not a time series. It can establish "this family has no
two-sided quote at all right now", which is enough to kill on dimension A when
combined with a low trade count. It CANNOT establish two-sided *uptime*, so a
family that passes here is marked measured-once, not confirmed.

Read-only, paced, public.
"""
import json
import os
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import kalshi_api as K  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
TOP_N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
PER_SERIES = 3


def main():
    counts = Counter()
    with open(os.path.join(DATA, "kalshi_trades_24h.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                tk = json.loads(line).get("ticker")
            except json.JSONDecodeError:
                continue
            if tk:
                counts[K.series_of(tk)] += 1
    print(f"tape: {sum(counts.values()):,} trades, {len(counts)} series")

    by_series = defaultdict(list)
    with open(os.path.join(DATA, "kalshi_markets_open.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            m = json.loads(line)
            by_series[K.series_of(m["ticker"])].append(
                (K.f(m.get("volume_24h_fp")) or 0.0, m["ticker"]))

    targets = [s for s, _ in counts.most_common(TOP_N)]
    print(f"probing top {len(targets)} series x up to {PER_SERIES} markets\n")
    out = []
    t0 = time.time()
    for i, s in enumerate(targets):
        ms = by_series.get(s)
        if not ms:
            out.append({"series": s, "trades_in_tape": counts[s],
                        "status": "no_open_markets"})
            continue
        rec = {"series": s, "trades_in_tape": counts[s], "sampled": 0,
               "two_sided": 0, "any_depth": 0, "spreads": [], "bid_sz": [],
               "levels": []}
        for _v, tk in sorted(ms, reverse=True)[:PER_SERIES]:
            yes, no = K.orderbook(tk)
            if yes is None and no is None:
                continue
            yes, no = yes or [], no or []
            rec["sampled"] += 1
            if yes or no:
                rec["any_depth"] += 1
            rec["levels"].append(len(yes) + len(no))
            yb, ya, bs, _a = K.touch(yes, no)
            if yb is not None and ya is not None:
                rec["two_sided"] += 1
                rec["spreads"].append(round(ya - yb, 2))
                if bs is not None:
                    rec["bid_sz"].append(bs)
        n = rec["sampled"] or 1
        rec["pct_two_sided_snapshot"] = round(100 * rec["two_sided"] / n, 1)
        rec["spread_med_c"] = (round(sorted(rec["spreads"])[len(rec["spreads"]) // 2], 2)
                               if rec["spreads"] else None)
        rec["bid_sz_med"] = (round(sorted(rec["bid_sz"])[len(rec["bid_sz"]) // 2], 1)
                             if rec["bid_sz"] else None)
        rec["status"] = "ok"
        out.append(rec)
        if (i + 1) % 40 == 0:
            print(f"  {i+1}/{len(targets)}  {time.time()-t0:.0f}s", flush=True)

    with open(os.path.join(REP, "depth_sweep_wide.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    ok = [r for r in out if r.get("status") == "ok" and r["sampled"]]
    dead = [r for r in ok if r["two_sided"] == 0]
    print(f"\nprobed {len(ok)} series with open markets")
    print(f"series with NO two-sided quote on any sampled market: "
          f"{len(dead)} ({100*len(dead)/max(len(ok),1):.0f}%)")
    print(f"\nbusiest families with NO two-sided quote (kill candidates):")
    print(f"{'series':30s} {'trades':>8s} {'sampled':>7s} {'anydepth':>8s}")
    for r in sorted(dead, key=lambda r: -r["trades_in_tape"])[:25]:
        print(f"{r['series'][:30]:30s} {r['trades_in_tape']:8d} "
              f"{r['sampled']:7d} {r['any_depth']:8d}")
    print(f"\nwrote reports/depth_sweep_wide.json  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
