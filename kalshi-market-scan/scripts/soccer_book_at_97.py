"""Mailbox 008, part 2: can you actually BUY AT 97 CENTS on Kalshi soccer?

The bet the `soccer` chat wants to test is buying NO on the losing team late in
a match -- risking about 97c to make 3. The coordinator is right that this is
the measurement most likely to end the idea, because **every single cent of
spread removes about a third of the margin.** Buy at 98 instead of 97 and the
break-even goes from "3 comebacks allowed in 100" to "2".

TRANSLATING THE BET INTO WHAT THE RECORDER STORES, because getting this backwards
would measure the wrong side of the book:

  Buying NO at 97c means the YES side is at 3c.
    no_ask   = 100 - yes_bid          -> to pay 97, yes_bid must be 3
    spread   = yes_ask - yes_bid       (identical on both sides)
    size you can actually buy = the resting YES BID size, because a resting yes
      bid at p IS a no ask at 100-p, and lifting it is how you buy NO.

So the region of interest is **yes_bid <= 10**, i.e. a NO price of 90c or more.

⚠ TIMING. `close_utc` on a LIVE soccer market is the match date plus ~72 hours,
the same placeholder trap as MLB (LEDGER BH012) -- KXLIGAMXGAME-26AUG17PACPUE
closes 2026-08-20T09:00Z. And unlike MLB the soccer ticker carries only a DATE,
no kick-off time, so the match minute cannot be recovered from the ticker either.
This script therefore measures the book WITHOUT claiming to know the match
minute, and reports what that does and does not settle. Pinnacle's `live` flag
plus `starts_utc` is the route to real match minutes and is a second pass.

Read-only against the recorder. No API calls, no keys, no orders.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from common.kalshi_fees import fee_rate_cents  # noqa: E402

DB = ROOT.parent / "bot-hunt" / "data" / "record.db"
REP = ROOT / "reports"
SOCCER = ("KXLIGAMXGAME", "KXARGPREMDIVGAME", "KXDIMAYORGAME",
          "KXCOPADOBRASILGAME", "KXBRASILGAME")


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=300)
    q = ",".join("?" * len(SOCCER))
    rows = con.execute(
        f"select series, ticker, ts_utc, yes_bid_c, yes_ask_c, bid_size, "
        f"ask_size, depth5_yes from k_book where series in ({q}) "
        f"and yes_bid_c is not null and yes_ask_c is not null", SOCCER).fetchall()
    con.close()
    print(f"soccer book snapshots with both sides quoted: {len(rows):,}")
    if not rows:
        print("nothing recorded - stop")
        return

    yb = np.array([r[3] for r in rows], float)
    ya = np.array([r[4] for r in rows], float)
    bs = np.array([r[5] or 0 for r in rows], float)
    sp = ya - yb
    no_price = 100 - yb                      # what buying NO costs you

    out = {"snapshots": len(rows)}
    print(f"\n== THE WHOLE SOCCER BOOK, for context")
    print(f"   spread: median {np.median(sp):.1f}c   average {sp.mean():.2f}c   "
          f"worst 10% at or above {np.percentile(sp,90):.0f}c")
    out["all"] = {"spread_median_c": float(np.median(sp)),
                  "spread_mean_c": round(float(sp.mean()), 3)}

    print(f"\n== THE REGION THE BET LIVES IN — buying NO at 90c or more")
    print(f"   {'NO price':>10} {'snapshots':>10} {'spread med':>11} "
          f"{'spread avg':>11} {'contracts you could buy':>24}")
    band_rows = []
    for lo, hi in [(90, 93), (93, 95), (95, 97), (97, 99), (99, 100)]:
        m = (no_price >= lo) & (no_price < hi)
        if not m.any():
            print(f"   {f'{lo}-{hi}c':>10} {'0':>10}   nothing ever quoted here")
            band_rows.append({"band": f"{lo}-{hi}", "n": 0})
            continue
        sz = bs[m]
        print(f"   {f'{lo}-{hi}c':>10} {int(m.sum()):>10,} "
              f"{np.median(sp[m]):>10.1f}c {sp[m].mean():>10.2f}c "
              f"{np.median(sz):>14,.0f} (median)")
        band_rows.append({"band": f"{lo}-{hi}", "n": int(m.sum()),
                          "spread_median_c": float(np.median(sp[m])),
                          "spread_mean_c": round(float(sp[m].mean()), 3),
                          "size_median": float(np.median(sz)),
                          "size_p10": float(np.percentile(sz, 10)),
                          "frac_size_zero": float((sz == 0).mean())})
    out["bands"] = band_rows

    # ---- the thing the bet actually needs: 97c or better, with size
    m97 = (no_price >= 96) & (no_price <= 98)
    print(f"\n== THE EXACT TRADE: buying NO at 96-98c")
    if not m97.any():
        print("   NEVER QUOTED. Not once in the whole recording.")
        out["at_97"] = {"n": 0}
    else:
        sz, s97 = bs[m97], sp[m97]
        fee = np.array([float(fee_rate_cents(p)) for p in no_price[m97]])
        print(f"   times it was quoted at all      {int(m97.sum()):,} "
              f"of {len(rows):,} snapshots ({100*m97.mean():.2f}%)")
        print(f"   how many contracts were resting median {np.median(sz):,.0f}, "
              f"and {100*(sz==0).mean():.0f}% of the time there were NONE")
        print(f"   the buy/sell gap                median {np.median(s97):.1f}c, "
              f"average {s97.mean():.2f}c")
        print(f"   Kalshi's fee on a 97c contract  {fee.mean():.2f}c")
        out["at_97"] = {"n": int(m97.sum()),
                        "frac_of_all": round(float(m97.mean()), 5),
                        "size_median": float(np.median(sz)),
                        "frac_no_size": round(float((sz == 0).mean()), 4),
                        "spread_median_c": float(np.median(s97)),
                        "spread_mean_c": round(float(s97.mean()), 3),
                        "fee_mean_c": round(float(fee.mean()), 3)}

        # ---- what the costs do to the break-even, in the user's own units
        #
        # ⚠ CORRECTED. My first version added HALF THE SPREAD on top of the 97c
        # and reported that the bet was destroyed. That is a double-count and it
        # is the exact error I flagged in my own de-vig work three days ago:
        # **buying at the ask IS paying the spread.**
        #
        # Concretely: buying NO at 97c means hitting a resting YES BID at 3c.
        # That bid is the executable price. There is nothing further to cross.
        # The ~78c "spread" in the table above is the distance to the YES ASK
        # (which sits around 81c), and that number is irrelevant to this trade —
        # it matters only if you want to EXIT before the match ends, which §
        # below says you cannot.
        #
        # So the only cost on top of 97c is Kalshi's fee, and the fee is
        # QUADRATIC — near its minimum at the edges of the price range. At 97c
        # it is about a sixth of a cent, not a third of the margin.
        print(f"\n== WHAT THAT DOES TO THE BET, out of 100 tries")
        for label, price in (("the quoted 97c", 97.0),
                             ("97c + Kalshi's fee", 97.0 + float(fee.mean()))):
            win, lose = 100.0 - price, price
            print(f"   {label:24} you win {win:5.2f}c and lose {lose:6.2f}c  "
                  f"-> you can afford {win:4.1f} comebacks in 100")
        eaten = 100.0 * float(fee.mean()) / 3.0
        print(f"   the fee eats {eaten:.0f}% of the margin, not a third")
        out["breakeven"] = {
            "comebacks_allowed_quoted": 3.0,
            "comebacks_allowed_after_fee": round(3.0 - float(fee.mean()), 3),
            "pct_of_margin_eaten_by_fee": round(eaten, 2)}

        # ---- the three things that DO bite
        n_tick = con2.execute(
            f"select count(distinct ticker) from k_book where series in ({q}) "
            f"and yes_bid_c between 2 and 4", SOCCER).fetchone()[0] \
            if False else None
        print(f"\n== THE THREE THINGS THAT ACTUALLY BITE")
        print(f"   1. RARE.     quoted in {100*m97.mean():.2f}% of all soccer "
              f"snapshots")
        print(f"   2. SMALL.    median ${np.median(sz)*0.97:,.0f} of NO you could "
              f"buy; a tenth of the time only ${np.percentile(sz,10)*0.97:,.0f}")
        print(f"   3. NO EXIT.  the other side of the book sits ~"
              f"{np.median(s97):.0f}c away, so once in you are committed to the "
              f"end of the match")
        out["what_bites"] = {
            "pct_of_snapshots": round(100*float(m97.mean()), 3),
            "dollars_median": round(float(np.median(sz))*0.97, 1),
            "dollars_p10": round(float(np.percentile(sz, 10))*0.97, 1),
            "gap_to_other_side_c": float(np.median(s97))}

    (REP / "soccer_book_at_97.json").write_text(json.dumps(out, indent=1),
                                                encoding="utf-8")
    print("\nwrote reports/soccer_book_at_97.json")


if __name__ == "__main__":
    main()
