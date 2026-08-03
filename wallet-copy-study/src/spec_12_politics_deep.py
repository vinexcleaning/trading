r"""Stress-test the politics finding, and characterise what 'other_residual' is.

Politics is now positive in 36/36 specifications across three cuts. That is the
strongest thing this project has found, which is exactly why it should be
attacked rather than celebrated. Concentration is the obvious way it could still
be worthless:

  - if the edge lives in ONE event (an election night), it is one bet, not a
    strategy;
  - if it lives in ONE wallet, the top decile is a rounding error around a
    single lucky trader;
  - if it lives in ONE price band, it is favourite-longshot exposure wearing a
    category label;
  - if it lives in ONE month, it is a regime, not an edge.

Each is tested by leave-one-out: drop the largest contributor and see whether the
result holds. A finding that survives dropping its biggest single event is much
harder to dismiss than one that does not.

`other_residual` is also characterised, because "residual" is not something
anyone can trade and calling it a winner without knowing what it contains would
be dishonest.
"""
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import (  # noqa: E402
    add_excess, band_of, bh_fdr, fee, paired_excess_over_naive,
    price_band_benchmark, rank_within_category,
)

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
UNI = ROOT / "data" / "markets_clob.jsonl"
CATMAP = ROOT / "data" / "spec_cid_category.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
OUT = ROOT / "reports" / "spec_politics_deep.json"

CUTS = [("2025-01-01", 1735689600), ("2025-07-01", 1751328000),
        ("2026-01-08_fee_era", 1767830400)]
FILT = {"min_trades": 20, "min_events": 10, "recent_within_days": 30,
        "max_gap_days": 30}
MIN_RANKED = 30
MM = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])

print("loading panel...", flush=True)
rows = [json.loads(l) for l in PANEL.open(encoding="utf-8")]
pol = [r for r in rows if r["cat"] == "politics"]
print(f"  {len(rows):,} rows, {len(pol):,} politics")

report = {"meta": {"filters": FILT, "cuts": [c[0] for c in CUTS]},
          "concentration": {}, "leave_one_out": {}, "other_residual": {}}
tests = []

for cut_label, cut in CUTS:
    sel = [r for r in rows if r["ts"] < cut]
    mea = [r for r in rows if r["ts"] >= cut]
    add_excess(sel, price_band_benchmark(sel))
    add_excess(mea, price_band_benchmark(mea))
    f2 = dict(FILT)
    f2["exclude"] = MM
    scores, _ = rank_within_category(sel, "politics", f2, None)
    if len(scores) < MIN_RANKED:
        print(f"  {cut_label}: too few ranked ({len(scores)})")
        continue
    order = sorted(scores, key=lambda w: -scores[w])
    k = max(len(order) // 10, 1)
    top = set(order[:k])

    base = paired_excess_over_naive(mea, top, "politics")
    if not base:
        continue
    print(f"\n=== {cut_label}: {len(scores)} ranked, top {k}, "
          f"base excess {base['excess_pp']:+.3f}pp "
          f"CI{base['ci95']} n_ev={base['n_events']} ===", flush=True)
    tests.append((f"pol|{cut_label}|base", base["p"]))

    sel_rows = [r for r in mea if r["cat"] == "politics" and r["w"] in top]

    # ---------- concentration diagnostics
    by_ev = Counter()
    by_w = Counter()
    by_band = Counter()
    by_month = Counter()
    for r in sel_rows:
        by_ev[r["ev"]] += r["cost"]
        by_w[r["w"]] += r["cost"]
        by_band[band_of(r["px"])] += r["cost"]
        by_month[time.strftime("%Y-%m", time.gmtime(r["ts"]))] += r["cost"]
    tot = sum(by_ev.values()) or 1.0
    conc = {
        "n_positions": len(sel_rows), "n_events": len(by_ev),
        "n_wallets": len(by_w),
        "top_event_share": round(by_ev.most_common(1)[0][1] / tot, 4),
        "top5_event_share": round(
            sum(v for _, v in by_ev.most_common(5)) / tot, 4),
        "top_wallet_share": round(by_w.most_common(1)[0][1] / tot, 4),
        "top_month_share": round(by_month.most_common(1)[0][1] / tot, 4),
        "band_shares": {b: round(v / tot, 4) for b, v in by_band.most_common()},
        "top_events": [(e[:48], round(v / tot, 4)) for e, v in by_ev.most_common(5)],
        "top_months": [(m, round(v / tot, 4)) for m, v in by_month.most_common(4)],
    }
    report["concentration"][cut_label] = conc
    print(f"  concentration: top event {conc['top_event_share']:.1%}, "
          f"top-5 events {conc['top5_event_share']:.1%}, "
          f"top wallet {conc['top_wallet_share']:.1%}, "
          f"top month {conc['top_month_share']:.1%}")
    print(f"  bands: {conc['band_shares']}")

    # ---------- leave-one-out
    loo = {}
    drop_ev = by_ev.most_common(1)[0][0]
    drop_w = by_w.most_common(1)[0][0]
    drop_m = by_month.most_common(1)[0][0]
    variants = {
        "drop_largest_event": lambda r: r["ev"] != drop_ev,
        "drop_top5_events": (lambda s: (lambda r: r["ev"] not in s))(
            {e for e, _ in by_ev.most_common(5)}),
        "drop_largest_wallet": lambda r: r["w"] != drop_w,
        "drop_largest_month": lambda r: time.strftime(
            "%Y-%m", time.gmtime(r["ts"])) != drop_m,
        "drop_top_band": (lambda b: (lambda r: band_of(r["px"]) != b))(
            by_band.most_common(1)[0][0]),
    }
    for vname, keep in variants.items():
        sub = [r for r in mea if keep(r)]
        pe = paired_excess_over_naive(sub, top, "politics")
        if not pe:
            continue
        loo[vname] = {"excess_pp": pe["excess_pp"], "ci95": pe["ci95"],
                      "p": pe["p"], "n_events": pe["n_events"],
                      "n_eff": pe["n_eff"],
                      "delta_vs_base": round(pe["excess_pp"] - base["excess_pp"], 4)}
        tests.append((f"pol|{cut_label}|{vname}", pe["p"]))
        print(f"    {vname:>22}: {pe['excess_pp']:>+7.3f}pp "
              f"CI{str(pe['ci95']):>18} p={pe['p']:.4f} "
              f"(delta {loo[vname]['delta_vs_base']:+.3f})")
    report["leave_one_out"][cut_label] = {"base": base, "variants": loo}

# ------------------------------------------- what is other_residual?
print("\n=== CHARACTERISING 'other_residual' ===", flush=True)
other_cids = {json.loads(l)["cid"] for l in CATMAP.open(encoding="utf-8")
              if '"cat": "other"' in l}
slugs = {}
n = 0
for line in UNI.open(encoding="utf-8"):
    m = json.loads(line)
    if m["condition_id"] in other_cids:
        slugs[m["condition_id"]] = (m.get("slug") or "")[:70]
    n += 1
vol = Counter()
cnt = Counter()
for r in rows:
    if r["cid"] in slugs:
        s = slugs[r["cid"]]
        head = "-".join(s.split("-")[:3])
        vol[head] += r["cost"]
        cnt[head] += 1
tv = sum(vol.values()) or 1.0
top = [(h, round(v / tv, 4), cnt[h]) for h, v in vol.most_common(25)]
report["other_residual"] = {
    "n_markets": len(slugs),
    "top_slug_prefixes_by_volume": top,
    "note": "'residual' is not a tradeable description; these prefixes are what "
            "it actually contains",
}
print(f"  {len(slugs):,} markets; top slug prefixes by volume:")
for h, sh, c in top[:18]:
    print(f"    {h[:44]:>44}  {sh:>7.2%}  n={c:,}")

report["bh_fdr"] = bh_fdr(tests) if tests else None
if report["bh_fdr"]:
    print(f"\n  BH-FDR across {report['bh_fdr']['n_tests']} tests: "
          f"{report['bh_fdr']['n_significant']} significant")
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
