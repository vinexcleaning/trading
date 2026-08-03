r"""Is politics special, or does the rolling method find edge everywhere?

Politics showed positive excess in 94% of 16 rolling windows. That is either a
strong result or a broken method, and only two checks can tell them apart:

  1. RUN EVERY CATEGORY. If crypto, nba, soccer and the rest also come out at
     ~94%, then the rolling design manufactures positives and politics is not
     special.
  2. RUN THE NULL. Permute wallet labels within each event -- destroying the
     link between a wallet and which side it took, changing nothing else -- and
     roll again. A method that finds edge in permuted data is measuring itself.

Both are run here at once, so the politics number can be read against its own
controls rather than in isolation.
"""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import random

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import (  # noqa: E402
    add_excess, paired_excess_over_naive, price_band_benchmark,
    rank_within_category,
)

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
OUT = ROOT / "reports" / "spec_rolling_control.json"

CATS = ["politics", "crypto", "nba", "soccer", "nfl", "esports", "other",
        "weather"]
FILT = {"min_trades": 20, "min_events": 10, "recent_within_days": 30,
        "max_gap_days": 30}
MIN_RANKED = 25
WINDOW_DAYS = 60
SEED = 20260801

CUTS = []
for y, m in [(2024, 12)] + [(2025, m) for m in range(1, 13)] + \
            [(2026, m) for m in range(1, 4)]:
    CUTS.append((f"{y}-{m:02d}",
                 int(time.mktime(time.struct_time((y, m, 1, 0, 0, 0, 0, 1, 0))))))

MM = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])

print("loading panel...", flush=True)
base_rows = [json.loads(l) for l in PANEL.open(encoding="utf-8")]
print(f"  {len(base_rows):,} rows")


def roll(rows, cats, label):
    out = {}
    for cat in cats:
        wins = []
        for clab, cut in CUTS:
            end = cut + WINDOW_DAYS * 86400
            sel = [r for r in rows if r["ts"] < cut]
            mea = [r for r in rows if cut <= r["ts"] < end]
            if not sel or not mea:
                continue
            add_excess(sel, price_band_benchmark(sel))
            add_excess(mea, price_band_benchmark(mea))
            f2 = dict(FILT)
            f2["exclude"] = MM
            scores, _ = rank_within_category(sel, cat, f2, None)
            if len(scores) < MIN_RANKED:
                continue
            order = sorted(scores, key=lambda w: -scores[w])
            top = set(order[:max(len(order) // 10, 1)])
            pex = paired_excess_over_naive(mea, top, cat)
            if pex:
                wins.append({"cut": clab, "excess_pp": pex["excess_pp"],
                             "p": pex["p"], "n_events": pex["n_events"]})
        if len(wins) < 5:
            continue
        ex = np.array([w["excess_pp"] for w in wins])
        out[cat] = {
            "n_windows": len(wins),
            "mean_pp": round(float(ex.mean()), 4),
            "median_pp": round(float(np.median(ex)), 4),
            "sd": round(float(ex.std(ddof=1)), 4),
            "frac_positive": round(float((ex > 0).mean()), 4),
            "n_sig_p05": int(sum(1 for w in wins if w["p"] < 0.05)),
            "min": round(float(ex.min()), 4), "max": round(float(ex.max()), 4),
            "windows": wins,
        }
        print(f"  [{label}] {cat:>9}: {len(wins):>2} windows  "
              f"mean {ex.mean():+7.3f}  median {np.median(ex):+7.3f}  "
              f"positive {float((ex>0).mean()):>5.0%}  "
              f"sig {out[cat]['n_sig_p05']:>2}", flush=True)
    return out


print("\n=== REAL DATA, ALL CATEGORIES ===")
real = roll(base_rows, CATS, "real")

print("\n=== NULL: wallet labels permuted within each event ===")
rng = random.Random(SEED)
perm_rows = [dict(r) for r in base_rows]
by_ev = defaultdict(list)
for i, r in enumerate(perm_rows):
    by_ev[r["ev"]].append(i)
n_perm = 0
for ev, idxs in by_ev.items():
    if len(idxs) < 2:
        continue
    ws = [perm_rows[i]["w"] for i in idxs]
    rng.shuffle(ws)
    for i, w in zip(idxs, ws):
        perm_rows[i]["w"] = w
    n_perm += 1
print(f"  permuted {n_perm:,} multi-position events; outcomes untouched")
null = roll(perm_rows, CATS, "null")

report = {"meta": {"window_days": WINDOW_DAYS, "n_cuts": len(CUTS),
                   "filters": FILT, "seed": SEED,
                   "null": "wallet labels permuted within event"},
          "real": real, "null": null}

print("\n=== REAL vs NULL ===")
print(f"{'category':>10} {'real mean':>10} {'real %pos':>10} {'real sig':>9} | "
      f"{'null mean':>10} {'null %pos':>10} {'null sig':>9}")
for cat in CATS:
    r = real.get(cat)
    nl = null.get(cat)
    if not r:
        continue
    print(f"{cat:>10} {r['mean_pp']:>10.3f} {r['frac_positive']:>9.0%} "
          f"{r['n_sig_p05']:>9} | " +
          (f"{nl['mean_pp']:>10.3f} {nl['frac_positive']:>9.0%} "
           f"{nl['n_sig_p05']:>9}" if nl else f"{'--':>10} {'--':>10} {'--':>9}"))

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
