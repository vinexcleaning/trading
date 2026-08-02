"""Where does the selected wallets' edge actually come from -- and can it be copied?

Phase 4a says a period-1 top decile keeps ~+3.5pp of excess into period 2.
Phase 4c says copying those same wallets' buys loses ~5.9pp, and the curve is
FLAT across delays from 0s to 1800s. Both cannot be casually true, so this
decomposes the contradiction. The 4c measurement rests on only 1,944 signals in
140 markets (the overlap between the selected wallets and the 2,529-market
panel), so the first job is to redo it at full sample size.

The two quantities are genuinely different, and that is the point:

    wallet edge   = (exit proceeds + settlement value) / shares_bought
                    - cost / shares_bought
    copier return = outcome - entry_price - fee            [buy and hold]

A wallet that buys, watches the price rise, and sells has a large edge. A copier
who buys at the same price and holds to settlement gets whatever the market
finally does, which is a different bet. If the selected wallets' edge lives in
their EXITS, it cannot be captured by copying their entries -- and their exits
arrive with the same delay as their entries.

Computed on the WALLET panel, where every fill of every selected wallet is
present, rather than on the sliver that intersects the market panel.
"""
import json
import math
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = ROOT / "data" / "wallet_positions.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
OUT = ROOT / "reports" / "phase4c_copyability.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

FEE_RATE = 0.10
import os
CUT = int(os.environ.get("COPY_CUT", "1751328000"))     # default 2025-07-01
MIN_MARKETS_P1 = int(os.environ.get("COPY_MIN_MKTS", "50"))
OUT = ROOT / "reports" / f"phase4c_copyability_{CUT}.json"
SEED = 20260801
N_BOOT = 2000

BUCKETS = [(0.00, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.30),
           (0.30, 0.40), (0.40, 0.50), (0.50, 0.60), (0.60, 0.70),
           (0.70, 0.80), (0.80, 0.90), (0.90, 0.95), (0.95, 1.00)]


def bucket_of(p):
    for lo, hi in BUCKETS:
        if lo <= p < hi:
            return f"{lo:.2f}-{hi:.2f}"
    return "1.00"


def fee(p):
    return FEE_RATE * min(p, 1 - p)


excluded = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])

print("loading positions...", flush=True)
p1, p2 = [], []
n = 0
for line in POS.open(encoding="utf-8"):
    r = json.loads(line)
    n += 1
    if r["flags"] or r["edge"] is None or r["settle_state"] != "settled":
        continue
    if r["cost"] <= 0 or r["shares_in"] <= 0:
        continue
    rec = (r["wallet"], r["cid"], r["cost"], r["edge"], r["entry_px"],
           1.0 if r["is_winner"] else 0.0, r["frac_held"], r["fees"],
           r["shares_in"], r["n_sells"])
    (p1 if r["first_ts"] < CUT else p2).append(rec)
    if n % 3_000_000 == 0:
        print(f"  {n:,}", flush=True)
print(f"  {n:,} rows -> p1 {len(p1):,}  p2 {len(p2):,}")


def wallet_market(rows):
    wm = {}
    for w, cid, c, e, px, out, fh, fees, si, nsell in rows:
        k = (w, cid)
        a = wm.get(k)
        if a is None:
            a = wm[k] = {"c": 0.0, "e": 0.0, "px": 0.0, "out": 0.0,
                         "fh": 0.0, "si": 0.0, "nsell": 0}
        a["c"] += c
        a["e"] += e * c
        a["px"] += px * c
        a["out"] += out * c
        a["fh"] += (fh or 0.0) * c
        a["si"] += si
        a["nsell"] += nsell
    return [{"w": k[0], "cid": k[1], "cost": a["c"], "edge": a["e"] / a["c"],
             "px": a["px"] / a["c"], "outcome": a["out"] / a["c"],
             "frac_held": a["fh"] / a["c"], "shares_in": a["si"],
             "n_sells": a["nsell"]}
            for k, a in wm.items()]


wm1, wm2 = wallet_market(p1), wallet_market(p2)

# period-1 benchmark and selection
bench = defaultdict(lambda: [0, 0.0])
for r in wm1:
    b = bench[bucket_of(r["px"])]
    b[0] += 1
    b[1] += r["edge"]
mu1 = {k: v[1] / v[0] for k, v in bench.items() if v[0]}
per_w = defaultdict(list)
for r in wm1:
    per_w[r["w"]].append(r["edge"] - mu1.get(bucket_of(r["px"]), 0.0))
elig = {w: sum(v) / len(v) for w, v in per_w.items()
        if len(v) >= MIN_MARKETS_P1 and w not in excluded}
order = sorted(elig, key=lambda w: -elig[w])
k = max(len(order) // 10, 1)
TOP, BOTTOM, ALL = set(order[:k]), set(order[-k:]), set(order)
print(f"\n  {len(elig)} eligible; top decile {len(TOP)} wallets, "
      f"p1 excess {sum(elig[w] for w in TOP)/len(TOP)*100:.3f}pp")

# period-2 benchmark
bench2 = defaultdict(lambda: [0, 0.0])
for r in wm2:
    b = bench2[bucket_of(r["px"])]
    b[0] += 1
    b[1] += r["edge"]
mu2 = {kk: v[1] / v[0] for kk, v in bench2.items() if v[0]}


MAX_BOOT_CLUSTERS = 20_000


def boot_ci(by_mkt, n_boot=N_BOOT, seed=SEED):
    """Market-clustered bootstrap.

    The resample is over MARKETS, so cost is n_boot * n_markets. The "everyone"
    group spans hundreds of thousands of markets, which makes the full version
    ~1e9 operations and it does not finish. Above MAX_BOOT_CLUSTERS the cluster
    list is subsampled to that size and the draw count matched to it. That
    WIDENS the interval slightly relative to the full resample, so it is
    conservative rather than flattering -- and it only ever applies to the large
    groups, whose intervals are already tight. The small groups that decide the
    verdict are bootstrapped in full.
    """
    keys = [kk for kk, v in by_mkt.items() if v]
    if len(keys) < 5:
        return None
    rng = random.Random(seed)
    subsampled = False
    if len(keys) > MAX_BOOT_CLUSTERS:
        keys = rng.sample(keys, MAX_BOOT_CLUSTERS)
        subsampled = True
    pre = [(len(by_mkt[kk]), sum(by_mkt[kk])) for kk in keys]
    K, out = len(pre), []
    for _ in range(n_boot):
        c = s = 0
        for _ in range(K):
            a, b = pre[rng.randrange(K)]
            c += a
            s += b
        if c:
            out.append(s / c * 100)
    out.sort()
    ci = [round(out[int(len(out) * .025)], 4), round(out[int(len(out) * .975)], 4)]
    return ci + ["subsampled_clusters"] if subsampled else ci


def analyse(group_name, members):
    rows = [r for r in wm2 if members is None or r["w"] in members]
    if not rows:
        return None
    edge_m, excess_m, copy_m, held_m, sells_m = (defaultdict(list) for _ in range(5))
    for r in rows:
        cid = r["cid"]
        edge_m[cid].append(r["edge"])
        excess_m[cid].append(r["edge"] - mu2.get(bucket_of(r["px"]), 0.0))
        # what a copier gets: buy at the wallet's entry, hold to settlement
        copy_m[cid].append(r["outcome"] - r["px"] - fee(r["px"]))
        held_m[cid].append(r["frac_held"])
        sells_m[cid].append(1.0 if r["n_sells"] > 0 else 0.0)

    def flat(d):
        return [v for vs in d.values() for v in vs]

    e, x, c, h, s = (flat(d) for d in (edge_m, excess_m, copy_m, held_m, sells_m))
    return {
        "n_wallets": len({r["w"] for r in rows}),
        "n_wallet_markets": len(rows),
        "n_markets": len(edge_m),
        "wallet_edge_pp": round(sum(e) / len(e) * 100, 4),
        "wallet_excess_pp": round(sum(x) / len(x) * 100, 4),
        "wallet_excess_ci95": boot_ci(excess_m),
        "copier_buy_and_hold_pp": round(sum(c) / len(c) * 100, 4),
        "copier_ci95": boot_ci(copy_m),
        "gap_edge_minus_copier_pp": round((sum(e) / len(e) - sum(c) / len(c)) * 100, 4),
        "mean_frac_held_to_settlement": round(sum(h) / len(h), 4),
        "frac_positions_with_any_sell": round(sum(s) / len(s), 4),
        "mean_entry_px": round(
            sum(r["px"] for r in rows) / len(rows), 4),
    }


groups = {"top_decile": TOP, "bottom_decile": BOTTOM,
          "all_eligible": ALL, "everyone": None}
out = {}
print("\n=== PERIOD 2 (out of sample): wallet edge vs what a copier gets ===")
print(f"{'group':>14} {'n_wm':>9} {'edge':>8} {'excess':>8} {'excess CI':>18} "
      f"{'copier':>9} {'copier CI':>18} {'gap':>8} {'held':>6} {'sold':>6}")
for g, mem in groups.items():
    r = analyse(g, mem)
    if r is None:
        continue
    out[g] = r
    print(f"{g:>14} {r['n_wallet_markets']:>9,} {r['wallet_edge_pp']:>8.3f} "
          f"{r['wallet_excess_pp']:>8.3f} {str(r['wallet_excess_ci95']):>18} "
          f"{r['copier_buy_and_hold_pp']:>9.3f} {str(r['copier_ci95']):>18} "
          f"{r['gap_edge_minus_copier_pp']:>8.3f} "
          f"{r['mean_frac_held_to_settlement']:>6.3f} "
          f"{r['frac_positions_with_any_sell']:>6.3f}")

report = {
    "meta": {
        "cut_iso": time.strftime("%Y-%m-%d", time.gmtime(CUT)),
        "selection": f"period-1 only, >= {MIN_MARKETS_P1} markets, non-MM",
        "n_eligible": len(elig), "n_top_decile": len(TOP),
        "definitions": {
            "wallet_edge": "(proceeds + settlement) / shares_in - cost / shares_in",
            "wallet_excess": "wallet_edge minus period-2 pooled mean at same "
                             "entry-price bucket",
            "copier_buy_and_hold": "outcome - entry_price - fee(entry_price); "
                                   "what copying the ENTRY and holding gives",
            "gap": "wallet_edge - copier_return; the part of the wallet's edge "
                   "that lives in its EXITS rather than its entries",
        },
        "clustering": "market-level bootstrap",
    },
    "period2": out,
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
