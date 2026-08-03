"""Adaptive allocation tests.

These pin the behaviours that the static scoring got wrong on real data: a stale
wallet ranking first, a decaying wallet keeping its rank because its lifetime
average was good, and a longshot strategy being penalised for the shape it is
designed to have.
"""

from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.enums import PositionStatus
from app.models import ReconstructedPosition, Wallet
from app.services.allocation import (
    MAX_SILENCE_DAYS,
    AllocationEngine,
    Stance,
    rotation_report,
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)

# Token ids must stay unique across every _positions() call, since a wallet can
# receive several blocks (an early good run plus a recent bad one, say) and
# (wallet_id, token_id, sequence) is a uniqueness constraint.
_token_seq = itertools.count()


def _wallet(db, address: str) -> Wallet:
    wallet = Wallet(address=address, source="manual")
    db.add(wallet)
    db.flush()
    return wallet


def _positions(
    db,
    wallet: Wallet,
    *,
    count: int,
    days_ago_start: int,
    days_ago_end: int,
    roi: float,
    entry: str = "0.50",
    stake: str = "100",
) -> None:
    """Add `count` positions spread over a window, each returning `roi`."""
    span = max(days_ago_start - days_ago_end, 1)
    for i in range(count):
        offset = days_ago_start - (span * i / max(count - 1, 1))
        opened = NOW - timedelta(days=offset)
        capital = Decimal(stake)
        pnl = capital * Decimal(str(roi))
        db.add(
            ReconstructedPosition(
                wallet_id=wallet.id,
                token_id=f"tok-{wallet.id}-{next(_token_seq)}",
                status=PositionStatus.SETTLED,
                is_tennis=True,
                opened_at=opened,
                opened_ts=int(opened.timestamp()),
                closed_at=opened + timedelta(hours=3),
                first_entry_price=Decimal(entry),
                avg_entry_price=Decimal(entry),
                capital_committed=capital,
                net_pnl=pnl,
                realized_pnl=pnl,
                roi=roi,
                is_win=roi > 0,
                entry_phase="prematch",
                tennis_market_type="match_winner",
                behaviour="directional",
            )
        )
    db.flush()


def _engine(db) -> AllocationEngine:
    return AllocationEngine(db, now=NOW)


# ------------------------------------------------------------- liveness gate


def test_silent_wallet_is_dropped_however_good_its_record(db_session):
    """The failure this module exists to fix.

    A wallet with an outstanding lifetime record that stopped trading two months
    ago ranked first under the static score, because a lifetime average has no
    opinion about whether the trader is still there.
    """
    wallet = _wallet(db_session, "0x" + "a1" * 20)
    _positions(
        db_session, wallet, count=44, days_ago_start=65, days_ago_end=57, roi=0.57
    )

    state = _engine(db_session).evaluate(wallet)
    assert state is not None
    assert state.stance is Stance.DROP
    assert state.form_score == 0.0
    assert state.suggested_stake_fraction == 0.0
    assert "not followable" in " ".join(state.reasons)


def test_active_wallet_survives_the_liveness_gate(db_session):
    wallet = _wallet(db_session, "0x" + "a2" * 20)
    _positions(db_session, wallet, count=40, days_ago_start=25, days_ago_end=0, roi=0.10)

    state = _engine(db_session).evaluate(wallet)
    assert state.stance is Stance.FOLLOW
    assert state.days_since_last_trade == 0


@pytest.mark.parametrize("days_silent", [MAX_SILENCE_DAYS - 1, MAX_SILENCE_DAYS + 1])
def test_liveness_gate_boundary(db_session, days_silent):
    wallet = _wallet(db_session, f"0x{'a3' * 19}{days_silent:02d}")
    _positions(
        db_session, wallet, count=40,
        days_ago_start=days_silent + 30, days_ago_end=days_silent, roi=0.10,
    )
    state = _engine(db_session).evaluate(wallet)
    if days_silent > MAX_SILENCE_DAYS:
        assert state.stance is Stance.DROP
    else:
        assert state.stance is not Stance.DROP


# ------------------------------------------------------------ decay detection


def test_decaying_wallet_is_paused_despite_good_lifetime_record(db_session):
    """A strong past must not mask a negative present.

    Observed on real data: a wallet at +10.2% per trade lifetime was losing 2.9%
    per trade over the last 30 days. Ranking on the lifetime figure would have
    kept it in the follow list while it bled.
    """
    wallet = _wallet(db_session, "0x" + "b1" * 20)
    # Excellent 90-60 days ago...
    _positions(db_session, wallet, count=40, days_ago_start=90, days_ago_end=60, roi=0.40)
    # ...losing over the last 30.
    _positions(db_session, wallet, count=20, days_ago_start=28, days_ago_end=0, roi=-0.15)

    state = _engine(db_session).evaluate(wallet)
    assert state.lifetime.mean_pct > 0, "lifetime should still look good"
    assert state.form.mean_pct < 0, "recent form should be negative"
    assert state.stance is Stance.PAUSE
    assert state.suggested_stake_fraction == 0.0


def test_deteriorating_but_still_positive_goes_on_probation(db_session):
    wallet = _wallet(db_session, "0x" + "b2" * 20)
    _positions(db_session, wallet, count=40, days_ago_start=90, days_ago_end=60, roi=0.30)
    _positions(db_session, wallet, count=20, days_ago_start=28, days_ago_end=0, roi=0.02)

    state = _engine(db_session).evaluate(wallet)
    assert state.trend_pp is not None and state.trend_pp < 0
    assert state.stance is Stance.PROBATION
    # Halved for deterioration rather than dropped outright.
    assert 0 < state.suggested_stake_fraction < 1.0


def test_improving_wallet_is_noted(db_session):
    wallet = _wallet(db_session, "0x" + "b3" * 20)
    _positions(db_session, wallet, count=30, days_ago_start=90, days_ago_end=60, roi=0.05)
    _positions(db_session, wallet, count=30, days_ago_start=28, days_ago_end=0, roi=0.25)

    state = _engine(db_session).evaluate(wallet)
    assert state.trend_pp > 0
    assert state.stance is Stance.FOLLOW
    assert any("improving" in r for r in state.reasons)


# --------------------------------------------------- concentration / longshot


def test_longshot_concentration_reduces_size_not_rank(db_session):
    """A longshot strategy earns from rare large winners by design.

    Penalising the ranking for that shape punishes the strategy for working as
    intended. Concentration belongs in the sizing decision instead.
    """
    wallet = _wallet(db_session, "0x" + "c1" * 20)
    # Mostly total losses at a longshot price...
    _positions(
        db_session, wallet, count=38, days_ago_start=28, days_ago_end=1,
        roi=-1.0, entry="0.20",
    )
    # ...redeemed by two large winners, which is the real shape: most of the
    # profit traces to a single trade.
    _positions(
        db_session, wallet, count=2, days_ago_start=20, days_ago_end=0,
        roi=25.0, entry="0.20",
    )

    state = _engine(db_session).evaluate(wallet)
    assert state.concentration is not None and state.concentration >= 0.5
    # Still ranked as followable: the lifetime return is genuinely positive.
    assert state.stance is Stance.FOLLOW
    assert state.form_score > 0
    # Sized down for variance, and told why -- but not demoted.
    assert state.suggested_stake_fraction < 1.0
    assert any("sized down" in w for w in state.warnings)
    assert any("not penalised in the ranking" in w for w in state.warnings)


def test_favourite_buyer_is_sized_down_for_tail_risk(db_session):
    """High win rate at high prices means rare, large, under-sampled losses."""
    wallet = _wallet(db_session, "0x" + "c2" * 20)
    _positions(
        db_session, wallet, count=59, days_ago_start=28, days_ago_end=0,
        roi=0.05, entry="0.95",
    )
    _positions(
        db_session, wallet, count=1, days_ago_start=14, days_ago_end=14,
        roi=-1.0, entry="0.95",
    )

    state = _engine(db_session).evaluate(wallet)
    assert state.lifetime.win_rate > 0.9
    assert state.suggested_stake_fraction < 1.0
    assert any("under-sampled" in w for w in state.warnings)


# ------------------------------------------------------------------- sizing


def test_thin_sample_is_watch_only_not_rejected(db_session):
    """A promising short record earns observation, not a verdict either way."""
    wallet = _wallet(db_session, "0x" + "d1" * 20)
    _positions(db_session, wallet, count=11, days_ago_start=28, days_ago_end=0, roi=0.54)

    state = _engine(db_session).evaluate(wallet)
    assert state.stance is Stance.WATCH
    assert state.suggested_stake_fraction == 0.0
    assert state.form_score > 0, "still ranked, just not staked"


def test_stake_fraction_scales_with_sample_size(db_session):
    small = _wallet(db_session, "0x" + "d2" * 20)
    _positions(db_session, small, count=30, days_ago_start=28, days_ago_end=0, roi=0.10)
    large = _wallet(db_session, "0x" + "d3" * 20)
    _positions(db_session, large, count=120, days_ago_start=28, days_ago_end=0, roi=0.10)

    engine = _engine(db_session)
    assert (
        engine.evaluate(small).suggested_stake_fraction
        < engine.evaluate(large).suggested_stake_fraction
    )


def test_wallets_below_the_floor_are_skipped(db_session):
    wallet = _wallet(db_session, "0x" + "d4" * 20)
    _positions(db_session, wallet, count=4, days_ago_start=10, days_ago_end=0, roi=0.10)
    assert _engine(db_session).evaluate(wallet, min_lifetime_trades=10) is None


# ------------------------------------------------------------------- report


def test_rotation_report_separates_stances_and_counts_silence(db_session):
    live = _wallet(db_session, "0x" + "e1" * 20)
    _positions(db_session, live, count=40, days_ago_start=25, days_ago_end=0, roi=0.12)
    stale = _wallet(db_session, "0x" + "e2" * 20)
    _positions(db_session, stale, count=40, days_ago_start=90, days_ago_end=60, roi=0.50)

    report = rotation_report(db_session)
    assert report["summary"]["evaluated"] == 2
    assert report["summary"]["followable"] == 1
    assert report["summary"]["dropped_for_silence"] == 1
    assert report["follow"][0]["address"] == live.address
    assert report["drop"][0]["address"] == stale.address
    # The report must state what it is and is not.
    assert "not recommendations to bet" in report["note"]


def test_follow_list_is_ordered_by_form_score(db_session):
    better = _wallet(db_session, "0x" + "f1" * 20)
    _positions(db_session, better, count=60, days_ago_start=28, days_ago_end=0, roi=0.25)
    worse = _wallet(db_session, "0x" + "f2" * 20)
    _positions(db_session, worse, count=60, days_ago_start=28, days_ago_end=0, roi=0.03)

    follow = rotation_report(db_session)["follow"]
    assert [r["address"] for r in follow] == [better.address, worse.address]
