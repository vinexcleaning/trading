"""
t3b_proxy.py - TASK 3, second arm. Covering ITF.

t3_replay.py runs the real entry rule against real set scores, and that is the
better test - but `backtest/data/sofascore_matches.jsonl` contains ATP,
Challenger and WTA and **no ITF whatsoever**. ITF is ~76% of Kalshi's tennis
book and 64 of the 108 matches the bot actually traded live. A decisive test
that cannot see ITF is not decisive.

So this arm replaces the score gate with a PRICE PROXY and runs on all 13,658
market views:

    "a set has resolved and my player is ahead on it"
        ->  the mid has climbed at least `climb` cents above the opening line

and validates the proxy where truth exists: the same proxy arm is run on the
ATP/Challenger/WTA subset that HAS scores, and compared against t3_replay's
true-score result on the same markets. If proxy and truth agree there, the
proxy's ITF numbers are worth something. If they do not, that is the finding
and the ITF question stays open.

Everything else is identical to t3_replay: the same Config objects, the same
price band and spread gates read off the Config, engine._walk for execution
and exits, one position per event, the same portfolio cap.
"""
from __future__ import annotations
import sys, os, json, pickle, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "..", "..", "kalshi-inplay-bot", "backtest"))
BOT = os.path.dirname(BT)
for p in (BT, BOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import pandas as pd
import engine
from engine import _walk
import tennis_engine as te
import strategies as st
from t3_replay import NIGHT, CURRENT, VARIANTS, SLIP, load_all

pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 400)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")

CLIMB = 10.0        # cents above the open that stand in for "won a set and ahead"


def replay_proxy(views, cfg, climb=CLIMB, restrict=None, tiers=None):
    cand = []
    for v in views:
        if np.isnan(v.settlement) or v.live.sum() < 10:
            continue
        if restrict is not None and v.event not in restrict:
            continue
        if tiers is not None and v.tournament not in tiers:
            continue
        opened = float(v.mid[0])
        fav = opened >= cfg.favorite_threshold
        hi = cfg.max_favorite_price if fav else cfg.max_divergence_price
        ok = (v.live
              & (v.spread <= cfg.max_spread)
              & (v.ask_close >= cfg.min_entry_price)
              & (v.ask_close < hi)
              & ((v.mid - opened) >= climb))     # the proxy for "ahead on sets"
        for i in np.flatnonzero(ok):
            if i + 1 >= v.n:
                continue
            cand.append((int(v.ts[i]), v, i, fav))

    cand.sort(key=lambda x: x[0])
    busy, last_exit, nre = {}, {}, {}
    open_until, trades = [], []
    for ets, v, i, fav in cand:
        open_until = [x for x in open_until if x > ets]
        if len(open_until) >= cfg.max_open_positions:
            continue
        if ets < busy.get(v.event, 0):
            continue
        if v.event in last_exit:
            if nre.get(v.event, 0) >= cfg.max_reentries_per_event:
                continue
            if ets - last_exit[v.event] < cfg.reentry_cooldown_sec:
                continue
            if cfg.reentry_respects_price_floor and \
                    round(v.ask_close[i]) < cfg.min_entry_price:
                continue
        e = engine._enter(v, i + 1, SLIP)
        if e is None:
            continue
        px, _ = e
        qty = max(1, int((cfg.bankroll * cfg.stake_pct / 100) / (px / 100)))
        qty = min(qty, cfg.max_contracts)
        if fav:
            target = float(cfg.favorite_target_price)
            stop = max(1.0, px - cfg.favorite_exit_drop)
        else:
            target = min(99.0, px + 15.0)
            stop = max(1.0, round(px * (1 - cfg.divergence_exit_pct)))
        tl = cfg.max_hold_minutes if cfg.max_hold_minutes > 0 else None
        t = _walk(v, i + 1, px, qty, target, stop, SLIP, tl, None)
        if t is None:
            continue
        t.spread = float(v.spread[i])
        trades.append(t)
        open_until.append(t.exit_ts)
        busy[v.event] = t.exit_ts
        if v.event in last_exit:
            nre[v.event] = nre.get(v.event, 0) + 1
        last_exit[v.event] = t.exit_ts
    return trades


def summ(trades, label):
    if not trades:
        return {"config": label, "trades": 0}
    df = pd.DataFrame([t.__dict__ for t in trades])
    df["net_c"] = df.net / df.contracts * 100.0
    pm = df.groupby("event").net.sum()
    se = pm.std(ddof=1) / math.sqrt(len(pm)) if len(pm) > 1 else np.nan
    return {"config": label, "trades": len(df), "matches": df.event.nunique(),
            "tr_per_match": len(df) / df.event.nunique(),
            "win_rate": (df.net > 0).mean() * 100,
            "net_$": df.net.sum(), "net_c_per_trade": df.net_c.mean(),
            "net_$_per_match": pm.mean(), "se_$_per_match": se,
            "t_match": pm.mean() / se if se else np.nan,
            "avg_entry": df.entry.mean()}


if __name__ == "__main__":
    views, markets, scores = load_all()
    tr, ho = st.split(views, markets)
    tr_ev = {v.event for v in tr}
    ho_ev = {v.event for v in ho}

    tours = sorted({v.tournament for v in views})
    print(f"tournaments in the candle data: {tours}")
    cnt = pd.Series([v.tournament for v in views]).value_counts()
    print(cnt.to_string())
    sc_tours = pd.Series([r.get("tournament") for r in scores.values()]).value_counts()
    print(f"\ntournaments in the SCORE file: {sc_tours.to_dict()}")
    print("-> ITF has no score coverage at all. That is why this arm exists.")

    SCORED = {"ATP", "Challenger", "WTA"}
    ITF = {t for t in tours if t.startswith("ITF")}

    rows = []
    for label, cfg in VARIANTS.items():
        for scope, restrict, tiers in (
                ("ALL tiers", None, None),
                ("ITF only", None, ITF),
                ("ATP/Ch/WTA", None, SCORED),
                ("ITF HOLDOUT", ho_ev, ITF),
                ("ALL HOLDOUT", ho_ev, None)):
            t = replay_proxy(views, cfg, restrict=restrict, tiers=tiers)
            r = summ(t, f"{label} [{scope}]")
            rows.append(r)
            print(f"  {label:34s} {scope:12s} -> {r.get('trades',0):6d} tr / "
                  f"{r.get('matches',0):5d} m  "
                  f"{r.get('net_c_per_trade', float('nan')):+.2f} c/trade  "
                  f"{r.get('net_$_per_match', float('nan')):+.3f} $/match")
    T = pd.DataFrame(rows)
    print()
    print("=" * 78)
    print("TASK 3b - price-proxy arm, all 13,658 views including ITF")
    print("=" * 78)
    print(T.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    T.to_csv(os.path.join(OUT, "t3b_proxy.csv"), index=False)

    # --- proxy validation ------------------------------------------------
    print()
    print("=" * 78)
    print("PROXY VALIDATION - proxy vs true scores on the SAME markets")
    print("=" * 78)
    try:
        true = pd.read_csv(os.path.join(OUT, "t3_replay.csv"))
        for label in VARIANTS:
            a = true[true.config == f"{label} [ALL]"]
            b = T[T.config == f"{label} [ATP/Ch/WTA]"]
            if len(a) and len(b) and a.iloc[0].get("trades"):
                print(f"{label:34s} true-score {a.iloc[0].net_c_per_trade:+6.2f}  "
                      f"proxy {b.iloc[0].net_c_per_trade:+6.2f}  "
                      f"delta {b.iloc[0].net_c_per_trade - a.iloc[0].net_c_per_trade:+6.2f} c")
    except FileNotFoundError:
        print("run t3_replay.py first")
    print()
    print("The proxy arm runs on every ATP/Ch/WTA market; the true-score arm only")
    print("on the ~1,400 with a Sofascore join. They are not the same sample, so")
    print("the delta mixes proxy error with sample difference. Read it as a")
    print("sanity check on sign and magnitude, not as a calibration constant.")

    # --- sensitivity to the proxy threshold ------------------------------
    print()
    print("--- sensitivity: NIGHT config, ITF only, by climb threshold")
    for c in (0, 5, 10, 15, 20, 30):
        t = replay_proxy(views, NIGHT, climb=c, tiers=ITF)
        r = summ(t, f"climb>={c}")
        print(f"  climb >= {c:2d}c : {r.get('trades',0):6d} trades  "
              f"{r.get('net_c_per_trade', float('nan')):+.2f} c/trade  "
              f"{r.get('net_$_per_match', float('nan')):+.3f} $/match  "
              f"t={r.get('t_match', float('nan')):+.2f}")
