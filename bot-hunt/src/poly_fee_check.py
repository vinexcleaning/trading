"""Mailbox 026: does Polymarket's DOCUMENTED sports fee match real sports fills?

⚠ WHY THIS EXISTS. `BH025` established Polymarket's sports fee from their
documentation -- `C x 0.05 x p x (1-p)`, retrieved 2026-08-31 -- and my
cross-venue work used it. **This repo has already proved, once, exactly, that
Polymarket's documentation did not match what it actually charged:**

    C004 (SETTLED): the real fee was 0.10 * min(p, 1-p), resolved from 4,310
    fee-bearing on-chain fills (2026-04-20..27) at median relative error
    0.000000, 100% within 1%. The DOCUMENTED form matched 0.0% of fills.
    Independently reproduced on 5,362 fills (W015).

So a cost bar built on documentation alone repeats the mistake C004 caught. This
checks the current sports markets against BOTH candidate formulas, using the
same public source C004 used -- the Goldsky orderbook subgraph, no account
needed, because Polymarket fills are on-chain.

THE SAMPLE IS SPORTS BY CONSTRUCTION
-------------------------------------
Rather than sampling all fills and hoping some are sports, this takes the CLOB
token ids of **the live MLB run-total markets the paired sampler is already
watching** and asks the subgraph only about those. Every fill returned is
therefore a sports fill on a market we are actively pricing.

WHAT WOULD MAKE THIS INCONCLUSIVE, STATED BEFORE THE ANSWER
------------------------------------------------------------
* the subgraph's indexed range may end before today -- C004 recorded it
  covering 2022-11-21 -> 2026-04-28. **If it has not advanced, no current fill
  exists to check and that is the answer**: the sports fee stays documented-only
  and every output must keep saying so.
* fee-BEARING fills are the only informative ones. A market where every fill
  shows fee 0 tells us makers were involved, not that the fee is zero.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT.parent))
import venues as V  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

GOLDSKY = ("https://api.goldsky.com/api/public/"
           "project_cl6mb8i9h0003e201j6li0diw/subgraphs/"
           "orderbook-subgraph/prod/gn")
UA = {"User-Agent": "bot-hunt-research/1.0"}
USDC = Decimal(10) ** 6
TOKEN = Decimal(10) ** 6
REP = ROOT / "reports"
FIELDS = ("id timestamp makerAssetId takerAssetId "
          "makerAmountFilled takerAmountFilled fee")


def gql(query):
    for attempt in range(4):
        try:
            r = requests.post(GOLDSKY, json={"query": query}, headers=UA,
                              timeout=60)
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 * (attempt + 1))
            continue
        try:
            j = r.json()
        except ValueError:
            time.sleep(1.5)
            continue
        if "errors" in j:
            print(f"   subgraph errors: {str(j['errors'])[:200]}")
            return None
        return j.get("data")
    return None


def sports_tokens():
    """CLOB token ids for the live MLB run-total markets we already price."""
    toks = {}
    for tag in ("mlb", "baseball"):
        r = V.p_gamma("/events", {"tag_slug": tag, "closed": "false",
                                  "active": "true", "limit": 200,
                                  "order": "volume24hr", "ascending": "false"})
        if r is None or r.status_code != 200:
            continue
        for e in (r.json() or []):
            for m in (e.get("markets") or []):
                slug = m.get("slug") or ""
                if not re.match(r"^mlb-[a-z]+-[a-z]+-\d{4}-\d{2}-\d{2}", slug):
                    continue
                try:
                    ids = json.loads(m.get("clobTokenIds") or "[]")
                except (json.JSONDecodeError, TypeError):
                    continue
                for t in ids:
                    toks[str(t)] = slug
    return toks


def decode(ev, tokens):
    """One fill -> price, size, fee per share. Returns None if not one of ours."""
    mk, tk = str(ev.get("makerAssetId")), str(ev.get("takerAssetId"))
    ma = Decimal(ev.get("makerAmountFilled") or 0)
    ta = Decimal(ev.get("takerAmountFilled") or 0)
    fee = Decimal(ev.get("fee") or 0) / USDC
    # exactly one side is USDC (assetId "0"); the other is the outcome token
    if mk == "0" and tk in tokens:
        usdc, shares, slug = ma / USDC, ta / TOKEN, tokens[tk]
    elif tk == "0" and mk in tokens:
        usdc, shares, slug = ta / USDC, ma / TOKEN, tokens[mk]
    else:
        return None
    if shares <= 0:
        return None
    return {"price": float(usdc / shares), "shares": float(shares),
            "fee": float(fee), "slug": slug,
            "ts": int(ev.get("timestamp") or 0)}


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    print("=" * 78)
    print("POLYMARKET SPORTS FEE — documentation vs REAL FILLS")
    print("=" * 78)
    print("C004 proved the docs wrong once (0.0% of 4,310 fills). This checks")
    print("the current sports markets, on the same public on-chain source.\n")

    print("   how far does the subgraph index?")
    d = gql('{ orderFilledEvents(first:1, orderBy:timestamp, orderDirection:desc)'
            ' { timestamp } }')
    if not d or not d.get("orderFilledEvents"):
        # ⚠ MEASURED 2026-09-02, and the reason matters more than the failure.
        # The endpoint replies HTTP 429 with:
        #   "This Polymarket subgraph endpoint is paused and deprecated
        #    following Polymarket's migration to V2 - the data is stale and
        #    incorrect. Stop using it."
        # So C004's SOURCE no longer exists -- and, more importantly, C004's
        # April measurement PREDATES a platform migration. That is a concrete,
        # named reason the old measured formula may no longer describe the
        # venue, which is different from "the docs have been wrong before".
        #
        # The replacements were probed the same minute:
        #   data-api.polymarket.com/trades   HTTP 200, but carries NO fee field
        #   clob.polymarket.com/trades       HTTP 401, needs authentication
        # So the fee CANNOT currently be observed from a free public source.
        print("   ⚠ THE SUBGRAPH C004 USED IS DEPRECATED. Its own error says the")
        print("     data is stale and incorrect after Polymarket's V2 migration.")
        print("     data-api /trades: 200 but no fee field. clob /trades: 401.")
        print("     So the sports fee is NOT VERIFIABLE from free sources today,")
        print("     and C004's April number predates the migration.")
        print("     -> keep BOTH formulas, label UNVERIFIED, use the LARGER for")
        print("        any cost bar, because that is the conservative direction.")
        (REP / "poly_fee_check.json").write_text(json.dumps({
            "verdict": "UNVERIFIABLE from free sources, 2026-09-02",
            "subgraph": "deprecated after Polymarket V2 migration; "
                        "'data is stale and incorrect'",
            "data_api_trades": "HTTP 200, no fee field",
            "clob_trades": "HTTP 401, auth required",
            "consequence": "C004 (0.10*min(p,1-p), April, 4310 fills) predates "
                           "the V2 migration; docs (0.05*p*(1-p), sports, "
                           "2026-08-31) are unverified against fills. Use the "
                           "larger -- C004 -- as the conservative cost bar and "
                           "label it unverified everywhere.",
        }, indent=1), encoding="utf-8")
        return
    newest = int(d["orderFilledEvents"][0]["timestamp"])
    import datetime as dt
    print(f"      newest indexed fill: "
          f"{dt.datetime.fromtimestamp(newest, dt.timezone.utc):%Y-%m-%d %H:%M}Z")
    age_d = (time.time() - newest) / 86400
    print(f"      that is {age_d:.1f} days old")
    if age_d > 3:
        print("   ⚠ THE INDEX HAS NOT ADVANCED TO TODAY. No CURRENT sports fill")
        print("     can be checked from here, which is itself the answer: the")
        print("     sports fee remains DOCUMENTED-ONLY and must stay labelled so.")

    toks = sports_tokens()
    print(f"\n   live MLB market tokens to look for: {len(toks):,}")
    if not toks:
        print("   ⚠ no live tokens; apparatus result.")
        return

    # the subgraph cannot filter on a big id list cheaply, so walk recent
    # windows and keep the fills that belong to our tokens.
    rows, scanned = [], 0
    t_end = newest
    for _ in range(12):
        q = ('{ orderFilledEvents(first:1000, orderBy:timestamp, '
             'orderDirection:desc, where:{timestamp_lt:"%d"}) { %s } }'
             % (t_end, FIELDS))
        d = gql(q)
        evs = (d or {}).get("orderFilledEvents") or []
        if not evs:
            break
        scanned += len(evs)
        for e in evs:
            r = decode(e, toks)
            if r:
                rows.append(r)
        t_end = min(int(e["timestamp"]) for e in evs)
        time.sleep(0.3)
    print(f"   fills scanned: {scanned:,}   of ours: {len(rows):,}")
    fee_bearing = [r for r in rows if r["fee"] > 0]
    print(f"   FEE-BEARING fills on our markets: {len(fee_bearing):,}")
    if not fee_bearing:
        print("\n   ⚠ NO FEE-BEARING SPORTS FILL FOUND. Not evidence the fee is")
        print("   zero, and not evidence either formula is right — it is an")
        print("   absence of evidence, and the fee stays DOCUMENTED-ONLY.")
        out = {"verdict": "UNVERIFIED - no fee-bearing sports fills found",
               "scanned": scanned, "ours": len(rows),
               "newest_indexed_utc": newest}
        (REP / "poly_fee_check.json").write_text(json.dumps(out, indent=1),
                                                 encoding="utf-8")
        return

    print(f"\n   {'price bin':>12} {'n':>5} {'observed':>11} "
          f"{'docs .05p(1-p)':>15} {'C004 .10min':>13}  who fits")
    import numpy as np
    bins = np.linspace(0.02, 0.98, 17)
    fits = {"docs": 0, "c004": 0, "neither": 0}
    for lo, hi in zip(bins, bins[1:]):
        sel = [r for r in fee_bearing if lo <= r["price"] < hi]
        if len(sel) < 3:
            continue
        obs = float(np.median([r["fee"] / r["shares"] for r in sel]))
        pm = (lo + hi) / 2
        docs = 0.05 * pm * (1 - pm)
        c004 = 0.10 * min(pm, 1 - pm)
        best = min(("docs", abs(obs - docs)), ("c004", abs(obs - c004)),
                   key=lambda x: x[1])[0]
        fits[best] += 1
        print(f"   {lo:.2f}-{hi:.2f} {len(sel):>5} {obs:>11.6f} "
              f"{docs:>15.6f} {c004:>13.6f}  {best}")
    print(f"\n   bins better fit by the DOCUMENTED form : {fits['docs']}")
    print(f"   bins better fit by C004's MEASURED form: {fits['c004']}")
    out = {"scanned": scanned, "ours": len(rows), "fee_bearing": len(fee_bearing),
           "bins_fit_docs": fits["docs"], "bins_fit_c004": fits["c004"],
           "newest_indexed_utc": newest}
    (REP / "poly_fee_check.json").write_text(json.dumps(out, indent=1),
                                             encoding="utf-8")
    print("\n   wrote reports/poly_fee_check.json")


if __name__ == "__main__":
    main()
