"""Adaptive wallet rotation.

The rules exist to catch a wallet *while* its edge is working and release it when
it turns, without whipsawing on ordinary variance.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.rotation import (
    RotationAction,
    RotationConfig,
    TradeOutcome,
    WalletRotationEngine,
    rank_candidates,
)

NOW = datetime(2026, 7, 30, tzinfo=timezone.utc)


def trades(n: int, *, win_rate: float, price: float, end_days_ago: int = 0,
           per_day: float = 5.0) -> list[TradeOutcome]:
    """Build n trades ending `end_days_ago` before NOW."""
    out = []
    end = NOW - timedelta(days=end_days_ago)
    for i in range(n):
        ts = int((end - timedelta(days=(n - i) / per_day)).timestamp())
        # Bresenham-style spread so wins are distributed evenly rather than
        # bunched -- bunching would leave the rolling window all-wins or
        # all-losses and test nothing.
        is_win = int((i + 1) * win_rate) > int(i * win_rate)
        out.append(TradeOutcome(opened_ts=ts, entry_price=price, is_win=is_win))
    return out


def engine(**overrides) -> WalletRotationEngine:
    return WalletRotationEngine(RotationConfig(**overrides), now=NOW)


def test_active_wallet_with_edge_is_followed():
    """400 trades in two days beats a long stale record -- sample is counted in
    outcomes, not calendar time."""
    d = engine().evaluate(
        "0xhot", trades(400, win_rate=0.60, price=0.50, per_day=200), currently_followed=False
    )
    assert d.action is RotationAction.FOLLOW
    assert d.window_edge > 0.05


def test_dormant_wallet_is_never_followed_however_good():
    """The decisive question is whether it is still trading."""
    d = engine().evaluate(
        "0xdead", trades(200, win_rate=0.85, price=0.50, end_days_ago=57), currently_followed=False
    )
    assert d.action is RotationAction.IGNORE
    assert "silent for 57 days" in " ".join(d.reasons)


def test_dormant_wallet_already_followed_is_dropped():
    d = engine().evaluate(
        "0xdead", trades(200, win_rate=0.85, price=0.50, end_days_ago=57), currently_followed=True
    )
    assert d.action is RotationAction.DROP


def test_followed_wallet_is_dropped_when_edge_turns_negative():
    d = engine().evaluate(
        "0xfading", trades(60, win_rate=0.40, price=0.50), currently_followed=True
    )
    assert d.action is RotationAction.DROP
    assert "fallen below" in " ".join(d.reasons)


def test_followed_wallet_survives_ordinary_variance():
    """A thin positive edge must not trigger a sale -- that is the whipsaw the
    drop line sits below zero to prevent."""
    d = engine().evaluate(
        "0xsteady", trades(60, win_rate=0.51, price=0.50), currently_followed=True
    )
    assert d.action is RotationAction.HOLD


def test_hot_streak_on_too_few_trades_is_only_watched():
    """A burst of luck cannot promote a wallet on its own."""
    d = engine().evaluate(
        "0xlucky", trades(8, win_rate=1.0, price=0.40), currently_followed=False
    )
    assert d.action is RotationAction.WATCH
    assert "before form means anything" in " ".join(d.reasons)


def test_infrequent_trader_is_watched_not_followed():
    """If the window cannot refresh, the signal is stale by construction."""
    d = engine(min_trades_per_day=1.0).evaluate(
        "0xslow", trades(40, win_rate=0.70, price=0.50, per_day=0.1), currently_followed=False
    )
    assert d.action is RotationAction.WATCH


def test_edge_is_measured_against_price_not_raw_win_rate():
    """Winning 90% at $0.95 is a negative edge; winning 45% at $0.35 is positive."""
    favourite = engine().evaluate(
        "0xfav", trades(60, win_rate=0.90, price=0.95), currently_followed=False
    )
    longshot = engine().evaluate(
        "0xdog", trades(60, win_rate=0.45, price=0.35), currently_followed=False
    )
    assert favourite.window_edge < 0
    assert favourite.action is RotationAction.IGNORE
    assert longshot.window_edge > 0
    assert longshot.action is RotationAction.FOLLOW


def test_ranking_puts_followable_wallets_first():
    ds = [
        engine().evaluate("0xa", trades(60, win_rate=0.40, price=0.50)),
        engine().evaluate("0xb", trades(60, win_rate=0.65, price=0.50)),
    ]
    ranked = rank_candidates(ds)
    assert ranked[0].address == "0xb"
    assert ranked[0].is_followable
