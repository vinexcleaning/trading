"""Why does the event panel lose so many events, and where exactly?

The first grid run had 2,779 settled esports events available and only 271 with
a usable panel. A 90% loss between "settled" and "analysable" is either a data
fact worth reporting or a bug in my own filter, and the difference matters:
GUARDS #8's whole point is that the denominator has to be honest.

Reports the attrition step by step, per series, so the loss is attributed rather
than absorbed silently.
"""
from __future__ import annotations

import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "kalshi_soccer.db"
con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=120)


def ts(s):
    if not s:
        return None
    for f in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(s, f).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    return None


SERIES = ["KXCS2GAME", "KXLOLGAME", "KXVALORANTGAME", "KXMLBGAME"]
print(f"{'series':16} {'settled_ev':>10} {'has_cand':>9} {'any_2sided':>10} "
      f"{'q@-60m':>8} {'q@-6h':>7} {'q@-24h':>8}")
for s in SERIES:
    evs = {}
    for ev, tk, res, ct in con.execute(
            "select event_ticker, ticker, result, close_time from markets "
            "where series=? and result in ('yes','no')", (s,)):
        evs.setdefault(ev, []).append((tk, res, ct))
    n_settled = len(evs)
    has_c = two = q60 = q6h = q24 = 0
    lead_hours = []
    for ev, mk in evs.items():
        mk.sort(key=lambda x: x[0])
        tk, res, ct = mk[0]
        close = ts(ct)
        rows = con.execute(
            "select end_period_ts, yes_bid_close, yes_ask_close from candles "
            "where ticker=? order by end_period_ts", (tk,)).fetchall()
        if not rows:
            continue
        has_c += 1
        good = [(t, b, a) for t, b, a in rows if b is not None and a is not None]
        if not good:
            continue
        two += 1
        if close:
            first = min(t for t, _, _ in good)
            lead_hours.append((close - first) / 3600.0)
            for lim, box in ((60, "q60"), (360, "q6h"), (1440, "q24")):
                cut = close - lim * 60
                if any(t < cut for t, _, _ in good):
                    if box == "q60":
                        q60 += 1
                    elif box == "q6h":
                        q6h += 1
                    else:
                        q24 += 1
    print(f"{s:16} {n_settled:>10} {has_c:>9} {two:>10} {q60:>8} {q6h:>7} "
          f"{q24:>8}")
    if lead_hours:
        lead_hours.sort()
        n = len(lead_hours)
        print(f"                 hours of quoted history before close: "
              f"p10={lead_hours[n//10]:.1f} med={lead_hours[n//2]:.1f} "
              f"p90={lead_hours[9*n//10]:.1f} max={lead_hours[-1]:.1f}")

print("\n== is the loss CANDLES MISSING or QUOTES MISSING? (esports, sample)")
miss = Counter()
for s in ["KXCS2GAME"]:
    for ev, tk, ct in con.execute(
            "select event_ticker, ticker, close_time from markets "
            "where series=? and result in ('yes','no') limit 400", (s,)):
        n = con.execute("select count(*) from candles where ticker=?",
                        (tk,)).fetchone()[0]
        if n == 0:
            miss["no candle rows at all"] += 1
            continue
        g = con.execute("select count(*) from candles where ticker=? and "
                        "yes_bid_close is not null and yes_ask_close is not null",
                        (tk,)).fetchone()[0]
        miss["candles, 0 two-sided" if g == 0 else "candles with two-sided"] += 1
print(f"   {dict(miss)}")
con.close()
