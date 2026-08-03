"""Shared enumerations.

These are stored as strings in the database so that adding a value never
requires a migration, and so raw SQL stays readable.
"""

from __future__ import annotations

from enum import StrEnum


class WalletSource(StrEnum):
    """How a wallet entered the registry."""

    MANUAL = "manual"
    CSV_IMPORT = "csv_import"
    LEADERBOARD_VOLUME = "leaderboard_volume"
    LEADERBOARD_PROFIT = "leaderboard_profit"
    MARKET_ACTIVITY = "market_activity"
    MARKET_HOLDERS = "market_holders"
    SYSTEM_SUGGESTED = "system_suggested"
    WATCHLIST = "watchlist"


class WalletStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class ActivityType(StrEnum):
    """Values observed on data-api /activity (verified 2026-07-29)."""

    TRADE = "TRADE"
    REDEEM = "REDEEM"
    REWARD = "REWARD"
    TAKER_REBATE = "TAKER_REBATE"
    MAKER_REBATE = "MAKER_REBATE"
    SPLIT = "SPLIT"
    MERGE = "MERGE"
    CONVERSION = "CONVERSION"
    UNKNOWN = "UNKNOWN"


class TradeSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class SportCategory(StrEnum):
    TENNIS = "tennis"
    OTHER_SPORT = "other_sport"
    NON_SPORT = "non_sport"
    UNKNOWN = "unknown"


class TennisMarketType(StrEnum):
    """Tennis market shapes we can act on.

    ``sportsMarketType`` values observed live: moneyline,
    tennis_completed_match, tennis_set_winner, tennis_first_set_winner.
    """

    MATCH_WINNER = "match_winner"
    SET_WINNER = "set_winner"
    GAME_WINNER = "game_winner"
    HANDICAP = "handicap"
    TOTAL_GAMES = "total_games"
    COMPLETED_MATCH = "completed_match"
    CORRECT_SCORE = "correct_score"
    TOURNAMENT_FUTURE = "tournament_future"
    OTHER = "other"
    UNKNOWN = "unknown"


class MarketPhase(StrEnum):
    """Whether a trade happened before or during the match."""

    PREMATCH = "prematch"
    LIVE = "live"
    POST_MATCH = "post_match"
    UNKNOWN = "unknown"


class ClassificationMethod(StrEnum):
    OFFICIAL_SPORTS_METADATA = "official_sports_metadata"
    TAG = "tag"
    EVENT_METADATA = "event_metadata"
    TITLE_PARSE = "title_parse"
    KEYWORD = "keyword"
    MANUAL_OVERRIDE = "manual_override"


class PositionStatus(StrEnum):
    OPEN = "open"
    PARTIALLY_CLOSED = "partially_closed"
    CLOSED = "closed"
    SETTLED = "settled"
    REVERSED = "reversed"


class PositionBehaviour(StrEnum):
    """Behavioural label attached to a reconstructed position.

    Deliberately a *flag*, not a verdict: the spec requires we avoid pretending
    this classification is exact.
    """

    DIRECTIONAL = "directional"
    POSSIBLE_HEDGE = "possible_hedge"
    LIKELY_MARKET_MAKING = "likely_market_making"
    POSSIBLE_ARBITRAGE = "possible_arbitrage"
    LIQUIDITY_PROVISION = "liquidity_provision"
    SCALP = "scalp"
    UNCLEAR = "unclear"


class PriceSourceQuality(StrEnum):
    """Evidence tier behind a reconstructed historical price.

    This is the honesty mechanism for delay analysis. Polymarket's
    ``/prices-history`` bottoms out at 1-minute fidelity, so sub-minute follower
    delays cannot be answered from it. We fall back through progressively weaker
    evidence and record which tier produced each number.
    """

    OBSERVED_TRADE = "observed_trade"          # real print within tolerance
    INTERPOLATED_TRADE = "interpolated_trade"  # between two real prints
    MINUTE_BAR = "minute_bar"                  # prices-history point
    NEAREST_TRADE = "nearest_trade"            # closest print, outside tolerance
    MODELED = "modeled"                        # heuristic fallback
    UNAVAILABLE = "unavailable"

    @property
    def confidence(self) -> float:
        """0-100 confidence contribution for this tier."""
        return {
            "observed_trade": 100.0,
            "interpolated_trade": 80.0,
            "minute_bar": 60.0,
            "nearest_trade": 40.0,
            "modeled": 20.0,
            "unavailable": 0.0,
        }[self.value]


class SignalType(StrEnum):
    SINGLE_WALLET = "single_wallet"
    CONSENSUS = "consensus"
    POSITION_INCREASE = "position_increase"
    WALLET_EXIT = "wallet_exit"


class SignalStatus(StrEnum):
    """Alert lifecycle states surfaced in the live feed."""

    OBSERVED = "observed"
    EVALUATING = "evaluating"
    QUALIFIED = "qualified"
    REJECTED = "rejected"
    EXPIRED = "expired"
    PAPER_ENTERED = "paper_entered"
    PAPER_EXITED = "paper_exited"


class ClusterRelation(StrEnum):
    """Graded wallet-relationship labels -- never a claim of ownership."""

    LIKELY_INDEPENDENT = "likely_independent"
    POSSIBLY_RELATED = "possibly_related"
    HIGHLY_CORRELATED = "highly_correlated"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class PaperTradeStatus(StrEnum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    SETTLED = "settled"
    REJECTED = "rejected"


class ExitStrategy(StrEnum):
    HOLD_TO_RESOLUTION = "hold_to_resolution"
    FOLLOW_WALLET_EXIT = "follow_wallet_exit"
    PROFIT_TARGET = "profit_target"
    STOP_LOSS = "stop_loss"
    FIXED_HOLD = "fixed_hold"
    CONSENSUS_GONE = "consensus_gone"
    WALLET_REDUCES = "wallet_reduces"
    TRAILING_STOP = "trailing_stop"


class PaperEventType(StrEnum):
    CREATED = "created"
    FILLED = "filled"
    PARTIAL_EXIT = "partial_exit"
    EXITED = "exited"
    SETTLED = "settled"
    REJECTED = "rejected"
    MARK_TO_MARKET = "mark_to_market"


class JobStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class RiskFlag(StrEnum):
    """Wallet- and trade-level warnings shown in the UI."""

    SMALL_SAMPLE = "small_sample"
    PROFIT_CONCENTRATION = "profit_concentration"
    SEVERE_DRAWDOWN = "severe_drawdown"
    NEGATIVE_RECENT_TREND = "negative_recent_trend"
    NEGATIVE_COPYABLE_ROI = "negative_copyable_roi"
    LIKELY_MARKET_MAKING = "likely_market_making"
    LOW_LIQUIDITY_MARKETS = "low_liquidity_markets"
    AMBIGUOUS_RECONSTRUCTION = "ambiguous_reconstruction"
    SUSPECTED_RELATED_WALLET = "suspected_related_wallet"
    STALE_ACTIVITY = "stale_activity"
    THIN_DATA = "thin_data"
    RAPID_EXIT_PATTERN = "rapid_exit_pattern"
    HEDGING_BEHAVIOUR = "hedging_behaviour"
    FAST_MOVING_MARKET = "fast_moving_market"
    AMBIGUOUS_CLASSIFICATION = "ambiguous_classification"
    WIDE_SPREAD = "wide_spread"
    SURVIVORSHIP_RISK = "survivorship_risk"
    # Wins often and small, loses rarely and large -- the favourite-longshot
    # shape. Observed in real data: a wallet buying at ~$0.95 with a 98.9% win
    # rate where a single loss erased 14 wins. The danger is not the observed
    # record but that a 1-2% loss rate cannot be estimated from the handful of
    # losses such a sample contains.
    TAIL_RISK_ASYMMETRY = "tail_risk_asymmetry"


class RejectionReason(StrEnum):
    """Why a candidate signal failed to qualify. Surfaced verbatim in reports."""

    WALLET_NOT_QUALIFIED = "wallet_not_qualified"
    INSUFFICIENT_TRADES = "insufficient_trades"
    LOW_SKILL_SCORE = "low_skill_score"
    NEGATIVE_COPYABLE_ROI = "negative_copyable_roi"
    EXCESSIVE_DRAWDOWN = "excessive_drawdown"
    LOW_DATA_CONFIDENCE = "low_data_confidence"
    PRICE_MOVED_TOO_FAR = "price_moved_too_far"
    INSUFFICIENT_LIQUIDITY = "insufficient_liquidity"
    SPREAD_TOO_WIDE = "spread_too_wide"
    SIGNAL_TOO_OLD = "signal_too_old"
    WALLET_ALREADY_EXITING = "wallet_already_exiting"
    AMBIGUOUS_CLASSIFICATION = "ambiguous_classification"
    LOW_COPYABILITY = "low_copyability"
    MARKET_MAKING_BEHAVIOUR = "market_making_behaviour"
    CLUSTERED_WALLETS = "clustered_wallets"
    INSUFFICIENT_CONSENSUS = "insufficient_consensus"
    POSITION_TOO_SMALL = "position_too_small"
    MARKET_CLOSED = "market_closed"
    DUPLICATE_SIGNAL = "duplicate_signal"
    RISK_FLAGGED = "risk_flagged"
    NO_EDGE = "no_edge"
