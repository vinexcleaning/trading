r"""Two open questions closed: politics at a THIRD cut, and what 'other' really is.

1. THIRD CUT. Politics was positive in 42/42 specifications, but across only two
   split points. Two is the minimum, not comfort -- a result that holds at two
   cuts and dies at a third was never robust. An earlier window is added and the
   whole specification grid re-run on it.

2. DECOMPOSING 'other'. It is 20.1% of volume, it was significant at one cut and
   dead at the next, and it is a BUCKET rather than a category -- so a positive
   there means almost nothing until it is broken into real things. Sub-categories
   are derived from slug/tag structure and each is tested on its own.

Same guards throughout: selection on period 1 only with a look-ahead assertion,
paired copier-vs-naive test (never copier-vs-zero), event clustering, BH-FDR.
"""
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import (  # noqa: E402
    add_excess, assert_no_lookahead, band_of, bh_fdr, measure,
    naive_benchmark, paired_excess_over_naive, price_band_benchmark,
    rank_within_category,
)

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
UNI = ROOT / "data" / "markets_clob.jsonl"
CATMAP = ROOT / "data" / "spec_cid_category.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
OUT = ROOT / "reports" / "spec_thirdcut_other.json"

CUTS = [("2025-01-01_THIRD", 1735689600),
        ("2025-07-01", 1751328000),
        ("2026-01-08_fee_era", 1767830400)]
FILTER_SETS = {
    "F1_min20": {"min_trades": 20, "min_events": 10},
    "F2_min50": {"min_trades": 50, "min_events": 20},
    "F4_min20_cadence": {"min_trades": 20, "min_events": 10,
                         "recent_within_days": 30, "max_gap_days": 30},
    "F6_min20_all": {"min_trades": 20, "min_events": 10,
                     "recent_within_days": 30, "max_gap_days": 30,
                     "use_mm_filter": True},
}
HALF_LIVES = [None, 30, 90]
MIN_RANKED = 30

MM = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])

# ------------------------------------------ sub-categorise the 'other' bucket
SUB_RULES = [
    ("hockey", (r"^nhl-", r"\bnhl\b")),
    ("baseball", (r"^mlb-", r"\bmlb\b")),
    ("tennis", (r"^(atp|wta|tennis)-", r"\btennis\b")),
    ("mma_boxing", (r"^(ufc|mma|box)-", r"\bufc\b", r"\bboxing\b")),
    ("motorsport", (r"^(f1|nascar|motogp)-", r"\bformula\b")),
    ("golf", (r"^(pga|golf)-", r"\bgolf\b")),
    ("cricket", (r"^(cricket|ipl)-", r"\bcricket\b")),
    ("awards_culture", (r"(oscar|grammy|emmy|album|movie|box-office|rotten|"
                        r"spotify|netflix|billboard)",)),
    ("tech_ai", (r"(openai|gpt|-ai-|anthropic|nvidia|apple|tesla|spacex|nasa)",)),
    ("finance_macro", (r"(fed-|cpi|inflation|gdp|unemployment|rate-cut|"
                       r"recession|s-p-500|nasdaq|stock)",)),
    ("mentions_speech", (r"(will-.*-say|mention|tweet|post-.*-times)",)),
]
SUB_RULES = [(c, tuple(re.compile(p) for p in ps)) for c, ps in SUB_RULES]


def subcat(slug, question):
    s = f"{slug or ''} {question or ''}".lower()
    for c, pats in SUB_RULES:
        if any(p.search(s) for p in pats):
            return c
    return "other_residual"


print("loading category map + slugs for the 'other' bucket...", flush=True)
other_cids = set()
for line in CATMAP.open(encoding="utf-8"):
    r = json.loads(line)
    if r["cat"] == "other":
        other_cids.add(r["cid"])
print(f"  {len(other_cids):,} markets currently labelled 'other'")

sub_of = {}
n = 0
for line in UNI.open(encoding="utf-8"):
    m = json.loads(line)
    cid = m["condition_id"]
    if cid in other_cids:
        sub_of[cid] = subcat(m.get("slug"), m.get("question"))
    n += 1
    if n % 800_000 == 0:
        print(f"  scanned {n:,}", flush=True)
print(f"  sub-categorised {len(sub_of):,}: "
      f"{dict(Counter(sub_of.values()).most_common())}")

print("\nloading panel...", flush=True)
rows = []
for line in PANEL.open(encoding="utf-8"):
    r = json.loads(line)
    if r["cat"] == "other":
        r["cat"] = sub_of.get(r["cid"], "other_residual")
    rows.append(r)
print(f"  {len(rows):,} rows; categories now "
      f"{len(set(r['cat'] for r in rows))}")

vol = defaultdict(float)
for r in rows:
    vol[r["cat"]] += r["cost"]
tot_v = sum(vol.values())
print("  volume share by category (after decomposition):")
for k, v in sorted(vol.items(), key=lambda kv: -kv[1]):
    print(f"    {k:>18}: {v/tot_v:>7.2%}  ${v:>14,.0f}")

CATS = [c for c, v in sorted(vol.items(), key=lambda kv: -kv[1])
        if v / tot_v >= 0.002]
print(f"\n  testing {len(CATS)} categories with >=0.2% of volume")

report = {"meta": {"cuts": [c[0] for c in CUTS], "categories": CATS,
                   "volume_share": {k: round(v / tot_v, 5)
                                    for k, v in sorted(vol.items(),
                                                       key=lambda kv: -kv[1])},
                   "subcategory_counts": dict(Counter(sub_of.values()))},
          "results": [], "lookahead": []}
tests = []

for cut_label, cut in CUTS:
    sel = [r for r in rows if r["ts"] < cut]
    mea = [r for r in rows if r["ts"] >= cut]
    la = assert_no_lookahead(sel, mea, cut, cut_label)
    la["cut_label"] = cut_label
    report["lookahead"].append(la)
    print(f"\n--- {cut_label}: sel {len(sel):,} / meas {len(mea):,} "
          f"({la['verdict']}) ---", flush=True)
    add_excess(sel, price_band_benchmark(sel))
    add_excess(mea, price_band_benchmark(mea))

    for fname, fdef in FILTER_SETS.items():
        filt = dict(fdef)
        if filt.pop("use_mm_filter", False):
            filt["exclude"] = MM
        for hl in HALF_LIVES:
            hlab = "unweighted" if hl is None else f"hl{hl}d"
            for cat in CATS:
                scores, diag = rank_within_category(sel, cat, filt, hl)
                if len(scores) < MIN_RANKED:
                    continue
                order = sorted(scores, key=lambda w: -scores[w])
                k = max(len(order) // 10, 1)
                top = set(order[:k])
                res, mrows = measure(mea, top, cat, sizing="equal")
                if res is None or res["n_events"] < 5:
                    continue
                pex = paired_excess_over_naive(mea, top, cat)
                if not pex:
                    continue
                key = f"{cut_label}|{fname}|{hlab}|{cat}"
                report["results"].append({
                    "cut": cut_label, "filters": fname, "weighting": hlab,
                    "category": cat, "n_wallets_ranked": len(scores),
                    "n_top": k, "copier": res,
                    "naive": naive_benchmark(
                        mea, cat, {band_of(r["px"]) for r in mrows}),
                    "paired": pex})
                tests.append((key, pex["p"]))

report["bh_fdr"] = bh_fdr(tests) if tests else None
print(f"\n  {len(report['results'])} results; BH-FDR "
      f"{report['bh_fdr']['n_significant'] if report['bh_fdr'] else 0} of "
      f"{len(tests)} significant")

# --------------------------------- consistency across ALL THREE cuts
print("\n=== CONSISTENCY BY CATEGORY ACROSS THREE CUTS ===")
print(f"{'category':>18} {'cut':>20} {'specs':>6} {'pos':>5} {'sig':>4} "
      f"{'median excess':>14} {'range':>22}")
cons = {}
byc = defaultdict(list)
for r in report["results"]:
    byc[(r["category"], r["cut"])].append(r)
fdr = report["bh_fdr"]["detail"] if report["bh_fdr"] else {}
for (cat, cut), rs in sorted(byc.items()):
    ex = sorted(x["paired"]["excess_pp"] for x in rs)
    npos = sum(1 for v in ex if v > 0)
    nsig = sum(1 for x in rs if fdr.get(
        f"{x['cut']}|{x['filters']}|{x['weighting']}|{x['category']}",
        {}).get("significant"))
    cons[f"{cat}|{cut}"] = {"n": len(rs), "n_positive": npos,
                            "n_significant": nsig,
                            "median_excess_pp": round(ex[len(ex) // 2], 4),
                            "min": round(ex[0], 4), "max": round(ex[-1], 4)}
    print(f"{cat:>18} {cut:>20} {len(rs):>6} {npos:>5} {nsig:>4} "
          f"{ex[len(ex)//2]:>14.3f}  [{ex[0]:>8.3f},{ex[-1]:>8.3f}]")
report["consistency"] = cons

# --------------------------------- which categories survive ALL cuts positive
print("\n=== CATEGORIES POSITIVE IN EVERY SPECIFICATION AT EVERY CUT ===")
allcuts = defaultdict(list)
for k, v in cons.items():
    cat = k.split("|")[0]
    allcuts[cat].append(v)
survivors = {}
for cat, vs in sorted(allcuts.items()):
    if len(vs) < len(CUTS):
        continue
    all_pos = all(v["n_positive"] == v["n"] for v in vs)
    tot_specs = sum(v["n"] for v in vs)
    tot_sig = sum(v["n_significant"] for v in vs)
    meds = [v["median_excess_pp"] for v in vs]
    survivors[cat] = {"all_specs_positive_at_every_cut": all_pos,
                      "n_specs": tot_specs, "n_significant": tot_sig,
                      "medians_by_cut": meds}
    flag = "SURVIVES" if all_pos else "fails"
    print(f"  {cat:>18}: {flag:>8}  specs={tot_specs:>3}  sig={tot_sig:>3}  "
          f"medians={[round(m,3) for m in meds]}")
report["survives_all_cuts"] = survivors

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
