r"""Task 5 top-up: raise per-wallet coverage, not just total coverage.

After 4,625 tokens the pooled curve is solid (1,806 events, n_eff 1,124) but only
9 of 30 survivors clear the 30-event reporting floor, because tokens were pulled
in panel order and panel order is grouped by wallet. That is a coverage skew
across WALLETS, and per-wallet latency is the actual deliverable.

So this samples additional tokens **per under-covered wallet**, uniformly at
random with a fixed seed, capped so the job finishes. No performance criterion
enters the choice -- only how many events that wallet already has.

Full books (no timestamp filter): the windowed variant was tried and was SLOWER,
because adding a timestamp predicate to an `_in` query makes graph-node scan more
rather than less. Recorded so nobody tries it again.
"""
import json
import random
import sys
import time
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
TARGETS = ROOT / "data" / "spec_task5_targets.json"
OUT = ROOT / "data" / "spec_task5_fills.jsonl"
DONE = ROOT / "data" / "spec_task5_done.json"
BOOKS = [OUT, ROOT / "data" / "exit_fills.jsonl", ROOT / "data" / "fills.jsonl"]
STATS = ROOT / "reports" / "spec_task5_topup_stats.json"

ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})

CUT = 1767830400
SEED = 20260801
TARGET_EVENTS = 500          # overnight run: push coverage much higher
MAX_TOKENS = 9000            # overnight budget
BATCH = 25
PAGE = 1000
MAX_PAGES = 40
USDC = 1_000_000.0
TIME_BUDGET_S = 18000        # 5h, leaves room before the recorder ends

Q = """
query($toks:[BigInt!],$skip:Int!){
  rows: orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp, orderDirection:asc,
      where:{%s:$toks}){
    id timestamp maker makerAssetId takerAssetId
    makerAmountFilled takerAmountFilled fee } }
"""
Q_MAKER, Q_TAKER = Q % "makerAssetId_in", Q % "takerAssetId_in"


def gql(q, v, retries=3):
    for a in range(retries):
        try:
            r = S.post(ORDERBOOK, json={"query": q, "variables": v}, timeout=150)
            if r.status_code == 429:
                time.sleep(6 * (a + 1))
                continue
            if r.status_code != 200:
                time.sleep(2 * (a + 1))
                continue
            b = r.json()
            if "errors" in b:
                time.sleep(2 * (a + 1))
                continue
            return b["data"]
        except Exception:  # noqa: BLE001
            time.sleep(2 * (a + 1))
    return None


def decode(x):
    ma, ta = x["makerAssetId"], x["takerAssetId"]
    mf, tf = int(x["makerAmountFilled"]), int(x["takerAmountFilled"])
    if ma == "0" and ta != "0":
        return "BUY", ta, tf / USDC, mf / USDC, (mf / tf if tf else 0)
    if ta == "0" and ma != "0":
        return "SELL", ma, mf / USDC, tf / USDC, (tf / mf if mf else 0)
    return None


cfg = json.loads(TARGETS.read_text(encoding="utf-8"))
survivors = set(cfg["survivors"])
done = set(json.loads(DONE.read_text(encoding="utf-8"))) if DONE.exists() else set()
print(f"{len(survivors)} survivors, {len(done):,} tokens already pulled",
      flush=True)

print("measuring current per-wallet event coverage...", flush=True)
have_tok = set()
for p in BOOKS:
    if not p.exists():
        continue
    for line in p.open(encoding="utf-8"):
        i = line.find('"token": "')
        if i >= 0:
            j = line.find('"', i + 10)
            have_tok.add(line[i + 10:j])
print(f"  books exist for {len(have_tok):,} tokens")

cov_ev = defaultdict(set)
uncov = defaultdict(list)
for line in PANEL.open(encoding="utf-8"):
    r = json.loads(line)
    if r["ts"] < CUT or r["w"] not in survivors:
        continue
    if r["tok"] in have_tok:
        cov_ev[r["w"]].add(r["ev"])
    else:
        uncov[r["w"]].append(r["tok"])

rng = random.Random(SEED)
picks, plan = [], {}
for w in sorted(survivors):
    have_n = len(cov_ev.get(w, ()))
    short = max(TARGET_EVENTS - have_n, 0)
    pool = sorted(set(uncov.get(w, [])))
    take = min(short, len(pool))
    chosen = rng.sample(pool, take) if take else []
    plan[w] = {"events_covered": have_n, "shortfall": short,
               "uncovered_tokens": len(pool), "requested": take}
    picks += chosen
picks = sorted(set(picks) - done)
rng.shuffle(picks)
picks = picks[:MAX_TOKENS]
print(f"  under-covered wallets: "
      f"{sum(1 for v in plan.values() if v['shortfall'] > 0)} of {len(plan)}")
print(f"  pulling {len(picks):,} additional tokens "
      f"(cap {MAX_TOKENS:,}, time budget {TIME_BUDGET_S//60}m)\n", flush=True)

batches = [picks[i:i + BATCH] for i in range(0, len(picks), BATCH)]
stats = Counter()
t0 = time.time()
n_rows = 0
with OUT.open("a", encoding="utf-8") as fh:
    for i, b in enumerate(batches):
        if time.time() - t0 > TIME_BUDGET_S:
            stats["stopped_on_time_budget"] = 1
            print("  time budget reached; stopping cleanly", flush=True)
            break
        got = {}
        for q in (Q_MAKER, Q_TAKER):
            for pg in range(MAX_PAGES):
                d = gql(q, {"toks": b, "skip": pg * PAGE})
                if d is None:
                    stats["page_failed"] += 1
                    break
                rows = d["rows"]
                for r_ in rows:
                    got[r_["id"]] = r_
                if len(rows) < PAGE:
                    break
                if pg == MAX_PAGES - 1:
                    stats["batch_truncated"] += 1
        want = set(b)
        for x in got.values():
            dd = decode(x)
            if dd is None:
                continue
            side, token, shares, usdc, p = dd
            if token not in want or not 0.0 < p < 1.0:
                continue
            fh.write(json.dumps({
                "token": token, "ts": int(x["timestamp"]), "side": side,
                "price": round(p, 8), "shares": round(shares, 6),
                "usdc": round(usdc, 6), "maker": str(x["maker"]).lower(),
            }) + "\n")
            n_rows += 1
        done.update(b)
        stats["batches_done"] += 1
        if (i + 1) % 20 == 0:
            fh.flush()
            DONE.write_text(json.dumps(sorted(done)), encoding="utf-8")
            el = time.time() - t0
            print(f"  batch {i+1:>4}/{len(batches)}  fills={n_rows:>9,}  "
                  f"{el:>5.0f}s  eta {(len(batches)-i-1)/((i+1)/el)/60:>5.1f}m",
                  flush=True)

DONE.write_text(json.dumps(sorted(done)), encoding="utf-8")
summary = {"n_new_tokens": len(picks), "n_tokens_total": len(done),
           "n_new_fills": n_rows, "seconds": round(time.time() - t0),
           "seed": SEED, "target_events_per_wallet": TARGET_EVENTS,
           "sampling": "uniform random over each under-covered wallet's "
                       "uncovered tokens; no performance criterion",
           "plan": plan, "counters": dict(stats)}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(f"\n  {n_rows:,} new fills over {len(picks):,} tokens in "
      f"{time.time()-t0:.0f}s")
print(f"wrote {OUT}, {STATS}")
