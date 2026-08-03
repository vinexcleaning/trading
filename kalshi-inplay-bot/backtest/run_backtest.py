"""
run_backtest.py - driver for steps 4-7.

    python run_backtest.py prep     # clean + cache market views
    python run_backtest.py step5    # five strategies, TRAINING set only
    python run_backtest.py step6    # parameter sweep, TRAINING set only
    python run_backtest.py step7    # holdout, run once, nothing tuned
    python run_backtest.py report   # assemble the markdown

The holdout is only ever touched by step7.
"""

from __future__ import annotations

import itertools
import os
import pickle
import sys

import numpy as np
import pandas as pd

import engine
import strategies as st
from strategies import Params

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "views.pkl")
OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)

BASE = {
    "s1": Params(),
    "s3": Params(min_price=30, max_price=70, target=12, stop=20, time_limit=12),
    "s4": Params(min_price=30, max_price=70, target=12, stop=20, time_limit=12),
    "s5": Params(min_price=30, max_price=75, target=15, stop=20, time_limit=12),
}
NAMES = {"s1": "S1 V3 ramp", "s2": "S2 buy&hold", "s3": "S3 fade drop",
         "s4": "S4 ride rise", "s5": "S5 random"}


def get_views():
    if os.path.exists(CACHE):
        with open(CACHE, "rb") as f:
            return pickle.load(f)
    markets, candles = engine.load()
    print(f"loaded {len(markets)} markets, {len(candles):,} raw candles")
    df = engine.prepare(candles)
    print(f"cleaned -> {len(df):,} candles, {int(df.live.sum()):,} live "
          f"({df.live.mean()*100:.1f}%)")
    views = engine.build_views(df, markets)
    print(f"built {len(views)} market views")
    with open(CACHE, "wb") as f:
        pickle.dump((views, markets), f)
    return views, markets


def _tune(kind: str, **kw) -> Params:
    p = BASE[kind]
    return Params(**{**p.__dict__, **kw})


def run_one(views, kind: str, p: Params, label: str = ""):
    trades, fn = st.run(views, p, kind)
    return st.metrics(trades, label or NAMES[kind]), trades, fn


# ------------------------------------------------------------------ step 5
def step5(views, markets):
    tr, ho = st.split(views, markets)
    print(f"TRAIN {len(tr)} markets  |  HOLDOUT {len(ho)} markets (untouched)")
    rows, allt, funnels = [], {}, {}
    for kind in ["s1", "s2", "s3", "s4", "s5"]:
        p = BASE["s1"] if kind == "s2" else BASE[kind]
        m, trades, fn = run_one(tr, kind, p)
        rows.append(m)
        allt[NAMES[kind]] = trades
        funnels[NAMES[kind]] = fn
        print(f"  {NAMES[kind]:14s} {m['trades']:6d} trades")
    table = pd.DataFrame(rows).sort_values("net_c_per_trade", ascending=False)

    # slippage sensitivity: if the sign flips between 0c and 2c it is spread noise
    slip_rows = []
    for slp in (0.0, 1.0, 2.0):
        for kind in ["s1", "s2", "s3", "s4", "s5"]:
            base = BASE["s1"] if kind == "s2" else BASE[kind]
            p = Params(**{**base.__dict__, "slip": slp})
            m, _, _ = run_one(tr, kind, p)
            slip_rows.append({"slip_c": slp, "strategy": NAMES[kind],
                              "trades": m["trades"],
                              "net_c_per_trade": m["net_c_per_trade"],
                              "net": m["net"]})
    slip = pd.DataFrame(slip_rows).pivot(index="strategy", columns="slip_c",
                                         values="net_c_per_trade")

    spread_t = {k: st.by_group(v, "spread_bucket") for k, v in allt.items()}
    series_t = {k: st.by_group(v, "tournament") for k, v in allt.items()}
    with open(os.path.join(OUT, "step5.pkl"), "wb") as f:
        pickle.dump((table, slip, spread_t, series_t, funnels, allt), f)
    return table, slip, spread_t, series_t, funnels


# ------------------------------------------------------------------ step 6
SWEEPS = {
    "max_price": [65, 70, 75, 80, 85, 99],
    "thresh":    [8, 10, 12, 15, 20],
    "stop":      [15, 20, 25, 30],
    "target":    [10, 15, 20, 25],
}


def step6(views, markets, kind: str):
    tr, _ = st.split(views, markets)
    base = BASE[kind]
    print(f"sweeping {NAMES[kind]} on {len(tr)} training markets")

    one_at_a_time = []
    for dim, vals in SWEEPS.items():
        for val in vals:
            kw = {dim: float(val)}
            if kind == "s1" and dim == "stop":
                kw = {"disaster": float(val)}     # S1's stop is the disaster floor
            p = _tune(kind, **kw)
            m, _, _ = run_one(tr, kind, p)
            one_at_a_time.append({"dim": dim, "value": val, **{
                k: m[k] for k in ("trades", "matches", "win_rate",
                                  "net", "net_c_per_trade", "max_dd")}})
            print(f"  {dim}={val}: {m['trades']} tr, "
                  f"{m['net_c_per_trade']:.2f} c/trade", flush=True)
    oat = pd.DataFrame(one_at_a_time)

    grid_rows = []
    combos = list(itertools.product(*SWEEPS.values()))
    print(f"full grid: {len(combos)} configs")
    for n, (mx, th, sp, tg) in enumerate(combos, 1):
        kw = {"max_price": float(mx), "thresh": float(th), "target": float(tg)}
        kw["disaster" if kind == "s1" else "stop"] = float(sp)
        p = _tune(kind, **kw)
        m, _, _ = run_one(tr, kind, p)
        grid_rows.append({"max_price": mx, "thresh": th, "stop": sp,
                          "target": tg, **{k: m[k] for k in
                          ("trades", "matches", "win_rate", "net",
                           "net_c_per_trade", "max_dd")}})
        if n % 60 == 0:
            print(f"  {n}/{len(combos)}", flush=True)
    grid = pd.DataFrame(grid_rows)
    with open(os.path.join(OUT, f"step6_{kind}.pkl"), "wb") as f:
        pickle.dump((oat, grid), f)
    return oat, grid


def sensitivity(grid: pd.DataFrame, best: pd.Series) -> pd.DataFrame:
    """How far does net c/trade move when one knob shifts one notch?"""
    rows = []
    for dim, vals in SWEEPS.items():
        cur = best[dim]
        idx = vals.index(cur) if cur in vals else None
        for j in (idx - 1 if idx else None, idx + 1 if idx is not None else None):
            if j is None or j < 0 or j >= len(vals):
                continue
            q = grid
            for d2 in SWEEPS:
                q = q[q[d2] == (vals[j] if d2 == dim else best[d2])]
            if len(q):
                r = q.iloc[0]
                rows.append({"dim": dim, "from": cur, "to": vals[j],
                             "net_c": r.net_c_per_trade,
                             "delta": r.net_c_per_trade - best.net_c_per_trade,
                             "trades": r.trades})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ step 7
def step7(views, markets, kind: str, configs: list[dict]):
    tr, ho = st.split(views, markets)
    print(f"HOLDOUT: {len(ho)} markets - single pass, no tuning")
    rows = []
    for cfg in configs:
        kw = {"max_price": float(cfg["max_price"]), "thresh": float(cfg["thresh"]),
              "target": float(cfg["target"])}
        kw["disaster" if kind == "s1" else "stop"] = float(cfg["stop"])
        p = _tune(kind, **kw)
        lab = (f"max{cfg['max_price']}/th{cfg['thresh']}/"
               f"sl{cfg['stop']}/tg{cfg['target']}")
        m_tr, _, _ = run_one(tr, kind, p, label=lab)
        m_ho, trades_ho, _ = run_one(ho, kind, p, label=lab)
        rows.append({"config": lab,
                     "train_trades": m_tr["trades"],
                     "train_net_c": m_tr["net_c_per_trade"],
                     "train_net": m_tr["net"],
                     "hold_trades": m_ho["trades"],
                     "hold_matches": m_ho["matches"],
                     "hold_win": m_ho["win_rate"],
                     "hold_avg_win_c": m_ho["avg_win_c"],
                     "hold_avg_loss_c": m_ho["avg_loss_c"],
                     "hold_gross": m_ho["gross"], "hold_fees": m_ho["fees"],
                     "hold_net": m_ho["net"], "hold_net_c": m_ho["net_c_per_trade"],
                     "hold_dd": m_ho["max_dd"]})
        print(f"  {lab}: train {m_tr['net_c_per_trade']:.2f} -> "
              f"holdout {m_ho['net_c_per_trade']:.2f} c/trade")
    res = pd.DataFrame(rows)
    with open(os.path.join(OUT, f"step7_{kind}.pkl"), "wb") as f:
        pickle.dump(res, f)
    return res


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "prep"
    views, markets = get_views()
    if cmd == "prep":
        print(f"OK {len(views)} views")
    elif cmd == "step5":
        t, slip, sp, se, fn = step5(views, markets)
        print("\n=== STEP 5 (training set) ===")
        print(t.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
        print("\n--- slippage sensitivity, net c/trade ---")
        print(slip.to_string(float_format=lambda x: f"{x:.2f}"))
    elif cmd == "step6":
        kind = sys.argv[2] if len(sys.argv) > 2 else "s3"
        oat, grid = step6(views, markets, kind)
        print(oat.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
