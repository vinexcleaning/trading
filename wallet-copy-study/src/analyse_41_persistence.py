"""Phase 4a: PERSISTENCE. The decisive test -- if this fails, the study is over.

Rank wallets on period 1, then evaluate those same wallets on period 2 without
touching period 2 during selection. If the rank correlation is near zero, past
wallet performance does not predict future wallet performance and copy trading
is dead regardless of how good the leaderboard looks: with tens of thousands of
wallets, the top of any past-performance ranking is guaranteed to look brilliant
by chance alone.

Two things this does that the prior attempt did not:

1. **The unit of observation is a MARKET, not a trade.** A wallet's positions
   are aggregated to market level first (cost-weighted across the tokens it held
   in that market), and every average and every bootstrap draw is over markets.
   21 bets on one match is one observation. Treating it as 21 is what turned a
   coinflip into a "+95pp genius".

2. **Everything is measured as EXCESS over the price-bucket benchmark.** A
   wallet buying at 0.90 and winning 90% has zero skill; it bought favourites.
   So each position's edge has the pooled average edge at that entry-price
   bucket subtracted from it. Raw edge is reported alongside, and where the two
   disagree the raw number is the misleading one.

Run at multiple cut points, because a persistence result that only appears at
one split is an artifact of where the split was drawn. The 2026-01-08 fee-regime
cut is included deliberately: it straddles a change in the cost structure, so
comparing it against the calendar cuts separates skill decay from regime change.
"""
import json
import math
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = ROOT / "data" / "wallet_positions.jsonl"
OUT = ROOT / "reports" / "phase4a_persistence.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

FEE_START = 1767830400
SEED = 20260801
N_BOOT = 2000
MIN_MARKETS = [10, 20, 50]

CUTS = [
    ("2024-07-01", 1719792000),
    ("2025-01-01", 1735689600),
    ("2025-07-01", 1751328000),
    ("2026-01-08_fee_regime", FEE_START),
]

BUCKETS = [(0.00, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.30),
           (0.30, 0.40), (0.40, 0.50), (0.50, 0.60), (0.60, 0.70),
           (0.70, 0.80), (0.80, 0.90), (0.90, 0.95), (0.95, 1.00)]


def bucket_of(p):
    for lo, hi in BUCKETS:
        if lo <= p < hi:
            return f"{lo:.2f}-{hi:.2f}"
    return "1.00"


# --------------------------------------------------------- load positions
print("loading positions...", flush=True)
# aggregate to (wallet, market): cost-weighted edge, cost, entry px, first_ts
wm = {}
n = 0
t0 = time.time()
for line in POS.open(encoding="utf-8"):
    r = json.loads(line)
    n += 1
    if r["flags"] or r["edge"] is None or r["settle_state"] != "settled":
        continue
    c = r["cost"]
    if c <= 0:
        continue
    k = (r["wallet"], r["cid"])
    a = wm.get(k)
    if a is None:
        a = wm[k] = {"cost": 0.0, "wedge": 0.0, "wedge_net": 0.0, "wpx": 0.0,
                     "ts": r["first_ts"], "n": 0}
    a["cost"] += c
    a["wedge"] += r["edge"] * c
    a["wedge_net"] += r["edge_net"] * c
    a["wpx"] += r["entry_px"] * c
    a["ts"] = min(a["ts"], r["first_ts"])
    a["n"] += 1
    if n % 2_000_000 == 0:
        print(f"  {n:,} rows  {time.time()-t0:.0f}s", flush=True)

recs = []
for (w, cid), a in wm.items():
    c = a["cost"]
    recs.append({"w": w, "cid": cid, "ts": a["ts"], "cost": c,
                 "edge": a["wedge"] / c, "edge_net": a["wedge_net"] / c,
                 "px": a["wpx"] / c})
del wm
print(f"  {n:,} position rows -> {len(recs):,} (wallet,market) observations "
      f"in {time.time()-t0:.0f}s")

# ------------------------------------- pooled price-bucket benchmark
bench = defaultdict(lambda: [0, 0.0, 0.0])
for r in recs:
    b = bench[bucket_of(r["px"])]
    b[0] += 1
    b[1] += r["edge"]
    b[2] += r["edge_net"]
benchmark = {k: {"n": v[0], "mean_edge_pp": round(v[1] / v[0] * 100, 4),
                 "mean_edge_net_pp": round(v[2] / v[0] * 100, 4)}
             for k, v in bench.items() if v[0]}
bench_mu = {k: v[1] / v[0] for k, v in bench.items() if v[0]}
bench_mu_net = {k: v[2] / v[0] for k, v in bench.items() if v[0]}

print("\n=== pooled benchmark by entry-price bucket (wallet panel) ===")
for lo, hi in BUCKETS:
    b = f"{lo:.2f}-{hi:.2f}"
    if b in benchmark:
        e = benchmark[b]
        print(f"  {b:>12}  n={e['n']:>8,}  edge {e['mean_edge_pp']:>8.3f}pp  "
              f"net {e['mean_edge_net_pp']:>8.3f}pp")

for r in recs:
    b = bucket_of(r["px"])
    r["ex"] = r["edge"] - bench_mu.get(b, 0.0)
    r["ex_net"] = r["edge_net"] - bench_mu_net.get(b, 0.0)


# ----------------------------------------------------------- statistics
def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                rk[order[k]] = avg
            i = j + 1
        return rk

    rx, ry = rank(xs), rank(ys)
    nn = len(xs)
    mx, my = sum(rx) / nn, sum(ry) / nn
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (dx * dy) if dx and dy else 0.0


def boot_mean_ci(vals, n_boot=N_BOOT, seed=SEED):
    if len(vals) < 5:
        return None
    rng = random.Random(seed)
    N = len(vals)
    out = []
    for _ in range(n_boot):
        s = 0.0
        for _ in range(N):
            s += vals[rng.randrange(N)]
        out.append(s / N * 100)
    out.sort()
    return [round(out[int(len(out) * .025)], 4), round(out[int(len(out) * .975)], 4)]


def analyse_cut(label, cut, min_mkts):
    p1, p2 = defaultdict(list), defaultdict(list)
    for r in recs:
        (p1 if r["ts"] < cut else p2)[r["w"]].append(r)
    both = [w for w in p1 if w in p2
            and len(p1[w]) >= min_mkts and len(p2[w]) >= min_mkts]

    # ---- SURVIVORSHIP AUDIT -------------------------------------------
    # Requiring activity in BOTH periods silently excludes wallets that blew up
    # and stopped trading. If the quitters were the bad ones, every persistence
    # number below is biased upward. Measured rather than assumed: compare the
    # period-1 performance of wallets that came back against those that did not.
    p1_qualified = [w for w in p1 if len(p1[w]) >= min_mkts]
    survivors = [w for w in p1_qualified if w in p2]
    quitters = [w for w in p1_qualified if w not in p2]

    def mu_of(ws, per, key):
        vals = [sum(x[key] for x in per[w]) / len(per[w]) for w in ws]
        return (sum(vals) / len(vals) * 100) if vals else None

    survivorship = {
        "n_p1_qualified": len(p1_qualified),
        "n_survived_into_p2": len(survivors),
        "n_quit_after_p1": len(quitters),
        "attrition_rate": round(len(quitters) / max(len(p1_qualified), 1), 4),
        "p1_excess_pp_of_survivors": round(mu_of(survivors, p1, "ex"), 4)
            if survivors else None,
        "p1_excess_pp_of_quitters": round(mu_of(quitters, p1, "ex"), 4)
            if quitters else None,
    }
    if survivorship["p1_excess_pp_of_survivors"] is not None and \
            survivorship["p1_excess_pp_of_quitters"] is not None:
        survivorship["survivor_minus_quitter_pp"] = round(
            survivorship["p1_excess_pp_of_survivors"]
            - survivorship["p1_excess_pp_of_quitters"], 4)
        survivorship["bias_direction"] = (
            "UPWARD: survivors outperformed quitters in period 1, so the "
            "both-periods requirement keeps the better wallets"
            if survivorship["survivor_minus_quitter_pp"] > 0 else
            "downward or neutral: survivors did not outperform quitters")
    if len(both) < 20:
        return {"cut": label, "min_markets": min_mkts,
                "n_wallets_qualifying": len(both),
                "survivorship_audit": survivorship,
                "verdict": "TOO FEW WALLETS QUALIFY -- no test possible"}

    def mu(rows, key):
        return sum(x[key] for x in rows) / len(rows)

    a_ex = [mu(p1[w], "ex") for w in both]
    b_ex = [mu(p2[w], "ex") for w in both]
    a_raw = [mu(p1[w], "edge") for w in both]
    b_raw = [mu(p2[w], "edge") for w in both]

    rho_ex = spearman(a_ex, b_ex)
    rho_raw = spearman(a_raw, b_raw)

    # top decile selected on period 1 EXCESS, evaluated on period 2
    order = sorted(range(len(both)), key=lambda i: -a_ex[i])
    k = max(len(both) // 10, 1)
    top = [order[i] for i in range(k)]
    bot = [order[-(i + 1)] for i in range(k)]
    top_p2 = [b_ex[i] for i in top]
    bot_p2 = [b_ex[i] for i in bot]
    all_p2 = b_ex

    # a null: shuffle period-1 ranks, re-select, same size. If the real top
    # decile is no better than a random decile, selection is doing nothing.
    rng = random.Random(SEED)
    nulls = []
    for _ in range(400):
        idx = rng.sample(range(len(both)), k)
        nulls.append(sum(b_ex[i] for i in idx) / k * 100)
    nulls.sort()

    return {
        "cut": label,
        "cut_ts": cut,
        "min_markets": min_mkts,
        "n_wallets_qualifying": len(both),
        "survivorship_audit": survivorship,
        "median_markets_p1": sorted(len(p1[w]) for w in both)[len(both) // 2],
        "median_markets_p2": sorted(len(p2[w]) for w in both)[len(both) // 2],
        "spearman_excess": round(rho_ex, 4),
        "spearman_raw_edge": round(rho_raw, 4),
        "period1_top_decile": {
            "n": k,
            "p1_mean_excess_pp": round(sum(a_ex[i] for i in top) / k * 100, 4),
            "p2_mean_excess_pp": round(sum(top_p2) / k * 100, 4),
            "p2_ci95_pp": boot_mean_ci(top_p2),
        },
        "period1_bottom_decile": {
            "n": k,
            "p1_mean_excess_pp": round(sum(a_ex[i] for i in bot) / k * 100, 4),
            "p2_mean_excess_pp": round(sum(bot_p2) / k * 100, 4),
        },
        "all_qualifying_wallets_p2_mean_excess_pp":
            round(sum(all_p2) / len(all_p2) * 100, 4),
        "random_decile_null_p2_excess_pp": {
            "mean": round(sum(nulls) / len(nulls), 4),
            "p05": round(nulls[int(len(nulls) * .05)], 4),
            "p95": round(nulls[int(len(nulls) * .95)], 4),
        },
        "top_decile_beats_random_decile":
            (sum(top_p2) / k * 100) > nulls[int(len(nulls) * .95)],
    }


print("\n=== PERSISTENCE ===")
results = []
for label, cut in CUTS:
    for mm in MIN_MARKETS:
        r = analyse_cut(label, cut, mm)
        results.append(r)
        if "verdict" in r:
            print(f"  {label:>24} min={mm:<3} {r['verdict']} "
                  f"(n={r['n_wallets_qualifying']})")
        else:
            td = r["period1_top_decile"]
            print(f"  {label:>24} min={mm:<3} n={r['n_wallets_qualifying']:>5}  "
                  f"rho_excess={r['spearman_excess']:>7.4f}  "
                  f"rho_raw={r['spearman_raw_edge']:>7.4f}  "
                  f"top-decile P2 {td['p2_mean_excess_pp']:>8.3f}pp "
                  f"CI{td['p2_ci95_pp']}  "
                  f"vs random {r['random_decile_null_p2_excess_pp']['mean']:>7.3f}pp")

report = {
    "meta": {
        "n_position_rows": n,
        "n_wallet_market_observations": len(recs),
        "n_distinct_wallets": len({r["w"] for r in recs}),
        "unit_of_observation": "wallet x market; positions aggregated "
                               "cost-weighted across tokens within a market",
        "metric": "excess = (realised value per share - entry price) minus the "
                  "pooled mean at the same entry-price bucket",
        "n_bootstrap": N_BOOT,
        "cuts": [c[0] for c in CUTS],
        "min_markets_tested": MIN_MARKETS,
    },
    "price_bucket_benchmark": benchmark,
    "persistence": results,
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
