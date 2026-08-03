"""Raw and normalized wallet activity.

Two layers on purpose: ``raw_activity`` preserves the exact API payload for
reproducibility and schema-drift forensics, while ``normalized_transactions``
holds the typed, deduplicated rows the analytics pipeline consumes.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db import UtcDateTime, Base, Money, Price, Qty
from ..enums import ActivityType, MarketPhase, TradeSide


class RawActivity(Base):
    """Verbatim API payload, stored once per (wallet, dedupe key).

    ``dedupe_key`` makes ingestion idempotent: re-running a sync over the same
    window inserts nothing new. A single transaction hash can legitimately
    contain several fills, so the key includes asset, side, size and price.
    """

    __tablename__ = "raw_activity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(120), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(200), nullable=False)

    transaction_hash: Mapped[str | None] = mapped_column(String(80), index=True)
    activity_timestamp: Mapped[int | None] = mapped_column(Integer, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)

    ingested_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    ingestion_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_jobs.id", ondelete="SET NULL")
    )

    __table_args__ = (
        UniqueConstraint("wallet_id", "dedupe_key", name="uq_raw_activity_dedupe"),
        Index("ix_raw_activity_wallet_ts", "wallet_id", "activity_timestamp"),
    )


class NormalizedTransaction(Base):
    """One typed wallet action against one outcome token."""

    __tablename__ = "normalized_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_activity.id", ondelete="SET NULL")
    )

    market_id: Mapped[int | None] = mapped_column(
        ForeignKey("markets.id", ondelete="SET NULL"), index=True
    )
    outcome_id: Mapped[int | None] = mapped_column(
        ForeignKey("outcomes.id", ondelete="SET NULL"), index=True
    )
    # Kept denormalized so transactions survive markets we have not yet synced.
    condition_id: Mapped[str | None] = mapped_column(String(80), index=True)
    token_id: Mapped[str | None] = mapped_column(String(90), index=True)
    outcome_index: Mapped[int | None] = mapped_column(Integer)

    activity_type: Mapped[str] = mapped_column(
        String(20), default=ActivityType.TRADE, nullable=False, index=True
    )
    side: Mapped[str | None] = mapped_column(String(6))

    # Shares transacted. Signed quantity is derived at reconstruction time.
    size: Mapped[Decimal] = mapped_column(Qty, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Price)
    usdc_size: Mapped[Decimal | None] = mapped_column(Money)
    fee_usdc: Mapped[Decimal | None] = mapped_column(Money)

    timestamp: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    transaction_hash: Mapped[str | None] = mapped_column(String(80), index=True)

    # Phase at execution time, resolved against the market's game_start_time.
    market_phase: Mapped[str] = mapped_column(
        String(15), default=MarketPhase.UNKNOWN, nullable=False
    )
    # Seconds before match start (negative once live). Null when unknown.
    seconds_to_start: Mapped[int | None] = mapped_column(Integer)

    is_tennis: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    # True when this row has been folded into a reconstructed position, so
    # re-running reconstruction cannot double-count it.
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "wallet_id", "transaction_hash", "token_id", "side", "size", "price",
            name="uq_normalized_tx",
        ),
        Index("ix_norm_tx_wallet_time", "wallet_id", "timestamp"),
        Index("ix_norm_tx_tennis_time", "is_tennis", "timestamp"),
        Index("ix_norm_tx_token_time", "token_id", "timestamp"),
        Index("ix_norm_tx_unprocessed", "wallet_id", "processed", "timestamp"),
    )

    @property
    def signed_size(self) -> Decimal:
        """Positive when shares are acquired, negative when disposed."""
        if self.activity_type == ActivityType.TRADE:
            return self.size if self.side == TradeSide.BUY else -self.size
        if self.activity_type in (ActivityType.REDEEM, ActivityType.MERGE):
            return -self.size
        if self.activity_type == ActivityType.SPLIT:
            return self.size
        return Decimal("0")

