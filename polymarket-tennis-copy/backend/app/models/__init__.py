"""ORM models.

Importing this package registers every table on ``Base.metadata``, which Alembic
autogenerate and ``create_all`` both rely on.
"""

from __future__ import annotations

from ..db import Base
from .activity import NormalizedTransaction, RawActivity
from .backtest import BacktestRun, BacktestTrade
from .market import Event, Market, Outcome
from .metrics import WalletMetricHistory, WalletMetrics, WalletScore
from .paper import PaperDailyStat, PaperTrade, PaperTradeEvent
from .position import PositionLot, ReconstructedPosition, TradeCopyability
from .price import LiquiditySnapshot, MarketPrice, PriceObservationKind
from .signal import Alert, Signal, SignalWallet
from .system import (
    ApplicationSetting,
    DataQualityReport,
    IngestionJob,
    ManualOverride,
    SchemaDriftEvent,
    SystemError,
)
from .wallet import Wallet, WalletCluster, WalletClusterMember, WalletTag

__all__ = [
    "Base",
    # wallet
    "Wallet",
    "WalletTag",
    "WalletCluster",
    "WalletClusterMember",
    # market
    "Event",
    "Market",
    "Outcome",
    # activity
    "RawActivity",
    "NormalizedTransaction",
    # position
    "ReconstructedPosition",
    "PositionLot",
    "TradeCopyability",
    # price
    "MarketPrice",
    "LiquiditySnapshot",
    "PriceObservationKind",
    # metrics
    "WalletMetrics",
    "WalletMetricHistory",
    "WalletScore",
    # signals
    "Signal",
    "SignalWallet",
    "Alert",
    # paper
    "PaperTrade",
    "PaperTradeEvent",
    "PaperDailyStat",
    # backtest
    "BacktestRun",
    "BacktestTrade",
    # system
    "IngestionJob",
    "SystemError",
    "ManualOverride",
    "ApplicationSetting",
    "DataQualityReport",
    "SchemaDriftEvent",
]
