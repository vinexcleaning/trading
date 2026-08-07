"""What MLB markets does Kalshi actually list, and what do they cost to trade?

Answers the SCOREBOARD question directly: do KXMLBTOTAL (over/under, 249
tickers recorded) and KXMLBRFI (first inning, 71) beat KXMLBGAME (moneyline)
as the target for a forward paper test?

The comparison is on four axes, all measured here rather than quoted:
  1. events per day        -> how fast a forward test accumulates power
  2. cost to cross         -> spread at the touch + the Kalshi taker fee
  3. depth at the touch    -> can a $5-$25 paper ticket even be filled
  4. reference price       -> is there a free sharp line for this market type

Axis 4 is the one that decides it, and it points the opposite way to axis 2.
Everything here is a PUBLIC UNAUTHENTICATED Kalshi endpoint. No keys.

Two traps this repo has already paid for and that are avoided here:
  - `volume` / `yes_bid` / `yes_ask` are None on live markets; the live fields
    are `volume_fp`, `yes_bid_dollars`, `yes_ask_dollars` (LEDGER C024).
  - `close_time` on a LIVE Kalshi MLB market is game start + exactly 72 h.
    Start is derived from the ticker, never from close_time.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "trading-research/1.0 (personal research; contact via github)"}
OUT = Path(__file__).resolve().parent.parent / "reports"

SERIES = ["KXMLBGAME", "KXMLBTOTAL", "KXMLBRFI", "KXMLBSPREAD",
          "KXMLBF5TOTAL", "KXMLBF5", "KXMLBF5SPREAD"]

# KXMLBGAME-26AUG06DETKC-DET  ->  2026-08-06
TICKER_DATE = re.compile(r"-(\d{2})([A-Z]{3})(\d{2})", re.I)
MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}


def get(path, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
    url = f"{BASE}{path}" + (f"?{q}" if q else "")
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise
        except Exception:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise


def all_markets(series, status="open"):
    out, cursor = [], None
    while True:
        d = get("/markets", series_ticker=series, status=status,
                limit=1000, cursor=cursor)
        out += d.get("markets", [])
        cursor = d.get("cursor")
        if not cursor:
            break
        time.sleep(0.25)
    return out


def cents(v):
    """Kalshi's *_dollars fields are decimal-dollar strings. -> int cents."""
    if v is None:
        return None
    try:
        return int(round(float(v) * 100))
    except (TypeError, ValueError):
        return None


def game_date(ticker):
    m = TICKER_DATE.search(ticker)
    if not m:
        return None
    dd, mon, yy = m.group(1), m.group(2).upper(), m.group(3)
    if mon not in MONTHS:
        return None
    try:
        return f"20{yy}-{MONTHS[mon]:02d}-{int(dd):02d}"
    except ValueError:
        return None


def taker_fee_cents(price_c, contracts=1):
    """Kalshi quadratic taker fee, via the single shared implementation.

    GUARDS #6 / common/tests/test_no_fee_reimplementation.py: this file must
    never contain the arithmetic itself. It delegates.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from common.kalshi_fees import fee_order_cents
    return float(fee_order_cents(price_c, contracts))


def census():
    rows = []
    per_series = {}
    for s in SERIES:
        try:
            mk = all_markets(s)
        except Exception as e:
            print(f"{s}: FAILED {e}")
            continue
        per_series[s] = mk
        spreads, depths, mids = [], [], []
        events, dates = set(), set()
        two_sided = 0
        for m in mk:
            bid = cents(m.get("yes_bid_dollars"))
            ask = cents(m.get("yes_ask_dollars"))
            events.add(m.get("event_ticker"))
            d = game_date(m.get("ticker", ""))
            if d:
                dates.add(d)
            if bid is None or ask is None or bid <= 0 or ask >= 100:
                continue
            two_sided += 1
            spreads.append(ask - bid)
            mids.append((ask + bid) / 2)
            # depth at touch: the API exposes size only via /orderbook
        rows.append({
            "series": s,
            "open_markets": len(mk),
            "events": len(events),
            "distinct_game_dates": len(dates),
            "two_sided": two_sided,
            "two_sided_pct": round(100 * two_sided / max(1, len(mk)), 1),
            "median_spread_c": statistics.median(spreads) if spreads else None,
            "p90_spread_c": (statistics.quantiles(spreads, n=10)[8]
                             if len(spreads) >= 10 else None),
            "mean_spread_c": round(statistics.mean(spreads), 2) if spreads else None,
            "median_mid_c": statistics.median(mids) if mids else None,
        })
        print(f"{s:<16} open={len(mk):<5} events={len(events):<4} "
              f"dates={len(dates):<3} 2sided={rows[-1]['two_sided_pct']}% "
              f"medspread={rows[-1]['median_spread_c']} "
              f"p90={rows[-1]['p90_spread_c']} "
              f"medmid={rows[-1]['median_mid_c']}")
        time.sleep(0.4)
    return rows, per_series


def depth_probe(per_series):
    """Size at the touch.

    NOT from /orderbook. Two reasons. First, the market object already carries
    `yes_bid_size_fp` / `yes_ask_size_fp`, so the whole census costs zero extra
    requests. Second, /orderbook returns its data under `orderbook_fp` with
    keys `yes_dollars` / `no_dollars` -- a *fourth* renamed-field trap in this
    repo's history (C024 was the first). Reading the documented-looking
    `orderbook.yes` returns nothing and sums silently to zero, which is exactly
    the failure mode that produced a clean fake result once already.
    """
    out = []
    for s, mk in per_series.items():
        for m in mk:
            bid = cents(m.get("yes_bid_dollars"))
            ask = cents(m.get("yes_ask_dollars"))
            if not bid or not ask:
                continue
            bs = float(m.get("yes_bid_size_fp") or 0)
            as_ = float(m.get("yes_ask_size_fp") or 0)
            out.append({
                "series": s,
                "ticker": m["ticker"],
                "event": m.get("event_ticker"),
                "volume": float(m.get("volume_fp") or 0),
                "open_interest": float(m.get("open_interest_fp") or 0),
                "yes_bid": bid, "yes_ask": ask,
                "yes_bid_size": bs, "yes_ask_size": as_,
                "min_side_size": min(bs, as_),
            })
    return out


def strikes_per_event(per_series):
    """A ladder is ONE observation, not N.

    GUARDS: "a 10-strike ladder is one temperature reading, not ten markets."
    KXMLBTOTAL lists many strikes per game; counting tickers as events is the
    single easiest way to overstate the sample by an order of magnitude.
    """
    out = []
    for s, mk in per_series.items():
        by_ev = {}
        for m in mk:
            by_ev.setdefault(m.get("event_ticker"), 0)
            by_ev[m["event_ticker"]] += 1
        if not by_ev:
            continue
        vals = sorted(by_ev.values())
        out.append({
            "series": s,
            "events": len(by_ev),
            "markets": len(mk),
            "median_strikes_per_event": statistics.median(vals),
            "max_strikes_per_event": vals[-1],
        })
    return out


def cost_bar(rows):
    """Round-trip cost to enter and exit as a taker, in cents per contract."""
    out = []
    for r in rows:
        mid = r["median_mid_c"]
        sp = r["median_spread_c"]
        if mid is None or sp is None:
            continue
        entry = int(round(mid + sp / 2))          # pay the ask
        fee_in = taker_fee_cents(entry, 1)
        # exit: either settle (no second fee on a winning hold - Kalshi charges
        # on the trade, so a hold-to-settle strategy pays ONE fee) or sell.
        fee_out = taker_fee_cents(int(round(mid - sp / 2)), 1)
        out.append({
            "series": r["series"],
            "median_mid_c": mid,
            "median_spread_c": sp,
            "hold_to_settle_cost_c": round(sp / 2 + fee_in, 2),
            "round_trip_cost_c": round(sp + fee_in + fee_out, 2),
        })
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows, per = census()
    print("\n-- cost bars (taker, via common/kalshi_fees.py) --")
    cb = cost_bar(rows)
    for c in cb:
        print(f"  {c['series']:<16} mid={c['median_mid_c']:<5} "
              f"spread={c['median_spread_c']:<4} "
              f"hold-to-settle={c['hold_to_settle_cost_c']}c  "
              f"round-trip={c['round_trip_cost_c']}c")
    print("\n-- strikes per event (a ladder is ONE observation) --")
    spe = strikes_per_event(per)
    for r in spe:
        print(f"  {r['series']:<16} {r['markets']} markets over "
              f"{r['events']} events -> median "
              f"{r['median_strikes_per_event']} strikes/game "
              f"(max {r['max_strikes_per_event']})")
    print("\n-- size at the touch (from the market object, not /orderbook) --")
    dp = depth_probe(per)
    by = {}
    for d in dp:
        by.setdefault(d["series"], []).append(d["min_side_size"])
    for s, v in by.items():
        v = sorted(v)
        print(f"  {s:<16} n={len(v)} median min-side size = "
              f"{statistics.median(v)}  p10 = {v[max(0, len(v)//10 - 1)]}")
    (OUT / "market_census.json").write_text(json.dumps(
        {"measured_at_utc": stamp, "census": rows, "cost_bars": cb,
         "strikes_per_event": spe, "depth": dp}, indent=2))
    print(f"\nwrote {OUT / 'market_census.json'}")
