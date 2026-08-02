r"""Exit study: anatomy of the exit component, without needing the book.

The exit component is exactly

    exit_component = frac_sold * (exit_price - outcome)

so it splits cleanly by what the position eventually did:

  - on eventual WINNERS (outcome = 1), selling early means `exit_price - 1 < 0`
    for any exit below par -- this term is how much they GIVE UP by taking
    profit before settlement;
  - on eventual LOSERS (outcome = 0), selling means `exit_price - 0 > 0` for any
    positive price -- this term is how much they SAVE by cutting losses.

The sum of the two is the whole effect, and their relative size says what kind
of exit behaviour this is. A wallet that is good at exits should show a large
positive loser term (cuts losses before they go to zero) that outweighs the
negative winner term. If instead the winner term dominates, the wallet is
simply taking profit too early and the "exit skill" story is inverted.

Also bucketed by entry price and by holding period, because "they hold shorter
and eat less tail risk" predicts a specific pattern -- the benefit should
concentrate in short holds and in mid-priced positions where there is most left
to lose.

Guards: market clustering, bootstrap p-values, BH-FDR, never pooled across
markets.
"""
import json
import os
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = ROOT / "data" / "wallet_positions.jsonl"
SEL = ROOT / "data" / "exit_selection.json"
OUT = ROOT / "reports" / "exit_anatomy.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

FEE_RATE = 0.10
CUT = int(os.environ.get("EXIT_CUT", "1751328000"))
SEED = 20260801
N_BOOT = 2000
MAX_BOOT_CLUSTERS = 20_000

PX_BUCKETS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
HOLD_BUCKETS = [(0, 60), (60, 600), (600, 3600), (3600, 86400),
                (86400, 604800), (604800, 10 ** 12)]


def px_bucket(p):
    for lo, hi in PX_BUCKETS:
        if lo <= p < hi:
            return f"{lo:.1f}-{hi:.1f}"
    return "1.0"


def hold_bucket(s):
    for lo, hi in HOLD_BUCKETS:
        if lo <= s < hi:
            return f"{lo}-{hi if hi < 10**12 else 'inf'}"
    return "?"


def fee(p):
    return FEE_RATE * min(p, 1.0 - p)


sel = json.loads(SEL.read_text(encoding="utf-8"))
TOP = set(sel["top_decile"])
ALL_ELIG = set(sel["all_eligible"])

print("loading period-2 positions with sells...", flush=True)
rows = []
n = 0
for line in POS.open(encoding="utf-8"):
    r = json.loads(line)
    n += 1
    if r["flags"] or r["edge"] is None or r["settle_state"] != "settled":
        continue
    if r["cost"] <= 0 or r["shares_in"] <= 0 or r["first_ts"] < CUT:
        continue
    so = r["shares_out"]
    if so <= 1e-9:
        continue
    rows.append({
        "w": r["wallet"], "cid": r["cid"],
        "outcome": 1.0 if r["is_winner"] else 0.0,
        "exit_px": r["proceeds"] / so,
        "entry_px": r["entry_px"],
        "frac_sold": min(so / r["shares_in"], 1.0),
        "hold": r["hold_seconds"],
    })
    if n % 3_000_000 == 0:
        print(f"  {n:,}", flush=True)
print(f"  {n:,} rows -> {len(rows):,} period-2 positions WITH sells")


def boot(by_mkt, n_boot=N_BOOT, seed=SEED):
    keys = [k for k, v in by_mkt.items() if v]
    if len(keys) < 5:
        return None
    rng = random.Random(seed)
    if len(keys) > MAX_BOOT_CLUSTERS:
        keys = rng.sample(keys, MAX_BOOT_CLUSTERS)
    pre = [(len(by_mkt[k]), sum(by_mkt[k])) for k in keys]
    tn = sum(a for a, _ in pre)
    ts_ = sum(b for _, b in pre)
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
    return {"mean_pp": round(ts_ / tn * 100, 4),
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


def contrib(r):
    return r["frac_sold"] * (r["exit_px"] - r["outcome"])


GROUPS = {"top_decile": TOP, "all_eligible": ALL_ELIG, "everyone": None}
tests = []
report = {"meta": {"cut_iso": time.strftime("%Y-%m-%d", time.gmtime(CUT)),
                   "n_positions_with_sells": len(rows),
                   "identity": "exit_component = frac_sold * (exit_price - outcome)",
                   "clustering": "market-level bootstrap, never pooled"},
          "by_outcome": {}, "by_entry_price": {}, "by_hold_period": {}}

print("\n=== EXIT COMPONENT SPLIT BY EVENTUAL OUTCOME ===")
print(f"{'group':>14} {'slice':>10} {'n':>9} {'contribution':>13} "
      f"{'CI95':>20} {'p':>9} {'mean exit px':>13}")
for g, mem in GROUPS.items():
    rs = [r for r in rows if mem is None or r["w"] in mem]
    if not rs:
        continue
    report["by_outcome"][g] = {}
    for lab, sub in (("winners", [r for r in rs if r["outcome"] == 1.0]),
                     ("losers", [r for r in rs if r["outcome"] == 0.0]),
                     ("all", rs)):
        if not sub:
            continue
        b = boot(bm(sub, contrib))
        if not b:
            continue
        mx = sum(r["exit_px"] for r in sub) / len(sub)
        report["by_outcome"][g][lab] = {
            "contribution_pp": b, "n_positions": len(sub),
            "share_of_positions": round(len(sub) / len(rs), 4),
            "mean_exit_price": round(mx, 4)}
        tests.append((f"exit_contrib[{g}][{lab}]", b))
        print(f"{g:>14} {lab:>10} {len(sub):>9,} {b['mean_pp']:>13.3f} "
              f"{str(b['ci95']):>20} {b['p']:>9.5f} {mx:>13.4f}")

print("\n=== BY ENTRY PRICE (top decile) ===")
rs = [r for r in rows if r["w"] in TOP]
for lo, hi in PX_BUCKETS:
    sub = [r for r in rs if lo <= r["entry_px"] < hi]
    if len(sub) < 50:
        continue
    b = boot(bm(sub, contrib))
    if not b:
        continue
    key = f"{lo:.1f}-{hi:.1f}"
    report["by_entry_price"][key] = {"contribution_pp": b, "n": len(sub)}
    tests.append((f"exit_contrib_px[{key}]", b))
    print(f"  {key:>10} n={len(sub):>7,} {b['mean_pp']:>9.3f}pp CI{b['ci95']}")

print("\n=== BY HOLDING PERIOD (top decile) ===")
for lo, hi in HOLD_BUCKETS:
    sub = [r for r in rs if lo <= r["hold"] < hi]
    if len(sub) < 50:
        continue
    b = boot(bm(sub, contrib))
    if not b:
        continue
    key = f"{lo}-{hi if hi < 10**12 else 'inf'}"
    report["by_hold_period"][key] = {"contribution_pp": b, "n": len(sub)}
    tests.append((f"exit_contrib_hold[{key}]", b))
    print(f"  {key:>16} n={len(sub):>7,} {b['mean_pp']:>9.3f}pp CI{b['ci95']}")

ps = sorted((t[1]["p"], t[0]) for t in tests)
m_ = len(ps)
crit = None
for i, (p, lab) in enumerate(ps, 1):
    if p <= i / m_ * 0.05:
        crit = i
report["bh_fdr"] = {
    "n_tests": m_, "n_significant": crit or 0,
    "detail": {lab: {"p": p, "bh_threshold": round(i / m_ * 0.05, 6),
                     "significant_at_fdr_5pct": bool(crit and i <= crit)}
               for i, (p, lab) in enumerate(ps, 1)}}
print(f"\n=== BH-FDR across {m_} tests: {crit or 0} significant at 5% ===")

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
