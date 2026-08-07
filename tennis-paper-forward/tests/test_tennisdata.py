"""The form refresh. Every test here is a trap that actually fired."""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from src import safety  # noqa: E402
from src.safety import PaperOnlyViolation  # noqa: E402
from src.tennisdata import (_SURNAME_FIRST, _level, _score_string,  # noqa: E402
                            _surname_keys, _to_yyyymmdd, resolve)


# --------------------------------------------------------------------------
# Name formats — 273 of 984 rows were lost to these on the first run
# --------------------------------------------------------------------------

@pytest.mark.parametrize("raw,surname,initial", [
    ("Sinner J.", "Sinner", "J."),
    ("De Minaur A.", "De Minaur", "A."),
    ("Auger-Aliassime F.", "Auger-Aliassime", "F."),
    ("Davidovich Fokina A.", "Davidovich Fokina", "A."),
    ("Cerundolo J.M.", "Cerundolo", "J.M."),        # compound initial
    ("Bittoun Kouzmine C.", "Bittoun Kouzmine", "C."),
])
def test_the_name_format_parses(raw, surname, initial):
    m = _SURNAME_FIRST.match(raw)
    assert m is not None, f"{raw!r} did not parse at all"
    assert m.group(1) == surname
    assert m.group(2) == initial


def test_surname_keys_cover_hyphens_and_multiword_surnames():
    k = _surname_keys("Felix Auger Aliassime")
    assert "augeraliassime" in k, "the de-hyphenated joined form is missing"
    assert "auger aliassime" in k
    assert "aliassime" in k
    assert "de minaur" in _surname_keys("Alex De Minaur")
    assert "minaur" in _surname_keys("Alex De Minaur")


class _Rec:
    def __init__(self, name, levels):
        self.name = name
        self.by_level = levels


class _Arch:
    """Two players who share a surname AND an initial - the Nakashima case."""
    def __init__(self):
        self.players = {
            "brandon nakashima": _Rec("Brandon Nakashima", {"A": [200, 450]}),
            "bryce nakashima": _Rec("Bryce Nakashima", {"S": [20, 43]}),
            "jannik sinner": _Rec("Jannik Sinner", {"A": [300, 400]}),
            "alex de minaur": _Rec("Alex De Minaur", {"A": [200, 350]}),
            "jo wilfried tsonga": _Rec("Jo Wilfried Tsonga", {"A": [100, 200]}),
            "stan wawrinka": _Rec("Stan Wawrinka", {"A": [100, 200]}),
            "steve wawrinka": _Rec("Steve Wawrinka", {"A": [10, 20]}),
        }


def test_unambiguous_names_resolve():
    a = _Arch()
    assert resolve("Sinner J.", a) == "jannik sinner"
    assert resolve("De Minaur A.", a) == "alex de minaur"


def test_the_main_tour_tiebreak_picks_the_only_main_tour_candidate():
    """'Nakashima B.' is Brandon (main tour) and Bryce (futures only).

    This source publishes main tour ONLY, so a candidate who has never played
    a main-tour match cannot be the player in a main-tour row. That is a
    constraint from the source, not a guess about which is more famous.
    """
    assert resolve("Nakashima B.", _Arch()) == "brandon nakashima"


def test_a_genuinely_ambiguous_name_is_REFUSED_not_guessed():
    """Two main-tour players, same surname, same initial. GUARDS #22."""
    assert resolve("Wawrinka S.", _Arch()) is None


def test_an_unknown_surname_is_refused():
    assert resolve("Nobody Z.", _Arch()) is None


# --------------------------------------------------------------------------
# GUARDS #13 — content traps
# --------------------------------------------------------------------------

def test_a_future_date_is_droppable():
    """The WTA workbook contains a 2029 typo. A naive max(date) would set the
    form window five years out and empty every 'last 90 days' figure."""
    assert _to_yyyymmdd(datetime(2029, 7, 20)) == 20290720
    today = int(date(2026, 8, 7).strftime("%Y%m%d"))
    assert 20290720 > today, "the fixture no longer represents a future date"


def test_the_score_string_rebuilds_from_per_set_columns():
    s, bo = _score_string({"W1": 6, "L1": 4, "W2": 3, "L2": 6, "W3": 7, "L3": 5,
                           "Best of": 3, "Comment": "Completed"})
    assert s == "6-4 3-6 7-5" and bo == 3
    s, _ = _score_string({"W1": 6, "L1": 2, "W2": 2, "L2": 1,
                          "Best of": 3, "Comment": "Retired"})
    assert s.endswith("RET")


def test_the_level_map_is_sackmann_shaped():
    assert _level({"Series": "Grand Slam"}) == "G"
    assert _level({"Series": "Masters 1000"}) == "M"
    assert _level({"Series": "ATP250"}) == "A"


# --------------------------------------------------------------------------
# GUARDS #14 — the host's own robots.txt, implemented rather than summarised
# --------------------------------------------------------------------------

def test_the_year_directories_we_use_are_permitted():
    safety._check("GET", "http://www.tennis-data.co.uk/2026/2026.xlsx", False)
    safety._check("GET", "http://www.tennis-data.co.uk/2026w/2026.xlsx", False)


def test_the_year_directories_that_host_disallows_are_refused_BY_ROBOTS():
    """robots.txt Disallows 2000-2005. Those paths DO match the `/20` allowlist
    prefix, so only the robots rule stands between us and them - which is
    exactly why the rule is implemented rather than summarised. GUARDS #14."""
    for bad in ("/2000/2000.xlsx", "/2003/2003.xlsx", "/2005/2005.xlsx"):
        with pytest.raises(PaperOnlyViolation) as e:
            safety._check("GET", f"http://www.tennis-data.co.uk{bad}", False)
        assert "robots.txt" in str(e.value), (
            f"{bad} was refused, but by the allowlist rather than by the host's "
            f"own robots.txt - so the robots rule is not doing the work here")


def test_stuff_is_refused_too_though_by_the_allowlist():
    """/stuff/ is also Disallowed, and is refused one layer earlier because it
    does not match the `/20` prefix at all. Recorded so the distinction between
    the two mechanisms stays visible."""
    with pytest.raises(PaperOnlyViolation) as e:
        safety._check("GET", "http://www.tennis-data.co.uk/stuff/x.xlsx", False)
    assert "allowlist" in str(e.value)


def test_the_refresh_cannot_reach_anything_else_on_that_host():
    with pytest.raises(PaperOnlyViolation):
        safety._check("GET", "http://www.tennis-data.co.uk/admin", False)
