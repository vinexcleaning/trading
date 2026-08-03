r"""Task 5 prep: identify the survivors' tokens and size the book pull exactly.

Reproduces the survivor set from spec_05 (same cut, same filters, same
exclusions) so the pull targets precisely the wallets whose latency tolerance is
in question, then subtracts tokens whose books were already pulled in earlier
sessions so nothing is fetched twice.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import add_excess, price_band_benchmark, rank_within_category  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
HAVE = [ROOT / "data" / "exit_fills.jsonl", ROOT / "data" / "fills.jsonl"]
OUT = ROOT / "data" / "spec_task5_targets.json"

CUT = 1767830400          # 2026-01-08 fee era, as in spec_05
CATS = ["politics", "crypto", "soccer", "nba", "nfl", "esports", "other", "weather"]
FILT = {"min_trades": 20, "min_events": 10, "recent_within_days": 30,
        "max_gap_days": 30}
MIN_RANKED = 30

flags = json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"]
MM = {w for w, rs in flags.items() if any(r.startswith("market_maker") for r in rs)}
WH = {w for w, rs in flags.items() if "too_large_to_copy" in rs}

print("loading panel...", flush=True)
rows = [json.loads(l) for l in PANEL.open(encoding="utf-8")]
sel = [r for r in rows if r["ts"] < CUT]
mea = [r for r in rows if r["ts"] >= CUT]
add_excess(sel, price_band_benchmark(sel))
print(f"  {len(rows):,} rows; sel {len(sel):,} meas {len(mea):,}")

f2 = dict(FILT)
f2["exclude"] = MM | WH
survivors = {}
for cat in CATS:
    scores, _ = rank_within_category(sel, cat, f2, None)
    if len(scores) < MIN_RANKED:
        continue
    order = sorted(scores, key=lambda w: -scores[w])
    for w in order[:max(len(order) // 10, 1)]:
        survivors.setdefault(w, []).append(cat)
print(f"  {len(survivors)} survivors: "
      f"{Counter(c for v in survivors.values() for c in v)}")

pos = [r for r in mea if r["w"] in survivors]
toks = Counter(r["tok"] for r in pos)
print(f"  {len(pos):,} period-2 positions over {len(toks):,} distinct tokens")

print("\nchecking tokens already pulled...", flush=True)
have = set()
for p in HAVE:
    if not p.exists():
        continue
    n = 0
    for line in p.open(encoding="utf-8"):
        i = line.find('"token": "')
        if i >= 0:
            j = line.find('"', i + 10)
            have.add(line[i + 10:j])
        n += 1
    print(f"  {p.name}: {n:,} fills, {len(have):,} distinct tokens cumulative")

need = [t for t in toks if t not in have]
covered_pos = sum(c for t, c in toks.items() if t in have)
print(f"\n  already have books for {len(toks)-len(need):,} of {len(toks):,} tokens "
      f"({covered_pos:,} of {len(pos):,} positions)")
print(f"  NEED TO PULL: {len(need):,} tokens")

# how heavy are they? positions per token is a rough proxy for fill count
heavy = sorted(toks[t] for t in need)
print(f"  positions per needed token: median {heavy[len(heavy)//2]}, "
      f"p90 {heavy[int(len(heavy)*.9)]}, max {heavy[-1]}")

OUT.write_text(json.dumps({
    "cut": CUT, "filters": FILT, "min_ranked": MIN_RANKED,
    "n_survivors": len(survivors),
    "survivors": {w: c for w, c in survivors.items()},
    "n_period2_positions": len(pos),
    "n_distinct_tokens": len(toks),
    "n_already_have": len(toks) - len(need),
    "n_to_pull": len(need),
    "tokens_to_pull": need,
}, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
