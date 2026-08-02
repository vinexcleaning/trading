"""Is Kalshi's first-inning price already right? The cheapest real test.

This needs no model and no history backfill. Take every SETTLED KXMLBRFI
market in Kalshi's ~69-day window, read its pre-game price and its actual
result, and ask: when the market says 55%, does a run happen 55% of the time?

Why this is the right first test
  * If the price is well calibrated AND tight, there is little room, and we
    learn that in an hour instead of a week.
  * If it is systematically biased in some price band, that IS the edge, and
    it is visible without building anything.
  * It also gives the base rate, which is the number any model must beat
    before it is interesting at all.

Prices are executable (bid/ask), never the mid alone -- the mid is reported
for calibration but the spread is carried alongside so nothing is overstated.
"""
import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "market-selection", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "common"))
import kalshi_api as K  # noqa: E402
import costbar  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")


def main():
    print("pulling settled KXMLBRFI markets ...", flush=True)
    ms = []
    for status in ("settled",):
        r = K.get("/markets", {"series_ticker": "KXMLBRFI", "status": status,
                               "limit": 1000})
        if r is not None and r.status_code == 200:
            ms += r.json().get("markets", [])
    print(f"  {len(ms)} settled markets")
    if not ms:
        print("none -- cannot run")
        return

    # ------------------------------------------------------------------
    # TWO BUGS FIXED HERE, BOTH MINE, BOTH INFLATING THE RESULT
    #
    # 1. THESE MARKETS TRADE DURING THE FIRST INNING. A game at 4:10 PM EDT
    #    has close_time 20:29 UTC -- about 20 minutes AFTER first pitch. So
    #    "the last quote before close" is a LIVE in-inning price, not a
    #    pre-game one. First pitch is parsed from the ticker instead
    #    (KXMLBRFI-26AUG021610SFSD -> Aug 2, 16:10 ET) and only quotes
    #    STRICTLY BEFORE it are used.
    #
    # 2. REQUIRING ask < 100 SILENTLY SELECTED ON THE OUTCOME. When a run
    #    scores the price jumps to ~99 and the ask goes to 100, so those
    #    quotes were discarded and the last KEPT quote was the one just
    #    before the run. No-run games decay to ~2c and stay quotable. That
    #    manufactures "mid price -> usually YES, low price -> usually NO"
    #    from nothing, and produced a fake +17.25c lean with a 46-point
    #    calibration gap. Pre-game quotes are not subject to this, but the
    #    filter is now recorded rather than applied blindly.
    # ------------------------------------------------------------------
    MON = {m: i + 1 for i, m in enumerate(
        ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
         "NOV", "DEC"])}

    def first_pitch(ticker):
        """KXMLBRFI-26AUG021610SFSD -> first pitch in UTC.
        The embedded time is US Eastern; MLB's season is entirely inside EDT
        (UTC-4), which is checked below against close_time."""
        import re
        mm = re.match(r"KXMLBRFI-(\d\d)([A-Z]{3})(\d\d)(\d{4})", ticker)
        if not mm:
            return None
        yy, mon, dd, hhmm = mm.groups()
        try:
            naive = datetime(2000 + int(yy), MON[mon], int(dd),
                             int(hhmm[:2]), int(hhmm[2:]),
                             tzinfo=timezone.utc)
        except ValueError:
            return None
        return naive + timedelta(hours=4)      # ET -> UTC

    rows = []
    skipped = Counter()
    for i, m in enumerate(ms):
        res = m.get("result")
        if res not in ("yes", "no"):
            skipped["not_yes_no"] += 1
            continue
        ct = m.get("close_time")
        fp = first_pitch(m["ticker"])
        if not ct or fp is None:
            skipped["no_time"] += 1
            continue
        close = datetime.fromisoformat(ct.replace("Z", "+00:00"))
        if not (fp <= close + timedelta(hours=1)):
            skipped["first_pitch_after_close"] += 1
            continue
        # quotes STRICTLY BEFORE first pitch
        rr = K.get(f"/series/KXMLBRFI/markets/{m['ticker']}/candlesticks",
                   {"start_ts": int((fp - timedelta(hours=8)).timestamp()),
                    "end_ts": int(fp.timestamp()), "period_interval": 1})
        if rr is None or rr.status_code != 200:
            skipped["no_candles"] += 1
            continue
        cs = rr.json().get("candlesticks", [])
        last = None
        n_q = 0
        for c in cs:
            if c.get("end_period_ts", 0) > fp.timestamp():
                continue                      # belt and braces
            yb = (c.get("yes_bid") or {}).get("close_dollars")
            ya = (c.get("yes_ask") or {}).get("close_dollars")
            if yb is None or ya is None:
                continue
            b, a = float(yb) * 100, float(ya) * 100
            if b > 0 and a < 100:
                last = (b, a)
                n_q += 1
        if last is None:
            skipped["no_pregame_quote"] += 1
            continue
        b, a = last
        rows.append({
            "ticker": m["ticker"], "close": ct,
            "title": m.get("title"), "yes_sub": m.get("yes_sub_title"),
            "bid": b, "ask": a, "mid": (b + a) / 2, "spread": a - b,
            "quoted_minutes": n_q,
            "won": 1 if res == "yes" else 0,
        })
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(ms)} ... {len(rows)} usable", flush=True)

    json.dump(rows, open(os.path.join(REP, "rfi_calibration.json"), "w"),
              indent=1)
    n = len(rows)
    print(f"\nsettled markets: {len(ms)}")
    print(f"dropped: {dict(skipped)}")
    print(f"usable with a quote STRICTLY BEFORE first pitch: {n}")
    if n < 30:
        print("too few to say anything -- UNTESTABLE")
        return

    base = sum(r["won"] for r in rows) / n
    print(f"\n=== BASE RATE ===")
    print(f"  a run was scored in the first inning in {base:.4f} of {n} markets")
    print(f"  Brier of always predicting the base rate: {base*(1-base):.4f}")
    print("  ^ any model must beat this before it is interesting")

    mids = [r["mid"] for r in rows]
    sps = sorted(r["spread"] for r in rows)
    print(f"\n=== THE MARKET ===")
    print(f"  mid price: median {st.median(mids):.1f}c  "
          f"mean {st.mean(mids):.1f}c  min {min(mids):.0f}  max {max(mids):.0f}")
    print(f"  spread:    median {sps[n//2]:.1f}c  p90 {sps[int(n*.9)]:.1f}c")
    bar = costbar.cost_bar_cents(round(st.median(mids)), sps[n // 2],
                                 "kalshi")["total_c"]
    print(f"  cost bar at the median price and spread: {bar:.2f}c "
          f"=> need a {bar:.2f} pp edge to break even")

    # Brier of the market itself
    bm = sum((r["mid"] / 100 - r["won"]) ** 2 for r in rows) / n
    print(f"\n=== IS THE MARKET BETTER THAN THE BASE RATE? ===")
    print(f"  market Brier     {bm:.4f}")
    print(f"  base-rate Brier  {base*(1-base):.4f}")
    print(f"  difference       {bm - base*(1-base):+.4f}  "
          f"(negative = the market adds information)")

    print(f"\n=== CALIBRATION: when the price says X, how often does it happen? ===")
    print(f"  {'price band':>14s} {'n':>5s} {'avg price':>10s} {'actual':>8s} "
          f"{'gap':>8s}")
    buckets = defaultdict(list)
    for r in rows:
        buckets[min(int(r["mid"] // 10) * 10, 90)].append(r)
    for lo in sorted(buckets):
        sel = buckets[lo]
        if len(sel) < 10:
            continue
        ap = sum(x["mid"] for x in sel) / len(sel)
        ac = sum(x["won"] for x in sel) / len(sel) * 100
        print(f"  {f'{lo}-{lo+10}c':>14s} {len(sel):5d} {ap:10.1f} "
              f"{ac:7.1f}% {ac-ap:+8.1f}")

    over = sum(1 for r in rows if abs(r["mid"] - r["won"] * 100) > 0)
    print(f"\n=== IS THERE A SYSTEMATIC LEAN? ===")
    resid = [r["won"] * 100 - r["mid"] for r in rows]
    m_ = st.mean(resid)
    se = st.pstdev(resid) / (n ** 0.5)
    print(f"  mean (outcome - price) = {m_:+.2f}c  +/- {1.96*se:.2f} (95%)")
    if abs(m_) > 1.96 * se:
        print(f"  ^ SIGNIFICANT lean. Buying YES on every market would have "
              f"returned {m_:+.2f}c per contract gross, before the "
              f"{bar:.2f}c cost bar => net {m_-bar:+.2f}c")
    else:
        print("  ^ no significant lean: the market is unbiased on average")

    print(f"\n=== SPREAD REALITY CHECK ===")
    wide = sum(1 for r in rows if r["spread"] > 5)
    print(f"  markets quoted wider than 5c: {wide} of {n} "
          f"({100*wide/n:.0f}%)")
    print(f"  median minutes with a two-sided quote in the final 6h: "
          f"{st.median([r['quoted_minutes'] for r in rows]):.0f}")


if __name__ == "__main__":
    main()
