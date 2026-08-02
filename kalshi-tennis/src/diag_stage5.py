"""Why does Stage 5 show a fat ROI when Stage 4 says the model is not better?

A model that loses on Brier producing +25% ROI is a contradiction. Something in
the P&L is wrong. Prime suspects, in order:
  1. execution price -- betting at the MID of a wide, illiquid spread is not a
     trade anyone can actually make
  2. row duplication from the enrich merge (502 joined -> 512 rows)
  3. price timing -- is occurrence_datetime the match START or the expiry?
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"

j = pd.read_parquet(CACHE / "stage4_kalshi_join.parquet")
prices = pd.read_parquet(ROOT / "data" / "kalshi" / "kalshi_prematch_prices.parquet")
j = j.merge(prices[["event_ticker", "pre_bid", "pre_ask", "pre_last", "pre_mid"]],
            on="event_ticker", how="left", suffixes=("", "_p"))

print("=" * 78)
print("1. SPREAD -- can you actually trade at the mid?")
print("=" * 78)
j["spread_calc"] = j["pre_ask"] - j["pre_bid"]
print(j["spread_calc"].describe().to_string())
print()
for lo, hi in [(0, 0.02), (0.02, 0.05), (0.05, 0.10), (0.10, 0.25),
               (0.25, 0.50), (0.50, 1.01)]:
    m = j["spread_calc"].between(lo, hi, inclusive="left")
    print(f"  spread {lo:.2f}-{hi:.2f}: {m.sum():>4} markets "
          f"({m.mean() * 100:5.1f}%)")
print()
print(f"  markets with spread > 10c: {(j['spread_calc'] > 0.10).mean() * 100:.1f}%")
print(f"  markets with spread > 25c: {(j['spread_calc'] > 0.25).mean() * 100:.1f}%")
print("\n  A 25c spread means the mid is a fiction: you buy at the ask and")
print("  sell at the bid, and the round trip alone costs a quarter of a dollar.")

print("\n" + "=" * 78)
print("2. DUPLICATION from the enrich merge")
print("=" * 78)
pred = pd.read_parquet(CACHE / "stage4_predictions.parquet",
                       columns=["date", "p1", "p2", "d_elo"])
pred["date"] = pd.to_datetime(pred["date"])
jj = j.copy()
jj["date"] = pd.to_datetime(jj["date"])
merged = jj.merge(pred, on=["date", "p1", "p2"], how="left")
print(f"  join rows {len(j)} -> merged {len(merged)}  "
      f"(duplicates introduced: {len(merged) - len(j)})")
dupes = pred.duplicated(subset=["date", "p1", "p2"], keep=False)
print(f"  prediction frame has {dupes.sum():,} rows on duplicate (date,p1,p2) keys")

print("\n" + "=" * 78)
print("3. IS THE PRICE ACTUALLY PRE-MATCH?")
print("=" * 78)
print("  If occurrence_datetime were the expiry, the 'pre-match' quote would")
print("  sit near the end of the match and the market Brier would collapse.")
y = j["y"].to_numpy()
pm = j["p_market"].to_numpy()
print(f"  market Brier on the joined set: {np.mean((pm - y) ** 2):.5f}")
print(f"  (a leaked/post-match price would be far below 0.10)")
print(f"  mean market prob assigned to the eventual winner: "
      f"{np.mean(np.where(y == 1, pm, 1 - pm)):.4f}")

print("\n" + "=" * 78)
print("4. THE ACTUAL P&L QUESTION -- mid vs executable price")
print("=" * 78)


def fee(p):
    return np.ceil(0.07 * p * (1 - p) * 100) / 100


for thresh in (0.02, 0.05, 0.10):
    d = j.copy()
    d["edge"] = d["p_model"] - d["p_market"]
    take = d[d["edge"].abs() >= thresh].copy()
    take = take[take["pre_bid"].notna() & take["pre_ask"].notna()]
    if take.empty:
        continue
    side_yes = (take["edge"] > 0).to_numpy()
    won = take["y"].to_numpy()

    # (a) fantasy: fill at the mid
    mid = take["p_market"].to_numpy()
    entry_mid = np.where(side_yes, mid, 1 - mid)
    hit = np.where(side_yes, won, 1 - won)
    pnl_mid = np.where(hit == 1, 1 - entry_mid, -entry_mid) - fee(entry_mid)

    # (b) reality: buying YES lifts the ask; buying NO costs 1 - bid
    bid = take["pre_bid"].to_numpy()
    ask = take["pre_ask"].to_numpy()
    entry_exec = np.where(side_yes, ask, 1 - bid)
    pnl_exec = np.where(hit == 1, 1 - entry_exec, -entry_exec) - fee(entry_exec)

    print(f"\n  min edge {thresh:.2f}  ({len(take)} bets)")
    print(f"    fill at MID      mean P&L {pnl_mid.mean():+.4f}  "
          f"ROI {pnl_mid.mean() / entry_mid.mean() * 100:+.1f}%")
    print(f"    fill at ASK/BID  mean P&L {pnl_exec.mean():+.4f}  "
          f"ROI {pnl_exec.mean() / entry_exec.mean() * 100:+.1f}%")
    print(f"    mean entry: mid {entry_mid.mean():.3f} -> exec "
          f"{entry_exec.mean():.3f}  (+{(entry_exec - entry_mid).mean() * 100:.1f}c)")
    print(f"    hit rate {hit.mean():.3f} vs mid-implied "
          f"{(1 - entry_mid).mean():.3f}")
