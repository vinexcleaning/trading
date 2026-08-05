"""Find an anchor that is genuinely PRE-MATCH, by measurement not by assumption.

The pre-registered leak gate voided the -60min anchor on esports: 13.96% of
quotes extreme (<=2c or >=98c) and **99.7% of those correct**. A real pre-match
market cannot do that. At -6h it is still 2.34% extreme and **100% correct**.

The cause is a modelling error of mine, not a market fact. `close_time` is when
the market SETTLES, not when the match starts. A best-of-3 CS2 series runs
1.5-3 hours and settlement follows it, so "60 minutes before close" is usually
mid-match and sometimes after the result is known. The canary caught it, which
is what T010/T011 exists for - there, a -0h anchor had 4.1% of quotes outside
2c-98c and 100% of them correct, and the fix was to move the anchor back until
the signature disappeared.

Two things measured here:
  1. does the market record carry a real START time, so the anchor can be set
     from the event rather than guessed backwards from settlement?
  2. the full sweep: at what lead time does the extreme-correct signature go
     away, per series?

Nothing is chosen here. This produces the evidence; the anchor choice is then
amended in PREREGISTRATION.md with its reason, before any strategy re-runs.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "kalshi_soccer.db"
REP = ROOT / "reports"

SERIES = ["KXCS2GAME", "KXLOLGAME", "KXVALORANTGAME", "KXMLBGAME"]
ANCHORS = [0, 30, 60, 120, 180, 360, 720, 1440, 2880, 4320]


def ts(s):
    if not s:
        return None
    for f in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(s, f).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=120)

    # --- 1. what time fields does the market record actually carry? ---
    print("== time fields present in the stored market JSON (esports sample)")
    keys = Counter()
    samples = []
    for (raw,) in con.execute(
            "select raw from markets where series='KXCS2GAME' "
            "and result in ('yes','no') limit 300"):
        try:
            d = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for k, v in d.items():
            if any(w in k.lower() for w in ("time", "date", "ts", "expir")):
                keys[k] += 1
                if len(samples) < 3 and k not in ("close_time",):
                    pass
        if len(samples) < 2:
            samples.append({k: v for k, v in d.items()
                            if any(w in k.lower()
                                   for w in ("time", "date", "expir"))})
    for k, n in keys.most_common():
        print(f"   {k:26} present on {n}/300")
    for s in samples:
        print(f"   sample: {json.dumps(s)[:400]}")

    # --- 2. the anchor sweep, per series ---
    print(f"\n== ANCHOR SWEEP — extreme quotes and how often they are correct")
    print("   A clean anchor has either no extremes, or extremes that are NOT "
          "near-perfectly correct.")
    out = {}
    for s in SERIES:
        evs = {}
        for ev, tk, res, ct in con.execute(
                "select event_ticker, ticker, result, close_time from markets "
                "where series=? and result in ('yes','no')", (s,)):
            evs.setdefault(ev, []).append((tk, res, ct))
        rows = []
        for ev, mk in evs.items():
            mk.sort(key=lambda x: x[0])
            tk, res, ct = mk[0]
            close = ts(ct)
            if close is None:
                continue
            cds = con.execute(
                "select end_period_ts, yes_bid_close, yes_ask_close from candles "
                "where ticker=? and yes_bid_close is not null "
                "and yes_ask_close is not null order by end_period_ts",
                (tk,)).fetchall()
            if cds:
                rows.append((close, 1 if res == "yes" else 0, cds))
        print(f"\n   {s}  ({len(rows)} events)")
        print(f"     {'lead':>7} {'n':>6} {'%extreme':>9} {'%correct':>9}  verdict")
        ser = {}
        for a in ANCHORS:
            n = ext = right = 0
            for close, won, cds in rows:
                cut = close - a * 60
                best = None
                for t, b, ask in cds:
                    if t < cut:
                        best = (t, b, ask)
                if not best:
                    continue
                n += 1
                ask = best[2]
                if ask <= 2.0 or ask >= 98.0:
                    ext += 1
                    if (ask >= 98.0) == bool(won):
                        right += 1
            pe = 100 * ext / n if n else None
            pc = 100 * right / ext if ext else None
            # The pre-registered VOID condition, applied uniformly.
            if pc is not None and pc >= 99.0 and (pe or 0) > 1.0:
                v = "VOID — leak signature"
            elif n < 100:
                v = "UNTESTABLE — n<100"
            else:
                v = "clean"
            ser[a] = {"n": n, "pct_extreme": pe, "pct_correct": pc,
                      "verdict": v}
            print(f"     {a:>6}m {n:>6} "
                  f"{('-' if pe is None else f'{pe:8.2f}%')} "
                  f"{('-' if pc is None else f'{pc:8.1f}%')}  {v}")
        out[s] = ser

    (REP / "anchor_sweep.json").write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
    # THE RULE IS MONOTONE CLEANLINESS, NOT FIRST-CLEAN.
    #
    # v1 of this file took the smallest anchor labelled clean and it was wrong.
    # KXVALORANTGAME reads "clean" at 30m on 98.5% correct - just under a hard
    # 99% cutoff - and then VOID at 60m, 120m and 180m. A single reading that
    # slips under a threshold is not evidence the leak is gone; the leak
    # signature must be absent at that lead AND at every longer one. Same class
    # of error as the fixed 0.25c tolerance in validate_engine.py: a hard
    # threshold applied to a noisy statistic.
    print("\n== earliest MONOTONE-CLEAN anchor (clean here AND at every "
          "longer lead), n>=100")
    chosen = {}
    for s, ser in out.items():
        pick = None
        for i, a in enumerate(ANCHORS):
            tail = ANCHORS[i:]
            if all(ser[t]["verdict"] == "clean" for t in tail
                   if ser[t]["n"] >= 100) and ser[a]["n"] >= 100 \
                    and ser[a]["verdict"] == "clean":
                pick = a
                break
        chosen[s] = pick
        first_clean = next((a for a in ANCHORS
                            if ser[a]["verdict"] == "clean"), None)
        note = ""
        if first_clean is not None and pick is not None and first_clean < pick:
            note = (f"   (first-clean would have said {first_clean}m — "
                    f"a borderline reading, rejected)")
        print(f"   {s:18} {pick if pick else 'NONE'}{'m' if pick else ''}"
              f"   n={ser[pick]['n'] if pick else '-'}{note}")
    uniform = max(v for v in chosen.values() if v is not None)
    print(f"\n   A SINGLE anchor clean for every series: {uniform}m "
          f"(-{uniform/60:.0f}h)")
    tot = sum(out[s][uniform]["n"] for s in out if s != "KXMLBGAME")
    print(f"   test-family events surviving at that uniform anchor: {tot}")
    out["_chosen_per_series"] = chosen
    out["_uniform_anchor_min"] = uniform
    print("\nwrote reports/anchor_sweep.json")
    con.close()


if __name__ == "__main__":
    main()
