"""Database-facing pipeline behaviour.

The pure clustering algorithm is tested in ``test_signals_clustering``. What is
tested here is the persistence path, which is where a correct computation can
still fail to reach the column that the rest of the system reads.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.enums import PositionBehaviour, PositionStatus
from app.models import Market, Outcome, ReconstructedPosition, Wallet
from app.services.pipeline import AnalyticsPipeline, cluster_membership_map

BASE_TS = 1_760_000_000


@pytest.fixture()
def related_wallets(db_session):
    """Two wallets entering the same markets minutes apart, plus a loner."""
    wallets = {}
    for name in ("alpha", "beta", "loner"):
        wallet = Wallet(address="0x" + name.encode().hex().ljust(40, "0")[:40], nickname=name)
        db_session.add(wallet)
        wallets[name] = wallet
    db_session.flush()

    markets = []
    for index in range(8):
        market = Market(
            condition_id=f"0xcluster{index}",
            question=f"Match {index}",
            is_tennis=True,
            classification_confidence=100.0,
        )
        db_session.add(market)
        db_session.flush()
        outcome = Outcome(
            market_id=market.id,
            token_id=f"cluster-token-{index}",
            outcome_index=0,
            label="Player A",
        )
        db_session.add(outcome)
        markets.append((market, outcome))
    db_session.flush()

    def add_position(wallet: Wallet, index: int, market, outcome, offset_seconds: int):
        opened = BASE_TS + index * 86_400 + offset_seconds
        db_session.add(
            ReconstructedPosition(
                wallet_id=wallet.id,
                market_id=market.id,
                outcome_id=outcome.id,
                token_id=outcome.token_id,
                condition_id=market.condition_id,
                outcome_index=0,
                status=PositionStatus.CLOSED,
                opened_at=datetime.fromtimestamp(opened, tz=timezone.utc),
                opened_ts=opened,
                closed_at=datetime.fromtimestamp(opened + 7200, tz=timezone.utc),
                closed_ts=opened + 7200,
                first_entry_price=Decimal("0.50"),
                avg_entry_price=Decimal("0.50"),
                avg_exit_price=Decimal("0.60"),
                capital_committed=Decimal("200"),
                max_shares=Decimal("400"),
                total_shares_bought=Decimal("400"),
                total_shares_sold=Decimal("400"),
                realized_pnl=Decimal("40"),
                net_pnl=Decimal("40"),
                roi=0.2,
                is_win=True,
                holding_seconds=7200,
                behaviour=PositionBehaviour.DIRECTIONAL,
                is_tennis=True,
                reconstruction_confidence=100.0,
            )
        )

    for index, (market, outcome) in enumerate(markets):
        add_position(wallets["alpha"], index, market, outcome, 0)
        # Beta follows alpha into the same outcome ~90 seconds later.
        add_position(wallets["beta"], index, market, outcome, 90)

    # The loner trades different markets entirely.
    for index, (market, outcome) in enumerate(markets[:5]):
        add_position(wallets["loner"], index + 100, market, outcome, 500_000)

    db_session.commit()
    return wallets


def test_cluster_membership_is_written_back_to_wallets(db_session, related_wallets):
    """The cluster id must reach ``Wallet.suspected_cluster_id``.

    Everything downstream -- consensus de-duplication, the wallet profile page --
    reads that column, not the membership table. If it stays NULL the
    independence rule silently does nothing.
    """
    pipeline = AnalyticsPipeline(db_session)
    assert pipeline.compute_clusters(min_positions=4) >= 1
    db_session.commit()

    alpha = related_wallets["alpha"]
    beta = related_wallets["beta"]
    db_session.refresh(alpha)
    db_session.refresh(beta)

    assert alpha.suspected_cluster_id is not None
    assert alpha.suspected_cluster_id == beta.suspected_cluster_id

    membership = cluster_membership_map(db_session)
    assert membership[alpha.id] == membership[beta.id]
    assert membership[alpha.id] is not None


def test_cluster_assignment_survives_a_second_run(db_session, related_wallets):
    """Re-running must not silently blank the assignment.

    The rebuild nulls every wallet's cluster before reinserting. With the bulk
    update unsynchronised, the in-memory objects keep their old id, SQLite reuses
    the same cluster ids, and re-assigning the same value looks like no change --
    so no UPDATE is emitted and the column stays NULL.
    """
    pipeline = AnalyticsPipeline(db_session)
    pipeline.compute_clusters(min_positions=4)
    db_session.commit()

    pipeline.compute_clusters(min_positions=4)
    db_session.commit()

    membership = cluster_membership_map(db_session)
    alpha_id = related_wallets["alpha"].id
    beta_id = related_wallets["beta"].id

    assert membership[alpha_id] is not None, (
        "cluster assignment was lost on the second run; consensus independence "
        "checks would be inert"
    )
    assert membership[alpha_id] == membership[beta_id]


def test_unrelated_wallet_is_not_clustered(db_session, related_wallets):
    pipeline = AnalyticsPipeline(db_session)
    pipeline.compute_clusters(min_positions=4)
    db_session.commit()

    membership = cluster_membership_map(db_session)
    loner_id = related_wallets["loner"].id
    alpha_id = related_wallets["alpha"].id
    assert membership[loner_id] != membership[alpha_id] or membership[loner_id] is None
