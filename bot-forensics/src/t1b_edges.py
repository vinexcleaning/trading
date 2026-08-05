"""
t1b_edges.py - the awkward rows, before they are allowed into any total.

Three of them, and one is worth $14.51 against a bot total of ~$29:
  * SHIDON, classed 'bot' on one small surviving buy order, but its settlement
    record shows a position the fills endpoint no longer returns
  * the five tiny 'bot' buy orders on 26 Jul, before the bot demonstrably
    started
  * eight tickers traded after the last settlement pull, carrying pnl=0
"""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import load

pd.set_option("display.width", 250)
O = load.orders(); F = load.fills(); S = load.settlements(); OU = load.outcomes()

print("=" * 78)
print("A. SHIDON")
print("=" * 78)
tk = "KXWTACHALLENGERMATCH-26JUL25SHIDON-SHI"
print("orders:")
print(O[O.ticker == tk][["t", "action", "side", "initial", "filled", "px",
                        "status", "client_order_id"]].to_string(index=False))
print("fills:")
print(F[F.ticker == tk][["t", "action", "side", "qty", "yes_px", "fee", "is_taker"]]
      .to_string(index=False))
print("settlement:")
print(S[S.ticker == tk].T.to_string())
print("sibling market:")
sib = [t for t in S.ticker if t.startswith("KXWTACHALLENGERMATCH-26JUL25SHIDON")]
print(S[S.ticker.isin(sib)][["ticker", "market_result", "yes_ct", "no_ct",
                             "yes_cost", "no_cost", "fee", "revenue", "value"]].to_string())

print()
print("=" * 78)
print("B. the small 'bot-shaped' buy orders on 25-26 Jul")
print("=" * 78)
B = O[(O.action == "buy")].copy()
B["notional"] = B.initial * B.px
early = B[(B.t < "2026-07-27") & (B.notional <= 7.5)]
print(early[["t", "ticker", "side", "initial", "px", "notional", "filled",
             "status"]].to_string(index=False))
print()
print("...and the ORDERS on the same tickers, to see whether the small one is a "
      "leg of a larger manual order:")
for tkk in early.ticker.unique():
    print(f"\n-- {tkk}")
    print(O[O.ticker == tkk][["t", "action", "side", "initial", "filled", "px",
                              "status"]].to_string(index=False))

print()
print("=" * 78)
print("C. tickers traded after the last settlement pull (2026-07-28 20:08)")
print("=" * 78)
settled = set(S.ticker)
late = [t for t in F.ticker.unique() if t not in settled]
for tkk in sorted(late):
    g = F[F.ticker == tkk]
    buy = g[(g.action == "buy") & (g.side == "yes")]
    sell = g[g.action == "sell"]
    resid = buy.qty.sum() - sell.qty.sum()
    cash = -(buy.qty * buy.yes_px).sum() + (sell.qty * sell.yes_px).sum() - g.fee.sum()
    print(f"{tkk:42s} bought {buy.qty.sum():6.2f} sold {sell.qty.sum():6.2f} "
          f"resid {resid:6.2f}  cash ${cash:7.3f}  outcome={OU.get(tkk, 'UNKNOWN')}")
