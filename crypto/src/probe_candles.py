"""TASK 1 probe: characterise the Kalshi candlesticks endpoint before pulling.

Decides the pull design. 291,840 settled KXBTC markets cannot all be pulled
one-at-a-time; we need to know cost per call, candles per call, and — critically
— whether NEAR-MONEY strikes carry genuine two-sided quotes over the contract's
life (the settled /markets records were 100% degenerate at 0/1, which is why
this endpoint is the unlock).
"""
import json
import os
import time
from collections import Counter

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}
ROOT = r"C:\Users\gianf\crypto\data\kalshi_settled"


def get(path, **params):
    t0 = time.perf_counter()
    for a in range(6):
        try:
            r = requests.get(f"{BASE}{path}", params=params, headers=UA,
                             timeout=45)
        except Exception:
            time.sleep(1.0 * (a + 1))
            continue
        if r.status_code == 429:
            time.sleep(1.5 * (a + 1))
            continue
        return r, time.perf_counter() - t0
    return None, time.perf_counter() - t0


def load_event(series, want_event=None, limit=400000):
    """Return all settled markets for one event."""
    rows, ev = [], None
    p = os.path.join(ROOT, f"{series}.jsonl")
    with open(p, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i > limit:
                break
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev is None and want_event is None:
                ev = m.get("event_ticker")
            if want_event and m.get("event_ticker") != want_event:
                continue
            if want_event is None and m.get("event_ticker") != ev:
                continue
            rows.append(m)
    return ev or want_event, rows


def main():
    ev, mkts = load_event("KXBTCD")
    print(f"event {ev}: {len(mkts)} markets")
    settle = None
    for m in mkts:
        if m.get("expiration_value"):
            settle = float(m["expiration_value"])
            break
    print(f"settlement = {settle}")
    close = mkts[0]["close_time"]
    import datetime as dt
    ct = dt.datetime.fromisoformat(close.replace("Z", "+00:00"))
    end = int(ct.timestamp())
    start = end - 3600

    # order strikes by distance from settlement -> near-money first
    mkts.sort(key=lambda m: abs((m.get("floor_strike") or 0) - settle))
    print(f"\nnearest strikes to settlement: "
          f"{[m.get('floor_strike') for m in mkts[:6]]}")

    print(f"\n{'ticker':<34} {'|K-S|':>9} {'ms':>6} {'n':>5} "
          f"{'2-sided':>8} {'mid range':>18} {'med spread':>11}")
    lat = []
    for m in mkts[:14]:
        tk = m["ticker"]
        r, el = get(f"/series/KXBTCD/markets/{tk}/candlesticks",
                    start_ts=start, end_ts=end, period_interval=1)
        lat.append(el)
        if r is None or r.status_code != 200:
            print(f"  {tk:<34} HTTP {r.status_code if r else 'ERR'}")
            continue
        cs = r.json().get("candlesticks", []) or []
        two, mids, spreads = 0, [], []
        for c in cs:
            b = (c.get("yes_bid") or {}).get("close_dollars")
            a = (c.get("yes_ask") or {}).get("close_dollars")
            if b is None or a is None:
                continue
            b, a = float(b), float(a)
            if 0 < b < a < 1:
                two += 1
                mids.append((a + b) / 2)
                spreads.append(a - b)
        mr = (f"{min(mids):.3f}-{max(mids):.3f}" if mids else "-")
        ms = (f"{sorted(spreads)[len(spreads)//2]:.4f}" if spreads else "-")
        print(f"  {tk:<34} {abs((m.get('floor_strike') or 0)-settle):>9.0f} "
              f"{el*1000:>6.0f} {len(cs):>5} {two:>8} {mr:>18} {ms:>11}")

    print(f"\nmedian latency {1000*sorted(lat)[len(lat)//2]:.0f} ms")

    # ---- how far back does the endpoint go, and what intervals exist? ----
    tk = mkts[0]["ticker"]
    print(f"\nperiod_interval support on {tk}:")
    for pi in [1, 60, 1440]:
        r, el = get(f"/series/KXBTCD/markets/{tk}/candlesticks",
                    start_ts=end - 86400, end_ts=end, period_interval=pi)
        n = len(r.json().get("candlesticks", [])) if r and r.status_code == 200 else None
        print(f"  interval={pi:<6} -> {r.status_code if r else 'ERR'} "
              f"n={n} ({el*1000:.0f} ms)")

    # ---- oldest event still served? ----
    print("\noldest-event reachability:")
    import itertools
    for series in ["KXBTCD"]:
        evs = {}
        with open(os.path.join(ROOT, f"{series}.jsonl"), encoding="utf-8") as f:
            for line in itertools.islice(f, 400000):
                try:
                    m = json.loads(line)
                except json.JSONDecodeError:
                    continue
                e = m.get("event_ticker")
                if e and e not in evs:
                    evs[e] = m
        keys = sorted(evs, key=lambda k: evs[k].get("close_time") or "")
        for k in [keys[0], keys[len(keys)//2], keys[-1]]:
            m = evs[k]
            ct = dt.datetime.fromisoformat(
                m["close_time"].replace("Z", "+00:00"))
            e_ = int(ct.timestamp())
            r, el = get(f"/series/{series}/markets/{m['ticker']}/candlesticks",
                        start_ts=e_ - 3600, end_ts=e_, period_interval=1)
            n = (len(r.json().get("candlesticks", []))
                 if r and r.status_code == 200 else None)
            print(f"  {k:<24} close={m['close_time'][:16]} "
                  f"-> {r.status_code if r else 'ERR'} n={n}")


if __name__ == "__main__":
    main()
