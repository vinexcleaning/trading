r"""Exit study: rank inside the FEE-BEARING ERA only, and see who survives.

Every ranking so far drew period 1 from history that was 91% fee-free. A wallet
whose edge came from trading patterns that only pay when execution is costless
would look skilled there and be worthless now. So this repeats the exercise
entirely inside the fee era:

    period 1 = 2026-01-08 .. 2026-03-01     (fees live)
    period 2 = 2026-03-01 .. 2026-04-28     (fees live, untouched by selection)

and reports three things:

  1. does persistence survive inside the fee era at all;
  2. does the top decile CHANGE COMPOSITION versus the fee-free-history ranking
     -- if the same wallets come top under both, the fee-free history was not
     misleading; if they are disjoint, every earlier ranking was selecting on a
     regime that no longer exists;
  3. what the exit component looks like for fee-era-selected wallets, since the
     whole point of the exit study is whether exits are worth copying.

The window is short -- about eight weeks per period -- so the qualifying bar is
lowered to 20 markets and the resulting sample sizes are reported honestly
rather than presented as equivalent to the long-history runs.

Guards: market clustering, bootstrap p-values, BH-FDR over every test here.
"""
import json
import math
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = ROOT / "data" / "wallet_positions.jsonl"
SEL = ROOT / "data" / "exit_selection.json"
FLAGS = ROOT / "data" / "wallet_flags.json"
OUT = ROOT / "reports" / "exit_fee_era_ranking.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

FEE_START = 1767830400          # 2026-01-08, bisected in probe_03
INNER_CUT = 1772323200          # 2026-03-01
END = 1777374040                # 2026-04-28
MIN_MARKETS = 20
FEE_RATE = 0.10
SEED = 20260801
N_BOOT = 2000
MAX_BOOT_CLUSTERS = 20_000

BUCKETS = [(0.00, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.30),
           (0.30, 0.40), (0.40, 0.50), (0.50, 0.60), (0.60, 0.70),
           (0.70, 0.80), (0.80, 0.90), (0.90, 0.95), (0.95, 1.00)]


def bucket_of(p):
    for lo, hi in BUCKETS:
        if lo <= p < hi:
            return f"{lo:.2f}-{hi:.2f}"
    return "1.00"


def fee(p):
    return FEE_RATE * min(p, 1.0 - p)


excluded = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])
legacy = json.loads(SEL.read_text(encoding="utf-8"))
LEGACY_TOP = set(legacy["top_decile"])
LEGACY_ELIG = set(legacy["all_eligible"])

print("loading fee-era positions...", flush=True)
P1, P2 = [], []
n = 0
for line in POS.open(encoding="utf-8"):
    r = json.loads(line)
    n += 1
    if r["flags"] or r["edge"] is None or r["settle_state"] != "settled":
        continue
    if r["cost"] <= 0 or r["shares_in"] <= 0:
        continue
    t = r["first_ts"]
    if t < FEE_START or t >= END:
        continue
    so = r["shares_out"]
    rec = {"w": r["wallet"], "cid": r["cid"], "cost": r["cost"],
           "edge": r["edge"], "px": r["entry_px"],
           "realised": r["realised_per_share"],
           "outcome": 1.0 if r["is_winner"] else 0.0,
           "frac_sold": min(so / r["shares_in"], 1.0),
           "exit_px": (r["proceeds"] / so) if so > 1e-9 else None}
    (P1 if t < INNER_CUT else P2).append(rec)
    if n % 3_000_000 == 0:
        print(f"  {n:,}", flush=True)
print(f"  fee-era p1 {len(P1):,}  p2 {len(P2):,}")


def collapse(rs):
    """Cost-weighted collapse to (wallet, market).

    `exit_px` is weighted by the SOLD notional, not total cost, and is None
    where nothing was sold -- a position with no exit has no exit price, and
    substituting one would invent a trade that never happened.
    """
    wm = {}
    for r in rs:
        a = wm.setdefault((r["w"], r["cid"]),
                          {"c": 0.0, "e": 0.0, "px": 0.0, "re": 0.0,
                           "ou": 0.0, "fs": 0.0, "xw": 0.0, "xn": 0.0})
        c = r["cost"]
        a["c"] += c
        a["e"] += r["edge"] * c
        a["px"] += r["px"] * c
        a["re"] += r["realised"] * c
        a["ou"] += r["outcome"] * c
        a["fs"] += r["frac_sold"] * c
        if r["exit_px"] is not None and r["frac_sold"] > 0:
            wgt = c * r["frac_sold"]
            a["xw"] += r["exit_px"] * wgt
            a["xn"] += wgt
    return [{"w": k[0], "cid": k[1], "cost": a["c"], "edge": a["e"] / a["c"],
             "px": a["px"] / a["c"], "realised": a["re"] / a["c"],
             "outcome": a["ou"] / a["c"], "frac_sold": a["fs"] / a["c"],
             "exit_px": (a["xw"] / a["xn"]) if a["xn"] > 0 else None}
            for k, a in wm.items()]


w1, w2 = collapse(P1), collapse(P2)


def excess_of(rs):
    b = defaultdict(lambda: [0, 0.0])
    for r in rs:
        e = b[bucket_of(r["px"])]
        e[0] += 1
        e[1] += r["edge"]
    mu = {k: v[1] / v[0] for k, v in b.items() if v[0]}
    for r in rs:
        r["ex"] = r["edge"] - mu.get(bucket_of(r["px"]), 0.0)
    return rs


w1, w2 = excess_of(w1), excess_of(w2)

by_w1, by_w2 = defaultdict(list), defaultdict(list)
for r in w1:
    by_w1[r["w"]].append(r)
for r in w2:
    by_w2[r["w"]].append(r)

elig = {w: sum(x["ex"] for x in v) / len(v) for w, v in by_w1.items()
        if len(v) >= MIN_MARKETS and w not in excluded}
order = sorted(elig, key=lambda w: -elig[w])
k = max(len(order) // 10, 1)
FEE_TOP = set(order[:k])
print(f"\n  {len(elig)} wallets qualify in fee-era p1 (>= {MIN_MARKETS} markets)")
print(f"  fee-era top decile: {len(FEE_TOP)} wallets, "
      f"p1 excess {sum(elig[w] for w in FEE_TOP)/len(FEE_TOP)*100:.3f}pp")


def boot(by_mkt, n_boot=N_BOOT, seed=SEED):
    keys = [kk for kk, v in by_mkt.items() if v]
    if len(keys) < 5:
        return None
    rng = random.Random(seed)
    if len(keys) > MAX_BOOT_CLUSTERS:
        keys = rng.sample(keys, MAX_BOOT_CLUSTERS)
    pre = [(len(by_mkt[kk]), sum(by_mkt[kk])) for kk in keys]
    tn = sum(a for a, _ in pre)
    ts = sum(b for _, b in pre)
    K, draws = len(pre), []
    for _ in range(n_boot):
        c = s = 0.0
        for _ in range(K):
            a, b = pre[rng.randrange(K)]
            c += a
            s += b
        if c:
            draws.append(s / c * 100)
    draws.sort()
    neg = sum(1 for d in draws if d <= 0) / len(draws)
    pos = sum(1 for d in draws if d >= 0) / len(draws)
    return {"mean_pp": round(ts / tn * 100, 4),
            "ci95": [round(draws[int(len(draws) * .025)], 4),
                     round(draws[int(len(draws) * .975)], 4)],
            "p": round(max(min(2 * min(neg, pos), 1.0), 1.0 / len(draws)), 6),
            "n_obs": tn, "n_markets": len(keys)}


def bm(rs, fn):
    d = defaultdict(list)
    for r in rs:
        v = fn(r)
        if v is not None:
            d[r["cid"]].append(v)
    return d


def spearman(xs, ys):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            a = (i + j) / 2.0 + 1
            for t in range(i, j + 1):
                rk[o[t]] = a
            i = j + 1
        return rk
    rx, ry = rank(xs), rank(ys)
    nn = len(xs)
    mx, my = sum(rx) / nn, sum(ry) / nn
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (dx * dy) if dx and dy else 0.0


# ---- persistence inside the fee era
both = [w for w in elig if len(by_w2.get(w, [])) >= MIN_MARKETS]
tests = []
persist = {"n_wallets_both_periods": len(both)}
if len(both) >= 20:
    a = [elig[w] for w in both]
    b = [sum(x["ex"] for x in by_w2[w]) / len(by_w2[w]) for w in both]
    o = sorted(range(len(both)), key=lambda i: -a[i])
    kk = max(len(both) // 10, 1)
    top_p2 = [b[o[i]] for i in range(kk)]
    bot_p2 = [b[o[-(i + 1)]] for i in range(kk)]
    topw = {both[o[i]] for i in range(kk)}
    tp = boot(bm([r for r in w2 if r["w"] in topw], lambda r: r["ex"]))
    persist.update({
        "spearman": round(spearman(a, b), 4),
        "top_decile_n": kk,
        "top_decile_p1_excess_pp": round(sum(a[o[i]] for i in range(kk)) / kk * 100, 4),
        "top_decile_p2_excess_pp": round(sum(top_p2) / kk * 100, 4),
        "top_decile_p2_boot": tp,
        "bottom_decile_p2_excess_pp": round(sum(bot_p2) / kk * 100, 4),
        "all_qualifying_p2_excess_pp": round(sum(b) / len(b) * 100, 4),
    })
    if tp:
        tests.append(("fee_era_top_decile_p2_excess", tp))
    print(f"\n  persistence inside fee era: n={len(both)}  "
          f"rho={persist['spearman']}  "
          f"top P1 {persist['top_decile_p1_excess_pp']:.3f} -> "
          f"P2 {persist['top_decile_p2_excess_pp']:.3f}pp  "
          f"bottom P2 {persist['bottom_decile_p2_excess_pp']:.3f}pp")
else:
    persist["verdict"] = "too few wallets in both fee-era sub-periods"
    print(f"\n  persistence inside fee era: only {len(both)} wallets qualify")

# ---- composition change vs the fee-free-history ranking
inter = FEE_TOP & LEGACY_TOP
comp = {
    "fee_era_top_decile_n": len(FEE_TOP),
    "legacy_top_decile_n": len(LEGACY_TOP),
    "overlap_n": len(inter),
    "overlap_frac_of_fee_era_top": round(len(inter) / max(len(FEE_TOP), 1), 4),
    "jaccard": round(len(inter) / max(len(FEE_TOP | LEGACY_TOP), 1), 4),
    "fee_era_top_that_were_legacy_eligible": len(FEE_TOP & LEGACY_ELIG),
    "fee_era_top_not_even_eligible_before": len(FEE_TOP - LEGACY_ELIG),
}
print(f"\n  top-decile composition: fee-era {len(FEE_TOP)} vs legacy "
      f"{len(LEGACY_TOP)}; overlap {len(inter)} "
      f"(Jaccard {comp['jaccard']:.3f})")
print(f"  of the fee-era top decile, {comp['fee_era_top_not_even_eligible_before']} "
      f"were not even eligible under the legacy ranking")

# ---- exit component for fee-era-selected wallets
print("\n  exit component, fee-era selection:")
exits = {}
for gname, mem in (("fee_era_top_decile", FEE_TOP),
                   ("fee_era_all_eligible", set(order)),
                   ("fee_era_everyone", None)):
    rs = [r for r in w2 if mem is None or r["w"] in mem]
    if not rs:
        continue
    ec = boot(bm(rs, lambda r: r["realised"] - r["outcome"]))
    dl = boot(bm(rs, lambda r: (r["realised"] - r["outcome"])
                 - (fee(r["exit_px"]) if r["exit_px"] else 0.0) * r["frac_sold"]
                 - 0.01 * r["frac_sold"]))
    if ec:
        exits[gname] = {"exit_component_pp": ec, "exit_copy_delta_1pp_spread": dl,
                        "n_positions": len(rs)}
        tests.append((f"fee_era_exit_component[{gname}]", ec))
        if dl:
            tests.append((f"fee_era_exit_delta[{gname}]", dl))
        print(f"    {gname:>22}  n={len(rs):>7,}  exit {ec['mean_pp']:>7.3f}pp "
              f"CI{ec['ci95']}  delta {dl['mean_pp'] if dl else 'n/a'}")

# ---- BH-FDR
ps = sorted((t[1]["p"], t[0]) for t in tests)
m = len(ps)
crit = None
for i, (p, lab) in enumerate(ps, 1):
    if p <= i / m * 0.05:
        crit = i
fdr = {lab: {"p": p, "bh_threshold": round(i / m * 0.05, 6),
             "significant_at_fdr_5pct": bool(crit and i <= crit)}
       for i, (p, lab) in enumerate(ps, 1)}

report = {
    "meta": {
        "fee_era": [time.strftime("%Y-%m-%d", time.gmtime(FEE_START)),
                    time.strftime("%Y-%m-%d", time.gmtime(END))],
        "inner_cut": time.strftime("%Y-%m-%d", time.gmtime(INNER_CUT)),
        "min_markets": MIN_MARKETS,
        "n_p1_positions": len(P1), "n_p2_positions": len(P2),
        "caveat": "about eight weeks per sub-period; sample sizes are much "
                  "smaller than the long-history runs and are not equivalent",
    },
    "n_eligible_fee_era": len(elig),
    "persistence_within_fee_era": persist,
    "top_decile_composition_change": comp,
    "exit_component_fee_era": exits,
    "bh_fdr": {"n_tests": m, "n_significant": crit or 0, "detail": fdr},
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\n  BH-FDR: {crit or 0} of {m} tests significant at 5%")
print(f"\nwrote {OUT}")
