"""MM Task 0: what data do we ACTUALLY have for a market-making study?

Premise check before Task 1. The brief assumes "the machine holding the recorded
order books". Two things need verifying:

  P1  Do we have Kalshi ORDER BOOKS (depth) or only top-of-book?
  P2  Is there a historical TRADE TAPE? A fill model needs to know when the book
      traded THROUGH a price. Without trades there is no fill model, and without
      a fill model every downstream number is invented.

Also measures real round-trip latency, since the brief quotes 373ms from another
session and our recorder is logging ~47ms.
"""
import json
import os
import statistics
import time
from collections import Counter

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}
SETTLED = r"C:\Users\gianf\crypto\data\kalshi_settled"


def timed_get(path, **params):
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{BASE}{path}", params=params, headers=UA, timeout=45)
    except Exception as e:
        return None, time.perf_counter() - t0, str(e)
    return r, time.perf_counter() - t0, None


def section(t):
    print("\n" + "=" * 96)
    print(t)
    print("=" * 96)


def main():
    section("P1 — does Kalshi expose ORDER BOOK DEPTH (live)?")
    r, el, err = timed_get("/markets", series_ticker="KXBTCD", status="open",
                           limit=5)
    tk = None
    if r and r.status_code == 200:
        ms = r.json().get("markets", [])
        # pick one with a real two-sided quote
        for m in ms:
            if m.get("yes_bid_dollars") and m.get("yes_ask_dollars"):
                tk = m["ticker"]
                break
        tk = tk or (ms[0]["ticker"] if ms else None)
    print(f"  probe ticker: {tk}")
    if tk:
        r2, el2, _ = timed_get(f"/markets/{tk}/orderbook", depth=50)
        print(f"  /markets/{{t}}/orderbook -> {r2.status_code if r2 else 'ERR'} "
              f"({el2*1000:.0f} ms)")
        if r2 and r2.status_code == 200:
            # ⚠ FIXED 2026-08-08 (mailbox 004, found by the mlb session under
            # GUARD #23). The response has ONE top-level key, `orderbook_fp`,
            # holding `yes_dollars`/`no_dollars`. There is no `orderbook` key
            # and no `yes`/`no` key, so the old read returned an empty dict from
            # an HTTP 200 on EVERY market -- liquid or dead.
            #
            # This file is a CAPABILITY PROBE: its entire job is to answer "does
            # this endpoint return data?". Reading a key that does not exist
            # made it answer "no" confidently and repeatably. CLAUDE.md §5 lists
            # "whether the orderbook endpoint returns data" as one of only two
            # recorded contradictions between sessions in this repo -- this file
            # is where that contradiction came from.
            #
            # Depth IS public: 20 levels a side, free, unauthenticated. Verified
            # live 2026-08-06 on KXBTCD (16 levels) and recorded as LEDGER M001.
            j = r2.json() or {}
            ob = j.get("orderbook_fp") or j.get("orderbook") or {}
            print(f"    keys: {list(ob.keys())}")
            for side in ("yes_dollars", "no_dollars", "yes", "no"):
                lv = ob.get(side)
                if lv:
                    print(f"    {side}: {len(lv)} levels, "
                          f"first 5 = {lv[:5]}")
                else:
                    print(f"    {side}: {lv}")

    section("P2 — is there a historical TRADE TAPE?")
    for path, params in [("/markets/trades", {"ticker": tk, "limit": 100}),
                         ("/markets/trades", {"limit": 20})]:
        r3, el3, _ = timed_get(path, **params)
        print(f"  GET {path} {params} -> "
              f"{r3.status_code if r3 else 'ERR'} ({el3*1000:.0f} ms)")
        if r3 and r3.status_code == 200:
            j = r3.json()
            tr = j.get("trades", [])
            print(f"    {len(tr)} trades, cursor={str(j.get('cursor'))[:24]}")
            if tr:
                print(f"    fields: {sorted(tr[0].keys())}")
                for t in tr[:4]:
                    print(f"      {t}")
                break

    section("P2b — how far BACK does the trade tape go on a SETTLED market?")
    # take a settled KXBTCD market from the middle of the 68-day window
    import datetime as dt
    evs = {}
    with open(os.path.join(SETTLED, "KXBTCD.jsonl"), encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i > 120000:
                break
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            ct = m.get("close_time")
            if ct:
                evs.setdefault(ct, []).append(m)
    keys = sorted(evs)
    print(f"  settled close_times available: {len(keys)}, "
          f"{keys[0][:16]} -> {keys[-1][:16]}")
    for ct in [keys[0], keys[len(keys)//2], keys[-1]]:
        rows = evs[ct]
        # choose a market that actually traded
        rows.sort(key=lambda m: -float(m.get("volume_fp") or 0))
        m = rows[0]
        r4, el4, _ = timed_get("/markets/trades", ticker=m["ticker"],
                               limit=100)
        n = len(r4.json().get("trades", [])) if r4 and r4.status_code == 200 else None
        print(f"  {ct[:16]}  {m['ticker']:<32} vol={m.get('volume_fp'):>10} "
              f"-> {r4.status_code if r4 else 'ERR'} trades={n}")
        if r4 and r4.status_code == 200 and n:
            t = r4.json()["trades"][0]
            print(f"      sample: {t}")

    section("LATENCY — measured round trip from this machine")
    lat = []
    for _ in range(12):
        r5, el5, _ = timed_get("/exchange/status")
        lat.append(el5 * 1000)
        time.sleep(0.15)
    lat.sort()
    print(f"  /exchange/status  n=12  "
          f"min={lat[0]:.0f} p50={lat[len(lat)//2]:.0f} "
          f"p90={lat[int(0.9*len(lat))]:.0f} max={lat[-1]:.0f} ms")
    lat2 = []
    for _ in range(8):
        r6, el6, _ = timed_get("/markets", series_ticker="KXBTCD",
                               status="open", limit=200)
        lat2.append(el6 * 1000)
        time.sleep(0.2)
    lat2.sort()
    print(f"  /markets (200 rows) n=8  "
          f"min={lat2[0]:.0f} p50={lat2[len(lat2)//2]:.0f} "
          f"max={lat2[-1]:.0f} ms")

    section("P3 — what did OUR recorder actually capture for Kalshi?")
    import glob
    files = sorted(glob.glob(
        r"C:\Users\gianf\crypto\data\kalshi_quotes\*\*\*.jsonl"))
    n = 0
    keys_seen = Counter()
    ivals = []
    prev_by_ticker = {}
    for p in files[-2:]:
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                n += 1
                for k in row:
                    keys_seen[k] += 1
                tkr = row.get("ticker")
                t = row.get("ts_recv_ns")
                if tkr in prev_by_ticker and t:
                    ivals.append((t - prev_by_ticker[tkr]) / 1e9)
                prev_by_ticker[tkr] = t
    print(f"  {n} rows scanned from the last 2 partitions")
    print(f"  fields captured: {sorted(keys_seen)}")
    depth_fields = [k for k in keys_seen if "level" in k or "depth" in k
                    or k in ("bids", "asks")]
    print(f"  DEPTH fields present: {depth_fields or 'NONE — top of book only'}")
    if ivals:
        ivals.sort()
        print(f"  per-ticker resample interval (s): "
              f"p10={ivals[int(0.1*len(ivals))]:.1f} "
              f"p50={ivals[len(ivals)//2]:.1f} "
              f"p90={ivals[int(0.9*len(ivals))]:.1f}")


if __name__ == "__main__":
    main()
