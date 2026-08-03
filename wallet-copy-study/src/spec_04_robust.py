r"""Tasks 2 and 3: robustness across the whole specification grid, and the
specialist-vs-generalist comparison.

262 real results were produced across 7 filter sets x 3 weightings x 8
categories x 2 cuts. Reporting the best-looking one would be cherry-picking, so
this asks the only question that matters about a grid that size: **is the effect
consistent across specifications, or does it live in a handful of them?**

Each result is also carried to a NET number. Every figure out of spec_03 is gross
of the bid-ask spread, and this project's own spread floor -- the median
same-block trade-price dispersion -- is 1.0pp, itself a lower bound because the
subgraph carries no book. A copier crosses once on entry, so 1.0pp is subtracted
to compare like with like against the generalist result.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "reports" / "spec_task2_real.json"
SYN = ROOT / "reports" / "spec_task2_synthetic.json"
OUT = ROOT / "reports" / "spec_task3_comparison.json"

SPREAD_PP = 1.0          # lower bound, from same-block trade dispersion
GEN = {"2025-07-01": 0.9374, "2026-01-08_fee_era": -0.1348}

real = json.loads(REAL.read_text(encoding="utf-8"))
syn = json.loads(SYN.read_text(encoding="utf-8"))

R = [r for r in real["results"] if r.get("paired_excess_over_naive")]
S = [r for r in syn["results"] if r.get("paired_excess_over_naive")]
print(f"real results {len(R)}, synthetic results {len(S)}")

rfdr = real["bh_fdr"]["detail"]
sfdr = syn["bh_fdr"]["detail"]


def key(r):
    return f"{r['cut']}|{r['filters']}|{r['weighting']}|{r['category']}"


# ------------------------------------------- consistency by category
print("\n=== CONSISTENCY BY CATEGORY (across all filter sets and weightings) ===")
print(f"{'category':>9} {'cut':>20} {'n_spec':>7} {'n_pos':>6} {'n_sig':>6} "
      f"{'median excess':>14} {'min':>8} {'max':>8}")
bycat = defaultdict(list)
for r in R:
    bycat[(r["category"], r["cut"])].append(r)

consistency = {}
for (cat, cut), rs in sorted(bycat.items()):
    ex = sorted(x["paired_excess_over_naive"]["excess_pp"] for x in rs)
    npos = sum(1 for v in ex if v > 0)
    nsig = sum(1 for x in rs if rfdr.get(key(x), {}).get("significant"))
    med = ex[len(ex) // 2]
    consistency[f"{cat}|{cut}"] = {
        "n_specifications": len(rs), "n_positive": npos, "n_significant": nsig,
        "median_excess_pp": round(med, 4),
        "min_excess_pp": round(ex[0], 4), "max_excess_pp": round(ex[-1], 4),
        "frac_positive": round(npos / len(rs), 3),
    }
    print(f"{cat:>9} {cut:>20} {len(rs):>7} {npos:>6} {nsig:>6} "
          f"{med:>14.3f} {ex[0]:>8.3f} {ex[-1]:>8.3f}")

# ------------------------------------------- which filters mattered
print("\n=== WHICH FILTERS MATTERED ===")
print(f"{'filter set':>18} {'n_spec':>7} {'n_sig':>6} {'median excess':>14} "
      f"{'median n_eff':>13} {'median nW':>10}")
byfilt = defaultdict(list)
for r in R:
    byfilt[r["filters"]].append(r)
filters_report = {}
for f, rs in sorted(byfilt.items()):
    ex = sorted(x["paired_excess_over_naive"]["excess_pp"] for x in rs)
    eff = sorted(x["paired_excess_over_naive"]["n_eff"] for x in rs)
    nw = sorted(x["n_wallets_ranked"] for x in rs)
    nsig = sum(1 for x in rs if rfdr.get(key(x), {}).get("significant"))
    filters_report[f] = {
        "n_specifications": len(rs), "n_significant": nsig,
        "median_excess_pp": round(ex[len(ex) // 2], 4),
        "median_n_eff": eff[len(eff) // 2],
        "median_wallets_ranked": nw[len(nw) // 2],
    }
    print(f"{f:>18} {len(rs):>7} {nsig:>6} {ex[len(ex)//2]:>14.3f} "
          f"{eff[len(eff)//2]:>13.1f} {nw[len(nw)//2]:>10}")

print("\n=== WHICH WEIGHTING MATTERED (recency half-life) ===")
print(f"{'weighting':>14} {'n_spec':>7} {'n_sig':>6} {'median excess':>14}")
byw = defaultdict(list)
for r in R:
    byw[r["weighting"]].append(r)
weight_report = {}
for w, rs in sorted(byw.items()):
    ex = sorted(x["paired_excess_over_naive"]["excess_pp"] for x in rs)
    nsig = sum(1 for x in rs if rfdr.get(key(x), {}).get("significant"))
    weight_report[w] = {"n_specifications": len(rs), "n_significant": nsig,
                        "median_excess_pp": round(ex[len(ex) // 2], 4)}
    print(f"{w:>14} {len(rs):>7} {nsig:>6} {ex[len(ex)//2]:>14.3f}")

# ------------------------------------------- real vs synthetic
rex = sorted(x["paired_excess_over_naive"]["excess_pp"] for x in R)
sex = sorted(x["paired_excess_over_naive"]["excess_pp"] for x in S)
control = {
    "real": {"n": len(rex), "median_pp": round(rex[len(rex) // 2], 4),
             "frac_positive": round(sum(1 for v in rex if v > 0) / len(rex), 3),
             "n_significant_bh": real["bh_fdr"]["n_significant"]},
    "synthetic": {"n": len(sex), "median_pp": round(sex[len(sex) // 2], 4),
                  "frac_positive": round(sum(1 for v in sex if v > 0) / len(sex), 3),
                  "n_significant_bh": syn["bh_fdr"]["n_significant"]},
}
print("\n=== CONTROL DISCRIMINATION ===")
print(f"  real      : median excess {control['real']['median_pp']:>7.3f}pp  "
      f"{control['real']['frac_positive']:.1%} positive  "
      f"{control['real']['n_significant_bh']}/{len(rex)} significant")
print(f"  synthetic : median excess {control['synthetic']['median_pp']:>7.3f}pp  "
      f"{control['synthetic']['frac_positive']:.1%} positive  "
      f"{control['synthetic']['n_significant_bh']}/{len(sex)} significant")

# ------------------------------- TASK 3: specialist vs generalist
print("\n=== TASK 3: SPECIALIST vs GENERALIST (F6_min20_all, unweighted) ===")
print(f"{'cut':>20} {'category':>9} {'copier gross':>13} {'copier net':>11} "
      f"{'naive':>8} {'excess':>8} {'p':>8} {'BH':>5} {'n_ev':>7} {'n_eff':>8} "
      f"{'generalist':>11}")
task3 = []
for r in R:
    if r["filters"] != "F6_min20_all" or r["weighting"] != "unweighted":
        continue
    pe = r["paired_excess_over_naive"]
    c = r["copier"]
    sig = rfdr.get(key(r), {}).get("significant", False)
    row = {
        "cut": r["cut"], "category": r["category"],
        "copier_gross_pp": c["mean_pp"],
        "copier_net_of_spread_pp": round(c["mean_pp"] - SPREAD_PP, 4),
        "copier_ci95": c["ci95"],
        "naive_pp": r["naive_benchmark"]["mean_pp"] if r["naive_benchmark"] else None,
        "excess_over_naive_pp": pe["excess_pp"], "excess_ci95": pe["ci95"],
        "p": pe["p"], "significant_bh": sig,
        "n_events": pe["n_events"], "n_eff": pe["n_eff"],
        "n_selected_obs": pe["n_selected_obs"],
        "generalist_copier_pp": GEN.get(r["cut"]),
        "specialist_minus_generalist_pp": round(
            c["mean_pp"] - GEN.get(r["cut"], 0.0), 4),
    }
    task3.append(row)
    print(f"{r['cut']:>20} {r['category']:>9} {c['mean_pp']:>13.3f} "
          f"{row['copier_net_of_spread_pp']:>11.3f} "
          f"{(row['naive_pp'] or 0):>8.3f} {pe['excess_pp']:>8.3f} "
          f"{pe['p']:>8.4f} {str(sig):>5} {pe['n_events']:>7,} "
          f"{pe['n_eff']:>8.1f} {GEN.get(r['cut'], 0):>11.3f}")

report = {
    "meta": {
        "n_real_results": len(R), "n_synthetic_results": len(S),
        "spread_pp_applied": SPREAD_PP,
        "spread_note": "median same-block trade-price dispersion; a LOWER bound "
                       "on the quoted spread, so net figures are optimistic",
        "generalist_reference": GEN,
        "unit_of_observation": "event (a game, or a recurring series-day)",
    },
    "control_discrimination": control,
    "consistency_by_category": consistency,
    "filters_report": filters_report,
    "weighting_report": weight_report,
    "task3_table": task3,
    "pooled_real": real["pooled"],
    "pooled_synthetic": syn["pooled"],
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
