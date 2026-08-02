"""Phase 1b: draw the market sample, and report its composition BEFORE analysis.

The brief is explicit that a prior false positive came from sampling closed 2023
sports markets without noticing, because the endpoint returned oldest-first. So
the sample is drawn with a fixed seed, stratified across time and across the
2026-01-08 fee regime break, and its composition is written out and read before
anything is computed on it.

Eligibility is STRUCTURAL only -- resolved with a single winner, inside subgraph
coverage, order-book enabled. No filter here touches volume, liquidity, or any
wallet property; selecting markets on volume would preferentially select
market-maker-heavy books and bias every downstream number.
"""
import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI = ROOT / "data" / "markets_clob.jsonl"
OUT = ROOT / "data" / "sample_markets.jsonl"
STATS = ROOT / "data" / "sample_composition.json"

SEED = 20260801
N_TARGET = 4000          # markets to sample
FEE_START = 1767830400   # 2026-01-08

# Streamed, not loaded: the universe file is 2.04GB / 2.1M markets and holding
# it all as dicts reached 8.65GB and was OOM-killed once already (see D8). Only
# eligible rows are retained, and only the fields the sampler and puller need.
KEEP = ("condition_id", "tokens", "winner_token", "winner_outcome", "slug",
        "question", "end_ts", "end_date_iso", "neg_risk", "settle_verdict",
        "in_subgraph_window", "fee_regime", "min_tick", "min_order")

elig, why = [], Counter()
n_universe = 0
for line in UNI.open(encoding="utf-8"):
    r = json.loads(line)
    n_universe += 1
    if r["settle_verdict"] != "clean":
        why[f"drop_{r['settle_verdict']}"] += 1
        continue
    if not r.get("in_subgraph_window"):
        why["drop_outside_subgraph_window"] += 1
        continue
    # `enable_order_book` is NOT required -- see build_10c_stats.py. It reports
    # current tradability and is false for essentially every resolved market,
    # so requiring it left zero eligible rows.
    if not r.get("end_ts"):
        why["drop_no_end_date"] += 1
        continue
    why["eligible"] += 1
    elig.append({k: r.get(k) for k in KEEP})

rows = elig          # composition below is reported on the eligible set
print(f"universe: {n_universe:,} markets")
print(f"eligible: {len(elig):,}")
for k, v in why.most_common():
    print(f"  {k:>34}: {v:>7}")

# ------------------------------------------------------- stratified sample
def stratum(r):
    ym = time.strftime("%Y-%m", time.gmtime(r["end_ts"]))
    regime = "post" if r["end_ts"] >= FEE_START else "pre"
    return f"{regime}|{ym}"


buckets = defaultdict(list)
for r in elig:
    buckets[stratum(r)].append(r)

rng = random.Random(SEED)
# proportional allocation, but with a floor so thin months are not wiped out
# and a ceiling so one fat month cannot dominate the sample
n_str = len(buckets)
base = max(N_TARGET // max(n_str, 1), 1)
FLOOR, CEIL = 20, 250

sample, alloc = [], {}
for k, v in sorted(buckets.items()):
    want = min(max(int(round(N_TARGET * len(v) / len(elig))), FLOOR), CEIL)
    want = min(want, len(v))
    alloc[k] = {"available": len(v), "drawn": want}
    sample += rng.sample(v, want)

rng.shuffle(sample)
print(f"\nsampled: {len(sample)} markets across {len(buckets)} strata")

with OUT.open("w", encoding="utf-8") as fh:
    for r in sample:
        fh.write(json.dumps(r) + "\n")

# ------------------------------------------------------------ composition
def yr(r):
    return time.strftime("%Y", time.gmtime(r["end_ts"]))


def month(r):
    return time.strftime("%Y-%m", time.gmtime(r["end_ts"]))


def guess_type(r):
    """Coarse market-type label from the slug, for composition reporting only.

    This is descriptive, never a filter -- the sample is not selected on type.
    """
    s = ((r.get("slug") or "") + " " + (r.get("question") or "")).lower()
    for key, pats in [
        ("crypto_updown", ("updown", "up-or-down", "-up-down")),
        ("crypto", ("bitcoin", "btc", "ethereum", "eth", "solana", "xrp", "doge", "crypto")),
        ("sports", ("nba", "nfl", "mlb", "nhl", "soccer", "premier", "laliga",
                    "ufc", "tennis", "cricket", "vs-", " vs ", "epl", "ncaa",
                    "champions-league", "serie-a", "bundesliga")),
        ("politics", ("election", "president", "senate", "congress", "trump",
                      "biden", "harris", "governor", "parliament", "prime-minister")),
        ("econ", ("fed", "cpi", "inflation", "gdp", "unemployment", "rate-cut",
                  "recession", "jobs")),
        ("entertainment", ("oscar", "grammy", "movie", "album", "netflix",
                           "box-office", "rotten")),
        ("science_tech", ("openai", "gpt", "ai-", "spacex", "nasa", "launch")),
    ]:
        if any(p in s for p in pats):
            return key
    return "other"


comp = {
    "seed": SEED,
    "n_universe": n_universe,
    "eligibility": dict(why.most_common()),
    "n_eligible": len(elig),
    "n_sampled": len(sample),
    "n_strata": len(buckets),
    "allocation": alloc,
    "sample_by_regime": dict(Counter(
        ("post" if r["end_ts"] >= FEE_START else "pre") for r in sample)),
    "sample_by_year": dict(sorted(Counter(yr(r) for r in sample).items())),
    "sample_by_month": dict(sorted(Counter(month(r) for r in sample).items())),
    "sample_by_type": dict(Counter(guess_type(r) for r in sample).most_common()),
    "eligible_by_type": dict(Counter(guess_type(r) for r in elig).most_common()),
    "eligible_by_year": dict(sorted(Counter(yr(r) for r in elig).items())),
    "sample_neg_risk_share": round(
        sum(1 for r in sample if r.get("neg_risk")) / len(sample), 4) if sample else None,
    "sample_end_date_range": [
        min(r["end_date_iso"] for r in sample),
        max(r["end_date_iso"] for r in sample)] if sample else None,
    "winner_outcome_balance": dict(Counter(
        (r.get("winner_outcome") or "?") for r in sample)),
}
STATS.write_text(json.dumps(comp, indent=2), encoding="utf-8")

print("\n=== SAMPLE COMPOSITION (read this before any analysis) ===")
print(f"  date range      : {comp['sample_end_date_range']}")
print(f"  by regime       : {comp['sample_by_regime']}")
print(f"  by year         : {comp['sample_by_year']}")
print(f"  by type (sample): {comp['sample_by_type']}")
print(f"  by type (elig)  : {comp['eligible_by_type']}")
print(f"  winner balance  : {comp['winner_outcome_balance']}")
print(f"  neg-risk share  : {comp['sample_neg_risk_share']}")
print(f"\nwrote {OUT} and {STATS}")
