"""GUARDS #1, #2, #9, #13 — the leak canaries and the content assertions.

The selection tests include a GUARD-ROT test: they assert that the known-bad
dedupe rules still produce a DIFFERENT answer from the one in use. A guard that
cannot fail is not a guard.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from src.brief import _r, _ratio  # noqa: E402
from src.charting import ServeResponse, _game_sequence  # noqa: E402
from src.kalshi_read import (Quote, build_match_pool, dedupe_event,  # noqa: E402
                             parse_rules)
from src.sackmann import norm_name, parse_score, surname_of  # noqa: E402


def q(ticker, *, volume, oi, last, ask, bid=None, player="P", event="E1"):
    return Quote(ticker=ticker, event_ticker=event, series="KXATPMATCH",
                 player=player, yes_bid=(bid if bid is not None else ask - 2),
                 yes_ask=ask, yes_bid_size=100.0, yes_ask_size=100.0,
                 last=last, volume=volume, open_interest=oi, status="active",
                 open_time=None, expected_expiration=None, result="",
                 fetched_at="2026-08-06T00:00:00Z")


# --------------------------------------------------------------------------
# GUARDS #1 — the selection canary
# --------------------------------------------------------------------------

def test_dedupe_uses_ticker_order_and_nothing_else():
    """Construct a pair where volume, open interest and last price ALL point
    the other way. If the dedupe ever reads one of them, this flips."""
    a = q("KXATPMATCH-E1-AAA", volume=10.0, oi=10.0, last=20, ask=22, player="A")
    b = q("KXATPMATCH-E1-ZZZ", volume=99999.0, oi=99999.0, last=95, ask=96, player="B")
    m = dedupe_event([b, a])
    assert m.primary.ticker.endswith("AAA"), (
        "the dedupe picked the high-volume/high-price side. That rule reads "
        "P(kept wins) = 0.5356, z = +10.0, and it voided three phases of "
        "earlier work in this repo.")


def test_dedupe_is_stable_under_input_order():
    a = q("KXATPMATCH-E1-AAA", volume=1.0, oi=1.0, last=20, ask=22, player="A")
    b = q("KXATPMATCH-E1-ZZZ", volume=2.0, oi=2.0, last=80, ask=82, player="B")
    assert dedupe_event([a, b]).primary.ticker == dedupe_event([b, a]).primary.ticker


def test_guard_rot_the_bad_rules_would_still_pick_differently():
    """GUARDS #9. If sorting by volume ever agrees with sorting by ticker on
    this fixture, the fixture has stopped testing anything."""
    a = q("KXATPMATCH-E1-AAA", volume=10.0, oi=10.0, last=20, ask=22, player="A")
    b = q("KXATPMATCH-E1-ZZZ", volume=99999.0, oi=99999.0, last=95, ask=96, player="B")
    by_volume = sorted([a, b], key=lambda x: -x.volume)[0]
    by_last = sorted([a, b], key=lambda x: -(x.last or 0))[0]
    by_oi = sorted([a, b], key=lambda x: -(x.open_interest or 0))[0]
    chosen = dedupe_event([a, b]).primary
    for bad, name in ((by_volume, "volume"), (by_last, "last price"), (by_oi, "open interest")):
        assert bad.ticker != chosen.ticker, f"the {name} rule now agrees - fixture is dead"


def test_the_dedupe_source_reads_no_outcome_bearing_field():
    """Source-level, so a future edit cannot quietly reintroduce it."""
    import ast
    src = (ROOT / "src" / "kalshi_read.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name == "dedupe_event")
    # Drop the docstring. It legitimately NAMES the fields it refuses to read,
    # and a text-level scan cannot tell that apart from reading them - which is
    # the whole reason this test parses the AST instead of grepping.
    stmts = fn.body
    if stmts and isinstance(stmts[0], ast.Expr) and isinstance(stmts[0].value, ast.Constant):
        stmts = stmts[1:]
    code = "\n".join(ast.unparse(s) for s in stmts)
    for bad in ("volume", "open_interest", "last_price", "liquidity", "result"):
        assert bad not in code, f"dedupe_event references {bad!r}: {code}"
    # and the sort key must be the ticker
    assert "key=lambda q: q.ticker" in code


# --------------------------------------------------------------------------
# GUARDS #2 — no outcome may reach the pool
# --------------------------------------------------------------------------

def test_a_market_carrying_a_result_is_excluded_by_the_runner():
    src = (ROOT / "src" / "forward.py").read_text(encoding="utf-8")
    assert "if not q.result" in src, (
        "the runner no longer filters markets that already carry a result. "
        "An open market with a result is a settled market that has not been "
        "reclassified, and letting one in hands every bot the answer.")


# --------------------------------------------------------------------------
# GUARDS #18 — the structural invariant
# --------------------------------------------------------------------------

def test_bids_summing_over_a_dollar_is_the_stale_book_signal():
    a = q("E1-A", volume=1, oi=1, last=60, ask=62, bid=60, player="A")
    b = q("E1-B", volume=1, oi=1, last=45, ask=47, bid=45, player="B")   # 60+45=105
    m = dedupe_event([a, b])
    assert m.crossed() is True
    assert m.bid_sum() == 105


def test_asks_summing_under_a_dollar_is_arbitrage_not_a_stale_book():
    a = q("E1-A", volume=1, oi=1, last=76, ask=76, bid=75, player="A")
    b = q("E1-B", volume=1, oi=1, last=23, ask=23, bid=21, player="B")   # 99
    m = dedupe_event([a, b])
    assert m.crossed() is False, "gross arbitrage mislabelled as a stale book"
    assert m.gross_arb_cents() == 1


# --------------------------------------------------------------------------
# Parsing — GUARDS #13, assert the CONTENT
# --------------------------------------------------------------------------

def test_the_rules_text_yields_tournament_round_and_surface():
    r = parse_rules(
        "If Learner Tien wins the Tien vs Paul professional tennis match in the "
        "2026 ATP Montreal Round Of 32 after a ball has been played, then the "
        "market resolves to Yes.")
    assert r["rules_parsed"] is True
    assert r["surname_a"] == "Tien" and r["surname_b"] == "Paul"
    assert r["round"] == "R32"
    assert r["year"] == 2026
    assert "Montreal" in r["tournament"]
    assert r["surface"] == "Hard"


def test_an_unknown_tournament_yields_no_surface_rather_than_a_guess():
    r = parse_rules("If A wins the A vs B tennis match in the 2026 ITF M15 "
                    "Nowhereville Round Of 32 after a ball has been played")
    assert r["rules_parsed"] is True
    assert r["surface"] is None, "a guessed surface is worse than a missing one"


def test_unparseable_rules_do_not_raise_and_do_not_invent():
    r = parse_rules("this is not a tennis rule at all")
    assert r["rules_parsed"] is False
    assert r["surname_a"] is None and r["surface"] is None


# --------------------------------------------------------------------------
# Score parsing — where the deciding-set fact comes from
# --------------------------------------------------------------------------

@pytest.mark.parametrize("score,best_of,deciding,straight,tb", [
    ("6-4 6-3", 3, False, True, 0),
    ("6-4 3-6 7-5", 3, True, False, 0),
    ("7-6(4) 6-7(2) 6-3", 3, True, False, 2),
    ("6-4 6-4 6-4", 5, False, True, 0),
    ("6-4 3-6 6-4 3-6 6-4", 5, True, False, 0),
    ("6-2 2-1 RET", 3, False, False, 0),
])
def test_parse_score(score, best_of, deciding, straight, tb):
    p = parse_score(score, best_of)
    assert p.went_deciding is deciding
    assert p.straight is straight
    assert p.tiebreaks == tb


def test_a_retirement_is_not_a_completed_match():
    p = parse_score("6-2 2-1 RET", 3)
    assert p.retired is True and p.completed is False


# --------------------------------------------------------------------------
# Names
# --------------------------------------------------------------------------

def test_accents_fold_so_the_player_is_not_invisible():
    assert norm_name("Aleksandar Vukić") == norm_name("Aleksandar Vukic")
    assert norm_name("Miomir Kecmanović") == "miomir kecmanovic"
    assert norm_name("Borna Ćorić") == "borna coric"
    assert surname_of("Jesper De Jong") == "jong"


# --------------------------------------------------------------------------
# Every rate carries its denominator
# --------------------------------------------------------------------------

def test_a_rate_is_never_a_bare_number():
    r = _r(3, 4)
    assert r == {"value": 0.75, "w": 3, "n": 4}
    assert _r(0, 0)["value"] is None, "an empty record must be None, never 0.0"
    assert _ratio(0, 0)["value"] is None


# --------------------------------------------------------------------------
# The game sequence the after-break statistic rests on
# --------------------------------------------------------------------------

def test_game_sequence_reads_the_last_point_of_each_game():
    rows = [
        {"Set1": "0", "Set2": "0", "Gm#": "1", "Svr": "1", "PtWinner": "1"},
        {"Set1": "0", "Set2": "0", "Gm#": "1", "Svr": "1", "PtWinner": "2"},
        {"Set1": "0", "Set2": "0", "Gm#": "1", "Svr": "1", "PtWinner": "1"},
        {"Set1": "0", "Set2": "0", "Gm#": "2", "Svr": "2", "PtWinner": "1"},
        {"Set1": "0", "Set2": "0", "Gm#": "2", "Svr": "2", "PtWinner": "1"},
    ]
    assert _game_sequence(rows) == [(1, 1), (2, 1)]


def test_the_after_break_control_is_a_matched_pair_not_a_baseline():
    """GUARDS #20. `breakback_vs_control` compares like with like inside the
    same match; `breakback_delta` compares against all games including those
    against weaker opponents."""
    s = ServeResponse(player="X", serve_games=100, holds=75,
                      return_games=100, breaks=25, broken=25,
                      breakback_next=5, breakback_chances=25,
                      breakback_after_hold=25, breakback_after_hold_chances=75,
                      held_after_broken=15, held_after_broken_chances=25,
                      held_after_hold=60, held_after_hold_chances=75)
    d = s.as_dict()
    assert d["break_rate"] == pytest.approx(0.25)
    assert d["breakback_rate"] == pytest.approx(0.20)
    assert d["break_after_hold"] == pytest.approx(0.3333, abs=1e-3)
    assert d["breakback_delta"] == pytest.approx(-0.05)
    assert d["breakback_vs_control"] == pytest.approx(-0.1333, abs=1e-3)
    assert abs(d["breakback_vs_control"]) > abs(d["breakback_delta"]), (
        "the controlled figure must be able to differ from the uncontrolled one, "
        "or the control is decorative")


# --------------------------------------------------------------------------
# The substring trap. Third time in this repo. GUARDS #22.
# --------------------------------------------------------------------------

def test_challenger_is_not_grass():
    """"C-halle-nger" contains "halle".

    Unbounded, that painted 160 settled Challenger matches as GRASS in August,
    when the grass season ends in July. Nothing caught it: the field was
    populated, the value was a legal surface, and the count looked plausible.
    """
    from src.kalshi_read import _SURFACE_HINTS
    for name in ("Challenger Hamburg", "Challenger Todi", "Challenger Astana",
                 "Challenger Lexington", "ATP Challenger Tour"):
        hits = [s for pat, s in _SURFACE_HINTS if re.search(pat, name, re.I)]
        assert "Grass" not in hits, f"{name!r} matched Grass: {hits}"


def test_the_real_grass_venues_still_match():
    """A boundary fix that breaks the true positives is not a fix."""
    from src.kalshi_read import _SURFACE_HINTS
    for name, want in (("Halle", "Grass"), ("Wimbledon", "Grass"),
                       ("Eastbourne", "Grass"), ("Montreal", "Hard"),
                       ("Hamburg", "Clay"), ("Roland Garros", "Clay")):
        hits = [s for pat, s in _SURFACE_HINTS if re.search(pat, name, re.I)]
        assert want in hits, f"{name!r} lost its {want} match: {hits}"


def test_every_surface_pattern_is_word_bounded():
    """Source-level, so a new venue added without boundaries fails the build."""
    from src.kalshi_read import _SURFACE_HINTS
    for pat, surf in _SURFACE_HINTS:
        assert pat.startswith(r"\b") and pat.endswith(r"\b"), (
            f"the {surf} pattern is not word-bounded: {pat[:40]}... "
            f"An unbounded name matches inside other words - that is how "
            f"Challenger became Grass.")


def test_the_venue_key_strips_the_challenger_prefix():
    """The other half of the same bug: 'Challenger Hamburg' missed the archive
    index entirely, which is why it fell through to the regex table at all."""
    from src.sackmann import venue_key
    assert venue_key("Challenger Hamburg") == "hamburg"
    assert venue_key("M25 Koksijde") == "koksijde"
    assert venue_key("ATP Montreal") == "montreal"
    assert venue_key("W75 Leipzig") == "leipzig"


# --------------------------------------------------------------------------
# pre-game: the only mentality that must NOT act once the match is under way
# --------------------------------------------------------------------------

def _brief_with_start(delta_hours):
    """A minimal brief whose scheduled start is delta_hours from now."""
    from datetime import datetime, timedelta, timezone
    from src.brief import Brief
    start = (datetime.now(timezone.utc) + timedelta(hours=delta_hours)).isoformat()
    return Brief(
        event_ticker="E1", built_at="now", tour="atp", tier="ATP", series="KXATPMATCH",
        tournament="Montreal", round="R32", surface="Hard",
        surface_source="test", surface_meta={},
        player_a="A Player", player_b="B Player",
        a={"resolved": True}, b={"resolved": True},
        h2h={"n": 0, "a_wins": 0, "b_wins": 0, "meetings": []},
        market={"expected_expiration": start, "stale_book": False},
        model={"elo_prob_a": 0.70}, staleness_days=3, archive_last_date=20260601,
        coverage={}, warnings=[])


def test_pre_game_refuses_once_the_match_has_started():
    """The whole point of this mentality is the clock. If it can fire after the
    first ball it is an in-play bot wearing a pre-game label - and this repo
    measured 97.4% of the price move as already gone by then."""
    from src.bots import PreGameMentality, LiveState, _score
    m = PreGameMentality()
    started = _brief_with_start(-0.5)          # began 30 minutes ago
    cons, _ = m.consider(None, started, LiveState("E1", "E1-A"), "E1-A", "A Player", 60, 2)
    assert any(c.tactic == "already_started" for c in cons)
    assert _score(cons) < m.enter_at, "pre-game was willing to bet on a live match"


def test_pre_game_refuses_when_there_is_no_start_time():
    from src.bots import PreGameMentality, LiveState, _score
    m = PreGameMentality()
    b = _brief_with_start(5)
    b.market["expected_expiration"] = None
    cons, _ = m.consider(None, b, LiveState("E1", "E1-A"), "E1-A", "A Player", 60, 2)
    assert any(c.tactic == "no_start_time" for c in cons)
    assert _score(cons) < m.enter_at


def test_pre_game_will_consider_a_match_that_has_not_started():
    from src.bots import PreGameMentality, LiveState
    m = PreGameMentality()
    cons, _ = m.consider(None, _brief_with_start(6), LiveState("E1", "E1-A"),
                         "E1-A", "A Player", 60, 2)
    assert any(c.tactic == "pre_game" for c in cons), (
        "pre-game refused a match six hours away - it can never trade")


def test_pre_game_does_not_read_recent_form():
    """Form is ten weeks stale for 90% of this pool. A pre-game bot leaning on
    it would measure staleness, not the idea. Source-level so it cannot creep
    back in."""
    import ast
    src = (ROOT / "src" / "bots.py").read_text(encoding="utf-8")
    cls = next(n for n in ast.parse(src).body
               if isinstance(n, ast.ClassDef) and n.name == "PreGameMentality")
    fn = next(n for n in cls.body
              if isinstance(n, ast.FunctionDef) and n.name == "consider")
    stmts = fn.body[1:] if (fn.body and isinstance(fn.body[0], ast.Expr)) else fn.body
    code = "\n".join(ast.unparse(s) for s in stmts)
    for bad in ("form_last10", "form_last20", "form_last90d"):
        assert bad not in code, (
            f"PreGameMentality reads {bad!r}. That field is ten weeks stale for "
            f"90% of this pool; using it makes the bot a staleness detector.")


def test_the_single_exit_mentality_really_gets_one_bot():
    from src.bots import BOT_NAMES
    pg = [b for b in BOT_NAMES if b.startswith("pre-game")]
    assert pg == ["pre-game__hold"], pg
    assert len(BOT_NAMES) == 17
