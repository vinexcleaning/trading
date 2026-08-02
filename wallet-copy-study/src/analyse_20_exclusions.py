"""Phase 2: STRUCTURAL exclusions. Never performance-based.

Three groups get removed, and each removal rule is a measurement with a stated
threshold rather than a judgement call:

  1. **Market makers.** Two-sided flow in the same token, short holds, high
     frequency, round lot sizes, near-zero rate of holding to settlement. A
     market maker's "edge" is spread capture, which a copier cannot replicate:
     by the time you see the fill, the quote that earned it is gone.
  2. **Wallets too large to copy.** If a wallet's typical trade moves the book,
     you cannot get its price -- you fill worse by construction, and the
     measured edge is one you could never have taken.
  3. **Infrastructure addresses.** Operator/relayer contracts identified in
     Phase 0 (no data API record, very large fill share).

Insider and wash-trading patterns are REPORTED but not used to exclude: they are
neither legal to follow nor reproducible, and flagging them matters more than
filtering them.

Nothing here looks at whether a wallet made money. Performance filtering happens
only in Phase 4, with out-of-sample discipline.
"""
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILLS = ROOT / "data" / "wallet_fills.jsonl"
POS = ROOT / "data" / "wallet_positions.jsonl"
OUT = ROOT / "reports" / "phase2_exclusions.json"
FLAGS = ROOT / "data" / "wallet_flags.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

# Operator addresses identified in Phase 0 (no data-api record, huge fill share)
INFRA = {
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e",
    "0xc5d563a36ae78145c45a50134d48a1215220f80a",
}

# thresholds, each justified by the distribution printed below
TH = {
    "mm_two_sided_rate": 0.50,      # >50% of tokens traded on both sides
    "mm_median_hold_s": 3600,       # median position held under an hour
    "mm_settle_rate": 0.10,         # <10% of positions carried to settlement
    "large_median_notional": 5000,  # median market notional, USD
}

print("scanning fills...", flush=True)
w_stats = defaultdict(lambda: {
    "n": 0, "buy": 0, "sell": 0, "usd": 0.0, "sizes": [],
    "t0": None, "t1": None, "days": set(), "round": 0,
})
n = 0
t0 = time.time()
for line in FILLS.open(encoding="utf-8"):
    f = json.loads(line)
    n += 1
    a = w_stats[f["wallet"]]
    a["n"] += 1
    a["buy" if f["side"] == "BUY" else "sell"] += 1
    a["usd"] += f["usdc"]
    if len(a["sizes"]) < 4000:
        a["sizes"].append(f["usdc"])
    ts = f["ts"]
    a["t0"] = ts if a["t0"] is None else min(a["t0"], ts)
    a["t1"] = ts if a["t1"] is None else max(a["t1"], ts)
    a["days"].add(ts // 86400)
    s = f["shares"]
    if abs(s - round(s)) < 1e-6 and s >= 1:
        a["round"] += 1
    if n % 2_000_000 == 0:
        print(f"  {n:,} fills  {time.time()-t0:.0f}s", flush=True)
print(f"  {n:,} fills over {len(w_stats):,} wallets in {time.time()-t0:.0f}s")

print("\nscanning positions...", flush=True)
w_pos = defaultdict(lambda: {
    "pos": 0, "two_sided": 0, "settled_held": 0, "holds": [],
    "mkts": set(), "notional": [], "both_outcomes": 0,
})
wm_tokens = defaultdict(set)
m = 0
for line in POS.open(encoding="utf-8"):
    r = json.loads(line)
    m += 1
    a = w_pos[r["wallet"]]
    a["pos"] += 1
    a["mkts"].add(r["cid"])
    if r["n_buys"] > 0 and r["n_sells"] > 0:
        a["two_sided"] += 1
    if r["held_to_settlement"]:
        a["settled_held"] += 1
    a["holds"].append(r["hold_seconds"])
    a["notional"].append(r["cost"])
    wm_tokens[(r["wallet"], r["cid"])].add(r["token"])
for (w, cid), toks in wm_tokens.items():
    if len(toks) > 1:
        w_pos[w]["both_outcomes"] += 1
print(f"  {m:,} positions")


def med(xs):
    if not xs:
        return None
    s = sorted(xs)
    return s[len(s) // 2]


rows = {}
for w, a in w_stats.items():
    p = w_pos.get(w, {"pos": 0, "two_sided": 0, "settled_held": 0,
                      "holds": [], "mkts": set(), "notional": [],
                      "both_outcomes": 0})
    npos = max(p["pos"], 1)
    nmkt = max(len(p["mkts"]), 1)
    span_days = max((a["t1"] - a["t0"]) / 86400, 1e-9) if a["t1"] else 0
    rows[w] = {
        "n_fills": a["n"],
        "n_positions": p["pos"],
        "n_markets": len(p["mkts"]),
        "buy_share": round(a["buy"] / a["n"], 4),
        "two_sided_rate": round(p["two_sided"] / npos, 4),
        "both_outcomes_rate": round(p["both_outcomes"] / nmkt, 4),
        "settle_rate": round(p["settled_held"] / npos, 4),
        "median_hold_s": med(p["holds"]),
        "median_trade_usd": round(med(a["sizes"]) or 0, 2),
        "median_market_notional_usd": round(med(p["notional"]) or 0, 2),
        "total_usd": round(a["usd"], 2),
        "round_lot_rate": round(a["round"] / a["n"], 4),
        "active_days": len(a["days"]),
        "span_days": round(span_days, 2),
        "fills_per_active_day": round(a["n"] / max(len(a["days"]), 1), 2),
    }

# ------------------------------------------------------------ exclusions
excl = {}
counts = Counter()
for w, r in rows.items():
    reasons = []
    if w in INFRA:
        reasons.append("infrastructure_address")
    mm_hits = 0
    if r["two_sided_rate"] >= TH["mm_two_sided_rate"]:
        mm_hits += 1
    if r["median_hold_s"] is not None and r["median_hold_s"] <= TH["mm_median_hold_s"]:
        mm_hits += 1
    if r["settle_rate"] <= TH["mm_settle_rate"]:
        mm_hits += 1
    if mm_hits >= 2:
        reasons.append(f"market_maker_{mm_hits}of3")
    if r["median_market_notional_usd"] >= TH["large_median_notional"]:
        reasons.append("too_large_to_copy")
    if reasons:
        excl[w] = reasons
        for x in reasons:
            counts[x.split("_")[0] if x.startswith("market_maker") else x] += 1
        counts["ANY"] += 1

FLAGS.write_text(json.dumps(
    {"thresholds": TH, "infrastructure": sorted(INFRA),
     "excluded": excl, "wallet_stats": rows}, indent=2), encoding="utf-8")


def dist(key, qs=(.1, .25, .5, .75, .9, .99)):
    v = sorted(r[key] for r in rows.values() if r[key] is not None)
    if not v:
        return None
    return {f"p{int(q*100)}": v[int(len(v) * q)] for q in qs}


report = {
    "meta": {
        "n_wallets": len(rows), "n_fills": n, "n_positions": m,
        "thresholds": TH,
        "principle": "structural only -- no rule here consults profitability",
    },
    "distributions": {k: dist(k) for k in
                      ("two_sided_rate", "settle_rate", "median_hold_s",
                       "median_trade_usd", "median_market_notional_usd",
                       "round_lot_rate", "fills_per_active_day", "n_markets")},
    "exclusions": {
        "n_excluded": len(excl),
        "frac_excluded": round(len(excl) / max(len(rows), 1), 4),
        "by_reason": dict(counts),
        "n_remaining": len(rows) - len(excl),
    },
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("\n=== PHASE 2 EXCLUSIONS ===")
for k, v in report["distributions"].items():
    print(f"  {k:>28}: {v}")
print(f"\n  excluded {len(excl):,} of {len(rows):,} wallets "
      f"({len(excl)/max(len(rows),1):.1%})")
for k, v in counts.most_common():
    print(f"    {k:>28}: {v:,}")
print(f"\nwrote {OUT} and {FLAGS}")
