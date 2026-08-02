"""Exit study, step 0: select wallets on period 1, dump the tokens to pull.

Two things happen here and nothing else, so that the expensive network pull can
start before any analysis is written.

1. Wallets are ranked on PERIOD-1 data only, exactly as in analyse_46 -- excess
   over the entry-price-bucket benchmark, minimum market count, Phase-2
   exclusions already applied. Period 2 is never consulted.

2. The tokens those wallets traded in period 2 are dumped for a targeted fill
   pull. Complete books are needed because "the price 60 seconds after the
   wallet sold" is only meaningful if every trade in that token is visible, and
   the existing 2,529-market panel overlaps the selected wallets in only ~140
   markets -- the thin slice that produced the retracted -5.9pp reading.

Token sampling is random with a fixed seed and carries NO performance
criterion. Positions WITH sells are the ones that can answer the exit question,
so they are sampled; positions without sells are unaffected by exit policy and
their buy-and-hold value is already known from the wallet panel.
"""
import json
import os
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = ROOT / "data" / "wallet_positions.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
OUT_TOK = ROOT / "data" / "exit_target_tokens.json"
OUT_SEL = ROOT / "data" / "exit_selection.json"

CUT = int(os.environ.get("EXIT_CUT", "1751328000"))       # 2025-07-01
MIN_MARKETS_P1 = int(os.environ.get("EXIT_MIN_MKTS", "50"))
N_TOKENS = int(os.environ.get("EXIT_N_TOKENS", "3200"))
SEED = 20260801

BUCKETS = [(0.00, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.30),
           (0.30, 0.40), (0.40, 0.50), (0.50, 0.60), (0.60, 0.70),
           (0.70, 0.80), (0.80, 0.90), (0.90, 0.95), (0.95, 1.00)]


def bucket_of(p):
    for lo, hi in BUCKETS:
        if lo <= p < hi:
            return f"{lo:.2f}-{hi:.2f}"
    return "1.00"


excluded = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])

print("loading positions...", flush=True)
p1_rows = []
p2_rows = []
n = 0
for line in POS.open(encoding="utf-8"):
    r = json.loads(line)
    n += 1
    if r["flags"] or r["edge"] is None or r["settle_state"] != "settled":
        continue
    if r["cost"] <= 0 or r["shares_in"] <= 0:
        continue
    if r["first_ts"] < CUT:
        p1_rows.append((r["wallet"], r["cid"], r["cost"], r["edge"], r["entry_px"]))
    else:
        p2_rows.append(r)
print(f"  {n:,} rows -> p1 {len(p1_rows):,}  p2 {len(p2_rows):,}")

# ---- period-1 wallet ranking (selection never sees period 2)
wm = {}
for w, cid, c, e, px in p1_rows:
    a = wm.setdefault((w, cid), {"c": 0.0, "e": 0.0, "px": 0.0})
    a["c"] += c
    a["e"] += e * c
    a["px"] += px * c
bench = defaultdict(lambda: [0, 0.0])
for (w, cid), a in wm.items():
    b = bench[bucket_of(a["px"] / a["c"])]
    b[0] += 1
    b[1] += a["e"] / a["c"]
mu = {k: v[1] / v[0] for k, v in bench.items() if v[0]}
per_w = defaultdict(list)
for (w, cid), a in wm.items():
    per_w[w].append(a["e"] / a["c"] - mu.get(bucket_of(a["px"] / a["c"]), 0.0))

elig = {w: sum(v) / len(v) for w, v in per_w.items()
        if len(v) >= MIN_MARKETS_P1 and w not in excluded}
order = sorted(elig, key=lambda w: -elig[w])
k = max(len(order) // 10, 1)
TOP = order[:k]
BOTTOM = order[-k:]
print(f"  {len(elig)} eligible; top decile {len(TOP)} wallets, "
      f"p1 excess {sum(elig[w] for w in TOP)/len(TOP)*100:.3f}pp")

topset = set(TOP)

# ---- tokens to pull: period-2 positions of top-decile wallets that SOLD
cand = defaultdict(set)          # token -> wallets
stats = Counter()
for r in p2_rows:
    if r["wallet"] not in topset:
        continue
    stats["top_p2_positions"] += 1
    if r["n_sells"] > 0:
        stats["with_sells"] += 1
        cand[r["token"]].add(r["wallet"])
    else:
        stats["no_sells"] += 1

toks = sorted(cand)
rng = random.Random(SEED)
sample = toks if len(toks) <= N_TOKENS else rng.sample(toks, N_TOKENS)
print(f"  top-decile p2 positions {stats['top_p2_positions']:,}; "
      f"with sells {stats['with_sells']:,} over {len(toks):,} distinct tokens; "
      f"sampling {len(sample):,}")

OUT_TOK.write_text(json.dumps({
    "cut": CUT, "min_markets_p1": MIN_MARKETS_P1, "seed": SEED,
    "n_distinct_tokens_available": len(toks),
    "n_sampled": len(sample),
    "sampling": "uniform random over tokens where a top-decile wallet sold in "
                "period 2; fixed seed; no performance criterion",
    "counters": dict(stats),
    "tokens": sample,
}, indent=2), encoding="utf-8")

OUT_SEL.write_text(json.dumps({
    "cut": CUT, "min_markets_p1": MIN_MARKETS_P1,
    "n_eligible": len(elig),
    "top_decile": TOP, "bottom_decile": BOTTOM,
    "all_eligible": order,
    "p1_excess": {w: round(elig[w], 6) for w in order},
}, indent=2), encoding="utf-8")
print(f"\nwrote {OUT_TOK} and {OUT_SEL}")
