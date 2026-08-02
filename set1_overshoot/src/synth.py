"""Synthetic control -- run the whole pipeline on data with a known answer.

Two worlds are generated, in the same on-disk format as the real candles so the
identical Phase 1 and Phase 2 code runs on them without modification:

  null   -- the price is an exact martingale and the outcome is drawn from the
            terminal price. E[win | price_t] = price_t at every t, by
            construction. A correct pipeline must find zero miscalibration and
            a net expectancy of exactly minus (spread + slippage + fees).

  boost  -- the same paths, but the outcome is drawn at (terminal price + DELTA)
            for matches that had a qualifying set-1-style drop. A correct
            pipeline must recover DELTA. This measures the study's POWER: if the
            real sample cannot see a planted 3pp effect, "no effect found" means
            "underpowered", not "no effect".

Durations, pre-match price distribution and per-minute volatility are all read
off the real data so the synthetic sample is matched, not invented.
"""
import argparse
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

PRE_MIN = 240        # minutes of dormant pre-match quoting


def simulate(n, durations, pre_mids, sigma, delta, rng):
    """Bounded-martingale price paths on the probability scale.

    dp = sigma * p * (1 - p) * dW keeps p in (0,1) without reflection, and is a
    martingale, so the price is a fair forecast at every instant.
    """
    rows_t, rows_ts, rows_b, rows_a = [], [], [], []
    meta = []
    base_ts = 1_780_000_000

    for i in range(n):
        dur = int(durations[i])
        q = float(pre_mids[i]) / 100.0
        p = np.empty(dur + 1)
        p[0] = q
        z = rng.standard_normal(dur)
        for t in range(dur):
            p[t + 1] = np.clip(p[t] + sigma * p[t] * (1 - p[t]) * z[t],
                               0.002, 0.998)
        # let the last few minutes converge, as a real market does at match end
        # Converge to the outcome over the closing minutes, as a real market
        # does. This preserves the martingale property: the target is drawn
        # from p[dur], so E[blend | F_t] = p_t for any t before the blend.
        tail = min(20, dur)
        pull = np.linspace(0, 1, tail + 1)[1:]
        target = 1.0 if rng.random() < p[dur] else 0.0
        seg = p[dur - tail + 1:]
        p[dur - tail + 1:] = (1 - pull[:len(seg)]) * seg + pull[:len(seg)] * target

        win = int(target)
        cents = np.clip(np.rint(p * 100), 1, 99).astype(np.int32)

        pre = np.full(PRE_MIN, int(round(q * 100)), np.int32)
        full = np.concatenate([pre, cents])
        spread = rng.choice([1, 2], size=len(full), p=[0.75, 0.25])
        bid = np.clip(full - spread // 2 - (spread % 2), 1, 98)
        ask = np.clip(bid + spread, 2, 99)

        t_start = base_ts + i * 200_000
        ts = t_start + np.arange(len(full), dtype=np.int64) * 60
        tick = f"SYNTH-{i:06d}"
        rows_t.append(np.full(len(full), tick))
        rows_ts.append(ts)
        rows_b.append(bid)
        rows_a.append(ask)
        meta.append({
            "ticker": tick, "event_ticker": f"SYNTHEV-{i:06d}",
            "tour": "SYNTH", "series": "SYNTH",
            "true_win": win, "p_final": float(p[dur]),
            "open_time": pd.Timestamp(t_start, unit="s", tz="UTC"),
            "close_time": pd.Timestamp(ts[-1], unit="s", tz="UTC"),
            "volume": 1000.0,
        })
    md = pd.DataFrame(meta)

    if delta:
        # bias only the matches that dropped -- the exact population the study
        # conditions on, so the planted effect is where the test looks
        prem = pre_mids[:len(md)] / 100.0
        dropped = (prem >= 0.60)
        pb = np.clip(md["p_final"].values + delta * dropped, 0.001, 0.999)
        md["true_win"] = (rng.random(len(md)) < pb).astype(int)

    md["result"] = np.where(md["true_win"] == 1, "yes", "no")
    b_all = np.concatenate(rows_b).astype(np.int16)
    a_all = np.concatenate(rows_a).astype(np.int16)
    cd = pd.DataFrame({
        "ticker": np.concatenate(rows_t),
        "ts": np.concatenate(rows_ts),
        "bid": b_all,
        "ask": a_all,
        # synthetic minutes have no intra-minute range, so the extremes equal
        # the closes. Present so the OHLC-era p1_state can read this frame.
        "bid_h": b_all, "bid_l": b_all, "bid_o": b_all,
        "ask_h": a_all, "ask_l": a_all, "ask_o": a_all,
        "vol": 0,
    })
    return cd, md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12000)
    ap.add_argument("--delta", type=float, default=0.0)
    ap.add_argument("--tag", default="null")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--src", default="paths")
    args = ap.parse_args()

    st = pd.read_parquet(DATA / f"{args.src}_state.parquet")
    st = st[st["ok"].fillna(False) & st["plausible"].fillna(False)]
    rng = np.random.default_rng(args.seed)
    dur = rng.choice(st["dur_min"].values, size=args.n)
    pre = (st["pre_bid"].values + st["pre_ask"].values) / 2
    pre = rng.choice(pre[pre >= 50], size=args.n)

    npz = np.load(DATA / f"{args.src}_paths.npz", allow_pickle=True)
    b, a = npz["bid"].astype(np.float64), npz["ask"].astype(np.float64)
    mid = np.where((b >= 0) & (a >= 0), (b + a) / 2, np.nan)
    d = np.diff(mid, axis=1)
    real_sd = np.nanstd(d) / 100.0
    typical = 0.25 * 0.75
    sigma = float(real_sd / typical)
    print(f"real per-minute mid sd  {np.nanstd(d):.3f} cents "
          f"-> sigma {sigma:.4f}")

    cd, md = simulate(args.n, dur, pre, sigma, args.delta, rng)
    out = DATA / f"synth_{args.tag}"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.parquet"):
        f.unlink()
    cd.to_parquet(out / "part_0000.parquet", index=False)
    md.to_parquet(DATA / f"synth_{args.tag}_universe.parquet", index=False)
    print(f"{args.n:,} synthetic matches, delta={args.delta}, "
          f"win rate {md['true_win'].mean():.4f} -> {out}")


if __name__ == "__main__":
    main()
