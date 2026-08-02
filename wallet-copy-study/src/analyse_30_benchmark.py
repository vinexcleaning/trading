"""Phase 3: the naive bias benchmark. Run BEFORE ranking anybody.

Buy everything in a price bucket, no wallet selection at all, hold to
settlement. This is the number every wallet must beat. A prior attempt reported
a +7.23pp top-decile "wallet edge" that turned out to be +7.05pp of
favourite-longshot bias available to anyone who bought favourites -- the wallets
had exposure, not skill.

Return on a buy held to settlement is
    (1 if the token won else 0) - price
which is exactly "realised outcome minus entry price", the study's only metric.

Confidence intervals are CLUSTERED BY MARKET via a market-level bootstrap.
Trade-level intervals would be a lie here: 21 bets on one match is one
coinflip, not 21, and independent-trade intervals are what made a coinflip
wallet look like a +95pp genius.

Reported per fee regime, because fees were zero before 2026-01-08 (probe_03) and
a bias that is profitable gross may not be net.
"""
import json
import math
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILLS = ROOT / "data" / "fills.jsonl"
OUT = ROOT / "reports" / "phase3_benchmark.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

FEE_RATE = 0.10
FEE_START = 1767830400          # 2026-01-08
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


# ------------------------------------------------------------------ load
print("loading buy-side fills...")
# per market: list of (bucket, gross_return, net_return, dollars)
by_mkt = defaultdict(list)
n_read = n_buy = 0
skipped = Counter()
t0 = time.time()

for line in FILLS.open(encoding="utf-8"):
    f = json.loads(line)
    n_read += 1
    if f["maker_side"] != "BUY":
        continue
    if f.get("is_winner") is None:
        skipped["no_settlement"] += 1
        continue
    p = f["price"]
    if not (0.0 < p < 1.0):
        skipped["bad_price"] += 1
        continue
    n_buy += 1
    outcome = 1.0 if f["is_winner"] else 0.0
    gross = outcome - p
    net = gross - FEE_RATE * min(p, 1 - p)
    by_mkt[f["cid"]].append(
        (bucket_of(p), gross, net, f["shares"] * p,
         "post" if f["ts"] >= FEE_START else "pre"))

print(f"read {n_read:,} fills, {n_buy:,} buys with settlement, "
      f"{len(by_mkt):,} markets, {time.time()-t0:.0f}s")
print(f"skipped: {dict(skipped)}")


# ------------------------------------------------------- point estimates
def summarise(rows_by_mkt, regime=None):
    """rows_by_mkt: cid -> list of tuples. Returns per-bucket aggregates."""
    agg = defaultdict(lambda: {"n": 0, "g": 0.0, "net": 0.0,
                               "dol": 0.0, "gdol": 0.0, "netdol": 0.0,
                               "mkts": set()})
    for cid, rows in rows_by_mkt.items():
        for b, g, nt, d, reg in rows:
            if regime and reg != regime:
                continue
            a = agg[b]
            a["n"] += 1
            a["g"] += g
            a["net"] += nt
            a["dol"] += d
            a["gdol"] += g * d
            a["netdol"] += nt * d
            a["mkts"].add(cid)
    out = {}
    for b, a in agg.items():
        if not a["n"]:
            continue
        out[b] = {
            "n_trades": a["n"],
            "n_markets": len(a["mkts"]),
            "mean_gross_pp": round(a["g"] / a["n"] * 100, 4),
            "mean_net_pp": round(a["net"] / a["n"] * 100, 4),
            "dollar_wtd_gross_pp": round(a["gdol"] / a["dol"] * 100, 4) if a["dol"] else None,
            "dollar_wtd_net_pp": round(a["netdol"] / a["dol"] * 100, 4) if a["dol"] else None,
            "notional_usd": round(a["dol"], 2),
        }
    return out


# ------------------------------------------ market-clustered bootstrap CI
def bootstrap(rows_by_mkt, regime=None, n_boot=N_BOOT, seed=SEED):
    """Resample MARKETS with replacement. 21 bets on one match is one draw."""
    cids = list(rows_by_mkt.keys())
    # pre-aggregate per market per bucket so each bootstrap draw is cheap
    pre = {}
    for cid in cids:
        d = defaultdict(lambda: [0, 0.0, 0.0])
        for b, g, nt, dol, reg in rows_by_mkt[cid]:
            if regime and reg != regime:
                continue
            e = d[b]
            e[0] += 1
            e[1] += g
            e[2] += nt
        if d:
            pre[cid] = dict(d)
    keys = list(pre.keys())
    if not keys:
        return {}
    rng = random.Random(seed)
    draws = defaultdict(lambda: {"g": [], "net": []})
    K = len(keys)
    for _ in range(n_boot):
        acc = defaultdict(lambda: [0, 0.0, 0.0])
        for _ in range(K):
            cid = keys[rng.randrange(K)]
            for b, (c, g, nt) in pre[cid].items():
                a = acc[b]
                a[0] += c
                a[1] += g
                a[2] += nt
        for b, (c, g, nt) in acc.items():
            if c:
                draws[b]["g"].append(g / c * 100)
                draws[b]["net"].append(nt / c * 100)
    out = {}
    for b, d in draws.items():
        g = sorted(d["g"])
        nt = sorted(d["net"])
        if len(g) < 20:
            continue
        lo, hi = int(len(g) * 0.025), int(len(g) * 0.975)
        out[b] = {
            "gross_ci95_pp": [round(g[lo], 4), round(g[hi], 4)],
            "net_ci95_pp": [round(nt[lo], 4), round(nt[hi], 4)],
            "gross_se_pp": round(statistics_stdev(g), 4),
        }
    return out


def statistics_stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


print("\ncomputing point estimates...")
overall = summarise(by_mkt)
pre_reg = summarise(by_mkt, "pre")
post_reg = summarise(by_mkt, "post")

print("bootstrapping (market-clustered)...")
t0 = time.time()
ci_all = bootstrap(by_mkt)
print(f"  overall done {time.time()-t0:.0f}s")
ci_pre = bootstrap(by_mkt, "pre", n_boot=1000)
ci_post = bootstrap(by_mkt, "post", n_boot=1000)
print(f"  regimes done {time.time()-t0:.0f}s")

# ------------------------------------- the specific claim under audit:
# "buying everything priced 0.60-0.95 earned +7.05pp"
band = defaultdict(list)
for cid, rows in by_mkt.items():
    for b, g, nt, d, reg in rows:
        lo = float(b.split("-")[0]) if "-" in b else 1.0
        if 0.60 <= lo < 0.95:
            band[cid].append((b, g, nt, d, reg))
n_band = sum(len(v) for v in band.values())
band_g = sum(g for v in band.values() for _, g, _, _, _ in v)
band_net = sum(nt for v in band.values() for _, _, nt, _, _ in v)
band_ci = bootstrap({k: [("all", g, nt, d, r) for _, g, nt, d, r in v]
                     for k, v in band.items()}, n_boot=2000)

favourite_band = {
    "definition": "all buys priced 0.60 <= p < 0.95, held to settlement",
    "n_trades": n_band,
    "n_markets": len(band),
    "mean_gross_pp": round(band_g / n_band * 100, 4) if n_band else None,
    "mean_net_pp": round(band_net / n_band * 100, 4) if n_band else None,
    "ci95": band_ci.get("all"),
}

report = {
    "meta": {
        "n_fills_read": n_read,
        "n_buys_scored": n_buy,
        "n_markets": len(by_mkt),
        "skipped": dict(skipped),
        "fee_rate": FEE_RATE,
        "fee_formula": "0.10 * min(p, 1-p) per share, verified probe_02",
        "n_bootstrap": N_BOOT,
        "clustering": "market-level bootstrap; a market is one draw regardless "
                      "of how many trades it contains",
    },
    "by_bucket_overall": overall,
    "by_bucket_ci95": ci_all,
    "by_bucket_pre_fee_regime": pre_reg,
    "by_bucket_pre_ci95": ci_pre,
    "by_bucket_post_fee_regime": post_reg,
    "by_bucket_post_ci95": ci_post,
    "favourite_band_0.60_0.95": favourite_band,
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

# --------------------------------------------------------------- print
print("\n=== NAIVE BENCHMARK: buy everything in bucket, hold to settlement ===")
print(f"{'bucket':>12} {'n_trades':>10} {'n_mkts':>8} "
      f"{'gross pp':>10} {'net pp':>9} {'gross CI95':>22}")
for lo, hi in BUCKETS:
    b = f"{lo:.2f}-{hi:.2f}"
    if b not in overall:
        continue
    o = overall[b]
    c = ci_all.get(b, {})
    ci = c.get("gross_ci95_pp")
    print(f"{b:>12} {o['n_trades']:>10,} {o['n_markets']:>8,} "
          f"{o['mean_gross_pp']:>10.3f} {o['mean_net_pp']:>9.3f} "
          f"{('[%7.3f, %7.3f]' % (ci[0], ci[1])) if ci else '':>22}")

print(f"\nfavourite band 0.60-0.95: n={n_band:,} trades over {len(band):,} markets")
print(f"  gross {favourite_band['mean_gross_pp']}pp   "
      f"net {favourite_band['mean_net_pp']}pp   CI95 {band_ci.get('all', {}).get('gross_ci95_pp')}")
print(f"\nwrote {OUT}")
