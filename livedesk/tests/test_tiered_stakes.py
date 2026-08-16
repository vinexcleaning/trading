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
    assert STAKE_PCT_AGREED == 10.0
    assert STAKE_PCT_OTHER == 5.0


def test_agreed_gets_ten_percent():
    assert bucket_for(False, "early agreed") == BUCKET_AGREED
    assert stake_for_bucket(BAL, False, "early agreed") == pytest.approx(10.00)


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
