"""Observed prices and liquidity snapshots.

``market_prices`` stores two very different kinds of observation and keeps them
distinguishable, because conflating them is how a delay analysis ends up with
fake precision:

* ``TRADE_PRINT`` -- an executed trade from data-api ``/trades``. Second-level
  timestamp, genuinely observed, but sparse.
* ``MINUTE_BAR`` -- a point from CLOB ``/prices-history``. Dense but never finer
  than 1-minute fidelity, which is the platform's floor.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
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


class PriceObservationKind:
    """Kind values for :class:`MarketPrice`."""

    TRADE_PRINT = "trade_print"
    MINUTE_BAR = "minute_bar"
    MIDPOINT = "midpoint"
    BEST_BID = "best_bid"
    BEST_ASK = "best_ask"


class MarketPrice(Base):
    """A single price observation for one outcome token."""

    __tablename__ = "market_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_id: Mapped[str] = mapped_column(String(90), nullable=False, index=True)
    market_id: Mapped[int | None] = mapped_column(
        ForeignKey("markets.id", ondelete="CASCADE"), index=True
    )

    timestamp: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)

    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Price, nullable=False)
    # Size only exists for trade prints.
    size: Mapped[Decimal | None] = mapped_column(Qty)
    # Aggressor side of the print, when known.
    side: Mapped[str | None] = mapped_column(String(6))

    source: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Two different wallets can print the same size at the same price and
        # second, so the natural key stays coarse and we tolerate near-dupes
        # rather than dropping real volume.
        Index("ix_price_token_kind_ts", "token_id", "kind", "timestamp"),
        Index("ix_price_token_ts", "token_id", "timestamp"),
    )


class LiquiditySnapshot(Base):
    """Order-book depth at a point in time.

    Depth is what determines whether a follower's stake is even fillable, so we
    store the aggregated ladder rather than only top-of-book.
    """

    __tablename__ = "liquidity_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_id: Mapped[str] = mapped_column(String(90), nullable=False, index=True)
    market_id: Mapped[int | None] = mapped_column(
        ForeignKey("markets.id", ondelete="CASCADE"), index=True
    )

    timestamp: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)

    best_bid: Mapped[Decimal | None] = mapped_column(Price)
    best_ask: Mapped[Decimal | None] = mapped_column(Price)
    midpoint: Mapped[Decimal | None] = mapped_column(Price)
    spread: Mapped[Decimal | None] = mapped_column(Price)

    bid_depth_usdc: Mapped[Decimal | None] = mapped_column(Money)
    ask_depth_usdc: Mapped[Decimal | None] = mapped_column(Money)
    # Notional available within 1c / 5c of touch -- the practically fillable size.
    ask_depth_1c_usdc: Mapped[Decimal | None] = mapped_column(Money)
    ask_depth_5c_usdc: Mapped[Decimal | None] = mapped_column(Money)

    tick_size: Mapped[Decimal | None] = mapped_column(Price)
    # JSON-encoded ladders: [[price, size], ...] truncated to a usable depth.
    bids_json: Mapped[str | None] = mapped_column(Text)
    asks_json: Mapped[str | None] = mapped_column(Text)

    source: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("token_id", "timestamp", name="uq_liquidity_token_ts"),
        Index("ix_liquidity_token_ts", "token_id", "timestamp"),
    )

