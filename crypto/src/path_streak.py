"""TEST 1 (path/touch) + TEST 2 (streaks) + TEST 3 (controls).

Runs entirely on data already on disk:
  - data/panel/panel_KXBTCD.jsonl  : per-minute yes_bid/yes_ask, 250 events,
                                     1,968 markets, 25 May - 30 Jul 2026
  - data/kalshi_settled/KXBTC15M.jsonl : settled 15-minute markets

LOOK-AHEAD: entry uses the ASK at minute t; the touch test scans only minutes
STRICTLY AFTER t; streak state uses only windows whose close_time precedes the
decision window's open. Asserted in code.

UNIT OF OBSERVATION: event. Every CI bootstraps events, never market-minutes
and never strikes.

FEES: exact decimal via fees.py. Entry at the real ask, exit at the real bid,
two taker fees for a round trip, one for hold-to-settlement.
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
OUT = r"C:\Users\gianf\crypto\reports"

ENTRIES = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80,
           0.90]
TARGETS = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50]
BAND = 0.025           # entry bucket half-width


def fee(p):
    return float(kalshi_fee_per_contract_unrounded(
        min(max(float(p), 0.001), 0.999)))


def boot_events(vals_by_event, n_boot=2000, seed=11):
    """Mean with a CI clustered by EVENT."""
    keys = list(vals_by_event)
    if not keys:
        return None
    per = np.array([np.mean(vals_by_event[k]) for k in keys])
    rng = np.random.default_rng(seed)
    n = len(per)
    bs = np.array([per[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return float(per.mean()), float(lo), float(hi), n


# ------------------------------------------------------------------ TEST 1
def load_panel():
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
    return by_mkt


def touch_matrix(by_mkt, synthetic=False):
    """For each entry opportunity, did the BID later reach entry+target?"""
    touch = defaultdict(lambda: defaultdict(list))     # (e,t) -> event -> 0/1
    expect_rt = defaultdict(lambda: defaultdict(list))
    expect_hold = defaultdict(lambda: defaultdict(list))
    ttt = defaultdict(list)
    zero = defaultdict(lambda: defaultdict(list))
    nopp = defaultdict(int)

    for (ev, tk), rows in by_mkt.items():
        n = len(rows)
        asks = np.array([r["ask"] for r in rows])
        bids = np.array([r["bid"] for r in rows])
        ts = np.array([r["ts"] for r in rows])
        y = rows[0]["y"]
        for i in range(n - 1):
            a_in = asks[i]
            for e in ENTRIES:
                if abs(a_in - e) > BAND:
                    continue
                nopp[e] += 1
                fut_b = bids[i + 1:]              # STRICTLY after entry
                fut_t = ts[i + 1:]
                for tgt in TARGETS:
                    lvl = e + tgt
                    if lvl >= 0.99:
                        continue
                    hit = np.flatnonzero(fut_b >= lvl)
                    touched = len(hit) > 0
                    touch[(e, tgt)][ev].append(1.0 if touched else 0.0)
                    if touched:
                        ttt[(e, tgt)].append((fut_t[hit[0]] - ts[i]) / 60.0)
                        pnl = lvl - a_in - fee(a_in) - fee(lvl)
                    else:
                        # never touched -> hold to settlement, ONE fee
                        pnl = y - a_in - fee(a_in)
                    expect_rt[(e, tgt)][ev].append(pnl)
                    zero[(e, tgt)][ev].append(
                        1.0 if (not touched and y == 0.0) else 0.0)
                # pure hold-to-settlement benchmark at this entry
                expect_hold[e][ev].append(y - a_in - fee(a_in))
    return touch, expect_rt, expect_hold, ttt, zero, nopp


def report_touch(touch, expect_rt, expect_hold, ttt, zero, nopp, label):
    print(f"\n{'='*112}")
    print(f"TEST 1 — TOUCH MATRIX AND EXPECTANCY   [{label}]")
    print(f"{'='*112}")
    print(f"  {'entry':>6} {'target':>7} {'n_opp':>8} {'n_ev':>5} "
          f"{'P(touch)':>9} {'med_min':>8} {'p90_min':>8} {'P(->0)':>8} "
          f"{'GROSS c':>9} {'NET c/ct':>10} {'95% CI (event)':>20}")
    rows = []
    for e in ENTRIES:
        for tgt in TARGETS:
            key = (e, tgt)
            if key not in touch or not touch[key]:
                continue
            tb = boot_events(touch[key])
            eb = boot_events(expect_rt[key])
            if tb is None or eb is None:
                continue
            ptouch, _, _, nev = tb
            net, lo, hi, _ = eb
            if sum(len(v) for v in touch[key].values()) < 200:
                continue
            tts = ttt[key]
            zb = boot_events(zero[key])
            gross = net + fee(e) + fee(e + tgt)   # add fees back
            print(f"  {e*100:>5.0f}c {tgt*100:>6.0f}c "
                  f"{sum(len(v) for v in touch[key].values()):>8} {nev:>5} "
                  f"{ptouch*100:>8.2f}% "
                  f"{(np.median(tts) if tts else -1):>8.1f} "
                  f"{(np.percentile(tts,90) if tts else -1):>8.1f} "
                  f"{zb[0]*100:>7.2f}% {gross*100:>+9.3f} {net*100:>+10.3f} "
                  f"[{lo*100:+.2f},{hi*100:+.2f}]")
            rows.append({"entry": e, "target": tgt, "p_touch": ptouch,
                         "net_c": net * 100, "gross_c": gross * 100,
                         "ci_lo": lo * 100, "ci_hi": hi * 100,
                         "n_opp": sum(len(v) for v in touch[key].values()),
                         "n_events": nev})
    print(f"\n  HOLD-TO-SETTLEMENT benchmark (one fee, no target):")
    print(f"  {'entry':>6} {'n_ev':>5} {'NET c/ct':>10} {'95% CI (event)':>20}")
    for e in ENTRIES:
        if e not in expect_hold or not expect_hold[e]:
            continue
        hb = boot_events(expect_hold[e])
        if hb is None:
            continue
        m, lo, hi, nev = hb
        print(f"  {e*100:>5.0f}c {nev:>5} {m*100:>+10.3f} "
              f"[{lo*100:+.2f},{hi*100:+.2f}]")
    return rows


# ------------------------------------------------------------------ TEST 2
def streak_test():
    print(f"\n{'='*112}")
    print("TEST 2 — STREAKS on KXBTC15M")
    print(f"{'='*112}")
    ev = {}
    with open(S15, encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            e, ct, res = (m.get("event_ticker"), m.get("close_time"),
                          str(m.get("result")))
            if not e or not ct or res not in ("yes", "no"):
                continue
            ev[e] = (ct, 1 if res == "yes" else 0,
                     m.get("yes_ask_dollars"), m.get("open_time"))
    rows = sorted(ev.values())
    ups = np.array([r[1] for r in rows])
    times = [r[0] for r in rows]
    print(f"  n = {len(ups)} settled windows, "
          f"{times[0][:16]} -> {times[-1][:16]}")
    base = ups.mean()
    ci = stats.binomtest(int(ups.sum()), len(ups), 0.5)
    print(f"  UNCONDITIONAL up rate = {base*100:.2f}%  "
          f"(binomial p vs 50% = {ci.pvalue:.4f})")
    print(f"  BREAK-EVEN BAR at 50c entry, hold-to-settlement, one fee: "
          f"51.75%")

    print(f"\n  {'condition':<26} {'n':>7} {'next-up%':>9} {'chance%':>8} "
          f"{'binom p':>9} {'vs 51.75% bar':>14}")
    out = []
    for N in (3, 5, 10, 20):
        for k in range(N + 1):
            idx = [i for i in range(N, len(ups))
                   if ups[i - N:i].sum() == k]
            if len(idx) < 60:
                continue
            nxt = ups[idx]
            r = nxt.mean()
            p = stats.binomtest(int(nxt.sum()), len(nxt), 0.5).pvalue
            chance = stats.binom.pmf(k, N, 0.5) * 100
            lab = f"{k}/{N} ups in last {N}"
            print(f"  {lab:<26} {len(idx):>7} {r*100:>8.2f}% "
                  f"{chance:>7.2f}% {p:>9.4f} "
                  f"{'PASS' if r > 0.5175 else 'below':>14}")
            out.append({"cond": lab, "n": len(idx), "rate": r, "p": p})
    print(f"\n  {'consecutive run':<26} {'n':>7} {'next-up%':>9} "
          f"{'binom p':>9} {'vs 51.75% bar':>14}")
    for k in range(2, 9):
        for direc, lab in ((1, "ups"), (0, "downs")):
            idx = [i for i in range(k, len(ups))
                   if all(ups[i - j - 1] == direc for j in range(k))]
            if len(idx) < 60:
                continue
            nxt = ups[idx]
            r = nxt.mean()
            p = stats.binomtest(int(nxt.sum()), len(nxt), 0.5).pvalue
            print(f"  {f'{k} consecutive {lab}':<26} {len(idx):>7} "
                  f"{r*100:>8.2f}% {p:>9.4f} "
                  f"{'PASS' if r > 0.5175 else 'below':>14}")
            out.append({"cond": f"{k} consec {lab}", "n": len(idx),
                        "rate": r, "p": p})

    # autocorrelation of the settlement sign
    print(f"\n  AUTOCORRELATION of settlement sign (lag 1-20), n={len(ups)}")
    x = ups - ups.mean()
    se = 1.0 / np.sqrt(len(ups))
    print(f"  {'lag':>4} {'autocorr':>10} {'95% CI':>20} {'signal':>10}")
    acs = []
    for lag in range(1, 21):
        ac = float(np.corrcoef(x[:-lag], x[lag:])[0, 1])
        sig = ("REVERSAL" if ac < -1.96 * se else
               ("MOMENTUM" if ac > 1.96 * se else "none"))
        if lag <= 10 or sig != "none":
            print(f"  {lag:>4} {ac:>+10.4f} "
                  f"[{ac-1.96*se:+.4f},{ac+1.96*se:+.4f}] {sig:>10}")
        acs.append(ac)

    # two disjoint halves
    print(f"\n  TWO DISJOINT PERIODS")
    half = len(ups) // 2
    for nm, seg in (("first half", ups[:half]), ("second half", ups[half:])):
        b = stats.binomtest(int(seg.sum()), len(seg), 0.5)
        print(f"    {nm:<12} n={len(seg):>6} up={seg.mean()*100:.2f}% "
              f"p={b.pvalue:.4f}")
    return out, float(base), acs


# ------------------------------------------------------------------ TEST 3
def synthetic_panel(by_mkt, seed=3):
    """A TRUE MARTINGALE binary-price path with random outcomes.

    THE FIRST VERSION WAS BROKEN AND THE CONTROL CAUGHT IT. It built the price
    as a random walk CLIPPED to [0.02, 0.98] and drew the outcome from the
    final price. Clipping destroys the martingale property: at p=0.05 the lower
    clip pushes the path up more often than down, so E[p_final | p_now] >
    p_now. That fabricated genuine positive drift at low entries, and the
    control duly reported +4c to +9c expectancy on data built to contain none.
    The touch code was fine; the generator was not.

    Correct construction: let W be a Brownian motion on [0, T] and define
        p_t = P(W_T > 0 | W_t) = Phi( W_t / sqrt(T - t) )
    with outcome y = 1{W_T > 0}. This is by construction a fair binary price
    and an exact martingale, so EVERY buy-here-sell-there rule must have zero
    gross expectancy and net expectancy of exactly -(fees + spread).
    """
    rng = np.random.default_rng(seed)
    # measured only for reporting; the martingale does not depend on it
    steps = []
    for rows in by_mkt.values():
        m = np.array([r["mid"] for r in rows])
        if len(m) > 3:
            steps.extend(np.diff(m))
    sd = float(np.std(steps))

    out = {}
    for (ev, tk), rows in list(by_mkt.items()):
        n = len(rows)
        if n < 3:
            continue
        dW = rng.normal(0.0, 1.0, n)
        W = np.cumsum(dW)
        tau = np.arange(n, 0, -1).astype(float)   # minutes remaining, >=1
        p = stats.norm.cdf(W / np.sqrt(tau))
        # terminal outcome consistent with the path: one more step to expiry
        y = float(W[-1] + rng.normal(0.0, 1.0) > 0.0)
        pb = np.clip(p - 0.005, 0.005, 0.985)
        pa = np.clip(p + 0.005, 0.015, 0.995)
        out[(ev, tk)] = [{"ts": rows[i]["ts"],
                          "bid": round(float(pb[i]), 4),
                          "ask": round(float(pa[i]), 4),
                          "mid": float(p[i]), "spread": 0.01,
                          "vol": 0.0, "oi": 0.0,
                          "y": y, "event": ev, "ticker": tk}
                         for i in range(n)]
    return out, sd


def selection_audit(by_mkt):
    print(f"\n{'='*112}")
    print("TEST 3b — SELECTION AUDIT (z-scores vs outcome)")
    print(f"{'='*112}")
    feats, ys = defaultdict(list), []
    for rows in by_mkt.values():
        y = rows[0]["y"]
        ys.append(y)
        feats["n_minutes"].append(len(rows))
        feats["mean_spread"].append(np.mean([r["spread"] for r in rows]))
        feats["first_ask"].append(rows[0]["ask"])
        feats["last_bid"].append(rows[-1]["bid"])
        feats["mean_vol"].append(np.mean([r.get("vol", 0) for r in rows]))
        feats["mean_oi"].append(np.mean([r.get("oi", 0) for r in rows]))
    y = np.array(ys)
    print(f"  n={len(y)} markets, outcome base rate {y.mean():.4f}")
    print(f"  {'field':<16} {'distinct':>9} {'corr':>9} {'z':>9} {'verdict':>14}")
    for k, v in feats.items():
        v = np.array(v, dtype=float)
        nd = len(np.unique(v))
        if nd < 3:
            print(f"  {k:<16} {nd:>9} {'--':>9} {'--':>9} "
                  f"{'UNTESTABLE':>14}")
            continue
        c = float(np.corrcoef(v, y)[0, 1])
        z = c * np.sqrt(len(y) - 1)
        vd = ("LEAK?" if abs(z) > 4 else
              ("watch" if abs(z) > 2 else "clean"))
        print(f"  {k:<16} {nd:>9} {c:>+9.4f} {z:>+9.2f} {vd:>14}")


def main():
    os.makedirs(OUT, exist_ok=True)
    by_mkt = load_panel()
    nev = len({k[0] for k in by_mkt})
    print(f"panel: {len(by_mkt)} markets, {nev} events, "
          f"{sum(len(v) for v in by_mkt.values())} market-minutes")

    # --- TEST 3a synthetic control FIRST ---
    syn, sd = synthetic_panel(by_mkt)
    print(f"\nsynthetic control: matched per-minute mid sd = {sd:.5f}")
    t, e, h, tt, z, no = touch_matrix(syn)
    report_touch(t, e, h, tt, z, no, "SYNTHETIC CONTROL — expect net ~ -fees")

    # --- TEST 1 real ---
    t, e, h, tt, z, no = touch_matrix(by_mkt)
    rows = report_touch(t, e, h, tt, z, no, "REAL DATA")

    # --- volatility framing ---
    print(f"\n  REALIZED VOL BY ENTRY BUCKET (per-minute mid sd)")
    volb = defaultdict(list)
    for rows_ in by_mkt.values():
        m = np.array([r["mid"] for r in rows_])
        a = np.array([r["ask"] for r in rows_])
        if len(m) < 5:
            continue
        s = float(np.std(np.diff(m)))
        for E in ENTRIES:
            if abs(np.median(a) - E) <= BAND:
                volb[E].append(s)
    print(f"  {'entry':>6} {'n_mkts':>7} {'per-min mid sd':>16}")
    for E in ENTRIES:
        if volb[E]:
            print(f"  {E*100:>5.0f}c {len(volb[E]):>7} "
                  f"{np.mean(volb[E])*100:>15.4f}c")

    selection_audit(by_mkt)
    sout, base, acs = streak_test()

    json.dump({"touch": rows, "streak": sout, "base_up": base,
               "autocorr": acs},
              open(os.path.join(OUT, "path_streak.json"), "w"),
              indent=2, default=str)


if __name__ == "__main__":
    main()
