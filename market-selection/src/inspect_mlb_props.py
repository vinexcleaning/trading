"""What are Kalshi's MLB derivative prop families, and are they tradeable?

They are the most interesting quadrant on paper: Statcast gives 119 columns per
pitch for free, and ESPN's free odds feed carries only moneyline / spread /
total -- NO props. So props are the one place where rich free data exists and
no free public reference price does.

That cuts both ways and the second half is the part that matters:
  + a private view is at least CONCEIVABLE, because the counterparty is not
    simply copying a number everyone can see
  - there is no cheap benchmark, so validation has to be against realised
    outcomes, which needs n and therefore needs the settlement rate to be high

This inspects structure, tick, fee type and live executable depth so the
shortlist entry rests on measurements rather than on the appeal of the idea.
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
PROPS = ["KXMLBRFI", "KXMLBKS", "KXMLBHR", "KXMLBHIT", "KXMLBTB", "KXMLBHRR",
         "KXMLBTEAMTOTAL", "KXMLBF5", "KXMLBF5TOTAL", "KXMLBF3", "KXMLBF7",
         "KXMLBEXTRAS", "KXMLBTOTAL", "KXMLBSPREAD", "KXMLBGAME"]
MAX_PER = 14


def main():
    out = []
    for s in PROPS:
        r = K.get("/markets", {"series_ticker": s, "status": "open",
                               "limit": 1000})
        if r is None or r.status_code != 200:
            print(f"{s:16s} http {getattr(r,'status_code','ERR')}")
            continue
        ms = r.json().get("markets", [])
        if not ms:
            print(f"{s:16s} no open markets")
            continue
        sr = K.get(f"/series/{s}")
        meta = sr.json().get("series", {}) if sr and sr.status_code == 200 else {}
        ex = ms[0]
        # sample the busiest markets for depth
        ms_sorted = sorted(ms, key=lambda m: -(K.f(m.get("volume_24h_fp")) or 0))
        spreads, bidsz, asksz, dep5, two = [], [], [], [], 0
        n = 0
        for m in ms_sorted[:MAX_PER]:
            yes, no = K.orderbook(m["ticker"])
            yb, ya, bs, a_s = K.touch(yes or [], no or [])
            n += 1
            if yb is None or ya is None:
                continue
            two += 1
            spreads.append(ya - yb)
            bidsz.append(bs)
            asksz.append(a_s)
            d = sum(sz for p, sz in (yes or []) if p >= yb - 5.0)
            d += sum(sz for p, sz in (no or []) if p >= (100.0 - ya) - 5.0)
            dep5.append(d)

        def med(x):
            return round(sorted(x)[len(x) // 2], 1) if x else None
        msp = med(spreads)
        bar = None
        if msp is not None:
            bar = costbar.cost_bar_cents(50, msp, "kalshi")["total_c"]
        rec = {"series": s, "title": meta.get("title"),
               "fee_type": meta.get("fee_type"),
               "price_level_structure": ex.get("price_level_structure"),
               "strike_type": ex.get("strike_type"),
               "open_markets": len(ms),
               "open_events": len({m.get("event_ticker") for m in ms}),
               "sampled": n, "two_sided": two,
               "pct_two_sided": round(100 * two / n, 1) if n else 0,
               "spread_med_c": msp, "bid_sz_med": med(bidsz),
               "ask_sz_med": med(asksz), "depth_5c_med": med(dep5),
               "cost_bar_at_50c": bar,
               "example_title": ex.get("title"),
               "example_yes_sub": ex.get("yes_sub_title"),
               "example_rules": (ex.get("rules_primary") or "")[:150]}
        out.append(rec)
        print(f"{s:16s} mkts={rec['open_markets']:5d} evts={rec['open_events']:4d} "
              f"2sid={rec['pct_two_sided']:5.1f}% spr={str(rec['spread_med_c']):>5s} "
              f"bidSz={str(rec['bid_sz_med']):>9s} d5c={str(rec['depth_5c_med']):>10s} "
              f"bar={str(rec['cost_bar_at_50c']):>6s} {rec['price_level_structure']}")
        print(f"{'':16s} {rec['example_title']!r} / {rec['example_yes_sub']!r}")

    with open(os.path.join(REP, "mlb_props.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("\nwrote reports/mlb_props.json")


if __name__ == "__main__":
    main()
