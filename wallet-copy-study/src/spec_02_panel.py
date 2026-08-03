r"""Build the compact analysis panel: positions joined to category and event.

One row per (wallet, market, token) settled position, carrying only the fields
the specialist pipeline needs. Written once so the real run and the synthetic
control read identical inputs.

Also emits, per token, the volume-weighted average traded price. The synthetic
control needs it: to simulate a world with no skill it redraws each token's
outcome from Bernoulli(that price), which makes every wallet exactly zero-edge
in expectation while preserving price selection, category mix, event structure
and -- crucially -- the fact that every wallet holding the same token shares the
same outcome. Redrawing per POSITION instead would destroy within-event
correlation and make the control far too easy to pass.
"""
import json
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = ROOT / "data" / "wallet_positions.jsonl"
CATMAP = ROOT / "data" / "spec_cid_category.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
OUT = ROOT / "data" / "spec_panel.jsonl"
TOKQ = ROOT / "data" / "spec_token_q.json"
STATS = ROOT / "reports" / "spec_task1_panel.json"

print("loading category map...", flush=True)
cat_of, ev_of = {}, {}
for line in CATMAP.open(encoding="utf-8"):
    r = json.loads(line)
    cat_of[r["cid"]] = r["cat"]
    ev_of[r["cid"]] = r["ev"]
print(f"  {len(cat_of):,} markets")

mm = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])
print(f"  {len(mm):,} Phase-2 excluded wallets (market makers / too large)")

print("\nbuilding panel...", flush=True)
n = n_out = 0
t0 = time.time()
tok_num, tok_den = defaultdict(float), defaultdict(float)
cats = defaultdict(int)
with OUT.open("w", encoding="utf-8") as fh:
    for line in POS.open(encoding="utf-8"):
        r = json.loads(line)
        n += 1
        if r["flags"] or r["edge"] is None or r["settle_state"] != "settled":
            continue
        if r["cost"] <= 0 or r["shares_in"] <= 0:
            continue
        cid = r["cid"]
        cat = cat_of.get(cid)
        if cat is None:
            continue
        px = r["entry_px"]
        out = 1.0 if r["is_winner"] else 0.0
        tok = r["token"]
        tok_num[tok] += px * r["cost"]
        tok_den[tok] += r["cost"]
        fh.write(json.dumps({
            "w": r["wallet"], "cid": cid, "tok": tok,
            "ev": ev_of.get(cid, f"cid:{cid}"), "cat": cat,
            "ts": r["first_ts"], "px": round(px, 6),
            "edge": round(r["edge"], 6), "outcome": out,
            "cost": round(r["cost"], 4), "si": round(r["shares_in"], 4),
            "nsell": r["n_sells"], "mm": r["wallet"] in mm,
        }) + "\n")
        n_out += 1
        cats[cat] += 1
        if n % 500_000 == 0:
            print(f"  {n:,} -> {n_out:,}  {time.time()-t0:.0f}s", flush=True)

q = {t: round(tok_num[t] / tok_den[t], 6) for t in tok_den if tok_den[t] > 0}
TOKQ.write_text(json.dumps(q), encoding="utf-8")

summary = {
    "n_positions_scanned": n,
    "n_panel_rows": n_out,
    "n_tokens": len(q),
    "by_category": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
    "n_mm_excluded_wallets": len(mm),
}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(f"\n  {n:,} positions -> {n_out:,} panel rows, {len(q):,} tokens "
      f"in {time.time()-t0:.0f}s")
print(f"  by category: {summary['by_category']}")
print(f"\nwrote {OUT}, {TOKQ}, {STATS}")
