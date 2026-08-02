"""Can the subgraph pull a wallet's complete fill history directly?

Design problem this solves: the CLOB enumeration is past 1,000,000 markets, so a
4,000-market sample observes roughly 0.4% of any wallet's activity. Persistence
testing needs wallets with enough INDEPENDENT MARKETS in each of two periods,
and a market-drawn sample cannot deliver that -- a wallet trading 1,000 markets
would appear in ~4 of them.

The fix is a wallet panel: draw wallets at random (never on performance, which
would be circular), then pull each one's complete history. That requires the
subgraph to filter on `maker`. Tested here, along with how expensive it is.

The market panel is still needed for the Phase 3 naive benchmark, where the
sampling unit genuinely is the market.
"""
import json
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probe_09_bywallet.json"
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
res = {}


def rec(k, **kw):
    res[k] = kw
    print(f"  {k}: {kw.get('note', '')}", flush=True)


def gql(q, v=None, timeout=120):
    r = S.post(ORDERBOOK, json={"query": q, "variables": v or {}}, timeout=timeout)
    r.raise_for_status()
    b = r.json()
    if "errors" in b:
        raise RuntimeError(str(b["errors"])[:400])
    return b["data"]


def iso(ts):
    return time.strftime("%Y-%m-%d", time.gmtime(int(ts)))


# --- get some real wallets from a mid-history window
LO = 1750000000
d = gql("""query($lo:BigInt!,$hi:BigInt!){
  orderFilledEvents(first:400, orderBy:timestamp, orderDirection:asc,
    where:{timestamp_gte:$lo, timestamp_lt:$hi}){ maker } }""",
        {"lo": str(LO), "hi": str(LO + 600)})
cands = [w for w, _ in Counter(str(x["maker"]).lower()
                               for x in d["orderFilledEvents"]).most_common(30)]
rec("candidates", n=len(cands), sample=cands[:4],
    note=f"{len(cands)} wallets from a 10-minute window")

print("\n== does `maker` filter work, and is it fast? ==")
Q = """
query($w:String!,$skip:Int!){
  rows: orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp,
      orderDirection:asc, where:{maker:$w}){
    id timestamp makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee }
}"""
ok = Counter()
timings = []
for w in cands[:6]:
    t0 = time.time()
    try:
        rows = gql(Q, {"w": w, "skip": 0})["rows"]
        el = time.time() - t0
        timings.append(el)
        ok["ok"] += 1
        ts = [int(r_["timestamp"]) for r_ in rows]
        # verify the filter actually filtered
        print(f"    {w[:14]}… n={len(rows):>5} {el:>5.2f}s "
              f"{iso(min(ts))}..{iso(max(ts))}" if ts else f"    {w[:14]}… empty",
              flush=True)
    except Exception as e:  # noqa: BLE001
        ok["error"] += 1
        print(f"    {w[:14]}… ERROR {str(e)[:120]}", flush=True)
rec("maker_filter", counts=dict(ok),
    mean_seconds=round(sum(timings) / len(timings), 2) if timings else None,
    note=f"{dict(ok)}; mean {round(sum(timings)/len(timings),2) if timings else '?'}s/page")

print("\n== full history depth for one wallet (paging cost) ==")
w = cands[0]
t0, tot, pages = time.time(), 0, 0
first_ts = last_ts = None
while pages < 60:
    rows = gql(Q, {"w": w, "skip": pages * 1000})["rows"]
    if not rows:
        break
    tot += len(rows)
    ts = [int(r_["timestamp"]) for r_ in rows]
    first_ts = first_ts or min(ts)
    last_ts = max(ts)
    pages += 1
    if len(rows) < 1000:
        break
el = time.time() - t0
rec("one_wallet_full_history", wallet=w, n_fills=tot, pages=pages,
    seconds=round(el, 1),
    range=[iso(first_ts), iso(last_ts)] if first_ts else None,
    note=f"{tot} fills in {pages} pages / {el:.1f}s "
         f"({iso(first_ts) if first_ts else '?'}..{iso(last_ts) if last_ts else '?'})")

print("\n== maker_in: can we batch several wallets per query? ==")
Q_IN = """
query($ws:[String!],$skip:Int!){
  rows: orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp,
      orderDirection:asc, where:{maker_in:$ws}){
    id timestamp maker makerAssetId takerAssetId }
}"""
try:
    t0 = time.time()
    rows = gql(Q_IN, {"ws": cands[:10], "skip": 0})["rows"]
    got = Counter(str(r_["maker"]).lower() for r_ in rows)
    stray = set(got) - set(cands[:10])
    rec("maker_in_batch", ok=True, n=len(rows), seconds=round(time.time() - t0, 2),
        n_distinct_makers_returned=len(got),
        stray_addresses=len(stray),
        note=f"{len(rows)} rows, {len(got)} distinct makers, "
             f"{len(stray)} stray (must be 0)")
except Exception as e:  # noqa: BLE001
    rec("maker_in_batch", ok=False, error=str(e)[:300], note="maker_in REJECTED")

print("\n== how many distinct wallets exist? (sample-based) ==")
# distinct makers seen in fixed windows, to size the wallet population
counts = {}
for label, lo, span in [("2024-06 1h", 1717200000, 3600),
                        ("2025-06 1h", 1748736000, 3600),
                        ("2026-03 1h", 1772496000, 3600)]:
    try:
        rows = gql("""query($lo:BigInt!,$hi:BigInt!){
          orderFilledEvents(first:1000, orderBy:timestamp, orderDirection:asc,
            where:{timestamp_gte:$lo, timestamp_lt:$hi}){ maker } }""",
                   {"lo": str(lo), "hi": str(lo + span)})["orderFilledEvents"]
        c = Counter(str(x["maker"]).lower() for x in rows)
        counts[label] = {"n_fills_capped": len(rows), "n_distinct_makers": len(c),
                         "top_share": round(c.most_common(1)[0][1] / len(rows), 3) if rows else None}
    except Exception as e:  # noqa: BLE001
        counts[label] = {"error": str(e)[:120]}
    print(f"    {label}: {counts[label]}", flush=True)
rec("wallet_population", windows=counts,
    note="distinct makers per 1000-fill window")

OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
