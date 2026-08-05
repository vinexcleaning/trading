"""
t0b_sides.py - resolve how a SELL is represented in this account's records.

204 buy/yes fills against 177 sell/no fills and only 1 sell/yes. If sell/no
meant "open a new short in the NO market" the account would be carrying
enormous unclosed positions. The competing reading is that Kalshi reports the
closing sale of a YES position as action=sell, side=no (i.e. it labels the
side by the book the order rested on). Whichever it is has to be settled from
the data, not assumed - it flips the sign of most of the P&L.
"""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import load

pd.set_option("display.width", 250)
F = load.fills()
O = load.orders()
S = load.settlements()

# --- 1. price identity check -----------------------------------------
# yes_price + no_price should be 1.00 on every row if they are two views of
# the same trade.
F["sum_px"] = (F.yes_px + F.no_px).round(4)
print("yes_px + no_px value counts:", F.sum_px.value_counts().to_dict())
print()

# --- 2. per-ticker sequences -----------------------------------------
print("=" * 78)
print("Per-ticker fill sequences, 6 busiest tennis tickers")
print("=" * 78)
tt = F[F.tier != "OTHER"]
for tk in tt.ticker.value_counts().head(6).index:
    g = tt[tt.ticker == tk]
    print(f"\n--- {tk}")
    print(g[["t", "action", "side", "qty", "yes_px", "no_px", "fee", "is_taker"]]
          .to_string(index=False))
    st = S[S.ticker == tk]
    if len(st):
        print("  settlement:", st.iloc[0][["market_result", "yes_ct", "no_ct",
                                           "yes_cost", "no_cost", "fee",
                                           "revenue", "value"]].to_dict())

# --- 3. the decisive test: net position under each reading -----------
print()
print("=" * 78)
print("Net residual position per ticker under the two readings")
print("=" * 78)


def resid_naive(g):
    """Reading A: side is a real, separate market. yes and no netted apart."""
    y = g[g.side == "yes"].signed.sum()
    n = g[g.side == "no"].signed.sum()
    return pd.Series({"A_yes": y, "A_no": n})


def resid_merged(g):
    """Reading B: everything is a YES position; sell/no is a closing sale of
    YES. buy/no is a real NO purchase (only 7 fills, 93 contracts)."""
    y = 0.0
    for _, r in g.iterrows():
        if r.action == "buy" and r.side == "yes":
            y += r.qty
        elif r.action == "sell" and r.side == "no":
            y -= r.qty
        elif r.action == "sell" and r.side == "yes":
            y -= r.qty
    return pd.Series({"B_yes": y})


a = tt.groupby("ticker").apply(resid_naive, include_groups=False)
b = tt.groupby("ticker").apply(resid_merged, include_groups=False)
r = a.join(b)
print(f"tickers: {len(r)}")
print(f"Reading A: tickers with a residual NO short  : "
      f"{int((r.A_no < -1e-9).sum())}   total short contracts {r.A_no[r.A_no < 0].sum():.0f}")
print(f"Reading A: tickers with residual YES long    : {int((r.A_yes > 1e-9).sum())}")
print(f"Reading B: tickers flat at the end           : {int((r.B_yes.abs() < 1e-9).sum())}")
print(f"Reading B: tickers with a residual YES long  : {int((r.B_yes > 1e-9).sum())}")
print(f"Reading B: tickers going NEGATIVE (impossible if B is right): "
      f"{int((r.B_yes < -1e-9).sum())}")
print()
print("Reading B residual distribution:")
print(r.B_yes.value_counts().sort_index().to_string())

# --- 4. cross-check against the settlement record --------------------
print()
print("=" * 78)
print("Residual under B vs the settlement record's counts")
print("=" * 78)
chk = r.join(S.set_index("ticker")[["market_result", "yes_ct", "no_ct",
                                    "yes_cost", "no_cost", "fee", "revenue",
                                    "value"]], how="left")
print(chk.head(40).to_string())
print()
agree = (chk.B_yes.round(2) == chk.yes_ct.round(2)).sum()
print(f"tickers where residual_B == settlement yes_count_fp : {agree} / {chk.yes_ct.notna().sum()}")
agree2 = (chk.B_yes.round(2) == chk.no_ct.round(2)).sum()
print(f"tickers where residual_B == settlement no_count_fp  : {agree2}")
print(f"settlement rows where yes_ct == no_ct               : "
      f"{int((S.yes_ct == S.no_ct).sum())} / {len(S)}")

# --- 5. what is `revenue`? -------------------------------------------
print()
print("settlement revenue non-zero rows:")
print(S[S.revenue != 0][["ticker", "market_result", "yes_ct", "no_ct",
                         "yes_cost", "no_cost", "fee", "revenue", "value"]].head(20).to_string())
print("revenue==0 count:", int((S.revenue == 0).sum()), "of", len(S))
