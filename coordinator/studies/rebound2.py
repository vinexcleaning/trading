"""Tennis rebound study, v2.

v1 was quadratic in two places and would not have finished: it recomputed
max(future) for every candle, and rescanned the whole control pool per event.
Both are single-pass here.

ONE DEFINITION CHANGED AND IT IS BETTER. "Returns to the prior peak" now means
"trades back to the TRIGGER level P" rather than to the exact realised peak.
That is event-independent, so the identical outcome can be counted for controls
-- and it is the question actually being asked: does an 80c player get back to
80c.

THE CONTROL IS THE WHOLE POINT. For each treated event -- peaked at >= P, now
dipped -- the comparison is every ticker-minute in the same competition, same
third of the match, same 10-cent price band, whose running peak had NOT yet
reached P. Same place, different history. If the lift is zero the path carried
nothing the price did not already contain.

No look-ahead: the trigger uses the running peak at or before the candle, the
outcome uses only candles strictly after it.
"""
from __future__ import annotations
import json, math, sqlite3, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(r"C:/Users/vinig/trading")
sys.path.insert(0, str(REPO))
from common.kalshi_fees import fee_order_dollars

DB = REPO / "set1_overshoot" / "data" / "maker.db"
PEAKS = [70, 75, 80, 85, 90]
DEST = [30, 40, 50, 60]
DRAW = [10, 20, 30, 40, 50]
ABS = [50, 60, 70, 80]
REL = [10, 20, 30]
MIN_CELL = 30
CUTOFF = "2026-08-01"


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, c - h), min(1.0, c + h))


def _cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def ztest(k1, n1, k2, n2):
    if n1 == 0 or n2 == 0:
        return (0.0, 1.0)
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return (0.0, 1.0)
    z = (p1 - p2) / se
    return (z, 2 * (1 - _cdf(abs(z))))


def bh(pv, q=0.05):
    if not pv:
        return set()
    order = sorted(range(len(pv)), key=lambda i: pv[i])
    m = len(pv)
    t = 0
    for r, i in enumerate(order, 1):
        if pv[i] <= q * r / m:
            t = r
    return {i for r, i in enumerate(order, 1) if r <= t}


def paths(conn, series_filter):
    meta = {}
    for r in conn.execute("SELECT ticker,series,result,close_time FROM markets"):
        if r["result"] not in ("yes", "no"):
            continue
        if series_filter and r["series"] not in series_filter:
            continue
        meta[r["ticker"]] = {"series": r["series"],
                             "won": 1 if r["result"] == "yes" else 0,
                             "close": str(r["close_time"])}
    cur = conn.execute("SELECT ticker,ts,bid_c,ask_c FROM candles "
                       "WHERE bid_c IS NOT NULL AND ask_c IS NOT NULL "
                       "ORDER BY ticker,ts")
    t0, buf = None, []
    for r in cur:
        t = r["ticker"]
        if t != t0:
            if t0 in meta and len(buf) >= 30:
                yield t0, meta[t0], buf
            t0, buf = t, []
        if t in meta:
            b, a = r["bid_c"], r["ask_c"]
            if 0 < b <= a < 100 and (a - b) <= 25:
                buf.append((b, a, (b + a) / 2.0))
    if t0 in meta and len(buf) >= 30:
        yield t0, meta[t0], buf


def main(series_filter, out_path, label):
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    events = defaultdict(list)
    base = defaultdict(lambda: {"n": 0, "abs": defaultdict(int),
                                "rel": defaultdict(int), "toP": 0, "win": 0})
    n_tick = 0
    for tk, m, path in paths(conn, series_filter):
        n_tick += 1
        won, series = m["won"], m["series"]
        seg = "train" if m["close"] < CUTOFF else "test"
        n = len(path)
        fmax = [0.0] * n
        run = 0.0
        for i in range(n - 1, -1, -1):
            fmax[i] = run
            if path[i][2] > run:
                run = path[i][2]
        peak = path[0][2]
        fired = set()
        for i, (bid, ask, mid) in enumerate(path):
            if mid > peak:
                peak = mid
            if i == n - 1:
                continue
            frac = i / n
            phase = "early" if frac < 0.33 else ("mid" if frac < 0.66 else "late")
            lvl = int(mid // 10) * 10
            fm = fmax[i]
            for P in PEAKS:
                if peak >= P:
                    for kind, vals in (("dest", DEST), ("draw", DRAW)):
                        for V in vals:
                            ok = (mid <= V) if kind == "dest" else (peak - mid >= V)
                            if not ok:
                                continue
                            cell = (P, kind, V)
                            if cell in fired:
                                continue
                            fired.add(cell)
                            events[cell].append({
                                "seg": seg, "series": series, "phase": phase,
                                "lvl": lvl, "won": won, "mid": mid, "bid": bid,
                                "ask": ask, "fmax": fm, "peak": peak, "tk": tk,
                                "fut": path[i + 1:]})
                else:
                    d = base[(series, phase, lvl, P)]
                    d["n"] += 1
                    for X in ABS:
                        if fm >= X:
                            d["abs"][X] += 1
                    for X in REL:
                        if fm >= mid + X:
                            d["rel"][X] += 1
                    if fm >= P:
                        d["toP"] += 1
                    d["win"] += won
    conn.close()

    rows, pv = [], []
    outs = ([("toP", None)] + [("abs", x) for x in ABS]
            + [("rel", x) for x in REL] + [("win", None)])
    for (P, kind, V), evs in sorted(events.items()):
        for seg in ("train", "test", "all"):
            sel = evs if seg == "all" else [e for e in evs if e["seg"] == seg]
            if not sel:
                continue
            for ok, oa in outs:
                if ok == "toP":
                    k = sum(1 for e in sel if e["fmax"] >= P)
                elif ok == "abs":
                    k = sum(1 for e in sel if e["fmax"] >= oa)
                elif ok == "rel":
                    k = sum(1 for e in sel if e["fmax"] >= e["mid"] + oa)
                else:
                    k = sum(e["won"] for e in sel)
                n = len(sel)
                bk = bn = 0
                for e in sel:
                    d = base.get((e["series"], e["phase"], e["lvl"], P))
                    if not d or d["n"] == 0:
                        continue
                    bn += d["n"]
                    if ok == "toP":
                        bk += d["toP"]
                    elif ok == "abs":
                        bk += d["abs"][oa]
                    elif ok == "rel":
                        bk += d["rel"][oa]
                    else:
                        bk += d["win"]
                rate, lo, hi = wilson(k, n)
                brate, _, _ = wilson(bk, bn)
                z, p = ztest(k, n, bk, bn)
                sparse = n < MIN_CELL or bn < MIN_CELL
                rows.append({"peak": P, "dip": f"{kind}{V}", "seg": seg,
                             "outcome": f"{ok}{'' if oa is None else ':' + str(oa)}",
                             "n": n, "hits": k, "rate": round(rate, 4),
                             "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
                             "base_n": bn, "base_rate": round(brate, 4),
                             "lift": round(rate - brate, 4), "z": round(z, 2),
                             "p": round(p, 6), "sparse": sparse})
                if seg == "test" and not sparse:
                    pv.append(p)
    keep = bh(pv)
    i = 0
    for r in rows:
        if r["seg"] == "test" and not r["sparse"]:
            r["bh"] = i in keep
            i += 1
        else:
            r["bh"] = None
    Path(out_path).write_text(json.dumps(
        {"label": label, "n_tickers": n_tick, "rows": rows}, indent=1),
        encoding="utf-8")

    print(f"=== {label}: {n_tick} settled tickers, {len(rows)} cells")
    for oname, title in (("win", "ULTIMATE WIN"),
                         ("toP", "RETURNS TO THE PEAK LEVEL")):
        sel = [r for r in rows if r["seg"] == "test"
               and r["outcome"] == oname and not r["sparse"]]
        print(f"\n{title} -- out-of-sample, non-sparse, sorted by lift")
        print(f"{'peak':>5}{'dip':>9}{'n':>6}{'rate':>8}{'base':>8}"
              f"{'lift':>8}{'p':>10}  BH")
        for r in sorted(sel, key=lambda x: -x["lift"])[:12]:
            print(f"{r['peak']:>5}{r['dip']:>9}{r['n']:>6}{100*r['rate']:>7.1f}%"
                  f"{100*r['base_rate']:>7.1f}%{100*r['lift']:>+7.1f}"
                  f"{r['p']:>10.5f}  {'YES' if r['bh'] else '-'}")
        if not sel:
            print("   (no non-sparse cells)")

    print("\nMONEY -- out-of-sample, buy at the ASK on the dip, sell at the BID")
    print(f"{'peak':>5}{'dip':>9}{'exit':>6}{'n':>6}{'ROI':>9}{'hit':>7}{'avg$':>9}")
    for (P, kind, V), evs in sorted(events.items()):
        sel = [e for e in evs if e["seg"] == "test"]
        if len(sel) < MIN_CELL:
            continue
        for xt in (60, 70, 80):
            pnl = []
            for e in sel:
                cost = e["ask"] / 100.0 + float(fee_order_dollars(int(e["ask"]), 1))
                got = None
                for (b, a, md) in e["fut"]:
                    if b >= xt:
                        got = b / 100.0 - float(fee_order_dollars(int(b), 1))
                        break
                pnl.append((got if got is not None
                            else (1.0 if e["won"] else 0.0)) - cost)
            st = sum(e["ask"] / 100.0 + float(fee_order_dollars(int(e["ask"]), 1))
                     for e in sel)
            print(f"{P:>5}{kind + str(V):>9}{xt:>6}{len(sel):>6}"
                  f"{100 * sum(pnl) / st:>+8.1f}%"
                  f"{100 * sum(1 for x in pnl if x > 0) / len(pnl):>6.1f}%"
                  f"{sum(pnl) / len(pnl):>+9.3f}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", nargs="*")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", required=True)
    a = ap.parse_args()
    main(a.series, a.out, a.label)
