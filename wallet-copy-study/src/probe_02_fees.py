"""Phase 0 probe, part 3: the fee formula, derived rather than assumed.

probe_01 got median relative error 0.96 because it inverted the side. In
`OrderFilled(orderHash, maker, taker, makerAssetId, takerAssetId,
makerAmountFilled, takerAmountFilled, fee)` the amounts describe what the
MAKER gave and received, and `fee` is charged on the maker's leg:

    makerAssetId == 0  -> maker paid USDC, received tokens  -> maker BOUGHT
    takerAssetId == 0  -> maker paid tokens, received USDC  -> maker SOLD

The fee is taken in whichever asset the maker RECEIVES, so a buy's fee is
denominated in outcome tokens and a sell's in USDC. Both legs are 6-decimal
integers, so predictions are computed in raw integer units throughout.

Candidate forms tested head-to-head rather than assumed:
    A  economic = rate * min(p, 1-p)          [claimed, rate 0.10]
    B  published = 0.07 * p * (1-p)
Also: when did fees switch on at all? 2022 fills carry fee = 0.
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
OUT = ROOT / "data" / "probe_02_fees.json"
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
res = {}


def rec(k, **kw):
    res[k] = kw
    print(f"  {k}: {kw.get('note', '')}", flush=True)


def gql(q, v=None):
    r = S.post(ORDERBOOK, json={"query": q, "variables": v or {}}, timeout=60)
    r.raise_for_status()
    b = r.json()
    if "errors" in b:
        raise RuntimeError(b["errors"])
    return b["data"]


def iso(ts):
    return time.strftime("%Y-%m-%d", time.gmtime(int(ts)))


Q = """
query($lo:BigInt!,$hi:BigInt!,$skip:Int!){
  orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp, orderDirection:asc,
    where:{timestamp_gte:$lo, timestamp_lt:$hi}){
      timestamp makerAssetId takerAssetId
      makerAmountFilled takerAmountFilled fee
  }
}"""


def decode(x):
    """-> (side, shares_raw, usdc_raw, p) from the MAKER's perspective."""
    ma, ta = int(x["makerAssetId"]), int(x["takerAssetId"])
    mf, tf = int(x["makerAmountFilled"]), int(x["takerAmountFilled"])
    if ma == 0 and ta != 0:
        side, shares, usdc = "BUY", tf, mf     # paid USDC, got tokens
    elif ta == 0 and ma != 0:
        side, shares, usdc = "SELL", mf, tf    # paid tokens, got USDC
    else:
        return None
    if shares <= 0 or usdc <= 0:
        return None
    p = usdc / shares
    if not (0.0 < p < 1.0):
        return None
    return side, shares, usdc, p


def pred_A(side, shares, p, rate=0.10):
    """Economic form: rate * min(p,1-p) per share, taken in the received asset."""
    mn = min(p, 1 - p)
    return rate * mn * shares / p if side == "BUY" else rate * mn * shares


def pred_B(side, shares, p, rate=0.07):
    """Published form: rate * p * (1-p) per share, same denomination rule."""
    q = rate * p * (1 - p)
    return q * shares / p if side == "BUY" else q * shares


def fetch(lo, hi, pages=3):
    out = []
    for i in range(pages):
        rows = gql(Q, {"lo": str(lo), "hi": str(hi), "skip": i * 1000})["orderFilledEvents"]
        out += rows
        if len(rows) < 1000:
            break
    return out


# ------------------------------------------------ when did fees switch on?
print("== fee switch-on: fraction of fills with fee != 0, by quarter ==")
timeline = {}
for y in (2022, 2023, 2024, 2025, 2026):
    for mo in (1, 4, 7, 10):
        if (y, mo) < (2022, 10) or (y, mo) > (2026, 4):
            continue
        lo = int(time.mktime(time.struct_time((y, mo, 1, 0, 0, 0, 0, 1, 0))))
        rows = fetch(lo, lo + 86400, pages=1)
        if not rows:
            timeline[f"{y}-{mo:02d}"] = {"n": 0}
            continue
        nz = sum(1 for r_ in rows if int(r_["fee"]) != 0)
        timeline[f"{y}-{mo:02d}"] = {"n": len(rows), "n_fee_nonzero": nz,
                                     "frac": round(nz / len(rows), 4)}
        print(f"    {y}-{mo:02d}  n={len(rows):>5}  fee!=0: {nz/len(rows):>7.2%}", flush=True)
rec("fee_switch_on", timeline=timeline,
    note="fees are not charged for most of the sample's history")

# ------------------------------------------------------- formula bake-off
print("\n== formula bake-off on fee-bearing fills ==")
HI = 1777374040
LO = HI - 86400 * 5
rows = fetch(LO, HI, pages=6)
A, B, bpsd, by_side, bad = [], [], [], Counter(), []
for x in rows:
    fee = int(x["fee"])
    if fee == 0:
        continue
    dec = decode(x)
    if dec is None:
        continue
    side, shares, usdc, p = dec
    a, b = pred_A(side, shares, p), pred_B(side, shares, p)
    if a <= 0 or b <= 0:
        continue
    ea, eb = abs(fee - a) / a, abs(fee - b) / b
    A.append(ea)
    B.append(eb)
    by_side[side] += 1
    # implied rate under form A, inverted per fill
    mn = min(p, 1 - p)
    denom = (mn * shares / p) if side == "BUY" else (mn * shares)
    bpsd.append(round(fee / denom * 10000))
    if ea > 0.01:
        bad.append({"side": side, "p": round(p, 4), "shares": shares,
                    "fee": fee, "predA": round(a, 2), "relerr": round(ea, 4)})

if A:
    A.sort(); B.sort()
    n = len(A)
    rec("bakeoff", n=n, window=f"{iso(LO)}..{iso(HI)}", by_side=dict(by_side),
        A_median_relerr=A[n // 2], A_frac_within_1pct=sum(1 for e in A if e < .01) / n,
        A_frac_within_0p1pct=sum(1 for e in A if e < .001) / n,
        B_median_relerr=B[n // 2], B_frac_within_1pct=sum(1 for e in B if e < .01) / n,
        note=f"n={n} | A(0.10*min(p,1-p)): median {A[n//2]:.2e}, "
             f"{sum(1 for e in A if e < .01)/n:.1%} within 1% | "
             f"B(0.07*p*(1-p)): median {B[n//2]:.2e}, "
             f"{sum(1 for e in B if e < .01)/n:.1%} within 1%")
    rec("implied_bps", dist=dict(Counter(bpsd).most_common(10)),
        note=f"modal implied bps = {Counter(bpsd).most_common(1)[0]}")
    rec("bakeoff_misfits", n_bad=len(bad), examples=bad[:8],
        note=f"{len(bad)}/{n} fills miss form A by >1%")
else:
    rec("bakeoff", n=0, note="no fee-bearing fills decoded")

# ---------------------------------------------------------- economic bar
bar = {}
for pc in (10, 25, 50, 75, 90):
    p = pc / 100
    poly = 0.10 * min(p, 1 - p)
    kal = float(kalshi_fee_rate_cents(pc)) / 100.0
    bar[f"{pc}c"] = {
        "poly_cents_per_share_one_way": round(poly * 100, 4),
        "poly_cents_round_trip": round(poly * 200, 4),
        "poly_cents_hold_to_settlement": round(poly * 100, 4),
        "kalshi_cents_per_contract": round(kal * 100, 4),
        "poly_over_kalshi": round(poly / kal, 3),
        "edge_pp_needed_to_break_even_hold": round(poly * 100, 4),
    }
rec("economic_bar", bar=bar,
    note="one-way taker fee in cents/share; settlement pays no exit fee")

OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
