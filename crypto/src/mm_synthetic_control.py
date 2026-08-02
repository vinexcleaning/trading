"""MM TASK 5 (run early): synthetic control for the market-making pipeline.

Generate order flow with NO exploitable structure and run the identical fill
model and P&L decomposition used on real data. If it reports profitable market
making where none exists, the pipeline is broken and every MM result is void.

Three arms again, because a control with only the null arm cannot distinguish
"no edge" from "no power":

  A  NULL       trades arrive at random, uncorrelated with future price.
                A maker should earn spread and lose exactly that much to
                adverse selection: NET ~= 0.
  B  BENIGN     trades arrive from uninformed flow (price mean-reverts after).
                A maker SHOULD make money. Tests that the pipeline can see a
                profit when one is really there.
  C  TOXIC      trades are informed (price continues in the taker's direction).
                A maker SHOULD lose. Tests that adverse selection is actually
                being measured rather than assumed away.

Arms B and C matter as much as A: a pipeline that reports ~0 on everything is
as useless as one that reports profit on noise.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from mm_fill_model import simulate, decompose  # noqa: E402


def make_book_v2(n_min=60, n_trades=400, drift_mult=1.0, half_spread=0.005,
                 sigma=0.002, seed=0, close_ts=1_800_000_000):
    """Flow whose informativeness is a CONTROLLED MULTIPLE of the half-spread.

    The first version of this control was mis-specified, and the gate caught
    it. Its "NULL" arm had trades arriving independently of price, which is not
    a null at all — it is a maker's paradise with zero informed flow, where
    earning the full spread is the CORRECT answer. And its "TOXIC" arm moved
    the price by less than the spread, so a maker still profited.

    Correct parameterisation: after a trade, the mid drifts in the aggressor's
    direction by `drift_mult * half_spread`.
        drift_mult = 1.0  -> adverse selection exactly offsets the spread -> NET 0
        drift_mult < 1.0  -> maker profits
        drift_mult > 1.0  -> maker loses
    That is the textbook efficient-market null for a market maker, and it makes
    the expected answer for each arm known in advance.
    """
    rng = np.random.default_rng(seed)
    start_ts = close_ts - n_min * 60

    # Each minute has a move of magnitude drift_mult*half_spread and random
    # sign. ALL trades inside a minute take the side that PROFITS from that
    # move — i.e. flow is informed and ONE-SIDED, which is what makes it toxic.
    #
    # The previous attempt drew each trade's side independently, so buys and
    # sells offset inside every minute, the maker filled both sides (99.79%)
    # and was perfectly hedged. A hedged maker cannot be adversely selected,
    # so adverse selection measured ~0 regardless of the arm. Real toxic flow
    # is one-directional; that is the whole mechanism.
    step = drift_mult * half_spread
    signs = np.where(rng.random(n_min) < 0.5, 1.0, -1.0)
    mid = np.empty(n_min)
    mid[0] = 0.5
    for i in range(1, n_min):
        mid[i] = mid[i - 1] + signs[i - 1] * step + rng.normal(0, sigma)
    mid = np.clip(mid, 0.10, 0.90)

    quotes = [{"ts": start_ts + i * 60,
               "bid": round(float(mid[i]) - half_spread, 4),
               "ask": round(float(mid[i]) + half_spread, 4),
               "vol": 0.0} for i in range(n_min)]

    trade_ts = np.sort(rng.uniform(start_ts, close_ts, n_trades))
    trades = []
    for t in trade_ts:
        i = min(n_min - 1, max(0, int((t - start_ts) // 60)))
        # price about to RISE -> informed taker BUYS -> lifts our ask
        s = "ask" if signs[i] > 0 else "bid"
        m = float(mid[i])
        px = round(m + half_spread, 4) if s == "ask" else round(
            m - half_spread, 4)
        trades.append({"ts": float(t), "px": px,
                       "sz": float(rng.integers(1, 40)),
                       "taker_book_side": s, "block": False})
    return quotes, trades, close_ts, float(mid[-1])


def make_book(n_min=60, n_trades=400, arm="NULL", sigma=0.004,
              drift_after=0.0, seed=0, close_ts=1_800_000_000):
    """Synthetic per-minute quotes + a trade tape with known structure."""
    rng = np.random.default_rng(seed)
    start_ts = close_ts - n_min * 60

    # random-walk mid, clipped away from the boundaries
    steps = rng.normal(0, sigma, n_min)
    mid = 0.5 + np.cumsum(steps)
    mid = np.clip(mid, 0.10, 0.90)
    quotes = []
    for i in range(n_min):
        m = float(mid[i])
        b = round(m - 0.005, 4)
        a = round(m + 0.005, 4)
        quotes.append({"ts": start_ts + i * 60, "bid": b, "ask": a,
                       "vol": 0.0})

    # trades arrive uniformly; aggressor side depends on the arm
    trades = []
    for _ in range(n_trades):
        t = float(rng.uniform(start_ts, close_ts))
        i = min(n_min - 1, max(0, int((t - start_ts) // 60)))
        m = float(mid[i])
        future = float(mid[min(n_min - 1, i + 1)])
        if arm == "NULL":
            side = "bid" if rng.random() < 0.5 else "ask"
        elif arm == "TOXIC":
            # taker trades in the direction the price is ABOUT to move
            side = "ask" if future > m else "bid"
        else:  # BENIGN — taker trades against the next move
            side = "bid" if future > m else "ask"
        px = round(m - 0.005, 4) if side == "bid" else round(m + 0.005, 4)
        trades.append({"ts": t, "px": px, "sz": float(rng.integers(1, 40)),
                       "taker_book_side": side, "block": False})
    trades.sort(key=lambda x: x["ts"])
    return quotes, trades, close_ts


def run_arm(label, drift_mult, n_markets=120, latency=0.373, seed0=100):
    """Each market is decomposed SEPARATELY and marked at its own terminal
    mid, then pooled. Pooling fills across markets before marking would net
    one market's long against another's short, which is not a position anyone
    holds."""
    opps = []
    per_market = []
    for k in range(n_markets):
        q, t, close_ts, term = make_book_v2(drift_mult=drift_mult,
                                            seed=seed0 + k)
        o, f = simulate(q, t, settle_y=0.0, close_ts=close_ts,
                        latency_s=latency, queue_ahead=0.0,
                        half_spread=0.005)
        opps.extend(o)
        d = decompose(f, terminal_mark=term)
        if d:
            per_market.append(d)
    nfill = sum(1 for o in opps if o["filled_bid"] > 0 or o["filled_ask"] > 0)
    if not per_market:
        return {"arm": label, "opportunities": len(opps), "decomp": None}
    w = np.array([d["contracts"] for d in per_market])
    agg = {k: float(np.average([d[k] for d in per_market], weights=w))
           for k in ("spread_per_contract", "adverse_per_contract",
                     "fee_per_contract", "inventory_per_contract",
                     "net_per_contract")}
    agg["contracts"] = float(w.sum())
    return {"arm": label, "drift_mult": drift_mult,
            "opportunities": len(opps), "filled_opps": nfill,
            "fill_rate": nfill / max(1, len(opps)), "decomp": agg,
            "n_markets": len(per_market)}


def main():
    print("=" * 100)
    print("MM SYNTHETIC CONTROL — does the pipeline report profit where none "
          "exists?")
    print("=" * 100)
    print("  120 synthetic markets/arm, 60 min each, 400 trades each")
    print("  latency 373 ms (measured), queue_ahead 0, half-spread 0.5c")
    print("  NOTE: zero fees applied — Kalshi crypto maker fee is zero\n")
    print(f"  {'arm':<20} {'drift':>6} {'fill%':>7} {'contracts':>10} "
          f"{'spread':>8} {'adverse':>8} {'invent':>8} {'NET c/ct':>9} "
          f"{'expected':>22}")
    out = []
    arms = [("BENIGN drift=0.3x", 0.3, "NET > 0"),
            ("NULL   drift=1.0x", 1.0, "NET ~ 0"),
            ("TOXIC  drift=2.0x", 2.0, "NET < 0")]
    for label, dm, exp in arms:
        r = run_arm(label, dm)
        d = r["decomp"]
        if d:
            print(f"  {label:<20} {dm:>6.1f} {r['fill_rate']*100:>6.2f}% "
                  f"{d['contracts']:>10.0f} "
                  f"{d['spread_per_contract']:>+8.4f} "
                  f"{d['adverse_per_contract']:>+8.4f} "
                  f"{d['inventory_per_contract']:>+8.4f} "
                  f"{d['net_per_contract']:>+9.4f} {exp:>22}")
        else:
            print(f"  {label:<20} no fills")
        out.append(r)

    print("\n" + "=" * 100)
    print("GATE VERDICTS")
    print("=" * 100)
    net = [(r["arm"], r["decomp"]["net_per_contract"] if r["decomp"] else None)
           for r in out]
    benign, null_, toxic = net[0][1], net[1][1], net[2][1]
    ok_benign = benign is not None and benign > 0
    ok_null = null_ is not None and abs(null_) < 0.15
    ok_toxic = toxic is not None and toxic < 0
    ordered = (None not in (benign, null_, toxic)
               and toxic < null_ < benign)
    print(f"  BENIGN : net > 0       -> "
          f"{'PASS' if ok_benign else '*** FAIL — blind to real maker profit'}"
          f"  (net = {benign:+.4f}c)")
    print(f"  NULL   : |net| < 0.15c -> "
          f"{'PASS' if ok_null else '*** FAIL — profit where none exists'}"
          f"  (net = {null_:+.4f}c)")
    print(f"  TOXIC  : net < 0       -> "
          f"{'PASS' if ok_toxic else '*** FAIL — adverse selection not measured'}"
          f"  (net = {toxic:+.4f}c)")
    print(f"  ORDERING : TOXIC < NULL < BENIGN -> "
          f"{'PASS' if ordered else '*** FAIL'}")
    gate = ok_null and ok_benign and ok_toxic and ordered
    print(f"\n  OVERALL GATE: "
          f"{'PASS — MM results may be trusted' if gate else '*** FAIL — MM results are VOID'}")

    json.dump({"arms": out, "gate": {"null": bool(ok_null),
                                     "benign": bool(ok_benign),
                                     "toxic": bool(ok_toxic),
                                     "ordering": bool(ordered),
                                     "overall": bool(gate)}},
              open(r"C:\Users\gianf\crypto\reports\mm_synthetic_control.json",
                   "w"), indent=2, default=str)


if __name__ == "__main__":
    main()
