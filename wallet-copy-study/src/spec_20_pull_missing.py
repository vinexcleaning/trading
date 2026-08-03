r"""Pull the 16,033 token books that Task 5 is missing entirely.

The coverage diagnosis split the 33,522 surviving-wallet period-2 positions
three ways:

    53.6%  no book on disk        <- this script fixes this
    30.3%  book present but too thin for at least one delay
    16.1%  usable at every delay

Pulling every missing token raises the ceiling from 16.1% to **69.7%**. The
remaining 30.3% cannot be fixed by pulling harder -- those tokens simply have no
print at t+delay, which is a fact about the market, not about our data.

Batched `_in` queries of 25 tokens, resumable via a done-file, with a time
budget. The windowed variant was tried in an earlier session and was SLOWER: a
timestamp predicate on an `_in` query makes graph-node scan more, not less.
"""
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DIAG = ROOT / "reports" / "spec_coverage_diag.json"
OUT = ROOT / "data" / "spec_task5_fills.jsonl"
DONE = ROOT / "data" / "spec_task5_missing_done.json"
STATS = ROOT / "reports" / "spec_task5_missing_stats.json"

ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})

BATCH = 25
PAGE = 1000
MAX_PAGES = 40
USDC = 1_000_000.0
TIME_BUDGET_S = int(os.environ.get("PULL_BUDGET_S", "25200"))     # 7h default

Q = """
query($toks:[BigInt!],$skip:Int!){
  rows: orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp, orderDirection:asc,
      where:{%s:$toks}){
    id timestamp maker makerAssetId takerAssetId
    makerAmountFilled takerAmountFilled fee } }
"""
Q_MAKER, Q_TAKER = Q % "makerAssetId_in", Q % "takerAssetId_in"


def gql(q, v, retries=4):
    for a in range(retries):
        try:
            r = S.post(ORDERBOOK, json={"query": q, "variables": v}, timeout=180)
            if r.status_code == 429:
                time.sleep(6 * (a + 1))
                continue
            if r.status_code != 200:
                time.sleep(2 * (a + 1))
                continue
            b = r.json()
            if "errors" in b:
                time.sleep(3 * (a + 1))
                continue
            return b["data"]
        except Exception:  # noqa: BLE001
            time.sleep(3 * (a + 1))
    return None


def decode(x):
    ma, ta = x["makerAssetId"], x["takerAssetId"]
    mf, tf = int(x["makerAmountFilled"]), int(x["takerAmountFilled"])
    if ma == "0" and ta != "0":
        side, tok, sh, usd = "BUY", ta, tf, mf
    elif ta == "0" and ma != "0":
        side, tok, sh, usd = "SELL", ma, mf, tf
    else:
        return None
    if sh <= 0 or usd <= 0:
        return None
    p = usd / sh
    if not 0.0 < p < 1.0:
        return None
    return side, tok, sh / USDC, usd / USDC, p


diag = json.loads(DIAG.read_text(encoding="utf-8"))
missing = diag["missing_tokens_ranked_by_positions_unlocked"]
done = set(json.loads(DONE.read_text(encoding="utf-8"))) if DONE.exists() else set()
todo = [t for t in missing if t not in done]
print(f"missing tokens: {len(missing):,}  already done: {len(done):,}  "
      f"to pull: {len(todo):,}", flush=True)
print(f"time budget: {TIME_BUDGET_S/3600:.1f}h", flush=True)

stats = Counter()
t0 = time.time()
n_rows = 0
wanted = set(todo)

with OUT.open("a", encoding="utf-8") as fh:
    for bi in range(0, len(todo), BATCH):
        if time.time() - t0 > TIME_BUDGET_S:
            stats["stopped_on_time_budget"] = 1
            print("  time budget reached", flush=True)
            break
        batch = todo[bi:bi + BATCH]
        got = {}
        for q in (Q_MAKER, Q_TAKER):
            for pg in range(MAX_PAGES):
                d = gql(q, {"toks": batch, "skip": pg * PAGE})
                if d is None:
                    stats["query_failed"] += 1
                    break
                rows = d["rows"]
                for r_ in rows:
                    got[r_["id"]] = r_
                if len(rows) < PAGE:
                    break
                if pg == MAX_PAGES - 1:
                    stats["batch_truncated"] += 1
        for x in got.values():
            dec = decode(x)
            if dec is None:
                continue
            side, tok, sh, usd, p = dec
            if tok not in wanted:
                continue
            fh.write(json.dumps({
                "token": tok, "ts": int(x["timestamp"]), "side": side,
                "price": round(p, 8), "shares": round(sh, 6),
                "usdc": round(usd, 6), "maker": str(x["maker"]).lower(),
            }) + "\n")
            n_rows += 1
        done.update(batch)
        stats["tokens_done"] += len(batch)
        stats["batches"] += 1
        if stats["batches"] % 20 == 0:
            fh.flush()
            DONE.write_text(json.dumps(sorted(done)), encoding="utf-8")
            el = time.time() - t0
            rate = stats["tokens_done"] / el
            left = len(todo) - stats["tokens_done"]
            print(f"  {stats['tokens_done']:>6,}/{len(todo):,}  "
                  f"fills=+{n_rows:>10,}  {el/3600:>5.2f}h  "
                  f"{rate:.2f} tok/s  eta {left/rate/3600:>5.2f}h", flush=True)

DONE.write_text(json.dumps(sorted(done)), encoding="utf-8")
el = time.time() - t0
summary = {"tokens_targeted": len(todo), "tokens_done": stats["tokens_done"],
           "fills_added": n_rows, "hours": round(el / 3600, 2),
           "counters": dict(stats)}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(f"\nwrote {OUT} (append) and {DONE}")
