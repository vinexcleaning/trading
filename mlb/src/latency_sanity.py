"""Is the +56s "window" real, or just an illiquid market?

THE CONFOUND. `inplay_rfi_latency.py` measured the gap from MLB's timestamp to
the first trade at a moved price, and found a median of +56s. But a trade
print only tells you when somebody DID trade. If KXMLBRFI only prints once a
minute anyway, then "56 seconds to react" is bounded below by the inter-trade
gap and says nothing about reaction speed.

So: measure the BASELINE inter-trade gap in the same markets at the same time
of day, away from any scoring play. If the baseline gap is ~50s, the finding
dissolves.

Also cleans up two obvious defects in that run:
  * max lag was 86,294s (24 hours) -- nonsense that polluted the mean
  * only 56 of 233 games joined; the rest are probably a UTC/ET date mismatch
"""
import glob
import json
import os
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..")
TAPE = os.path.join(ROOT, "..", "market-selection", "data", "tape_pmxt_window")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")

rows = json.load(open(os.path.join(REP, "inplay_rfi_latency.json"),
                      encoding="utf-8"))
print(f"{len(rows)} events from the latency run")

# ---- 1. how bad is the tail?
lags = [r["lag_s"] for r in rows if r["lag_s"] is not None]
sane = [x for x in lags if 0 <= x <= 900]
print(f"\nlags: n={len(lags)}, within 0..900s: {len(sane)} "
      f"({100*len(sane)/len(lags):.0f}%)")
print(f"  discarded as nonsense (>900s): "
      f"{[round(x) for x in sorted(lags) if x > 900]}")
if sane:
    s = sorted(sane)
    print(f"  SANE-ONLY lag: median {st.median(s):+.1f}s  "
          f"p25 {s[int(len(s)*.25)]:+.1f}  p75 {s[int(len(s)*.75)]:+.1f}  "
          f"max {s[-1]:+.1f}")

# ---- 2. the baseline inter-trade gap in the SAME markets
want = {r["ticker"] for r in rows}
feed_t = {r["ticker"]: datetime.fromisoformat(r["t_feed"].replace("Z", "+00:00"))
          for r in rows}
tr = defaultdict(list)
files = sorted(glob.glob(os.path.join(TAPE, "trades_*.jsonl")))
print(f"\nre-scanning {len(files)} tape files for {len(want)} tickers ...",
      flush=True)
for f in files:
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            if "KXMLBRFI" not in line:
                continue
            try:
                t = json.loads(line)
            except ValueError:
                continue
            tk = t.get("ticker")
            if tk not in want:
                continue
            try:
                ts = datetime.fromisoformat(
                    t["created_time"].replace("Z", "+00:00"))
                px = float(t["yes_price_dollars"]) * 100
            except (KeyError, ValueError, TypeError):
                continue
            tr[tk].append((ts, px))
print(f"  {sum(len(v) for v in tr.values()):,} trades")

gaps_pre, gaps_all = [], []
per_mkt = []
for tk, xs in tr.items():
    xs.sort()
    tf = feed_t.get(tk)
    if not tf or len(xs) < 5:
        continue
    # baseline: gaps in the 20 minutes BEFORE the scoring play
    pre = [x for x in xs if tf - timedelta(minutes=20) <= x[0] < tf]
    g = [(pre[i + 1][0] - pre[i][0]).total_seconds()
         for i in range(len(pre) - 1)]
    if g:
        gaps_pre += g
        per_mkt.append(st.median(g))
    allg = [(xs[i + 1][0] - xs[i][0]).total_seconds()
            for i in range(len(xs) - 1)]
    gaps_all += [x for x in allg if x < 3600]

print("\n" + "=" * 66)
print("BASELINE INTER-TRADE GAP (no event) vs the measured LAG")
print("=" * 66)
if gaps_pre:
    gp = sorted(gaps_pre)
    print(f"  gaps in the 20 min BEFORE the run: n={len(gp)}")
    print(f"    median {st.median(gp):.1f}s   p75 {gp[int(len(gp)*.75)]:.1f}s"
          f"   p90 {gp[int(len(gp)*.9)]:.1f}s")
    print(f"  per-market median gap: median of medians "
          f"{st.median(per_mkt):.1f}s  (n={len(per_mkt)} markets)")
if sane:
    print(f"\n  measured lag (sane only): median {st.median(sane):.1f}s")
if gaps_pre and sane:
    ratio = st.median(sane) / max(st.median(gaps_pre), 1e-9)
    print(f"\n  lag / baseline gap = {ratio:.2f}x")
    if ratio < 2:
        print("  => THE 'WINDOW' IS MOSTLY JUST AN ILLIQUID MARKET.")
        print("     The time to the next moved trade is dominated by the time")
        print("     to the NEXT TRADE AT ALL. This is not a reaction-speed")
        print("     measurement and must not be reported as one.")
    else:
        print("  => the lag is materially longer than the normal trade gap,")
        print("     so it is not purely an artefact of quietness.")

# ---- 3. how much trades in the 60s after the run, at ANY price?
print("\n" + "=" * 66)
print("LIQUIDITY IN THE 60 SECONDS AFTER THE RUN")
print("=" * 66)
vols, cnts = [], []
for tk, xs in tr.items():
    tf = feed_t.get(tk)
    if not tf:
        continue
    w = [x for x in xs if tf <= x[0] <= tf + timedelta(seconds=60)]
    cnts.append(len(w))
print(f"  trades printed in that window: median {st.median(cnts):.0f}  "
      f"mean {st.mean(cnts):.1f}  zero-trade markets "
      f"{sum(1 for c in cnts if c == 0)} of {len(cnts)}")
print("\n  If most markets print ZERO trades in the 60s after a run, then")
print("  there is nobody to trade against inside the supposed window, and")
print("  the 'opportunity' cannot be taken regardless of its length.")
