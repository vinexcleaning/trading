"""Phase 4d: adverse selection and capacity.

Runs on the MARKET panel, which holds every fill in each sampled market -- the
only place "the next trade after this one" is a meaningful quantity.

ADVERSE SELECTION. Two distinct questions, kept apart because conflating them
is easy and misleading:

  (a) Is the post-signal price move INFORMATIVE? Measured as the relationship
      between the price move after a buy and the eventual outcome. If price
      drifts toward the outcome, delay costs real edge rather than just spread.

  (b) Are COPYABLE fills a worse subset than all fills? A copier can only act
      when a next trade exists to trade against. If the subset where that is
      true has systematically worse outcomes than the full signal population,
      then the act of being able to copy is itself adversely selected -- you
      get filled precisely when someone is keen to sell to you.

CAPACITY. Price impact is measured as the signed price change from a fill to the
next fill in the same token, bucketed by the fill's notional. Expected P&L at
size is then edge minus impact minus fee. The impact estimate is a LOWER bound
on what a copier would suffer: it reflects the size that actually traded, and a
copier arriving after the signal adds their own demand on top -- which is the
reflexivity point, and it means capacity numbers here are optimistic.
"""
import json
import math
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILLS = ROOT / "data" / "fills.jsonl"
OUT = ROOT / "reports" / "phase4d_capacity.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

FEE_RATE = 0.10
DELAY = 60                      # seconds; the headline copy latency
SEED = 20260801
N_BOOT = 1000
SIZE_BUCKETS = [(0, 10), (10, 50), (50, 250), (250, 1000),
                (1000, 5000), (5000, 25000), (25000, float("inf"))]


def fee(p):
    return FEE_RATE * min(p, 1 - p)


def size_bucket(usd):
    for lo, hi in SIZE_BUCKETS:
        if lo <= usd < hi:
            return f"{lo}-{'inf' if hi == float('inf') else int(hi)}"
    return "other"


print("loading fills...", flush=True)
by_token = defaultdict(list)
n = 0
t0 = time.time()
for line in FILLS.open(encoding="utf-8"):
    f = json.loads(line)
    n += 1
    if f.get("is_winner") is None:
        continue
    by_token[f["token"]].append(
        (f["ts"], f["price"], f["is_winner"], f["cid"],
         f["maker_side"], f["shares"] * f["price"]))
    if n % 2_000_000 == 0:
        print(f"  {n:,}  {time.time()-t0:.0f}s", flush=True)
for k in by_token:
    by_token[k].sort()
print(f"read {n:,} fills over {len(by_token):,} tokens in {time.time()-t0:.0f}s")

# --------------------------------------------------- impact and selection
impact = defaultdict(lambda: {"n": 0, "signed": 0.0, "abs": 0.0})
copyable, uncopyable = defaultdict(list), defaultdict(list)
move_vs_outcome = []
stats = Counter()

for tok, evs in by_token.items():
    L = len(evs)
    for i, (t, p0, win, cid, side, notional) in enumerate(evs):
        if side != "BUY":
            continue
        stats["signals"] += 1
        outcome = 1.0 if win else 0.0

        # ---- price impact: this fill -> the immediately next fill
        if i + 1 < L:
            dp = evs[i + 1][1] - p0
            b = impact[size_bucket(notional)]
            b["n"] += 1
            b["signed"] += dp
            b["abs"] += abs(dp)

        # ---- copyability at DELAY
        j = i
        while j < L and evs[j][0] < t + DELAY:
            j += 1
        if j < L and evs[j][0] - t <= 6 * 3600:
            p_d = evs[j][1]
            stats["copyable"] += 1
            copyable[cid].append(outcome - p_d - fee(p_d))
            move_vs_outcome.append((p_d - p0, outcome - p0))
        else:
            stats["not_copyable"] += 1
            uncopyable[cid].append(outcome - p0 - fee(p0))

print(f"  {stats['signals']:,} signals, {stats['copyable']:,} copyable at +{DELAY}s")


def boot_ci(by_mkt, n_boot=N_BOOT, seed=SEED):
    keys = [k for k, v in by_mkt.items() if v]
    if len(keys) < 5:
        return None
    pre = {k: (len(by_mkt[k]), sum(by_mkt[k])) for k in keys}
    rng = random.Random(seed)
    K, out = len(keys), []
    for _ in range(n_boot):
        c = s = 0
        for _ in range(K):
            a, b = pre[keys[rng.randrange(K)]]
            c += a
            s += b
        if c:
            out.append(s / c * 100)
    out.sort()
    return [round(out[int(len(out) * .025)], 4), round(out[int(len(out) * .975)], 4)]


def flat(d):
    return [v for vs in d.values() for v in vs]


cop, unc = flat(copyable), flat(uncopyable)

# correlation between post-signal move and eventual outcome
if len(move_vs_outcome) > 100:
    xs = [a for a, _ in move_vs_outcome]
    ys = [b for _, b in move_vs_outcome]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    corr = num / (dx * dy) if dx and dy else None
    # slope: how much of the eventual move is realised in the first DELAY
    slope = num / (dx * dx) if dx else None
else:
    corr = slope = None

adverse = {
    "delay_s": DELAY,
    "n_signals": stats["signals"],
    "n_copyable": stats["copyable"],
    "n_not_copyable": stats["not_copyable"],
    "frac_copyable": round(stats["copyable"] / max(stats["signals"], 1), 4),
    "copyable_return_net_pp": round(sum(cop) / len(cop) * 100, 4) if cop else None,
    "copyable_ci95_pp": boot_ci(copyable),
    "uncopyable_signal_return_net_pp":
        round(sum(unc) / len(unc) * 100, 4) if unc else None,
    "uncopyable_ci95_pp": boot_ci(uncopyable),
    "corr_post_signal_move_with_outcome": round(corr, 5) if corr is not None else None,
    "info_share_of_move": round(slope, 5) if slope is not None else None,
    "reading":
        "A positive correlation means the price drifts toward the outcome after "
        "a buy, i.e. the signal carried information and delay costs real edge "
        "rather than only spread. A copyable return materially below the "
        "uncopyable-signal return means being able to copy is itself adversely "
        "selected.",
}

imp = {}
for b, v in impact.items():
    if v["n"]:
        imp[b] = {
            "n": v["n"],
            "mean_signed_move_pp": round(v["signed"] / v["n"] * 100, 5),
            "mean_abs_move_pp": round(v["abs"] / v["n"] * 100, 5),
        }

# ------------------------------------------------------- capacity table
cap = {}
base = adverse["copyable_return_net_pp"]
for b in sorted(imp, key=lambda k: SIZE_BUCKETS[
        [f"{lo}-{'inf' if hi==float('inf') else int(hi)}"
         for lo, hi in SIZE_BUCKETS].index(k)][0] if k in
        [f"{lo}-{'inf' if hi==float('inf') else int(hi)}"
         for lo, hi in SIZE_BUCKETS] else 0):
    if base is None:
        continue
    cap[b] = {
        "n_fills_observed": imp[b]["n"],
        "impact_pp": imp[b]["mean_signed_move_pp"],
        "net_of_impact_pp": round(base - imp[b]["mean_signed_move_pp"], 4),
    }

report = {
    "meta": {
        "n_fills": n, "n_tokens": len(by_token),
        "delay_s": DELAY, "fee_formula": "0.10*min(p,1-p) per share",
        "clustering": "market-level bootstrap",
        "limits": [
            "impact is measured on the size that ACTUALLY traded; a copier adds "
            "their own demand on top, so these capacity numbers are optimistic",
            "prices are trade prices, not asks, which further flatters the copier",
        ],
    },
    "counters": dict(stats),
    "adverse_selection": adverse,
    "price_impact_by_trade_size": imp,
    "capacity": cap,
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("\n=== ADVERSE SELECTION ===")
print(f"  copyable at +{DELAY}s : {adverse['frac_copyable']:.1%} of signals")
print(f"  copyable return      : {adverse['copyable_return_net_pp']}pp "
      f"CI{adverse['copyable_ci95_pp']}")
print(f"  uncopyable signal    : {adverse['uncopyable_signal_return_net_pp']}pp")
print(f"  corr(move, outcome)  : {adverse['corr_post_signal_move_with_outcome']}")
print("\n=== PRICE IMPACT BY TRADE SIZE ===")
for b, v in imp.items():
    print(f"  {b:>14} n={v['n']:>9,}  signed {v['mean_signed_move_pp']:>8.4f}pp  "
          f"abs {v['mean_abs_move_pp']:>8.4f}pp")
print(f"\nwrote {OUT}")
