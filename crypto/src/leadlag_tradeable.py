"""Is the 1-second lead-lag big enough to trade on Kalshi? The decisive number.

A statistically real lead is not a trade. Converting it requires four things to
survive, in order:

  1. DECAY      how much of the signal is left after our 373 ms latency?
  2. SIZE       what fraction of the next second's move is predictable?
  3. CONVERSION how much does that move the Kalshi contract price?
                a binary's sensitivity is dP/dS = phi(d2) / (S * sigma * sqrt(tau))
  4. COST       is what's left bigger than the 1c tick and the ~1.75c fee?

Anything smaller than one tick cannot be expressed as a trade at all, however
significant it is.
"""
import json
import math
import os
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
from fees import kalshi_fee_per_contract_unrounded  # noqa: E402
from leadlag import load, align, xcorr  # noqa: E402

OUT = r"C:\Users\gianf\crypto\reports"
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]

# Kalshi crypto binaries we could actually trade on this signal
CONTRACTS = [
    # name,        spot,     ann_vol, minutes_to_expiry, tick
    ("KXBTC15M @7.5m", 62900.0, 0.435, 7.5, 0.01),
    ("KXBTC15M @2m", 62900.0, 0.435, 2.0, 0.01),
    ("KXETH15M @7.5m", 1865.0, 0.566, 7.5, 0.01),
    ("KXBTCD  @30m", 62900.0, 0.435, 30.0, 0.01),
]

SEC_PER_YEAR = 365.25 * 86400.0


def dP_dS(S, sigma_ann, minutes):
    """At-the-money binary sensitivity to spot, per $1 of underlying."""
    tau = (minutes * 60.0) / SEC_PER_YEAR
    v = sigma_ann * math.sqrt(tau)
    # at the money d2 = -v/2
    return stats.norm.pdf(-v / 2.0) / (S * v)


def main():
    series = {}
    for s in SYMS:
        r = load(s)
        if r is not None:
            series[s] = r
    common, al = align(series)
    rets, vols = {}, {}
    for s, (px, vol) in al.items():
        rets[s] = np.diff(np.log(px))
        vols[s] = vol[1:]
    n = len(next(iter(rets.values())))

    print("=" * 100)
    print("1. SIGNAL DECAY — how fast does the lead die?")
    print("=" * 100)
    pairs = [("ETHUSDT", "XRPUSDT"), ("ETHUSDT", "DOGEUSDT"),
             ("ETHUSDT", "SOLUSDT"), ("BTCUSDT", "XRPUSDT")]
    decay = {}
    print(f"  {'pair':<16} " + " ".join(f"{l:>7}s" for l in range(1, 9)))
    for a, b in pairs:
        m = (vols[a] > 0) & (vols[b] > 0)
        xs = dict(xcorr(rets[a][m], rets[b][m], 10))
        decay[f"{a[:3]}->{b[:3]}"] = {l: xs[l] for l in range(1, 11)}
        print(f"  {a[:3]+'->'+b[:3]:<16} " +
              " ".join(f"{xs[l]:+8.4f}" for l in range(1, 9)))
    print("\n  our latency is 373 ms, so we can only act on the portion of the")
    print("  signal remaining AFTER the first second has already elapsed.")

    print("\n" + "=" * 100)
    print("2. SIZE — predictable fraction of the next second's move")
    print("=" * 100)
    print(f"  {'asset':<10} {'1s return sd':>14} {'in $ / in %':>20}")
    sd = {}
    for s in series:
        m = vols[s] > 0
        sd[s] = float(np.std(rets[s][m]))
        px = float(al[s][0][-1])
        print(f"  {s:<10} {sd[s]*100:>13.5f}% "
              f"{'$'+format(sd[s]*px, '.3f'):>20}")

    print("\n" + "=" * 100)
    print("3+4. CONVERSION AND COST — the decisive table")
    print("=" * 100)
    print("  Signal: observe the leader's 1s move, predict the follower's next")
    print("  1s move as corr * sd. Convert to contract cents via dP/dS.\n")
    print(f"  {'contract':<18} {'signal pair':<14} {'corr':>7} "
          f"{'pred move $':>12} {'dP/dS c/$':>11} {'edge c':>8} "
          f"{'tick c':>7} {'fee c':>7} {'verdict':>16}")
    rows = []
    for name, S, av, mins, tick in CONTRACTS:
        d = dP_dS(S, av, mins) * 100.0        # cents per $1 of spot
        # use the strongest clean lead as the most favourable case
        for a, b in [("ETHUSDT", "XRPUSDT"), ("BTCUSDT", "XRPUSDT")]:
            key = f"{a[:3]}->{b[:3]}"
            c = decay[key][1]
            # follower's own 1s sd, in dollars of ITS OWN price
            fol_px = float(al[b][0][-1])
            pred_ret = c * sd[b]
            # express in the CONTRACT's underlying: the contract is on the
            # asset whose name matches; use the follower's predicted return
            # applied to the contract's spot
            pred_dollars = pred_ret * S
            edge_c = pred_dollars * d
            fee_c = float(kalshi_fee_per_contract_unrounded("0.50")) * 100
            vd = ("TRADEABLE" if edge_c > tick * 100 + fee_c
                  else ("< tick" if edge_c < tick * 100 else "< tick+fee"))
            print(f"  {name:<18} {key:<14} {c:>7.4f} "
                  f"{pred_dollars:>12.3f} {d:>11.5f} {edge_c:>8.4f} "
                  f"{tick*100:>7.2f} {fee_c:>7.2f} {vd:>16}")
            rows.append({"contract": name, "pair": key, "corr": c,
                         "edge_c": edge_c, "tick_c": tick * 100,
                         "fee_c": fee_c})
        print()

    print("=" * 100)
    print("5. HOW BIG WOULD THE CORRELATION HAVE TO BE?")
    print("=" * 100)
    for name, S, av, mins, tick in CONTRACTS[:2]:
        d = dP_dS(S, av, mins) * 100.0
        fee_c = float(kalshi_fee_per_contract_unrounded("0.50")) * 100
        need_c = tick * 100 + fee_c
        # edge_c = corr * sd_follower * S * d  -> solve for corr
        s_ = sd["XRPUSDT"]
        need_corr = need_c / (s_ * S * d)
        best = decay["ETH->XRP"][1]
        print(f"  {name:<18} needs corr >= {need_corr:8.3f} "
              f"to clear tick+fee ({need_c:.2f}c); "
              f"observed best = {best:.4f}  -> "
              f"short by {need_corr/max(best,1e-9):.0f}x")

    json.dump({"decay": {k: {str(kk): vv for kk, vv in v.items()}
                         for k, v in decay.items()},
               "sd": sd, "rows": rows},
              open(os.path.join(OUT, "leadlag_tradeable.json"), "w"),
              indent=2, default=str)


if __name__ == "__main__":
    main()
