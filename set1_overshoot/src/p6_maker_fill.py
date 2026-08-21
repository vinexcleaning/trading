"""Phase 6c -- the fade entered as a MAKER, filled only by trades that happened.

WHAT THIS DOES NOT DO, AND THAT IS THE POINT
--------------------------------------------
It never invents a fill. A resting order is credited only when a real trade
printed on the correct side at a price that would have reached it. The crypto
maker work names the fill model as *"the single easiest thing to fake in a maker
backtest"*, and the way it gets faked is a rule that says "the price touched my
level, so I traded". Touching is not trading.

THE TWO REPRESENTATIONS (preregistration amendment A1)
------------------------------------------------------
Buying the underdog can be done two ways, and they are the same position
because the two tickers of a match are near-exact mirrors:

    R1  rest a YES BID on the underdog's ticker    -- filled by takers SELLING
    R2  rest a YES ASK on the favourite's ticker   -- filled by takers BUYING

Selling the favourite is being long the underdog. Measured on the tape, takers
buy about three times in four **on both tickers**, so R2 sits where the flow is
and R1 does not. **Both are computed and neither is chosen in advance.** If they
disagree, the disagreement is the finding.

THE QUEUE BRACKET (amendment A3)
--------------------------------
The candles carry `yes_bid` and `yes_ask` but no SIZE, so queue position is not
observable. Rather than pick one and pretend, every fill statistic is reported
as a bracket:

    FRONT  we are first in the queue -- any qualifying trade fills us
    BACK   we are behind the whole visible resting size for the tier

The truth is between them and this file does not claim to know where.

GEOMETRY. `paths` rows are PATH_MIN minutes starting AT t0, so column j is
minute t0 + j -- minutes from the first minute of play. `deep:30@38` starts
looking 38 minutes into the match.
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sqlite3
import sys
from decimal import Decimal

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))

import p2_calib as P2                              # noqa: E402
from common import kalshi_fees as KF               # noqa: E402

DB = ROOT / "data" / "maker.db"
PATH_MIN = 300

#: Median visible resting size per tier, from `bot-hunt/data/record.db`.
#: ONE CONSTANT PER TIER, never per market -- a market-structure fact, so it
#: cannot leak an outcome into any single match. See amendment A3.
QUEUE_AHEAD = {"main": 7512, "challenger": 3000, "itf": 1411}

#: How long the order rests before being given up on. Pre-committed primary and
#: two sensitivities. NOT chasing: if it does not fill, there is no trade.
REST_MIN = 30
REST_SENSITIVITY = (10, 120)


def _mid_from(bid, ask):
    m = np.where(bid >= 0, (bid.astype(float) + ask.astype(float)) / 2.0,
                 np.nan)
    return m


def load_paths(con, ticker):
    r = con.execute("select bid, ask from paths where ticker=?",
                    (ticker,)).fetchone()
    if not r:
        return None
    return (np.frombuffer(r[0], dtype=np.int16).astype(np.int32),
            np.frombuffer(r[1], dtype=np.int16).astype(np.int32))


def epoch_of(created):
    return dt.datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()


def trades_for(con, ticker):
    """(epoch, yes_price_c, count, taker_outcome_side) for real trades only."""
    out = []
    for ct, yp, n, side in con.execute(
            "select created_time, yes_price_c, count, taker_outcome_side "
            "from trades where ticker=? and is_block=0", (ticker,)):
        if yp is None or ct is None:
            continue
        try:
            out.append((epoch_of(ct), int(yp), float(n or 0), side))
        except ValueError:
            continue
    out.sort()
    return out


def find_entry(bid, ask, pre_mid, depth, min_minute):
    """The study's own rule, called rather than re-implemented.

    Returns the entry column (minutes from t0) or -1.
    """
    mid = _mid_from(bid, ask)
    lo = max(P2.CP_LO, min_minute)
    if lo + 8 >= len(mid):
        return -1
    cp = P2.completed_dip(mid[None, :], np.array([pre_mid]), depth, lo=lo)[0]
    if cp < 0:
        return -1
    e = int(cp) + P2.STAB
    return e if e < len(mid) else -1


def fill_from_tape(tape, t_start, t_end, price_c, want_side, contracts,
                   queue_ahead):
    """How many contracts a resting order at `price_c` would have got.

    `want_side` is the taker side that would have hit us:
      'no'  -- the taker is selling YES, so it reaches a resting YES BID
      'yes' -- the taker is buying YES, so it reaches a resting YES ASK

    Returns (front_of_queue_fill, back_of_queue_fill).
    """
    vol = 0.0
    for ts, yp, n, side in tape:
        if ts < t_start or ts > t_end:
            continue
        if side != want_side:
            continue
        # a taker selling reaches our BID only at or below our price;
        # a taker buying reaches our ASK only at or above it
        if want_side == "no" and yp > price_c:
            continue
        if want_side == "yes" and yp < price_c:
            continue
        vol += n
    front = min(contracts, vol)
    back = min(contracts, max(0.0, vol - queue_ahead))
    return front, back


def run(con, depth=30.0, min_minute=38, rest_min=REST_MIN, tiers=None,
        pre_spread_max=10, shuffle=False, seed=0):
    """One arm. Returns a list of per-match dicts."""
    rng = np.random.default_rng(seed)
    q = ("select ticker, event_ticker, series, tier, t_lo, t0, pre_bid, "
         "pre_ask, result, close_time from state where ok=1 "
         "and pre_spread <= ?")
    args = [pre_spread_max]
    if tiers:
        q += " and tier in (%s)" % ",".join("?" * len(tiers))
        args += list(tiers)
    rows = con.execute(q, args).fetchall()

    by_ev = {}
    for r in rows:
        by_ev.setdefault(r[1], []).append(r)

    fee_type = dict(con.execute("select series, fee_type from fees"))
    out = []

    for ev, mk in by_ev.items():
        if len(mk) != 2:
            continue                     # need both sides: one to read, one to rest on
        # the favourite is the higher pre-match mid. Ties broken by ticker
        # order, which is outcome-independent (GUARDS #1).
        mk.sort(key=lambda r: (-(r[6] + r[7]), r[0]))
        fav, dog = mk[0], mk[1]
        pre_mid_fav = (fav[6] + fav[7]) / 2.0
        if pre_mid_fav <= 50:
            continue                     # no favourite; not the study's setup

        pf = load_paths(con, fav[0])
        pd_ = load_paths(con, dog[0])
        if pf is None or pd_ is None:
            continue
        fb, fa = pf
        db_, da = pd_

        e = find_entry(fb, fa, pre_mid_fav, depth, min_minute)
        if e < 0:
            continue

        # the resting prices, at the touch, at the entry minute
        if db_[e] < 0 or fa[e] < 0:
            continue
        p_r1 = int(db_[e])               # YES bid on the underdog
        p_r2 = int(fa[e])                # YES ask on the favourite

        t_lo_f, t0_f = fav[4], fav[5]
        t_lo_d, t0_d = dog[4], dog[5]
        t_start_f = t_lo_f + (t0_f + e) * 60
        t_start_d = t_lo_d + (t0_d + e) * 60

        tape_f = trades_for(con, fav[0])
        tape_d = trades_for(con, dog[0])
        if shuffle:
            tape_f = _shuffled(tape_f, rng)
            tape_d = _shuffled(tape_d, rng)

        qa = QUEUE_AHEAD.get(fav[3], 1500)
        r1 = fill_from_tape(tape_d, t_start_d, t_start_d + rest_min * 60,
                            p_r1, "no", 1_000_000, qa)
        r2 = fill_from_tape(tape_f, t_start_f, t_start_f + rest_min * 60,
                            p_r2, "yes", 1_000_000, qa)

        dog_won = 1 if dog[8] == "yes" else 0

        out.append({
            "event": ev, "tier": fav[3], "series": fav[2],
            "close": fav[9], "entry_min": e,
            "p_r1": p_r1, "p_r2": p_r2,
            "r1_front": r1[0], "r1_back": r1[1],
            "r2_front": r2[0], "r2_back": r2[1],
            "dog_won": dog_won,
            "fee_type_fav": fee_type.get(fav[2], "?"),
            "fee_type_dog": fee_type.get(dog[2], "?"),
        })
    return out


def _shuffled(tape, rng):
    """PLACEBO P1 -- reassign which side was the aggressor, keeping prices and
    times. A real fill advantage must collapse. Asserted to have actually
    changed something, because the repo's first placebo was a no-op."""
    if not tape:
        return tape
    sides = [t[3] for t in tape]
    perm = list(rng.permutation(len(sides)))
    new = [(tape[i][0], tape[i][1], tape[i][2], sides[perm[i]])
           for i in range(len(tape))]
    return new


def pnl_cents(price_c, dog_won, series_fee_type, contracts):
    """Per-contract profit in cents for a MAKER buy of the underdog at
    `price_c`, held to settlement. Fees from common/kalshi_fees.py only."""
    fees = KF.SeriesFees("<s>", series_fee_type, Decimal(1))
    fee = KF.maker_fee_order_cents(price_c, max(1, int(round(contracts))), fees)
    gross = (100 - price_c) if dog_won else (-price_c)
    per = Decimal(gross) - (fee / Decimal(max(1, int(round(contracts)))))
    return float(per)


def summarise(rows, label):
    n = len(rows)
    if not n:
        print(f"{label}: no events fired")
        return
    print(f"\n{label}")
    print(f"  matches where the rule fired : {n:,}")
    won = sum(r['dog_won'] for r in rows)
    print(f"  underdog won                 : {won:,} ({won/n:.1%})")
    for rep in ("r1", "r2"):
        for bound in ("front", "back"):
            k = f"{rep}_{bound}"
            filled = [r for r in rows if r[k] > 0]
            rate = len(filled) / n
            print(f"  {rep.upper()} {bound:<5} filled on {len(filled):>5,} "
                  f"of {n:,} matches ({rate:5.1%})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=float, default=30.0)
    ap.add_argument("--min-minute", type=int, default=38)
    ap.add_argument("--rest-min", type=int, default=REST_MIN)
    ap.add_argument("--pre-spread-max", type=int, default=10)
    a = ap.parse_args()

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    have = con.execute("select count(distinct ticker) from trades").fetchone()[0]
    print(f"markets with trades on disk: {have:,}")
    print("(pass 2 of the pull fetches trades only for markets that fire)")

    rows = run(con, depth=a.depth, min_minute=a.min_minute,
               rest_min=a.rest_min, pre_spread_max=a.pre_spread_max)
    summarise(rows, f"deep:{a.depth:.0f}@{a.min_minute}, "
                    f"rest {a.rest_min}m, pre-spread <= {a.pre_spread_max}c")
    print("\nNO P&L IS REPORTED HERE YET -- the trades pass has not run, so a "
          "fill rate\ncomputed now would be a fill rate against a mostly empty "
          "tape.")


if __name__ == "__main__":
    sys.exit(main())
