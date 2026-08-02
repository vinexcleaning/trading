"""TASK 6: recorder health — CONTENT validation, not row counts.

Row counts were the check that missed a silent orderbook parse failure in this
project's history (correct counts, empty content). So this asserts schema,
non-emptiness and plausible value ranges on a sample of RECENT rows, checks
keyframes are landing, checks for duplicate writer processes, and logs gaps.
"""
import datetime as dt
import glob
import json
import os
import subprocess
from collections import Counter, defaultdict

import numpy as np

DATA = r"C:\Users\gianf\crypto\data"
GAPS = os.path.join(DATA, "gaps_report.md")


def recent_rows(source, n=4000):
    files = sorted(glob.glob(os.path.join(DATA, source, "*", "*", "*.jsonl")))
    rows = []
    for p in reversed(files):
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    rows.append({"__parse_error__": True})
        if len(rows) >= n:
            break
    return rows[-n:], files


def check_kalshi(rows):
    req = ["venue", "series", "ticker", "event_ticker", "yes_bid", "yes_ask",
           "ts_recv_ns", "ts_write_ns"]
    issues = Counter()
    prices = []
    for r in rows:
        if r.get("__parse_error__"):
            issues["parse_error"] += 1
            continue
        for k in req:
            if k not in r:
                issues[f"missing:{k}"] += 1
        b, a = r.get("yes_bid"), r.get("yes_ask")
        if b is None and a is None:
            issues["both_prices_null"] += 1
            continue
        try:
            bf = float(b) if b is not None else None
            af = float(a) if a is not None else None
        except (TypeError, ValueError):
            issues["unparseable_price"] += 1
            continue
        for v in (bf, af):
            if v is not None:
                if not (0.0 <= v <= 1.0):
                    issues["price_out_of_range"] += 1
                prices.append(v)
        if bf is not None and af is not None and bf > af:
            issues["crossed_quote"] += 1
        # timestamps must be ordered: event <= recv <= write
        te, tr, tw = (r.get("ts_event_ns"), r.get("ts_recv_ns"),
                      r.get("ts_write_ns"))
        if tr and tw and tr > tw:
            issues["recv_after_write"] += 1
        if te and tr and te > tr + 5 * 10**9:
            issues["event_after_recv"] += 1
    return issues, prices


def check_poly(rows):
    issues = Counter()
    depths = []
    for r in rows:
        if r.get("__parse_error__"):
            issues["parse_error"] += 1
            continue
        for k in ("slug", "token_id", "bids", "asks", "ts_recv_ns"):
            if k not in r:
                issues[f"missing:{k}"] += 1
        bids, asks = r.get("bids") or [], r.get("asks") or []
        if not bids and not asks:
            issues["empty_book"] += 1
            continue
        depths.append(len(bids) + len(asks))
        for lv in (bids + asks)[:40]:
            try:
                p, s = float(lv[0]), float(lv[1])
            except (TypeError, ValueError, IndexError):
                issues["unparseable_level"] += 1
                continue
            if not (0 < p <= 1):
                issues["price_out_of_range"] += 1
            if s <= 0:
                issues["nonpositive_size"] += 1
    return issues, depths


def main():
    print("=" * 92)
    print(f"RECORDER HEALTH — {dt.datetime.now(dt.timezone.utc).isoformat()}")
    print("=" * 92)

    # ---- duplicate writers -------------------------------------------------
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Select-Object -ExpandProperty CommandLine"],
        capture_output=True, text=True).stdout
    recs = [l for l in out.splitlines() if "recorder.py" in l]
    print(f"\n1. WRITER PROCESSES")
    print(f"   recorder.py instances: {len(recs)} "
          f"-> {'OK' if len(recs) == 1 else '*** DUPLICATE WRITERS'}")
    others = [l for l in out.splitlines()
              if "python" in l.lower() and "recorder.py" not in l and l.strip()]
    for o in others:
        tag = "OTHER SESSION" if "crypto" not in o else "ours"
        print(f"   [{tag}] {o.strip()[:96]}")

    # ---- content validation ------------------------------------------------
    print(f"\n2. CONTENT VALIDATION (schema / ranges / ordering, "
          f"not row counts)")
    kr, kf = recent_rows("kalshi_quotes")
    ki, kp = check_kalshi(kr)
    print(f"   kalshi_quotes: {len(kr)} recent rows across {len(kf)} files")
    print(f"     issues: {dict(ki) if ki else 'NONE'}")
    if kp:
        kp = np.array(kp)
        print(f"     price range {kp.min():.4f}-{kp.max():.4f}, "
              f"median {np.median(kp):.4f}  "
              f"-> {'plausible' if 0 <= kp.min() and kp.max() <= 1 else 'IMPLAUSIBLE'}")

    pr, pf = recent_rows("poly_books")
    pi, pd_ = check_poly(pr)
    print(f"   poly_books: {len(pr)} recent rows across {len(pf)} files")
    print(f"     issues: {dict(pi) if pi else 'NONE'}")
    if pd_:
        print(f"     book depth (levels): median {int(np.median(pd_))}, "
              f"max {max(pd_)} -> "
              f"{'non-empty' if np.median(pd_) > 0 else 'EMPTY BOOKS'}")

    # ---- keyframes ---------------------------------------------------------
    print(f"\n3. KEYFRAMES (required for complete-ladder A1 scans)")
    kfc = sum(1 for r in kr if r.get("keyframe") is True)
    print(f"   {kfc}/{len(kr)} of recent rows are keyframes "
          f"-> {'landing' if kfc > 0 else '*** NOT LANDING'}")

    # ---- gaps --------------------------------------------------------------
    print(f"\n4. GAPS")
    lines = ["# gaps_report.md", "",
             f"Generated {dt.datetime.now(dt.timezone.utc).isoformat()}", ""]
    for src in ("kalshi_quotes", "poly_books", "poly_trades"):
        rows, files = recent_rows(src, n=20000)
        ts = sorted(r.get("ts_recv_ns") for r in rows
                    if r.get("ts_recv_ns"))
        if len(ts) < 10:
            continue
        d = np.diff(ts) / 1e9
        gaps = [(a, b) for a, b in zip(ts, ts[1:]) if (b - a) / 1e9 > 60]
        print(f"   {src}: {len(ts)} rows, median inter-row "
              f"{np.median(d):.2f}s, {len(gaps)} gaps > 60s")
        lines.append(f"## {src}")
        lines.append(f"- rows examined: {len(ts)}")
        lines.append(f"- median inter-row gap: {np.median(d):.2f}s")
        lines.append(f"- gaps > 60s: {len(gaps)}")
        for a, b in gaps[:10]:
            lines.append(
                f"  - {dt.datetime.fromtimestamp(a/1e9, dt.timezone.utc)} -> "
                f"{dt.datetime.fromtimestamp(b/1e9, dt.timezone.utc)} "
                f"({(b-a)/1e9:.0f}s)")
        lines.append("")
        if gaps:
            lines.append("Cause: recorder polls every 5s and writes ON CHANGE; "
                         "a gap means no quote in any tracked market changed, "
                         "or the poll failed. Keyframes every 24 cycles bound "
                         "the maximum silent interval at ~2 min.")
            lines.append("")
    with open(GAPS, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n   wrote {GAPS}")


if __name__ == "__main__":
    main()
