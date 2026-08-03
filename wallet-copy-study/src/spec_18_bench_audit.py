r"""Self-audit: the RANKING benchmark is pooled across categories. Does it matter?

Found by re-reading my own code rather than by a test failing.

`rank_within_category` scores wallets on `ex = edge - pooled_band_benchmark`,
where the benchmark is the mean edge at that price band across ALL categories.
The measurement side is fine -- `paired_excess_over_naive` compares selected
wallets against other positions in the SAME events, which is category-controlled
by construction. But the ranking side is not: if politics at 0.80 behaves
differently from crypto at 0.80, then ranking on a pooled benchmark
systematically favours wallets who happen to trade the bands where their category
diverges from the pool. That would be a selection artifact dressed as skill.

Two checks:
  1. Re-rank using a benchmark computed WITHIN politics only, and see whether the
     same result survives.
  2. Split the politics excess BY PRICE BAND, because the 2025-07 cut collapsed
     when the top band was dropped and that needs explaining rather than noting.
"""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import (  # noqa: E402
    PX_BANDS, band_of, bh_fdr, paired_excess_over_naive, rank_within_category,
)

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
OUT = ROOT / "reports" / "spec_bench_audit.json"

CAT = "politics"
FILT = {"min_trades": 20, "min_events": 10, "recent_within_days": 30,
        "max_gap_days": 30}
MIN_RANKED = 25
WINDOW_DAYS = 60

CUTS = []
for y, m in [(2024, 12)] + [(2025, m) for m in range(1, 13)] + \
            [(2026, m) for m in range(1, 4)]:
    CUTS.append((f"{y}-{m:02d}",
                 int(time.mktime(time.struct_time((y, m, 1, 0, 0, 0, 0, 1, 0))))))

MM = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])
rows = [json.loads(l) for l in PANEL.open(encoding="utf-8")]
print(f"{len(rows):,} panel rows", flush=True)


def band_bench(rs):
    b = defaultdict(lambda: [0, 0.0])
    for r in rs:
        e = b[band_of(r["px"])]
        e[0] += 1
        e[1] += r["edge"]
    return {k: v[1] / v[0] for k, v in b.items() if v[0]}


def apply_bench(rs, bench):
    for r in rs:
        r["ex"] = r["edge"] - bench.get(band_of(r["px"]), 0.0)


# ------------------------------------ 1. pooled vs within-category ranking
print("\n=== RANKING BENCHMARK: pooled (all categories) vs within-politics ===")
print(f"{'cut':>9} " + " ".join(f"{n:>22}" for n in ("pooled", "within-category")))
res = {"pooled": [], "within": []}
detail = []
tests = []
for label, cut in CUTS:
    end = cut + WINDOW_DAYS * 86400
    sel = [r for r in rows if r["ts"] < cut]
    mea = [r for r in rows if cut <= r["ts"] < end]
    if not sel or not mea:
        continue
    row = {"cut": label}
    for mode in ("pooled", "within"):
        src = sel if mode == "pooled" else [r for r in sel if r["cat"] == CAT]
        apply_bench(sel, band_bench(src))
        f2 = dict(FILT)
        f2["exclude"] = MM
        scores, _ = rank_within_category(sel, CAT, f2, None)
        if len(scores) < MIN_RANKED:
            row[mode] = None
            continue
        order = sorted(scores, key=lambda w: -scores[w])
        top = set(order[:max(len(order) // 10, 1)])
        pex = paired_excess_over_naive(mea, top, CAT)
        row[mode] = pex["excess_pp"] if pex else None
        row[mode + "_p"] = pex["p"] if pex else None
        row[mode + "_top"] = sorted(top)
        if pex:
            res[mode].append(pex["excess_pp"])
            tests.append((f"{mode}|{label}", pex["p"]))
    if row.get("pooled") is not None and row.get("within") is not None:
        ov = len(set(row["pooled_top"]) & set(row["within_top"]))
        row["top_overlap"] = ov
        row["top_n"] = len(row["pooled_top"])
        print(f"{label:>9} {row['pooled']:>+21.3f} {row['within']:>+22.3f}"
              f"   (top-decile overlap {ov}/{len(row['pooled_top'])})")
    detail.append({k: v for k, v in row.items() if not k.endswith("_top")})

summary = {}
for mode in ("pooled", "within"):
    a = np.array(res[mode])
    if a.size:
        summary[mode] = {
            "n_windows": int(a.size), "mean": round(float(a.mean()), 4),
            "median": round(float(np.median(a)), 4),
            "frac_positive": round(float((a > 0).mean()), 4),
            "sd": round(float(a.std(ddof=1)), 4)}
print("\n  pooled  :", summary.get("pooled"))
print("  within  :", summary.get("within"))
if summary.get("pooled") and summary.get("within"):
    d = summary["within"]["mean"] - summary["pooled"]["mean"]
    print(f"  -> within-category ranking changes the mean by {d:+.4f}pp "
          f"and %positive by "
          f"{summary['within']['frac_positive']-summary['pooled']['frac_positive']:+.1%}")

# ------------------------------------------- 2. excess by price band
print("\n=== POLITICS EXCESS BY PRICE BAND (pooled ranking, all windows) ===")
band_ex = defaultdict(list)
for label, cut in CUTS:
    end = cut + WINDOW_DAYS * 86400
    sel = [r for r in rows if r["ts"] < cut]
    mea = [r for r in rows if cut <= r["ts"] < end]
    if not sel or not mea:
        continue
    apply_bench(sel, band_bench(sel))
    f2 = dict(FILT)
    f2["exclude"] = MM
    scores, _ = rank_within_category(sel, CAT, f2, None)
    if len(scores) < MIN_RANKED:
        continue
    order = sorted(scores, key=lambda w: -scores[w])
    top = set(order[:max(len(order) // 10, 1)])
    for lo, hi in PX_BANDS:
        b = f"{lo:.2f}-{hi:.2f}"
        sub = [r for r in mea if band_of(r["px"]) == b]
        if len(sub) < 200:
            continue
        pex = paired_excess_over_naive(sub, top, CAT)
        if pex and pex["n_events"] >= 20:
            band_ex[b].append(pex["excess_pp"])

print(f"{'band':>12} {'windows':>8} {'mean':>9} {'median':>9} {'%pos':>7}")
bands_out = {}
for lo, hi in PX_BANDS:
    b = f"{lo:.2f}-{hi:.2f}"
    v = band_ex.get(b)
    if not v:
        continue
    a = np.array(v)
    bands_out[b] = {"n_windows": int(a.size), "mean": round(float(a.mean()), 4),
                    "median": round(float(np.median(a)), 4),
                    "frac_positive": round(float((a > 0).mean()), 4)}
    print(f"{b:>12} {a.size:>8} {a.mean():>+9.3f} {np.median(a):>+9.3f} "
          f"{float((a>0).mean()):>6.0%}")

report = {"meta": {"window_days": WINDOW_DAYS, "category": CAT,
                   "issue": "ranking benchmark was pooled across categories; "
                            "measurement was already category-controlled"},
          "ranking_benchmark_comparison": summary,
          "per_window": detail,
          "excess_by_band": bands_out,
          "bh_fdr": bh_fdr(tests) if tests else None}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
