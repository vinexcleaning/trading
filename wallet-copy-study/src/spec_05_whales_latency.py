r"""Task 4 (whale exclusion) and Task 5 (per-wallet latency tolerance).

TASK 4. Phase 2 excluded 41 wallets as "too large to copy" on price-impact
grounds. The brief argues that if edge does not decay with latency then impact
may not be eating the copier either -- but that premise is FALSE as stated (see
spec_premise_check: conditioned on selected wallets, buy-and-hold decays ~3pp
inside five minutes). The exclusion is therefore tested empirically rather than
argued either way:
  (a) realised price impact around large fills, and how fast it reverts;
  (b) the specialist result re-run with the whales PUT BACK, entering at the
      price available AFTER their fill rather than at their fill price.

TASK 5. The global "no latency decay" finding is an average. Per surviving
wallet, copier return at 0s / 10s / 60s / 300s / 1800s, so that wallets
followable by hand from a phone alert can be separated from ones that are not.
Coverage is limited to markets where a complete book was pulled, and the
coverage fraction is reported rather than glossed.
"""
import json
import sys
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import (  # noqa: E402
    add_excess, band_of, bh_fdr, boot_by_event, fee, measure,
    paired_excess_over_naive, price_band_benchmark, rank_within_category,
)

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
MKT_FILLS = ROOT / "data" / "fills.jsonl"
EXIT_FILLS = ROOT / "data" / "exit_fills.jsonl"
OUT = ROOT / "reports" / "spec_task45_whales_latency.json"

CUT = 1767830400          # 2026-01-08 fee era
DELAYS = [0, 10, 60, 300, 1800]
CATS = ["politics", "crypto", "soccer", "nba", "nfl", "esports", "other", "weather"]
FILT = {"min_trades": 20, "min_events": 10, "recent_within_days": 30,
        "max_gap_days": 30}
MIN_RANKED = 30

flags = json.loads(FLAGS.read_text(encoding="utf-8"))
excluded = flags["excluded"]
MM = {w for w, rs in excluded.items()
      if any(r.startswith("market_maker") for r in rs)}
WHALES = {w for w, rs in excluded.items() if "too_large_to_copy" in rs}
print(f"market makers {len(MM):,}  whales(too_large) {len(WHALES):,}")

print("loading panel...", flush=True)
rows = [json.loads(l) for l in PANEL.open(encoding="utf-8")]
print(f"  {len(rows):,} rows")

sel = [r for r in rows if r["ts"] < CUT]
mea = [r for r in rows if r["ts"] >= CUT]
add_excess(sel, price_band_benchmark(sel))
add_excess(mea, price_band_benchmark(mea))

report = {"meta": {"cut": CUT, "n_mm": len(MM), "n_whales": len(WHALES),
                   "filters": FILT, "delays_s": DELAYS}}
tests = []

# ================================================== TASK 4a: price impact
print("\n=== TASK 4a: price impact around large fills ===", flush=True)
book_ts, book_px, book_sz = defaultdict(list), defaultdict(list), defaultdict(list)
n = 0
for src, keyname in ((MKT_FILLS, "token"), (EXIT_FILLS, "token")):
    if not src.exists():
        continue
    for line in src.open(encoding="utf-8"):
        f = json.loads(line)
        t = f.get(keyname)
        if t is None:
            continue
        book_ts[t].append(f["ts"])
        book_px[t].append(f["price"])
        book_sz[t].append(f.get("shares", 0.0) * f["price"])
        n += 1
        if n % 4_000_000 == 0:
            print(f"  {n:,}", flush=True)
for t in book_ts:
    z = sorted(zip(book_ts[t], book_px[t], book_sz[t]))
    book_ts[t] = [a for a, _, _ in z]
    book_px[t] = [b for _, b, _ in z]
    book_sz[t] = [c for _, _, c in z]
print(f"  {n:,} fills over {len(book_ts):,} tokens")

SIZE_BINS = [(0, 100), (100, 1000), (1000, 10000), (10000, 1e18)]


def px_at(tok, when, horizon=6 * 3600):
    ts = book_ts.get(tok)
    if not ts:
        return None
    i = bisect_left(ts, when)
    if i >= len(ts) or ts[i] - when > horizon:
        return None
    return book_px[tok][i]


impact = {f"{int(lo)}-{int(hi) if hi < 1e17 else 'inf'}":
          {f"d{d}": [] for d in DELAYS} for lo, hi in SIZE_BINS}
for tok, ts in book_ts.items():
    pxs, szs = book_px[tok], book_sz[tok]
    for i in range(len(ts)):
        sz = szs[i]
        lab = None
        for lo, hi in SIZE_BINS:
            if lo <= sz < hi:
                lab = f"{int(lo)}-{int(hi) if hi < 1e17 else 'inf'}"
                break
        if lab is None:
            continue
        p0 = pxs[i]
        for d in DELAYS:
            p = px_at(tok, ts[i] + d)
            if p is not None:
                impact[lab][f"d{d}"].append(p - p0)

imp_out = {}
print(f"{'size bin ($)':>16} " + " ".join(f"{'d'+str(d):>9}" for d in DELAYS)
      + f" {'n':>10}")
for lab, dd in impact.items():
    row = {}
    for d in DELAYS:
        v = dd[f"d{d}"]
        row[f"d{d}_pp"] = round(float(np.mean(v)) * 100, 4) if v else None
    row["n"] = len(dd[f"d{DELAYS[0]}"])
    imp_out[lab] = row
    print(f"{lab:>16} " + " ".join(
        f"{(row[f'd{d}_pp'] if row[f'd{d}_pp'] is not None else 0):>9.4f}"
        for d in DELAYS) + f" {row['n']:>10,}")
report["task4a_price_impact"] = imp_out
print("  (positive = price moved up after the fill; reversion shows as the "
      "later columns falling back toward zero)")

# ============================= TASK 4b: specialist result with whales back in
print("\n=== TASK 4b: specialist result, whales EXCLUDED vs INCLUDED ===",
      flush=True)
variants = {"whales_excluded": MM | WHALES, "whales_included": MM}
t4 = []
print(f"{'variant':>18} {'cat':>9} {'nW':>5} {'copier':>9} {'excess':>8} "
      f"{'CI95':>20} {'p':>8} {'n_ev':>7} {'n_eff':>8}")
for vname, excl in variants.items():
    f2 = dict(FILT)
    f2["exclude"] = excl
    for cat in CATS:
        scores, diag = rank_within_category(sel, cat, f2, None)
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
        n_whale_in_top = len(top & WHALES)
        t4.append({"variant": vname, "category": cat,
                   "n_wallets_ranked": len(scores), "n_top": k,
                   "n_whales_in_top_decile": n_whale_in_top,
                   "copier_pp": res["mean_pp"], "copier_ci95": res["ci95"],
                   "excess_pp": pex["excess_pp"], "excess_ci95": pex["ci95"],
                   "p": pex["p"], "n_events": pex["n_events"],
                   "n_eff": pex["n_eff"]})
        tests.append((f"t4|{vname}|{cat}", pex["p"]))
        print(f"{vname:>18} {cat:>9} {len(scores):>5} {res['mean_pp']:>9.3f} "
              f"{pex['excess_pp']:>8.3f} {str(pex['ci95']):>20} "
              f"{pex['p']:>8.4f} {pex['n_events']:>7,} {pex['n_eff']:>8.1f}")
report["task4b_whale_variants"] = t4

# ===================================== TASK 5: per-wallet latency tolerance
print("\n=== TASK 5: per-wallet latency tolerance ===", flush=True)
f2 = dict(FILT)
f2["exclude"] = MM | WHALES
survivors = {}
for cat in CATS:
    scores, _ = rank_within_category(sel, cat, f2, None)
    if len(scores) < MIN_RANKED:
        continue
    order = sorted(scores, key=lambda w: -scores[w])
    for w in order[:max(len(order) // 10, 1)]:
        survivors.setdefault(w, []).append(cat)
print(f"  {len(survivors)} surviving top-decile wallets across categories")

per_w = defaultdict(lambda: {d: defaultdict(list) for d in DELAYS})
cover = Counter()
for r in mea:
    if r["w"] not in survivors:
        continue
    tok = r["tok"]
    if tok not in book_ts:
        cover["no_book"] += 1
        continue
    cover["with_book"] += 1
    for d in DELAYS:
        p = px_at(tok, r["ts"] + d)
        if p is None:
            continue
        per_w[r["w"]][d][r["ev"]].append(r["outcome"] - p - fee(p))

cov_frac = cover["with_book"] / max(sum(cover.values()), 1)
print(f"  book coverage of survivor positions: {cover['with_book']:,} of "
      f"{sum(cover.values()):,} ({cov_frac:.1%})")

t5 = []
for w, dd in per_w.items():
    row = {"wallet": w, "categories": survivors[w]}
    ok = True
    for d in DELAYS:
        b = boot_by_event(dd[d], n_boot=800)
        row[f"d{d}"] = b
        if b is None:
            ok = False
    if not ok or row["d0"] is None:
        continue
    row["n_events"] = row["d0"]["n_events"]
    row["decay_0_to_1800_pp"] = (
        round(row["d1800"]["mean_pp"] - row["d0"]["mean_pp"], 4)
        if row.get("d1800") else None)
    row["followable_slowly"] = bool(
        row.get("d1800") and row["d1800"]["mean_pp"] > 1.0
        and row["d1800"]["ci95"][0] > 0)
    t5.append(row)

t5.sort(key=lambda r: -(r["d1800"]["mean_pp"] if r.get("d1800") else -99))
report["task5_latency"] = {
    "book_coverage_frac": round(cov_frac, 4),
    "n_survivors": len(survivors),
    "n_with_enough_book": len(t5),
    "wallets": t5,
}
print(f"\n  {len(t5)} survivors had enough book coverage to measure")
print(f"{'wallet':>14} {'cats':>18} {'n_ev':>6} " +
      " ".join(f"{'d'+str(d):>8}" for d in DELAYS) + f" {'slow?':>6}")
for r in t5[:25]:
    print(f"{r['wallet'][:12]+'..':>14} {','.join(r['categories'])[:18]:>18} "
          f"{r['n_events']:>6} " +
          " ".join(f"{r['d'+str(d)]['mean_pp']:>8.2f}" if r.get(f"d{d}") else f"{'--':>8}"
                   for d in DELAYS) +
          f" {str(r['followable_slowly']):>6}")
n_slow = sum(1 for r in t5 if r["followable_slowly"])
print(f"\n  wallets whose edge survives 30 minutes with a positive lower CI: "
      f"{n_slow} of {len(t5)}")
report["task5_n_followable_slowly"] = n_slow

report["bh_fdr_task4"] = bh_fdr(tests) if tests else None
OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
