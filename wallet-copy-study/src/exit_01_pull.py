"""Exit study, step 1: pull complete books for the target tokens.

"The price 60 seconds after the wallet sold" is only meaningful if every trade
in that token is visible. The existing market panel overlaps the selected
wallets in ~140 markets, which is the thin slice that produced the retracted
-5.9pp reading, so this pulls complete fills for tokens where a top-decile
wallet actually sold in period 2.

Single-threaded and paced, per the standing API-courtesy constraint.
"""
import json
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "data" / "exit_target_tokens.json"
OUT = ROOT / "data" / "exit_fills.jsonl"
STATS = ROOT / "data" / "exit_fills_stats.json"

ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
PAGE = 1000
MAX_PAGES = 30
USDC = 1_000_000.0

Q_MAKER = """
query($t:BigInt!,$skip:Int!){
  rows: orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp, orderDirection:asc,
      where:{makerAssetId:$t}){
    id timestamp maker makerAssetId takerAssetId
    makerAmountFilled takerAmountFilled fee } }
"""
Q_TAKER = """
query($t:BigInt!,$skip:Int!){
  rows: orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp, orderDirection:asc,
      where:{takerAssetId:$t}){
    id timestamp maker makerAssetId takerAssetId
    makerAmountFilled takerAmountFilled fee } }
"""


def gql(q, v, retries=5):
    for a in range(retries):
        try:
            r = S.post(ORDERBOOK, json={"query": q, "variables": v}, timeout=120)
            if r.status_code == 429:
                time.sleep(5 * (a + 1))
                continue
            if r.status_code != 200:
                time.sleep(1.5 * (a + 1))
                continue
            b = r.json()
            if "errors" in b:
                time.sleep(2.0 * (a + 1))
                continue
            return b["data"]
        except Exception:  # noqa: BLE001
            time.sleep(2.0 * (a + 1))
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


cfg = json.loads(TOKENS.read_text(encoding="utf-8"))
tokens = cfg["tokens"]
print(f"pulling complete books for {len(tokens):,} tokens", flush=True)

stats = Counter()
t0 = time.time()
n_rows = 0
with OUT.open("w", encoding="utf-8") as fh:
    for i, tok in enumerate(tokens):
        got = {}
        trunc = False
        for q in (Q_MAKER, Q_TAKER):
            for pg in range(MAX_PAGES):
                d = gql(q, {"t": tok, "skip": pg * PAGE})
                if d is None:
                    trunc = True
                    break
                rows = d["rows"]
                for r_ in rows:
                    got[r_["id"]] = r_
                if len(rows) < PAGE:
                    break
                if pg == MAX_PAGES - 1:
                    trunc = True
        if trunc:
            stats["tokens_truncated"] += 1
        if not got:
            stats["tokens_empty"] += 1
        for x in got.values():
            d = decode(x)
            if d is None:
                stats["undecodable"] += 1
                continue
            side, token, shares, usdc, p = d
            if token != tok:
                continue
            fh.write(json.dumps({
                "token": tok, "ts": int(x["timestamp"]),
                "side": side, "price": round(p, 8),
                "shares": round(shares, 6), "usdc": round(usdc, 6),
                "maker": str(x["maker"]).lower(),
            }) + "\n")
            n_rows += 1
            stats[f"side_{side}"] += 1
        stats["tokens_done"] += 1
        if (i + 1) % 100 == 0:
            el = time.time() - t0
            rate = (i + 1) / el
            print(f"  {i+1:>5}/{len(tokens)}  fills={n_rows:>9,}  {el:>6.0f}s  "
                  f"{rate:.1f} tok/s  eta {(len(tokens)-i-1)/rate/60:>5.1f}m",
                  flush=True)

el = time.time() - t0
summary = {"n_tokens": len(tokens), "seconds": round(el),
           "n_fills": n_rows, "counters": dict(stats)}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(f"\nwrote {OUT} and {STATS}")
