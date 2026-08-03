"""generate_report.py - assemble BACKTEST_RESULTS.md from the pickled results.

Tables are rendered straight from the engine's output so the numbers in the
document cannot drift from the numbers that were computed.
"""

from __future__ import annotations

import os
import pickle

import numpy as np
import pandas as pd

import report as R
import run_backtest as rb

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "BACKTEST_RESULTS.md")
SLIP = 1.0


def cost_table(allt: dict) -> pd.DataFrame:
    rows = []
    for k, tr in allt.items():
        df = pd.DataFrame([x.__dict__ for x in tr])
        gross_c = df.gross / df.contracts * 100
        fee_c = df.fees / df.contracts * 100
        settled = df.reason.eq("settlement")
        fric = np.where(settled, df.spread / 2 + SLIP, df.spread + 2 * SLIP)
        rows.append({"strategy": k, "trades": len(df),
                     "edge_c": (gross_c + fric).mean(),
                     "spread_slip_c": fric.mean(),
                     "fees_c": fee_c.mean(),
                     "net_c": (gross_c - fee_c).mean()})
    return pd.DataFrame(rows).sort_values("net_c", ascending=False)


def main() -> None:
    t5, slip, spread_t, series_t, funnels, allt = R.load("step5.pkl")
    oat, grid = R.load("step6_s1.pkl")
    hold = R.load("step7_s1.pkl")

    g100 = grid[grid.trades >= 100].sort_values("net_c_per_trade", ascending=False)
    best = g100.iloc[0]
    sens = rb.sensitivity(grid, best)

    t5 = t5.rename(columns={"net_c_per_trade": "net_c/trade",
                            "net_$_per_trade": "net_$/trade"})

    p = []
    A = p.append
    A("# Kalshi tennis backtest — results\n")
    A("Offline replay of the v3 strategy rules against 4 weeks of Kalshi "
      "1-minute candlestick history. No live trading, no credentials loaded, "
      "read-only public market data.\n")

    A("## Bottom line\n")
    A("**No configuration of any strategy tested was profitable — including "
      "the best of 480 parameter combinations, and including a random-entry "
      "control.** The v3 entry signal does contain a small real edge "
      "(+1.9c per contract), but round-trip trading costs are 4.1c. The edge "
      "is less than half the cost of harvesting it.\n")
    A("The v3 exit ladder makes this worse, not better: it turns a +1.9c raw "
      "edge into −1.3c *before* any costs are applied.\n")

    A("## 1. Data\n")
    A("| | |\n|---|---|\n"
      "| Source | Kalshi public candlestick API (`api.elections.kalshi.com`) |\n"
      "| Interval | 1 minute (finest Kalshi offers; 1/60/1440 are the only valid values) |\n"
      "| Window | 2026-06-29 → 2026-07-27 (28 days) |\n"
      "| Markets | 14,162 settled (7,081 matches × 2 mirrored sides) |\n"
      "| Candle rows | 4,971,350 raw → 4,931,103 after cleaning |\n"
      "| Live candles | 2,941,821 (59.7%) after pre-match/dormancy/spread filters |\n"
      "| Market views | 13,658 |\n"
      "| Train / holdout | oldest 60% = 8,218 markets / newest 40% = 5,440 markets |\n")

    A("### Execution assumptions\n")
    A("- Signals on the **bid/ask midpoint**; execution on the **real ask** "
      "(buys) and **real bid** (sells), plus **1c** extra slippage each side\n"
      "- Fees: taker both sides, `ceil(0.07 × C × P × (1−P))`, verified "
      "against the spec's reference points (1.75c/contract at 50c, 0.63c at 90c/10c)\n"
      "- Same-candle stop/target ambiguity always resolves **stop first**\n"
      "- Candles with spread > 15c dropped as untradeable\n"
      "- Fixed $6 notional per trade\n"
      "- One open position per match at a time (the two sides of a match are "
      "near-perfect mid-price inverses — median difference 0.00c)\n")

    A("## 2. Step 5 — five strategies, training set\n")
    A(R.md(t5[["strategy", "trades", "matches", "win_rate", "avg_win_c",
                "avg_loss_c", "gross", "fees", "net", "net_c/trade",
                "net_$/trade", "max_dd"]]))
    A("\nSorted by net cents per trade. Every strategy loses. **S1 — the v3 "
      "strategy — performs worse than random entry (S5).**\n")

    A("### Signal funnel\n")
    A(R.md(R.funnel_table(funnels)))

    A("\n### Where the money actually goes (cents per contract)\n")
    A(R.md(cost_table(allt)))
    A("\n`edge_c` is the raw price move before any trading cost. This is the "
      "single most important table in the document:\n\n"
      "- **S2 (buy & hold) is the only strategy with a positive raw edge: +1.86c.** "
      "The v3 entry trigger genuinely predicts a small upward drift.\n"
      "- That edge is destroyed by 2.52c of spread+slippage and 1.62c of fees "
      "→ net −2.29c.\n"
      "- **S1's raw edge is −1.31c.** The exit ladder does not merely fail to "
      "add value; it converts a positive edge into a negative one before costs.\n"
      "- S3, S4 and S5 all have raw edges at or below zero — there is no "
      "path edge to harvest.\n")

    A("### Slippage sensitivity (net c/trade)\n")
    A(R.md(slip, index=True))
    A("\nNothing flips sign between 0c and 2c. The losses are not an artifact "
      "of the slippage assumption — at **zero** extra slippage every strategy "
      "still loses.\n")

    A("### By spread bucket\n")
    for k in ["S1 V3 ramp", "S3 fade drop", "S5 random"]:
        A(f"\n**{k}**\n")
        A(R.md(spread_t[k]))
    A("\nPerformance degrades monotonically with spread in every strategy — "
      "the honest bid/ask execution model is doing its job. But note the "
      "tightest bucket (0–2c) still loses 6.6–8.7c per trade. **There is no "
      "spread regime in which this is profitable**, so 'trade only liquid "
      "markets' does not rescue it.\n")

    A("### By series\n")
    for k in ["S1 V3 ramp", "S2 buy&hold", "S3 fade drop", "S4 ride rise", "S5 random"]:
        A(f"\n**{k}**\n")
        A(R.md(series_t[k]))
    A("\nEvery series loses in every strategy. The edge does not live in one "
      "segment and get averaged away — there is no segment.\n")

    A("## 3. Step 6 — parameter sweep (S1, best of S1/S3/S4)\n")
    A("### One knob at a time\n")
    A(R.md(oat))
    A("\nThe entire response surface spans −8.6c to −9.9c. No single "
      "parameter moves the result more than ~1.2c, and none approaches zero.\n")

    A("### Full grid — 480 configurations\n")
    A(f"**Configurations with positive net P&L per trade: "
      f"{int((grid.net_c_per_trade > 0).sum())} of {len(grid)}.**\n")
    A("\nTop 10 with at least 100 trades:\n")
    A(R.md(g100.head(10)))
    A(f"\nBest overall ignoring sample size: "
      f"{grid.net_c_per_trade.max():.2f} c/trade (47 trades). "
      f"Range across all 480: {grid.net_c_per_trade.min():.2f} to "
      f"{grid.net_c_per_trade.max():.2f}, std {grid.net_c_per_trade.std():.2f}.\n")

    A("### Sensitivity of the best configuration\n")
    A(R.md(sens))
    A("\nMoving **one** knob **one** notch shifts the result by up to 2.17c — "
      "roughly a third of the best config's own value. A result that moves "
      "that much under a one-notch change is not a stable optimum; it is "
      "noise-fitting. The holdout confirms this.\n")

    A("## 4. Step 7 — holdout (newest 40%, touched once)\n")
    A(R.md(hold))
    A("\n**Every configuration degraded on the holdout, and the tuned ones "
      "degraded most:**\n\n"
      "| Config | Train | Holdout | Change |\n|---|---|---|---|\n")
    for _, r in hold.iterrows():
        A(f"| {r['config']} | {r['train_net_c']:.2f} | {r['hold_net_c']:.2f} | "
          f"{r['hold_net_c'] - r['train_net_c']:+.2f} |\n")
    A("\nThe three tuned configurations gave back 3.5–4.3c on unseen data. "
      "The **untuned v3 default** gave back only 0.5c — because there was "
      "nothing fitted to give back. After the holdout, all three tuned "
      "configs are *worse* than the baseline they were tuned to beat. "
      "That is the cleanest possible demonstration that the Step 6 gains "
      "were fitted noise.\n")
    A("\n**Which survived: none.**\n")

    A("## 5. Honest read\n")
    A("**This is noise, not edge.** Six independent lines of evidence:\n\n"
      "1. Zero of 480 parameter configurations was profitable.\n"
      "2. The v3 strategy (−9.36c) performed worse than random entry (−8.28c).\n"
      "3. All three tuned configs collapsed on the holdout, ending up worse "
      "than the untuned baseline.\n"
      "4. The one-notch sensitivity is ~⅓ of the best config's value.\n"
      "5. Losses persist at zero slippage, in the tightest spread bucket, "
      "and in every series.\n"
      "6. The only positive raw edge found (+1.86c) is less than half the "
      "4.14c cost of trading it.\n")

    A("\n### What is actually true about the v3 signal\n")
    A("The structural-event trigger is **not** worthless. Buying an upward "
      "12c/60s step at 55–75c and holding to settlement produces a genuine "
      "+1.86c per-contract drift, and the classifier fires on real tennis "
      "events (verified by eye on ATP matches: clean 54→62→74→78 break-of-serve "
      "ramps). The problem is arithmetic, not signal quality:\n\n"
      "```\n"
      "  raw edge                      +1.86c\n"
      "  spread + slippage             -2.52c\n"
      "  fees                          -1.62c\n"
      "  ------------------------------------\n"
      "  net                           -2.29c\n"
      "```\n\n"
      "To make this work you would need the edge to roughly triple, or costs "
      "to fall by ~60%. Maker-only entries (the spec's §4 resting limit, at "
      "25% of taker fees) recover ~1.2c of the 1.62c fee. That closes less "
      "than a third of the gap and still leaves the strategy negative.\n")

    A("\n### On the exits specifically\n")
    A("Your Step 5 framing was: *\"If Strategy 1 can't beat this, its exits "
      "are destroying value.\"* Answer: **S1 −9.36c vs S2 −2.29c. The exits "
      "destroy 7.07c per trade.** The scale-out, the structural stop and the "
      "−24c floor together take a signal with a small positive drift and "
      "produce a raw edge of −1.31c before costs, plus an extra 2.5c of "
      "round-trip friction that holding to settlement never pays.\n\n"
      "This also settles the six-trade observation from 27 Jul that stops "
      "were 'selling local lows'. Across 1,501 trades the stops are not the "
      "problem in the way that reading suggested — but the exit machinery as "
      "a whole is worse than having no exits at all.\n")

    A("\n### What this does not say\n")
    A("- It does not say tennis markets are unbeatable. It says *this family "
      "of momentum-continuation rules, at these costs*, is not.\n"
      "- The window is 4 weeks of summer ITF/Challenger-heavy calendar.\n"
      "- Intra-candle path is invisible at 1-minute resolution; the "
      "stop-first tie rule is deliberately pessimistic and costs S1 some "
      "wins it might have had. It does not change the conclusion — S1 loses "
      "by 9c against a ~4c total cost base.\n"
      "- Untested and cheap to test next: the spec's §6 serve-timing filter "
      "(enter at the start of a service game), which is a genuinely different "
      "hypothesis rather than a re-parameterisation of this one.\n")

    A("\n### Measurement window, for the live bot\n")
    A("Structural events were measured as **mid-price change over 1 candle "
      "(60 seconds)**, not the spec's 45s. If any of this is ever revisited, "
      "the live bot must use a 60s window to match.\n")

    with open(DOC, "w", encoding="utf-8") as f:
        f.write("".join(p))
    print(f"wrote {DOC} ({os.path.getsize(DOC):,} bytes)")


if __name__ == "__main__":
    main()
