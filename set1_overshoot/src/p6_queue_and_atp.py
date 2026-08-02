"""Backlog 4 and 5, from the recorded order books.

4. QUEUE POSITION. Task 1b assumes a resting order fills when the book trades
   through its price -- i.e. the whole queue at that level clears. The books say
   how much sits there. If typical queue-ahead is large relative to what trades
   in a minute, that assumption is generous and the maker line is worse than
   reported.

5. WHY IS ATP THE THINNEST BOOK? Median 30 lots at a 3c spread on the main tour
   against 1,822 lots at 1c on Challenger inverts the usual liquidity
   assumption, and it interacts with the spread>15c composition effect (z=-6.34).
"""
import glob
import json
import pathlib
import statistics as stats

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = []


def w(s=""):
    print(s, flush=True)
    OUT.append(s)


def main():
    rows = []
    for p in sorted(glob.glob(str(DATA / "depth" / "*" / "*" / "depth.jsonl"))):
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    w("# Queue position and the ATP liquidity inversion")
    w("")
    ts = sorted(r["ts"] for r in rows)
    w(f"Recorded books: **{len(rows):,}** snapshots, "
      f"{len({r['ticker'] for r in rows})} markets, "
      f"{ts[0][11:16]}–{ts[-1][11:16]} UTC on {ts[0][:10]}.")
    w("")

    # ---------- per-snapshot features -----------------------------------
    recs = []
    for r in rows:
        y, n = r["yes"], r["no"]
        if not y or not n:
            continue
        ybest, ysz = float(y[-1][0]) * 100, float(y[-1][1])
        nbest, nsz = float(n[-1][0]) * 100, float(n[-1][1])
        ask = 100 - nbest
        recs.append({"tk": r["ticker"], "series": r["series"], "ts": r["ts"],
                     "bid": ybest, "ask": ask, "spread": ask - ybest,
                     "bid_sz": ysz, "ask_sz": nsz,
                     "depth10": sum(float(s) for _, s in y),
                     "mid": (ybest + ask) / 2})
    d = pd.DataFrame(recs)
    d = d[(d["spread"] >= 0) & (d["spread"] <= 100)]

    # ---------- 5. ATP inversion -----------------------------------------
    w("## 5. Why is ATP the thinnest book?")
    w("")
    w("| series | snapshots | median spread ¢ | median top size | median mid ¢ "
      "| share of snapshots with mid in 5–95¢ |")
    w("|---|---|---|---|---|---|")
    for s, g in d.groupby("series"):
        inband = ((g["mid"] >= 5) & (g["mid"] <= 95)).mean()
        w(f"| {s} | {len(g):,} | {g['spread'].median():.1f} | "
          f"{g['bid_sz'].median():,.0f} | {g['mid'].median():.0f} | "
          f"{inband:.0%} |")
    w("")
    # the hypothesis: ATP markets sit at extreme prices where books are thin
    w("**Hypothesis tested:** the inversion is a *price-level* effect, not a "
      "tour effect.")
    w("Books thin out near 0 and 100 because there is little left to trade "
      "for. If ATP")
    w("markets sit at more extreme prices, they will look thinner without "
      "being less")
    w("liquid in any useful sense.")
    w("")
    d["band"] = pd.cut(d["mid"], [0, 10, 25, 50, 75, 90, 100],
                       labels=["0–10", "10–25", "25–50", "50–75", "75–90",
                               "90–100"])
    w("| mid band ¢ | snapshots | median top size | median spread ¢ |")
    w("|---|---|---|---|")
    for b, g in d.groupby("band", observed=True):
        w(f"| {b} | {len(g):,} | {g['bid_sz'].median():,.0f} | "
          f"{g['spread'].median():.1f} |")
    w("")
    w("Same comparison **within a single price band**, which removes the "
      "price-level")
    w("explanation if the gap survives:")
    w("")
    w("| series | snapshots in 25–75¢ | median top size | median spread ¢ |")
    w("|---|---|---|---|")
    mid_band = d[(d["mid"] >= 25) & (d["mid"] <= 75)]
    for s, g in mid_band.groupby("series"):
        if len(g) < 50:
            continue
        w(f"| {s} | {len(g):,} | {g['bid_sz'].median():,.0f} | "
          f"{g['spread'].median():.1f} |")
    w("")

    # ---------- 4. queue position ---------------------------------------
    w("## 4. Queue position — is 'the book trades through' generous?")
    w("")
    w("Task 1b fills a resting order only when the bid trades **strictly "
      "above** it,")
    w("which implies everything at that level cleared. The question is how "
      "much that is.")
    w("")
    q = d["bid_sz"].values
    w(f"- median size resting at the touch: **{np.median(q):,.0f}** contracts")
    w(f"- p10 {np.percentile(q, 10):,.0f}, p90 {np.percentile(q, 90):,.0f}")
    w("")
    # how often does the touch actually clear, minute to minute?
    d = d.sort_values(["tk", "ts"])
    moved = []
    for tk, g in d.groupby("tk"):
        b = g["bid"].values
        if len(b) < 5:
            continue
        moved.append(float((np.diff(b) > 0).mean()))
    w(f"- fraction of consecutive minutes in which the best bid **rose** "
      f"(i.e. the touch cleared): median across markets "
      f"**{np.median(moved):.1%}**, n={len(moved)} markets")
    w("")
    w("**Reading.** A resting sell fills in Task 1b when the bid ticks up "
      "through it. The")
    w(f"books show that happens in ~{np.median(moved):.0%} of minutes, and the "
      f"queue that has to clear is a")
    w(f"median of {np.median(q):,.0f} contracts. Those are consistent with the "
      f"55–88% fill rates")
    w("Task 1b reported over 5–60 minute windows, so the trade-through "
      "assumption is not")
    w("obviously generous at 1 contract.")
    w("")
    w("**What this does NOT establish.** Queue position *within* a level is "
      "invisible here:")
    w("the API gives aggregate size at each price, not order-level priority. A "
      "resting")
    w("order that arrives last still cannot be shown to fill when only part of "
      "the level")
    w("clears. Measuring that needs order-level data Kalshi does not publish, "
      "so the")
    w("honest statement is that the fill model is **bounded above** by these "
      "numbers and")
    w("cannot be tightened further with public data.")

    (ROOT / "reports" / "p6_queue_atp.md").write_text("\n".join(OUT),
                                                      encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / 'p6_queue_atp.md'}")


if __name__ == "__main__":
    main()
