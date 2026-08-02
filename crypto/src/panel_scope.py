"""TASK 1a: measure the ACTUAL scope of the panel before building it.

Two things the probe suggested and that must be measured on a properly drawn
sample rather than the first N rows of a file (failure mode #1):

  Q1  How many strikes per event carry a genuine TWO-SIDED quote? The headline
      benchmark is "Kalshi's mid", and where there is no two-sided quote there
      IS no mid. If only ~3 of 60 strikes are two-sided, the testable ladder is
      far narrower than the 291,840-market headline implies -- and the "wings"
      where fat tails should pay may not be quotable at all.

  Q2  What is the real distribution of contract lifetime? An earlier check over
      the first 40,000 rows returned a 1.0 h median, but the probe found a
      market with 23.7 h of candles. The first-N-rows sample was not random.

Sampling rule (stated up front): events are drawn EVENLY ACROSS THE 68 DAYS by
sorting distinct events on close_time and taking a fixed stride, so no calendar
period is over-represented.
"""
import datetime as dt
import json
import os
import random
import time
from collections import Counter, defaultdict

import numpy as np
import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}
ROOT = r"C:\Users\gianf\crypto\data\kalshi_settled"


def get(path, **params):
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
        return r
    return None


def load_all(series):
    """Every settled market, grouped by event. Full file, no truncation."""
    by_ev = defaultdict(list)
    n = 0
    with open(os.path.join(ROOT, f"{series}.jsonl"), encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            n += 1
            ev = m.get("event_ticker")
            if ev:
                by_ev[ev].append(m)
    return by_ev, n


def iso(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def main():
    for series in ["KXBTCD", "KXBTC"]:
        by_ev, n_rows = load_all(series)
        print("=" * 100)
        print(f"{series} — FULL FILE, {n_rows} rows, {len(by_ev)} events")
        print("=" * 100)

        # ---------------- Q2: lifetime, measured over ALL events -----------
        lifes, closes = [], []
        per_ev = []
        for ev, rows in by_ev.items():
            m = rows[0]
            ot, ct = m.get("open_time"), m.get("close_time")
            per_ev.append(len(rows))
            if ot and ct:
                lifes.append((iso(ct) - iso(ot)).total_seconds() / 3600.0)
                closes.append(ct)
        L = np.array(lifes)
        print(f"\nQ2 contract lifetime (hours), ALL {len(L)} events:")
        for q in [0, 5, 25, 50, 75, 95, 100]:
            print(f"    p{q:<3} = {np.percentile(L, q):8.2f} h")
        print(f"    fraction >= 54h (Deribit's shortest usable): "
              f"{100*np.mean(L>=54):.1f}%")
        print(f"    distinct lifetimes: "
              f"{dict(Counter(np.round(L).astype(int)).most_common(8))}")
        print(f"  markets per event: min={min(per_ev)} "
              f"med={int(np.median(per_ev))} max={max(per_ev)}")
        closes.sort()
        print(f"  close_time range: {closes[0][:16]} -> {closes[-1][:16]}")

        # ---------------- Q1: two-sided strike availability ----------------
        # stratified sample across the 68 days
        evs = sorted(by_ev, key=lambda e: by_ev[e][0].get("close_time") or "")
        k = 12
        stride = max(1, len(evs) // k)
        sample = evs[::stride][:k]
        print(f"\nQ1 two-sided quote availability")
        print(f"  sampling rule: {len(evs)} events sorted by close_time, "
              f"stride {stride}, {len(sample)} sampled evenly across the range")
        print(f"  sampled closes: {[by_ev[e][0]['close_time'][:13] for e in sample]}")

        tot_strikes = tot_twosided = 0
        dist_rows = []
        print(f"\n  {'event':<22} {'strikes':>8} {'2-sided':>8} "
              f"{'|K-S| max 2-sided':>19} {'settle':>10}")
        for ev in sample:
            rows = by_ev[ev]
            settle = None
            for m in rows:
                if m.get("expiration_value"):
                    try:
                        settle = float(m["expiration_value"])
                        break
                    except ValueError:
                        pass
            if settle is None:
                continue
            ct = iso(rows[0]["close_time"])
            end = int(ct.timestamp())
            start = end - 3600
            rows2 = sorted(rows, key=lambda m: abs(
                (m.get("floor_strike") or 0) - settle))
            n_two, maxd = 0, 0.0
            probe = rows2[:26]          # near-money first; wings are the test
            for m in probe:
                r = get(f"/series/{series}/markets/{m['ticker']}/candlesticks",
                        start_ts=start, end_ts=end, period_interval=1)
                if r is None or r.status_code != 200:
                    continue
                cs = r.json().get("candlesticks", []) or []
                ok = 0
                for c in cs:
                    b = (c.get("yes_bid") or {}).get("close_dollars")
                    a = (c.get("yes_ask") or {}).get("close_dollars")
                    if b is None or a is None:
                        continue
                    b, a = float(b), float(a)
                    if 0 < b < a < 1:
                        ok += 1
                d = abs((m.get("floor_strike") or 0) - settle)
                if ok > 0:
                    n_two += 1
                    maxd = max(maxd, d)
                dist_rows.append({"d": d, "two": ok, "n": len(cs)})
                time.sleep(0.02)
            tot_strikes += len(probe)
            tot_twosided += n_two
            print(f"  {ev:<22} {len(rows):>8} {n_two:>8} {maxd:>19.0f} "
                  f"{settle:>10.2f}")

        print(f"\n  TOTAL probed {tot_strikes} near-money strikes, "
              f"{tot_twosided} had any two-sided minute "
              f"({100*tot_twosided/max(1,tot_strikes):.1f}%)")

        # two-sidedness vs distance from settlement
        if dist_rows:
            print(f"\n  two-sided availability vs |K - settle|:")
            bands = [(0, 250), (250, 500), (500, 1000), (1000, 2000),
                     (2000, 4000), (4000, 1e9)]
            for lo, hi in bands:
                sel = [d for d in dist_rows if lo <= d["d"] < hi]
                if not sel:
                    continue
                frac = np.mean([1 if s["two"] > 0 else 0 for s in sel])
                med = np.median([s["two"] for s in sel])
                print(f"    ${lo:>6}-${hi if hi<1e9 else 'inf':<6} "
                      f"n={len(sel):>4}  any-2-sided={100*frac:5.1f}%  "
                      f"median 2-sided minutes={med:.0f}")
        print()


if __name__ == "__main__":
    main()
