"""Guards on the maker fill model.

The thing being defended against is not a coding slip. It is the specific way
maker backtests get faked: crediting a fill because the price *touched* a level.
Touching is not trading, and every test below is a way of asserting that.
"""
from __future__ import annotations

import os
import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))

import p6_maker_fill as M          # noqa: E402


def tape(*rows):
    """(epoch, yes_price_c, count, taker_outcome_side)"""
    return [(float(t), int(p), float(n), s) for t, p, n, s in rows]


# ---------------------------------------------------------------- the core
def test_a_resting_bid_is_not_filled_by_the_price_merely_touching():
    """The whole point. Trades happened, at our price, in our window -- but
    every one of them was a taker BUYING, which lifts an ask and never reaches
    a resting bid. A model that fills here is the faked model."""
    t = tape((100, 60, 5000, "yes"), (150, 60, 5000, "yes"))
    front, back = M.fill_from_tape(t, 0, 1000, 60, "no", 100, 0)
    assert front == 0, "a resting BID was filled by takers who were BUYING"
    assert back == 0


def test_the_mirror_case_is_also_guarded():
    t = tape((100, 60, 5000, "no"), (150, 60, 5000, "no"))
    front, _ = M.fill_from_tape(t, 0, 1000, 60, "yes", 100, 0)
    assert front == 0, "a resting ASK was filled by takers who were SELLING"


def test_a_seller_above_our_bid_does_not_reach_us():
    """A taker selling at 70 hit somebody else's better bid. Our 60 bid is
    untouched, even though the market clearly traded."""
    t = tape((100, 70, 5000, "no"))
    front, _ = M.fill_from_tape(t, 0, 1000, 60, "no", 100, 0)
    assert front == 0


def test_a_seller_at_or_below_our_bid_does_reach_us():
    t = tape((100, 60, 40, "no"), (200, 55, 30, "no"))
    front, _ = M.fill_from_tape(t, 0, 1000, 60, "no", 100, 0)
    assert front == 70


def test_a_buyer_at_or_above_our_ask_reaches_us_and_below_does_not():
    t = tape((100, 60, 40, "yes"), (200, 55, 30, "yes"))
    front, _ = M.fill_from_tape(t, 0, 1000, 60, "yes", 100, 0)
    assert front == 40


def test_trades_outside_the_resting_window_are_not_ours():
    """The order rests for a fixed time. A fill after we gave up is not a fill,
    and this is how a maker backtest quietly acquires a whole match of volume."""
    t = tape((5000, 60, 900, "no"))
    front, _ = M.fill_from_tape(t, 0, 1000, 60, "no", 100, 0)
    assert front == 0


# ------------------------------------------------------------ the bracket
def test_back_of_queue_never_beats_front_of_queue():
    t = tape((100, 60, 5000, "no"))
    front, back = M.fill_from_tape(t, 0, 1000, 60, "no", 10_000, 1411)
    assert back < front
    assert back == 5000 - 1411


def test_back_of_queue_is_zero_when_the_queue_never_clears():
    """7,512 contracts rest ahead of us on main tour and 40 traded. We did not
    get filled, and reporting a fill here is the optimistic lie the bracket
    exists to bound."""
    t = tape((100, 60, 40, "no"))
    front, back = M.fill_from_tape(t, 0, 1000, 60, "no", 100, 7512)
    assert front == 40
    assert back == 0


def test_neither_bound_can_exceed_what_we_asked_for():
    t = tape((100, 60, 10_000, "no"))
    front, back = M.fill_from_tape(t, 0, 1000, 60, "no", 25, 0)
    assert front == 25 and back == 25


# ------------------------------------------------------------- the placebo
def test_the_shuffle_placebo_actually_changes_the_assignment():
    """GUARDS: the repo's first placebo was algebraically a no-op and passed
    vacuously. A placebo that changes nothing proves nothing, so assert the
    planted difference."""
    rng = np.random.default_rng(0)
    t = tape(*[(i, 60, 1, "yes" if i % 2 else "no") for i in range(200)])
    s = M._shuffled(t, rng)
    assert [x[3] for x in s] != [x[3] for x in t], "the shuffle was a no-op"
    assert sorted(x[3] for x in s) == sorted(x[3] for x in t), \
        "the shuffle changed the side MIX, not just the assignment"
    assert [x[:3] for x in s] == [x[:3] for x in t], \
        "the shuffle must keep prices and times identical"


# ------------------------------------------------------------------- fees
def test_maker_pays_nothing_on_the_taker_only_families():
    """S010. ITF and Challenger are plain `quadratic`, so a maker fee of
    anything above zero there is a bug that would silently tax the result."""
    win = M.pnl_cents(66, 1, "quadratic", 100)
    lose = M.pnl_cents(66, 0, "quadratic", 100)
    assert win == pytest.approx(34.0)
    assert lose == pytest.approx(-66.0)


def test_maker_pays_a_fee_on_the_main_tour_families():
    win = M.pnl_cents(66, 1, "quadratic_with_maker_fees", 100)
    assert win < 34.0, "main tour charges makers; the fee did not appear"
    assert win > 33.0, "the maker fee is small, not a rounding disaster"


def test_the_two_representations_agree_on_a_perfect_mirror():
    """R1 buys the underdog at P. R2 sells the favourite at 100-P. They are the
    same position and must produce the same money, or the design is wrong."""
    for p, won in ((66, 1), (66, 0), (34, 1), (12, 0)):
        r1 = M.pnl_cents(p, won, "quadratic", 100)
        # selling the favourite at 100-p and the favourite losing == dog wins
        r2_gross = (100 - p) if won else (-p)
        assert r1 == pytest.approx(r2_gross)


# ------------------------------------------------------------------ shape
def test_entry_rule_is_the_studys_own_function_not_a_copy():
    """Guard #6's logic applied to the entry rule: if someone re-implements
    `completed_dip` here, this fails."""
    src = (ROOT / "src" / "p6_maker_fill.py").read_text(encoding="utf-8")
    assert "P2.completed_dip" in src, "the study's rule is no longer being called"
    assert "def completed_dip" not in src, \
        "completed_dip has been re-implemented in p6_maker_fill.py"


def test_entry_returns_minus_one_when_the_path_is_too_short():
    bid = np.full(20, 50, dtype=np.int32)
    ask = np.full(20, 52, dtype=np.int32)
    assert M.find_entry(bid, ask, 51.0, 30.0, 38) == -1


def test_entry_fires_on_a_planted_dip_and_not_on_a_flat_path():
    """A positive control. If a real 30c fall does not fire the rule, every
    'no events' result downstream is meaningless."""
    n = 300
    bid = np.full(n, 70, dtype=np.int32)
    ask = np.full(n, 72, dtype=np.int32)
    flat = M.find_entry(bid.copy(), ask.copy(), 71.0, 30.0, 38)
    assert flat == -1, "the rule fired on a completely flat price"

    bid[60:] = 35
    ask[60:] = 37
    fired = M.find_entry(bid, ask, 71.0, 30.0, 38)
    assert fired > 0, "a planted 35c fall did not fire the rule"
    assert fired >= 60, "the rule fired BEFORE the fall it is supposed to detect"


# ------------------------------------------------- the arm-level reporting
sys.path.insert(0, str(ROOT / "src"))
import p6_arms as A          # noqa: E402


def _row(**kw):
    base = dict(event="E", tier="main", series="KXATPMATCH", close="2026-07-01",
                entry_min=40, p_r1=66, p_r2=34, ask_dog=70, dog_won=1,
                r1_front=0, r1_back=0, r2_front=0, r2_back=0,
                tape_f=True, tape_d=True)
    base.update(kw)
    return base


def test_a_market_with_no_tape_is_not_counted_as_a_missed_fill():
    """The difference between 'we rested and nobody came' and 'we have not
    downloaded this market's trades yet'. Averaging them reports a
    data-coverage rate wearing a fill rate's clothes."""
    rows = [_row(tape_d=False), _row(tape_d=False), _row(r1_front=50)]
    c = A.cell(rows, "r1", "front", {"KXATPMATCH": "quadratic"})
    assert c["n"] == 1, "markets with no tape leaked into the denominator"
    assert c["no_tape"] == 2
    assert c["rate"] == 1.0


def test_unfilled_attempts_stay_in_the_denominator_as_zero():
    """Preregistration section 7 item 4. A maker strategy that counts only the
    matches it got into is the classic maker backtest lie."""
    rows = [_row(r1_front=50), _row(r1_front=0)]
    c = A.cell(rows, "r1", "front", {"KXATPMATCH": "quadratic"})
    assert c["n"] == 2 and c["filled"] == 1
    assert c["rate"] == 0.5
    # per-attempt must be half the per-fill number, not equal to it
    assert c["attempt"][0] == pytest.approx(c["fill"][0] / 2)


def test_the_taker_benchmark_pays_the_ask_and_not_the_bid():
    """Pricing the taker at the bid hands it the whole spread for free, which
    is the exact quantity this study is about. It read +8.79c against the
    study's -1.10c before this was fixed."""
    rows = [_row(p_r1=66, ask_dog=70, dog_won=1)]
    (mean_pnl, _lo, _hi), mean_px = A.taker_cell(rows)
    assert mean_px == 71, "the taker was not charged the ask plus slippage"
    assert mean_pnl < 100 - 66, "the taker paid less than the ask"


def test_the_taker_benchmark_loses_when_the_underdog_loses():
    rows = [_row(ask_dog=70, dog_won=0)]
    (mean_pnl, _l, _h), _ = A.taker_cell(rows)
    assert mean_pnl < -70, "a losing taker bet must cost the price plus fee"


# -------------------------------------------- end-to-end on a planted market
import sqlite3          # noqa: E402


def _planted_db(tmp_path, trade_side="yes", trade_price=34, n_trades=5000):
    """One match, one planted 35c collapse, one planted trade.

    Favourite opens at 70/72 and falls to 34/36 at minute 60. The underdog is
    its exact mirror. A single trade prints during the resting window.
    """
    db = tmp_path / "planted.db"
    con = sqlite3.connect(db)
    con.executescript("""
      create table markets (ticker text primary key, event_ticker text,
        series text, result text, status text, open_time text,
        close_time text, volume_fp real, tier text);
      create table fees (series text primary key, fee_type text,
        fee_multiplier real, seen_utc text);
      create table state (ticker text primary key, event_ticker text,
        series text, tier text, t_lo integer, n_min integer, t0 integer,
        t1 integer, dur integer, pre_bid integer, pre_ask integer,
        pre_spread integer, result text, close_time text, ok integer,
        why text);
      create table paths (ticker text primary key, bid blob, ask blob);
      create table trades (trade_id text primary key, ticker text,
        series text, count real, yes_price_c integer, no_price_c integer,
        taker_outcome_side text, taker_book_side text, created_time text,
        is_block integer);
    """)
    con.execute("insert into fees values ('S','quadratic',1,'')")
    T0, TLO = 10, 1_780_000_000
    n = 300
    fb = np.full(n, 70, dtype=np.int16); fa = np.full(n, 72, dtype=np.int16)
    fb[60:] = 34; fa[60:] = 36
    db_ = (100 - fa).astype(np.int16)      # exact mirror
    da_ = (100 - fb).astype(np.int16)
    for tk, bid, ask, pb, pa, res in (
            ("FAV", fb, fa, 70, 72, "no"), ("DOG", db_, da_, 28, 30, "yes")):
        con.execute("insert into markets values (?,?,?,?,?,?,?,?,?)",
                    (tk, "EV", "S", res, "settled", "", "2026-07-01", 0, "main"))
        con.execute("insert into state values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (tk, "EV", "S", "main", TLO, n, T0, 120, 110, pb, pa,
                     pa - pb, res, "2026-07-01", 1, ""))
        con.execute("insert into paths values (?,?,?)",
                    (tk, bid.tobytes(), ask.tobytes()))
    # entry fires at 61 + STAB = 64; rest 30 min -> trade at minute 70
    ts = TLO + (T0 + 70) * 60
    when = __import__("datetime").datetime.fromtimestamp(
        ts, __import__("datetime").timezone.utc).isoformat().replace(
            "+00:00", "Z")
    con.execute("insert into trades values (?,?,?,?,?,?,?,?,?,?)",
                ("t1", "FAV", "S", n_trades, trade_price, 100 - trade_price,
                 trade_side, "bid" if trade_side == "yes" else "ask", when, 0))
    con.commit()
    return con


def test_end_to_end_r2_fills_from_a_taker_buying_the_favourite(tmp_path):
    """The trade is a taker BUYING the favourite at 34. That lifts our resting
    ask on the favourite, which is economically buying the underdog at 66."""
    con = _planted_db(tmp_path, trade_side="yes", trade_price=36)
    rows = M.run(con, depth=30.0, min_minute=38, rest_min=30,
                 pre_spread_max=10)
    assert len(rows) == 1, "the planted 35c collapse did not produce an event"
    r = rows[0]
    # 64, not 63, and the arithmetic is the rule's own: the fall lands at
    # minute 60, but "done" requires the mid to be no lower than the
    # trailing 8-minute low, which only becomes true at 61 once that window
    # contains the new low. Plus STAB=3. completed_dip's docstring says so
    # explicitly -- "the rule fires ~1 minute after the fall stops".
    assert r["entry_min"] == 64, f"entry fired at {r['entry_min']}, expected 64"
    assert r["r2_front"] > 0, "R2 was not filled by a taker buying"
    assert r["r1_front"] == 0, \
        "R1 was filled by a taker BUYING -- a resting bid cannot be"
    assert r["dog_won"] == 1


def test_end_to_end_r1_fills_only_from_a_taker_selling(tmp_path):
    con = _planted_db(tmp_path, trade_side="no", trade_price=30)
    rows = M.run(con, depth=30.0, min_minute=38, rest_min=30,
                 pre_spread_max=10)
    assert len(rows) == 1
    r = rows[0]
    assert r["r2_front"] == 0, "R2 was filled by a taker SELLING"


def test_end_to_end_a_trade_after_the_resting_window_never_fills(tmp_path):
    con = _planted_db(tmp_path, trade_side="yes", trade_price=36)
    rows = M.run(con, depth=30.0, min_minute=38, rest_min=2,
                 pre_spread_max=10)
    assert rows[0]["r2_front"] == 0, \
        "an order that rested 2 minutes caught a trade 7 minutes later"


def test_placebo_p2_moves_the_entry_minute(tmp_path):
    """A random-timing placebo that leaves the timing alone proves nothing."""
    con = _planted_db(tmp_path, trade_side="yes", trade_price=36)
    real = M.run(con, depth=30.0, min_minute=38, rest_min=30,
                 pre_spread_max=10)
    moved = False
    for seed in range(12):
        rnd = M.run(con, depth=30.0, min_minute=38, rest_min=30,
                    pre_spread_max=10, random_entry=True, seed=seed)
        if rnd and rnd[0]["entry_min"] != real[0]["entry_min"]:
            moved = True
            break
    assert moved, "P2 never moved the entry minute -- the placebo is a no-op"


def test_the_underdog_price_comes_from_the_mirror_not_its_own_path(tmp_path):
    """Pins the clock fix.

    Each ticker has its own detected play start, so column e of the two paths
    are different moments in real time -- only 21.3% of real pairs agree to the
    minute. Here the underdog's stored path is deliberately garbage. If the code
    still reads it, the entry price changes; if it derives the mirror from the
    favourite, the garbage is ignored.
    """
    con = _planted_db(tmp_path, trade_side="yes", trade_price=36)
    good = M.run(con, depth=30.0, min_minute=38, rest_min=30,
                 pre_spread_max=10)[0]

    junk = np.full(300, 7, dtype=np.int16)
    con.execute("update paths set bid=?, ask=? where ticker='DOG'",
                (junk.tobytes(), (junk + 2).tobytes()))
    con.commit()
    after = M.run(con, depth=30.0, min_minute=38, rest_min=30,
                  pre_spread_max=10)[0]

    assert after["p_r1"] == good["p_r1"], \
        "the underdog's own path is still being read -- the clock bug is back"
    assert after["ask_dog"] == good["ask_dog"]
    assert good["p_r1"] + good["p_r2"] == 100, \
        "the two representations must rest at the same economic price"


def test_the_two_tapes_are_windowed_on_the_same_absolute_moment(tmp_path):
    """The entry happens at one instant. Deriving the underdog's window from
    its own t0 was the same misalignment bug in a second place."""
    con = _planted_db(tmp_path, trade_side="yes", trade_price=36)
    base = M.run(con, depth=30.0, min_minute=38, rest_min=30,
                 pre_spread_max=10)[0]
    # shift ONLY the underdog's clock; the fill must not move
    con.execute("update state set t0 = t0 + 90 where ticker='DOG'")
    con.commit()
    moved = M.run(con, depth=30.0, min_minute=38, rest_min=30,
                  pre_spread_max=10)[0]
    assert moved["r2_front"] == base["r2_front"], \
        "shifting the underdog's clock moved a fill on the favourite's tape"
