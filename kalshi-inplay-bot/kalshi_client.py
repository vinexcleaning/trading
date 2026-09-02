"""
kalshi_client.py — talks to Kalshi.

╔══════════════════════════════════════════════════════════════════════════╗
║  ⚠  ANYONE EDITING THIS FILE IS EDITING LIVE-MONEY CODE.                 ║
║                                                                          ║
║  This folder has looked dormant since 2026-08-03. It is not. The live    ║
║  desk places REAL ORDERS through this client:                            ║
║                                                                          ║
║      livedesk/src/demo_exec.py:113                                       ║
║          KalshiClient(demo=False, kill_switch=<livedesk's own switch>)   ║
║                                                                          ║
║  `demo=False` is PRODUCTION. A change here reaches his real account      ║
║  without passing through anything in `kalshi-inplay-bot` that looks      ║
║  switched off.                                                           ║
║                                                                          ║
║  ⚠  AND THE KILL SWITCH DOES NOT COVER DEMO. `_order` checks             ║
║      `os.path.exists(switch) and not self.demo`, so `demo=True` bypasses ║
║      the switch by design. That is intentional, and it means order code  ║
║      paths CAN fire today on fake money — and would be live the day the  ║
║      switch comes off.                                                   ║
║                                                                          ║
║  Found by the repo-wide audit, 2026-09-01 (`tennis` mailbox 022).        ║
╚══════════════════════════════════════════════════════════════════════════╝

Handles RSA-PSS request signing, market data, and order placement.
Nothing here decides anything; it just does what it's told.

Setup:
    pip install requests cryptography

    Kalshi -> Settings -> API Keys -> Create Key (read AND write)
    Save the .pem file next to this script.
    Set two environment variables:
        KALSHI_KEY_ID    = the UUID Kalshi shows you
        KALSHI_KEY_PATH  = path to your .pem file
"""

from __future__ import annotations

import base64
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Optional

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

DEMO_BASE = "https://external-api.demo.kalshi.co/trade-api/v2"
PROD_BASE = "https://external-api.kalshi.com/trade-api/v2"

# Every singles-match series Kalshi runs. ITF is where the small overnight
# tournaments live (M15/W75 Bali, Huamantla, etc.) — leaving these out was
# hiding hundreds of markets that the live score feed actually covers.
TENNIS_SERIES = (
    "KXATPMATCH",
    "KXWTAMATCH",
    "KXATPCHALLENGERMATCH",
    "KXITFMATCH",     # ITF men's
    "KXITFWMATCH",    # ITF women's
)

# Per-SET markets ("will X win set 2"). A different market from match-winner,
# so the fact that match-winner is efficiently priced says nothing about
# these. Liquid enough to matter: ~300k volume and 1c spreads when checked.
# Kept separate so the trading bot never touches them by accident — only the
# recorder reads them, until there is evidence worth acting on.
SET_SERIES = (
    "KXATPSETWINNER",
    "KXWTASETWINNER",
)


def _cents(dollar_str) -> int:
    """API now returns prices like '0.8100' — convert to whole cents."""
    try:
        return round(float(dollar_str) * 100)
    except (TypeError, ValueError):
        return 0


def _fp(v) -> float:
    """Fixed-point fields come back as decimal strings ('14.18', '0.00')."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class Market:
    ticker: str
    title: str
    yes_bid: int
    yes_ask: int
    status: str
    volume: int
    last_price: int = 0
    open_interest: int = 0

    @property
    def spread(self) -> int:
        return self.yes_ask - self.yes_bid

    @property
    def is_trading(self) -> bool:
        """Has this market got a real, tradeable quote?"""
        return self.yes_bid > 0 or self.yes_ask > 0 or self.volume > 0 or self.last_price > 0

    @property
    def is_open(self) -> bool:
        """Accepting orders? Careful: you filter the API with status=open,
        but it hands back status='active' for the very same markets. Compare
        against this, never against the literal "open"."""
        return self.status in ("active", "open")


class KalshiClient:
    def __init__(self, demo: bool = True, read_only: bool = False,
                 kill_switch: str | None = None):
        self.base = DEMO_BASE if demo else PROD_BASE
        self.demo = demo
        self.read_only = read_only
        # Which TRADING_DISABLED file governs THIS client. None keeps the
        # tennis bot's own, so nothing about that bot changes. Another project
        # passes its own path so the two switches are independent.
        self.kill_switch = kill_switch
        self.key_id = os.environ.get("KALSHI_KEY_ID", "")
        key_path = os.environ.get("KALSHI_KEY_PATH", "kalshi_private_key.pem")

        self._open_px: dict[str, int] = {}   # ticker -> opening price, cached

        self._key = None
        if self.key_id and os.path.exists(key_path):
            with open(key_path, "rb") as f:
                self._key = serialization.load_pem_private_key(f.read(), password=None)

    @property
    def authenticated(self) -> bool:
        return self._key is not None and bool(self.key_id)

    # ---- signing ----------------------------------------------------
    def _headers(self, method: str, path: str) -> dict[str, str]:
        if not self.authenticated:
            return {"Content-Type": "application/json"}
        ts = str(int(time.time() * 1000))
        msg = f"{ts}{method.upper()}{path}".encode()
        sig = self._key.sign(
            msg,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=hashes.SHA256().digest_size),
            hashes.SHA256(),
        )
        return {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: Optional[dict] = None) -> dict[str, Any]:
        """Reads retry: a brief wifi drop shouldn't look like 'you own nothing'
        to the stop logic. Writes are deliberately NOT retried — resending an
        order you can't confirm is how you buy the same thing twice."""
        url = self.base + path
        full = "/trade-api/v2" + path
        last = None
        for attempt in range(3):
            try:
                r = requests.get(url, headers=self._headers("GET", full),
                                 params=params, timeout=10)
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                last = e
                status = getattr(e.response, "status_code", None)
                # 401 is usually permanent, but Kalshi also throws it
                # transiently — and one of those used to permanently break the
                # balance readout and the stop restore. Retrying a READ is
                # harmless, so give it a couple of goes before believing it.
                retryable = status is None or status >= 500 or status in (401, 429)
                if not retryable:
                    raise
                if attempt < 2:
                    time.sleep(1.0 * (attempt + 1))
        raise last

    def _post(self, path: str, body: dict) -> dict[str, Any]:
        url = self.base + path
        full = "/trade-api/v2" + path
        r = requests.post(url, headers=self._headers("POST", full),
                          json=body, timeout=10)
        self._raise_with_detail(r)
        return r.json()

    def _delete(self, path: str) -> dict[str, Any]:
        url = self.base + path
        full = "/trade-api/v2" + path
        r = requests.delete(url, headers=self._headers("DELETE", full), timeout=10)
        self._raise_with_detail(r)
        return r.json() if r.content else {}

    @staticmethod
    def _raise_with_detail(r: requests.Response) -> None:
        """Kalshi explains rejections in the body — surface it. A bare
        '400 Bad Request' tells you nothing about which field it hated."""
        if r.status_code >= 400:
            detail = ""
            try:
                detail = r.json().get("error", {}).get("message", "") or r.text[:300]
            except ValueError:
                detail = r.text[:300]
            raise requests.HTTPError(
                f"{r.status_code} {r.reason}: {detail}".strip(), response=r)
        r.raise_for_status()

    # ---- reading ----------------------------------------------------
    def balance(self) -> float:
        """Available cash in dollars."""
        data = self._get("/portfolio/balance")
        if "balance_dollars" in data:
            return float(data["balance_dollars"])
        return data.get("balance", 0) / 100

    def set_markets(self) -> list[Market]:
        """Open per-SET markets. Recorder-only: never fed to the trading
        engine, so nothing can accidentally place an order in one."""
        return self._markets_for(SET_SERIES)

    def tennis_markets(self) -> list[Market]:
        """Open tennis markets, most liquid first.

        The five series are fetched CONCURRENTLY. Sequentially this took ~31
        seconds, which was the entire scan budget — the bot was deciding on
        prices half a minute old and could not scan faster than once a minute
        no matter what interval you set. In parallel it is one round trip.
        """
        return self._markets_for(TENNIS_SERIES)

    def _markets_for(self, series_list: tuple) -> list[Market]:
        def fetch(series: str) -> list[dict]:
            try:
                return self._get("/markets", {"series_ticker": series,
                                              "status": "open",
                                              "limit": 200}).get("markets", [])
            except requests.RequestException:
                return []

        out: list[Market] = []
        with ThreadPoolExecutor(max_workers=max(1, len(series_list))) as ex:
            for markets in ex.map(fetch, series_list):
                for m in markets:
                    out.append(Market(
                        ticker=m["ticker"], title=m.get("title", ""),
                        yes_bid=_cents(m.get("yes_bid_dollars")),
                        yes_ask=_cents(m.get("yes_ask_dollars")),
                        status=m.get("status", ""),
                        volume=int(float(m.get("volume_fp", 0) or 0)),
                        last_price=_cents(m.get("last_price_dollars")),
                        open_interest=int(float(m.get("open_interest_fp", 0) or 0)),
                    ))
        return sorted(out, key=lambda m: (-m.volume, -m.open_interest))

    def orderbook(self, ticker: str) -> dict:
        """Authoritative bid/ask for one market."""
        return self._get(f"/markets/{ticker}/orderbook")

    def opening_price(self, ticker: str) -> Optional[int]:
        """The market's first quoted price in cents — i.e. the pre-match
        favourite, straight from Kalshi. Free, no external feed.

        The Apify feed used to supply this from bookmaker odds; Sofascore's
        live endpoint carries no odds, so we read it off the candlestick
        history instead (v3 spec section 6). Above 50c means the market
        opened this player as the favourite.

        Hourly candles over the last 3 days: a tennis market opens a few
        hours before play, so the first candle with a real two-sided quote is
        the opening line. Hourly keeps this to ~72 rows instead of 4,320.

        Cached per ticker — an opening price cannot change once set.
        """
        if ticker in self._open_px:
            return self._open_px[ticker]
        series = ticker.split("-")[0]
        now = int(time.time())
        try:
            d = self._get(
                f"/series/{series}/markets/{ticker}/candlesticks",
                {"start_ts": now - 3 * 86400, "end_ts": now,
                 "period_interval": 60},
            )
        except requests.RequestException:
            return None
        for c in d.get("candlesticks", []):
            bid = (c.get("yes_bid") or {}).get("open_dollars")
            ask = (c.get("yes_ask") or {}).get("open_dollars")
            if bid is None or ask is None:
                continue
            b, a = round(float(bid) * 100), round(float(ask) * 100)
            # The first candle of a market is usually an EMPTY BOOK quoted
            # 0/99, which would average to a fake 50c and make every market
            # look like a coin flip. Require a real two-sided quote before
            # believing it.
            if b <= 0 or a >= 100 or a - b > 15:
                continue
            px = round((b + a) / 2)
            if 0 < px < 100:
                self._open_px[ticker] = px
                return px
        return None

    def positions(self, open_only: bool = True) -> list[dict]:
        """Your positions. Note the API keeps returning markets you've fully
        closed, with position_fp "0.00" — counting those as open is how you
        end up hitting a position limit you aren't actually near. The size
        field is position_fp (a decimal STRING), not position."""
        rows = self._get("/portfolio/positions").get("market_positions", [])
        if not open_only:
            return rows
        return [p for p in rows if _fp(p.get("position_fp")) != 0]

    def resting_orders(self) -> list[dict]:
        return self._get("/portfolio/orders", {"status": "resting"}).get("orders", [])

    def realized_pnl_total(self) -> float:
        """Lifetime realized P&L in dollars, summed over every market you've
        traded. Snapshot this at startup and diff it later to get the P&L for
        one session — the closed rows the API keeps returning are exactly what
        makes that possible."""
        total = 0.0
        for p in self.positions(open_only=False):
            total += _fp(p.get("realized_pnl_dollars"))
        return total

    def get_order(self, order_id: str) -> dict:
        """One order by id, so we can see whether it actually filled."""
        for o in self._get("/portfolio/orders", {"limit": 100}).get("orders", []):
            if o.get("order_id") == order_id:
                return o
        return {}

    # ---- writing ----------------------------------------------------
    # Kalshi retired POST /portfolio/orders (it now answers 410 Gone) in favour
    # of the V2 single-book endpoint. The shape changed in three ways that
    # matter, and getting any of them wrong places a wrong order:
    #   * path   -> /portfolio/events/orders
    #   * side   -> "bid" to BUY yes, "ask" to SELL yes. No more action/side pair.
    #   * price  -> a dollar STRING ("0.7400"), not an int of cents (74).
    # count is a string too. time_in_force must be given explicitly.
    #: Presence of this file in the bot directory blocks ALL order placement.
    #: Created 2026-08-03 when the user decided to stop trading this strategy.
    #: To trade again, delete the file — nothing else needs changing.
    KILL_SWITCH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "TRADING_DISABLED")

    def _check_writable(self) -> None:
        # Checked before read_only, so it cannot be bypassed by constructing
        # the client differently. Fail closed: if the file is there, no order
        # goes out, whatever the caller intended.
        #
        # Exception: demo=True bypasses this check. The tennis bot's kill
        # switch protects production orders only; demo execution uses fake
        # money and must continue working even when the tennis bot is off.
        #
        # ⚠ ONE SWITCH PER BOT, 2026-08-16. `kill_switch` is per INSTANCE and
        # defaults to this file's own TRADING_DISABLED, so the tennis bot's
        # behaviour is unchanged. A different caller passes its own path, and
        # then neither bot can silently disable the other -- which is what was
        # happening: livedesk moved to production and was then blocked by a
        # file that is about the tennis strategy.
        switch = getattr(self, "kill_switch", None) or self.KILL_SWITCH
        if os.path.exists(switch) and not self.demo:
            raise PermissionError(
                "TRADING IS DISABLED. "
                f"Delete {switch} to re-enable order placement. "
                "Turned off 2026-08-03: the strategy's own backtest returns "
                "-9c/trade and no maker configuration clears its cost bar "
                "under a realistic fill model.")
        if self.read_only:
            raise PermissionError("watch mode — this client cannot place orders")

    def _order(self, ticker: str, side: str, count: int, price_cents: int) -> dict:
        self._check_writable()
        if side not in ("bid", "ask"):
            raise ValueError(f"side must be 'bid' (buy yes) or 'ask' (sell yes), got {side!r}")
        if not 1 <= price_cents <= 99:
            raise ValueError(f"price must be 1-99 cents, got {price_cents}")
        if count < 1:
            raise ValueError(f"count must be at least 1, got {count}")
        return self._post("/portfolio/events/orders", {
            "ticker": ticker,
            "side": side,
            "count": f"{count}.00",
            "price": f"{price_cents / 100:.4f}",
            "time_in_force": "good_till_canceled",
            "self_trade_prevention_type": "taker_at_cross",
            "client_order_id": str(uuid.uuid4()),
        })

    def limit_buy(self, ticker: str, count: int, price_cents: int) -> dict:
        """Buy YES at price_cents or better. Rests if it can't fill."""
        return self._order(ticker, "bid", count, price_cents)

    def await_fill(self, order_id: str, timeout_sec: float = 6.0) -> tuple[float, str]:
        """Wait briefly for an order to fill. Returns (filled_count, status).

        Matters because a limit buy at a stale price just rests. Anything
        that depends on owning the contracts — a take-profit sell, a stop —
        must not be set up until this reports a real fill."""
        deadline = time.time() + timeout_sec
        filled, status = 0.0, "unknown"
        while time.time() < deadline:
            o = self.get_order(order_id)
            if o:
                filled = _fp(o.get("fill_count_fp"))
                status = str(o.get("status", "unknown"))
                if filled > 0 or status in ("executed", "canceled"):
                    return filled, status
            time.sleep(0.75)
        return filled, status

    def limit_sell(self, ticker: str, count: int, price_cents: int) -> dict:
        """Rest a sell at price_cents. Fills without you when it gets there."""
        return self._order(ticker, "ask", count, price_cents)

    def cancel(self, order_id: str) -> dict:
        """Cancel a resting order.

        This is a WRITE. It was missing the read-only check, which meant watch
        mode — the mode whose entire promise is "cannot touch your account" —
        would happily cancel real resting orders once the 60-second stale-buy
        rule started firing.
        """
        self._check_writable()
        return self._delete(f"/portfolio/events/orders/{order_id}")
