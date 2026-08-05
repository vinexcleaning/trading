"""
t1_ledger.py - TASK 1. Rebuild every trade from the exchange record.

Accounting, established in t0b_sides.py and verified against Kalshi's own
settlement report on every settled ticker:

  Kalshi books a "sell YES" as a "buy NO". Holding 1 YES and 1 NO pays exactly
  $1.00 whatever happens, so the pair is a closed round trip. Therefore

      payout   = yes_ct * v + no_ct * (1 - v)        v = value/100 in {0,1}
      P&L      = payout - yes_cost - no_cost - fee

  and the settlement record's `fee` field is the CUMULATIVE TRADING fee for
  that ticker, not an extra settlement charge - verified equal to the sum of
  that ticker's fill fees. It is not double counted.

  Independent check on the same rows: `revenue` (cents) == residual_yes *
  value, where residual_yes = yes_ct - no_ct rebuilt from the fills.

BOT vs MANUAL. The account was also traded by hand. Split on order notional,
which is independent of the outcome: bot orders size qty = int(stake/price)
for a stake that never exceeds $6.25, manual orders run $11-$104, and there
are no orders in between.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import load

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")

F = load.fills()
O = load.orders()
S = load.settlements()
OUTC = load.outcomes()

BOT_MAX_NOTIONAL = 7.50          # see module docstring; the gap is 6.25 -> 11

# ----------------------------------------------------------------------
# 1. label every BUY order bot / manual
# ----------------------------------------------------------------------
B = O[(O.action == "buy")].copy()
B["notional"] = B.initial * B.px
B["is_bot"] = B.notional <= BOT_MAX_NOTIONAL
print("BUY orders by class:")
print(B.groupby([B.t.dt.floor("D"), "is_bot"]).agg(
    n=("notional", "size"), notional=("notional", "sum")).to_string())
print()
print("notional gap check - sorted unique notionals either side of the cut:")
srt = np.sort(B.notional.values)
print("  largest 'bot' side :", np.round(srt[srt <= BOT_MAX_NOTIONAL][-6:], 2))
print("  smallest 'manual'  :", np.round(srt[srt > BOT_MAX_NOTIONAL][:6], 2))

# ticker-level class
cls = B.groupby("ticker").is_bot.agg(["min", "max", "size"])
cls["klass"] = np.where(cls["min"] & cls["max"], "bot",
                 np.where(~cls["min"] & ~cls["max"], "manual", "mixed"))
print()
print("tickers by class:", cls.klass.value_counts().to_dict())
print("mixed tickers:", cls[cls.klass == "mixed"].index.tolist())

# ----------------------------------------------------------------------
# 2. per-ticker P&L from the settlement record
# ----------------------------------------------------------------------
S = S.copy()
S["v"] = S.value / 100.0
S["payout"] = S.yes_ct * S.v + S.no_ct * (1 - S.v)
S["cost"] = S.yes_cost + S.no_cost
S["pnl"] = S.payout - S.cost - S.fee

# independent reconstruction of the same number, from the fills only
def _resid(g):
    y = g[(g.action == "buy") & (g.side == "yes")].qty.sum()
    n = g[(g.action == "sell")].qty.sum()
    bn = g[(g.action == "buy") & (g.side == "no")].qty.sum()
    return pd.Series({"f_yes_buy": y, "f_sell": n, "f_no_buy": bn,
                      "f_yes_cost": (g[(g.action == "buy") & (g.side == "yes")].qty
                                     * g[(g.action == "buy") & (g.side == "yes")].yes_px).sum(),
                      "f_no_cost": (g[g.action == "sell"].qty
                                    * g[g.action == "sell"].no_px).sum(),
                      "f_fee": g.fee.sum(),
                      "t_first": g.t.min(), "t_last": g.t.max(),
                      "n_fills": len(g),
                      "n_buy_fills": int(((g.action == "bu" + "y") & (g.side == "yes")).sum())})

FT = F.groupby("ticker").apply(_resid, include_groups=False)
L = S.set_index("ticker")[["event", "tier", "market_result", "value", "yes_ct",
                           "no_ct", "yes_cost", "no_cost", "fee", "revenue",
                           "payout", "cost", "pnl", "t"]].join(FT, how="outer")
L = L.rename(columns={"t": "t_settled"})
L["klass"] = cls.klass.reindex(L.index)

print()
print("=" * 78)
print("CROSS-CHECK  settlement-record P&L vs fills-only P&L")
print("=" * 78)
both = L[L.pnl.notna() & L.f_yes_cost.notna()].copy()
both["fills_pnl"] = (both.f_yes_buy * both.value / 100
                     + both.f_sell * (1 - both.value / 100)
                     - both.f_yes_cost - both.f_no_cost - both.f_fee)
both["d"] = (both.pnl - both.fills_pnl).abs()
print(f"tickers on both records : {len(both)}")
print(f"agree within $0.01      : {(both.d < 0.01).sum()}")
print(f"agree within $0.10      : {(both.d < 0.10).sum()}")
print(f"max disagreement        : ${both.d.max():.2f}")
print("worst 8 (the fills endpoint is paginated and drops history; the "
      "settlement record is Kalshi's own book and is preferred):")
print(both.nlargest(8, "d")[["klass", "pnl", "fills_pnl", "d", "n_fills"]].to_string())

print()
print("tickers with fills but NO settlement record:")
nos = L[L.pnl.isna()]
print(nos[["klass", "f_yes_buy", "f_sell", "t_first", "n_fills"]].to_string())
print()
print("tickers with a settlement record but no fills (fill history truncated):")
nof = L[L.f_yes_cost.isna()]
print(f"  {len(nof)} tickers, total P&L ${nof.pnl.sum():.2f}, "
      f"class {nof.klass.value_counts().to_dict()}")
print(nof[["klass", "tier", "yes_ct", "pnl", "t_settled"]].to_string())

# ----------------------------------------------------------------------
# 3. the ledger
# ----------------------------------------------------------------------
L["tier"] = L.index.map(load.tier_of)
L["event"] = L.index.map(load.event_of)
L["match_date"] = L.index.map(load.match_date_of)
# entry time: prefer the first BUY order (orders survive even when fills are
# truncated), fall back to the first fill
fb = O[O.action == "buy"].groupby("ticker").t.min()
L["t_entry"] = fb.reindex(L.index)
L["t_entry"] = L.t_entry.fillna(L.t_first)
L["entry_px"] = (O[O.action == "buy"].sort_values("t").groupby("ticker").px.first()
                 .reindex(L.index) * 100).round()
L["n_buy_orders"] = O[O.action == "buy"].groupby("ticker").size().reindex(L.index)
L["gross_contracts"] = L.yes_ct.fillna(L.f_yes_buy)
L["klass"] = L.klass.fillna("unknown")
L.to_csv(os.path.join(OUT, "ledger_ticker.csv"))

print()
print("=" * 78)
print("TICKER LEDGER - totals by class")
print("=" * 78)
print(L.groupby("klass").agg(tickers=("pnl", "size"), pnl=("pnl", "sum"),
                             fee=("fee", "sum"), cost=("cost", "sum")).to_string())
print()
print("tennis only, by class and day of first entry:")
T = L[L.tier != "OTHER"].copy()
T["day"] = T.t_entry.dt.floor("D")
print(T.groupby(["day", "klass"]).agg(n=("pnl", "size"), pnl=("pnl", "sum")).to_string())

# ----------------------------------------------------------------------
# 4. fold to one observation per MATCH
# ----------------------------------------------------------------------
print()
print("=" * 78)
print("MATCH LEDGER - one row per event. This is the unit of observation.")
print("=" * 78)
M = (T.groupby("event")
       .agg(tier=("tier", "first"),
            match_date=("match_date", "first"),
            t_entry=("t_entry", "min"),
            t_settled=("t_settled", "max"),
            pnl=("pnl", "sum"),
            fee=("fee", "sum"),
            cost=("cost", "sum"),
            contracts=("gross_contracts", "sum"),
            n_tickers=("pnl", "size"),
            n_buy_orders=("n_buy_orders", "sum"),
            entry_px=("entry_px", "first"),
            klass=("klass", lambda s: "mixed" if s.nunique() > 1 else s.iloc[0]))
       .sort_values("t_entry"))
M.to_csv(os.path.join(OUT, "ledger_match.csv"))
print(f"matches: {len(M)}   bot-only: {(M.klass == 'bot').sum()}   "
      f"manual: {(M.klass == 'manual').sum()}   mixed: {(M.klass == 'mixed').sum()}")
print()
print(M.to_string())
