"""TASK 1b: verify the exact on-chain fee formula.

The pooled scan showed fee/share is FLAT at 0.100000 for p < 0.5 and DECLINING
above it. That asymmetry is the signature of the Polymarket CTF exchange's
side-dependent fee, not of the published 0.07*p*(1-p):

    BUY  (taker receives tokens, fee taken in TOKENS):
        fee_tokens = (bps/10000) * min(p, 1-p) * shares / p
    SELL (taker receives collateral, fee taken in COLLATERAL):
        fee_usdc   = (bps/10000) * min(p, 1-p) * shares

For p < 0.5 the BUY branch collapses to (bps/10000)*shares -- exactly the
observed flat 0.10 at bps=1000. Test this to machine precision.

ECONOMIC cost per share (what actually matters) = (bps/10000) * min(p, 1-p)
dollars, on BOTH branches.
"""
import json
import time
from collections import Counter

import numpy as np
import requests

UA = {"User-Agent": "research-readonly/0.1"}
GOLDSKY = ("https://api.goldsky.com/api/public/"
           "project_cl6mb8i9h0003e201j6li0diw/subgraphs/"
           "orderbook-subgraph/prod/gn")
FIELDS = ("timestamp makerAssetId takerAssetId makerAmountFilled "
          "takerAmountFilled fee")


def gql(q):
    for a in range(5):
        try:
            r = requests.post(GOLDSKY, json={"query": q}, headers=UA,
                              timeout=60)
            j = r.json()
        except Exception:
            time.sleep(2 * (a + 1))
            continue
        if "errors" in j:
            return None
        return j.get("data")
    return None


def fetch(ts, n=1000):
    d = gql('{ orderFilledEvents(first:%d, orderBy:timestamp, '
            'orderDirection:asc, where:{timestamp_gt:"%d"}) { %s } }'
            % (n, ts, FIELDS))
    return (d or {}).get("orderFilledEvents", []) or []


def main():
    rows = []
    for ts in [1777100000, 1777200000, 1777300000, 1776900000, 1776700000]:
        rows.extend(fetch(ts))
        time.sleep(0.25)
    print(f"pulled {len(rows)} fills")

    recs = []
    for e in rows:
        mid, tid = e["makerAssetId"], e["takerAssetId"]
        ma, ta, fee = (int(e["makerAmountFilled"]),
                       int(e["takerAmountFilled"]), int(e["fee"]))
        if fee == 0:
            continue
        if mid == "0" and tid != "0":
            usdc, tokens, side = ma, ta, "BUY"      # maker paid USDC
        elif tid == "0" and mid != "0":
            usdc, tokens, side = ta, ma, "SELL"     # maker gave tokens
        else:
            continue
        if tokens <= 0 or usdc <= 0:
            continue
        p = usdc / tokens
        if not (0.001 < p < 0.999):
            continue
        shares = tokens / 1e6
        recs.append({"ts": int(e["timestamp"]), "side": side, "p": p,
                     "shares": shares, "fee": fee / 1e6})

    print(f"{len(recs)} fee-bearing, decodable fills")
    print(f"  sides: {dict(Counter(r['side'] for r in recs))}")
    print(f"  dates: "
          f"{time.strftime('%Y-%m-%d', time.gmtime(min(r['ts'] for r in recs)))}"
          f" -> "
          f"{time.strftime('%Y-%m-%d', time.gmtime(max(r['ts'] for r in recs)))}")

    for bps in [1000]:
        rate = bps / 10000.0
        print(f"\n{'='*94}")
        print(f"CANDIDATE: side-dependent CTF formula at feeRateBps={bps} "
              f"(rate={rate})")
        print(f"{'='*94}")
        for side in ["BUY", "SELL"]:
            sel = [r for r in recs if r["side"] == side]
            if not sel:
                continue
            errs = []
            for r in sel:
                m = min(r["p"], 1 - r["p"])
                pred = (rate * m * r["shares"] / r["p"] if side == "BUY"
                        else rate * m * r["shares"])
                if pred > 0:
                    errs.append(abs(r["fee"] - pred) / pred)
            errs = np.array(errs)
            print(f"  {side:<5} n={len(sel):>5}  "
                  f"median rel.err={np.median(errs):.6f}  "
                  f"within 0.1%={100*np.mean(errs<0.001):5.1f}%  "
                  f"within 1%={100*np.mean(errs<0.01):5.1f}%")

    # economic cost per share, both branches -> rate * min(p,1-p)
    print(f"\n{'='*94}")
    print("ECONOMIC cost per share in DOLLARS, observed vs candidates")
    print(f"{'='*94}")
    print(f"  {'price bin':>12} {'n':>5} {'observed $':>12} "
          f"{'0.10*min(p,1-p)':>17} {'0.07*p*(1-p)':>14} {'obs/published':>14}")
    bins = np.linspace(0.02, 0.98, 25)
    for lo, hi in zip(bins, bins[1:]):
        sel = [r for r in recs if lo <= r["p"] < hi]
        if len(sel) < 5:
            continue
        # dollar value of the fee: BUY fee is in tokens (worth p each),
        # SELL fee is already in USDC
        vals = [(r["fee"] * r["p"] if r["side"] == "BUY" else r["fee"])
                / r["shares"] for r in sel]
        obs = float(np.median(vals))
        pm = (lo + hi) / 2
        cand = 0.10 * min(pm, 1 - pm)
        pub = 0.07 * pm * (1 - pm)
        print(f"  {lo:.2f}-{hi:.2f}   {len(sel):>5} {obs:>12.6f} "
              f"{cand:>17.6f} {pub:>14.6f} {obs/pub if pub else 0:>14.2f}")

    with open(r"C:\Users\gianf\crypto\reports\poly_fee_verify.json", "w") as f:
        json.dump({"n": len(recs)}, f, indent=2)


if __name__ == "__main__":
    main()
