"""TASK B (3a) — streaks, fades and autocorrelation on ETH, SOL, XRP vs BTC.

THREE INDEPENDENT REPLICATIONS. That is the whole point: a structural effect
should appear in all of them; noise scatters in sign and magnitude.

Thesis under test: if mean reversion is structural, thinner / less-arbitraged
assets should show MORE of it.

SELECTION: every settled window with a parseable result, deduplicated to one
row per event_ticker, ordered by close_time. No filtering on outcome.
LOOK-AHEAD: streak state at window i uses only windows < i, all of which had
settled before window i opened.
UNIT: the 15-minute window.

COSTING: deliberately NOT done. There is no recorded ask for settled history
and all three previously quoted bars were the wrong shape of number. Effects
are reported UNCOSTED and flagged as such. Costing waits for the recorder.
"""
import json
import os
from collections import Counter

import numpy as np
from scipy import stats

SETTLED = r"C:\Users\gianf\crypto\data\kalshi_settled"
OUT = r"C:\Users\gianf\crypto\reports"
ASSETS = [("BTC", "KXBTC15M"), ("ETH", "KXETH15M"),
          ("SOL", "KXSOL15M"), ("XRP", "KXXRP15M")]


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def load(series):
    p = os.path.join(SETTLED, f"{series}.jsonl")
    if not os.path.exists(p):
        return None
    ev = {}
    ticks = Counter()
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            e, ct, res = (m.get("event_ticker"), m.get("close_time"),
                          str(m.get("result")))
            if not e or not ct or res not in ("yes", "no"):
                continue
            ticks[str(m.get("price_level_structure"))] += 1
            ev[e] = (ct, 1 if res == "yes" else 0)
    rows = sorted(ev.values())
    return rows, ticks


def conditions(ups):
    out = {}
    n = len(ups)
    for N in (3, 5, 10, 20):
        for k in range(N + 1):
            idx = np.array([i for i in range(N, n) if ups[i - N:i].sum() == k])
            if len(idx) >= 100:
                out[f"{k}/{N} ups"] = idx
    for k in range(2, 9):
        for d, lab in ((1, "ups"), (0, "downs")):
            idx = np.array([i for i in range(k, n)
                            if all(ups[i - j - 1] == d for j in range(k))])
            if len(idx) >= 100:
                out[f"{k} consec {lab}"] = idx
    return out


def main():
    summary = {}
    all_p = []
    for name, series in ASSETS:
        got = load(series)
        if not got:
            print(f"{name}: no data")
            continue
        rows, ticks = got
        ups = np.array([r[1] for r in rows])
        times = [r[0] for r in rows]
        n = len(ups)

        print("=" * 104)
        print(f"{name}  ({series})  — SAMPLE COMPOSITION")
        print("=" * 104)
        print(f"  selection: every settled window with a parseable result, "
              f"deduped to one row per event_ticker, ordered by close_time")
        print(f"  n = {n} windows   {times[0][:16]} -> {times[-1][:16]}")
        print(f"  tick structure: {dict(ticks)}")
        up = ups.mean()
        b = stats.binomtest(int(ups.sum()), n, 0.5)
        lo, hi = wilson(int(ups.sum()), n)
        print(f"  unconditional UP rate = {up*100:.2f}% "
              f"[{lo*100:.2f},{hi*100:.2f}]  p vs 50% = {b.pvalue:.4f}")

        # autocorrelation
        x = ups - ups.mean()
        se = 1.0 / np.sqrt(n)
        acs = []
        for lag in range(1, 21):
            acs.append(float(np.corrcoef(x[:-lag], x[lag:])[0, 1]))
        a1, a2 = acs[0], acs[1]
        nsig = sum(1 for a in acs if abs(a) > 1.96 * se)
        print(f"  autocorr lag1 = {a1:+.4f} [{a1-1.96*se:+.4f},"
              f"{a1+1.96*se:+.4f}]   lag2 = {a2:+.4f}   "
              f"lags |ac|>1.96SE: {nsig}/20")

        # conditions
        conds = conditions(ups)
        best_lab, best_rate, best_n, best_p = None, 0.5, 0, 1.0
        rows_out = []
        for lab, idx in conds.items():
            nxt = ups[idx]
            nn = len(nxt)
            downs = int((nxt == 0).sum())
            r = downs / nn
            p = stats.binomtest(downs, nn, 0.5).pvalue
            all_p.append((name, lab, p))
            rows_out.append((lab, nn, r, p))
            if r > best_rate:
                best_lab, best_rate, best_n, best_p = lab, r, nn, p
        print(f"  {len(conds)} streak conditions tested")
        print(f"  strongest FADE cell (highest DOWN rate): {best_lab} "
              f"-> {best_rate*100:.2f}% on n={best_n}, p={best_p:.4f}")
        # the specific cells BTC flagged
        for want in ("2 consec ups", "2/3 ups", "10/20 ups"):
            for lab, nn, r, p in rows_out:
                if lab == want:
                    lo2, hi2 = wilson(int(round(r * nn)), nn)
                    print(f"    [{want:<13}] DOWN {r*100:>6.2f}% "
                          f"[{lo2*100:.2f},{hi2*100:.2f}] n={nn} p={p:.4f}")

        # two disjoint halves
        h = n // 2
        u1, u2 = ups[:h], ups[h:]
        print(f"  two periods: first UP {u1.mean()*100:.2f}% (n={len(u1)}), "
              f"second UP {u2.mean()*100:.2f}% (n={len(u2)})")

        summary[name] = {"n": n, "up": float(up), "p_uncond": float(b.pvalue),
                         "ac1": a1, "ac2": a2, "n_sig_lags": nsig,
                         "best_fade": best_lab, "best_rate": float(best_rate),
                         "best_n": int(best_n), "best_p": float(best_p),
                         "first_up": float(u1.mean()),
                         "second_up": float(u2.mean()),
                         "range": f"{times[0][:10]}..{times[-1][:10]}",
                         "conds": len(conds)}
        print()

    # ---------------- the deliverable: side-by-side ----------------
    print("=" * 104)
    print("FOUR-ASSET COMPARISON — the deliverable")
    print("=" * 104)
    print(f"  {'asset':<6} {'n':>6} {'UP%':>7} {'p':>7} {'lag1 ac':>9} "
          f"{'lag2 ac':>9} {'sig lags':>9} {'best fade cell':<16} "
          f"{'rate':>7} {'n':>6} {'p':>8}")
    for k, v in summary.items():
        print(f"  {k:<6} {v['n']:>6} {v['up']*100:>6.2f}% {v['p_uncond']:>7.3f} "
              f"{v['ac1']:>+9.4f} {v['ac2']:>+9.4f} {v['n_sig_lags']:>9} "
              f"{str(v['best_fade']):<16} {v['best_rate']*100:>6.2f}% "
              f"{v['best_n']:>6} {v['best_p']:>8.4f}")

    print(f"\n  REPLICATION CHECK — mean reversion (negative lag-1):")
    negs = [k for k, v in summary.items() if v["ac1"] < 0]
    sigs = [k for k, v in summary.items()
            if v["ac1"] < -1.96 / np.sqrt(v["n"])]
    print(f"    negative lag-1 in {len(negs)}/{len(summary)} assets: {negs}")
    print(f"    SIGNIFICANTLY negative in {len(sigs)}/{len(summary)}: {sigs}")

    print(f"\n  two-period stability of the unconditional rate:")
    for k, v in summary.items():
        gap = (v["first_up"] - v["second_up"]) * 100
        print(f"    {k:<5} first {v['first_up']*100:.2f}%  "
              f"second {v['second_up']*100:.2f}%  gap {gap:+.2f}pp")

    # BH across every streak test run this session
    print(f"\n  BH-FDR across all {len(all_p)} streak tests this session:")
    all_p.sort(key=lambda t: t[2])
    m = len(all_p)
    surv = 0
    for i, (a, lab, p) in enumerate(all_p[:10], 1):
        thr = 0.05 * i / m
        ok = p <= thr
        if ok:
            surv = i
        print(f"    {i:>2}. {a:<4} {lab:<16} p={p:.5f} thr={thr:.5f} "
              f"{'SURVIVES' if ok else ''}")
    print(f"    -> {surv} of {m} survive")

    json.dump({"summary": summary, "n_tests": m},
              open(os.path.join(OUT, "streaks_multiasset.json"), "w"),
              indent=2, default=str)


if __name__ == "__main__":
    main()
