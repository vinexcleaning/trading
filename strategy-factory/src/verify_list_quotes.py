"""DOES THE KALSHI LIST ENDPOINT CARRY A REAL QUOTE? Measured, not assumed.

`bot-hunt/src/venues.py` states in its module docstring, as an inherited trap:

    "Kalshi list endpoints null out bid/ask; quotes only come off the
     per-market orderbook endpoint. (Independently reported by a Reddit
     cross-venue bot author, and consistent with the field-name policy above.)"

If that is still true, widening the recorder costs one HTTP request per market
and the whole exchange is out of reach: 835,422 open markets at 0.12 s is 28
hours for one sweep.

If it is false, `/markets?limit=1000` returns 1,000 quotes in one request and
the whole exchange is roughly 100 seconds.

The difference between those two worlds is the entire Stage 1 design, so it
gets measured rather than believed. GUARDS #13: a 200 is not a result.

METHOD. Sample markets across many series. For each, read the list quote and
then immediately read the per-market orderbook, and compare. Agreement is
judged at 0.51 c tolerance because Kalshi returns dollar strings that float to
55.00000000000001 c, and because a live market genuinely moves between two
requests made ~200 ms apart. A disagreement larger than one tick is a real
disagreement; anything smaller cannot be distinguished from latency.

WHAT WOULD MAKE ME DROP THE CLAIM: below 90% agreement at one tick, or any
series where the list side is systematically absent while the book has one.
Reported per series, because "on average" would hide a family-shaped failure -
which is exactly how the `orderbook` vs `orderbook_fp` bug survived six days
across three scripts.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "bot-hunt" / "src"))
import venues as V  # noqa: E402

TOL_C = 0.51   # one tick, minus float noise


def close(a, b) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= TOL_C


def check_series(series: str, n_markets: int):
    r = V.k_get("/markets", {"status": "open", "limit": 200,
                             "series_ticker": series})
    if r is None or r.status_code != 200:
        return None
    ms = (r.json() or {}).get("markets") or []
    if not ms:
        return None
    out = {"series": series, "listed": len(ms), "checked": 0,
           "bid_ok": 0, "ask_ok": 0, "both_ok": 0,
           "list_quoted": 0, "book_quoted": 0,
           "list_blank_book_has": 0, "worst": 0.0}
    for m in ms[:n_markets]:
        # Kalshi returns 0.0000 for "no bid" and 1.0000 for "no ask" on the
        # list side, where the orderbook returns an absent level. Normalise
        # both to None so an empty book is not scored as a 0-cent bid.
        lb = V.fnum(m.get("yes_bid_dollars"))
        la = V.fnum(m.get("yes_ask_dollars"))
        lb = None if lb in (None, 0.0) else lb * 100.0
        la = None if la in (None, 1.0) else la * 100.0
        y, n = V.k_orderbook(m["ticker"])
        if y is None and n is None:
            continue
        ob, oa, _, _ = V.k_touch(y, n)
        out["checked"] += 1
        out["list_quoted"] += int(lb is not None or la is not None)
        out["book_quoted"] += int(ob is not None or oa is not None)
        b_ok, a_ok = close(lb, ob), close(la, oa)
        out["bid_ok"] += b_ok
        out["ask_ok"] += a_ok
        out["both_ok"] += (b_ok and a_ok)
        if (lb is None and la is None) and (ob is not None or oa is not None):
            out["list_blank_book_has"] += 1
        for x, z in ((lb, ob), (la, oa)):
            if x is not None and z is not None:
                out["worst"] = max(out["worst"], abs(x - z))
    return out if out["checked"] else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-series", type=int, default=8)
    ap.add_argument("--series", default="")
    args = ap.parse_args()
    if args.series:
        sers = [s.strip() for s in args.series.split(",") if s.strip()]
    else:
        # Deliberately spread across categories AND across liquidity, because
        # a check that only looks at busy sports markets would prove nothing
        # about the long tail this is being used to record.
        sers = ["KXMLBGAME", "KXMLBTOTAL", "KXATPMATCH", "KXWTAMATCH",
                "KXITFMATCH", "KXCS2GAME", "KXLOLGAME", "KXNFLGAME",
                "KXNFLSPREAD", "KXHIGHNY", "KXHIGHCHI", "KXBTCD", "KXETHD",
                "KXSOLD", "KXNASDAQ100U", "KXDJI", "KXCPIYOY", "KXFED",
                "KXHOUSERACE", "KXROTTENTOMATOES", "KXOSCARBP",
                "KXMVECROSSCATEGORY", "KXMVESPORTSMULTIGAMEEXTENDED"]
    tot = {k: 0 for k in ("checked", "bid_ok", "ask_ok", "both_ok",
                          "list_quoted", "book_quoted", "list_blank_book_has")}
    worst = 0.0
    print("%-30s %6s %7s %7s %7s %8s %8s %7s"
          % ("series", "check", "bid ok", "ask ok", "both", "listQ", "bookQ",
             "worst"))
    for s in sers:
        o = check_series(s, args.per_series)
        if not o:
            print("%-30s   (no open market or no book)" % s)
            continue
        for k in tot:
            tot[k] += o[k]
        worst = max(worst, o["worst"])
        print("%-30s %6d %7d %7d %7d %8d %8d %7.2f"
              % (s, o["checked"], o["bid_ok"], o["ask_ok"], o["both_ok"],
                 o["list_quoted"], o["book_quoted"], o["worst"]))
    c = max(tot["checked"], 1)
    print()
    print("TOTAL checked %d markets across %d series" % (tot["checked"], len(sers)))
    print("  bid agrees within %.2fc : %d (%.1f%%)"
          % (TOL_C, tot["bid_ok"], 100.0 * tot["bid_ok"] / c))
    print("  ask agrees within %.2fc : %d (%.1f%%)"
          % (TOL_C, tot["ask_ok"], 100.0 * tot["ask_ok"] / c))
    print("  BOTH sides agree        : %d (%.1f%%)"
          % (tot["both_ok"], 100.0 * tot["both_ok"] / c))
    print("  list blank while book quoted: %d  <-- the failure mode that "
          "would kill the idea" % tot["list_blank_book_has"])
    print("  worst disagreement seen : %.2f cents" % worst)


if __name__ == "__main__":
    main()
