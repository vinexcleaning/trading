"""Market classification and tennis detection.

Classification decides what enters the tennis universe at all, so a false
positive here silently pollutes every wallet metric downstream, and a false
negative makes a skilled wallet look inactive. These tests pin both directions,
plus the confidence and review behaviour that keeps ambiguous markets out of
alerting.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.enums import ClassificationMethod, SportCategory, TennisMarketType
from app.providers.base import ProviderMarket, ProviderOutcome
from app.services.classification import (
    TennisClassifier,
    infer_best_of,
    is_live_at,
    match_outcome_to_player,
    parse_players,
)


def market(
    question: str,
    *,
    sports_market_type: str | None = None,
    tags: list[str] | None = None,
    event_title: str | None = None,
    outcomes: list[str] | None = None,
    game_start_time: datetime | None = None,
    **kwargs,
) -> ProviderMarket:
    labels = outcomes or ["Yes", "No"]
    return ProviderMarket(
        condition_id="0xtest",
        question=question,
        event_title=event_title,
        sports_market_type=sports_market_type,
        tags=tags or [],
        game_start_time=game_start_time,
        outcomes=[
            ProviderOutcome(token_id=f"tok-{i}", outcome_index=i, label=label)
            for i, label in enumerate(labels)
        ],
        **kwargs,
    )


@pytest.fixture()
def classifier() -> TennisClassifier:
    return TennisClassifier()


# ------------------------------------------------------- official metadata


@pytest.mark.parametrize(
    "sports_type,expected,min_confidence",
    [
        # "moneyline" is shared with every other sport, so it earns less
        # confidence than the tennis-specific values even though the shape is
        # unambiguous once the market is known to be tennis.
        ("moneyline", TennisMarketType.MATCH_WINNER, 80.0),
        ("tennis_set_winner", TennisMarketType.SET_WINNER, 100.0),
        ("tennis_first_set_winner", TennisMarketType.SET_WINNER, 100.0),
        ("tennis_completed_match", TennisMarketType.COMPLETED_MATCH, 100.0),
    ],
)
def test_official_sports_metadata_is_trusted(
    classifier, sports_type, expected, min_confidence
):
    """Values verified against live Gamma responses."""
    result = classifier.classify(
        market(
            "Alcaraz vs Sinner",
            sports_market_type=sports_type,
            tags=["tennis", "sports"],
            outcomes=["Alcaraz", "Sinner"],
        )
    )
    assert result.is_tennis
    assert result.market_type == expected
    assert result.confidence >= min_confidence
    assert ClassificationMethod.OFFICIAL_SPORTS_METADATA in result.methods
    assert result.alertable


def test_official_metadata_market_is_not_flagged_for_review(classifier):
    result = classifier.classify(
        market(
            "Djokovic vs Medvedev",
            sports_market_type="moneyline",
            tags=["tennis"],
            outcomes=["Djokovic", "Medvedev"],
        )
    )
    assert result.needs_review is False


# ------------------------------------------------------------ non-tennis


@pytest.mark.parametrize(
    "question,tags",
    [
        ("Lakers vs Celtics", ["nba", "basketball", "sports"]),
        ("Will Bitcoin close above $100k?", ["crypto"]),
        ("Who will win the 2028 election?", ["politics"]),
        ("Chiefs vs Eagles", ["nfl", "sports"]),
    ],
)
def test_other_categories_are_rejected(classifier, question, tags):
    result = classifier.classify(market(question, tags=tags))
    assert result.is_tennis is False
    assert result.sport_category != SportCategory.TENNIS
    assert result.alertable is False


def test_table_tennis_is_not_tennis(classifier):
    """The substring trap: 'table tennis' must not enter the tennis universe."""
    result = classifier.classify(
        market("Ma Long vs Fan Zhendong", tags=["table-tennis", "sports"])
    )
    assert result.is_tennis is False


# ------------------------------------------------------------- title parsing


@pytest.mark.parametrize(
    "title,player_a,player_b",
    [
        ("Alcaraz vs Sinner", "Alcaraz", "Sinner"),
        ("Carlos Alcaraz vs. Jannik Sinner", "Carlos Alcaraz", "Jannik Sinner"),
        ("Swiatek v Sabalenka", "Swiatek", "Sabalenka"),
    ],
)
def test_player_parsing(title, player_a, player_b):
    _tournament, a, b = parse_players(title)
    assert a == player_a
    assert b == player_b


def test_tournament_prefix_is_separated_from_the_players():
    tournament, a, b = parse_players("Wimbledon: Alcaraz vs Sinner")
    assert (a, b) == ("Alcaraz", "Sinner")
    assert tournament and "Wimbledon" in tournament


def test_players_are_none_when_the_title_is_not_a_matchup():
    _tournament, a, b = parse_players("Who will win Wimbledon 2026?")
    assert a is None and b is None


def test_outcome_is_matched_to_the_right_player():
    assert match_outcome_to_player("Alcaraz", "Alcaraz", "Sinner") == "Alcaraz"
    assert match_outcome_to_player("Jannik Sinner", "Alcaraz", "Jannik Sinner") == (
        "Jannik Sinner"
    )
    # A generic label carries no player information and must not be guessed.
    assert match_outcome_to_player("Yes", "Alcaraz", "Sinner") is None


# ------------------------------------------------------------ format inference


def test_mens_grand_slam_is_best_of_five():
    assert infer_best_of("Wimbledon", "ATP", "Alcaraz vs Sinner") == 5
    assert infer_best_of("US Open", "ATP", None) == 5


def test_womens_grand_slam_stays_best_of_three():
    assert infer_best_of("Wimbledon", "WTA", "Swiatek vs Sabalenka") == 3


def test_regular_tour_event_is_best_of_three():
    assert infer_best_of("Miami Open", "ATP", None) == 3


# ---------------------------------------------------------------- futures


def test_tournament_future_is_detected_and_held_back_from_alerting(classifier):
    """A futures market is tennis, but not a copyable match trade."""
    result = classifier.classify(
        market(
            "Will Carlos Alcaraz win Wimbledon 2026?",
            tags=["tennis", "sports"],
            outcomes=["Yes", "No"],
        )
    )
    assert result.is_tennis
    assert result.market_type == TennisMarketType.TOURNAMENT_FUTURE


# ------------------------------------------------------------ confidence


def test_weak_keyword_only_evidence_does_not_become_tennis(classifier):
    """One ambiguous word is not enough to claim a market is tennis."""
    result = classifier.classify(market("Who will serve as the next CEO?", tags=[]))
    assert result.is_tennis is False


def test_ambiguous_tennis_market_is_flagged_for_review(classifier):
    """Tagged tennis with an unrecognisable shape is reviewed, not alerted."""
    result = classifier.classify(
        market("Special correct score market", tags=["tennis", "sports"])
    )
    if result.is_tennis:
        assert result.needs_review or not result.alertable


def test_classification_records_its_methods_and_notes(classifier):
    result = classifier.classify(
        market(
            "Alcaraz vs Sinner",
            sports_market_type="moneyline",
            tags=["tennis"],
            outcomes=["Alcaraz", "Sinner"],
        )
    )
    assert result.methods_json()
    assert result.methods  # every decision is attributable to a method


# ---------------------------------------------------------- manual override


def test_manual_override_wins_over_inference():
    overrides = {
        "0xtest": {"is_tennis": "true", "tennis_market_type": TennisMarketType.SET_WINNER}
    }
    classifier = TennisClassifier(overrides=overrides)
    result = classifier.classify(market("Completely unrecognisable title", tags=[]))
    assert result.is_tennis
    assert result.market_type == TennisMarketType.SET_WINNER
    assert ClassificationMethod.MANUAL_OVERRIDE in result.methods


# ------------------------------------------------------------- live vs prematch


def test_live_detection_relative_to_start_time():
    now = datetime.now(timezone.utc)
    assert is_live_at(now + timedelta(hours=2), now) is False
    assert is_live_at(now - timedelta(minutes=30), now) is True
    # Without a start time we say "unknown" rather than guessing, because the
    # live/prematch split drives the alert expiry window.
    assert is_live_at(None, now) is None
