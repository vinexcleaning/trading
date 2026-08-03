r"""Task 5 with three panels, and a test of whether the balanced one is biased.

The 16.1% headline used a BALANCED panel: only positions with a print at every
delay including 1800s. That is the right way to compare across delays -- the
population is held fixed -- but it costs coverage brutally, and worse, the
binding constraint is the 30-minute column. Requiring a print half an hour later
selects for LIQUID tokens, and liquid tokens may not carry the same edge.

So three panels are reported:

  balanced_all      every delay incl. 1800s   (the old headline, ~16%)
  balanced_300      every delay up to 300s    (drops the 1800s requirement)
  per_delay         each delay uses everything usable at that delay (~40-45%)

`per_delay` has the best coverage but its population shifts between rows, so it
must not be read as a decay curve. `balanced_300` is the honest compromise:
comparable across the delays that actually matter, at roughly twice the
coverage.

Then the control that matters: at a fixed delay of 10s, compare positions that
ALSO have a 1800s print against those that do not. If they differ, the balanced
headline is selected on liquidity and must be reported as such.
"""
import json
import sys
from array import array
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import boot_by_event, fee  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
PANEL = D / "spec_panel.jsonl"
TARGETS = D / "spec_task5_targets.json"
BOOKS = [D / "spec_task5_fills.jsonl", D / "exit_fills.jsonl", D / "fills.jsonl"]
OUT = ROOT / "reports" / "spec_latency_panels.json"

CUT = 1767830400
DELAYS = [0, 10, 60, 300, 1800]
CORE = [0, 10, 60, 300]
SPREAD_PP = 1.0
MAX_LOOKAHEAD = 3600
N_BOOT = 1500
MIN_EVENTS = 30

survivors = set(json.loads(TARGETS.read_text(encoding="utf-8"))["survivors"])

# The book files now total ~63M fills across ~11.4GB. Holding those as Python
# lists would need well over the free RAM on this box, so two economies:
#   1. keep only tokens the panel actually needs (most of fills.jsonl and
#      exit_fills.jsonl is irrelevant here);
#   2. store timestamps and prices in array('i')/array('d'), roughly a quarter
#      of the footprint of Python lists of boxed scalars.
print("collecting needed tokens...", flush=True)
needed = set()
for line in PANEL.open(encoding="utf-8"):
    r = json.loads(line)
    if r["ts"] >= CUT and r["w"] in survivors:
        needed.add(r["tok"])
print(f"  {len(needed):,} tokens needed")

print("loading books (filtered)...", flush=True)
bts, bpx = defaultdict(lambda: array("i")), defaultdict(lambda: array("d"))
n = kept = 0
for p in BOOKS:
    if not p.exists():
        continue
    for line in p.open(encoding="utf-8"):
        n += 1
        if n % 20_000_000 == 0:
            print(f"  scanned {n:,}, kept {kept:,}", flush=True)
        try:
            f = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        t = f.get("token")
        if t is None or t not in needed:
            continue
        bts[t].append(f["ts"])
        bpx[t].append(f["price"])
        kept += 1
for t in list(bts):
    z = sorted(zip(bts[t], bpx[t]))
    bts[t] = array("i", [a for a, _ in z])
    bpx[t] = array("d", [b for _, b in z])
print(f"  scanned {n:,} fills, kept {kept:,} over {len(bts):,} tokens")


def px_at(tok, when):
    ts = bts.get(tok)
    if not ts:
        return None
    i = bisect_left(ts, when)
    if i >= len(ts) or ts[i] - when > MAX_LOOKAHEAD:
        return None
    return bpx[tok][i]


rows = []
for line in PANEL.open(encoding="utf-8"):
    r = json.loads(line)
    if r["ts"] >= CUT and r["w"] in survivors:
        rows.append(r)
print(f"  {len(rows):,} survivor period-2 positions")

# resolve every delay for every position once
resolved = []
cover = Counter()
for r in rows:
    tok = r["tok"]
    if tok not in bts:
        cover["no_book"] += 1
        continue
    vals = {}
    for d in DELAYS:
        p = px_at(tok, r["ts"] + d)
        vals[d] = (r["outcome"] - p - fee(p)) if p is not None else None
    resolved.append((r, vals))
    cover["has_book"] += 1

N = len(rows)
have_all = [x for x in resolved if all(v is not None for v in x[1].values())]
have_core = [x for x in resolved if all(x[1][d] is not None for d in CORE)]
print(f"\n  balanced_all : {len(have_all):,}  ({len(have_all)/N:.1%})")
print(f"  balanced_300 : {len(have_core):,}  ({len(have_core)/N:.1%})")


def curve(pop, delays, label):
    out = {}
    print(f"\n=== {label} (n={len(pop):,}, {len(pop)/N:.1%} coverage) ===")
    print(f"{'delay':>7} {'gross':>9} {'net':>9} {'CI95':>22} {'p':>9} "
          f"{'events':>8} {'n_eff':>8}")
    for d in delays:
        ev = defaultdict(list)
        for r, vals in pop:
            if vals[d] is not None:
                ev[r["ev"]].append(vals[d])
        b = boot_by_event(ev, n_boot=N_BOOT)
        if not b:
            continue
        net = round(b["mean_pp"] - SPREAD_PP, 4)
        out[str(d)] = {"gross_pp": b["mean_pp"], "net_pp": net,
                       "ci95": b["ci95"], "p": b["p"],
                       "n_obs": b["n_obs"], "n_events": b["n_events"],
                       "n_eff": b["n_eff"],
                       "coverage": round(b["n_obs"] / N, 4)}
        print(f"{d:>6}s {b['mean_pp']:>9.3f} {net:>9.3f} {str(b['ci95']):>22} "
              f"{b['p']:>9.4f} {b['n_events']:>8,} {b['n_eff']:>8,.0f}")
    return out


res = {
    "meta": {
        "n_survivor_positions": N,
        "n_with_book": cover["has_book"],
        "n_no_book": cover["no_book"],
        "spread_pp": SPREAD_PP,
        "note": "per_delay has the best coverage but its population shifts "
                "between rows and it must NOT be read as a decay curve",
    },
    "balanced_all": curve(have_all, DELAYS, "BALANCED — all delays incl 1800s"),
    "balanced_300": curve(have_core, CORE, "BALANCED — through 300s only"),
    "per_delay": curve(resolved, DELAYS, "PER-DELAY — max coverage, shifting population"),
}

# ---------------------------------------------------------------- control
print("\n=== CONTROL: is the balanced panel selected on liquidity? ===")
print("  At a fixed 10s delay, positions WITH a 1800s print vs WITHOUT.")
with_ev, without_ev = defaultdict(list), defaultdict(list)
for r, vals in resolved:
    if vals[10] is None:
        continue
    (with_ev if vals[1800] is not None else without_ev)[r["ev"]].append(vals[10])
bw = boot_by_event(with_ev, n_boot=N_BOOT)
bo = boot_by_event(without_ev, n_boot=N_BOOT)
ctrl = {}
if bw and bo:
    ctrl = {
        "d10_with_1800s_print": bw,
        "d10_without_1800s_print": bo,
        "difference_pp": round(bw["mean_pp"] - bo["mean_pp"], 4),
        "ci_overlap": not (bw["ci95"][1] < bo["ci95"][0]
                           or bo["ci95"][1] < bw["ci95"][0]),
    }
    print(f"    WITH 1800s print : {bw['mean_pp']:>8.3f}pp  CI{bw['ci95']}  "
          f"n_ev={bw['n_events']:,}")
    print(f"    WITHOUT          : {bo['mean_pp']:>8.3f}pp  CI{bo['ci95']}  "
          f"n_ev={bo['n_events']:,}")
    print(f"    difference       : {ctrl['difference_pp']:>8.3f}pp  "
          f"CIs overlap: {ctrl['ci_overlap']}")
    print("    -> " + ("no detectable liquidity selection"
                       if ctrl["ci_overlap"] else
                       "BALANCED PANEL IS SELECTED ON LIQUIDITY"))
res["liquidity_selection_control"] = ctrl

# ------------------------------------------------ per-wallet, best panel
print("\n=== PER-WALLET (balanced_300) ===")
pw = defaultdict(lambda: defaultdict(list))
for r, vals in have_core:
    for d in CORE:
        pw[r["w"]][d].append((r["ev"], vals[d]))
per_wallet = {}
n_report = 0
for w, dd in pw.items():
    ev10 = defaultdict(list)
    for e, v in dd[10]:
        ev10[e].append(v)
    if len(ev10) < MIN_EVENTS:
        continue
    n_report += 1
    row = {}
    for d in CORE:
        ev = defaultdict(list)
        for e, v in dd[d]:
            ev[e].append(v)
        b = boot_by_event(ev, n_boot=600)
        if b:
            row[str(d)] = {"gross_pp": b["mean_pp"],
                           "net_pp": round(b["mean_pp"] - SPREAD_PP, 4),
                           "n_events": b["n_events"], "p": b["p"]}
    per_wallet[w] = row
surv10 = sum(1 for v in per_wallet.values()
             if v.get("10", {}).get("net_pp", -9) > 0)
surv300 = sum(1 for v in per_wallet.values()
              if v.get("300", {}).get("net_pp", -9) > 0)
print(f"  {n_report} wallets clear the {MIN_EVENTS}-event floor "
      f"(was 9 at 16.1% coverage)")
print(f"  net-positive at 10s : {surv10}/{n_report}")
print(f"  net-positive at 300s: {surv300}/{n_report}")
res["per_wallet"] = {"n_reportable": n_report,
                     "net_positive_at_10s": surv10,
                     "net_positive_at_300s": surv300,
                     "detail": per_wallet}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")

# Cache per-event contributions for the per-delay population so leave-one-out
# can be run without re-reading 63M fills. Saved for the NEGATIVE result
# specifically -- the same robustness test the positive politics finding got.
RAW = D / "spec_latency_raw.json"
rawdump = {}
for d in DELAYS:
    ev = defaultdict(list)
    for r, vals in resolved:
        if vals[d] is not None:
            ev[r["ev"]].append(round(vals[d], 6))
    rawdump[str(d)] = dict(ev)
RAW.write_text(json.dumps(rawdump), encoding="utf-8")
print(f"\nwrote {OUT}")
print(f"wrote {RAW} (per-event contributions for leave-one-out)")
