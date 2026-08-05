"""
t2d_martingale.py - caveat 3, and caveat 1.

PART A - THE MARTINGALE.
The brief asks whether the profitable stretch contains the same re-entry
pattern going the OTHER way, because a martingale that happens to win looks
identical to skill. Every multi-leg entry in the record is laid out here, with
the direction of each leg and what it did to the position.

PART B - THE STALE-SCORE BUG.
`fetched_at` was stamped at cache read, so the 30s guard never fired and the
bot may have been acting on scores minutes old. That is asserted in STATUS.md
but has never been measured. It can be, from the recorder tape, without any new
data:

    if our score feed is LATE, then on the tick where our `all_sets` /
    `games_won` finally changes, the market price will ALREADY have moved -
    because everyone watching the actual match repriced first.

So: for every score change in the tape, measure the price move in the window
BEFORE it against the move AFTER it. A feed that is on time puts the move
after. A feed that is late puts the move before.
"""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import load

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 300)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")

O = load.orders(); F = load.fills()
B = pd.read_csv(os.path.join(OUT, "bot_matches.csv"), parse_dates=["t_entry"])
botev = set(B.event)

# ======================================================================
# PART A
# ======================================================================
print("=" * 78)
print("PART A - every multi-leg entry the bot made")
print("=" * 78)
buys = O[(O.action == "buy") & (O.side == "yes")].copy()
buys["cents"] = (buys.px * 100).round().astype(int)
buys["notional"] = buys.initial * buys.px
buys = buys[buys.cents.between(10, 90) & buys.notional.between(4.60, 6.30)]
buys = buys[buys.event.isin(botev)]
buys = buys[buys.filled > 0].sort_values("t")

multi = buys.groupby("ticker").filter(lambda g: len(g) > 1)
pnl = B.set_index("event").pnl.to_dict()
print(f"{multi.ticker.nunique()} of {buys.ticker.nunique()} traded markets "
      f"had more than one filled entry\n")

rows = []
for tk, g in multi.groupby("ticker"):
    g = g.sort_values("t")
    legs = list(zip(g.cents, g.filled, g.t))
    dirn = "DOWN" if legs[-1][0] < legs[0][0] else ("UP" if legs[-1][0] > legs[0][0] else "FLAT")
    size_up = legs[-1][1] > legs[0][1]
    gaps = [(legs[i + 1][2] - legs[i][2]).total_seconds() for i in range(len(legs) - 1)]
    ev = load.event_of(tk)
    rows.append(dict(ticker=tk, legs=len(legs),
                     prices="->".join(str(c) for c, _, _ in legs),
                     sizes="->".join(f"{int(q)}" for _, q, _ in legs),
                     dirn=dirn, size_up=size_up,
                     min_gap_s=int(min(gaps)), total=g.filled.sum(),
                     pnl=pnl.get(ev, np.nan)))
MG = pd.DataFrame(rows).sort_values("pnl")
print(MG.to_string(index=False))

print()
print("--- classification")
down = MG[MG.dirn == "DOWN"]
up = MG[MG.dirn == "UP"]
print(f"averaging DOWN (each leg cheaper -> more contracts): {len(down)}   "
      f"total P&L ${down.pnl.sum():+.2f}   mean ${down.pnl.mean():+.3f}")
print(f"averaging UP   (each leg dearer  -> fewer contracts): {len(up)}   "
      f"total P&L ${up.pnl.sum():+.2f}   mean ${up.pnl.mean():+.3f}")
single = B[~B.event.isin(set(MG.ticker.map(load.event_of)))]
print(f"single-entry matches: {len(single)}   total ${single.pnl.sum():+.2f}   "
      f"mean ${single.pnl.mean():+.3f}")
print()
print(f"re-entries with a gap under 60s: {(MG.min_gap_s < 60).sum()} of {len(MG)}")
print(f"the martingale legs contributed ${down.pnl.sum():+.2f} of the "
      f"${B.pnl.sum():+.2f} total, on {len(down)} of {len(B)} matches")
print()
print("DID THE PROFITABLE STRETCH CONTAIN A WINNING MARTINGALE?")
MG["ev"] = MG.ticker.map(load.event_of)
te = B.set_index("event").t_entry.to_dict()
MG["t_entry"] = MG.ev.map(te)
early = MG[MG.t_entry < pd.Timestamp("2026-07-28 13:32:08", tz="UTC")]
print(f"  multi-leg entries BEFORE the equity peak: {len(early)}")
print(early[["ticker", "prices", "sizes", "dirn", "pnl"]].to_string(index=False))
print(f"  -> averaging-down legs before the peak: "
      f"{(early.dirn == 'DOWN').sum()}, total ${early[early.dirn == 'DOWN'].pnl.sum():+.2f}")

MG.to_csv(os.path.join(OUT, "multileg.csv"), index=False)

# ======================================================================
# PART B - is the score feed late?
# ======================================================================
print()
print("=" * 78)
print("PART B - measuring the stale-score bug from the recorder tape")
print("=" * 78)
recs = []
for fn in ("tennis_data.jsonl", "tennis_data_laptop.jsonl"):
    with open(os.path.join(load.BOT, fn), encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            recs.append((d.get("ts"), d.get("ticker"), d.get("bid"), d.get("ask"),
                         d.get("sets_won"), d.get("sets_lost"),
                         d.get("games_won"), d.get("games_lost"),
                         d.get("point"), d.get("opp_point"),
                         d.get("score_change_ts"), d.get("status_type")))
R = pd.DataFrame(recs, columns=["ts", "ticker", "bid", "ask", "sw", "sl",
                                "gw", "gl", "pt", "opt", "sct", "status"])
R = R.drop_duplicates(subset=["ts", "ticker"]).sort_values(["ticker", "ts"])
R = R[R.ask.notna() & R.bid.notna()]
R["mid"] = (R.ask + R.bid) / 2
R["tier"] = R.ticker.map(load.tier_of)
R = R[R.tier != "OTHER"]
print(f"tape rows: {len(R):,}  markets {R.ticker.nunique()}  "
      f"window {pd.to_datetime(R.ts.min(), unit='s', utc=True)} -> "
      f"{pd.to_datetime(R.ts.max(), unit='s', utc=True)}")

# how often does score_change_ts move at all, and what is its age?
R["age"] = R.ts - R.sct
print(f"\nage of the last score change at each observation (seconds):")
print(R.age.describe(percentiles=[.1, .25, .5, .75, .9, .99]).round(1).to_string())
print(f"observations where the score was already >30s old (the guard's limit): "
      f"{(R.age > 30).mean():.1%}")
print(f"                                        >120s old: {(R.age > 120).mean():.1%}")
print("NOTE: this is time since the score last CHANGED, which is mostly the")
print("natural rhythm of a tennis point. It is an upper bound on freshness,")
print("not a measure of feed lag. The lag test is below.")

# --- the lag test -----------------------------------------------------
g = R.groupby("ticker", sort=False)
R["d_games"] = (g.gw.diff().fillna(0) != 0) | (g.gl.diff().fillna(0) != 0)
R["d_sets"] = (g.sw.diff().fillna(0) != 0) | (g.sl.diff().fillna(0) != 0)
R["chg"] = R.d_games | R.d_sets
R["mid_prev"] = g.mid.shift(1)
R["mid_p2"] = g.mid.shift(2)
R["mid_p3"] = g.mid.shift(3)
R["mid_n1"] = g.mid.shift(-1)
R["mid_n2"] = g.mid.shift(-2)
R["mid_n3"] = g.mid.shift(-3)
R["dt_prev"] = g.ts.diff()

E = R[R.chg & R.mid_p3.notna() & R.mid_n3.notna() & (R.dt_prev < 120)].copy()
print(f"\ngame/set changes with 3 clean ticks either side: {len(E):,} "
      f"across {E.ticker.nunique()} markets")
# direction of the score event, from the perspective of THIS ticker's player
E["won_pt"] = (g.gw.diff().reindex(E.index) > 0).fillna(False) | \
              (g.sw.diff().reindex(E.index) > 0).fillna(False)
before = E.mid - E.mid_p3        # move over the 3 ticks BEFORE the change appeared
after = E.mid_n3 - E.mid         # move over the 3 ticks AFTER
sgn = np.where(E.won_pt, 1.0, -1.0)
print(f"\nsigned price move (cents of mid), oriented so + = 'in the direction the")
print(f"score change implies':")
print(f"  3 ticks BEFORE our feed showed the change : mean {np.mean(before * sgn):+.3f}c   "
      f"median {np.median(before * sgn):+.3f}c")
print(f"  3 ticks AFTER  our feed showed the change : mean {np.mean(after * sgn):+.3f}c   "
      f"median {np.median(after * sgn):+.3f}c")
tot = np.mean(before * sgn) + np.mean(after * sgn)
if tot != 0:
    print(f"  share of the repricing that had ALREADY happened when our feed "
          f"caught up: {np.mean(before * sgn) / tot:.1%}")
print()
print("READ THIS. If the feed were timely, essentially all of the repricing")
print("would fall AFTER the tick on which the score changed. Whatever share")
print("falls BEFORE is information the market had and the bot did not.")

pd.DataFrame({"before": before * sgn, "after": after * sgn,
              "tier": E.tier.values}).to_csv(
    os.path.join(OUT, "lag_events.csv"), index=False)

lag = pd.DataFrame({"before": before * sgn, "after": after * sgn, "tier": E.tier.values})
print("\nby tier:")
print(lag.groupby("tier").agg(n=("before", "size"), before=("before", "mean"),
                              after=("after", "mean")).round(3).to_string())

# ----------------------------------------------------------------------
# PLACEBO. A player who is winning games has a price drifting up anyway, so
# a window oriented by the direction of the NEXT game can pick up ordinary
# autocorrelation instead of feed lag. The control is an earlier window,
# ticks -6..-3, oriented the same way. If the move is concentrated in the
# three ticks immediately before our feed caught up, it is lag. If it is
# just as large six ticks earlier, it is drift and the lag reading is void.
# ----------------------------------------------------------------------
print()
print("-" * 78)
print("PLACEBO CONTROL and tick spacing")
print("-" * 78)
print(f"median seconds between consecutive ticks on one market: "
      f"{R.dt_prev[R.dt_prev.between(0, 600)].median():.1f}s   "
      f"mean {R.dt_prev[R.dt_prev.between(0, 600)].mean():.1f}s")
print(f"so the '3 ticks' windows are roughly "
      f"{3 * R.dt_prev[R.dt_prev.between(0, 600)].median():.0f}s wide")

for k in (4, 5, 6, 8):
    R[f"mid_p{k}"] = g.mid.shift(k)
E2 = R[R.chg & R.mid_p8.notna() & R.mid_n3.notna() & (R.dt_prev < 120)].copy()
s2 = np.where(E2.won_pt if "won_pt" in E2 else
              ((g.gw.diff().reindex(E2.index) > 0).fillna(False) |
               (g.sw.diff().reindex(E2.index) > 0).fillna(False)), 1.0, -1.0)
win_now = (E2.mid - E2.mid_p3) * s2          # ticks -3 -> 0   (the lag window)
win_pre = (E2.mid_p3 - E2.mid_p6) * s2       # ticks -6 -> -3  (placebo)
win_pre2 = (E2.mid_p6 - E2.mid_p8) * s2      # ticks -8 -> -6  (placebo)
win_post = (E2.mid_n3 - E2.mid) * s2         # ticks 0 -> +3
print(f"\nn = {len(E2):,} events with 8 clean ticks of history")
print(f"  ticks -8 -> -6 (placebo, further back) : mean {win_pre2.mean():+.3f}c")
print(f"  ticks -6 -> -3 (placebo)               : mean {win_pre.mean():+.3f}c")
print(f"  ticks -3 ->  0 (our feed catches up)   : mean {win_now.mean():+.3f}c")
print(f"  ticks  0 -> +3 (after)                 : mean {win_post.mean():+.3f}c")
tot2 = win_pre2.mean() + win_pre.mean() + win_now.mean() + win_post.mean()
print(f"\n  share of the whole repricing falling in the LAST window before our")
print(f"  feed updated: {win_now.mean() / tot2:.1%} of {tot2:+.3f}c")
print("\n  If the -6..-3 placebo were as large as the -3..0 window this would be")
print("  ordinary momentum and the lag reading would be void. Compare them.")
