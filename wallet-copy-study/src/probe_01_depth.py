"""Phase 0 probe, part 2: coverage depth, ordering, filter integrity, fee form.

Answers the questions probe_00 left open:
  - is the subgraph really stale, per its own _meta block?
  - how far back does the public data-api trade tape go, and where is the cap?
  - what is gamma's default ordering (the 2023-sports false-positive trap)?
  - do gamma filters filter at all? (probe_00 says no -- prove it hard)
  - does the fee formula hold on fills I pulled myself?
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]

# Kalshi fee arithmetic has exactly one implementation in this repo.
sys.path.insert(0, str(ROOT.parent / "common"))
from kalshi_fees import fee_rate_cents as kalshi_fee_rate_cents  # noqa: E402
OUT = ROOT / "data" / "probe_01.json"
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
T = 45

ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
DATA = "https://data-api.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"

res = {}


def rec(k, **kw):
    res[k] = kw
    print(f"  {k}: {kw.get('note', '')}", flush=True)


def gql(q, variables=None):
    r = S.post(ORDERBOOK, json={"query": q, "variables": variables or {}}, timeout=T)
    r.raise_for_status()
    b = r.json()
    if "errors" in b:
        raise RuntimeError(b["errors"])
    return b["data"]


def iso(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(ts)))


print("== subgraph _meta (self-reported head) ==")
d = gql("{ _meta { block { number timestamp } hasIndexingErrors deployment } }")
m = d["_meta"]
blk = m["block"]
bt = blk.get("timestamp")
rec("subgraph_meta", block=blk, hasIndexingErrors=m["hasIndexingErrors"],
    deployment=m["deployment"],
    block_iso=iso(bt) if bt else None,
    note=f"head block {blk['number']}"
         + (f" @ {iso(bt)}" if bt else " (no ts field)"))

print("\n== subgraph fill volume by month (is the tail thin?) ==")
# count fills in a window by paging ids; cheap proxy = sample 1 fill at
# month boundaries to confirm continuity rather than count everything.
months = {}
for y, mo in [(2023, 1), (2023, 7), (2024, 1), (2024, 7),
              (2025, 1), (2025, 7), (2026, 1), (2026, 3), (2026, 4)]:
    lo = int(time.mktime(time.struct_time((y, mo, 1, 0, 0, 0, 0, 1, 0))))
    hi = lo + 86400 * 2
    q = ("query($lo:BigInt!,$hi:BigInt!){ orderFilledEvents(first:1000, "
         "where:{timestamp_gte:$lo, timestamp_lt:$hi}){ id } }")
    n = len(gql(q, {"lo": str(lo), "hi": str(hi)})["orderFilledEvents"])
    months[f"{y}-{mo:02d}"] = n
    print(f"    {y}-{mo:02d}-01..02  fills(capped@1000)={n}", flush=True)
rec("subgraph_continuity_2day_samples", counts=months,
    note="1000 = hit page cap, i.e. dense; 0 = no data")

print("\n== data-api /trades: reach and cap ==")
tape = {}
for off in (0, 1000, 5000, 10000, 19000, 20000, 25000, 50000):
    try:
        r = S.get(f"{DATA}/trades", params={"limit": 100, "offset": off}, timeout=T)
        j = r.json() if r.ok else None
        if isinstance(j, list) and j:
            ts = [x["timestamp"] for x in j]
            tape[off] = {"n": len(j), "http": r.status_code,
                         "newest": iso(max(ts)), "oldest": iso(min(ts))}
        else:
            tape[off] = {"n": 0 if isinstance(j, list) else None,
                         "http": r.status_code, "body": r.text[:160]}
    except Exception as e:  # noqa: BLE001
        tape[off] = {"error": repr(e)}
    print(f"    offset={off:>6}  {tape[off]}", flush=True)
rec("data_api_trades_offsets", offsets=tape,
    note="where the public tape stops")

# how old is the oldest reachable trade on the tape?
try:
    r = S.get(f"{DATA}/trades", params={"limit": 1, "offset": 0,
                                        "takerOnly": "false"}, timeout=T)
    j = r.json()
    newest_ts = j[0]["timestamp"] if j else None
except Exception:  # noqa: BLE001
    newest_ts = None
rec("data_api_trades_newest", ts=newest_ts,
    iso=iso(newest_ts) if newest_ts else None,
    note=f"live tape head {iso(newest_ts) if newest_ts else 'n/a'}")

print("\n== gamma default ordering ==")
r = S.get(f"{GAMMA}/markets", params={"limit": 5}, timeout=T)
j = r.json()
rec("gamma_default_order",
    rows=[{"id": x.get("id"), "slug": x.get("slug", "")[:60],
           "createdAt": x.get("createdAt"), "closed": x.get("closed")}
          for x in j],
    note="check createdAt direction -- oldest-first is the 2023-sports trap")

r = S.get(f"{GAMMA}/markets",
          params={"limit": 5, "order": "createdAt", "ascending": "false"}, timeout=T)
j2 = r.json()
rec("gamma_explicit_desc",
    rows=[{"id": x.get("id"), "createdAt": x.get("createdAt")} for x in j2],
    note="does order/ascending work when tag_slug does not?")

print("\n== gamma filter integrity: do filters filter? ==")
base = S.get(f"{GAMMA}/markets", params={"limit": 20}, timeout=T).json()
base_ids = [x.get("id") for x in base]
for name, params in [
    ("tag_slug=nba", {"limit": 20, "tag_slug": "nba"}),
    ("slug_contains=bitcoin", {"limit": 20, "slug_contains": "bitcoin"}),
    ("closed=true", {"limit": 20, "closed": "true"}),
    ("closed=false", {"limit": 20, "closed": "false"}),
    ("active=true", {"limit": 20, "active": "true"}),
    ("liquidity_num_min=1000", {"limit": 20, "liquidity_num_min": 1000}),
]:
    try:
        rr = S.get(f"{GAMMA}/markets", params=params, timeout=T).json()
        ids = [x.get("id") for x in rr]
        same = ids == base_ids
        # does the filter's own semantics hold on the returned rows?
        holds = None
        if name == "closed=true":
            holds = all(x.get("closed") is True for x in rr)
        elif name == "closed=false":
            holds = all(x.get("closed") is False for x in rr)
        elif name == "active=true":
            holds = all(x.get("active") is True for x in rr)
        elif name == "slug_contains=bitcoin":
            holds = all("bitcoin" in (x.get("slug") or "") for x in rr)
        rec(f"gamma_filter[{name}]", n=len(rr),
            identical_to_unfiltered=same, semantics_hold=holds,
            note=("IGNORED (same rows as no filter)" if same
                  else f"filters; semantics_hold={holds}"))
    except Exception as e:  # noqa: BLE001
        rec(f"gamma_filter[{name}]", error=repr(e), note="error")

print("\n== fee formula, verified on fills I pulled myself ==")
# Pull a fresh window of fee-bearing fills and test
#   economic fee/share = (bps/1e4) * min(p, 1-p)
# against the raw on-chain `fee`, deriving side from which leg is collateral.
q = """
query($lo:BigInt!,$hi:BigInt!){
  orderFilledEvents(first:1000, orderBy:timestamp, orderDirection:desc,
    where:{timestamp_gte:$lo, timestamp_lt:$hi}){
      timestamp makerAssetId takerAssetId
      makerAmountFilled takerAmountFilled fee
  }
}"""
hi = 1777374040          # newest fill seen in probe_00
lo = hi - 86400 * 3
rows = gql(q, {"lo": str(lo), "hi": str(hi)})["orderFilledEvents"]

checks = []
for x in rows:
    fee = int(x["fee"])
    if fee == 0:
        continue
    ma, ta = int(x["makerAssetId"]), int(x["takerAssetId"])
    mf, tf = int(x["makerAmountFilled"]), int(x["takerAmountFilled"])
    # collateral leg has assetId 0.
    if ma == 0 and ta != 0:
        # maker gave USDC, taker gave tokens -> taker SOLD tokens for USDC
        shares, usdc, side = tf, mf, "SELL"
    elif ta == 0 and ma != 0:
        # maker gave tokens, taker gave USDC -> taker BOUGHT tokens
        shares, usdc, side = mf, tf, "BUY"
    else:
        continue
    if shares == 0:
        continue
    p = usdc / shares
    if not (0 < p < 1):
        continue
    mn = min(p, 1 - p)
    # predicted raw fee, in the asset the taker receives
    if side == "BUY":
        pred = 0.10 * mn * shares / p        # tokens (6dp)
    else:
        pred = 0.10 * mn * shares            # usdc (6dp)
    if pred <= 0:
        continue
    checks.append({"side": side, "p": round(p, 6),
                   "fee": fee, "pred": pred,
                   "relerr": abs(fee - pred) / pred})

if checks:
    errs = sorted(c["relerr"] for c in checks)
    n = len(errs)
    rec("fee_formula_check", n=n, n_rows_pulled=len(rows),
        window=f"{iso(lo)}..{iso(hi)}",
        median_relerr=errs[n // 2],
        p95_relerr=errs[int(n * 0.95)],
        frac_within_1pct=sum(1 for e in errs if e < 0.01) / n,
        frac_within_0p1pct=sum(1 for e in errs if e < 0.001) / n,
        by_side=dict(Counter(c["side"] for c in checks)),
        worst=sorted(checks, key=lambda c: -c["relerr"])[:3],
        note=f"n={n}, median relerr={errs[n//2]:.2e}, "
             f"{sum(1 for e in errs if e < 0.01)/n:.1%} within 1%")
    # implied bps, solved per fill, to confirm 1000 uniformly
    bps = []
    for c in checks:
        p = c["p"]
        mn = min(p, 1 - p)
        if c["side"] == "BUY":
            b = c["fee"] * p / (mn * (c["pred"] / (0.10 * mn / p))) * 0.10
        else:
            b = c["fee"] / (mn * (c["pred"] / (0.10 * mn))) * 0.10
        bps.append(round(b * 10000))
    rec("fee_implied_bps", dist=dict(Counter(bps).most_common(8)),
        note="expect 1000 dominant")
else:
    rec("fee_formula_check", n=0, note="NO fee-bearing fills in window")

# --- the economic bar the brief asks for, at the named price points ---
bar = {}
for pc in (10, 25, 50, 75, 90):
    p = pc / 100
    kalshi_c = float(kalshi_fee_rate_cents(pc))
    bar[f"{pc}c"] = {
        "poly_fee_cents_per_share": round(0.10 * min(p, 1 - p) * 100, 4),
        "kalshi_fee_cents_per_contract": round(kalshi_c, 4),
        "ratio_poly_over_kalshi": round((0.10 * min(p, 1 - p) * 100) / kalshi_c, 3),
    }
rec("economic_bar", bar=bar, note="one-way taker fee, cents per share")

OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
