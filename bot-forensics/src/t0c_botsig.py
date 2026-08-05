"""
t0c_botsig.py - separate BOT orders from MANUAL ones.

The account was also traded by hand: _trades.json contains BTC15M, soccer and
esports positions the tennis bot cannot possibly have opened, at 100-2300
contracts against the bot's 7-25. Pooling them would make the reconstruction
meaningless, so the split has to be established on a signature that does not
depend on the P&L.

Candidate signatures, tested here:
  S1  the bot always rests a SELL at exactly 95c right after an entry
      (Config.favorite_target_price)
  S2  the bot sizes qty = int(stake / price) for one fixed stake
  S3  client_order_id format
  S4  _18h.json carries an explicit bot=True flag for 28 Jul and can be used
      as a labelled training set to check whatever rule the others suggest
"""
from __future__ import annotations
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import load

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 400)

O = load.orders()
F = load.fills()
H = load.log_18h()

print("=" * 78)
print("S3  client_order_id shapes")
print("=" * 78)
uuid_re = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
O["coid_uuid"] = O.client_order_id.astype(str).str.match(uuid_re)
print(O.coid_uuid.value_counts().to_dict())
print("non-uuid examples:", O.loc[~O.coid_uuid, "client_order_id"].head(10).tolist())

print()
print("=" * 78)
print("S1  resting sells at exactly 95c")
print("=" * 78)
sells = O[(O.action == "sell")]
print("sell orders by yes_price (cents):")
print((sells.yes_px * 100).round().astype(int).value_counts().sort_index().to_string())

print()
print("=" * 78)
print("S2  entry sizes. Bot = int(stake/price) for a fixed stake.")
print("=" * 78)
buys = O[(O.action == "buy") & (O.side == "yes") & (O.tier != "OTHER")].copy()
buys["cents"] = (buys.yes_px * 100).round().astype(int)
buys["notional"] = buys.initial * buys.yes_px
buys["day"] = buys.t.dt.floor("D")
print(buys.groupby("day").notional.describe()[["count", "25%", "50%", "75%", "max"]])
print()
print("implied stake = initial * price, rounded to 25c, per day:")
buys["stake_bucket"] = (buys.notional / 0.25).round() * 0.25
for d, g in buys.groupby("day"):
    print(f"\n{d.date()}:")
    print(g.stake_bucket.value_counts().sort_index().head(20).to_string())

print()
print("=" * 78)
print("S2b  does int(stake/price) reproduce the size, for stake in a grid?")
print("=" * 78)
import numpy as np
for d, g in buys.groupby("day"):
    best = []
    for stake in np.arange(2.0, 30.01, 0.25):
        pred = np.maximum(1, (stake / g.yes_px).astype(int))
        hit = (pred == g.initial.round()).mean()
        best.append((hit, stake))
    best.sort(reverse=True)
    print(f"{d.date()}  n={len(g):3d}   best stakes: "
          + "  ".join(f"${s:.2f}->{h:.0%}" for h, s in best[:4]))

print()
print("=" * 78)
print("S4  cross-check against the labelled 28 Jul set (_18h.json, bot=True)")
print("=" * 78)
h_tk = set(H.tk)
o28 = O[(O.t >= "2026-07-28") & (O.action == "buy") & (O.side == "yes")]
print(f"28 Jul buy orders: {len(o28)} on {o28.ticker.nunique()} tickers")
print(f"tickers in _18h.json: {len(h_tk)}")
print(f"28 Jul buy tickers also in _18h: {o28.ticker.isin(h_tk).sum()} / {len(o28)}")
print(f"_18h qty values: {sorted(H.qty.unique())}")
print(f"_18h entry prices: {sorted(H['in'].round(1).unique())}")
print()
print("_18h implied stake = qty * in/100:")
H["stake"] = H.qty * H["in"] / 100
print(H.stake.describe().to_string())
print(H[["tk", "qty", "in", "stake", "how", "pnl"]].head(30).to_string())
