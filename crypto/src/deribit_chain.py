"""Phase 1.8 / Phase 4 model 6: Deribit option chain + DVOL.

The only free forward-looking volatility source, and the only one that yields a
complete risk-neutral distribution. If Kalshi or Polymarket disagree with the
Deribit-implied digital price systematically, that is the cleanest edge in the
session — and it needs no forecasting model at all.

A binary "S_T > K" is the negative of the derivative of the call price wrt
strike:  P(S_T > K) = -dC/dK.  With a discrete strike ladder this is estimated
by a central difference on the call curve, which is exactly what the option
chain gives us for free.

Read-only, public API, no auth.
"""
import json
import math
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

BASE = "https://www.deribit.com/api/v2/public"
UA = {"User-Agent": "research-readonly/0.1"}
OUT = r"C:\Users\gianf\crypto\data\deribit"


def get(method, **params):
    for attempt in range(6):
        try:
            r = requests.get(f"{BASE}/{method}", params=params, headers=UA,
                             timeout=45)
        except Exception:
            time.sleep(1.2 * (attempt + 1))
            continue
        if r.status_code == 429:
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code >= 400:
            return None
        j = r.json()
        return j.get("result")
    return None


def section(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


def main():
    os.makedirs(OUT, exist_ok=True)
    snap = {"captured_utc": datetime.now(timezone.utc).isoformat(),
            "captured_ns": time.time_ns()}

    section("1. Index prices (the settlement reference)")
    for idx in ["btc_usd", "eth_usd", "sol_usd", "xrp_usd"]:
        r = get("get_index_price", index_name=idx)
        print(f"  {idx:<10} {r}")
        snap.setdefault("index", {})[idx] = r

    section("2. DVOL — Deribit's implied-vol index")
    for cur in ["BTC", "ETH"]:
        now_ms = int(time.time() * 1000)
        r = get("get_volatility_index_data", currency=cur,
                start_timestamp=now_ms - 7 * 86400 * 1000,
                end_timestamp=now_ms, resolution="3600")
        data = (r or {}).get("data", [])
        print(f"  {cur} DVOL: {len(data)} hourly points over 7d")
        if data:
            last = data[-1]
            print(f"    latest [ts,open,high,low,close] = {last}")
            closes = [d[4] for d in data]
            print(f"    7d range: {min(closes):.2f} .. {max(closes):.2f}, "
                  f"last {closes[-1]:.2f}")
        snap.setdefault("dvol", {})[cur] = data

    section("3. Option chain — full book summary by currency")
    for cur in ["BTC", "ETH"]:
        book = get("get_book_summary_by_currency", currency=cur, kind="option")
        if not book:
            print(f"  {cur}: none")
            continue
        print(f"  {cur}: {len(book)} option instruments")
        # group by expiry
        by_exp = defaultdict(list)
        for b in book:
            name = b.get("instrument_name", "")
            parts = name.split("-")
            if len(parts) >= 4:
                by_exp[parts[1]].append(b)
        print(f"    {len(by_exp)} expiries")
        for exp in sorted(by_exp, key=lambda e: len(by_exp[e]),
                          reverse=True)[:8]:
            rows = by_exp[exp]
            ivs = [b.get("mark_iv") for b in rows if b.get("mark_iv")]
            oi = sum(b.get("open_interest") or 0 for b in rows)
            print(f"      {exp:<10} {len(rows):>4} strikes  "
                  f"OI={oi:>10.1f}  "
                  f"markIV {min(ivs):.1f}-{max(ivs):.1f}" if ivs else exp)
        snap.setdefault("book_summary", {})[cur] = book

    section("4. Nearest expiry chain in detail (the digital-price input)")
    for cur in ["BTC"]:
        instr = get("get_instruments", currency=cur, kind="option",
                    expired="false")
        if not instr:
            continue
        by_exp = defaultdict(list)
        for i in instr:
            by_exp[i["expiration_timestamp"]].append(i)
        now_ms = int(time.time() * 1000)
        future = sorted(e for e in by_exp if e > now_ms)
        print(f"  {cur}: {len(instr)} instruments, {len(future)} future "
              f"expiries")
        for e in future[:6]:
            hrs = (e - now_ms) / 3.6e6
            calls = [i for i in by_exp[e] if i["option_type"] == "call"]
            strikes = sorted(i["strike"] for i in calls)
            print(f"    expiry {datetime.fromtimestamp(e/1000, timezone.utc)}"
                  f"  T+{hrs:7.1f}h  {len(calls)} calls  "
                  f"strikes {strikes[0]:.0f}..{strikes[-1]:.0f}")
        snap.setdefault("instruments", {})[cur] = instr

    section("5. Digital price from the call curve, nearest expiry")
    # P(S_T > K) ~= -dC/dK, central difference on mark prices
    cur = "BTC"
    book = snap.get("book_summary", {}).get(cur) or []
    idx = (snap.get("index", {}).get("btc_usd") or {}).get("index_price")
    instr = snap.get("instruments", {}).get(cur) or []
    exp_of = {i["instrument_name"]: i["expiration_timestamp"] for i in instr}
    strike_of = {i["instrument_name"]: i["strike"] for i in instr}
    type_of = {i["instrument_name"]: i["option_type"] for i in instr}
    now_ms = int(time.time() * 1000)
    fut = sorted({e for e in exp_of.values() if e > now_ms})
    if fut and idx:
        e = fut[0]
        calls = []
        for b in book:
            n = b.get("instrument_name")
            if exp_of.get(n) == e and type_of.get(n) == "call":
                mark = b.get("mark_price")
                if mark is not None:
                    # Deribit quotes option prices in units of the underlying
                    calls.append((strike_of[n], mark * idx, b.get("mark_iv"),
                                  b.get("open_interest")))
        calls.sort()
        print(f"  expiry {datetime.fromtimestamp(e/1000, timezone.utc)}  "
              f"spot={idx:.2f}  {len(calls)} calls")
        print(f"  {'strike':>9} {'call$':>10} {'markIV':>7} {'OI':>9} "
              f"{'P(S>K)':>8}")
        for i in range(1, len(calls) - 1):
            k0, c0, _, _ = calls[i - 1]
            k1, c1, iv1, oi1 = calls[i]
            k2, c2, _, _ = calls[i + 1]
            if k2 == k0:
                continue
            dig = -(c2 - c0) / (k2 - k0)
            print(f"  {k1:>9.0f} {c1:>10.2f} {str(iv1):>7} {str(oi1):>9} "
                  f"{dig:>8.4f}")
        snap["digital_from_calls"] = [
            {"strike": calls[i][1], "k": calls[i][0]}
            for i in range(len(calls))]

    path = os.path.join(OUT, f"snapshot_{int(time.time())}.json")
    with open(path, "w") as f:
        json.dump(snap, f, default=str)
    print(f"\nwrote {path} ({os.path.getsize(path)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
