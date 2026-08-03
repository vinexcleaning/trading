r"""Task 5: targeted book pull for the survivors' period-2 tokens.

BATCHED. The earlier per-token puller ran at 0.53 tokens/s, which would have
taken ~16 hours here. `makerAssetId_in` / `takerAssetId_in` accept a list, so
this fetches many tokens per query and assigns fills to tokens afterwards.

Resumable: completed batches are journalled, so a restart skips them rather than
refetching. On a statement timeout the batch is split and retried, because one
very active token in a batch can make the whole query too heavy.

Single-threaded and paced, per the standing API-courtesy constraint.
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ROOT / "data" / "spec_task5_targets.json"
OUT = ROOT / "data" / "spec_task5_fills.jsonl"
DONE = ROOT / "data" / "spec_task5_done.json"
STATS = ROOT / "reports" / "spec_task5_pull_stats.json"

ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})

BATCH = 25
PAGE = 1000
MAX_PAGES = 150
USDC = 1_000_000.0

Q = """
query($toks:[BigInt!],$skip:Int!){
  rows: orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp, orderDirection:asc,
      where:{%s:$toks}){
    id timestamp maker makerAssetId takerAssetId
    makerAmountFilled takerAmountFilled fee } }
"""
Q_MAKER = Q % "makerAssetId_in"
Q_TAKER = Q % "takerAssetId_in"


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
        side, token, shares, usdc = "BUY", ta, tf, mf
    elif ta == "0" and ma != "0":
        side, token, shares, usdc = "SELL", ma, mf, tf
    else:
        return None
    if shares <= 0 or usdc <= 0:
        return None
    p = usdc / shares
    if not 0.0 < p < 1.0:
        return None
    return side, token, shares / USDC, usdc / USDC, p


def fetch_batch(toks, stats):
    """All fills touching any token in `toks`. Splits on failure."""
    got = {}
    for qname, q in (("maker", Q_MAKER), ("taker", Q_TAKER)):
        for pg in range(MAX_PAGES):
            d = gql(q, {"toks": toks, "skip": pg * PAGE})
            if d is None:
                if len(toks) > 1:
                    mid = len(toks) // 2
                    stats["batch_split"] += 1
                    a = fetch_batch(toks[:mid], stats)
                    b = fetch_batch(toks[mid:], stats)
                    a.update(b)
                    a.update(got)
                    return a
                stats["token_failed"] += 1
                break
            rows = d["rows"]
            for r_ in rows:
                got[r_["id"]] = r_
            if len(rows) < PAGE:
                break
            if pg == MAX_PAGES - 1:
                stats["batch_truncated"] += 1
    return got


cfg = json.loads(TARGETS.read_text(encoding="utf-8"))
tokens = cfg["tokens_to_pull"]
want = set(tokens)
print(f"targets: {len(tokens):,} tokens for {cfg['n_survivors']} survivors "
      f"({cfg['n_period2_positions']:,} period-2 positions)", flush=True)

done = set()
if DONE.exists():
    done = set(json.loads(DONE.read_text(encoding="utf-8")))
    print(f"  resuming: {len(done):,} tokens already pulled", flush=True)

todo = [t for t in tokens if t not in done]
batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
print(f"  {len(todo):,} remaining in {len(batches):,} batches of {BATCH}",
      flush=True)

stats = Counter()
t0 = time.time()
n_rows = 0
mode = "a" if done else "w"
with OUT.open(mode, encoding="utf-8") as fh:
    for i, b in enumerate(batches):
        got = fetch_batch(b, stats)
        for x in got.values():
            d = decode(x)
            if d is None:
                stats["undecodable"] += 1
                continue
            side, token, shares, usdc, p = d
            if token not in want:
                continue          # complementary token swept in by the batch
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
            rate = (i + 1) / el
            print(f"  batch {i+1:>5}/{len(batches)}  tokens~{len(done):,}  "
                  f"fills={n_rows:>9,}  {el:>6.0f}s  "
                  f"eta {(len(batches)-i-1)/rate/60:>6.1f}m", flush=True)

DONE.write_text(json.dumps(sorted(done)), encoding="utf-8")
el = time.time() - t0
summary = {"n_tokens_targeted": len(tokens), "n_tokens_done": len(done),
           "n_fills": n_rows, "seconds": round(el),
           "batch_size": BATCH, "counters": dict(stats)}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(f"\nwrote {OUT}")
