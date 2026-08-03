r"""What is the 0-second row actually measuring, and what do the units mean?

Two questions that decide how the Task 5 table should be read.

1. At delay 0, `px_at(token, t)` returns the first trade at or after the
   wallet's own entry timestamp -- which may BE the wallet's own trade. If so
   the 0s row is close to a restatement of the wallet's own edge rather than
   anything a copier could obtain, and quoting it as an opportunity would be
   the same class of error as backtesting over the selection window.

2. "+4.65pp" is percentage points of the $1 contract face value, not a return
   on capital deployed. At an entry price of 0.40 you risk $0.40 to earn
   $0.0465, which is a very different-looking number. Both framings are
   computed here so the honest one can be quoted.
"""
import json
import sys
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import boot_by_event, fee  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
TARGETS = ROOT / "data" / "spec_task5_targets.json"
BOOKS = [ROOT / "data" / "spec_task5_fills.jsonl",
         ROOT / "data" / "exit_fills.jsonl",
         ROOT / "data" / "fills.jsonl"]
OUT = ROOT / "reports" / "spec_d0_interpretation.json"

CUT = 1767830400
DELAYS = [0, 10, 60, 300, 1800]
SPREAD_PP = 1.0
MAX_LOOKAHEAD = 3600

survivors = json.loads(TARGETS.read_text(encoding="utf-8"))["survivors"]

print("loading books...", flush=True)
bts, bpx = defaultdict(list), defaultdict(list)
n = 0
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
        n += 1
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


rows = []
for line in PANEL.open(encoding="utf-8"):
    r = json.loads(line)
    if r["ts"] >= CUT and r["w"] in survivors:
        rows.append(r)

same = Counter()
by_ev = {d: defaultdict(list) for d in DELAYS}
roc_by_ev = {d: defaultdict(list) for d in DELAYS}
px_used = {d: [] for d in DELAYS}
lag0 = []

for r in rows:
    tok = r["tok"]
    if tok not in bts:
        continue
    vals, rocs, pxs = {}, {}, {}
    ok = True
    for d in DELAYS:
        p = px_at(tok, r["ts"] + d)
        if p is None:
            ok = False
            break
        vals[d] = r["outcome"] - p - fee(p)
        rocs[d] = vals[d] / p if p > 0 else None      # return on capital
        pxs[d] = p
    if not ok or any(v is None for v in rocs.values()):
        continue
    # is the d0 price the wallet's OWN entry price?
    if abs(pxs[0] - r["px"]) < 1e-6:
        same["d0_equals_wallet_own_price"] += 1
    else:
        same["d0_differs"] += 1
    ts = bts[tok]
    i = bisect_left(ts, r["ts"])
    lag0.append(ts[i] - r["ts"] if i < len(ts) else -1)
    for d in DELAYS:
        by_ev[d][r["ev"]].append(vals[d])
        roc_by_ev[d][r["ev"]].append(rocs[d])
        px_used[d].append(pxs[d])

tot = sum(same.values())
frac_same = same["d0_equals_wallet_own_price"] / max(tot, 1)
lag0.sort()
print(f"\n=== WHAT IS THE d0 ROW? ===")
print(f"  positions analysed: {tot:,}")
print(f"  d0 price == the wallet's OWN entry price: "
      f"{same['d0_equals_wallet_own_price']:,} ({frac_same:.1%})")
print(f"  median gap between wallet entry and the 'd0' print: "
      f"{lag0[len(lag0)//2]}s")

print(f"\n=== FACE-VALUE EDGE vs RETURN ON CAPITAL ===")
print(f"{'delay':>7} {'mean px':>9} {'edge pp':>9} {'net pp':>9} "
      f"{'ROC gross':>11} {'ROC net':>9}")
out = {}
for d in DELAYS:
    b = boot_by_event(by_ev[d], n_boot=1200)
    rb = boot_by_event(roc_by_ev[d], n_boot=1200)
    if not b or not rb:
        continue
    mpx = sum(px_used[d]) / len(px_used[d])
    net_pp = b["mean_pp"] - SPREAD_PP
    # net ROC: subtract the spread in face terms, then divide by price paid
    net_roc = net_pp / (mpx * 100) * 100
    out[str(d)] = {
        "mean_entry_price": round(mpx, 4),
        "edge_pp": b["mean_pp"], "net_pp": round(net_pp, 4),
        "roc_gross_pct": round(rb["mean_pp"], 4),
        "roc_net_pct": round(net_roc, 4),
        "ci95_pp": b["ci95"], "p": b["p"],
        "n_events": b["n_events"], "n_eff": b["n_eff"],
    }
    print(f"{d:>6}s {mpx:>9.4f} {b['mean_pp']:>9.3f} {net_pp:>9.3f} "
          f"{rb['mean_pp']:>10.2f}% {net_roc:>8.2f}%")

report = {
    "d0_interpretation": {
        "n_positions": tot,
        "frac_d0_is_wallet_own_price": round(frac_same, 4),
        "median_lag_s": lag0[len(lag0) // 2] if lag0 else None,
        "note": "where this fraction is high, the d0 row is the WALLET'S price, "
                "not a price a copier could reach, and must not be quoted as an "
                "opportunity",
    },
    "units": {
        "edge_pp": "percentage points of $1 contract face value",
        "roc_pct": "return on capital actually deployed = edge / entry price",
        "spread_pp_applied": SPREAD_PP,
    },
    "by_delay": out,
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
