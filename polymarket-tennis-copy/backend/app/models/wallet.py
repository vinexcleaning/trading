"""Wallet registry, tags and clustering."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import UtcDateTime, Base, Money
from ..enums import ClusterRelation, WalletSource, WalletStatus


class Wallet(Base):
    """A tracked Polymarket proxy wallet.

    Newly discovered wallets are never trusted: ``manually_approved`` defaults to
    False and alerting requires approval unless explicitly disabled in settings.
    """

    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Stored lowercase for stable joins; addresses are case-insensitive.
    address: Mapped[str] = mapped_column(String(42), unique=True, nullable=False, index=True)
    nickname: Mapped[str | None] = mapped_column(String(120))
    pseudonym: Mapped[str | None] = mapped_column(String(120))

    source: Mapped[str] = mapped_column(String(40), default=WalletSource.MANUAL, nullable=False)
    source_detail: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=WalletStatus.ACTIVE, nullable=False)

    manually_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    on_watchlist: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text)
    # JSON-encoded list[str] of RiskFlag values.
    risk_flags: Mapped[str | None] = mapped_column(Text)

    suspected_cluster_id: Mapped[int | None] = mapped_column(
        ForeignKey("wallet_clusters.id", ondelete="SET NULL")
    )

    first_activity_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    last_activity_at: Mapped[datetime | None] = mapped_column(UtcDateTime, index=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    last_sync_success_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    last_sync_error: Mapped[str | None] = mapped_column(Text)
    # Highest activity timestamp already ingested -- drives incremental sync.
    sync_cursor_ts: Mapped[int | None] = mapped_column(Integer)
    backfill_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Observed portfolio value from data-api /value (context for sizing).
    observed_portfolio_value: Mapped[Decimal | None] = mapped_column(Money)

    # Priority for the sync scheduler: higher wins.
    sync_priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tags: Mapped[list[WalletTag]] = relationship(
        back_populates="wallet", cascade="all, delete-orphan", lazy="selectin"
    )
    cluster: Mapped[WalletCluster | None] = relationship(
        foreign_keys=[suspected_cluster_id], back_populates="wallets"
    )

    __table_args__ = (
        Index("ix_wallets_status_approved", "status", "manually_approved"),
        Index("ix_wallets_sync", "status", "sync_priority", "last_sync_success_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Wallet {self.address} {self.status}>"


class WalletTag(Base):
    """Free-form label on a wallet (e.g. ``clay-specialist``)."""

    __tablename__ = "wallet_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    wallet: Mapped[Wallet] = relationship(back_populates="tags")

    __table_args__ = (UniqueConstraint("wallet_id", "tag", name="uq_wallet_tag"),)


class WalletCluster(Base):
    """A group of wallets whose behaviour is suspiciously similar.

    The label is graded (see :class:`ClusterRelation`) and never asserts common
    ownership. Its purpose is to stop three related wallets from being counted
    as three independent confirmations in the consensus engine.
    """

    __tablename__ = "wallet_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    relation: Mapped[str] = mapped_column(
        String(30), default=ClusterRelation.INSUFFICIENT_EVIDENCE, nullable=False
    )
    # 0-1 strength of the behavioural similarity evidence.
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Human-readable justification: which signals fired and how strongly.
    evidence: Mapped[str | None] = mapped_column(Text)
    member_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    wallets: Mapped[list[Wallet]] = relationship(
        foreign_keys=[Wallet.suspected_cluster_id], back_populates="cluster"
    )
    members: Mapped[list[WalletClusterMember]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan"
    )


class WalletClusterMember(Base):
    """Pairwise similarity evidence between a wallet and its cluster."""

    __tablename__ = "wallet_cluster_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("wallet_clusters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Overlap of traded (market, outcome) pairs.
    shared_market_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jaccard_similarity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Fraction of shared entries that landed within the timing window.
    timing_correlation: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    size_correlation: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    coordinated_exit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    cluster: Mapped[WalletCluster] = relationship(back_populates="members")

    __table_args__ = (
        UniqueConstraint("cluster_id", "wallet_id", name="uq_cluster_member"),
    )

