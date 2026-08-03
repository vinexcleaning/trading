r"""Tasks 2, 3 and 6: the specialist test, and the synthetic control on the same code.

Invoked twice:

    python spec_03_run.py real          -- the real panel
    python spec_03_run.py synthetic     -- outcomes redrawn so no wallet has skill

The synthetic run must come FIRST and must find nothing. It PERMUTES WALLET
LABELS WITHIN EACH EVENT, leaving every outcome untouched. That preserves prices,
costs, event structure, per-wallet position counts and the entire
favourite-longshot pattern -- so the naive benchmark is identical to the real run
-- while destroying the only thing under test: the link between a wallet and
which side it took. If the pipeline still reports specialist edge over the
benchmark, the pipeline is broken and every real result is void.

The registered hypothesis is the PAIRED one: does copying beat buying the same
price bands blindly in the same events? Testing the copier return against zero
instead is an error -- a copier can be significantly profitable purely by holding
favourites, and that is exactly what sank the earlier +7.05pp finding.

Selection uses period-1 rows only; measurement uses period-2 rows only; the
separation is asserted, not assumed.
"""
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import (  # noqa: E402
    PX_BANDS, add_excess, assert_no_lookahead, band_of, bh_fdr, boot_by_event,
    fee, measure, naive_benchmark, paired_excess_over_naive,
    price_band_benchmark, rank_within_category,
)

MODE = sys.argv[1] if len(sys.argv) > 1 else "real"
ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
TOKQ = ROOT / "data" / "spec_token_q.json"
OUT = ROOT / "reports" / f"spec_task2_{MODE}.json"

SEED = 20260801
CUTS = [("2025-07-01", 1751328000), ("2026-01-08_fee_era", 1767830400)]
CATS = ["politics", "crypto", "nba", "soccer", "nfl", "esports", "weather", "other"]

FILTER_SETS = {
    "F0_min10":        {"min_trades": 10, "min_events": 5},
    "F1_min20":        {"min_trades": 20, "min_events": 10},
    "F2_min50":        {"min_trades": 50, "min_events": 20},
    "F3_min20_recent": {"min_trades": 20, "min_events": 10,
                        "recent_within_days": 30},
    "F4_min20_cadence": {"min_trades": 20, "min_events": 10,
                         "recent_within_days": 30, "max_gap_days": 30},
    "F5_min20_nonMM":  {"min_trades": 20, "min_events": 10, "use_mm_filter": True},
    "F6_min20_all":    {"min_trades": 20, "min_events": 10,
                        "recent_within_days": 30, "max_gap_days": 30,
                        "use_mm_filter": True},
}
HALF_LIVES = [None, 30, 90]
MIN_RANKED = 30

MM_WALLETS = set(json.loads(
    (ROOT / "data" / "wallet_flags.json").read_text(encoding="utf-8"))["excluded"])

print(f"=== MODE: {MODE} ===", flush=True)
print(f"  {len(MM_WALLETS):,} market-maker/too-large wallets (from flags file)",
      flush=True)
print("loading panel...", flush=True)
rows = []
for line in PANEL.open(encoding="utf-8"):
    rows.append(json.loads(line))
print(f"  {len(rows):,} panel rows")

if MODE == "synthetic":
    # PERMUTE WALLET LABELS WITHIN EACH EVENT. Outcomes are untouched.
    #
    # Two earlier constructions were tried and both were rejected by their own
    # sanity check, which is what the check is for:
    #   1. redraw each TOKEN's outcome ~ Bernoulli(its vwap) -> pooled edge
    #      +3.94pp, because YES and NO are complementary and independent draws
    #      let a market resolve with both sides winning;
    #   2. draw one winner per MARKET with probability proportional to vwap ->
    #      +1.04pp, because vwap is volume-weighted while positions are
    #      equally weighted, so the two means do not coincide.
    # Rather than keep calibrating a price model, destroy the thing actually
    # under test and leave everything else exactly as observed.
    #
    # Shuffling the wallet vector within an event preserves: every position's
    # price, cost and outcome; each event's participant multiset; each wallet's
    # per-event position count; the whole favourite-longshot structure; and the
    # naive benchmark, which is therefore identical to the real run. It destroys
    # only the link between a wallet and WHICH SIDE it took. If the pipeline
    # still finds specialists with edge over the benchmark, it is broken.
    rng = random.Random(SEED)
    by_ev_idx = defaultdict(list)
    for i, r in enumerate(rows):
        by_ev_idx[r["ev"]].append(i)
    n_perm = 0
    for ev, idxs in by_ev_idx.items():
        if len(idxs) < 2:
            continue
        ws = [rows[i]["w"] for i in idxs]
        rng.shuffle(ws)
        for i, w in zip(idxs, ws):
            rows[i]["w"] = w
        n_perm += 1
    tot = sum(r["edge"] for r in rows) / len(rows)
    print(f"  wallet labels permuted within {n_perm:,} multi-position events "
          f"(of {len(by_ev_idx):,}); outcomes untouched")
    print(f"  sanity: pooled mean edge = {tot*100:.4f}pp "
          f"(matches the REAL panel by construction -- outcomes unchanged)")
    print("  PASS CRITERION: no category may show specialist edge over the "
          "naive benchmark surviving BH-FDR.")

report = {"mode": MODE, "meta": {"n_panel_rows": len(rows), "cuts": [c[0] for c in CUTS],
                                 "categories": CATS, "seed": SEED},
          "results": [], "lookahead": [], "filter_diagnostics": {},
          "skipped": {}}
tests = []

for cut_label, cut in CUTS:
    sel = [r for r in rows if r["ts"] < cut]
    mea = [r for r in rows if r["ts"] >= cut]
    la = assert_no_lookahead(sel, mea, cut, cut_label)
    la["cut_label"] = cut_label
    report["lookahead"].append(la)
    print(f"\n--- cut {cut_label}: sel {len(sel):,} / meas {len(mea):,} "
          f"(look-ahead {la['verdict']}) ---", flush=True)

    bench_sel = price_band_benchmark(sel)
    add_excess(sel, bench_sel)
    bench_mea = price_band_benchmark(mea)
    add_excess(mea, bench_mea)

    for fname, fdef in FILTER_SETS.items():
        filt = dict(fdef)
        if filt.pop("use_mm_filter", False):
            # MUST come from the wallet-level flags file, not from `rows`.
            # `mm` is stored per position as a copy of a per-wallet attribute;
            # under the synthetic permutation it travels with the POSITION, so
            # deriving the set from rows made almost every wallet look like a
            # market maker and silently gutted the control's F5/F6 arms.
            filt["exclude"] = set(MM_WALLETS)
        for hl in HALF_LIVES:
            hlab = "unweighted" if hl is None else f"hl{hl}d"
            for cat in CATS:
                scores, diag = rank_within_category(sel, cat, filt, hl)
                key = f"{cut_label}|{fname}|{hlab}|{cat}"
                # A top decile of 2 wallets is not a decile. Require enough
                # ranked wallets that the selection means something, and RECORD
                # every skip so "which filters mattered" is answerable rather
                # than inferred from a blank row.
                if len(scores) < MIN_RANKED:
                    report["skipped"][key] = {
                        "reason": "too_few_ranked_wallets",
                        "n_ranked": len(scores), "diag": diag}
                    continue
                order = sorted(scores, key=lambda w: -scores[w])
                k = max(len(order) // 10, 1)
                top = set(order[:k])
                res, mrows = measure(mea, top, cat, sizing="equal")
                if res is None or res["n_events"] < 5:
                    report["skipped"][key] = {
                        "reason": "too_few_measurement_events",
                        "n_ranked": len(scores),
                        "n_events": (res["n_events"] if res else 0)}
                    continue
                bands = {band_of(r["px"]) for r in mrows}
                nb = naive_benchmark(mea, cat, bands)
                # The hypothesis that matters is copier BEATS blind exposure,
                # not copier differs from zero. Registered test is the paired one.
                pex = paired_excess_over_naive(mea, top, cat)
                report["filter_diagnostics"][key] = diag
                rowr = {
                    "cut": cut_label, "filters": fname, "weighting": hlab,
                    "category": cat,
                    "n_wallets_ranked": len(scores), "n_top_decile": k,
                    "p1_top_score_pp": round(
                        sum(scores[w] for w in top) / k * 100, 4),
                    "copier": res,
                    "naive_benchmark": nb,
                    "paired_excess_over_naive": pex,
                    "excess_over_naive_pp": (
                        pex["excess_pp"] if pex else None),
                }
                report["results"].append(rowr)
                if pex:
                    tests.append((key, pex["p"]))

print(f"\n  {len(report['results'])} category-filter-cut results")

# headline slice: the fullest filter set, unweighted, at each cut
print("\n=== HEADLINE (F6_min20_all, unweighted) ===")
print(f"{'cut':>20} {'cat':>9} {'nW':>5} {'nTop':>5} {'copier':>9} "
      f"{'CI95':>20} {'n_ev':>7} {'n_eff':>8} {'naive':>8} {'excess':>8} "
      f"{'excess CI95':>20} {'p':>8}")
for r in report["results"]:
    if r["filters"] != "F6_min20_all" or r["weighting"] != "unweighted":
        continue
    c, nb, pe = r["copier"], r["naive_benchmark"], r["paired_excess_over_naive"]
    print(f"{r['cut']:>20} {r['category']:>9} {r['n_wallets_ranked']:>5} "
          f"{r['n_top_decile']:>5} {c['mean_pp']:>9.3f} {str(c['ci95']):>20} "
          f"{c['n_events']:>7,} {c['n_eff']:>8.1f} "
          f"{(nb['mean_pp'] if nb else 0):>8.3f} "
          f"{(pe['excess_pp'] if pe else 0):>8.3f} "
          f"{str(pe['ci95']) if pe else '':>20} {(pe['p'] if pe else 1):>8.4f}")

report["bh_fdr"] = bh_fdr(tests)
print(f"\n=== BH-FDR: {report['bh_fdr']['n_significant']} of "
      f"{report['bh_fdr']['n_tests']} tests significant at 5% ===")

# pooled across categories, headline filter
pooled = {}
for cut_label, _ in CUTS:
    sel_r = [r for r in report["results"]
             if r["cut"] == cut_label and r["filters"] == "F6_min20_all"
             and r["weighting"] == "unweighted"]
    if not sel_r:
        continue
    tot_n = sum(r["copier"]["n_obs"] for r in sel_r)
    tot_eff = sum(r["copier"]["n_eff"] for r in sel_r)
    wmean = sum(r["copier"]["mean_pp"] * r["copier"]["n_obs"] for r in sel_r) / tot_n
    nb_mean = sum((r["naive_benchmark"]["mean_pp"] if r["naive_benchmark"] else 0)
                  * r["copier"]["n_obs"] for r in sel_r) / tot_n
    pooled[cut_label] = {
        "n_categories": len(sel_r), "n_obs": tot_n,
        "n_eff": round(tot_eff, 1),
        "volume_weighted_copier_pp": round(wmean, 4),
        "volume_weighted_naive_pp": round(nb_mean, 4),
        "excess_over_naive_pp": round(wmean - nb_mean, 4),
    }
report["pooled"] = pooled
print("\n=== POOLED (F6_min20_all, unweighted) ===")
for k, v in pooled.items():
    print(f"  {k:>22}: copier {v['volume_weighted_copier_pp']:>7.3f}pp  "
          f"naive {v['volume_weighted_naive_pp']:>7.3f}pp  "
          f"excess {v['excess_over_naive_pp']:>7.3f}pp  "
          f"n={v['n_obs']:,} n_eff={v['n_eff']:,.0f}")

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
