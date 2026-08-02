"""Phase 4c, the version that decides the verdict: decay for SELECTED wallets.

analyse_40 measured decay over every buy in the market panel and found the copy
return negative at every delay (-1.4 to -2.4pp). That is the unconditional
population, and it is the right characterisation of the market -- but it is not
the question. Phase 4a found that a period-1 top decile keeps ~+3.5pp of excess
into period 2. The question is whether THAT edge survives being copied.

Design, and why it is not circular:
  - wallets are selected using PERIOD-1 data only (excess over the entry-price
    bucket benchmark, minimum market count, market makers already removed);
  - their signals are then evaluated in PERIOD 2, which selection never touched;
  - the copy price at each delay is the next trade at or after signal + d in the
    same token, taken from the market panel, which holds every fill in each
    sampled market.

The honest limits carry over from analyse_40 and are restated in the output:
p_d is a TRADE price rather than an ask, so a real copier pays more; Polygon
block time is ~2s so the +1s row is really "next block or later"; and where no
next fill exists the observation is counted missing rather than carried forward.
A same-block trade-price dispersion of ~1.0pp median (analyse_40) is applied as
an explicit spread haircut, and is itself a lower bound on the quoted spread.
"""
import json
import math
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = ROOT / "data" / "wallet_positions.jsonl"
FILLS = ROOT / "data" / "fills.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
OUT = ROOT / "reports" / "phase4c_decay_selected.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

FEE_RATE = 0.10
DELAYS = [0, 1, 10, 60, 300, 1800]
MAX_LOOKAHEAD = 6 * 3600
CUT = 1751328000                 # 2025-07-01, the cut with the strongest 4a result
MIN_MARKETS_P1 = 50
SEED = 20260801
N_BOOT = 2000
SPREAD_HAIRCUT_PP = 1.0          # median same-block trade dispersion, analyse_40

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

# --------------------------------------- 1. select wallets on PERIOD 1 only
print("selecting wallets on period-1 data only...", flush=True)
wm = {}
for line in POS.open(encoding="utf-8"):
    r = json.loads(line)
    if r["flags"] or r["edge"] is None or r["settle_state"] != "settled":
        continue
    if r["first_ts"] >= CUT:           # period 1 ONLY
        continue
    c = r["cost"]
    if c <= 0:
        continue
    k = (r["wallet"], r["cid"])
    a = wm.get(k)
    if a is None:
        a = wm[k] = {"c": 0.0, "e": 0.0, "px": 0.0}
    a["c"] += c
    a["e"] += r["edge"] * c
    a["px"] += r["entry_px"] * c

rows = [(w, a["e"] / a["c"], a["px"] / a["c"]) for (w, _), a in wm.items()]
del wm
bench = defaultdict(lambda: [0, 0.0])
for _, e, px in rows:
    b = bench[bucket_of(px)]
    b[0] += 1
    b[1] += e
mu_b = {k: v[1] / v[0] for k, v in bench.items() if v[0]}

per_w = defaultdict(list)
for w, e, px in rows:
    per_w[w].append(e - mu_b.get(bucket_of(px), 0.0))

elig = {w: sum(v) / len(v) for w, v in per_w.items()
        if len(v) >= MIN_MARKETS_P1 and w not in excluded}
if not elig:
    raise SystemExit("no wallets qualify")
order = sorted(elig, key=lambda w: -elig[w])
k = max(len(order) // 10, 1)
TOP = set(order[:k])
BOTTOM = set(order[-k:])
ALL_ELIG = set(order)
print(f"  {len(elig):,} eligible wallets (>= {MIN_MARKETS_P1} p1 markets, non-MM)")
print(f"  top decile = {len(TOP)} wallets, p1 mean excess "
      f"{sum(elig[w] for w in TOP)/len(TOP)*100:.3f}pp")

# ------------------------------------- 2. decay on PERIOD-2 signals only
print("\nloading market panel...", flush=True)
by_token = defaultdict(list)
n = 0
for line in FILLS.open(encoding="utf-8"):
    f = json.loads(line)
    n += 1
    if f.get("is_winner") is None:
        continue
    by_token[f["token"]].append(
        (f["ts"], f["price"], f["is_winner"], f["cid"], f["maker_side"], f["maker"]))
for kk in by_token:
    by_token[kk].sort()
print(f"  {n:,} fills over {len(by_token):,} tokens")

GROUPS = {"top_decile": TOP, "bottom_decile": BOTTOM,
          "all_eligible": ALL_ELIG, "everyone": None}
res = {g: {d: defaultdict(list) for d in DELAYS} for g in GROUPS}
counts = Counter()

print("measuring decay on period-2 signals...", flush=True)
t0 = time.time()
for tok, evs in by_token.items():
    L = len(evs)
    for i, (t, p0, win, cid, side, maker) in enumerate(evs):
        if side != "BUY" or t < CUT:
            continue
        groups = [g for g, s in GROUPS.items() if s is None or maker in s]
        if not groups:
            continue
        for g in groups:
            counts[f"signals_{g}"] += 1
        outcome = 1.0 if win else 0.0
        j = i
        for d in DELAYS:
            while j < L and evs[j][0] < t + d:
                j += 1
            if j >= L or evs[j][0] - t > MAX_LOOKAHEAD:
                continue
            p_d = evs[j][1]
            r = outcome - p_d - fee(p_d)
            for g in groups:
                res[g][d][cid].append(r)
print(f"  done in {time.time()-t0:.0f}s   {dict(counts)}")


def boot_ci(by_mkt, n_boot=N_BOOT, seed=SEED):
    keys = [kk for kk, v in by_mkt.items() if v]
    if len(keys) < 5:
        return None
    pre = {kk: (len(by_mkt[kk]), sum(by_mkt[kk])) for kk in keys}
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


report = {
    "meta": {
        "cut_iso": time.strftime("%Y-%m-%d", time.gmtime(CUT)),
        "selection": f"period-1 only, >= {MIN_MARKETS_P1} markets, non-MM, "
                     f"ranked on excess over entry-price bucket",
        "evaluation": "period-2 signals only; selection never saw them",
        "n_eligible_wallets": len(elig),
        "n_top_decile": len(TOP),
        "spread_haircut_pp": SPREAD_HAIRCUT_PP,
        "limits": [
            "p_d is a TRADE price, not an ask -- a real copier pays more, so "
            "every copy return here is an upper bound before the haircut",
            "Polygon block time ~2s: the +1s row is 'next block or later'",
            "missing next-fill counted missing, never carried forward",
        ],
    },
    "curves": {},
}

print("\n=== COPY RETURN BY DELAY, net of fee (pp) ===")
print(f"{'group':>14} {'delay':>7} {'n':>10} {'n_mkt':>7} {'copy':>9} "
      f"{'CI95':>20} {'after spread':>13}")
for g in GROUPS:
    report["curves"][g] = {}
    for d in DELAYS:
        by_mkt = res[g][d]
        vals = [v for vs in by_mkt.values() for v in vs]
        if not vals:
            continue
        mu = sum(vals) / len(vals) * 100
        ci = boot_ci(by_mkt)
        row = {
            "n_obs": len(vals), "n_markets": len(by_mkt),
            "copy_return_net_pp": round(mu, 4),
            "ci95_pp": ci,
            "after_spread_haircut_pp": round(mu - SPREAD_HAIRCUT_PP, 4),
        }
        report["curves"][g][str(d)] = row
        print(f"{g:>14} {d:>6}s {len(vals):>10,} {len(by_mkt):>7,} "
              f"{mu:>9.3f} {str(ci):>20} {mu - SPREAD_HAIRCUT_PP:>13.3f}")

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
