"""Is the Kalshi mid's calibration gap real and tradeable?

The reliability table shows the empirical rate EXCEEDING the mid in the 5-65%
range by up to +4.2pp. Taken at face value that is a large edge: buy YES at the
ask whenever the mid sits in that band.

Three reasons to distrust it before testing, all stated up front:

  1. The reliability table has NO event clustering. Consecutive minutes of the
     same market are almost the same observation; 2,562 "rows" in a bucket may
     be a few hundred events. This is failure mode #3.
  2. If the mid really underpriced a whole band by 4pp, M1/M2 -- which are
     roughly calibrated -- should have detected it and beaten the mid. They did
     not. That is evidence against the gap being real at the event level.
  3. The SAME statistic had the OPPOSITE SIGN on the 13-event dry run
     (empirical BELOW the mid in low buckets, i.e. longshots overpriced). A
     statistic that flips sign as n grows is behaving like noise.

So: test it with the bootstrap clustered BY EVENT, and apply the cost test --
you buy at the ASK, not the mid, and you pay the fee.
"""
import datetime as dt
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from models import cluster_bootstrap_diff  # noqa: E402
from fees import kalshi_fee_per_contract_unrounded  # noqa: E402

PANEL = r"C:\Users\gianf\crypto\data\panel\panel_KXBTCD.jsonl"


def boot_gap(y, p, events, n_boot=4000, seed=11):
    """Mean(y) - mean(p) with a CI clustered by EVENT."""
    uniq = np.unique(events)
    idx = {e: np.flatnonzero(events == e) for e in uniq}
    per_ev = np.array([y[idx[e]].mean() - p[idx[e]].mean() for e in uniq])
    rng = np.random.default_rng(seed)
    n = len(uniq)
    boots = np.array([per_ev[rng.integers(0, n, n)].mean()
                      for _ in range(n_boot)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    pv = 2.0 * min(float(np.mean(boots >= 0)), float(np.mean(boots <= 0)))
    return float(per_ev.mean()), float(lo), float(hi), min(1.0, pv), n


def main():
    rows = []
    with open(PANEL, encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    y = np.array([r["y"] for r in rows])
    mid = np.array([r["mid"] for r in rows])
    ask = np.array([r["ask"] for r in rows])
    ev = np.array([r["event"] for r in rows])
    ts = np.array([r["ts"] for r in rows])

    print("=" * 104)
    print("IS THE MID'S CALIBRATION GAP REAL? (event-clustered) AND TRADEABLE?")
    print("=" * 104)
    print(f"  n rows = {len(rows)}, n events = {len(set(ev))}")
    print(f"\n  {'mid bucket':>12} {'rows':>7} {'events':>7} {'raw gap':>9} "
          f"{'event-clustered 95% CI':>26} {'p':>8} | "
          f"{'buy@ask EV':>11} {'fee':>7} {'NET':>9} {'verdict':>9}")

    edges = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50,
             0.55, 0.60, 0.65, 0.70, 0.80, 0.90, 1.0]
    out = []
    for lo, hi in zip(edges, edges[1:]):
        m = (mid >= lo) & (mid < hi)
        if m.sum() < 200:
            continue
        g, cl, ch, pv, nev = boot_gap(y[m], mid[m], ev[m])
        # cost test: you BUY AT THE ASK and pay the fee at that price
        ev_gross = float(y[m].mean() - ask[m].mean())
        fee = float(np.mean([
            float(kalshi_fee_per_contract_unrounded(min(max(x, 0.001), 0.999)))
            for x in ask[m]]))
        net = ev_gross - fee
        sig = "REAL" if (cl > 0 or ch < 0) else "noise"
        verdict = "TRADEABLE" if (net > 0 and cl > 0) else "no"
        print(f"  {lo:.2f}-{hi:.2f} {m.sum():>7} {nev:>7} {g:>+9.4f} "
              f"[{cl:>+9.4f},{ch:>+9.4f}] {pv:>8.4f} | "
              f"{ev_gross:>+11.4f} {fee:>7.4f} {net:>+9.4f} "
              f"{sig:>5}/{verdict}")
        out.append({"lo": lo, "hi": hi, "rows": int(m.sum()), "events": nev,
                    "gap": g, "ci_lo": cl, "ci_hi": ch, "p": pv,
                    "ev_at_ask": ev_gross, "fee": fee, "net": net})

    # ---- the sign-flip check: does the gap hold in BOTH halves? ----------
    print("\n  STABILITY — same statistic on two disjoint halves")
    cut = np.median(ts)
    print(f"  {'mid bucket':>12} {'1st half gap':>28} {'2nd half gap':>28} "
          f"{'signs agree?':>13}")
    for lo, hi in zip(edges, edges[1:]):
        m = (mid >= lo) & (mid < hi)
        if m.sum() < 400:
            continue
        res = []
        for msk in (m & (ts < cut), m & (ts >= cut)):
            if msk.sum() < 100 or len(set(ev[msk])) < 10:
                res.append(None)
                continue
            res.append(boot_gap(y[msk], mid[msk], ev[msk], n_boot=2000))
        if None in res:
            continue
        a, b = res
        agree = "yes" if np.sign(a[0]) == np.sign(b[0]) else "NO"
        print(f"  {lo:.2f}-{hi:.2f} {a[0]:>+10.4f}[{a[1]:+.4f},{a[2]:+.4f}] "
              f"{b[0]:>+10.4f}[{b[1]:+.4f},{b[2]:+.4f}] {agree:>13}")

    json.dump(out, open(r"C:\Users\gianf\crypto\reports\mid_calibration.json",
                        "w"), indent=2)


if __name__ == "__main__":
    main()
