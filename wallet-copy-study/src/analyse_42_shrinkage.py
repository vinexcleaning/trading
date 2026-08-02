"""Phase 4b: skill versus luck. Bayesian shrinkage, and the sample-size bar.

Raw wallet means are uninterpretable at these sample sizes. With tens of
thousands of wallets, the best raw mean is essentially guaranteed to belong to
someone lucky rather than someone good, and the fewer markets they traded the
more extreme their mean will be. So only SHRUNK estimates are reported.

Empirical-Bayes, method of moments:
    observed   x_i | theta_i ~ N(theta_i, sigma^2 / n_i)
    true edge  theta_i       ~ N(mu, tau^2)
    tau^2 = Var(x_i) - E[sigma^2 / n_i]        (clamped at 0)
    shrunk_i = mu + tau^2 / (tau^2 + sigma^2/n_i) * (x_i - mu)

If tau^2 comes out at or below zero, the cross-wallet spread in performance is
no larger than sampling noise alone would produce -- which is a finding, not a
failure, and means every wallet's best estimate is the population mean.

n_i counts MARKETS, never trades. Twenty-one bets on one match is one
observation; counting it as 21 shrinks the standard error by 4.6x and is exactly
how a coinflip became a "+95pp genius".

The sample-size bar answers: how many independent markets does it take to tell a
genuinely +5pp wallet from a 0pp one? Because edge per market has SD near
sqrt(p(1-p)) -- roughly 0.5 near even money -- the answer is large, and the count
of wallets clearing it is the real constraint on this whole idea.
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
OUT = ROOT / "reports" / "phase4b_shrinkage.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

SEED = 20260801
TARGET_EDGE = 0.05          # the +5pp wallet we want to be able to detect
ALPHA_Z, POWER_Z = 1.96, 0.84

BUCKETS = [(0.00, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.30),
           (0.30, 0.40), (0.40, 0.50), (0.50, 0.60), (0.60, 0.70),
           (0.70, 0.80), (0.80, 0.90), (0.90, 0.95), (0.95, 1.00)]


def bucket_of(p):
    for lo, hi in BUCKETS:
        if lo <= p < hi:
            return f"{lo:.2f}-{hi:.2f}"
    return "1.00"


try:
    excluded = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])
    print(f"loaded {len(excluded):,} Phase-2 exclusions")
except Exception:  # noqa: BLE001
    excluded = set()
    print("no Phase-2 exclusion file; running on all wallets")

# ------------------------------------------- wallet x market observations
print("loading positions...", flush=True)
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
        a = wm[k] = {"c": 0.0, "e": 0.0, "en": 0.0, "px": 0.0}
    a["c"] += c
    a["e"] += r["edge"] * c
    a["en"] += r["edge_net"] * c
    a["px"] += r["entry_px"] * c
    if n % 2_000_000 == 0:
        print(f"  {n:,} rows  {time.time()-t0:.0f}s", flush=True)

obs = defaultdict(list)          # wallet -> list of (excess, excess_net)
raw = []
for (w, cid), a in wm.items():
    c = a["c"]
    raw.append((w, a["e"] / c, a["en"] / c, a["px"] / c))
del wm
print(f"  {n:,} rows -> {len(raw):,} wallet-market observations "
      f"in {time.time()-t0:.0f}s")

# pooled benchmark by entry-price bucket
bench = defaultdict(lambda: [0, 0.0, 0.0])
for _, e, en, px in raw:
    b = bench[bucket_of(px)]
    b[0] += 1
    b[1] += e
    b[2] += en
mu_b = {k: v[1] / v[0] for k, v in bench.items() if v[0]}
mu_bn = {k: v[2] / v[0] for k, v in bench.items() if v[0]}

for w, e, en, px in raw:
    b = bucket_of(px)
    obs[w].append((e - mu_b.get(b, 0.0), en - mu_bn.get(b, 0.0)))

if excluded:
    before = len(obs)
    obs = {w: v for w, v in obs.items() if w not in excluded}
    print(f"  dropped {before - len(obs):,} excluded wallets -> {len(obs):,}")


# --------------------------------------------------------------- moments
def shrink(min_n, idx=0):
    """idx 0 = gross excess, 1 = net excess."""
    ws = {w: [x[idx] for x in v] for w, v in obs.items() if len(v) >= min_n}
    if len(ws) < 30:
        return {"min_markets": min_n, "n_wallets": len(ws),
                "verdict": "too few wallets"}
    means = {w: sum(v) / len(v) for w, v in ws.items()}
    ns = {w: len(v) for w, v in ws.items()}

    # pooled within-wallet variance
    num = den = 0.0
    for w, v in ws.items():
        if len(v) < 2:
            continue
        m = means[w]
        num += sum((x - m) ** 2 for x in v)
        den += len(v) - 1
    sigma2 = num / den if den else 0.0

    mvals = list(means.values())
    mu = sum(mvals) / len(mvals)
    var_x = sum((x - mu) ** 2 for x in mvals) / (len(mvals) - 1)
    e_noise = sum(sigma2 / ns[w] for w in ws) / len(ws)
    tau2 = var_x - e_noise

    shrunk = {}
    for w in ws:
        if tau2 <= 0:
            shrunk[w] = mu
        else:
            lam = tau2 / (tau2 + sigma2 / ns[w])
            shrunk[w] = mu + lam * (means[w] - mu)
    sv = sorted(shrunk.values())

    # markets needed to separate a +5pp wallet from 0pp
    sigma = math.sqrt(sigma2) if sigma2 > 0 else float("nan")
    n_needed = ((ALPHA_Z + POWER_Z) * sigma / TARGET_EDGE) ** 2 if sigma2 > 0 else None
    n_clear = sum(1 for w in ws if ns[w] >= (n_needed or 1e18))

    def qv(f):
        return round(sv[int(len(sv) * f)] * 100, 4)

    return {
        "min_markets": min_n,
        "n_wallets": len(ws),
        "median_markets_per_wallet": sorted(ns.values())[len(ns) // 2],
        "sigma_per_market": round(sigma, 4),
        "sigma2": round(sigma2, 6),
        "raw_mean_spread_pp": {
            "p01": round(sorted(mvals)[int(len(mvals) * .01)] * 100, 4),
            "p50": round(sorted(mvals)[len(mvals) // 2] * 100, 4),
            "p99": round(sorted(mvals)[int(len(mvals) * .99)] * 100, 4),
            "max": round(max(mvals) * 100, 4),
        },
        "mu_pp": round(mu * 100, 4),
        "var_between_observed_pp2": round(var_x * 10000, 4),
        "expected_noise_var_pp2": round(e_noise * 10000, 4),
        "tau2_pp2": round(tau2 * 10000, 4),
        "tau_pp": round(math.sqrt(tau2) * 100, 4) if tau2 > 0 else 0.0,
        "skill_dispersion_detected": tau2 > 0,
        "shrunk_spread_pp": {"p01": qv(.01), "p10": qv(.10), "p50": qv(.50),
                             "p90": qv(.90), "p99": qv(.99),
                             "max": round(sv[-1] * 100, 4)},
        "n_shrunk_above_0": sum(1 for v in sv if v > 0),
        "n_shrunk_above_1pp": sum(1 for v in sv if v > 0.01),
        "n_shrunk_above_5pp": sum(1 for v in sv if v > 0.05),
        "markets_needed_to_detect_5pp": round(n_needed) if n_needed else None,
        "n_wallets_clearing_that_bar": n_clear,
        "frac_wallets_clearing_bar": round(n_clear / len(ws), 5),
    }


results_gross = [shrink(m, 0) for m in (10, 20, 50, 100)]
results_net = [shrink(m, 1) for m in (10, 20, 50, 100)]

print("\n=== PHASE 4b: SKILL VS LUCK (gross excess over price-bucket benchmark) ===")
for r in results_gross:
    if "verdict" in r:
        print(f"  min={r['min_markets']:<4} {r['verdict']} (n={r['n_wallets']})")
        continue
    print(f"  min={r['min_markets']:<4} n={r['n_wallets']:>6}  "
          f"sigma={r['sigma_per_market']:.3f}  "
          f"tau={r['tau_pp']:>6.3f}pp  "
          f"skill_detected={str(r['skill_dispersion_detected']):>5}  "
          f"raw max={r['raw_mean_spread_pp']['max']:>8.2f}pp -> "
          f"shrunk max={r['shrunk_spread_pp']['max']:>7.3f}pp")
    print(f"{'':>12}markets needed to detect +5pp: "
          f"{r['markets_needed_to_detect_5pp']:,}  |  wallets clearing it: "
          f"{r['n_wallets_clearing_that_bar']:,} "
          f"({r['frac_wallets_clearing_bar']:.4%})")

report = {
    "meta": {
        "n_position_rows": n,
        "n_wallet_market_obs": len(raw),
        "n_wallets": len(obs),
        "n_excluded_phase2": len(excluded),
        "metric": "excess edge over the pooled mean at the same entry-price "
                  "bucket; unit of observation is a MARKET",
        "target_edge_pp": TARGET_EDGE * 100,
        "power": "two-sided alpha 0.05, power 0.80",
    },
    "price_bucket_benchmark": {
        k: {"n": v[0], "mean_edge_pp": round(v[1] / v[0] * 100, 4)}
        for k, v in bench.items() if v[0]},
    "gross_excess": results_gross,
    "net_excess": results_net,
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
