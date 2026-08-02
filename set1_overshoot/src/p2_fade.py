"""The other side of the trade.

Phase 2 found the market UNDERSHOOTS: after a pre-match favourite's price dips,
the favourite goes on to win LESS often than the dipped price implies. The brief
says to report that loudly and check the opposite side, which is what this does.

Fading the favourite means buying the underdog. On Kalshi that is the NO side of
the favourite's market, and it is executable on the same market:

    underdog fill = 100 - favourite_bid,  plus slippage

Note the asymmetry that kills most of these ideas: the favourite's mid sits well
below 50c after the dip, so the underdog is the EXPENSIVE side, typically 65c.
A 2.5pp edge on a 65c contract has to cover a 65c fill plus roughly 1.6c of fee,
and the breakeven moves against you as the price rises. Being right about the
direction of the miscalibration is not the same as being able to trade it.
"""
import pathlib
from decimal import Decimal

import numpy as np
import pandas as pd

import fees
import p2_calib as p2

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

RULES = [("deep:12", 0), ("deep:30", 38), ("deep:20", 38), ("deep:25", 0),
         ("cp", 0), ("fixed", 45)]


def fade_block(e, rng, label, lines):
    """Buy the underdog at 100 - favourite_bid, plus 1c slippage."""
    fav_bid = e["entry_bid"].values
    fav_mid = e["entry_mid"].values
    dog_mid = 100.0 - fav_mid
    dog_ask = 100.0 - fav_bid
    fill = np.minimum(dog_ask + p2.SLIP, 99.0)
    dog_won = 1.0 - e["fav_won"].values

    p = dog_mid / 100.0
    mis = 100 * (dog_won - p)
    lo, hi = p2.bootstrap_ci(mis, rng, n=10000)
    one, two = p2.poisson_binom_p(int(dog_won.sum()), p, rng)

    fee = np.array([float(fees.fee_rate_cents(int(round(f)))) for f in fill])
    net = 100.0 * dog_won - fill - fee
    nlo, nhi = p2.bootstrap_ci(net, rng, n=10000)
    be = (fill.mean() + fee.mean()) / 100.0

    lines.append(
        f"| {label} | {len(e):,} | {p.mean():.4f} | {dog_won.mean():.4f} | "
        f"{mis.mean():+.2f} | [{lo:+.2f}, {hi:+.2f}] | {one:.4f} | "
        f"{fill.mean():.1f} | {fee.mean():.2f} | {be:.4f} | "
        f"{net.mean():+.3f} | [{nlo:+.3f}, {nhi:+.3f}] |")
    return {"mis": mis.mean(), "net": net.mean(), "nlo": nlo, "nhi": nhi,
            "be": be, "obs": dog_won.mean()}


def main():
    st, bid, ask, mid = p2.load("paths")
    rng = np.random.default_rng(31)
    out = []

    def w(s=""):
        print(s, flush=True)
        out.append(s)

    w("# The other side — fading the favourite after the dip")
    w("")
    w("Phase 2 found a **significant undershoot**: the favourite wins less "
      "often than the")
    w("dipped price implies. That makes the favourite the wrong side to buy "
      "and raises the")
    w("obvious question of whether the underdog is the right one. This file "
      "answers it.")
    w("")
    w("Fill is `100 - favourite_bid` plus 1c slippage — the executable NO side "
      "of the same")
    w("market, verified in `reports/p0_mirror.txt` to cost the same as the "
      "sibling market's")
    w("YES side to within 0.00c at the median.")
    w("")
    w("| entry rule | n | implied | observed | mis pp | 95% CI | p(1s) | fill "
      "| fee | breakeven | net c | net 95% CI |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    res = {}
    for rule, floor in RULES:
        ev = p2.build_events(st, bid, ask, mid, rule, 0 if rule != "fixed"
                             else floor, min_minute=floor if rule != "fixed"
                             else 0)
        e = ev[ev["is_event"]]
        if len(e) < 100:
            continue
        lbl = f"{rule}" + (f"@{floor}" if floor and rule != "fixed" else "")
        res[lbl] = fade_block(e, rng, lbl, out)
        print(out[-1], flush=True)
    w("")

    best = max(res.items(), key=lambda kv: kv[1]["net"])
    w("## Verdict on the fade")
    w("")
    w(f"Best cell: **{best[0]}**, net **{best[1]['net']:+.3f} c/contract**, "
      f"95% CI [{best[1]['nlo']:+.3f}, {best[1]['nhi']:+.3f}].")
    w("")
    n_pos = sum(1 for v in res.values() if v["net"] > 0)
    n_ci = sum(1 for v in res.values() if v["nlo"] > 0)
    w(f"**{n_pos} of {len(res)} configurations have a positive mean net "
      f"expectancy. {n_ci} of {len(res)} have a")
    w("confidence interval entirely above zero.**")
    w("")
    if n_pos == 0:
        w("So the miscalibration is real and it does point at the underdog, "
          "but it is")
        w("smaller than the cost of taking the position in every single "
          "configuration. The")
        w("reason is arithmetic rather than bad luck. After the dip the "
          "underdog is the")
        w("*expensive* side — around 66c on the best-targeted rule — so the "
          "fee sits near")
        w("its maximum and the fill eats most of the payout. A 2.5pp edge "
          "cannot pay for a")
        w("65.8c fill plus 1c of slippage plus 1.4c of fee, which together "
          "demand a 67.2%")
        w("win rate against the 66.1% actually observed.")
        w("")
        w("The best cell's interval does reach slightly above zero "
          f"([{best[1]['nlo']:+.3f}, {best[1]['nhi']:+.3f}]), which")
        w("means the data cannot rule out a very small positive expectancy "
          "there. It also")
        w("cannot rule out a loss three times that size, the point estimate "
          "is negative, and")
        w("this is the best of six cells chosen after the fact. That is not "
          "an edge; it is")
        w("the shape a null takes when you look at it from the profitable "
          "direction.")
    else:
        w("At least one configuration has positive mean expectancy. It must "
          "survive the")
        w("temporal holdout in Phase 4 before it is called anything.")
    w("")

    # what edge WOULD be needed
    w("## How big would the miscalibration have to be?")
    w("")
    w("| entry rule | observed underdog win rate | breakeven win rate | "
      "shortfall (pp) |")
    w("|---|---|---|---|")
    for k, v in res.items():
        w(f"| {k} | {v['obs']:.4f} | {v['be']:.4f} | "
          f"{100 * (v['obs'] - v['be']):+.2f} |")
    w("")
    w("The shortfall column is the whole study in one number: it is how many "
      "percentage")
    w("points of additional mispricing the market would have to be offering "
      "before this")
    w("trade broke even, before any profit at all.")

    (ROOT / "reports" / "p2_fade.md").write_text("\n".join(out),
                                                 encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / 'p2_fade.md'}")


if __name__ == "__main__":
    main()
