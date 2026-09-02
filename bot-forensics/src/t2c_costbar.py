"""
t2c_costbar.py - the cost bar per bucket, and a permutation test that does not
assume normality at n=5.

TWO FIXES TO t2b:

(a) The three BH "discoveries" all sit on n=4-6, and they are not independent
    tests - the 04-07 UTC block and the Challenger|night cell are largely the
    SAME five or six matches viewed twice. A t-statistic on five observations
    with a 100% win rate is not evidence. Replaced here with a label
    permutation: shuffle the bucket labels across all 108 matches 200,000
    times and ask how often a bucket of that size reaches that total.

(b) TASK 2 requires the cost bar PER BUCKET, not pooled. Spread and fee both
    vary by tier and by hour. Measured directly from the recorder tapes
    (tennis_data.jsonl 7,170 rows + tennis_data_laptop.jsonl 27,083 rows,
    27-28 Jul, the same window the bot traded), restricted to the price band
    the bot actually entered in.

    cost bar per round trip, in cents per contract
        = spread (cross to buy, cross back to sell)
        + entry fee + exit fee, from common/kalshi_fees.py at the observed
          entry price
    A strategy has to beat that before it has anything.
"""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "common")))
import numpy as np
import pandas as pd
from scipy import stats as st
import load
from kalshi_fees import fee_order_dollars, fee_rate_cents

rng = np.random.default_rng(20260805)
pd.set_option("display.width", 250)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
BOT = load.BOT

B = pd.read_csv(os.path.join(OUT, "bot_matches.csv"), parse_dates=["t_entry"])
B["utc_hour"] = B.t_entry.dt.hour
B["night"] = np.where((B.utc_hour >= 20) | (B.utc_hour < 8), "night", "day")
B["block"] = pd.cut(B.utc_hour, [-1, 3, 7, 11, 15, 19, 23],
                    labels=["00-03", "04-07", "08-11", "12-15", "16-19", "20-23"])

# ----------------------------------------------------------------------
# (a) permutation test for every bucket
# ----------------------------------------------------------------------
print("=" * 78)
print("(a) LABEL-PERMUTATION p-values (200,000 shuffles), replacing the")
print("    t-tests. Null: the bucket label carries no information.")
print("=" * 78)
x = B.pnl.values
NS = 200_000
perm = np.array([rng.permutation(x) for _ in range(2000)])   # reused blockwise

rows = []
for fam, col in (("night/day", "night"), ("4h block", "block"), ("tier", "tier")):
    for k, g in B.groupby(col, observed=True):
        m = len(g)
        obs = g.pnl.sum()
        # exact-in-distribution: sample m of the 108 without replacement
        idx = rng.integers(0, len(x), size=(NS, 1))  # placeholder, replaced below
        draws = np.empty(NS)
        for i in range(NS):
            draws[i] = x[rng.choice(len(x), m, replace=False)].sum()
        p_hi = (draws >= obs).mean()
        p_lo = (draws <= obs).mean()
        rows.append(dict(family=fam, bucket=str(k), n=m, total=obs,
                         mean=obs / m, contracts=g.contracts.sum(),
                         p_two=min(1.0, 2 * min(p_hi, p_lo)),
                         null_mean=draws.mean(), null_sd=draws.std()))
P = pd.DataFrame(rows).sort_values("p_two")
print(P.round(4).to_string(index=False))
P.to_csv(os.path.join(OUT, "perm_buckets.csv"), index=False)

Pf = P.sort_values("p_two").reset_index(drop=True)
Pf["rank"] = Pf.index + 1
Pf["bh"] = Pf["rank"] / len(Pf) * 0.05
print(f"\nBH at FDR 5% over {len(Pf)} buckets: "
      f"{int((Pf.p_two <= Pf.bh).sum())} discoveries")
print("NOTE: these buckets overlap heavily (the same 27 Jul morning matches")
print("appear in '04-07', in 'Challenger' and in 'night'), so even this")
print("correction is optimistic.")

# ----------------------------------------------------------------------
# (b) the cost bar, measured from the recorder tape
# ----------------------------------------------------------------------
print()
print("=" * 78)
print("(b) COST BAR PER BUCKET, from the recorder tapes")
print("=" * 78)
recs = []
for fn in ("tennis_data.jsonl", "tennis_data_laptop.jsonl"):
    p = os.path.join(BOT, fn)
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            recs.append((d.get("ts"), d.get("ticker"), d.get("bid"), d.get("ask"),
                         d.get("spread"), d.get("score_change_ts"),
                         d.get("tournament"), d.get("status_type")))
R = pd.DataFrame(recs, columns=["ts", "ticker", "bid", "ask", "spread",
                                "score_change_ts", "tournament", "status_type"])
R = R.drop_duplicates(subset=["ts", "ticker"])
R["t"] = pd.to_datetime(R.ts, unit="s", utc=True)
R["tier"] = R.ticker.map(load.tier_of)
R["utc_hour"] = R.t.dt.hour
R["night"] = np.where((R.utc_hour >= 20) | (R.utc_hour < 8), "night", "day")
R["block"] = pd.cut(R.utc_hour, [-1, 3, 7, 11, 15, 19, 23],
                    labels=["00-03", "04-07", "08-11", "12-15", "16-19", "20-23"])
R = R[(R.tier != "OTHER") & R.ask.notna() & R.bid.notna()]
R["spread"] = (R.ask - R.bid).astype(float)
print(f"recorder rows usable: {len(R):,}  "
      f"window {R.t.min()} -> {R.t.max()}  markets {R.ticker.nunique():,}")

BAND = R[(R.ask >= 40) & (R.ask <= 80)]      # the band the bot actually entered
print(f"restricted to ask 40-80c (the band the bot traded): {len(BAND):,} rows")


def bar(g):
    if not len(g):
        return pd.Series({"n_obs": 0})
    sp = g.spread.median()
    px = int(round(g.ask.median()))
    # **Both conventions, reported side by side. Added 2026-09-01.**
    #
    # The `reopen` audit flagged this as carrying the same rounding bias as
    # t7_sweep, and it is **half right, which is why both numbers are here
    # rather than one replacing the other.**
    #
    #   ORDER  fee_order_dollars(px, 1) rounds UP per order. If you really do
    #          trade one contract at a time -- which is exactly what this bot
    #          did -- that IS the bill. It is not an artefact.
    #   RATE   fee_rate_cents is the unrounded per-contract cost, and it is the
    #          only one comparable with a per-contract EXPECTANCY.
    #
    # **The error is not using the rounded one. It is comparing a rounded bar
    # against an unrounded expectancy, or the reverse.** t7_sweep reports
    # expectancy, so it now uses RATE; a bar quoted next to it must too.
    f_in = fee_order_dollars(px, 1) * 100          # cents per contract
    f_out = fee_order_dollars(min(99, px + 10), 1) * 100
    r_in = float(fee_rate_cents(px))
    r_out = float(fee_rate_cents(min(99, px + 10)))
    return pd.Series({"n_obs": len(g), "median_ask": px,
                      "median_spread": sp, "mean_spread": g.spread.mean(),
                      "fee_in_c": f_in, "fee_out_c": f_out,
                      "cost_bar_c": sp + f_in + f_out,
                      "fee_in_rate_c": r_in, "fee_out_rate_c": r_out,
                      "cost_bar_rate_c": sp + r_in + r_out})


print("\n--- cost bar by tier (cents per contract, round trip)")
cb_tier = BAND.groupby("tier").apply(bar, include_groups=False)
print(cb_tier.round(3).to_string())
print("\n--- cost bar by night/day")
cb_nd = BAND.groupby("night").apply(bar, include_groups=False)
print(cb_nd.round(3).to_string())
print("\n--- cost bar by 4h block")
cb_bl = BAND.groupby("block", observed=True).apply(bar, include_groups=False)
print(cb_bl.round(3).to_string())
print("\n--- cost bar by tier x night")
cb_x = BAND.groupby(["tier", "night"]).apply(bar, include_groups=False)
print(cb_x.round(3).to_string())

# ----------------------------------------------------------------------
# result vs bar
# ----------------------------------------------------------------------
print()
print("=" * 78)
print("RESULT AGAINST ITS OWN COST BAR, per bucket")
print("=" * 78)
res = B.groupby("tier").apply(
    lambda g: pd.Series({"n": len(g), "c_per_contract": g.pnl.sum() / g.contracts.sum() * 100}),
    include_groups=False)
res = res.join(cb_tier[["median_spread", "cost_bar_c"]])
res["gross_needed_c"] = res.cost_bar_c
print("\nby tier:")
print(res.round(3).to_string())
res2 = B.groupby("night").apply(
    lambda g: pd.Series({"n": len(g), "c_per_contract": g.pnl.sum() / g.contracts.sum() * 100}),
    include_groups=False).join(cb_nd[["median_spread", "cost_bar_c"]])
print("\nby night/day:")
print(res2.round(3).to_string())
res3 = B.groupby("block", observed=True).apply(
    lambda g: pd.Series({"n": len(g), "c_per_contract": g.pnl.sum() / g.contracts.sum() * 100}),
    include_groups=False).join(cb_bl[["median_spread", "cost_bar_c"]])
print("\nby 4h block:")
print(res3.round(3).to_string())
print()
print("The reported c_per_contract is ALREADY NET of both fees and of the")
print("spread actually paid - it comes from realised cash. The cost bar column")
print("is what the strategy had to overcome to reach zero, i.e. how much gross")
print("edge the signal needed to supply. Read them together, not as a subtraction.")

for nm, d in (("tier", res), ("night", res2), ("block", res3)):
    d.to_csv(os.path.join(OUT, f"costbar_{nm}.csv"))
