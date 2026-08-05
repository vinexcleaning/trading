"""
t0_survey.py - what is actually in the records, before any P&L is computed.

Answers: what window do the fills cover, how many, what tiers, does the
account hold anything that never settled, and do the bot's own logs agree
with the exchange record.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import load

pd.set_option("display.width", 200)
pd.set_option("display.max_rows", 300)

F = load.fills()
O = load.orders()
S = load.settlements()
T = load.bot_trades()
H = load.log_18h()

print("=" * 78)
print("FILLS")
print("=" * 78)
print(f"n fills          {len(F)}")
print(f"window           {F.t.min()}  ->  {F.t.max()}")
print(f"distinct tickers {F.ticker.nunique()}   events {F.event.nunique()}")
print(f"gross notional   ${(F.qty * F.px).sum():,.2f}")
print(f"total fees       ${F.fee.sum():,.2f}")
print(f"taker fills      {int(F.is_taker.sum())} / {len(F)}")
print()
print("by tier:")
print(F.groupby("tier").agg(fills=("qty", "size"), contracts=("qty", "sum"),
                            fee=("fee", "sum"), events=("event", "nunique")))
print()
print("by side/action:")
print(F.groupby(["side", "action"]).agg(n=("qty", "size"), ct=("qty", "sum")))
print()
print("fills per UTC calendar day:")
F["day"] = F.t.dt.floor("D")
print(F.groupby("day").agg(n=("qty", "size"), ct=("qty", "sum"), fee=("fee", "sum"),
                           events=("event", "nunique")))
print()
print("fills per UTC hour (all days pooled):")
F["hr"] = F.t.dt.hour
print(F.groupby("hr").agg(n=("qty", "size"), ct=("qty", "sum")).T)

print()
print("=" * 78)
print("ORDERS")
print("=" * 78)
print(f"n orders         {len(O)}")
print(f"window           {O.t.min()}  ->  {O.t.max()}")
print("status:")
print(O.status.value_counts())
print("by action/side:")
print(O.groupby(["action", "side"]).agg(n=("initial", "size"), init=("initial", "sum"),
                                        filled=("filled", "sum")))
print()
print("orders per UTC calendar day:")
O["day"] = O.t.dt.floor("D")
print(O.groupby("day").agg(n=("initial", "size"), filled=("filled", "sum")))

print()
print("=" * 78)
print("SETTLEMENTS")
print("=" * 78)
print(f"n settlements    {len(S)}")
print(f"window           {S.t.min()}  ->  {S.t.max()}")
print(f"sum revenue      ${S.revenue.sum():,.2f}")
print(f"sum fee          ${S.fee.sum():,.2f}")
print("value counts:", S.value.value_counts().to_dict())
print(S.groupby("tier").agg(n=("value", "size")))

print()
print("=" * 78)
print("BOT'S OWN LOGS (claims)")
print("=" * 78)
print(f"_trades.json  n={len(T)}  window {T.ts.min()} -> {T.ts.max()}"
      f"  sum pnl ${T.pnl.sum():.2f}")
print(T.groupby(T.ts.dt.floor("D")).agg(n=("pnl", "size"), pnl=("pnl", "sum")))
print()
print(f"_18h.json     n={len(H)}  window {H.ts.min()} -> {H.ts.max()}"
      f"  sum pnl ${H.pnl.sum():.2f}")
print("bot flag:", H.bot.value_counts().to_dict())
print("how:", H.how.value_counts().to_dict())
print(H.groupby(H.ts.dt.floor("h")).agg(n=("pnl", "size"), pnl=("pnl", "sum")))

print()
print("non-tennis tickers touched by fills:")
print(F[F.tier == "OTHER"].ticker.value_counts())
print()
print("non-tennis in _trades.json:")
print(T[T.tier == "OTHER"][["ts", "tk", "pnl", "kind"]].to_string())
