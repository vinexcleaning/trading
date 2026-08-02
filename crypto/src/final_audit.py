"""FINAL AUDIT — every dataset, plus CROSS-SOURCE validation.

Extends audit_all_data.py with the two things it did not cover:

  A. The Binance 1-second data (9.07M bars) — never audited. Every lead-lag
     number rests on it.
  B. CROSS-SOURCE agreement. We have THREE independent BTC price feeds:
        Binance 1s klines      (lead-lag)
        Coinbase 1m candles    (B1 model input)
        Kalshi expiration_value = CF Benchmarks BRTI (all outcomes)
     If they disagree materially, something is wrong somewhere. Agreement
     across three independent sources is the strongest single check available,
     because no single-source bug can produce it.

  C. Internal consistency of the derived reports — do the JSON outputs match
     the numbers actually reported.
"""
import datetime as dt
import glob
import json
import os
from collections import Counter, defaultdict

import numpy as np

ROOT = r"C:\Users\gianf\crypto\data"
REP = r"C:\Users\gianf\crypto\reports"
FAILS = []


def hdr(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


def check(cond, label, detail=""):
    if cond:
        print(f"  PASS  {label} {detail}")
    else:
        print(f"  ** FAIL ** {label} {detail}")
        FAILS.append(label)
    return cond


# ------------------------------------------------------------ A. Binance
def audit_binance():
    hdr("A. BINANCE 1-SECOND DATA (never audited; all lead-lag rests on it)")
    loaded = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "binance_1s", "*_1s.csv"))):
        sym = os.path.basename(p).replace("_1s.csv", "")
        days = Counter()
        ms, px, vol = [], [], []
        bad = 0
        with open(p, encoding="utf-8") as f:
            next(f, None)
            for line in f:
                q = line.rstrip("\n").split(",")
                if len(q) < 4:
                    bad += 1
                    continue
                try:
                    days[q[0]] += 1
                    ms.append(int(q[1]))
                    px.append(float(q[2]))
                    vol.append(float(q[3]))
                except ValueError:
                    bad += 1
        ms = np.array(ms, dtype=np.int64)
        px = np.array(px)
        vol = np.array(vol)
        loaded[sym] = (ms, px, vol)

        n_days = len(days)
        exact = sum(1 for v in days.values() if v == 86400)
        d = np.diff(ms)
        dups = int((d == 0).sum())
        nonmono = int((d < 0).sum())
        gaps = int((d > 1000).sum())
        print(f"\n  {sym}")
        print(f"    rows={len(ms):>9}  days={n_days}  "
              f"days with EXACTLY 86400 bars: {exact}/{n_days}")
        check(bad == 0, f"{sym} parse errors", f"({bad})")
        check(dups == 0, f"{sym} duplicate timestamps", f"({dups})")
        check(nonmono == 0, f"{sym} monotone time", f"({nonmono} backwards)")
        check(exact == n_days, f"{sym} complete days",
              f"({n_days-exact} short)")
        check((px > 0).all(), f"{sym} positive prices",
              f"(min {px.min()})")
        check(gaps == 0, f"{sym} no >1s gaps", f"({gaps})")
        r = np.diff(np.log(px))
        print(f"    price {px.min():.6g} - {px.max():.6g}   "
              f"|1s ret| max {np.abs(r).max()*100:.3f}%   "
              f"zero-vol bars {100*(vol==0).mean():.2f}%")
        check(np.abs(r).max() < 0.05, f"{sym} no absurd 1s jumps",
              f"(max {np.abs(r).max()*100:.3f}%)")
    return loaded


# -------------------------------------------------------- B. cross-source
def cross_source(loaded):
    hdr("B. CROSS-SOURCE VALIDATION — three independent BTC feeds")

    # Coinbase 1-minute
    cb = {}
    p = os.path.join(ROOT, "spot", "btc_1m.jsonl")
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                c = json.loads(line)
                cb[int(c["t"])] = float(c["close"])
            except Exception:
                pass
    print(f"  Coinbase 1m bars: {len(cb)}")

    # Binance -> 1-minute closes
    if "BTCUSDT" not in loaded:
        print("  no Binance BTC, skipping")
        return
    ms, px, _ = loaded["BTCUSDT"]
    sec = ms // 1000
    minute = (sec // 60) * 60
    bn = {}
    for m_, p_ in zip(minute, px):
        bn[int(m_)] = float(p_)          # last 1s close in that minute
    print(f"  Binance minute closes: {len(bn)}")

    common = sorted(set(cb) & set(bn))
    print(f"  overlapping minutes: {len(common)}")
    if len(common) > 1000:
        a = np.array([cb[t] for t in common])
        b = np.array([bn[t] for t in common])
        basis_bp = (b - a) / a * 1e4
        rc = np.diff(np.log(a))
        rb = np.diff(np.log(b))
        corr = float(np.corrcoef(rc, rb)[0, 1])
        print(f"\n  Binance vs Coinbase, {len(common)} common minutes:")
        print(f"    basis (Binance-Coinbase): mean {basis_bp.mean():+.2f}bp  "
              f"sd {basis_bp.std():.2f}bp  "
              f"p99|.| {np.percentile(np.abs(basis_bp),99):.1f}bp")
        print(f"    1-minute return correlation: {corr:.6f}")
        check(corr > 0.99, "Binance/Coinbase return correlation > 0.99",
              f"({corr:.6f})")
        check(abs(basis_bp.mean()) < 50, "basis under 50bp",
              f"({basis_bp.mean():+.2f}bp)")

    # Kalshi BRTI settlements vs both
    settles = {}
    with open(os.path.join(ROOT, "kalshi_settled", "KXBTCD.jsonl"),
              encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            v, ct = m.get("expiration_value"), m.get("close_time")
            if v in (None, "") or not ct:
                continue
            try:
                settles[ct] = float(v)
            except ValueError:
                pass
    print(f"\n  Kalshi BRTI settlements (deduped by boundary): {len(settles)}")
    dcb, dbn = [], []
    for ct, v in settles.items():
        t = int(dt.datetime.fromisoformat(
            ct.replace("Z", "+00:00")).timestamp())
        if t - 60 in cb:
            dcb.append((v - cb[t - 60]) / v * 1e4)
        if t - 60 in bn:
            dbn.append((v - bn[t - 60]) / v * 1e4)
    for nm, d in (("Coinbase", dcb), ("Binance", dbn)):
        if len(d) < 100:
            continue
        d = np.array(d)
        print(f"    BRTI - {nm}: n={len(d)} mean {d.mean():+.2f}bp "
              f"sd {d.std():.2f}bp  p99|.| "
              f"{np.percentile(np.abs(d),99):.1f}bp")
        check(abs(d.mean()) < 50, f"BRTI vs {nm} mean basis < 50bp",
              f"({d.mean():+.2f}bp)")


# ---------------------------------------------------- C. derived reports
def audit_reports():
    hdr("C. DERIVED REPORTS — do the saved numbers match what was reported?")
    checks = [
        ("b1_KXBTCD.json", lambda j: len(j.get("results", [])) >= 4,
         "B1 has >=4 model rows"),
        ("synthetic_control.json",
         lambda j: j["gate"]["overall"] is True, "B1 synthetic gate PASSED"),
        ("mm_synthetic_control.json",
         lambda j: j["gate"]["overall"] is True, "MM synthetic gate PASSED"),
        ("leadlag.json", lambda j: j["n_bars"] > 1_000_000,
         "lead-lag used >1M bars"),
        ("streak_fade.json", lambda j: len(j) >= 30,
         "fade table has >=30 conditions"),
        ("path_streak.json", lambda j: len(j.get("touch", [])) >= 50,
         "touch matrix has >=50 cells"),
    ]
    for fn, fn_check, label in checks:
        p = os.path.join(REP, fn)
        if not os.path.exists(p):
            check(False, label, "(file missing)")
            continue
        try:
            j = json.load(open(p))
            check(bool(fn_check(j)), label)
        except Exception as e:
            check(False, label, f"({type(e).__name__})")

    # headline number consistency
    p = os.path.join(REP, "b1_KXBTCD.json")
    if os.path.exists(p):
        j = json.load(open(p))
        m2 = [r for r in j["results"] if r["model"].startswith("M2")]
        if m2:
            r = m2[0]
            print(f"\n  B1 headline re-read from disk: M2 diff="
                  f"{r['diff']:+.6f} CI [{r['ci_lo']:+.6f},{r['ci_hi']:+.6f}] "
                  f"p={r['p']:.4f}")
            check(r["ci_lo"] < 0 < r["ci_hi"],
                  "M2 CI straddles zero (the reported tie)")


# --------------------------------------------------------- D. live feeds
def audit_live():
    hdr("D. LIVE RECORDER — 15-minute opens")
    fs = sorted(glob.glob(os.path.join(ROOT, "btc15m_opens", "*.jsonl")))
    n = bad = 0
    wins = set()
    ages, noask, yesbid = [], [], []
    for p in fs:
        with open(p, encoding="utf-8") as f:
            for line in f:
                n += 1
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    bad += 1
                    continue
                wins.add(r.get("ticker"))
                ages.append(r.get("age_since_open_s"))
                for src, dst in ((r.get("no_ask"), noask),
                                 (r.get("yes_bid"), yesbid)):
                    try:
                        dst.append(float(src))
                    except (TypeError, ValueError):
                        pass
    print(f"  rows={n} parse_err={bad} distinct_windows={len(wins)}")
    check(bad == 0, "opens parse errors", f"({bad})")
    if ages:
        a = np.array([x for x in ages if x is not None])
        check(a.min() >= 0 and a.max() <= 61,
              "capture ages within the 0-60s window",
              f"({a.min():.1f}-{a.max():.1f}s)")
    if noask:
        na = np.array(noask)
        print(f"  no_ask: n={len(na)} min={na.min():.4f} "
              f"med={np.median(na):.4f} max={na.max():.4f}")
        check(((na > 0) & (na <= 1)).all(), "no_ask in (0,1]")
        print(f"  --> median no_ask so far = {np.median(na)*100:.2f}c "
              f"(the fade bar depends on this)")


def main():
    loaded = audit_binance()
    cross_source(loaded)
    audit_reports()
    audit_live()
    hdr("FINAL AUDIT SUMMARY")
    if FAILS:
        print(f"  {len(FAILS)} FAILED CHECK(S):")
        for x in FAILS:
            print(f"    - {x}")
    else:
        print("  ALL CHECKS PASSED — no defect found in any dataset.")


if __name__ == "__main__":
    main()
