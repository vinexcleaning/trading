"""Phase 4a, re-run under the two conditions that could kill the result.

The first persistence pass found rank correlation 0.16-0.35 and a symmetric
decile pattern (top +6.05 -> +3.06pp, bottom -6.13 -> -2.19pp). Symmetry is
hard to get from noise, but two rival explanations remain and both must be
eliminated before the result means anything:

  A. MARKET MAKERS. Median hold time across the panel is 32 seconds and the
     25th percentile is zero. If the top decile is market makers earning the
     spread and the bottom decile is the retail flow paying it, the pattern is
     exactly this symmetric -- and it is uncopyable, because by the time you see
     a maker's fill the quote that earned it is gone. Phase 2 excluded 721 of
     2,500 wallets (682 market-maker fingerprints, 41 too large to copy); this
     re-runs without them.

  B. PSEUDO-REPLICATION ACROSS A SERIES. Clustering by market treats 288 BTC
     up/down 5-minute markets in one day as 288 independent observations. They
     are not. This is the same failure as "21 bets on one match counted 21
     times", one level up: the correlated unit is the SERIES, not the market.
     Observations are therefore also aggregated to (wallet, series, day) and the
     whole test re-run on that coarser, more honest unit.

If the result survives both, it is real. If it dies under either, that is the
finding.
"""
import json
import math
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI = ROOT / "data" / "markets_clob.jsonl"
POS = ROOT / "data" / "wallet_positions.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
OUT = ROOT / "reports" / "phase4a_persistence_clean.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

SEED = 20260801
N_BOOT = 2000
CUTS = [("2025-01-01", 1735689600), ("2025-07-01", 1751328000),
        ("2026-01-08_fee_regime", 1767830400)]
MIN_OBS = [10, 20, 50]

BUCKETS = [(0.00, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.30),
           (0.30, 0.40), (0.40, 0.50), (0.50, 0.60), (0.60, 0.70),
           (0.70, 0.80), (0.80, 0.90), (0.90, 0.95), (0.95, 1.00)]


def bucket_of(p):
    for lo, hi in BUCKETS:
        if lo <= p < hi:
            return f"{lo:.2f}-{hi:.2f}"
    return "1.00"


_num = re.compile(r"\d+")


def series_key(slug):
    """Collapse a slug to its recurring series.

    'btc-updown-5m-1785563700'          -> 'btc-updown-5m'
    'will-x-happen-20260612232105703'   -> 'will-x-happen'
    A one-off market keeps its own slug and is its own series, which is correct:
    it genuinely is one independent event.
    """
    if not slug:
        return "?"
    parts = [p for p in slug.split("-") if not (_num.fullmatch(p) and len(p) >= 4)]
    return "-".join(parts) if parts else slug


print("loading cid -> series map...", flush=True)
cid2series = {}
n = 0
t0 = time.time()
for line in UNI.open(encoding="utf-8"):
    m = json.loads(line)
    cid2series[m["condition_id"]] = series_key(m.get("slug"))
    n += 1
    if n % 700_000 == 0:
        print(f"  {n:,}  {time.time()-t0:.0f}s", flush=True)
print(f"  {n:,} markets, {len(set(cid2series.values())):,} distinct series "
      f"in {time.time()-t0:.0f}s")

excluded = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])
print(f"Phase-2 exclusions: {len(excluded):,} wallets")

# ------------------------------------------------------- load positions
print("\nloading positions...", flush=True)
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
        a = wm[k] = {"c": 0.0, "e": 0.0, "px": 0.0, "ts": r["first_ts"]}
    a["c"] += c
    a["e"] += r["edge"] * c
    a["px"] += r["entry_px"] * c
    a["ts"] = min(a["ts"], r["first_ts"])
    if n % 3_000_000 == 0:
        print(f"  {n:,}  {time.time()-t0:.0f}s", flush=True)

recs = []
for (w, cid), a in wm.items():
    c = a["c"]
    recs.append({"w": w, "cid": cid, "ts": a["ts"], "cost": c,
                 "edge": a["e"] / c, "px": a["px"] / c,
                 "series": cid2series.get(cid, "?")})
del wm
print(f"  -> {len(recs):,} (wallet,market) observations in {time.time()-t0:.0f}s")

# pooled price-bucket benchmark, computed on the SAME population evaluated
bench = defaultdict(lambda: [0, 0.0])
for r in recs:
    b = bench[bucket_of(r["px"])]
    b[0] += 1
    b[1] += r["edge"]
mu_b = {k: v[1] / v[0] for k, v in bench.items() if v[0]}
for r in recs:
    r["ex"] = r["edge"] - mu_b.get(bucket_of(r["px"]), 0.0)


def to_series_day(rows):
    """Collapse (wallet, market) rows to (wallet, series, day), cost-weighted."""
    agg = {}
    for r in rows:
        k = (r["w"], r["series"], r["ts"] // 86400)
        a = agg.get(k)
        if a is None:
            a = agg[k] = {"c": 0.0, "ex": 0.0, "ts": r["ts"]}
        a["c"] += r["cost"]
        a["ex"] += r["ex"] * r["cost"]
        a["ts"] = min(a["ts"], r["ts"])
    return [{"w": k[0], "ts": a["ts"], "ex": a["ex"] / a["c"], "cost": a["c"]}
            for k, a in agg.items() if a["c"] > 0]


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


def boot_ci(vals, n_boot=N_BOOT, seed=SEED):
    if len(vals) < 5:
        return None
    rng = random.Random(seed)
    N, out = len(vals), []
    for _ in range(n_boot):
        out.append(sum(vals[rng.randrange(N)] for _ in range(N)) / N * 100)
    out.sort()
    return [round(out[int(len(out) * .025)], 4), round(out[int(len(out) * .975)], 4)]


def run(rows, label, cut, min_obs, tag):
    p1, p2 = defaultdict(list), defaultdict(list)
    for r in rows:
        (p1 if r["ts"] < cut else p2)[r["w"]].append(r["ex"])
    both = [w for w in p1 if w in p2
            and len(p1[w]) >= min_obs and len(p2[w]) >= min_obs]
    if len(both) < 20:
        return {"unit": tag, "cut": label, "min_obs": min_obs,
                "n_wallets": len(both), "verdict": "too few wallets"}
    a = [sum(p1[w]) / len(p1[w]) for w in both]
    b = [sum(p2[w]) / len(p2[w]) for w in both]
    order = sorted(range(len(both)), key=lambda i: -a[i])
    k = max(len(both) // 10, 1)
    top = [b[order[i]] for i in range(k)]
    bot = [b[order[-(i + 1)]] for i in range(k)]
    rng = random.Random(SEED)
    nulls = sorted(sum(b[rng.randrange(len(b))] for _ in range(k)) / k * 100
                   for _ in range(400))
    return {
        "unit": tag, "cut": label, "min_obs": min_obs,
        "n_wallets": len(both),
        "median_obs_p1": sorted(len(p1[w]) for w in both)[len(both) // 2],
        "median_obs_p2": sorted(len(p2[w]) for w in both)[len(both) // 2],
        "spearman": round(spearman(a, b), 4),
        "top_decile_p1_pp": round(sum(a[order[i]] for i in range(k)) / k * 100, 4),
        "top_decile_p2_pp": round(sum(top) / k * 100, 4),
        "top_decile_p2_ci95": boot_ci(top),
        "bottom_decile_p1_pp": round(
            sum(a[order[-(i + 1)]] for i in range(k)) / k * 100, 4),
        "bottom_decile_p2_pp": round(sum(bot) / k * 100, 4),
        "bottom_decile_p2_ci95": boot_ci(bot),
        "all_wallets_p2_pp": round(sum(b) / len(b) * 100, 4),
        "random_decile_p2_pp": round(sum(nulls) / len(nulls), 4),
        "random_decile_p95": round(nulls[int(len(nulls) * .95)], 4),
        "top_beats_random_p95": (sum(top) / k * 100) > nulls[int(len(nulls) * .95)],
    }


results = []
scenarios = [
    ("A_all_wallets_market_unit", recs, False, "market"),
    ("B_nonMM_market_unit", [r for r in recs if r["w"] not in excluded], False, "market"),
    ("C_all_wallets_series_day_unit", recs, True, "series-day"),
    ("D_nonMM_series_day_unit",
     [r for r in recs if r["w"] not in excluded], True, "series-day"),
]

print("\n=== PERSISTENCE UNDER EACH CONDITION ===")
for name, rows, collapse, tag in scenarios:
    use = to_series_day(rows) if collapse else rows
    print(f"\n-- {name}  ({len(use):,} observations, "
          f"{len({r['w'] for r in use}):,} wallets)")
    for label, cut in CUTS:
        for mo in MIN_OBS:
            r = run(use, label, cut, mo, tag)
            r["scenario"] = name
            results.append(r)
            if "verdict" in r:
                print(f"   {label:>22} min={mo:<3} {r['verdict']} (n={r['n_wallets']})")
            else:
                print(f"   {label:>22} min={mo:<3} n={r['n_wallets']:>5} "
                      f"rho={r['spearman']:>7.4f}  "
                      f"top P1 {r['top_decile_p1_pp']:>7.2f} -> P2 "
                      f"{r['top_decile_p2_pp']:>7.3f}pp CI{r['top_decile_p2_ci95']}  "
                      f"bot P2 {r['bottom_decile_p2_pp']:>7.3f}pp  "
                      f"beats_rand={r['top_beats_random_p95']}")

report = {
    "meta": {
        "n_wallet_market_obs": len(recs),
        "n_excluded_wallets": len(excluded),
        "n_distinct_series": len(set(cid2series.values())),
        "scenarios": {
            "A": "all wallets, unit = market (the original pass)",
            "B": "market makers and too-large wallets removed, unit = market",
            "C": "all wallets, unit = (wallet, series, day)",
            "D": "both corrections applied -- the honest test",
        },
        "metric": "excess over pooled mean at same entry-price bucket",
    },
    "price_bucket_benchmark": {k: {"n": v[0], "mean_edge_pp": round(v[1] / v[0] * 100, 4)}
                               for k, v in bench.items() if v[0]},
    "results": results,
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
