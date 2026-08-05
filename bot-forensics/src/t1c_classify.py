"""
t1c_classify.py - a bot/manual classifier that does not depend on notional.

t1_ledger.py split on order notional and got SHIDON wrong: a hand-placed 6c
longshot on the NO side cost $0.93, so it looked like a bot-sized order, and it
returned +$14.51 - half the apparent bot total. A rule that misfires that
expensively on the largest single winner is not a rule.

Three structural signatures, none of which can see the outcome:

  R1  SIDE.      The engine only ever buys YES. Every `buy no` is manual.
  R2  PRICE.     Manual buys are marketable limits typed at 0.99 (or 0.01 for
                 a longshot). The engine posts a limit at the ask, inside the
                 60-85c band. Anything at 0.99 or below 0.10 is manual.
  R3  SIZE.      qty = max(1, int(stake / price)) for ONE stake, all day.
                 On 28 Jul this reproduces 113 of 113 order sizes at
                 stake = $6.25.

R3 is the discriminating one and is checked here against every stake on a
grid, per day, so the stake is measured rather than assumed.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import load

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 400)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")

O = load.orders()
B = O[O.action == "buy"].copy()
B["cents"] = (B.px * 100).round().astype(int)
B["day"] = B.t.dt.floor("D")

print("=" * 78)
print("R1/R2  side and price of every BUY order")
print("=" * 78)
print(pd.crosstab(B.day, B.side))
print()
print("buy price histogram, by day (cents):")
print(pd.crosstab(B.day, pd.cut(B.cents, [0, 9, 59, 74, 89, 98, 100],
                                labels=["1-9", "10-59", "60-74", "75-89",
                                        "90-98", "99"])))

# --- R3: measure the stake -------------------------------------------
print()
print("=" * 78)
print("R3  stake that reproduces the size, on buy/yes orders priced 10-90c")
print("=" * 78)
cand = B[(B.side == "yes") & (B.cents >= 10) & (B.cents <= 90)].copy()
for d, g in cand.groupby("day"):
    rows = []
    for stake in np.arange(3.0, 40.01, 0.05):
        pred = np.maximum(1, (stake / g.px).astype(int))
        rows.append(((pred == g.initial.round()).mean(), stake))
    rows.sort(reverse=True)
    print(f"{d.date()}  n={len(g):3d}  best: "
          + "   ".join(f"${s:.2f} -> {h:.0%}" for h, s in rows[:3]))

STAKE = 6.25
cand["pred"] = np.maximum(1, (STAKE / cand.px).astype(int))
cand["size_ok"] = cand.pred == cand.initial.round()
print()
print(f"orders where int({STAKE}/px) != qty, on buy/yes 10-90c:")
print(cand[~cand.size_ok][["t", "ticker", "cents", "initial", "pred", "filled",
                           "status"]].to_string(index=False))

# --- the rule ---------------------------------------------------------
B["bot"] = (
    (B.side == "yes")
    & (B.cents >= 10) & (B.cents <= 90)
    & (np.maximum(1, (STAKE / B.px).astype(int)) == B.initial.round())
)
print()
print("=" * 78)
print("CLASSIFIER OUTPUT")
print("=" * 78)
print(pd.crosstab(B.day, B.bot))
print()
print("manual buys that survive (should be hand trades only):")
mb = B[~B.bot]
print(mb.groupby("day").agg(n=("initial", "size"),
                            notional=(("initial"), lambda s: 0)).n.to_string())
print()
print(mb[["t", "ticker", "side", "cents", "initial"]].to_string(index=False))

# --- ticker-level class, and where it disagrees with the notional rule
B["notional"] = B.initial * B.px
old = B.groupby("ticker").apply(
    lambda g: "bot" if (g.notional <= 7.5).all() else
              ("manual" if (g.notional > 7.5).all() else "mixed"),
    include_groups=False)
new = B.groupby("ticker").apply(
    lambda g: "bot" if g.bot.all() else ("manual" if (~g.bot).all() else "mixed"),
    include_groups=False)
cmp = pd.DataFrame({"notional_rule": old, "structural_rule": new})
print()
print("agreement between the two rules, at ticker level:")
print(pd.crosstab(cmp.notional_rule, cmp.structural_rule))
print()
print("tickers they disagree on:")
print(cmp[cmp.notional_rule != cmp.structural_rule].to_string())

new.rename("klass").to_csv(os.path.join(OUT, "ticker_class.csv"))
print(f"\nwritten: out/ticker_class.csv  ({new.value_counts().to_dict()})")
