"""Tests for the replay at the centre of the comeback table.

Everything the table says rests on `observations()` walking a match minute by
minute and getting the state right. That function has no natural check on it --
a subtly wrong replay produces a table that looks completely normal and is
wrong everywhere. So it is tested against matches whose answer is known by
hand.

    py -3 soccer/tests/test_comeback_logic.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import build_comeback_table as B  # noqa: E402


def match(goals, tiers=("unknown", "unknown"), league="test"):
    """goals: list of (minute, 'home'|'away'). Regulation score is derived."""
    gs = [{"minute": mn, "side": sd, "kind": "goal"} for mn, sd in goals]
    gs.sort(key=lambda g: g["minute"])
    return {
        "espn_id": "x", "league": league, "date": "2020-01-01",
        "goals": gs,
        "reg_h": sum(1 for g in gs if g["side"] == "home" and g["minute"] <= 90),
        "reg_a": sum(1 for g in gs if g["side"] == "away" and g["minute"] <= 90),
        "home_tier": tiers[0], "away_tier": tiers[1], "has_strength": True,
    }


def at(m, minute):
    for o in B.observations(m):
        if o["minute"] == minute:
            return o
    return None


def test_goalless_draw_yields_nothing():
    """Nobody is ever ahead, so the match is in no cell at all."""
    assert list(B.observations(match([]))) == []


def test_the_users_own_example():
    """Home scores in the 20th and holds on. At minute 80 it is 1-0 and the
    team behind did NOT come back."""
    m = match([(20, "home")])
    o = at(m, 80)
    assert o["lead"] == 1 and o["trail"] == 0
    assert o["trailer_won"] is False
    # and before the goal there is no observation at all
    assert at(m, 19) is None
    assert at(m, 20) is not None


def test_a_real_comeback_is_counted_at_every_minute_it_was_live():
    """0-1 down at 70, equalise at 85, win at 89. The away side was ahead from
    minute 10 to 84, and the home side came back -- so every minute in that
    range is a comeback, and the minutes after it are a different state."""
    m = match([(10, "away"), (85, "home"), (89, "home")])
    for minute in (10, 45, 70, 80, 84):
        o = at(m, minute)
        assert o["lead"] == 1 and o["trail"] == 0, minute
        assert o["trailer_won"] is True, minute
    # at 85 it is level -- no observation
    assert at(m, 85) is None, "level at 85, so it belongs in no cell"
    # at 89 the home side leads 2-1 and the trailer (away) did not come back.
    # Note the cell is 2-1, NOT 1-0 -- the exact scoreline moves with the match.
    o = at(m, 89)
    assert (o["lead"], o["trail"]) == (2, 1), (o["lead"], o["trail"])
    assert o["trailer_won"] is False


def test_a_draw_is_not_a_comeback():
    """This is the whole point of the bet: betting against the team behind pays
    on a draw. Equalising in the 90th must NOT count as a comeback."""
    m = match([(30, "home"), (90, "away")])
    o = at(m, 80)
    assert o["lead"] == 1 and o["trail"] == 0
    assert o["trailer_won"] is False, "an equaliser is not a comeback"


def test_exact_scoreline_not_just_the_gap():
    """3-2 and 1-0 are both one goal and are different cells."""
    m = match([(5, "home"), (10, "home"), (15, "home"),
               (20, "away"), (25, "away")])
    o = at(m, 80)
    assert (o["lead"], o["trail"]) == (3, 2)


def test_the_leader_can_change_sides_mid_match():
    """Home leads, away turns it round. The tier labels must follow the lead."""
    m = match([(10, "home"), (50, "away"), (60, "away")],
              tiers=("top third", "bottom third"))
    early = at(m, 20)
    assert early["leader_tier"] == "top third"
    assert early["trailer_tier"] == "bottom third"
    assert early["trailer_won"] is True          # away wins 2-1
    late = at(m, 70)
    assert late["leader_tier"] == "bottom third"  # away leads now
    assert late["trailer_tier"] == "top third"
    assert late["trailer_won"] is False           # home does not come back


def test_stoppage_time_goal_counts_at_minute_90():
    """A '90+4' goal is stored as minute 90, which is what the clock said."""
    m = match([(90, "away"), (30, "home")])
    o = at(m, 89)
    assert (o["lead"], o["trail"]) == (1, 0)
    assert o["trailer_won"] is False, "the 90th-minute goal only levelled it"


def test_extra_time_goals_do_not_decide_a_regulation_market():
    """A goal at 105 is extra time. It must not turn a regulation draw into a
    comeback, because the state and the result are both read at 90."""
    gs = [{"minute": 30, "side": "home", "kind": "goal"},
          {"minute": 88, "side": "away", "kind": "goal"},
          {"minute": 105, "side": "away", "kind": "goal"}]
    m = {"espn_id": "x", "league": "cup", "date": "2020-01-01", "goals": gs,
         "reg_h": 1, "reg_a": 1, "home_tier": "unknown",
         "away_tier": "unknown", "has_strength": True}
    o = at(m, 80)
    assert o["trailer_won"] is False, "extra time must not count as a comeback"


def test_wilson_range_never_goes_negative():
    """At two or three in a hundred the simple range dips below zero, which is
    where a reader stops believing the table."""
    lo, hi = B.wilson(2, 100)
    assert lo >= 0.0 and hi <= 1.0 and lo < 0.02 < hi
    lo, hi = B.wilson(0, 500)
    assert lo == 0.0 and 0 < hi < 0.02


def test_breakeven_matches_hand_arithmetic():
    """97 cents to win 3, minus the fee, is about 2.8 comebacks per 100."""
    b = B.breakeven_rate(97) * 100
    assert 2.5 < b < 3.0, b
    assert B.breakeven_rate(98) < B.breakeven_rate(95), \
        "paying more must allow FEWER comebacks"


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL  {name}: {e}")
    print(f"\n{fails} failure(s)")
    sys.exit(1 if fails else 0)
