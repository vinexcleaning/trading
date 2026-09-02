"""Kalshi charges HALF fee on the baseball markets this desk trades.

    livedesk\\test.bat

⚠ WHAT WAS WRONG. `money.size_bet()` called `fee_order_cents()` with no rate,
so it used the full taker rate. `KXMLBGAME` and `KXMLBTOTAL` carry
`fee_multiplier = 0.5`, and that is everything this desk buys.

**In money it is pennies** -- about 3 cents on a $2 stake, maybe 30 cents
across his whole live history. **That is not why it matters.**
`breakeven_out_of_100` is the number on screen telling him how many wins in a
hundred he needs, and it overstated the bar by about one win in a hundred.
That is the figure he reasons with.

⚠ AND HALF-FEE IS NOT A FACT ABOUT BASEBALL. Only 19 of 144 baseball series
carry it -- the per-game ones. Season-long markets (`KXMLBWINS-*`, divisions,
All-Star) are full fee. **Half-fee implies baseball; baseball does not imply
half-fee.** So the multiplier is read per series from the API and never keyed
on the sport, and never hardcoded -- hardcoding a fee fact is how this repo
reached 17 copies of the formula.

NOTHING HERE TOUCHES THE NETWORK. The client is a stub returning fixed series
objects; the live values were verified separately on 2026-09-02 and are
recorded in `src/fees.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SRC.parents[1]))

import fees                                                # noqa: E402
from money import size_bet                                 # noqa: E402
from common.kalshi_fees import TAKER_RATE                  # noqa: E402

#: What the live API returned on 2026-09-02. Verified against Kalshi directly,
#: not taken from the message that reported it.
LIVE = {
    "KXMLBGAME":  {"ticker": "KXMLBGAME",  "fee_type": "quadratic_with_maker_fees", "fee_multiplier": 0.5},
    "KXMLBTOTAL": {"ticker": "KXMLBTOTAL", "fee_type": "quadratic",                  "fee_multiplier": 0.5},
    "KXATPMATCH": {"ticker": "KXATPMATCH", "fee_type": "quadratic_with_maker_fees", "fee_multiplier": 1},
    "KXNFLGAME":  {"ticker": "KXNFLGAME",  "fee_type": "quadratic_with_maker_fees", "fee_multiplier": 1},
}


class StubClient:
    """Answers /series/<t> from LIVE. Counts calls, so caching is testable."""

    def __init__(self, table=None):
        self.table = LIVE if table is None else table
        self.calls = 0

    def _get(self, path):
        self.calls += 1
        s = path.rsplit("/", 1)[-1]
        if s not in self.table:
            raise RuntimeError(f"404 no such series {s}")
        return {"series": self.table[s]}


@pytest.fixture(autouse=True)
def clean_cache():
    fees._reset_for_tests()
    yield
    fees._reset_for_tests()


# ------------------------------------------------- the rate, per series

def test_baseball_games_are_half_and_tennis_is_full():
    """⚠ THE TEST MAILBOX 025 ASKED FOR: a refactor that drops the multiplier
    fails here, loudly, instead of quietly overcharging him on screen."""
    c = StubClient()
    assert fees.rate_for("KXMLBGAME-26AUG221915PITLAD-PIT", c)[0] == \
        TAKER_RATE / 2
    assert fees.rate_for("KXMLBTOTAL-26AUG22-T8", c)[0] == TAKER_RATE / 2
    assert fees.rate_for("KXATPMATCH-26AUG22NAKTIA-NAK", c)[0] == TAKER_RATE
    assert fees.rate_for("KXNFLGAME-26SEP07-KC", c)[0] == TAKER_RATE


def test_the_series_is_taken_from_the_ticker():
    assert fees.series_of("KXMLBGAME-26AUG221915PITLAD-PIT") == "KXMLBGAME"
    assert fees.series_of("KXATPMATCH-26AUG22NAKTIA-NAK") == "KXATPMATCH"
    assert fees.series_of("") == ""


def test_a_season_long_baseball_market_is_NOT_assumed_to_be_half():
    """⚠ THE TRAP. Only the per-game series are discounted. A rule keyed on the
    sport would charge half on markets Kalshi bills in full, and understate his
    cost -- the dangerous direction."""
    c = StubClient({**LIVE, "KXMLBWINS": {"ticker": "KXMLBWINS",
                                          "fee_type": "quadratic",
                                          "fee_multiplier": 1}})
    assert fees.rate_for("KXMLBWINS-26-NYY", c)[0] == TAKER_RATE


def test_it_is_asked_once_per_series_and_then_cached():
    c = StubClient()
    for _ in range(5):
        fees.rate_for("KXMLBGAME-A-X", c)
        fees.rate_for("KXMLBGAME-B-Y", c)
    assert c.calls == 1, "one GET per series per session, not per bet"


# ---------------------------------------- what happens when it cannot ask

def test_an_unreadable_series_falls_back_to_the_FULL_rate():
    """⚠ THE SAFE DIRECTION AND THE ONLY ACCEPTABLE ONE. Guessing the discount
    would make a bet look cheaper than it is because of a network error. Too
    expensive is survivable; too cheap is not."""
    c = StubClient({})
    rate, known = fees.rate_for("KXMLBGAME-A-X", c)
    assert rate == TAKER_RATE
    assert known is False


def test_no_client_at_all_falls_back_to_the_FULL_rate():
    rate, known = fees.rate_for("KXMLBGAME-A-X", None)
    assert rate == TAKER_RATE and known is False


def test_a_failed_lookup_is_not_retried_every_single_bet():
    c = StubClient({})
    for _ in range(4):
        fees.rate_for("KXMLBGAME-A-X", c)
    assert c.calls == 1


def test_it_SAYS_when_it_could_not_read_the_rate():
    """'I do not know' and 'the full rate applies' are different answers, and
    only one of them means the number on screen is trustworthy."""
    assert "could not be read" in fees.note_for("KXMLBGAME-A-X", StubClient({}))


def test_it_says_nothing_at_the_ordinary_full_rate():
    """A message on every full-fee market is noise, and noise gets ignored."""
    assert fees.note_for("KXATPMATCH-A-X", StubClient()) == ""


def test_it_announces_the_discount():
    said = fees.note_for("KXMLBGAME-A-X", StubClient())
    assert "0.5x fee" in said and "KXMLBGAME" in said


def test_every_line_it_shows_is_plain_ascii():
    for t in ("KXMLBGAME-A-X", "KXATPMATCH-A-X"):
        fees.note_for(t, StubClient()).encode("cp1252")
        fees.note_for(t, StubClient({})).encode("cp1252")


# ------------------------------------- the number he actually reads

@pytest.mark.parametrize("price,stake,be_full,be_half", [
    (30, 2.00, 31.5, 30.8),
    (45, 2.00, 46.8, 46.0),
    (55, 2.00, 57.0, 56.0),
    (70, 2.00, 71.5, 71.0),
    (85, 2.00, 86.0, 85.5),
])
def test_the_breakeven_on_screen_drops_at_the_half_rate(price, stake,
                                                        be_full, be_half):
    """The whole point. Reproduced independently and every figure agrees with
    the table in mailbox 025."""
    assert size_bet(price, stake).breakeven_out_of_100 == be_full
    assert size_bet(price, stake,
                    TAKER_RATE / 2).breakeven_out_of_100 == be_half


def test_the_half_rate_never_makes_a_bet_look_worse():
    """A lower fee cannot raise a cost. If it ever does, the rate is being
    applied the wrong way round."""
    for price in range(5, 100, 5):
        full = size_bet(price, 3.00)
        half = size_bet(price, 3.00, TAKER_RATE / 2)
        assert half.fee_usd <= full.fee_usd
        assert half.cost_usd <= full.cost_usd
        assert half.win_profit_usd >= full.win_profit_usd
        assert half.breakeven_out_of_100 <= full.breakeven_out_of_100


def test_omitting_the_rate_still_charges_the_FULL_amount():
    """The default must never be the discount. A caller that forgets should
    overstate the cost, not understate it."""
    assert size_bet(55, 2.00).fee_usd == size_bet(55, 2.00,
                                                  TAKER_RATE).fee_usd


def test_the_multiplier_is_not_hardcoded_anywhere_in_this_project():
    """⚠ GUARD #6 IN SPIRIT: a fee fact gets ONE home. This repo went from 3
    copies of the fee formula to 17 while that was only a convention.

    ⚠ AND IT READS THE CODE, NOT THE PROSE. The first version matched raw
    lines and fired on `src/fees.py`'s own docstring, which explains the very
    thing it was checking for. `test_paper_only.py` records the identical
    correction -- 'COMMENTS AND DOCSTRINGS ARE DELIBERATELY NOT SCANNED' -- and
    I reproduced the mistake it already warns about. A canary that cries wolf
    gets switched off, and then the real thing walks through.
    """
    import ast
    for f in SRC.glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            names = [t.id.lower() for t in node.targets
                     if isinstance(t, ast.Name)]
            if not any("fee" in n or "mult" in n for n in names):
                continue
            v = node.value
            assert not (isinstance(v, ast.Constant)
                        and isinstance(v.value, (int, float))
                        and v.value not in (0, 1)), (
                f"{f.name}: fee multiplier assigned a literal {v.value!r} -- "
                f"read it from the series instead")
