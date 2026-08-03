r"""Task 5, properly: per-wallet latency tolerance for the surviving specialists.

The previous attempt had 0.9% book coverage and was reported as a coverage
failure rather than a result. This runs on the targeted pull.

Method, with the lessons from the exit study applied:

  - BALANCED PANEL. A position enters the curve at every delay or at none.
    Without that, n falls as the delay grows and what looks like decay is partly
    a different set of positions being averaged (the exit study saw 811 -> 692).
  - Clustered by EVENT, never by trade.
  - Spread applied explicitly. Every gross figure assumes you transact at the
    next traded price, which is not an ask; the project's 1.0pp same-block
    dispersion floor is subtracted for the net column and is itself a lower
    bound.
  - "Followable slowly" is a deliberately demanding flag: the wallet's NET
    return at 1800s must be positive with a bootstrap lower bound above zero,
    and must rest on enough events to mean anything. A +28pp reading on 8 events
    is the "+95pp genius" failure mode and is excluded by the event floor, not
    by judgement after the fact.

BH-FDR is applied across all per-wallet tests.
"""
import json
import sys
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import bh_fdr, boot_by_event, fee  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
TARGETS = ROOT / "data" / "spec_task5_targets.json"
BOOKS = [ROOT / "data" / "spec_task5_fills.jsonl",
         ROOT / "data" / "exit_fills.jsonl",
         ROOT / "data" / "fills.jsonl"]
OUT = ROOT / "reports" / "spec_task5_latency_final.json"

CUT = 1767830400
DELAYS = [0, 10, 60, 300, 1800]
SPREAD_PP = 1.0
MIN_EVENTS = 30            # below this a per-wallet number is not reportable
MAX_LOOKAHEAD = 6 * 3600
N_BOOT = 1500

cfg = json.loads(TARGETS.read_text(encoding="utf-8"))
survivors = cfg["survivors"]
print(f"{len(survivors)} survivors, {cfg['n_period2_positions']:,} period-2 "
      f"positions, {cfg['n_distinct_tokens']:,} tokens", flush=True)

print("loading books...", flush=True)
bts, bpx = defaultdict(list), defaultdict(list)
n = 0
for p in BOOKS:
    if not p.exists():
        print(f"  (missing {p.name})")
        continue
    m = 0
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
        n += 1
        m += 1
        if n % 6_000_000 == 0:
            print(f"  {n:,}", flush=True)
    print(f"  {p.name}: {m:,} fills")
for t in bts:
    z = sorted(zip(bts[t], bpx[t]))
    bts[t] = [a for a, _ in z]
    bpx[t] = [b for _, b in z]
print(f"  {n:,} fills over {len(bts):,} tokens")


def px_at(tok, when):
    ts = bts.get(tok)
    if not ts:
        return None
    i = bisect_left(ts, when)
    if i >= len(ts) or ts[i] - when > MAX_LOOKAHEAD:
        return None
    return bpx[tok][i]


print("\nloading panel...", flush=True)
rows = []
for line in PANEL.open(encoding="utf-8"):
    r = json.loads(line)
    if r["ts"] >= CUT and r["w"] in survivors:
        rows.append(r)
print(f"  {len(rows):,} survivor period-2 positions")

cover = Counter()
per_w = defaultdict(lambda: {d: defaultdict(list) for d in DELAYS})
pooled = {d: defaultdict(list) for d in DELAYS}

for r in rows:
    tok = r["tok"]
    if tok not in bts:
        cover["no_book"] += 1
        continue
    vals = {}
    ok = True
    for d in DELAYS:
        p = px_at(tok, r["ts"] + d)
        if p is None:
            ok = False
            break
        vals[d] = r["outcome"] - p - fee(p)
    if not ok:
        cover["incomplete_panel"] += 1
        continue
    cover["used"] += 1
    for d, v in vals.items():
        per_w[r["w"]][d][r["ev"]].append(v)
        pooled[d][r["ev"]].append(v)

tot = sum(cover.values())
print(f"\n  coverage: used {cover['used']:,} of {tot:,} "
      f"({cover['used']/max(tot,1):.1%}); no book {cover['no_book']:,}; "
      f"incomplete delay panel {cover['incomplete_panel']:,}")

# ------------------------------------------------------------- pooled
print("\n=== POOLED ACROSS ALL SURVIVORS (balanced panel) ===")
print(f"{'delay':>7} {'n_ev':>7} {'n_eff':>8} {'gross':>9} {'net':>9} "
      f"{'CI95 gross':>22} {'p':>9}")
pooled_out = {}
for d in DELAYS:
    b = boot_by_event(pooled[d], n_boot=N_BOOT)
    if not b:
        continue
    pooled_out[str(d)] = {**b, "net_pp": round(b["mean_pp"] - SPREAD_PP, 4)}
    print(f"{d:>6}s {b['n_events']:>7,} {b['n_eff']:>8.1f} {b['mean_pp']:>9.3f} "
          f"{b['mean_pp']-SPREAD_PP:>9.3f} {str(b['ci95']):>22} {b['p']:>9.5f}")

# --------------------------------------------------------- per wallet
print("\n=== PER-WALLET LATENCY TOLERANCE ===")
per_out, tests = [], []
for w, dd in per_w.items():
    b0 = boot_by_event(dd[0], n_boot=N_BOOT)
    if not b0 or b0["n_events"] < MIN_EVENTS:
        continue
    row = {"wallet": w, "categories": survivors[w], "n_events": b0["n_events"],
           "n_eff": b0["n_eff"]}
    ok = True
    for d in DELAYS:
        b = boot_by_event(dd[d], n_boot=N_BOOT)
        if not b:
            ok = False
            break
        row[f"d{d}"] = {**b, "net_pp": round(b["mean_pp"] - SPREAD_PP, 4)}
    if not ok:
        continue
    row["decay_0_to_1800_pp"] = round(
        row["d1800"]["mean_pp"] - row["d0"]["mean_pp"], 4)
    net1800 = row["d1800"]["net_pp"]
    lo1800 = row["d1800"]["ci95"][0] - SPREAD_PP
    row["net_1800_pp"] = net1800
    row["net_1800_ci_lo"] = round(lo1800, 4)
    row["followable_slowly"] = bool(net1800 > 0 and lo1800 > 0)
    per_out.append(row)
    tests.append((f"t5|{w}|d1800", row["d1800"]["p"]))

per_out.sort(key=lambda r: -r["net_1800_pp"])
print(f"{'wallet':>14} {'cats':>16} {'n_ev':>6} {'n_eff':>7} " +
      " ".join(f"{'d'+str(d):>8}" for d in DELAYS) +
      f" {'net1800':>8} {'loCI':>8} {'slow?':>6}")
for r in per_out:
    print(f"{r['wallet'][:12]+'..':>14} {','.join(r['categories'])[:16]:>16} "
          f"{r['n_events']:>6,} {r['n_eff']:>7.1f} " +
          " ".join(f"{r['d'+str(d)]['mean_pp']:>8.2f}" for d in DELAYS) +
          f" {r['net_1800_pp']:>8.2f} {r['net_1800_ci_lo']:>8.2f} "
          f" {str(r['followable_slowly']):>5}")

n_slow = sum(1 for r in per_out if r["followable_slowly"])
print(f"\n  wallets reportable (>= {MIN_EVENTS} events): {len(per_out)} of "
      f"{len(survivors)}")
print(f"  followable at 30 minutes, NET of spread, lower CI > 0: {n_slow}")

fdr = bh_fdr(tests) if tests else None
if fdr:
    print(f"  BH-FDR across {fdr['n_tests']} per-wallet d1800 tests: "
          f"{fdr['n_significant']} significant at 5%")

report = {
    "meta": {
        "cut": CUT, "delays_s": DELAYS, "spread_pp": SPREAD_PP,
        "min_events_to_report": MIN_EVENTS,
        "n_survivors": len(survivors),
        "n_book_tokens": len(bts), "n_book_fills": n,
        "balanced_panel": True,
        "limits": [
            "prices are TRADE prices, not asks -- gross figures flatter the copier",
            "spread floor is a LOWER bound (same-block trade dispersion)",
            "a position enters at every delay or none, so the curve is not "
            "composition drift",
        ],
    },
    "coverage": dict(cover),
    "coverage_frac": round(cover["used"] / max(tot, 1), 4),
    "pooled": pooled_out,
    "per_wallet": per_out,
    "n_followable_slowly": n_slow,
    "bh_fdr": fdr,
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
