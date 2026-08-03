r"""Measure the TRUE effective spread from the recording, and re-price the study.

Why the haircut used so far is probably wrong in BOTH directions at once.

Every net figure in this project subtracted a flat 1.0pp, taken from same-block
trade-price dispersion. Two corrections are needed:

  TOO HARSH. The copier return is computed as `outcome - p - fee(p)` where `p`
  is a TRADED price. Traded prices are a mix of buys lifting the ask and sells
  hitting the bid, so on average they sit near the MID. A buyer's extra cost is
  therefore `ask - mid`, i.e. roughly HALF the quoted spread, not all of it.

  TOO KIND. A real order does not fill at top-of-book. It walks levels, and the
  bigger the order the worse the average fill. Top-of-book spread understates
  the cost of any size worth trading.

So this computes, per category, the half-spread AND the size-walked effective
cost for realistic order sizes, then re-prices the politics headline with the
measured number instead of the assumed one.
"""
import json
import glob
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
RECDIR = ROOT / "data" / (sys.argv[1] if len(sys.argv) > 1 else "book_recording")
OUT = ROOT / "reports" / f"rec_spread_{(sys.argv[1] if len(sys.argv) > 1 else 'shallow')}.json"

SIZES = [50, 200, 500, 1000, 5000]

# Task 5 pooled GROSS figures (before any spread haircut), from
# reports/spec_task5_latency_final.json
TASK5_GROSS = {"0": 4.651, "10": 2.014, "60": 1.357, "300": 0.721,
               "1800": -0.125}
# Specialist headline GROSS copier returns, from spec_task3_comparison.json
HEADLINE_GROSS = {
    "politics_2025-07-01": 3.387, "politics_fee_era": 4.946,
    "soccer_fee_era": 3.582, "crypto_fee_era": 1.433,
    "other_2025-07-01": 0.907,
}


def walk(levels, notional):
    """Average fill price buying `notional` dollars through ask levels."""
    spent = shares = 0.0
    for px, sz in levels:
        if px <= 0:
            continue
        cap = px * sz                      # dollars available at this level
        take = min(cap, notional - spent)
        if take <= 0:
            break
        shares += take / px
        spent += take
        if spent >= notional - 1e-9:
            break
    if shares <= 0:
        return None, 0.0
    return spent / shares, spent


files = sorted(glob.glob(str(RECDIR / "books_*.jsonl")))
if not files:
    raise SystemExit("no recording yet")
print(f"reading {len(files)} file(s)...", flush=True)

by_cat = defaultdict(lambda: {"half": [], "full": [],
                              **{f"eff{s}": [] for s in SIZES},
                              "unfillable": Counter()})
n = 0
snapshots_per_tok = Counter()
for f in files:
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            bids, asks = r.get("bids") or [], r.get("asks") or []
            if not bids or not asks:
                continue
            bb, ba = bids[0][0], asks[0][0]
            if not (0 < bb < 1 and 0 < ba < 1) or ba <= bb:
                continue
            mid = (bb + ba) / 2.0
            cat = r.get("cat") or "?"
            d = by_cat[cat]
            d["full"].append((ba - bb) * 100)
            d["half"].append((ba - mid) * 100)
            for s in SIZES:
                eff, filled = walk(asks, s)
                if eff is None or filled < s * 0.999:
                    d["unfillable"][s] += 1
                    continue
                d[f"eff{s}"].append((eff - mid) * 100)
            snapshots_per_tok[r["tok"]] += 1
            n += 1
print(f"  {n:,} valid two-sided snapshots over {len(snapshots_per_tok):,} tokens")


def q(v, f):
    if not v:
        return None
    v = sorted(v)
    return round(v[int(len(v) * f)], 4)


print("\n=== EFFECTIVE COST OF BUYING, in pp above mid ===")
print(f"{'category':>10} {'n':>9} {'full sprd':>10} {'half':>7} " +
      " ".join(f"{'$'+str(s):>8}" for s in SIZES) + f" {'unfill$500':>11}")
cat_out = {}
for cat, d in sorted(by_cat.items(), key=lambda kv: -len(kv[1]["full"])):
    row = {
        "n_snapshots": len(d["full"]),
        "full_spread_pp": {"p25": q(d["full"], .25), "median": q(d["full"], .5),
                           "p75": q(d["full"], .75), "p90": q(d["full"], .9)},
        "half_spread_pp": {"median": q(d["half"], .5), "p75": q(d["half"], .75)},
        "effective_cost_pp": {str(s): {"median": q(d[f"eff{s}"], .5),
                                       "p75": q(d[f"eff{s}"], .75),
                                       "n": len(d[f"eff{s}"]),
                                       "unfillable": d["unfillable"][s]}
                              for s in SIZES},
    }
    cat_out[cat] = row
    unf = d["unfillable"][500] / max(len(d["full"]), 1)
    print(f"{cat:>10} {len(d['full']):>9,} "
          f"{q(d['full'], .5):>10.3f} {q(d['half'], .5):>7.3f} " +
          " ".join(f"{(q(d[f'eff{s}'], .5) or float('nan')):>8.3f}"
                   for s in SIZES) + f" {unf:>10.1%}")

pol = cat_out.get("politics")
report = {"meta": {"n_snapshots": n, "n_tokens": len(snapshots_per_tok),
                   "files": len(files), "sizes_usd": SIZES,
                   "assumed_haircut_pp_previously": 1.0,
                   "note": "cost is measured ABOVE MID because traded prices "
                           "sit near mid; the copier pays the ask"},
          "by_category": cat_out}

if pol:
    print("\n=== RE-PRICING THE HEADLINE WITH MEASURED POLITICS COST ===")
    variants = {
        "top_of_book_half_spread": pol["half_spread_pp"]["median"],
        "size_200": pol["effective_cost_pp"]["200"]["median"],
        "size_500": pol["effective_cost_pp"]["500"]["median"],
        "size_1000": pol["effective_cost_pp"]["1000"]["median"],
        "old_assumption_1pp": 1.0,
    }
    rep = {}
    print(f"{'haircut':>26} {'pp':>7} | " +
          " ".join(f"{'d'+k:>8}" for k in TASK5_GROSS) + " | " +
          " ".join(f"{k.split('_')[0][:8]:>9}" for k in HEADLINE_GROSS))
    for vname, hc in variants.items():
        if hc is None:
            continue
        t5 = {k: round(v - hc, 4) for k, v in TASK5_GROSS.items()}
        hl = {k: round(v - hc, 4) for k, v in HEADLINE_GROSS.items()}
        rep[vname] = {"haircut_pp": hc, "task5_net": t5, "headline_net": hl}
        print(f"{vname:>26} {hc:>7.3f} | " +
              " ".join(f"{t5[k]:>8.3f}" for k in TASK5_GROSS) + " | " +
              " ".join(f"{hl[k]:>9.3f}" for k in HEADLINE_GROSS))
    report["repricing"] = rep
    print("\n  (d0 is NOT reachable -- 55.5% of the time it is the wallet's own "
          "trade. Read d10/d60.)")

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
