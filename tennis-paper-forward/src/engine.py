"""engine.py — paper execution. No orders, no venue, no money.

EXECUTION REALISM, and the one decision that matters most
    Every fill in this repo's archive that turned out to be fake was fake for
    the same reason: it happened at a price nobody could get. Marked at the
    mid, a tennis strategy returned +14.4% to +24.6%; at executable fills the
    same trades returned -24.3% to -30.9%. GUARDS #7.

    So: BUY LIFTS THE ASK. SELL HITS THE BID. There is no mid in this engine.
    `Quote.mid` exists and is named `mid_DIAGNOSTIC_ONLY` in the brief so that
    using it by accident is impossible.

LATENCY IS MODELLED BY DEFERRING THE FILL A WHOLE TICK, not by a random draw
    A backtest adds 50-150 ms of synthetic latency because it has a tape at
    millisecond resolution. A forward test polling every ~60 s does not, and a
    synthetic draw here would be theatre. Instead: a decision made on tick t
    fills at the ask observed on tick t+1. That is strictly more conservative
    than any millisecond model, it is real rather than simulated, and the
    difference between the two prices is recorded as `slippage_cents` so the
    cost of the delay is measured rather than assumed.

    The finding this defends against is quoted in this repo's own notes:
    "without latency, most strategies are profitable."

DEPTH IS CHECKED BEFORE ENTRY
    `yes_ask_size_fp` is top-of-book size. An order larger than it is cut down
    to it, and the shortfall is recorded. A fill that consumes size the book
    never showed is the second way this archive has produced fake profits.

FEES COME FROM common/kalshi_fees.py AND ARE NOT REIMPLEMENTED HERE
    GUARDS #6/#6b. The formula existed seventeen times in this repo before a
    failing test stopped the eighteenth. There is no fee arithmetic in this
    file - only calls.

    There is NO separate settlement fee. Holding to settlement pays the entry
    fee only; an early exit pays entry + exit. Getting that wrong doubles the
    cost bar on every hold-to-settle strategy, which is three of our thirteen.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.kalshi_fees import (  # noqa: E402
    TAKER_RATE, fee_order_cents, fee_rate_cents,
)

from .kalshi_read import MatchView  # noqa: E402

DEFAULT_SIZE = 10          # fallback only; every bot chooses its own size
MAX_DEPTH_FRACTION = 0.25  # never take more than a quarter of the shown size

# SIZE IS CHOSEN PER TRADE BY EACH BOT, IN src/sizing.py, AND THE RISK IS REAL.
# The live bot in this repo sized by dollars: qty = int(stake / price). A fixed
# dollar stake buys MORE contracts as the price falls, so re-entering a falling
# market martingales automatically. Nobody designed that; it was an emergent
# property of the sizing rule, and it cost -$7.56 on one match in 50 minutes
# across legs of 12, 20 and 32 contracts.
#
# Confidence-based sizing has the same divide-by-price inside it. Three guards
# stand between this engine and that sequence, and all three are enforced here
# or in sizing.py: a re-entry may not exceed the FIRST entry's contract count
# (`Ledger.first_entry_contracts`), total open exposure may not exceed the
# bankroll (`Ledger.open_exposure_cents`), and there is a hard per-trade
# ceiling. The 12 -> 20 -> 32 sequence is refused by the first guard alone.


@dataclass
class Fill:
    ts: str
    kind: str                 # "entry" | "exit" | "settle"
    ticker: str
    event_ticker: str
    price_cents: int
    qty: int
    fee_cents: float
    decided_at: str
    decided_price_cents: int | None
    slippage_cents: int | None
    depth_shown: float | None
    depth_shortfall: int
    note: str = ""


@dataclass
class Position:
    bot: str
    event_ticker: str
    ticker: str
    player: str
    qty: int
    entry_price: int
    entry_fee_cents: float
    entry_ts: str
    decision_id: str
    open: bool = True
    exit_price: int | None = None
    exit_fee_cents: float = 0.0
    exit_ts: str | None = None
    exit_kind: str | None = None       # "traded" | "settled" | "voided"
    settled_value: int | None = None   # 100 or 0
    pnl_cents: float | None = None

    def mark_exit_traded(self, price: int, ts: str) -> None:
        self.exit_price = price
        self.exit_fee_cents = float(fee_order_cents(price, self.qty, TAKER_RATE))
        self.exit_ts = ts
        self.exit_kind = "traded"
        self.open = False
        gross = (price - self.entry_price) * self.qty
        self.pnl_cents = gross - self.entry_fee_cents - self.exit_fee_cents

    def mark_settled(self, won: bool, ts: str) -> None:
        self.settled_value = 100 if won else 0
        self.exit_price = self.settled_value
        self.exit_fee_cents = 0.0          # no separate settlement fee
        self.exit_ts = ts
        self.exit_kind = "settled"
        self.open = False
        gross = (self.settled_value - self.entry_price) * self.qty
        self.pnl_cents = gross - self.entry_fee_cents

    def mark_voided(self, ts: str, note: str = "") -> None:
        """The market closed without a settlement we could read.

        Recorded as its own state. A void is not a loss and not a win, and
        folding it into either would be a silent selection effect.
        """
        self.exit_ts = ts
        self.exit_kind = "voided"
        self.open = False
        self.pnl_cents = None


@dataclass
class PendingOrder:
    """A decision waiting for the next tick. This is the latency model."""
    bot: str
    event_ticker: str
    ticker: str
    player: str
    side: str                  # "buy" | "sell"
    qty: int
    decided_at: str
    decided_price: int | None
    decision_id: str
    max_price: int | None = None    # refuse the fill if the market ran away
    min_price: int | None = None


@dataclass
class Ledger:
    bot: str
    fills: list[Fill] = field(default_factory=list)
    positions: list[Position] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)

    def open_position(self, event_ticker: str) -> Position | None:
        for p in self.positions:
            if p.open and p.event_ticker == event_ticker:
                return p
        return None

    def entries_for(self, event_ticker: str) -> int:
        return sum(1 for p in self.positions if p.event_ticker == event_ticker)

    def first_entry_contracts(self, event_ticker: str) -> int | None:
        """Size of the FIRST entry on this event, or None if there is none.

        This is the anti-martingale reference. A re-entry is capped at it, so a
        falling price cannot mechanically buy more contracts for the same
        stake. See sizing.py for why that is the single most dangerous line in
        this design.
        """
        for p in self.positions:
            if p.event_ticker == event_ticker:
                return p.qty
        return None

    def open_exposure_cents(self) -> int:
        """Cash committed to open positions, at what was actually paid."""
        return int(sum(p.qty * p.entry_price + p.entry_fee_cents
                       for p in self.positions if p.open))

    def realised_cents(self) -> float:
        return sum(p.pnl_cents for p in self.positions
                   if p.pnl_cents is not None)

    def closed(self) -> list[Position]:
        return [p for p in self.positions if not p.open and p.pnl_cents is not None]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PaperEngine:
    """Holds one ledger per bot and executes pending orders on the next tick."""

    def __init__(self, bot_names: list[str], size: int = DEFAULT_SIZE):
        self.size = size
        self.ledgers: dict[str, Ledger] = {b: Ledger(bot=b) for b in bot_names}
        self.pending: list[PendingOrder] = []

    # -- queueing ----------------------------------------------------------

    def queue_buy(self, bot: str, mv: MatchView, side_ticker: str, player: str,
                  decision_id: str, qty: int | None = None,
                  max_price: int | None = None) -> None:
        q = mv.primary if mv.primary.ticker == side_ticker else mv.mirror
        self.pending.append(PendingOrder(
            bot=bot, event_ticker=mv.event_ticker, ticker=side_ticker,
            player=player, side="buy", qty=qty or self.size,
            decided_at=_now(), decided_price=(q.yes_ask if q else None),
            decision_id=decision_id, max_price=max_price,
        ))

    def queue_sell(self, bot: str, pos: Position, mv: MatchView,
                   decision_id: str, min_price: int | None = None) -> None:
        q = mv.primary if mv.primary.ticker == pos.ticker else mv.mirror
        self.pending.append(PendingOrder(
            bot=bot, event_ticker=pos.event_ticker, ticker=pos.ticker,
            player=pos.player, side="sell", qty=pos.qty,
            decided_at=_now(), decided_price=(q.yes_bid if q else None),
            decision_id=decision_id, min_price=min_price,
        ))

    # -- execution ---------------------------------------------------------

    def execute_pending(self, pool: dict[str, MatchView]) -> int:
        """Fill everything queued on the previous tick against THIS tick's book."""
        done = 0
        still: list[PendingOrder] = []
        for o in self.pending:
            mv = pool.get(o.event_ticker)
            if mv is None:
                self._reject(o, "event no longer in the pool at fill time")
                continue
            q = mv.primary if mv.primary.ticker == o.ticker else mv.mirror
            if q is None or not q.is_quotable():
                self._reject(o, "no two-sided quote at fill time")
                continue
            if o.side == "buy":
                done += int(self._fill_buy(o, q))
            else:
                done += int(self._fill_sell(o, q))
        self.pending = still
        return done

    def _reject(self, o: PendingOrder, why: str) -> None:
        self.ledgers[o.bot].rejected.append(
            {"ts": _now(), "decision_id": o.decision_id, "side": o.side,
             "ticker": o.ticker, "reason": why,
             "decided_price": o.decided_price}
        )

    def _fill_buy(self, o: PendingOrder, q) -> bool:
        lg = self.ledgers[o.bot]
        if lg.open_position(o.event_ticker) is not None:
            self._reject(o, "already holding this event")
            return False
        px = q.yes_ask
        if o.max_price is not None and px > o.max_price:
            self._reject(o, f"ask ran to {px}c past the {o.max_price}c limit")
            return False
        shown = q.yes_ask_size or 0.0
        cap = int(shown * MAX_DEPTH_FRACTION)
        qty = min(o.qty, cap) if cap > 0 else 0
        if qty <= 0:
            self._reject(o, f"insufficient shown depth ({shown}) at {px}c")
            return False
        fee = float(fee_order_cents(px, qty, TAKER_RATE))
        pos = Position(
            bot=o.bot, event_ticker=o.event_ticker, ticker=o.ticker,
            player=o.player, qty=qty, entry_price=px, entry_fee_cents=fee,
            entry_ts=_now(), decision_id=o.decision_id,
        )
        lg.positions.append(pos)
        lg.fills.append(Fill(
            ts=pos.entry_ts, kind="entry", ticker=o.ticker,
            event_ticker=o.event_ticker, price_cents=px, qty=qty,
            fee_cents=fee, decided_at=o.decided_at,
            decided_price_cents=o.decided_price,
            slippage_cents=(px - o.decided_price) if o.decided_price is not None else None,
            depth_shown=shown, depth_shortfall=max(0, o.qty - qty),
        ))
        return True

    def _fill_sell(self, o: PendingOrder, q) -> bool:
        lg = self.ledgers[o.bot]
        pos = lg.open_position(o.event_ticker)
        if pos is None:
            self._reject(o, "no open position at fill time")
            return False
        px = q.yes_bid
        if o.min_price is not None and px < o.min_price:
            self._reject(o, f"bid fell to {px}c below the {o.min_price}c limit")
            return False
        shown = q.yes_bid_size or 0.0
        if shown < pos.qty:
            # A partial exit would leave a stub position and a second fee. The
            # honest paper equivalent is to refuse and try again next tick;
            # the refusal is recorded so the analysis can count how often
            # wanting out was not the same as getting out.
            self._reject(o, f"bid depth {shown} below position size {pos.qty}")
            return False
        before = pos.exit_price
        pos.mark_exit_traded(px, _now())
        lg.fills.append(Fill(
            ts=pos.exit_ts, kind="exit", ticker=o.ticker,
            event_ticker=o.event_ticker, price_cents=px, qty=pos.qty,
            fee_cents=pos.exit_fee_cents, decided_at=o.decided_at,
            decided_price_cents=o.decided_price,
            slippage_cents=(o.decided_price - px) if o.decided_price is not None else None,
            depth_shown=shown, depth_shortfall=0,
            note="" if before is None else "re-exit",
        ))
        return True

    # -- settlement --------------------------------------------------------

    def settle(self, event_ticker: str, winning_ticker: str | None,
               *, voided: bool = False) -> int:
        n = 0
        ts = _now()
        for lg in self.ledgers.values():
            pos = lg.open_position(event_ticker)
            if pos is None:
                continue
            if voided or winning_ticker is None:
                pos.mark_voided(ts, "settlement not readable")
            else:
                pos.mark_settled(pos.ticker == winning_ticker, ts)
                lg.fills.append(Fill(
                    ts=ts, kind="settle", ticker=pos.ticker,
                    event_ticker=event_ticker,
                    price_cents=pos.settled_value or 0, qty=pos.qty,
                    fee_cents=0.0, decided_at=ts, decided_price_cents=None,
                    slippage_cents=None, depth_shown=None, depth_shortfall=0,
                    note="no separate settlement fee",
                ))
            n += 1
        return n

    # -- serialisation -----------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        return {
            "ts": _now(),
            "size": self.size,
            "ledgers": {
                b: {
                    "positions": [asdict(p) for p in lg.positions],
                    "fills": [asdict(f) for f in lg.fills],
                    "rejected": lg.rejected,
                }
                for b, lg in self.ledgers.items()
            },
        }

    def load(self, snap: dict[str, Any]) -> None:
        for b, d in (snap.get("ledgers") or {}).items():
            if b not in self.ledgers:
                self.ledgers[b] = Ledger(bot=b)
            lg = self.ledgers[b]
            lg.positions = [Position(**p) for p in d.get("positions", [])]
            lg.fills = [Fill(**f) for f in d.get("fills", [])]
            lg.rejected = list(d.get("rejected", []))


def round_trip_cost_cents(price_cents: int, spread_cents: int) -> float:
    """What a bot must beat to break even, at this price and this spread.

    Entry fee + exit fee + the spread paid on the way in. Reported next to
    every decision so an entry can be judged against its own cost bar rather
    than against a repo-wide average. The archive's tennis cost bar was 3.61pp
    and every measured edge was smaller than it.
    """
    entry = float(fee_rate_cents(price_cents, TAKER_RATE))
    exit_ = float(fee_rate_cents(price_cents, TAKER_RATE))
    return entry + exit_ + float(spread_cents)


def hold_cost_cents(price_cents: int, spread_cents: int) -> float:
    """Cost bar for a hold-to-settle position: entry fee + spread only."""
    return float(fee_rate_cents(price_cents, TAKER_RATE)) + float(spread_cents)
