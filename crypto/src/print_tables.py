"""(a) fade table with BOTH bars side by side, (b) speed-conditional touch.

(a) is re-formatting of numbers already computed; the 54.74% bar is arithmetic
    on the measured no_ask=0.53 open price.
(b) IS new: P(touch a higher target) conditioned on whether the move to an
    intermediate level was FAST or SLOW. Never computed before.
"""
import json
import os
import sys
from collections import defaultdict

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
from fees import kalshi_fee_per_contract_unrounded  # noqa: E402

PANEL = r"C:\Users\gianf\crypto\data\panel\panel_KXBTCD.jsonl"
S15 = r"C:\Users\gianf\crypto\data\kalshi_settled\KXBTC15M.jsonl"

BAR50 = 0.5175
ENTRY_REAL = 0.53
BAR_REAL = ENTRY_REAL + float(kalshi_fee_per_contract_unrounded(ENTRY_REAL))


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


# ------------------------------------------------------------- fade table
def fade():
    ev = {}
    with open(S15, encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            e, ct, res = (m.get("event_ticker"), m.get("close_time"),
                          str(m.get("result")))
            if e and ct and res in ("yes", "no"):
                ev[e] = (ct, 1 if res == "yes" else 0)
    ups = np.array([v[1] for v in sorted(ev.values())])
    n = len(ups)

    conds = {}
    for N in (3, 5, 10, 20):
        for k in range(N + 1):
            idx = np.array([i for i in range(N, n) if ups[i - N:i].sum() == k])
            if len(idx) >= 100:
                conds[f"{k}/{N} ups"] = idx
    for k in range(2, 9):
        for d, lab in ((1, "ups"), (0, "downs")):
            idx = np.array([i for i in range(k, n)
                            if all(ups[i - j - 1] == d for j in range(k))])
            if len(idx) >= 100:
                conds[f"{k} consec {lab}"] = idx

    print("=" * 112)
    print("FADE TABLE — buy the DOWN side. BOTH bars shown side by side.")
    print("=" * 112)
    print(f"  BAR A = {BAR50*100:.2f}%  (assumes a 50c entry — OPTIMISTIC, "
          f"the market does not open there)")
    print(f"  BAR B = {BAR_REAL*100:.2f}%  (measured no_ask = 53c at open, "
          f"+ {float(kalshi_fee_per_contract_unrounded(ENTRY_REAL))*100:.2f}c "
          f"fee)  <-- THE REAL ONE")
    print(f"  n = {n} settled KXBTC15M windows, 2026-05-25 -> 2026-08-01\n")
    print(f"  {'condition':<20} {'n':>6} {'DOWN%':>7} {'95% CI':>16} "
          f"{'vs A':>8} {'vs B':>8} {'p vs A':>8} {'p vs B':>8} "
          f"{'clears B?':>10}")
    rows = []
    for lab, idx in conds.items():
        nxt = ups[idx]
        nn = len(nxt)
        downs = int((nxt == 0).sum())
        r = downs / nn
        lo, hi = wilson(downs, nn)
        pa = stats.binomtest(downs, nn, BAR50, alternative="greater").pvalue
        pb = stats.binomtest(downs, nn, BAR_REAL,
                             alternative="greater").pvalue
        clears = "YES" if lo > BAR_REAL else ("point" if r > BAR_REAL
                                              else "no")
        print(f"  {lab:<20} {nn:>6} {r*100:>6.2f}% "
              f"[{lo*100:>5.2f},{hi*100:>5.2f}] "
              f"{(r-BAR50)*100:>+7.2f}pp {(r-BAR_REAL)*100:>+7.2f}pp "
              f"{pa:>8.4f} {pb:>8.4f} {clears:>10}")
        rows.append((lab, nn, r, lo, hi, pa, pb))
    above = [x for x in rows if x[2] > BAR_REAL]
    print(f"\n  conditions with DOWN% above the REAL bar: {len(above)} of "
          f"{len(rows)}")
    print(f"  conditions whose CI LOWER BOUND clears the real bar: "
          f"{sum(1 for x in rows if x[3] > BAR_REAL)} of {len(rows)}")


# ------------------------------------------- speed-conditional touch matrix
def speed_conditional():
    by_mkt = defaultdict(list)
    with open(PANEL, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            by_mkt[(r["event"], r["ticker"])].append(r)
    for k in by_mkt:
        by_mkt[k].sort(key=lambda r: r["ts"])

    print("\n" + "=" * 112)
    print("SPEED-CONDITIONAL TOUCH — does a FAST early move predict reaching "
          "a HIGHER level?")
    print("=" * 112)
    print("  Read: enter at E. Among the paths that reached E+T1, split by "
          "whether they got")
    print("  there FAST (below median minutes) or SLOW. Then ask how many go "
          "on to reach E+T2.")
    print("  If momentum is real, FAST should beat SLOW. If the price is "
          "fair, they should match.\n")
    print(f"  {'entry':>6} {'T1':>4} {'T2':>4} {'n_fast':>7} {'n_slow':>7} "
          f"{'P(T2|fast)':>11} {'P(T2|slow)':>11} {'diff pp':>9} "
          f"{'z':>7} {'verdict':>10}")

    ENTRIES = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    PAIRS = [(0.05, 0.15), (0.05, 0.20), (0.10, 0.20), (0.10, 0.30)]
    BAND = 0.025
    out = []
    for E in ENTRIES:
        for T1, T2 in PAIRS:
            if E + T2 >= 0.99:
                continue
            recs = []
            for (evk, tk), rows in by_mkt.items():
                asks = np.array([r["ask"] for r in rows])
                bids = np.array([r["bid"] for r in rows])
                ts = np.array([r["ts"] for r in rows])
                for i in range(len(rows) - 1):
                    if abs(asks[i] - E) > BAND:
                        continue
                    fb, ft = bids[i + 1:], ts[i + 1:]
                    h1 = np.flatnonzero(fb >= E + T1)
                    if len(h1) == 0:
                        continue
                    j = h1[0]
                    mins = (ft[j] - ts[i]) / 60.0
                    # did it go on to T2 AFTER reaching T1?
                    rest = fb[j + 1:]
                    hit2 = bool((rest >= E + T2).any()) if len(rest) else False
                    recs.append((mins, hit2, evk))
                    break        # one observation per market, avoids
                                 # counting the same path many times
            if len(recs) < 120:
                continue
            m = np.array([r[0] for r in recs])
            h = np.array([1.0 if r[1] else 0.0 for r in recs])
            med = np.median(m)
            fast, slow = h[m <= med], h[m > med]
            if len(fast) < 40 or len(slow) < 40:
                continue
            pf, ps = fast.mean(), slow.mean()
            se = np.sqrt(pf * (1 - pf) / len(fast) + ps * (1 - ps) / len(slow))
            z = (pf - ps) / se if se > 0 else 0.0
            vd = ("MOMENTUM" if z > 2 else ("REVERSAL" if z < -2 else "none"))
            print(f"  {E*100:>5.0f}c {T1*100:>3.0f}c {T2*100:>3.0f}c "
                  f"{len(fast):>7} {len(slow):>7} {pf*100:>10.2f}% "
                  f"{ps*100:>10.2f}% {(pf-ps)*100:>+8.2f} {z:>+7.2f} "
                  f"{vd:>10}")
            out.append({"E": E, "T1": T1, "T2": T2, "p_fast": pf,
                        "p_slow": ps, "z": z})
    sig = [o for o in out if abs(o["z"]) > 2]
    print(f"\n  cells tested: {len(out)}; |z|>2: {len(sig)}; "
          f"expected by chance at 5%: {0.05*len(out):.1f}")
    json.dump(out, open(r"C:\Users\gianf\crypto\reports\speed_conditional.json",
                        "w"), indent=2)


if __name__ == "__main__":
    fade()
    speed_conditional()
