"""Phase 1c: pull every fill in every sampled market.

One `orderFilledEvent` is TWO wallet-level trades -- the maker's and the taker's
-- on opposite sides. Both are emitted, so a wallet is measured whichever leg it
happened to be on.

Decoding (established in probe_02, and an inverted version of it is exactly the
error that produced a 0.96 median relative fee error):
    makerAssetId == 0  -> maker paid USDC, received tokens  -> maker BOUGHT
    takerAssetId == 0  -> maker paid tokens, received USDC  -> maker SOLD
`fee` is charged on the maker's leg, denominated in the asset the maker
receives. The taker's fee is not in this event, so taker-leg fees are imputed
from the same verified formula rather than assumed zero.

Per-market fill counts are heavily skewed, so each market is capped and any
truncation is RECORDED -- a silently truncated market would look like a thin
book and distort both the naive benchmark and price-impact measurement.
"""
import json
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample_markets.jsonl"
OUT = ROOT / "data" / "fills.jsonl"
STATS = ROOT / "data" / "fills_stats.json"
STATE = ROOT / "data" / "fills_progress.json"

ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})

PAGE = 1000
MAX_PAGES_PER_SIDE = 40          # 40k fills/side/market cap; truncation recorded
FEE_RATE = 0.10                  # verified in probe_02: 0.10 * min(p,1-p)/share
USDC = 1_000_000.0               # 6 decimals


def gql(q, v, retries=5):
    for a in range(retries):
        try:
            r = S.post(ORDERBOOK, json={"query": q, "variables": v}, timeout=120)
            if r.status_code != 200:
                time.sleep(1.5 * (a + 1))
                continue
            b = r.json()
            if "errors" in b:
                # statement timeouts are transient at this size; back off
                time.sleep(2.0 * (a + 1))
                continue
            return b["data"]
        except Exception:  # noqa: BLE001
            time.sleep(2.0 * (a + 1))
    return None


Q = """
query($toks:[BigInt!],$skip:Int!,$field:Int!){
  a: orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp, orderDirection:asc,
      where:{makerAssetId_in:$toks}){
    id timestamp transactionHash orderHash maker taker
    makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee }
}"""

Q_MAKER = """
query($toks:[BigInt!],$skip:Int!){
  rows: orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp, orderDirection:asc,
      where:{makerAssetId_in:$toks}){
    id timestamp transactionHash orderHash maker taker
    makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee }
}"""

Q_TAKER = """
query($toks:[BigInt!],$skip:Int!){
  rows: orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp, orderDirection:asc,
      where:{takerAssetId_in:$toks}){
    id timestamp transactionHash orderHash maker taker
    makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee }
}"""


def decode(x):
    """-> dict describing the trade from the MAKER's perspective, or None."""
    ma, ta = x["makerAssetId"], x["takerAssetId"]
    mf, tf = int(x["makerAmountFilled"]), int(x["takerAmountFilled"])
    if ma == "0" and ta != "0":
        side, token, shares, usdc = "BUY", ta, tf, mf
    elif ta == "0" and ma != "0":
        side, token, shares, usdc = "SELL", ma, mf, tf
    else:
        return None                      # token-for-token; not a cash trade
    if shares <= 0 or usdc <= 0:
        return None
    p = usdc / shares
    if not (0.0 < p < 1.0):
        return None
    return {"side": side, "token": token,
            "shares": shares / USDC, "usdc": usdc / USDC, "price": p}


def fetch_market(tokens):
    """All fills touching either outcome token. Returns (rows, truncated)."""
    got, trunc = {}, False
    for q in (Q_MAKER, Q_TAKER):
        for pg in range(MAX_PAGES_PER_SIDE):
            d = gql(q, {"toks": tokens, "skip": pg * PAGE})
            if d is None:
                trunc = True
                break
            rows = d["rows"]
            for r_ in rows:
                got[r_["id"]] = r_
            if len(rows) < PAGE:
                break
            if pg == MAX_PAGES_PER_SIDE - 1:
                trunc = True
    return list(got.values()), trunc


markets = [json.loads(l) for l in SAMPLE.open(encoding="utf-8")]
print(f"pulling fills for {len(markets)} sampled markets", flush=True)

stats = Counter()
per_market = {}
t0 = time.time()
n_fill_rows = 0

with OUT.open("w", encoding="utf-8") as fh:
    for i, m in enumerate(markets):
        toks = m["tokens"]
        rows, trunc = fetch_market(toks)
        stats["markets_done"] += 1
        if trunc:
            stats["markets_truncated"] += 1
        if not rows:
            stats["markets_with_no_fills"] += 1
        per_market[m["condition_id"]] = {"n_fills": len(rows), "truncated": trunc}

        winner = m.get("winner_token")
        for x in rows:
            d = decode(x)
            if d is None:
                stats["fills_undecodable"] += 1
                continue
            if d["token"] not in toks:
                stats["fills_token_not_in_market"] += 1
                continue
            p = d["price"]
            econ_fee_per_share = FEE_RATE * min(p, 1 - p)
            # maker-leg fee as actually charged on chain, converted to dollars
            raw_fee = int(x["fee"])
            if raw_fee:
                maker_fee_usd = (raw_fee / USDC * p if d["side"] == "BUY"
                                 else raw_fee / USDC)
            else:
                maker_fee_usd = 0.0
            rec = {
                "cid": m["condition_id"],
                "ts": int(x["timestamp"]),
                "tx": x["transactionHash"],
                "token": d["token"],
                "price": round(p, 8),
                "shares": round(d["shares"], 6),
                "usdc": round(d["usdc"], 6),
                "maker": str(x["maker"]).lower(),
                "taker": str(x["taker"]).lower(),
                "maker_side": d["side"],
                "maker_fee_usd": round(maker_fee_usd, 8),
                "econ_fee_per_share": round(econ_fee_per_share, 8),
                "is_winner": (d["token"] == winner) if winner else None,
                "end_ts": m["end_ts"],
            }
            fh.write(json.dumps(rec) + "\n")
            n_fill_rows += 1
            stats[f"maker_{d['side']}"] += 1

        if (i + 1) % 100 == 0:
            el = time.time() - t0
            rate = (i + 1) / el
            print(f"  {i+1:>5}/{len(markets)}  fills={n_fill_rows:>9}  "
                  f"{el:>6.0f}s  {rate:.1f} mkt/s  "
                  f"eta {(len(markets)-i-1)/rate/60:>5.1f}m", flush=True)
            STATE.write_text(json.dumps(
                {"done": i + 1, "of": len(markets), "fills": n_fill_rows},
                indent=2), encoding="utf-8")

el = time.time() - t0
nf = [v["n_fills"] for v in per_market.values()]
nf_sorted = sorted(nf)
summary = {
    "n_markets": len(markets),
    "seconds": round(el),
    "n_fill_rows_written": n_fill_rows,
    "counters": dict(stats),
    "fills_per_market": {
        "mean": round(sum(nf) / len(nf), 1) if nf else 0,
        "median": nf_sorted[len(nf_sorted) // 2] if nf else 0,
        "p90": nf_sorted[int(len(nf_sorted) * 0.9)] if nf else 0,
        "p99": nf_sorted[int(len(nf_sorted) * 0.99)] if nf else 0,
        "max": max(nf) if nf else 0,
        "zero": sum(1 for v in nf if v == 0),
    },
    "markets_truncated": stats["markets_truncated"],
    "truncation_note": ("markets hitting the 40k/side cap are recorded here; "
                        "their books are incomplete and must be excluded from "
                        "price-impact and depth measurements"),
}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(f"\nwrote {OUT} and {STATS}")
