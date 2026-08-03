r"""Rolling out-of-sample windows: replace three arbitrary cuts with a distribution.

Every result so far rests on three hand-picked split points, and the sizing sweep
showed that outcomes swing between +252% and -82% on neighbouring configurations.
Three windows cannot distinguish "this works" from "this happened to work three
times", and picking the config that was positive on those three is selecting a
parameter on the evaluation data.

So: roll the cut monthly. At each cut, rank on EVERYTHING before it and measure
on a FIXED 60-day window after it. Fixed length matters -- using "all data after
the cut" gives early cuts long measurement windows and late cuts short ones, and
the resulting comparison is between window lengths rather than between periods.

Reports two things per window, because they answer different questions:
  - per-position EXCESS over the naive benchmark, which tests whether the edge
    exists;
  - simulated bankroll RETURN at a fixed sizing, which tests whether it can be
    harvested.
The gap between how stable those two are is the entire story of this session.
"""
import json
import sys
import time
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import (  # noqa: E402
    add_excess, fee, paired_excess_over_naive, price_band_benchmark,
    rank_within_category,
)

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
BOOKS = [ROOT / "data" / "spec_task5_fills.jsonl",
         ROOT / "data" / "exit_fills.jsonl", ROOT / "data" / "fills.jsonl"]
OUT = ROOT / "reports" / "spec_rolling_windows.json"

CAT = "politics"
FILT = {"min_trades": 20, "min_events": 10, "recent_within_days": 30,
        "max_gap_days": 30}
MIN_RANKED = 25
DELAY, MAX_LOOKAHEAD = 60, 3600
WINDOW_DAYS = 60
BANKROLL, STAKE_FRAC, CAP = 10_000.0, 0.01, 1.00
COST_PP = 1.000   # CORRECTED: 10-level book gives 1.000pp at $200, not 0.675

# monthly cuts from 2024-12 through 2026-03 (last window must fit before the
# subgraph's 2026-04-28 horizon)
CUTS = []
for y, m in [(2024, 12)] + [(2025, m) for m in range(1, 13)] + \
            [(2026, m) for m in range(1, 4)]:
    CUTS.append((f"{y}-{m:02d}",
                 int(time.mktime(time.struct_time((y, m, 1, 0, 0, 0, 0, 1, 0))))))

MM = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])

print("loading books...", flush=True)
bts, bpx = defaultdict(list), defaultdict(list)
for p in BOOKS:
    if not p.exists():
        continue
    for line in p.open(encoding="utf-8"):
        try:
            f = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        t = f.get("token")
        if t is None:
            continue
        bts[t].append(f["ts"])
        bpx[t].append(f["price"])
for t in bts:
    z = sorted(zip(bts[t], bpx[t]))
    bts[t] = [a for a, _ in z]
    bpx[t] = [b for _, b in z]
print(f"  {len(bts):,} tokens")


def px_at(tok, when):
    ts = bts.get(tok)
    if not ts:
        return None
    i = bisect_left(ts, when)
    if i >= len(ts) or ts[i] - when > MAX_LOOKAHEAD:
        return None
    return bpx[tok][i]


rows = [json.loads(l) for l in PANEL.open(encoding="utf-8")]
print(f"  {len(rows):,} panel rows")

stake = BANKROLL * STAKE_FRAC
results = []
print(f"\n{'cut':>9} {'nRank':>6} {'nTop':>5} {'excess':>8} {'CI95':>20} "
      f"{'p':>7} {'nEv':>6} {'sigs':>6} {'taken':>6} {'return':>9}")

for label, cut in CUTS:
    end = cut + WINDOW_DAYS * 86400
    sel = [r for r in rows if r["ts"] < cut]
    mea = [r for r in rows if cut <= r["ts"] < end]
    if not sel or not mea:
        continue
    add_excess(sel, price_band_benchmark(sel))
    add_excess(mea, price_band_benchmark(mea))
    f2 = dict(FILT)
    f2["exclude"] = MM
    scores, _ = rank_within_category(sel, CAT, f2, None)
    if len(scores) < MIN_RANKED:
        continue
    order = sorted(scores, key=lambda w: -scores[w])
    k = max(len(order) // 10, 1)
    top = set(order[:k])

    pex = paired_excess_over_naive(mea, top, CAT)

    sig = []
    for r in sorted((x for x in mea if x["cat"] == CAT and x["w"] in top),
                    key=lambda x: x["ts"]):
        p = px_at(r["tok"], r["ts"] + DELAY)
        if p is None:
            continue
        eff = p + COST_PP / 100.0
        if 0 < eff < 1:
            sig.append((r["ts"], eff, r["outcome"],
                        r.get("end_ts") or r["ts"] + 86400 * 30))

    cash, open_pos, committed, taken = BANKROLL, [], 0.0, 0
    for ts, eff, outcome, res_ts in sig:
        keep = []
        for rts, payout, amt in open_pos:
            if rts <= ts:
                cash += payout
                committed -= amt
            else:
                keep.append((rts, payout, amt))
        open_pos = keep
        if cash < stake or committed + stake > CAP * BANKROLL:
            continue
        shares = stake / eff
        cash -= stake
        committed += stake
        open_pos.append((res_ts, shares * outcome - fee(eff) * shares, stake))
        taken += 1
    for _, payout, _ in open_pos:
        cash += payout
    ret = (cash - BANKROLL) / BANKROLL * 100

    row = {"cut": label, "n_ranked": len(scores), "n_top": k,
           "excess_pp": pex["excess_pp"] if pex else None,
           "excess_ci95": pex["ci95"] if pex else None,
           "excess_p": pex["p"] if pex else None,
           "n_events": pex["n_events"] if pex else 0,
           "n_signals": len(sig), "n_taken": taken,
           "return_pct": round(ret, 2)}
    results.append(row)
    print(f"{label:>9} {len(scores):>6} {k:>5} "
          f"{(pex['excess_pp'] if pex else float('nan')):>8.3f} "
          f"{str(pex['ci95']) if pex else '':>20} "
          f"{(pex['p'] if pex else 1):>7.4f} "
          f"{(pex['n_events'] if pex else 0):>6,} {len(sig):>6,} {taken:>6,} "
          f"{ret:>8.1f}%")

ex = np.array([r["excess_pp"] for r in results if r["excess_pp"] is not None])
rt = np.array([r["return_pct"] for r in results])

summary = {
    "n_windows": len(results),
    "window_days": WINDOW_DAYS,
    "sizing": {"stake_frac": STAKE_FRAC, "exposure_cap": CAP},
    "excess_pp": {
        "mean": round(float(ex.mean()), 4), "median": round(float(np.median(ex)), 4),
        "sd": round(float(ex.std(ddof=1)), 4),
        "min": round(float(ex.min()), 4), "max": round(float(ex.max()), 4),
        "frac_positive": round(float((ex > 0).mean()), 4),
        "n_significant_p05": int(sum(
            1 for r in results if r["excess_p"] is not None and r["excess_p"] < 0.05)),
    } if ex.size else None,
    "return_pct": {
        "mean": round(float(rt.mean()), 3), "median": round(float(np.median(rt)), 3),
        "sd": round(float(rt.std(ddof=1)), 3),
        "min": round(float(rt.min()), 3), "max": round(float(rt.max()), 3),
        "frac_positive": round(float((rt > 0).mean()), 4),
    } if rt.size else None,
    "windows": results,
}
OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")

print(f"\n=== {len(results)} ROLLING WINDOWS ({WINDOW_DAYS}d each) ===")
if ex.size:
    e = summary["excess_pp"]
    print(f"  EXCESS pp : mean {e['mean']:+.3f}  median {e['median']:+.3f}  "
          f"sd {e['sd']:.3f}  range [{e['min']:+.2f}, {e['max']:+.2f}]")
    print(f"              positive in {e['frac_positive']:.0%} of windows, "
          f"{e['n_significant_p05']} significant at p<0.05")
if rt.size:
    v = summary["return_pct"]
    print(f"  RETURN %  : mean {v['mean']:+.1f}  median {v['median']:+.1f}  "
          f"sd {v['sd']:.1f}  range [{v['min']:+.1f}, {v['max']:+.1f}]")
    print(f"              positive in {v['frac_positive']:.0%} of windows")
print(f"\nwrote {OUT}")
