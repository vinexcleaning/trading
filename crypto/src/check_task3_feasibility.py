"""Feasibility check for TASK 3, run BEFORE building the comparison.

Task 3 asks to compare, for every settled Kalshi ladder market, "Kalshi mid,
bid, ask" at the decision timestamp against a Deribit reference. Two premises
have to hold and both are checked here rather than assumed:

  P1  settled Kalshi records retain a usable DECISION-TIME quote
  P2  Deribit has a usable expiry near Kalshi's time-to-expiry

If P1 fails the 68-day settled history cannot support a vs-mid comparison at
all, and the headline must come from recorded data instead.
"""
import glob
import json
import os
from collections import Counter

import numpy as np

ROOT = r"C:\Users\gianf\crypto\data\kalshi_settled"


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    print("=" * 96)
    print("P1 — do SETTLED Kalshi records retain a decision-time quote?")
    print("=" * 96)
    for series in ["KXBTC", "KXBTCD"]:
        p = os.path.join(ROOT, f"{series}.jsonl")
        if not os.path.exists(p):
            continue
        last, pbid, pask, ybid, yask, res = [], [], [], [], [], []
        n = 0
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                if n >= 60000:
                    break
                try:
                    m = json.loads(line)
                except json.JSONDecodeError:
                    continue
                n += 1
                for src, dst in ((m.get("last_price_dollars"), last),
                                 (m.get("previous_yes_bid_dollars"), pbid),
                                 (m.get("previous_yes_ask_dollars"), pask),
                                 (m.get("yes_bid_dollars"), ybid),
                                 (m.get("yes_ask_dollars"), yask)):
                    v = f(src)
                    if v is not None:
                        dst.append(v)
                res.append(str(m.get("result")))

        print(f"\n{series}  (first {n} settled markets)")
        for name, arr in (("last_price", last),
                          ("previous_yes_bid", pbid),
                          ("previous_yes_ask", pask),
                          ("yes_bid", ybid), ("yes_ask", yask)):
            if not arr:
                print(f"  {name:<20} ALL NULL")
                continue
            a = np.array(arr)
            deg = float(np.mean((a <= 0.01) | (a >= 0.99)))
            print(f"  {name:<20} n={len(a):>7} "
                  f"med={np.median(a):.4f} "
                  f"frac at 0/1 extremes={deg*100:5.1f}%  "
                  f"frac in 0.05-0.95={100*np.mean((a>=0.05)&(a<=0.95)):5.1f}%")
        print(f"  results: {dict(Counter(res).most_common(4))}")

    print("\n" + "=" * 96)
    print("P2 — Kalshi ladder time-to-expiry vs Deribit's usable expiries")
    print("=" * 96)
    rp = r"C:\Users\gianf\crypto\data\deribit\pricer_report.json"
    if os.path.exists(rp):
        rep = json.load(open(rp))
        for cur in ["BTC", "ETH"]:
            exps = rep.get(cur, {}).get("expiries", [])
            usable = [e for e in exps if e.get("kept", 0) > 0]
            if usable:
                print(f"  {cur}: {len(usable)} usable expiries, "
                      f"shortest tau = {min(e['tau_h'] for e in usable):.1f}h")
                drop = [e for e in exps if e.get("kept", 0) == 0]
                for e in drop:
                    print(f"     DROPPED tau={e['tau_h']:>7.2f}h  "
                          f"{e.get('discarded')}")

    # Kalshi ladder horizons, from settled close_time vs open_time
    print()
    for series in ["KXBTC", "KXBTCD"]:
        p = os.path.join(ROOT, f"{series}.jsonl")
        if not os.path.exists(p):
            continue
        import datetime as dt
        hs = []
        n = 0
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                if n >= 40000:
                    break
                try:
                    m = json.loads(line)
                except json.JSONDecodeError:
                    continue
                n += 1
                ot, ct = m.get("open_time"), m.get("close_time")
                if not ot or not ct:
                    continue
                try:
                    a = dt.datetime.fromisoformat(ot.replace("Z", "+00:00"))
                    b = dt.datetime.fromisoformat(ct.replace("Z", "+00:00"))
                except ValueError:
                    continue
                hs.append((b - a).total_seconds() / 3600.0)
        if hs:
            h = np.array(hs)
            print(f"  {series} contract LIFETIME (open->close), hours: "
                  f"min={h.min():.1f} p25={np.percentile(h,25):.1f} "
                  f"med={np.median(h):.1f} p75={np.percentile(h,75):.1f} "
                  f"max={h.max():.1f}")
            print(f"    fraction with lifetime >= 54h (Deribit's shortest "
                  f"usable): {100*np.mean(h>=54):.1f}%")


if __name__ == "__main__":
    main()
