"""Market-quality measure: do Kalshi's 3-way soccer ladders sum to 100c?

Kalshi lists soccer as three mutually exclusive, collectively exhaustive
markets per game (home / tie / away). That makes an exact internal-consistency
test available for free:

    buy all three YES at the ASK  -> pays exactly $1.00. Cost must be >= 100c.
    sell all three YES at the BID -> pays exactly $1.00. Proceeds must be <= 100c.

This is a MARKET-QUALITY measurement for selection, not a strategy. What it
reports is how tightly a family is arbitraged, which is a direct read on how
much professional attention it receives -- and therefore on how plausible it is
that a private view survives.

LEDGER C014 is the warning attached to this test: 464 "profitable bucket-sum
violations" at 96-97c turned out to be a forward-filled PARTIAL ladder -- 3 of
80 buckets -- and all 464 vanished once a complete contiguous tiling was
required. Here the tiling is complete by construction (exactly 3 outcomes), and
the code REFUSES any event that does not have all three legs quoted two-sided.

Fees are charged per leg, so a 3-leg basket pays 3 entry fees. That is included.
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common"))
import kalshi_api as K  # noqa: E402
import costbar  # noqa: E402

REP = os.path.join(os.path.dirname(__file__), "..", "reports")
SERIES = ["KXLIGAMXGAME", "KXMLSGAME", "KXARGPREMDIVGAME", "KXCOPADOBRASILGAME",
          "KXDIMAYORGAME", "KXPERLIGA1GAME", "KXECULPGAME", "KXURYPDGAME",
          "KXUSLGAME", "KXNWSLGAME", "KXCLUBFGAME", "KXINTLFRIENDLYGAME",
          "KXLEAGUESCUPGAME"]


def main():
    rows = []
    for s in SERIES:
        r = K.get("/markets", {"series_ticker": s, "status": "open",
                               "limit": 1000})
        if r is None or r.status_code != 200:
            print(f"{s}: http {getattr(r,'status_code','ERR')}")
            continue
        by_event = defaultdict(list)
        for m in r.json().get("markets", []):
            by_event[m.get("event_ticker")].append(m)
        n_ev = n_full = 0
        for ev, ms in by_event.items():
            n_ev += 1
            if len(ms) != 3:
                continue
            legs = []
            ok = True
            for m in ms:
                yes, no = K.orderbook(m["ticker"])
                yb, ya, bsz, asz = K.touch(yes or [], no or [])
                if yb is None or ya is None:
                    ok = False
                    break
                legs.append({"ticker": m["ticker"], "side": m.get("yes_sub_title"),
                             "bid": yb, "ask": ya, "bid_sz": bsz, "ask_sz": asz})
            if not ok or len(legs) != 3:
                continue
            n_full += 1
            ask_sum = sum(x["ask"] for x in legs)
            bid_sum = sum(x["bid"] for x in legs)
            # 3 legs, 3 entry fees, held to settlement (no exit fee)
            fee = sum(float(costbar.kalshi_fee_cents(
                int(min(max(round(x["ask"]), 1), 99)))) for x in legs)
            fee_bid = sum(float(costbar.kalshi_fee_cents(
                int(min(max(round(x["bid"]), 1), 99)))) for x in legs)
            rows.append({
                "series": s, "event": ev,
                "ask_sum_c": round(ask_sum, 2), "bid_sum_c": round(bid_sum, 2),
                "overround_ask_c": round(ask_sum - 100.0, 2),
                "underround_bid_c": round(100.0 - bid_sum, 2),
                "buy_all_net_c": round(100.0 - ask_sum - fee, 2),
                "sell_all_net_c": round(bid_sum - 100.0 - fee_bid, 2),
                "min_leg_sz": min(x["ask_sz"] for x in legs),
                "legs": legs,
            })
        print(f"{s:24s} events={n_ev:4d} fully-quoted 3-way={n_full:4d}")

    with open(os.path.join(REP, "threeway_sum.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    if not rows:
        print("no fully-quoted 3-way events")
        return

    def q(xs, p):
        xs = sorted(xs)
        return round(xs[min(int(len(xs) * p), len(xs) - 1)], 2)

    oa = [r["overround_ask_c"] for r in rows]
    ub = [r["underround_bid_c"] for r in rows]
    n = len(rows)
    print(f"\nunit of observation: one fully-quoted 3-way soccer event, n={n}")
    print(f"ASK-side overround (sum of 3 asks - 100c):")
    print(f"  min {min(oa):+.2f}  p10 {q(oa,.1):+.2f}  median {q(oa,.5):+.2f}  "
          f"p90 {q(oa,.9):+.2f}  max {max(oa):+.2f}")
    print(f"BID-side underround (100c - sum of 3 bids):")
    print(f"  min {min(ub):+.2f}  median {q(ub,.5):+.2f}  max {max(ub):+.2f}")
    buy = [r for r in rows if r["buy_all_net_c"] > 0]
    sell = [r for r in rows if r["sell_all_net_c"] > 0]
    print(f"\nevents where buying all three at the ask is NET PROFITABLE "
          f"after 3 fees: {len(buy)} of {n}")
    print(f"events where selling all three at the bid is NET PROFITABLE: "
          f"{len(sell)} of {n}")
    neg = [r for r in rows if r["overround_ask_c"] < 0]
    print(f"events with a GROSS ask-sum below 100c (before fees): "
          f"{len(neg)} of {n}")
    for r in sorted(rows, key=lambda r: r["overround_ask_c"])[:8]:
        print(f"  {r['series'][:22]:22s} {r['event'][:30]:30s} "
              f"askSum={r['ask_sum_c']:7.2f} bidSum={r['bid_sum_c']:7.2f} "
              f"buyNet={r['buy_all_net_c']:+7.2f} minSz={r['min_leg_sz']}")
    print("\nwrote reports/threeway_sum.json")


if __name__ == "__main__":
    main()
