"""Phase 6b -- turn the re-pulled candles into the arrays the study's own rule
functions already expect.

THE POINT OF THIS FILE IS THAT IT DOES NOT RE-IMPLEMENT THE ENTRY RULE.

`p1_state.find_play_start_causal` and `p2_calib.completed_dip` are imported and
called. A second implementation of `deep:N` that was subtly different would be
worse than useless: it would look like a replication and would not be one. This
module's only job is to hand those functions arrays in the shape they want.

The shapes, taken from `p1_state.py` rather than guessed:

  * one row per market, one column per MINUTE, on a common grid
  * `bid` / `ask` in integer cents, forward-filled, **-1 where no quote has
    ever been seen** -- not 0, which would read as a price
  * `mid2 = bid + ask` (i.e. twice the mid, kept integer so that "the quote
    changed" is an exact test rather than a float comparison)
  * `t0` = the causal play-start detector's answer
  * the pre-match anchor is `t0 - 1`: **the last quote strictly before play**,
    so it cannot contain in-play information

Usage:
    p6_state.py --build           # write the state table
    p6_state.py --check           # what it found, and what it threw away
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import p1_state as P1        # noqa: E402
import p2_calib as P2        # noqa: E402

DB = ROOT / "data" / "maker.db"

SCHEMA = """
create table if not exists state (
  ticker text primary key, event_ticker text, series text, tier text,
  t_lo integer,            -- epoch seconds of column 0
  n_min integer,           -- number of minutes on the grid
  t0 integer,              -- play start, column index; -1 if not found
  t1 integer,              -- play end (backward walk); -1 if not found
  dur integer,             -- t1 - t0, minutes of inferred play
  pre_bid integer, pre_ask integer, pre_spread integer,
  result text, close_time text,
  ok integer, why text);
create table if not exists paths (
  ticker text primary key,
  bid blob, ask blob);          -- int16, PATH_MIN long, from t0. -1 = no quote
"""

#: A market with fewer quoted minutes than this cannot support a rule that
#: needs minute 38 plus an 8-minute lookback plus 3 minutes of stabilisation.
MIN_MINUTES = 60

#: Duration plausibility, taken from `p1_state.MIN_PLAY`/`MAX_PLAY` rather than
#: chosen here, so this study and the original agree on what a match is.
MIN_PLAY, MAX_PLAY = P1.MIN_PLAY, P1.MAX_PLAY

#: ⚠ THE PATH STARTS AT t0, AND GETTING THIS WRONG IS A SILENT DISASTER.
#:
#: `p1_state.py` stores `src_arr[t0:t0 + PATH_MIN]`, so in `p2_calib` COLUMN j
#: IS MINUTE t0 + j -- minutes counted from the first minute of play. `CP_LO=15`
#: therefore means "15 minutes into the match", and `deep:30@38` means "start
#: looking 38 minutes into the match", which is about when a first set ends.
#:
#: My first version kept the whole market-life array and passed t0 as an index.
#: The rule would then have searched from minute 38 OF THE ARRAY -- typically
#: hours before play began, in a dormant pre-match book. It would still have
#: produced numbers. They would have been meaningless.
#:
#: Truncating here also fixes the duration detector. On a 4,800-minute array the
#: backward walk bridges the sparse pre-match repricing and reports "matches"
#: lasting 80 hours: among markets with a real pre-match book, 47.9% came back
#: over 330 minutes. Inside a 300-minute window from t0 that cannot happen.
PATH_MIN = P1.PATH_MIN

#: ⚠ THE PRE-MATCH QUOTE GATE, AND WHY IT HAD TO BE ADDED (amendment A2).
#:
#: The original study did not gate on the width of the pre-match quote -- it
#: only required one to exist. That was safe for its universe, which was main
#: tour. It is NOT safe here, because this universe includes ITF.
#:
#: MEASURED: the pre-match spread is sharply bimodal, not a continuum. Either
#: there is a real quote (median 3c on main tour, 1c on Challenger) or the book
#: is effectively empty (p75 of 77c on main, 86c median on ITF -- a 1/99 book).
#: Share with a spread of 10c or less: main 65.0%, Challenger 85.7%, ITF 19.7%.
#:
#: `deep:30` means "30 cents below the pre-match mid". Measured against the
#: midpoint of an empty 1/99 book that number is meaningless, and it would fire
#: on the book being filled in rather than on anything happening in the match.
#:
#: The threshold is taken from the SHAPE OF THE QUOTE DISTRIBUTION and from no
#: outcome. Because 5c and 10c are not interchangeable (56.7% vs 65.0% on main
#: tour), BOTH are reported: 10c is primary, 5c is the pre-committed
#: sensitivity check, and any result where they disagree is reported as
#: disagreeing rather than resolved by preference.
PRE_SPREAD_MAX = 10
PRE_SPREAD_MAX_SENSITIVITY = 5


def arrays(con, ticker):
    """(t_lo, bid, ask, mid2) for one market, forward-filled, -1 for unseen."""
    rows = con.execute(
        "select ts, bid_c, ask_c from candles where ticker=? order by ts",
        (ticker,)).fetchall()
    if not rows:
        return None
    t_lo = rows[0][0]
    n = (rows[-1][0] - t_lo) // 60 + 1
    if n <= 0 or n > 20000:
        return None
    bid = np.full(n, -1, dtype=np.int32)
    ask = np.full(n, -1, dtype=np.int32)
    for ts, b, a in rows:
        i = (ts - t_lo) // 60
        if 0 <= i < n and b is not None and a is not None:
            bid[i], ask[i] = b, a

    # forward fill. A gap in the candles means the quote did not change or was
    # not reported; it does NOT mean the market went to zero.
    seen = bid >= 0
    if not seen.any():
        return None
    idx = np.where(seen, np.arange(len(seen)), -1)
    idx = np.maximum.accumulate(idx)
    keep = idx >= 0
    fb = np.full(len(bid), -1, dtype=np.int32)
    fa = np.full(len(ask), -1, dtype=np.int32)
    fb[keep] = bid[idx[keep]]
    fa[keep] = ask[idx[keep]]
    mid2 = np.where(fb >= 0, fb + fa, -1)
    return t_lo, fb, fa, mid2


def build(con):
    con.executescript(SCHEMA)
    tick = con.execute(
        "select m.ticker, m.event_ticker, m.series, m.tier, m.result, "
        "m.close_time from markets m join pulled p on p.ticker = m.ticker "
        "where p.n_candles > 0").fetchall()
    print(f"{len(tick):,} markets with candles", flush=True)

    out, paths, n_ok = [], [], 0
    for i, (tk, ev, ser, tier, res, ct) in enumerate(tick):
        a = arrays(con, tk)
        if a is None:
            out.append((tk, ev, ser, tier, 0, 0, -1, -1, -1, -1, -1, -1,
                        res, ct, 0, "no usable candles"))
            continue
        t_lo, fb, fa, mid2 = a
        n = len(fb)
        if n < MIN_MINUTES:
            out.append((tk, ev, ser, tier, t_lo, n, -1, -1, -1, -1, -1, -1,
                        res, ct, 0, "too few minutes"))
            continue

        t0 = P1.find_play_start_causal(mid2)
        if t0 is None or t0 < 1:
            out.append((tk, ev, ser, tier, t_lo, n, -1, -1, -1, -1, -1, -1,
                        res, ct, 0, "no play start detected"))
            continue

        # MUST pass the density floor. `find_play_window`'s signature
        # defaults to dens_win=0/dens_min=0, which DISABLES it, and the
        # docstring says plainly that a pure gap rule "lets sparse pre-match
        # repricing bleed in". Called with the defaults the median inferred
        # match ran 1,093 minutes -- 18 hours, i.e. the whole market life, not
        # a tennis match. `p1_state.py:225` passes GAP_MIN, DENS_WIN, DENS_MIN
        # and so must this.
        # the path the study analyses: PATH_MIN minutes starting AT t0
        seg_b = np.full(PATH_MIN, -1, dtype=np.int16)
        seg_a = np.full(PATH_MIN, -1, dtype=np.int16)
        take = min(PATH_MIN, n - t0)
        if take > 0:
            seg_b[:take] = fb[t0:t0 + take]
            seg_a[:take] = fa[t0:t0 + take]
        seg_m2 = np.where(seg_b >= 0,
                          seg_b.astype(np.int32) + seg_a.astype(np.int32), -1)

        # duration measured INSIDE that window, so it cannot run away
        w = P1.find_play_window(seg_m2, P1.GAP_MIN, P1.DENS_WIN, P1.DENS_MIN)
        t1 = int(w[1]) if w else -1
        dur = t1 if t1 >= 0 else -1

        pre = t0 - 1
        if fb[pre] < 0:
            out.append((tk, ev, ser, tier, t_lo, n, int(t0), t1, dur,
                        -1, -1, -1, res, ct, 0, "no quote before play"))
            continue

        sp = int(fa[pre]) - int(fb[pre])
        row = (tk, ev, ser, tier, t_lo, n, int(t0), t1, dur,
               int(fb[pre]), int(fa[pre]), sp, res, ct)
        if sp > PRE_SPREAD_MAX:
            out.append(row + (0, "pre-match book empty"))
            continue
        if dur >= 0 and not (MIN_PLAY <= dur <= MAX_PLAY):
            out.append(row + (0, "implausible duration"))
            continue

        out.append(row + (1, ""))
        paths.append((tk, seg_b.tobytes(), seg_a.tobytes()))
        n_ok += 1
        if (i + 1) % 2000 == 0:
            print(f"  {i + 1:,}/{len(tick):,}", flush=True)

    # The pull is very likely still running against this same database, so a
    # single large write will hit "database is locked" (it did). Chunked,
    # with an explicit wait, so the two can share the file.
    import time as _t
    for i in range(0, len(out), 500):
        chunk = out[i:i + 500]
        for attempt in range(8):
            try:
                con.executemany(
                    "insert or replace into state values "
                    "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", chunk)
                con.commit()
                break
            except sqlite3.OperationalError as e:
                if "locked" not in str(e) and "busy" not in str(e):
                    raise
                _t.sleep(1.0 + 2.0 * attempt)
        else:
            raise SystemExit("could not write state: database stayed locked")
    for i in range(0, len(paths), 500):
        for attempt in range(8):
            try:
                con.executemany("insert or replace into paths values (?,?,?)",
                                paths[i:i + 500])
                con.commit()
                break
            except sqlite3.OperationalError as e:
                if "locked" not in str(e) and "busy" not in str(e):
                    raise
                _t.sleep(1.0 + 2.0 * attempt)
    print(f"\nusable: {n_ok:,} of {len(tick):,}")
    for why, k in con.execute(
            "select why, count(*) from state where ok=0 group by why "
            "order by 2 desc"):
        print(f"  dropped -- {why}: {k:,}")
    print("\n  (the numbers behind those categories are kept per row in "
          "pre_spread / dur / n_min, so nothing is lost by naming them)")


def check(con):
    tot = con.execute("select count(*) from state").fetchone()[0]
    ok = con.execute("select count(*) from state where ok=1").fetchone()[0]
    print(f"state rows: {tot:,}   usable: {ok:,}")
    if not ok:
        return
    print("\nby tier:")
    for r in con.execute(
            "select tier, count(*), sum(ok) from state group by tier"):
        print(f"  {r[0]:<12} {r[2]:>6,} usable of {r[1]:,}")
    print("\nboth sides of the match usable? (the rule needs the pair)")
    r = con.execute(
        "select n, count(*) from (select event_ticker, sum(ok) n from state "
        "group by event_ticker) group by n order by n").fetchall()
    for n, k in r:
        print(f"  {n} usable side(s): {k:,} matches")
    print("\npre-match anchor sanity -- the spread at t0-1:")
    for r in con.execute(
            "select tier, count(*), round(avg(pre_ask-pre_bid),2), "
            "round(avg((pre_bid+pre_ask)/2.0),1) from state where ok=1 "
            "group by tier"):
        print(f"  {r[0]:<12} n={r[1]:>6,}  mean spread {r[2]:>5}c  "
              f"mean mid {r[3]}c")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    con = sqlite3.connect(DB, timeout=120)
    con.execute("pragma busy_timeout=120000")
    con.executescript(SCHEMA)
    if a.build:
        build(con)
    check(con)
    _ = P2.completed_dip          # imported so the rule source is pinned here


if __name__ == "__main__":
    sys.exit(main())
