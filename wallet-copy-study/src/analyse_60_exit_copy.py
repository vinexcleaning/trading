r"""Exit study, stage 1: is the 2.38pp gap actually exit skill? Decompose it.

The gap was defined as `wallet_edge - copier_buy_and_hold`. Expanding it:

    gap = (realised_per_share - entry_px) - (outcome - entry_px - fee(entry_px))
        = (realised_per_share - outcome)  +  fee(entry_px)
          \_______ exit component ______/    \___ accounting artifact ___/

The second term exists only because a GROSS wallet edge was compared against a
NET copier return. It is the fee the copier pays and the wallet was never
charged -- and for the 78% of top-decile positions that are simply held to
settlement, `realised_per_share == outcome`, so the ENTIRE gap on those
positions is that fee term. At a mean entry price near 0.5 the fee alone is
~5pp, which is larger than the whole 2.38pp gap.

So the headline "72% of the edge lives in exits" is checked here before anything
else is built on it.

Stage 1 also runs the real question at zero delay, which is an upper bound on
what exit-copying can ever be worth:

    full replication = realised_per_share - entry_px
                       - fee(entry_px) - fee(exit_px) * frac_sold
                       - spread_entry  - spread_exit  * frac_sold
    buy and hold     = outcome - entry_px - fee(entry_px) - spread_entry

    value of copying exits = (realised - outcome)
                             - fee(exit_px) * frac_sold
                             - spread_exit * frac_sold

Guards: clustered by market throughout, never pooled across markets; bootstrap
p-values; Benjamini-Hochberg FDR applied across every test in this file.
"""
import json
import math
import os
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = ROOT / "data" / "wallet_positions.jsonl"
SEL = ROOT / "data" / "exit_selection.json"
OUT = ROOT / "reports" / "exit_stage1_decomposition.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

FEE_RATE = 0.10
CUT = int(os.environ.get("EXIT_CUT", "1751328000"))
SEED = 20260801
N_BOOT = 2000
MAX_BOOT_CLUSTERS = 20_000
SPREADS_PP = {"none": 0.0, "half_0.5pp_per_leg": 0.5, "full_1.0pp_per_leg": 1.0}


def fee(p):
    return FEE_RATE * min(p, 1.0 - p)


sel = json.loads(SEL.read_text(encoding="utf-8"))
TOP = set(sel["top_decile"])
BOTTOM = set(sel["bottom_decile"])
ALL_ELIG = set(sel["all_eligible"])

print("loading period-2 positions...", flush=True)
rows = []
n = 0
for line in POS.open(encoding="utf-8"):
    r = json.loads(line)
    n += 1
    if r["flags"] or r["edge"] is None or r["settle_state"] != "settled":
        continue
    if r["cost"] <= 0 or r["shares_in"] <= 0 or r["first_ts"] < CUT:
        continue
    si, so = r["shares_in"], r["shares_out"]
    entry_px = r["entry_px"]
    exit_px = (r["proceeds"] / so) if so > 1e-9 else None
    outcome = 1.0 if r["is_winner"] else 0.0
    rows.append({
        "w": r["wallet"], "cid": r["cid"],
        "si": si, "frac_sold": min(so / si, 1.0) if si > 0 else 0.0,
        "entry_px": entry_px, "exit_px": exit_px,
        "realised": r["realised_per_share"], "outcome": outcome,
        "edge": r["edge"], "cost": r["cost"],
    })
    if n % 3_000_000 == 0:
        print(f"  {n:,}", flush=True)
print(f"  {n:,} rows -> {len(rows):,} period-2 positions")


# --------------------------------------------------------------- bootstrap
def boot(by_mkt, n_boot=N_BOOT, seed=SEED):
    """Market-clustered bootstrap -> (mean_pp, ci95, two-sided p)."""
    keys = [k for k, v in by_mkt.items() if v]
    if len(keys) < 5:
        return None
    rng = random.Random(seed)
    sub = False
    if len(keys) > MAX_BOOT_CLUSTERS:
        keys = rng.sample(keys, MAX_BOOT_CLUSTERS)
        sub = True
    pre = [(len(by_mkt[k]), sum(by_mkt[k])) for k in keys]
    tot_n = sum(a for a, _ in pre)
    tot_s = sum(b for _, b in pre)
    point = tot_s / tot_n * 100
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
    lo = draws[int(len(draws) * .025)]
    hi = draws[int(len(draws) * .975)]
    neg = sum(1 for d in draws if d <= 0) / len(draws)
    pos = sum(1 for d in draws if d >= 0) / len(draws)
    p = max(min(2 * min(neg, pos), 1.0), 1.0 / len(draws))
    return {"mean_pp": round(point, 4), "ci95": [round(lo, 4), round(hi, 4)],
            "p": round(p, 6), "n_obs": tot_n, "n_markets": len(keys),
            "subsampled_clusters": sub}


def by_market(rs, fn):
    d = defaultdict(list)
    for r in rs:
        v = fn(r)
        if v is not None:
            d[r["cid"]].append(v)
    return d


GROUPS = {"top_decile": TOP, "bottom_decile": BOTTOM,
          "all_eligible": ALL_ELIG, "everyone": None}

tests = []          # (label, result) for FDR
report = {
    "meta": {
        "cut_iso": time.strftime("%Y-%m-%d", time.gmtime(CUT)),
        "n_period2_positions": len(rows),
        "fee_formula": "0.10*min(p,1-p) per share (probe_02, 100% of 5362 fills)",
        "clustering": "market-level bootstrap; never pooled across markets",
        "n_bootstrap": N_BOOT,
    },
    "gap_decomposition": {},
    "exit_copy_zero_delay": {},
}

print("\n=== GAP DECOMPOSITION: is it exit skill, or the fee I charged one side? ===")
print(f"{'group':>14} {'n_pos':>9} {'gap':>9} {'exit comp':>11} {'fee comp':>10} "
      f"{'frac sold':>10} {'exit share':>11}")
for g, mem in GROUPS.items():
    rs = [r for r in rows if mem is None or r["w"] in mem]
    if not rs:
        continue
    gap = boot(by_market(rs, lambda r: (r["realised"] - r["outcome"])
                         + fee(r["entry_px"])))
    exitc = boot(by_market(rs, lambda r: r["realised"] - r["outcome"]))
    feec = boot(by_market(rs, lambda r: fee(r["entry_px"])))
    fs = sum(r["frac_sold"] for r in rs) / len(rs)
    if not (gap and exitc and feec):
        continue
    share = (exitc["mean_pp"] / gap["mean_pp"]) if gap["mean_pp"] else None
    report["gap_decomposition"][g] = {
        "n_positions": len(rs),
        "gap_pp": gap, "exit_component_pp": exitc, "fee_component_pp": feec,
        "mean_frac_sold": round(fs, 4),
        "exit_share_of_gap": round(share, 4) if share is not None else None,
    }
    tests += [(f"gap[{g}]", gap), (f"exit_component[{g}]", exitc)]
    print(f"{g:>14} {len(rs):>9,} {gap['mean_pp']:>9.3f} "
          f"{exitc['mean_pp']:>11.3f} {feec['mean_pp']:>10.3f} "
          f"{fs:>10.3f} {(f'{share:.1%}' if share is not None else 'n/a'):>11}")

print("\n=== EXIT COPYING AT ZERO DELAY (upper bound on its value) ===")
for sname, spp in SPREADS_PP.items():
    sp = spp / 100.0
    print(f"\n-- spread assumption: {sname}")
    print(f"{'group':>14} {'buy&hold':>10} {'full repl':>11} {'delta':>9} "
          f"{'delta CI95':>20} {'p':>9}")
    report["exit_copy_zero_delay"][sname] = {}
    for g, mem in GROUPS.items():
        rs = [r for r in rows if mem is None or r["w"] in mem]
        if not rs:
            continue

        def bh(r):
            return r["outcome"] - r["entry_px"] - fee(r["entry_px"]) - sp

        def full(r):
            f = r["frac_sold"]
            ex_fee = fee(r["exit_px"]) if r["exit_px"] is not None else 0.0
            return (r["realised"] - r["entry_px"] - fee(r["entry_px"]) - sp
                    - (ex_fee + sp) * f)

        b_bh = boot(by_market(rs, bh))
        b_fu = boot(by_market(rs, full))
        b_dl = boot(by_market(rs, lambda r: full(r) - bh(r)))
        if not (b_bh and b_fu and b_dl):
            continue
        report["exit_copy_zero_delay"][sname][g] = {
            "buy_and_hold": b_bh, "full_replication": b_fu, "delta": b_dl}
        tests.append((f"exit_delta[{g}][{sname}]", b_dl))
        print(f"{g:>14} {b_bh['mean_pp']:>10.3f} {b_fu['mean_pp']:>11.3f} "
              f"{b_dl['mean_pp']:>9.3f} {str(b_dl['ci95']):>20} "
              f"{b_dl['p']:>9.5f}")

# ------------------------------------------------------------- BH-FDR
ps = sorted((t[1]["p"], t[0]) for t in tests)
m = len(ps)
alpha = 0.05
crit = None
for i, (p, lab) in enumerate(ps, 1):
    if p <= i / m * alpha:
        crit = i
fdr = {}
for i, (p, lab) in enumerate(ps, 1):
    fdr[lab] = {"p": p, "bh_threshold": round(i / m * alpha, 6),
                "significant_at_fdr_5pct": bool(crit and i <= crit)}
report["bh_fdr"] = {
    "n_tests": m, "alpha": alpha,
    "n_significant": crit or 0,
    "detail": fdr,
}
print(f"\n=== BH-FDR across {m} tests at alpha=0.05: "
      f"{crit or 0} significant ===")
for p, lab in ps[:12]:
    print(f"  {'PASS' if fdr[lab]['significant_at_fdr_5pct'] else 'fail'}  "
          f"p={p:<10.6f} {lab}")

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
