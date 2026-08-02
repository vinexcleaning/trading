"""FULL DATA AUDIT — every dataset this project's conclusions rest on.

Motivated by a direct instruction: if the data is bad, every test is bad.

This project has had TWO silent-corruption incidents (correct row counts, wrong
or empty content) and one duplicate-writer incident. So nothing here trusts a
row count. Every check is content-level:

  - does every row PARSE
  - are required fields PRESENT and non-null
  - are values in PLAUSIBLE RANGES (prices in [0,1], strikes > 0, ts sane)
  - is the TIME AXIS sane (monotone where it should be, no future timestamps,
    no impossible gaps)
  - are there DUPLICATE keys (the signature of two writers)
  - do INVARIANTS hold (bid <= ask; outcome in {0,1}; settlement consistent
    within an event)
  - VARIATION check: a field that is constant or mostly-null passes any
    correlation test for free and must be flagged UNTESTABLE, not clean
"""
import datetime as dt
import glob
import json
import os
from collections import Counter, defaultdict

import numpy as np

ROOT = r"C:\Users\gianf\crypto\data"
NOW_NS = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1e9)


def hdr(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def variation(vals):
    """Flag fields that cannot be meaningfully tested."""
    nn = [v for v in vals if v is not None]
    if not nn:
        return "ALL NULL", 0
    d = len(set(nn))
    frac_null = 1 - len(nn) / len(vals)
    if d == 1:
        return f"CONSTANT ({nn[0]})", d
    if frac_null > 0.9:
        return f"{frac_null*100:.0f}% NULL", d
    return "ok", d


# ------------------------------------------------------- settled markets
def audit_settled():
    hdr("1. KALSHI SETTLED MARKETS — the outcome source for every test")
    for p in sorted(glob.glob(os.path.join(ROOT, "kalshi_settled", "*.jsonl"))):
        name = os.path.basename(p)
        n = bad = 0
        results = Counter()
        tick = Counter()
        by_event_settle = defaultdict(set)
        dup = Counter()
        strikes_bad = 0
        expv_present = 0
        closes = []
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                n += 1
                try:
                    m = json.loads(line)
                except json.JSONDecodeError:
                    bad += 1
                    continue
                dup[m.get("ticker")] += 1
                results[str(m.get("result"))] += 1
                tick[str(m.get("price_level_structure"))] += 1
                ev, v = m.get("event_ticker"), m.get("expiration_value")
                if v not in (None, ""):
                    expv_present += 1
                    fv = f(v)
                    if fv is not None and ev:
                        by_event_settle[ev].add(round(fv, 6))
                fs, cs = m.get("floor_strike"), m.get("cap_strike")
                if fs is None and cs is None:
                    strikes_bad += 1
                ct = m.get("close_time")
                if ct:
                    closes.append(ct)
        multi = sum(1 for v in by_event_settle.values() if len(v) > 1)
        dups = sum(c - 1 for c in dup.values() if c > 1)
        closes.sort()
        ok = (bad == 0 and dups == 0 and multi == 0)
        print(f"  {'OK ' if ok else 'FAIL'} {name:<16} n={n:>7} "
              f"parse_err={bad:<3} dup_tickers={dups:<3} "
              f"events={len(by_event_settle):<6} "
              f"multi_settle_events={multi:<3} "
              f"expv={100*expv_present/max(1,n):5.1f}% "
              f"no_strike={strikes_bad}")
        print(f"       results={dict(results)} "
              f"span={closes[0][:16] if closes else '-'} -> "
              f"{closes[-1][:16] if closes else '-'}")


# ---------------------------------------------------------------- panel
def audit_panel():
    hdr("2. DECISION-TIME PANEL — the input to B1 and the touch matrix")
    p = os.path.join(ROOT, "panel", "panel_KXBTCD.jsonl")
    if not os.path.exists(p):
        print("  MISSING")
        return
    rows = []
    bad = 0
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                bad += 1
    n = len(rows)
    inv_bad = sum(1 for r in rows if not (0 < r["bid"] < r["ask"] < 1))
    tau_bad = sum(1 for r in rows if r["tau_s"] <= 0)
    y_bad = sum(1 for r in rows if r["y"] not in (0.0, 1.0))
    future = sum(1 for r in rows if r["ts"] * 1e9 > NOW_NS)
    look = sum(1 for r in rows if r["ts"] > r["close_ts"])
    anchor_bad = sum(1 for r in rows if r.get("anchor_ts", 0) > r["ts"])
    key = Counter((r["ticker"], r["ts"]) for r in rows)
    dups = sum(c - 1 for c in key.values() if c > 1)
    evs = {r["event"] for r in rows}
    print(f"  rows={n} parse_err={bad} events={len(evs)} "
          f"markets={len({r['ticker'] for r in rows})}")
    print(f"  bid<ask violations : {inv_bad}")
    print(f"  tau<=0             : {tau_bad}")
    print(f"  outcome not in 0/1 : {y_bad}")
    print(f"  timestamps in future: {future}")
    print(f"  ts AFTER close (look-ahead): {look}")
    print(f"  anchor_ts AFTER decision ts (look-ahead): {anchor_bad}")
    print(f"  duplicate (ticker,ts) keys: {dups}")
    print(f"  VERDICT: {'CLEAN' if (bad or inv_bad or tau_bad or y_bad or future or look or anchor_bad or dups) == 0 else 'DEFECTS ABOVE'}")

    print("\n  variation check (a constant field passes any test for free):")
    for fld in ("bid", "ask", "mid", "spread", "vol", "oi", "K", "anchor",
                "settle", "y", "tau_s"):
        vals = [r.get(fld) for r in rows[:20000]]
        v, d = variation(vals)
        flag = "" if v == "ok" else "  <-- UNTESTABLE"
        print(f"    {fld:<10} distinct={d:<7} {v}{flag}")

    # settlement consistency: y should match settle vs K
    mism = 0
    for r in rows:
        if r.get("settle") is None:
            continue
        implied = 1.0 if float(r["settle"]) > float(r["K"]) else 0.0
        if implied != r["y"]:
            mism += 1
    print(f"\n  outcome vs (settlement > strike) mismatches: {mism} / {n} "
          f"({100*mism/max(1,n):.3f}%)   <- KXBTCD is a `greater` ladder so "
          f"these should agree")


# ------------------------------------------------------------------ spot
def audit_spot():
    hdr("3. COINBASE 1-MIN SPOT — the model input for B1")
    p = os.path.join(ROOT, "spot", "btc_1m.jsonl")
    if not os.path.exists(p):
        print("  MISSING")
        return
    ts, px = [], []
    bad = 0
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            try:
                c = json.loads(line)
                ts.append(int(c["t"]))
                px.append(float(c["close"]))
            except Exception:
                bad += 1
    ts = np.array(ts)
    px = np.array(px)
    o = np.argsort(ts)
    ts, px = ts[o], px[o]
    d = np.diff(ts)
    gaps = int((d > 60).sum())
    dups = int((d == 0).sum())
    ret = np.diff(np.log(px))
    print(f"  rows={len(ts)} parse_err={bad}")
    print(f"  span {dt.datetime.utcfromtimestamp(ts[0])} -> "
          f"{dt.datetime.utcfromtimestamp(ts[-1])}")
    print(f"  duplicate timestamps: {dups}")
    print(f"  gaps > 60s: {gaps}  (largest {d.max()/60:.0f} min)")
    print(f"  price range {px.min():.2f} - {px.max():.2f}")
    print(f"  non-positive prices: {int((px <= 0).sum())}")
    print(f"  |1-min return| > 5%: {int((np.abs(ret) > 0.05).sum())} "
          f"(max {np.abs(ret).max()*100:.2f}%)")
    print(f"  zero-return minutes: {int((ret == 0).sum())} "
          f"({100*(ret==0).mean():.1f}%)  <- a stuck feed shows up here")


# --------------------------------------------------------------- 15m opens
def audit_opens():
    hdr("4. KXBTC15M OPEN RECORDER — the live capture started this session")
    fs = sorted(glob.glob(os.path.join(ROOT, "btc15m_opens", "*.jsonl")))
    if not fs:
        print("  no files yet (recorder started 08:02 UTC; windows open at "
              ":00/:15/:30/:45)")
        return
    n = bad = 0
    wins = set()
    ages = []
    noask = []
    for p in fs:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                n += 1
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    bad += 1
                    continue
                wins.add(r.get("ticker"))
                ages.append(r.get("age_since_open_s"))
                v = f(r.get("no_ask"))
                if v is not None:
                    noask.append(v)
    print(f"  rows={n} parse_err={bad} distinct_windows={len(wins)}")
    if ages:
        a = np.array([x for x in ages if x is not None])
        print(f"  age since open: min={a.min():.1f}s max={a.max():.1f}s "
              f"(should be 0-60)")
    if noask:
        na = np.array(noask)
        print(f"  no_ask: n={len(na)} min={na.min():.4f} med={np.median(na):.4f} "
              f"max={na.max():.4f}")
        print(f"  no_ask in [0.40,0.60] (near-50c as expected at open): "
              f"{100*((na>=0.40)&(na<=0.60)).mean():.1f}%")


# --------------------------------------------------------------- recorder
def audit_recorder():
    hdr("5. MAIN RECORDER — kalshi_quotes / poly_books")
    for src in ("kalshi_quotes", "poly_books", "poly_trades"):
        fs = sorted(glob.glob(os.path.join(ROOT, src, "*", "*", "*.jsonl")))
        n = bad = 0
        empties = 0
        for p in fs[-3:]:
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    n += 1
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        bad += 1
                        continue
                    if src == "poly_books":
                        if not (r.get("bids") or r.get("asks")):
                            empties += 1
                    elif src == "kalshi_quotes":
                        if r.get("yes_bid") is None and r.get("yes_ask") is None:
                            empties += 1
        print(f"  {src:<14} files={len(fs):<4} sampled_rows={n:<8} "
              f"parse_err={bad:<3} empty_content={empties}")


def main():
    audit_settled()
    audit_panel()
    audit_spot()
    audit_opens()
    audit_recorder()
    print("\n" + "=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()
