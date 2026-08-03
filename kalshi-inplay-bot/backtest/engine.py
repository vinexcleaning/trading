"""
engine.py - offline replay engine for Kalshi tennis markets.

Strictly causal: a decision made at candle i may only read candles <= i, and
any resulting trade executes at candle i+1's opening quote. Nothing in here
touches the network or the exchange.

Execution model (per the operator's spec):
  * signal detection uses the bid/ask MIDPOINT (continuous, no gaps)
  * execution uses the REAL ask to buy and the REAL bid to sell, plus
    `extra_slip` cents of additional adverse slippage on each side
  * fees are taker on both sides: ceil(0.07 * C * P * (1-P)) dollars
  * if a candle's low hits the stop and its high hits the target, the STOP
    is always assumed to have hit first
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

NOTIONAL = 6.0          # dollars per trade
MAX_SPREAD = 15         # cents; wider than this was never actually tradeable
FLAT_WINDOW = 30        # minutes of no activity that marks a market dormant


# ---------------------------------------------------------------- data prep
def load(series: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    markets = pd.read_parquet(os.path.join(DATA, "markets.parquet"))
    candles = pd.read_parquet(os.path.join(DATA, "candles.parquet"))
    if series:
        markets = markets[markets.tournament.isin(series)]
        candles = candles[candles.ticker.isin(set(markets.ticker))]
    return markets, candles


def prepare(candles: pd.DataFrame) -> pd.DataFrame:
    """Clean quotes, derive mid/spread, and mark which candles are live.

    Two hygiene rules from the operator:
      3. drop any candle whose spread exceeds 15c - untradeable, phantom signal
      5. suppress leading pre-match candles and post-delay restarts, so the
         first real tick after a dormant stretch is not read as a structural
         event when it is just play resuming
    """
    df = candles.copy()

    # A quote persists until it changes; a missing close means "no update".
    df = df.sort_values(["ticker", "ts"]).reset_index(drop=True)
    for c in ("bid_close", "ask_close"):
        df[c] = df.groupby("ticker")[c].ffill()

    df["spread"] = df.ask_close - df.bid_close
    df["mid"] = (df.ask_close + df.bid_close) / 2.0

    valid = (
        df.bid_close.notna() & df.ask_close.notna()
        & (df.bid_close > 0) & (df.ask_close > 0)
        & (df.ask_close <= 100) & (df.spread >= 0)
    )
    df = df[valid].reset_index(drop=True)

    df["tradeable"] = df.spread <= MAX_SPREAD

    g = df.groupby("ticker")
    # Activity over the trailing FLAT_WINDOW minutes. A candle only counts as
    # live if something actually happened recently: some volume AND some
    # price movement. This is what kills the pre-match flat line.
    df["vol_roll"] = g.volume.transform(
        lambda s: s.rolling(FLAT_WINDOW, min_periods=1).sum())
    df["mid_std"] = g.mid.transform(
        lambda s: s.rolling(FLAT_WINDOW, min_periods=1).std().fillna(0.0))
    # Cumulative volume so we can drop everything before the first real trade.
    df["cum_vol"] = g.volume.cumsum()

    df["live"] = (
        df.tradeable
        & (df.cum_vol > 0)                 # market has traded at least once
        & (df.vol_roll > 0)                # something traded in last 30 min
        & (df.mid_std > 0)                 # price actually moved in last 30 min
    )
    return df


# ------------------------------------------------------------------- fees
def fee(contracts: float, price_cents: float) -> float:
    """Kalshi taker fee, in dollars, rounded UP to the next cent.

    The round(.., 9) is not cosmetic: 0.07*100*0.5*0.5*100 evaluates to
    175.00000000000003 in binary floating point, and a naive ceil() would
    charge a spurious extra cent on exactly-representable fee amounts.
    """
    p = price_cents / 100.0
    return math.ceil(round(0.07 * contracts * p * (1.0 - p) * 100.0, 9)) / 100.0


# ------------------------------------------------------------------ trades
@dataclass
class Trade:
    ticker: str
    event: str
    tournament: str
    entry_ts: int
    exit_ts: int
    entry: float            # cents actually paid, incl. slippage
    exit: float             # cents actually received, incl. slippage
    contracts: float
    spread: float           # spread in cents at entry
    reason: str
    gross: float = 0.0      # dollars
    fees: float = 0.0
    net: float = 0.0

    def settle(self) -> "Trade":
        self.gross = (self.exit - self.entry) / 100.0 * self.contracts
        self.fees = fee(self.contracts, self.entry) + fee(self.contracts, self.exit)
        self.net = self.gross - self.fees
        return self


@dataclass
class MarketView:
    """Per-market numpy arrays. Indexing is by candle position, and every
    lookup in the strategies is bounds-checked against `n`."""
    ticker: str
    event: str
    tournament: str
    settlement: float
    ts: np.ndarray
    mid: np.ndarray
    bid_close: np.ndarray
    ask_close: np.ndarray
    bid_high: np.ndarray
    bid_low: np.ndarray
    spread: np.ndarray
    live: np.ndarray
    range5: np.ndarray = field(default=None)      # trailing 5-min mid range
    n: int = field(init=False)

    def __post_init__(self):
        self.n = len(self.ts)
        if self.range5 is None:
            self.range5 = _rolling_range(self.mid, 5)


def build_views(df: pd.DataFrame, markets: pd.DataFrame) -> list[MarketView]:
    meta = markets.set_index("ticker")[
        ["event_ticker", "tournament", "settlement"]].to_dict("index")
    views = []
    for tk, sub in df.groupby("ticker", sort=False):
        m = meta.get(tk)
        if m is None or len(sub) < 20:
            continue
        bh = sub.bid_high.fillna(sub.bid_close).to_numpy(float)
        bl = sub.bid_low.fillna(sub.bid_close).to_numpy(float)
        views.append(MarketView(
            ticker=tk, event=m["event_ticker"], tournament=m["tournament"],
            settlement=m["settlement"] * 100.0,
            ts=sub.ts.to_numpy(np.int64),
            mid=sub.mid.to_numpy(float),
            bid_close=sub.bid_close.to_numpy(float),
            ask_close=sub.ask_close.to_numpy(float),
            bid_high=bh, bid_low=bl,
            spread=sub.spread.to_numpy(float),
            live=sub.live.to_numpy(bool),
        ))
    return views


# -------------------------------------------------------------- primitives
def _rolling_range(a: np.ndarray, w: int) -> np.ndarray:
    """Trailing max-min over w samples, expanding at the head. Causal."""
    s = pd.Series(a)
    return (s.rolling(w, min_periods=1).max()
            - s.rolling(w, min_periods=1).min()).to_numpy()


def deltas(v: MarketView, window: int) -> np.ndarray:
    """mid[i] - mid[i-window], NaN where undefined. Vectorised and causal."""
    d = np.full(v.n, np.nan)
    if v.n > window:
        d[window:] = v.mid[window:] - v.mid[:-window]
    return d


def structural(v: MarketView, i: int, window: int, thresh: float) -> int:
    """Direction of a structural event ending at candle i, else 0.

    Reads mid[i] and mid[i-window] only - never past i.
    """
    if i - window < 0:
        return 0
    d = v.mid[i] - v.mid[i - window]
    if d >= thresh:
        return 1
    if d <= -thresh:
        return -1
    return 0


def range_5m(v: MarketView, i: int) -> float:
    lo = max(0, i - 4)
    seg = v.mid[lo:i + 1]
    return float(seg.max() - seg.min())


def _enter(v: MarketView, j: int, slip: float) -> tuple[float, float] | None:
    """Buy at candle j's ask. Returns (price_paid, spread) or None."""
    if j >= v.n or not v.live[j]:
        return None
    px = v.ask_close[j] + slip
    if not (1 <= px <= 99):
        return None
    return px, v.spread[j]


def _walk(v: MarketView, start: int, entry: float, contracts: float,
          target: float | None, stop: float | None, slip: float,
          time_limit: int | None, structural_stop: tuple[int, float] | None,
          scale_out: bool = False) -> Trade | None:
    """Walk forward from the candle AFTER entry, applying the exit ladder.

    We bought at candle `start`'s closing ask, so that candle's own high and
    low already happened - scanning them would be look-ahead. Evaluation
    begins at start+1.

    Stop-before-target on same-candle ambiguity, always.
    """
    live = contracts            # contracts still open
    realized = 0.0              # dollars banked from a scaled-out half
    fees_paid = fee(contracts, entry)     # entry fee, on the full position
    stop_now = stop
    tgt = target
    half_done = False
    down_since = None

    def close(i: int, px: float, reason: str, settled: bool = False) -> Trade:
        px = max(1.0, min(99.0, px)) if not settled else px
        gross = (px - entry) / 100.0 * live + realized
        fees = fees_paid + (0.0 if settled else fee(live, px))
        t = Trade(v.ticker, v.event, v.tournament, int(v.ts[start]),
                  int(v.ts[i]), entry, px, contracts, 0.0, reason)
        t.gross, t.fees, t.net = gross, fees, gross - fees
        return t

    for i in range(start + 1, v.n):
        # --- stop first, always (ties resolve against us by construction) ---
        if stop_now is not None and v.bid_low[i] <= stop_now:
            return close(i, stop_now - slip,
                         "stop" if not half_done else "stop_after_scale")

        # --- structural stop: adverse event not reversed within 3 minutes ---
        if structural_stop is not None:
            win, thr = structural_stop
            if structural(v, i, win, thr) == -1 and down_since is None:
                down_since = i
            if down_since is not None and i - down_since >= 3:
                k = down_since - win
                ref = v.mid[k] if k >= 0 else v.mid[down_since]
                if v.mid[i] < ref:
                    return close(i, v.bid_close[i] - slip, "structural_stop")
                down_since = None

        # --- scale-out: bank half at +15c, remainder rides at breakeven ---
        if scale_out and not half_done and tgt is not None and v.bid_high[i] >= tgt:
            px = max(1.0, tgt - slip)
            half = live / 2.0
            realized += (px - entry) / 100.0 * half
            fees_paid += fee(half, px)
            live -= half
            half_done = True
            stop_now = entry        # breakeven stop on the remainder
            tgt = 95.0              # remainder targets 95c
            continue

        # --- target ---
        if tgt is not None and v.bid_high[i] >= tgt:
            return close(i, tgt - slip,
                         "target" if not half_done else "target_final")

        # --- time stop ---
        if time_limit is not None and (i - start) >= time_limit:
            return close(i, v.bid_close[i] - slip, "time")

    # ran out of candles -> settle at the market's actual outcome (no fee)
    return close(v.n - 1, v.settlement, "settlement", settled=True)
