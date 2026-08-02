"""TASK 1: build the decision-time price panel from Kalshi candlesticks.

LOOK-AHEAD DISCIPLINE (failure mode #4) — the strike-selection rule.
The obvious design is "pull the N strikes nearest the settlement". That is
LOOK-AHEAD: it selects the sample using the outcome, and it would concentrate
the panel on exactly the strikes that finished near the money. Instead strikes
are chosen by distance from the ANCHOR = the previous event's settlement, which
is the spot at the moment this event's window opens and is knowable before any
decision in this event. Every selection input therefore precedes every decision
timestamp, and this is asserted in code.

SAMPLING RULE (failure mode #1) — events are drawn on a fixed stride through
all events sorted by close_time, so every calendar week is represented equally.
Composition is written to panel_manifest.md before analysis.

CONCURRENCY — single-threaded on purpose. Another session on this machine is
running a 9-worker Kalshi candlestick pull; adding workers here would produce
rate-limit contention and silently thin the panel.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np
import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}
SETTLED = r"C:\Users\gianf\crypto\data\kalshi_settled"
OUT = r"C:\Users\gianf\crypto\data\panel"

MAX_SPREAD = 0.10          # pre-registered: quotes wider than 10c are not
                           # actionable and are dropped (count reported)


def iso(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def get(path, **params):
    for a in range(7):
        try:
            r = requests.get(f"{BASE}{path}", params=params, headers=UA,
                             timeout=45)
        except Exception:
            time.sleep(0.8 * (a + 1))
            continue
        if r.status_code == 429:
            time.sleep(1.5 * (a + 1))
            continue
        if r.status_code >= 500:
            time.sleep(0.8 * (a + 1))
            continue
        return r
    return None


def load_events(series):
    by_ev = defaultdict(list)
    with open(os.path.join(SETTLED, f"{series}.jsonl"), encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            ev = m.get("event_ticker")
            if ev:
                by_ev[ev].append(m)
    return by_ev


def event_settlement(rows):
    for m in rows:
        v = m.get("expiration_value")
        if v not in (None, ""):
            try:
                return float(v)
            except ValueError:
                pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="KXBTCD")
    ap.add_argument("--events", type=int, default=400)
    ap.add_argument("--strikes", type=int, default=12)
    ap.add_argument("--minutes-before-close", type=int, default=60)
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    by_ev = load_events(args.series)
    evs = sorted(by_ev, key=lambda e: by_ev[e][0].get("close_time") or "")
    print(f"{args.series}: {len(evs)} settled events", flush=True)

    # anchor = PREVIOUS event's settlement (knowable at this event's open)
    settle_of = {e: event_settlement(by_ev[e]) for e in evs}
    anchor_of = {}
    for i, e in enumerate(evs):
        if i == 0:
            continue
        prev = evs[i - 1]
        # only use it if the previous event closes at/before this one's open
        try:
            po = iso(by_ev[prev][0]["close_time"])
            co = iso(by_ev[e][0]["open_time"])
        except Exception:
            continue
        if settle_of[prev] is not None and po <= co:
            anchor_of[e] = (settle_of[prev], po)

    usable = [e for e in evs if e in anchor_of and settle_of[e] is not None]
    print(f"  {len(usable)} events with a knowable anchor and a settlement",
          flush=True)

    stride = max(1, len(usable) // args.events)
    sample = usable[::stride][:args.events]
    print(f"  sampling stride {stride} -> {len(sample)} events", flush=True)

    path = os.path.join(OUT, f"panel_{args.series}.jsonl")
    tmp = path + ".partial"
    fout = open(tmp, "w", encoding="utf-8")

    rows_out = []
    stats = defaultdict(int)
    t0 = time.time()
    for n, ev in enumerate(sample):
        mkts = by_ev[ev]
        anchor, anchor_ts = anchor_of[ev]
        settle = settle_of[ev]
        close = iso(mkts[0]["close_time"])
        close_ts = int(close.timestamp())
        start_ts = close_ts - args.minutes_before_close * 60

        # --- ASSERT knowability: the anchor predates every decision minute ---
        assert anchor_ts.timestamp() <= start_ts, (
            f"anchor {anchor_ts} is not before first decision "
            f"{dt.datetime.utcfromtimestamp(start_ts)}")

        cand = [m for m in mkts if m.get("floor_strike") is not None]
        cand.sort(key=lambda m: abs(float(m["floor_strike"]) - anchor))
        pick = cand[:args.strikes]

        for m in pick:
            K = float(m["floor_strike"])
            r = get(f"/series/{args.series}/markets/{m['ticker']}/candlesticks",
                    start_ts=start_ts, end_ts=close_ts, period_interval=1)
            stats["calls"] += 1
            if r is None or r.status_code != 200:
                stats["http_err"] += 1
                continue
            cs = r.json().get("candlesticks", []) or []
            y = 1.0 if str(m.get("result")) == "yes" else 0.0
            for c in cs:
                ts = c.get("end_period_ts")
                b = (c.get("yes_bid") or {}).get("close_dollars")
                a = (c.get("yes_ask") or {}).get("close_dollars")
                stats["candles"] += 1
                if ts is None or b is None or a is None:
                    stats["drop_null"] += 1
                    continue
                b, a = float(b), float(a)
                if not (0 < b < a < 1):
                    stats["drop_one_sided"] += 1
                    continue
                if (a - b) > MAX_SPREAD:
                    stats["drop_wide_spread"] += 1
                    continue
                tau_s = close_ts - int(ts)
                if tau_s <= 0:
                    stats["drop_nonpositive_tau"] += 1
                    continue
                # --- ASSERT no look-ahead on the decision timestamp ---
                if int(ts) > close_ts:
                    stats["drop_after_close"] += 1
                    continue
                rec = {
                    "series": args.series, "event": ev, "ticker": m["ticker"],
                    "ts": int(ts), "close_ts": close_ts, "tau_s": tau_s,
                    "K": K, "anchor": anchor,
                    "anchor_ts": int(anchor_ts.timestamp()),
                    "settle": settle, "y": y,
                    "bid": b, "ask": a, "mid": (a + b) / 2.0,
                    "spread": a - b,
                    "vol": float(c.get("volume_fp") or 0),
                    "oi": float(c.get("open_interest_fp") or 0),
                }
                rows_out.append(rec)
                fout.write(json.dumps(rec, separators=(",", ":")) + "\n")
            time.sleep(0.02)
        if (n + 1) % 5 == 0:
            fout.flush()
            el = time.time() - t0
            rate = (n + 1) / el if el > 0 else 0
            eta = (len(sample) - n - 1) / rate / 60 if rate > 0 else 0
            print(f"  [{el:6.0f}s] {n+1}/{len(sample)} ev "
                  f"({rate*60:.1f} ev/min, ETA {eta:.0f}m) "
                  f"{len(rows_out)} rows {dict(stats)}", flush=True)

    fout.close()
    os.replace(tmp, path)
    print(f"\nwrote {path}: {len(rows_out)} rows")
    print(f"stats: {dict(stats)}")

    with open(os.path.join(OUT, f"stats_{args.series}.json"), "w") as f:
        json.dump({"stats": dict(stats), "n_events_sampled": len(sample),
                   "stride": stride, "rows": len(rows_out),
                   "max_spread": MAX_SPREAD}, f, indent=2)


if __name__ == "__main__":
    main()
