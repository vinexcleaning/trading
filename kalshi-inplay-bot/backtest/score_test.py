"""
score_test.py — the test the whole project has been waiting for.

Joins real Sofascore set scores to Kalshi minute prices and asks the only
question that matters: when a player has ACTUALLY won a set, is the market
pricing him correctly?

Every earlier backtest used price as a proxy for "he's winning", which is
circular — you cannot find a price-vs-score divergence using price alone.
This uses the real scoreline.

METHOD
    For each candle timestamp we count the sets that had FINISHED by then,
    using boundaries reconstructed from Sofascore set durations. A set counts
    as won by our player if he took more games in it.

    Confidence intervals are computed on ONE OBSERVATION PER MARKET, not per
    minute. 200 minutes inside one match is a single outcome, and treating
    them as 200 independent samples is how a 1.9c edge turns into a fake 8.7c
    one — that mistake was made and caught earlier in this project.

THE BAR
    Realised win rate must beat the price by more than the round-trip cost:
    ~4.1c taker on Kalshi, ~2.9c maker. Below that there is nothing to trade.
"""

from __future__ import annotations

import json
import math
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autoscan import _name_matches      # noqa: E402

COST_TAKER = 4.1
COST_MAKER = 2.9


def load_scores(path="data/sofascore_matches.jsonl") -> dict:
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("boundaries") and r.get("sets"):
                out[r["event"]] = r
    return out


def build(views, markets, scores) -> pd.DataFrame:
    """One row per (market, sampled minute) with the real set score attached."""
    by_ticker = {}
    for _, m in markets.iterrows():
        by_ticker[m.ticker] = m

    rows = []
    for v in views:
        if np.isnan(v.settlement):
            continue
        m = by_ticker.get(v.ticker)
        if m is None:
            continue
        sc = scores.get(m.event_ticker)
        if sc is None:
            continue

        # which side of the Sofascore match is this Kalshi market about?
        player = m.player
        if _name_matches(player, sc.get("home") or ""):
            me, them = "home", "away"
        elif _name_matches(player, sc.get("away") or ""):
            me, them = "away", "home"
        else:
            continue

        bounds = sorted(sc["boundaries"], key=lambda b: b["set"])
        sets = sc["sets"]
        opened = v.mid[0]

        live_idx = np.flatnonzero(v.live)
        if len(live_idx) < 10:
            continue
        for i in live_idx[::10]:            # every 10th live minute
            t = v.ts[i]
            won = lost = 0
            margins = []
            for b in bounds:
                if b["end_ts"] > t:
                    break
                g = sets.get(f"set{b['set']}") or {}
                a, d = g.get(me), g.get(them)
                if a is None or d is None:
                    continue
                if a > d:
                    won += 1
                    margins.append(a - d)
                else:
                    lost += 1
            px = v.mid[i]
            if not (5 <= px <= 95) or v.spread[i] > 3:
                continue
            rows.append({
                "ticker": v.ticker, "tournament": v.tournament,
                "px": px, "opened": opened,
                "sets_won": won, "sets_lost": lost,
                "best_margin": max(margins) if margins else 0,
                "ahead": won > lost,
                "won_a_set": won > 0,
                "underdog": opened < 40,
                "favourite": opened >= 60,
                "settled_yes": v.settlement >= 99.5,
            })
    return pd.DataFrame(rows)


def edge_table(df: pd.DataFrame, by, label: str, min_markets=40) -> None:
    """Market-level edge with a 95% CI. One outcome per market."""
    print(f"\n=== {label} ===")
    out = []
    for key, g in df.groupby(by, observed=True):
        per_mkt = g.groupby("ticker").agg(px=("px", "mean"),
                                          won=("settled_yes", "first"))
        n = len(per_mkt)
        if n < min_markets:
            continue
        p = per_mkt.won.mean()
        avg_px = per_mkt.px.mean()
        se = math.sqrt(max(p * (1 - p), 1e-9) / n)
        edge = p * 100 - avg_px
        out.append({"group": key if not isinstance(key, tuple) else "/".join(map(str, key)),
                    "markets": n, "avg_price": avg_px,
                    "realised_%": p * 100, "edge_c": edge,
                    "ci_lo": edge - 1.96 * se * 100,
                    "ci_hi": edge + 1.96 * se * 100})
    if not out:
        print("  (no group had enough markets)")
        return
    t = pd.DataFrame(out).sort_values("edge_c", ascending=False)
    print(t.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    best = t.iloc[0]
    verdict = ("TRADEABLE" if best.ci_lo > COST_TAKER else
               "maker-only maybe" if best.ci_lo > COST_MAKER else
               "NOT TRADEABLE - CI includes less than the cost of trading")
    print(f"  -> best group ci_lo = {best.ci_lo:+.2f}c   {verdict}")


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    pd.set_option("display.width", 220)

    views, markets = pickle.load(open("data/views.pkl", "rb"))
    scores = load_scores()
    print(f"{len(scores)} matches with usable score data")
    df = build(views, markets, scores)
    print(f"{len(df):,} sampled minutes across {df.ticker.nunique()} markets\n")
    print(f"Bar to clear: edge must exceed {COST_TAKER}c taker "
          f"/ {COST_MAKER}c maker, with the CI low end above it.")

    df["state"] = df.sets_won.astype(str) + "-" + df.sets_lost.astype(str)

    edge_table(df, "state", "1. BY SET SCORE (all markets)")

    edge_table(df[df.underdog], "state",
               "2. THE THESIS: UNDERDOG (opened <40c) BY SET SCORE", min_markets=15)

    edge_table(df[df.favourite], "state",
               "3. FAVOURITE (opened >=60c) BY SET SCORE", min_markets=15)

    up = df[(df.sets_won == 1) & (df.sets_lost == 0)].copy()
    up["px_band"] = pd.cut(up.px, [5, 55, 70, 80, 88, 95])
    edge_table(up, "px_band",
               "2b. UP A SET, BY PRICE - where does the +5c live?", min_markets=25)

    edge_table(up, "tournament",
               "2c. UP A SET, BY TOUR", min_markets=25)

    won = df[df.won_a_set].copy()
    won["margin_band"] = pd.cut(won.best_margin, [0, 1, 2, 3, 6],
                                labels=["won by 1 (tiebreak)", "won by 2",
                                        "won by 3", "won by 4+"])
    edge_table(won, "margin_band", "4. SET QUALITY - does 6-3 beat 7-6?")

    u = df[df.underdog & df.won_a_set].copy()
    u["px_band"] = pd.cut(u.px, [5, 25, 40, 55, 70, 95])
    edge_table(u, "px_band",
               "5. UNDERDOG WHO WON A SET, BY CURRENT PRICE (the exact trade)")


if __name__ == "__main__":
    main()
