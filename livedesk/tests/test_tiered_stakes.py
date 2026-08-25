"""10% on agreed games, 5% on everything else. And a blank flag sizes SMALL.

His words, 2026-08-16: *"ten percent on agreed games, five percent on
everything else"*.

⚠ HE ALSO SAID *"and then we don't even bet on the alone games"*. **That half is
deliberately NOT built.** The coordinator put the arithmetic to him -- skipping
the alone games takes him from 28 bets to 8 -- and he has not answered. It is
one line to add if he confirms.

⚠ AND THE BLOCKER THAT MADE THIS UNBUILDABLE UNTIL NOW: `alone` was empty on all
31 ledger rows, including three that filled AFTER the flag was wired. The
manual click path carried it; the automatic path built its own `Entry(...)` and
did not, and every bet is automatic. Two construction sites for one object.
There is one now, and a test below that both paths use it.

    livedesk\test.bat
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from money import (BUCKET_AGREED, BUCKET_ALONE, BUCKET_OPPOSITE,   # noqa: E402
                   BUCKET_UNKNOWN, MAX_STAKE_USD, STAKE_PCT_AGREED,
                   STAKE_PCT_OTHER, bucket_for, size_bet, stake_for_bucket,
                   stake_pct_for)

BAL = 100.00


def test_his_numbers():
    """⚠ CHANGED 2026-08-25. It asserted 10.0/5.0. His words: **"Put five
    percent flat on everything."** The tier was withdrawn on evidence -- all
    three buckets reversed out of sample -- not on a preference."""
    assert STAKE_PCT_AGREED == 5.0
    assert STAKE_PCT_OTHER == 5.0


def test_agreed_is_still_CLASSIFIED_even_though_it_no_longer_pays_more():
    """⚠ WAS `test_agreed_gets_ten_percent`. The classification is unchanged
    and still recorded -- it is the only data that could ever justify bringing
    the tier back, so deleting the machinery would delete the evidence. What
    changed is the stake it leads to."""
    assert bucket_for(False, "early agreed") == BUCKET_AGREED
    assert stake_for_bucket(BAL, False, "early agreed") == pytest.approx(5.00)


def test_the_other_side_gets_five():
    assert bucket_for(False, "early took the OTHER side") == BUCKET_OPPOSITE
    assert stake_for_bucket(BAL, False,
                            "early took the OTHER side") == pytest.approx(5.00)


def test_alone_gets_five_and_is_still_BET(led=None):
    """Not skipped. He has not confirmed the skip and it is not built."""
    assert bucket_for(True, "NOBODY ELSE took a position") == BUCKET_ALONE
    stake = stake_for_bucket(BAL, True, "NOBODY ELSE took a position")
    assert stake == pytest.approx(5.00)
    assert size_bet(50, stake).contracts > 0, "an alone game must still bet"


# ============================ the one that matters most

def test_a_BLANK_flag_sizes_SMALL_not_big():
    """A missing flag must fail to 5%, never to 10%. Every row in his ledger
    had a blank flag tonight, so this is the realistic case, not the edge."""
    assert bucket_for(None) == BUCKET_UNKNOWN
    assert stake_pct_for(None) == STAKE_PCT_OTHER
    assert stake_for_bucket(BAL, None) == pytest.approx(5.00)
    assert stake_for_bucket(BAL, None, "") == pytest.approx(5.00)


def test_a_blank_flag_still_BETS_rather_than_refusing():
    """It must not fail to no-bet either -- that silently reproduces the 24
    bets that vanished tonight when a guard quietly refused everything."""
    stake = stake_for_bucket(BAL, None)
    assert stake > 0
    assert size_bet(50, stake).contracts > 0


def test_an_unknown_balance_still_fails_closed():
    for bad in (None, 0, -1, "abc"):
        assert stake_for_bucket(bad, False, "early agreed") == 0.0, bad


def test_the_ceiling_still_applies_to_the_big_tier():
    assert stake_for_bucket(1_000_000.0, False,
                            "early agreed") == MAX_STAKE_USD


# ==================== the blocker: one place builds the ledger row

def test_both_paths_build_the_entry_through_ONE_function():
    """⚠ THE BUG THIS PREVENTS. The manual path passed `alone`; the automatic
    path built its own Entry and did not. Every bet is automatic, so the flag
    was blank on all 31 rows and the tiering could not be switched on."""
    import ast
    src = (SRC / "desk.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    built = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and getattr(n.func, "id", "") == "Entry"]
    assert len(built) <= 1, (
        f"{len(built)} places build an Entry in desk.py. There must be one "
        f"(_entry_from), or they drift and a field goes missing again.")
    assert "_entry_from" in src
    assert src.count("self._entry_from(") >= 2, (
        "both the manual and the automatic path must go through it")


def test_the_builder_carries_the_flag():
    src = (SRC / "desk.py").read_text(encoding="utf-8")
    body = src[src.index("def _entry_from"):]
    body = body[:body.index("\n    def ")]
    assert "alone=p.alone" in body
    assert "consensus=p.consensus" in body


def test_the_skip_is_NOT_built():
    """He said it; he has not confirmed it after seeing the numbers. Building
    it early would quietly cut him from 28 bets to 8."""
    src = (SRC / "money.py").read_text(encoding="utf-8")
    assert stake_for_bucket(BAL, True, "NOBODY ELSE") > 0, (
        "the alone tier must still produce a stake, not a skip")


# ================= mailbox 010: what must NOT be built, and what must be said

def test_the_sample_behind_the_big_tier_is_on_the_card_every_time():
    """⚠ THE 10% TIER RESTS ON THREE GAMES. He must see that each time it
    fires, not once in a document.

    `consensus.decompose()` will say 18 agreed games. That is the HINDSIGHT
    number -- it counts games where the other bot arrived hours later. Live, at
    the moment of entry, it is 3. Showing 18 would overstate the evidence six
    times over."""
    from money import AGREED_EVIDENCE_GAMES
    assert AGREED_EVIDENCE_GAMES == 3
    src = (SRC / "desk.py").read_text(encoding="utf-8")
    agreed_line = [l for l in src.splitlines() if '"agreed":' in l]
    assert agreed_line, "the agreed tier has no card line"
    block = src[src.index('"agreed":'):src.index('"opposite":')]
    assert "AGREED_EVIDENCE_GAMES" in block, (
        "the card must show the sample count where the big tier fires")
    assert "experiment" in block.lower()


def test_no_cash_reserve_or_agreed_priority_exists():
    """⚠ HE ASKED FOR THIS AND IT MUST NOT BE BUILT. Measured: reserving $20 to
    protect agreed games rescues 1 of them and ends $35 WORSE, because it
    blocks 8 alone bets and 2 opposite ones to do it."""
    for name in ("money.py", "desk.py", "ledger.py", "demo_exec.py"):
        src = (SRC / name).read_text(encoding="utf-8").lower()
        for banned in ("reserve_usd", "cash_reserve", "agreed_priority",
                       "reserve_for_agreed", "priority_bucket"):
            assert banned not in src, f"{banned} appeared in {name}"


def test_a_bet_is_never_upgraded_from_five_to_ten_after_the_fact():
    """⚠ Of the 8 games where the other bot arrived later, it took the
    OPPOSITE side 5 times. Topping up on a later 'agreement' means topping up
    a position the other bot is betting against, more often than not.

    The size is fixed when the entry is built. The retry path resubmits the
    SAME entry object and never re-sizes it."""
    src = (SRC / "desk.py").read_text(encoding="utf-8")
    retry = src[src.index("---- retry deferred entries first ----"):]
    retry = retry[:retry.index("---- fresh picks")]
    assert "size_bet(" not in retry, (
        "the retry path re-sizes a bet — a 5% bet could become 10% later")
    assert "_stake(" not in retry


def test_the_bucket_is_recorded_on_the_entry_for_counting():
    """010 asked for a COUNTER, not a feature: record which tier a bet was in
    so starvation of agreed games can be counted later rather than argued."""
    from ledger import Entry
    e = Entry(game_key="g", ticker="t", event_ticker="e", team="X",
              matchup="a at b", side="YES", price_c=50, contracts=1,
              cost_usd=1.0, fee_usd=0.0, win_profit_usd=1.0, lose_usd=1.0,
              starts_utc="2099-01-01T00:00:00+00:00",
              confirmed_utc="2026-08-17T00:00:00+00:00")
    assert hasattr(e, "bucket")
    src = (SRC / "desk.py").read_text(encoding="utf-8")
    assert "bucket=bucket_for(" in src, "the builder must record the tier"


# ==========================================================================
# ⚠ THE TIER WAS WITHDRAWN ON EVIDENCE, 2026-08-25. His words: **"Put five
# percent flat on everything."**
#
# The tests ABOVE are deliberately left in place and still pass. The bucket
# machinery is unchanged -- `bucket_for`, `stake_pct_for`, `stake_for_bucket`
# all still work and the card still names the bucket. Only the two numbers
# moved, so that if the evidence ever comes back this is one number and not a
# rebuild.
#
# WHY IT WAS WITHDRAWN. Out of every $100 staked, split on settlement date and
# classified only on what was knowable at bet time:
#
#   bucket      the 81 games it came from      the 24 games since
#   agreed      made $38                       LOST $29
#   opposite    made $21                       made $36
#   alone       LOST $10                       made $39
#
# All three flipped. The gap the rule rested on is gone.
# ==========================================================================

def test_every_bucket_now_stakes_the_same():
    """The whole of his decision, in one assertion.

    ⚠ NOTE THE SIGNATURE. `stake_for_bucket(balance, alone, consensus)` -- it
    takes the FLAGS, not a bucket name. The first version of this test passed a
    bucket string as `alone`, which is truthy, so every case silently collapsed
    to `alone` and the test asserted nothing at all while passing.
    """
    cases = {"agreed": (False, "early agreed"),
             "opposite": (False, "took the other side"),
             "alone": (True, ""),
             "unknown": (None, "")}
    stakes = {k: stake_for_bucket(BAL, a, c) for k, (a, c) in cases.items()}
    assert len(set(stakes.values())) == 1, stakes
    assert stakes["agreed"] == pytest.approx(BAL * 0.05)


def test_an_agreed_game_no_longer_gets_double():
    """This is the change. It used to be $10 against $5 on this balance."""
    assert stake_for_bucket(BAL, False, "early agreed") ==         stake_for_bucket(BAL, True, "")


def test_an_unknown_flag_still_sizes_and_never_refuses_to_bet():
    """⚠ A missing flag must size at 5%, NOT at nothing. Turning an unknown
    bucket into a no-bet would silently stop him trading on the day the
    classifier broke, and nothing would say so."""
    s = stake_for_bucket(BAL, None, "")
    assert s == pytest.approx(BAL * 0.05)
    assert s > 0


def test_the_bucket_is_still_recorded_even_though_it_changes_nothing():
    assert bucket_for(False, "early agreed") == BUCKET_AGREED
    assert bucket_for(False, "took the other side") == BUCKET_OPPOSITE
    assert bucket_for(True, "") == BUCKET_ALONE
    assert bucket_for(None, "") == BUCKET_UNKNOWN
    assert stake_pct_for(False, "early agreed") == stake_pct_for(True, "") == 5.0


def test_the_cap_and_the_floor_were_not_touched():
    """His decision was about the percentage and nothing else. A sizing change
    that quietly moved a guard would not be the change he approved."""
    import ledger as _L
    assert MAX_STAKE_USD == 50.00
    assert _L.ACCOUNT_FLOOR_USD == 40.00
    assert _L.TRAILING_DROP_FRAC == 0.35


def test_a_big_balance_still_hits_the_ceiling():
    assert stake_for_bucket(5000.00, False, "early agreed") ==         pytest.approx(50.00)
