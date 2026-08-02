"""MM TASK 1: which series can even be made?

Scores candidate Kalshi series on the properties a market maker needs, using
the two data sources that actually exist over 68 days:
  - candlesticks  -> per-minute bid/ask  -> two-sided uptime, spread
  - /markets/trades -> real trades w/ aggressor side -> trade frequency

HARD DISQUALIFIERS, pre-registered here before running:
  D1  median spread <= maker round-trip cost  -> no gross margin to capture
  D2  two-sided uptime < 50%                  -> cannot quote continuously
  D3  < 2 trades/hour per market              -> quoting earns nothing

SAMPLING: for each series, events are drawn on a fixed STRIDE through all
settled events sorted by close_time, so every calendar week is represented.
Within each event, the N strikes nearest the ANCHOR (previous event's
settlement — knowable before the event opens) are taken. Never the strikes
nearest the settlement; that would select on the outcome.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import requests

sys.path.insert(0, os.path.dirname(__file__))
from fees import kalshi_fee_per_contract_unrounded, KALSHI_MAKER_RATE  # noqa

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}
SETTLED = r"C:\Users\gianf\crypto\data\kalshi_settled"
OUT = r"C:\Users\gianf\crypto\data\mm"

# candidate series: crypto ladders we hold settled data for
CANDIDATES = ["KXBTCD", "KXBTC", "KXETHD", "KXETH", "KXSOLD", "KXXRPD",
              "KXXRP", "KXDOGED", "KXBTC15M", "KXETH15M", "KXSOL15M",
              "KXXRP15M"]


def get(path, **params):
    for a in range(6):
        try:
            r = requests.get(f"{BASE}{path}", params=params, headers=UA,
                             timeout=45)
        except Exception:
            time.sleep(0.7 * (a + 1))
            continue
        if r.status_code == 429:
            time.sleep(1.4 * (a + 1))
            continue
        if r.status_code >= 500:
            time.sleep(0.7 * (a + 1))
            continue
        return r
    return None


def iso(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_events(series):
    p = os.path.join(SETTLED, f"{series}.jsonl")
    if not os.path.exists(p):
        return {}
    by_ev = defaultdict(list)
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            ev = m.get("event_ticker")
            if ev:
                by_ev[ev].append(m)
    return by_ev


def settlement(rows):
    for m in rows:
        v = m.get("expiration_value")
        if v not in (None, ""):
            try:
                return float(v)
            except ValueError:
                pass
    return None


def all_trades(ticker, max_pages=12):
    """Full trade tape for one market, paginated."""
    out, cursor = [], None
    for _ in range(max_pages):
        p = {"ticker": ticker, "limit": 1000}
        if cursor:
            p["cursor"] = cursor
        r = get("/markets/trades", **p)
        if r is None or r.status_code != 200:
            break
        j = r.json()
        tr = j.get("trades", []) or []
        out.extend(tr)
        cursor = j.get("cursor")
        if not cursor or not tr:
            break
    return out


def score_series(series, n_events, n_strikes, minutes):
    by_ev = load_events(series)
    if not by_ev:
        return {"series": series, "kill": "no settled data on disk"}
    evs = sorted(by_ev, key=lambda e: by_ev[e][0].get("close_time") or "")

    # anchors, knowable-before-open
    anchor_of = {}
    for i, e in enumerate(evs):
        if i == 0:
            continue
        prev = evs[i - 1]
        try:
            po = iso(by_ev[prev][0]["close_time"])
            co = iso(by_ev[e][0]["open_time"])
        except Exception:
            continue
        s = settlement(by_ev[prev])
        if s is not None and po <= co:
            anchor_of[e] = (s, po)
    usable = [e for e in evs if e in anchor_of]
    if len(usable) < 5:
        return {"series": series, "kill": "too few events with a usable anchor",
                "n_events_total": len(evs)}

    stride = max(1, len(usable) // n_events)
    sample = usable[::stride][:n_events]

    spreads, two_sided, total_min = [], 0, 0
    trades_per_mkt, trade_sizes, taker_sides = [], [], Counter()
    hours = Counter()
    n_mkts = 0
    for ev in sample:
        mkts = by_ev[ev]
        anchor, _ = anchor_of[ev]
        close = iso(mkts[0]["close_time"])
        close_ts = int(close.timestamp())
        start_ts = close_ts - minutes * 60
        cand = [m for m in mkts if m.get("floor_strike") is not None]
        cand.sort(key=lambda m: abs(float(m["floor_strike"]) - anchor))
        for m in cand[:n_strikes]:
            n_mkts += 1
            r = get(f"/series/{series}/markets/{m['ticker']}/candlesticks",
                    start_ts=start_ts, end_ts=close_ts, period_interval=1)
            if r is not None and r.status_code == 200:
                for c in r.json().get("candlesticks", []) or []:
                    total_min += 1
                    b = (c.get("yes_bid") or {}).get("close_dollars")
                    a = (c.get("yes_ask") or {}).get("close_dollars")
                    if b is None or a is None:
                        continue
                    b, a = float(b), float(a)
                    if 0 < b < a < 1:
                        two_sided += 1
                        spreads.append(a - b)
            # /markets/trades returns a market's ENTIRE life, which for these
            # ladders can be 33h. Dividing that by our 1h analysis window
            # overstated trade frequency by ~30x on the first run. Window the
            # tape to the same [start_ts, close_ts] the quotes cover.
            tr_all = all_trades(m["ticker"], max_pages=3)
            tr = []
            for t in tr_all:
                ct = t.get("created_time")
                if not ct:
                    continue
                try:
                    tsec = iso(ct).timestamp()
                except ValueError:
                    continue
                if start_ts <= tsec <= close_ts:
                    tr.append(t)
            trades_per_mkt.append(len(tr))
            for t in tr:
                try:
                    trade_sizes.append(float(t.get("count_fp") or 0))
                except ValueError:
                    pass
                taker_sides[t.get("taker_side")] += 1
                ct = t.get("created_time")
                if ct:
                    hours[ct[11:13]] += 1
            time.sleep(0.02)

    if not spreads:
        return {"series": series, "kill": "no two-sided minutes at all",
                "markets_probed": n_mkts, "candle_minutes": total_min}

    sp = np.array(spreads)
    tpm = np.array(trades_per_mkt)
    hours_per_mkt = minutes / 60.0
    res = {
        "series": series,
        "events_sampled": len(sample),
        "events_total": len(evs),
        "markets_probed": n_mkts,
        "candle_minutes": total_min,
        "two_sided_uptime": two_sided / max(1, total_min),
        "spread_med": float(np.median(sp)),
        "spread_p90": float(np.percentile(sp, 90)),
        "spread_p99": float(np.percentile(sp, 99)),
        "trades_per_market": float(np.mean(tpm)),
        "trades_per_market_hour": float(np.mean(tpm) / hours_per_mkt),
        "trade_size_med": float(np.median(trade_sizes)) if trade_sizes else 0.0,
        "trade_size_p90": (float(np.percentile(trade_sizes, 90))
                           if trade_sizes else 0.0),
        "taker_side_mix": dict(taker_sides),
        "hour_profile": dict(sorted(hours.items())),
        "events_per_week": len(evs) / 9.7,      # 68-day window
    }
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=10)
    ap.add_argument("--strikes", type=int, default=4)
    ap.add_argument("--minutes", type=int, default=60)
    ap.add_argument("--series", nargs="*", default=CANDIDATES)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    # maker round-trip cost at 50c, exact decimal.
    # VERIFIED 2026-08-01: crypto series are fee_type `quadratic` = TAKER ONLY.
    # The maker fee is ZERO, so the full tick survives to meet adverse
    # selection. D1 therefore cannot bind on fees alone; the binding
    # constraint is adverse selection, measured in Task 3.
    mk50 = float(kalshi_fee_per_contract_unrounded("0.50",
                                                   KALSHI_MAKER_RATE)) * 100
    print(f"Kalshi CRYPTO maker fee at 50c = {mk50:.4f}c/contract; "
          f"round trip = {2*mk50:.4f}c  (verified zero — taker-only fee type)")
    print(f"D1 disqualifier: median spread <= {2*mk50:.4f}c "
          f"-> cannot bind; gross margin at a 1c tick is the full 1.00c\n")

    results = []
    for s in args.series:
        t0 = time.time()
        r = score_series(s, args.events, args.strikes, args.minutes)
        r["seconds"] = round(time.time() - t0, 1)
        results.append(r)
        if r.get("kill"):
            print(f"{s:<12} KILLED: {r['kill']}")
        else:
            print(f"{s:<12} uptime={r['two_sided_uptime']*100:5.1f}%  "
                  f"spread_med={r['spread_med']*100:5.2f}c  "
                  f"p90={r['spread_p90']*100:5.2f}c  "
                  f"trades/mkt/hr={r['trades_per_market_hour']:7.1f}  "
                  f"sz_med={r['trade_size_med']:7.1f}  "
                  f"ev/wk={r['events_per_week']:5.1f}  ({r['seconds']}s)")
        sys.stdout.flush()

    with open(os.path.join(OUT, "universe.json"), "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nwrote {os.path.join(OUT, 'universe.json')}")


if __name__ == "__main__":
    main()
