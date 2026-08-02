"""TASK 1 — hold-to-settlement across assets.

The last untested item with a real prior. On BTC, holding to settlement beat
every exit rule at every entry price, and the 5c bucket was the only cell with a
CI excluding zero (+2.94c, n=237, the noisiest bucket). One bucket, one asset.

MECHANISM UNDER TEST: if cheap contracts are systematically underpriced that is
favourite-longshot bias — longshots overpriced, so their complements are cheap.
It should appear on EVERY asset if real.

THE TRAP: thin assets have wide spreads, so buying at a wide ask into settlement
should be WORSE, not better. Any asset that looks good gets its two-sided uptime
and spread checked before the result is believed.

EFFECTIVE N: the four crypto assets are 1.81 effective independent series, not
4. Every cross-asset statement below carries that.

Entry at the REAL ask, ONE taker fee (settlement costs nothing), payoff = the
realised outcome. CIs bootstrap EVENTS.
"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from fees import kalshi_fee_per_contract_unrounded  # noqa: E402

PANEL = r"C:\Users\gianf\crypto\data\panel"
OUT = r"C:\Users\gianf\crypto\reports"
BUCKETS = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80,
           0.90]
BAND = 0.025
EFFECTIVE_N = 1.81


def boot(by_event, n_boot=2000, seed=17):
    keys = list(by_event)
    if len(keys) < 5:
        return None
    per = np.array([np.mean(by_event[k]) for k in keys])
    rng = np.random.default_rng(seed)
    n = len(per)
    bs = np.array([per[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return float(per.mean()), float(lo), float(hi), n


def load(series):
    p = os.path.join(PANEL, f"panel_{series}.jsonl")
    if not os.path.exists(p):
        return None
    rows = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main():
    series_list = [("BTC", "KXBTCD"), ("ETH", "KXETHD"),
                   ("SOL", "KXSOLD"), ("XRP", "KXXRPD")]
    results = {}
    quality = {}

    for name, s in series_list:
        rows = load(s)
        if not rows:
            print(f"{name} ({s}): panel not built yet — SKIPPED")
            continue
        evs = {r["event"] for r in rows}
        ts = [r["ts"] for r in rows]
        import datetime as dt
        print("=" * 100)
        print(f"{name} ({s}) — SAMPLE COMPOSITION")
        print("=" * 100)
        print(f"  selection: events on a fixed stride through all settled "
              f"events sorted by close_time; within each event the strikes "
              f"nearest the ANCHOR (previous settlement, knowable pre-open)")
        print(f"  rows={len(rows)}  events={len(evs)}  "
              f"markets={len({r['ticker'] for r in rows})}")
        print(f"  {dt.datetime.utcfromtimestamp(min(ts))} -> "
              f"{dt.datetime.utcfromtimestamp(max(ts))}")
        sp = np.array([r["spread"] for r in rows])
        print(f"  spread: median {np.median(sp)*100:.2f}c  "
              f"p75 {np.percentile(sp,75)*100:.2f}c  "
              f"p90 {np.percentile(sp,90)*100:.2f}c  "
              f"frac > 1c: {100*np.mean(sp > 0.0101):.1f}%")
        quality[name] = {"med_spread_c": float(np.median(sp) * 100),
                         "p90_spread_c": float(np.percentile(sp, 90) * 100),
                         "frac_gt_1c": float(np.mean(sp > 0.0101)),
                         "rows": len(rows), "events": len(evs)}

        per_bucket = {}
        print(f"\n  {'entry':>6} {'n_opp':>7} {'n_ev':>5} {'med ask':>8} "
              f"{'NET c/ct':>10} {'95% CI (event)':>20} {'verdict':>10}")
        for E in BUCKETS:
            by_ev = defaultdict(list)
            asks = []
            for r in rows:
                if abs(r["ask"] - E) > BAND:
                    continue
                a = r["ask"]
                pnl = r["y"] - a - float(
                    kalshi_fee_per_contract_unrounded(a))
                by_ev[r["event"]].append(pnl)
                asks.append(a)
            if len(asks) < 200:
                continue
            b = boot(by_ev)
            if b is None:
                continue
            m, lo, hi, nev = b
            vd = ("POSITIVE" if lo > 0 else
                  ("negative" if hi < 0 else "tie"))
            print(f"  {E*100:>5.0f}c {len(asks):>7} {nev:>5} "
                  f"{np.median(asks)*100:>7.2f}c {m*100:>+10.3f} "
                  f"[{lo*100:>+7.2f},{hi*100:>+7.2f}] {vd:>10}")
            per_bucket[E] = {"n": len(asks), "n_ev": nev, "net_c": m * 100,
                             "lo_c": lo * 100, "hi_c": hi * 100,
                             "verdict": vd}
        results[name] = per_bucket
        print()

    # ------------------------------------------------ comparison table
    print("=" * 100)
    print("FOUR-ASSET HOLD-TO-SETTLEMENT — the deliverable")
    print("=" * 100)
    print(f"  NOMINAL assets: {len(results)}   "
          f"EFFECTIVE independent series: {EFFECTIVE_N} (of 4)")
    print(f"  Four assets agreeing is ~1.8 observations, not 4.\n")
    hdr = f"  {'entry':>6}"
    for k in results:
        hdr += f" {k:>22}"
    print(hdr)
    for E in BUCKETS:
        line = f"  {E*100:>5.0f}c"
        any_row = False
        for k in results:
            c = results[k].get(E)
            if c:
                any_row = True
                star = "*" if c["verdict"] == "POSITIVE" else " "
                line += f" {c['net_c']:>+8.2f}[{c['lo_c']:>+5.1f},{c['hi_c']:>+5.1f}]{star}"
            else:
                line += f" {'--':>22}"
        if any_row:
            print(line)
    print("\n  * = CI excludes zero (positive)")

    # cheap-bucket replication check
    print("\n" + "=" * 100)
    print("DOES THE CHEAP-CONTRACT EFFECT (5-15c) REPLICATE?")
    print("=" * 100)
    for E in (0.05, 0.10, 0.15):
        cells = {k: results[k].get(E) for k in results if results[k].get(E)}
        if not cells:
            continue
        pos = [k for k, c in cells.items() if c["verdict"] == "POSITIVE"]
        signs = {k: ("+" if c["net_c"] > 0 else "-") for k, c in cells.items()}
        print(f"  {E*100:.0f}c bucket: {len(cells)} assets tested, "
              f"{len(pos)} with CI excluding zero {pos}")
        print(f"    signs: {signs}")
        if len(cells) > 1:
            eff = EFFECTIVE_N * len(cells) / 4.0
            print(f"    effective independent observations here: ~{eff:.1f}")

    json.dump({"results": {k: {str(e): v for e, v in d.items()}
                           for k, d in results.items()},
               "quality": quality, "effective_n": EFFECTIVE_N},
              open(os.path.join(OUT, "hold_to_settlement.json"), "w"),
              indent=2, default=str)


if __name__ == "__main__":
    main()
