"""
strategies.py - the five strategies, plus metrics and the train/holdout split.

Every strategy is a generator of candidate signals; execution and exits are
handled by engine._walk so the fee/slippage/tie-break rules are identical
across all of them.

Dedup: the two markets in a match are near-perfect price inverses, so a
signal can fire on both sides of the same event. At most one position per
EVENT may be open at any instant, and metrics report distinct matches
alongside trade count so the sample is not counted twice.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine import (MarketView, Trade, _enter, _walk, deltas, range_5m,
                    structural, NOTIONAL)


@dataclass
class Params:
    window: int = 1           # measurement window in minutes (60s ~ spec's 45s)
    thresh: float = 12.0      # structural event threshold, cents
    min_price: float = 55.0
    max_price: float = 75.0
    target: float = 15.0
    stop: float = 20.0
    slip: float = 1.0
    time_limit: int | None = 12
    act2_range: float = 30.0  # skip if trailing 5-min range exceeds this
    hold_min: int = 2         # minutes price must hold after the step
    hold_tol: float = 8.0     # max retrace during the hold, cents
    disaster: float = 24.0    # hard floor below entry
    struct_stop: bool = False


def _size(entry: float) -> float:
    return NOTIONAL / (entry / 100.0)


# ------------------------------------------------------------- signal gen
def _event_idx(v: MarketView, p: Params, direction: int) -> np.ndarray:
    """Indices of live candles carrying a structural event in `direction`."""
    d = deltas(v, p.window)
    if direction > 0:
        mask = d >= p.thresh
    else:
        mask = d <= -p.thresh
    return np.flatnonzero(mask & v.live & ~np.isnan(d))


def _signals_s1(v: MarketView, p: Params, funnel: dict) -> list[tuple[int, float]]:
    """Strategy 1/2 entry: upward step, 2-min hold within 8c, price in band."""
    funnel["live"] += int(v.live.sum())
    out = []
    for i in _event_idx(v, p, +1):
        funnel["event"] += 1
        if v.range5[i] > p.act2_range:
            continue
        funnel["act2"] += 1
        j = i + p.hold_min
        if j + 1 >= v.n:
            continue
        if v.mid[i + 1:j + 1].min() < v.mid[i] - p.hold_tol:
            continue
        funnel["hold"] += 1
        e = _enter(v, j + 1, p.slip)          # execute on the NEXT candle
        if e is None:
            continue
        px, _ = e
        if not (p.min_price <= px <= p.max_price):
            continue
        funnel["band"] += 1
        out.append((j + 1, px))
    return out


def _signals_dir(v: MarketView, p: Params, direction: int,
                 funnel: dict) -> list[tuple[int, float]]:
    """Strategy 3/4 entry: structural event, buy on the next candle."""
    funnel["live"] += int(v.live.sum())
    out = []
    for i in _event_idx(v, p, direction):
        funnel["event"] += 1
        funnel["act2"] += 1
        funnel["hold"] += 1
        e = _enter(v, i + 1, p.slip)
        if e is None:
            continue
        px, _ = e
        if not (p.min_price <= px <= p.max_price):
            continue
        funnel["band"] += 1
        out.append((i + 1, px))
    return out


def _signals_random(v: MarketView, p: Params, rng: np.random.Generator,
                    funnel: dict, rate: float) -> list[tuple[int, float]]:
    live_idx = np.flatnonzero(v.live)
    live_idx = live_idx[live_idx < v.n - 1]
    funnel["live"] += len(live_idx)
    picks = live_idx[rng.random(len(live_idx)) <= rate]
    out = []
    for i in picks:
        funnel["event"] += 1
        funnel["act2"] += 1
        funnel["hold"] += 1
        e = _enter(v, i + 1, p.slip)
        if e is None:
            continue
        px, _ = e
        if not (p.min_price <= px <= p.max_price):
            continue
        funnel["band"] += 1
        out.append((i + 1, px))
    return out


# ---------------------------------------------------------------- runner
def run(views: list[MarketView], p: Params, kind: str,
        seed: int = 42, rand_rate: float = 0.004) -> tuple[list[Trade], dict]:
    """Generate signals across all markets, then execute them in time order
    with one-position-per-event enforced."""
    funnel = {"live": 0, "event": 0, "act2": 0, "hold": 0, "band": 0, "taken": 0}
    rng = np.random.default_rng(seed)

    cand: list[tuple[int, MarketView, int, float]] = []
    for v in views:
        if kind in ("s1", "s2"):
            sigs = _signals_s1(v, p, funnel)
        elif kind == "s3":
            sigs = _signals_dir(v, p, -1, funnel)
        elif kind == "s4":
            sigs = _signals_dir(v, p, +1, funnel)
        elif kind == "s5":
            sigs = _signals_random(v, p, rng, funnel, rand_rate)
        else:
            raise ValueError(kind)
        for idx, px in sigs:
            cand.append((int(v.ts[idx]), v, idx, px))

    cand.sort(key=lambda x: x[0])
    busy: dict[str, int] = {}
    trades: list[Trade] = []

    for ets, v, idx, px in cand:
        if ets < busy.get(v.event, 0):
            continue
        c = _size(px)
        if kind == "s2":
            t = _walk(v, idx, px, c, None, None, p.slip, None, None)
        elif kind == "s1":
            t = _walk(v, idx, px, c, px + p.target, px - p.disaster, p.slip,
                      None, (p.window, p.thresh), scale_out=True)
        else:
            t = _walk(v, idx, px, c, px + p.target, px - p.stop, p.slip,
                      p.time_limit, None)
        if t is None:
            continue
        t.spread = float(v.spread[idx])
        trades.append(t)
        busy[v.event] = t.exit_ts
        funnel["taken"] += 1

    return trades, funnel


# --------------------------------------------------------------- metrics
def metrics(trades: list[Trade], label: str = "") -> dict:
    if not trades:
        return {"strategy": label, "trades": 0, "matches": 0, "win_rate": np.nan,
                "avg_win_c": np.nan, "avg_loss_c": np.nan, "gross": 0.0,
                "fees": 0.0, "net": 0.0, "net_c_per_trade": np.nan,
                "net_$_per_trade": np.nan, "max_dd": 0.0}
    df = pd.DataFrame([t.__dict__ for t in trades])
    df["net_c"] = df.net / df.contracts * 100.0
    wins = df[df.net > 0]
    losses = df[df.net <= 0]
    cum = df.sort_values("exit_ts").net.cumsum().to_numpy()
    dd = float((np.maximum.accumulate(cum) - cum).max()) if len(cum) else 0.0
    return {
        "strategy": label,
        "trades": len(df),
        "matches": df.event.nunique(),
        "win_rate": len(wins) / len(df) * 100.0,
        "avg_win_c": wins.net_c.mean() if len(wins) else np.nan,
        "avg_loss_c": losses.net_c.mean() if len(losses) else np.nan,
        "gross": df.gross.sum(),
        "fees": df.fees.sum(),
        "net": df.net.sum(),
        "net_c_per_trade": df.net_c.mean(),
        "net_$_per_trade": df.net.mean(),
        "max_dd": dd,
    }


def by_group(trades: list[Trade], col: str) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame([t.__dict__ for t in trades])
    df["net_c"] = df.net / df.contracts * 100.0
    if col == "spread_bucket":
        df[col] = pd.cut(df.spread, [-0.1, 2, 5, 10, 1e9],
                         labels=["0-2c", "3-5c", "6-10c", "10c+"])
    rows = []
    for k, sub in df.groupby(col, observed=True):
        rows.append({
            col: k, "trades": len(sub), "matches": sub.event.nunique(),
            "win_rate": (sub.net > 0).mean() * 100.0,
            "net": sub.net.sum(), "net_c_per_trade": sub.net_c.mean(),
        })
    return pd.DataFrame(rows).sort_values("net_c_per_trade", ascending=False)


# ------------------------------------------------------------------ split
def split(views: list[MarketView], markets: pd.DataFrame,
          frac: float = 0.60) -> tuple[list[MarketView], list[MarketView]]:
    """Oldest `frac` of MATCHES by close time -> train; newest -> holdout.
    Split on the event so both mirrored markets land on the same side."""
    ev = (markets.groupby("event_ticker").close_ts.max()
          .sort_values())
    n = int(len(ev) * frac)
    train_ev = set(ev.index[:n])
    hold_ev = set(ev.index[n:])
    tr = [v for v in views if v.event in train_ev]
    ho = [v for v in views if v.event in hold_ev]
    return tr, ho
