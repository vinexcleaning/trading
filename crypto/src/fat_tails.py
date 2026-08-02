"""TASK 4: fat tails in the wings, from the settled data alone.

`expiration_value` is the realised CF Benchmarks 60-second-average settlement at
each Kalshi hourly boundary — a free, high-quality spot series sampled exactly
at settlement, needing no candle reconstruction.

Questions:
  1. What is the distribution of hourly log returns? Tail index, Student-t nu.
  2. How badly does a Gaussian misprice each ladder position, especially the
     deep wings?
  3. Is the mispricing large relative to the fee at those strikes?

UNIT OF OBSERVATION: the EVENT. One settlement per hourly event, deduplicated
across the ladder's ~180 strikes. A ladder is ONE observation, not 180
(failure mode #3, 4 prior instances).

SAMPLE HYGIENE: date range, composition and selection rule printed BEFORE any
conclusion (failure mode #1).
"""
import json
import os
from collections import Counter

import numpy as np
from scipy import stats

import sys
sys.path.insert(0, os.path.dirname(__file__))
from fees import kalshi_fee_per_contract_unrounded  # noqa: E402

ROOT = r"C:\Users\gianf\crypto\data\kalshi_settled"


def load_series(series):
    """-> sorted list of (close_time, settlement), one per event."""
    p = os.path.join(ROOT, f"{series}.jsonl")
    if not os.path.exists(p):
        return []
    by_ev, conflicts = {}, 0
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            ev, v, ct = (m.get("event_ticker"), m.get("expiration_value"),
                         m.get("close_time"))
            if not ev or not ct or v in (None, ""):
                continue
            try:
                x = float(v)
            except (TypeError, ValueError):
                continue
            if x <= 0:
                continue
            if ev in by_ev and abs(by_ev[ev][1] - x) > 1e-9:
                conflicts += 1
            by_ev[ev] = (ct, x)
    rows = sorted(by_ev.values())
    return rows, conflicts


def main():
    out = {}
    for series in ["KXBTC", "KXETH"]:
        rows, conflicts = load_series(series)
        if len(rows) < 200:
            print(f"{series}: only {len(rows)} events, skipping")
            continue

        print("=" * 96)
        print(f"{series} — SAMPLE COMPOSITION (printed before any conclusion)")
        print("=" * 96)
        times = [r[0] for r in rows]
        vals = np.array([r[1] for r in rows])
        print(f"  selection rule : all settled events with a parseable "
              f"`expiration_value`, deduplicated to ONE row per event_ticker")
        print(f"  unit           : one hourly settlement (NOT one strike)")
        print(f"  n events       : {len(rows)}")
        print(f"  date range     : {times[0][:16]} -> {times[-1][:16]}")
        print(f"  settlement rng : {vals.min():.2f} .. {vals.max():.2f}")
        print(f"  conflicting settlements within an event: {conflicts}")
        hrs = Counter(t[11:13] for t in times)
        print(f"  hour-of-day coverage: {len(hrs)} distinct hours, "
              f"min/max per hour = {min(hrs.values())}/{max(hrs.values())}")

        # ---- hourly log returns, consecutive events only -------------------
        # Guard: only use consecutive-hour pairs so a gap does not masquerade
        # as a 1-hour return.
        import datetime as dt
        ts = [dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
              for t in times]
        rets, gaps = [], 0
        for (t0, v0), (t1, v1) in zip(zip(ts, vals), zip(ts[1:], vals[1:])):
            dh = (t1 - t0).total_seconds() / 3600.0
            if abs(dh - 1.0) > 1e-6:
                gaps += 1
                continue
            rets.append(np.log(v1 / v0))
        r = np.array(rets)
        print(f"  consecutive 1h returns: {len(r)} "
              f"({gaps} non-1h gaps excluded)")

        # ---- distribution --------------------------------------------------
        mu, sd = float(r.mean()), float(r.std(ddof=1))
        print(f"\n  mean={mu:.6e}  sd={sd:.6e}  "
              f"annualised vol={sd*np.sqrt(24*365.25)*100:.1f}%")
        print(f"  skew={stats.skew(r):.4f}  "
            f"excess kurtosis={stats.kurtosis(r):.4f}  "
            f"(Gaussian = 0)")
        jb = stats.jarque_bera(r)
        print(f"  Jarque-Bera = {jb.statistic:.1f}, p = {jb.pvalue:.3e}")

        nu, loc, scale = stats.t.fit(r)
        print(f"  Student-t fit: nu={nu:.3f} loc={loc:.3e} scale={scale:.3e}")
        # Hill tail index on the upper 5% of |returns|
        a = np.sort(np.abs(r))[::-1]
        k = max(10, int(0.05 * len(a)))
        hill = float(1.0 / np.mean(np.log(a[:k] / a[k])))
        print(f"  Hill tail index (top {k} of {len(a)}): alpha={hill:.3f}  "
              f"(alpha<4 => 4th moment undefined)")

        # ---- how badly does a Gaussian misprice the wings? -----------------
        print(f"\n  GAUSSIAN vs EMPIRICAL tail probability, hourly horizon")
        print(f"  {'sigma':>7} {'move %':>9} {'P_gauss':>10} {'P_emp':>10} "
            f"{'P_t':>10} {'emp/gauss':>10} {'kalshi fee@P_emp':>17}")
        res = []
        for z in [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]:
            thr = z * sd
            pg = 2 * (1 - stats.norm.cdf(z))
            pe = float(np.mean(np.abs(r - mu) > thr))
            pt = float(2 * (1 - stats.t.cdf(thr / scale, nu)))
            ratio = pe / pg if pg > 0 else float("nan")
            fee = float(kalshi_fee_per_contract_unrounded(
                max(min(pe, 0.99), 0.001))) * 100
            print(f"  {z:>7.1f} {thr*100:>9.3f} {pg:>10.5f} {pe:>10.5f} "
                f"{pt:>10.5f} {ratio:>10.2f} {fee:>16.3f}c")
            res.append({"z": z, "p_gauss": pg, "p_emp": pe, "p_t": pt,
                        "ratio": ratio, "fee_c": fee})

        # ---- the economic question ----------------------------------------
        print(f"\n  ECONOMIC SIZE of the tail mispricing (per contract):")
        print(f"  {'sigma':>7} {'edge (P_emp-P_gauss)':>22} {'in cents':>10} "
            f"{'fee@that price':>16} {'edge - fee':>12} {'tradeable?':>12}")
        for d in res:
            edge_c = (d["p_emp"] - d["p_gauss"]) * 100
            net = edge_c - d["fee_c"]
            print(f"  {d['z']:>7.1f} {d['p_emp']-d['p_gauss']:>22.5f} "
                f"{edge_c:>10.3f}c {d['fee_c']:>15.3f}c {net:>11.3f}c "
                f"{'YES' if net > 0 else 'no':>12}")

        out[series] = {"n_events": len(rows), "n_returns": len(r),
                       "date_min": times[0], "date_max": times[-1],
                       "sd": sd, "skew": float(stats.skew(r)),
                       "excess_kurtosis": float(stats.kurtosis(r)),
                       "student_t_nu": float(nu), "hill_alpha": hill,
                       "tails": res}
        print()

    with open(r"C:\Users\gianf\crypto\reports\fat_tails.json", "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
