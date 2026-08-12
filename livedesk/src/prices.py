"""Kalshi's public read API. GET only, no key, no signing, nothing to place.

VERIFIED ALIVE 2026-08-12 02:50 UTC against
`GET /trade-api/v2/markets/KXMLBGAME-26AUG121840PITMIA-MIA`, which answered
200 with a live bid and ask. This mattered: the screenshot that started this
build showed a `410 Gone` from the OLD order-placing endpoint on
`external-api.kalshi.com`, and that error was from an early build of the
tennis app, not evidence that reading prices is dead.

TRAP C024, and it is the whole reason this file exists rather than a one-line
fetch: on a live market `yes_bid`, `yes_ask`, `volume` and `last_price` are
all **None**. The live fields are `yes_bid_dollars`, `yes_ask_dollars`,
`volume_fp`. Reading the old names returns None and sums silently to ZERO --
three scripts in this repo were reporting zeros that way as recently as last
week. Nothing here reads the old names.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "trading-research/1.0 (personal research)"}
TIMEOUT = 20


@dataclass(frozen=True)
class Quote:
    ticker: str
    status: str
    bid_c: Optional[int]
    ask_c: Optional[int]
    ask_size: float
    result: str                  # '', 'yes' or 'no' once the game is final

    @property
    def is_final(self) -> bool:
        return self.status in ("settled", "finalized") and self.result in ("yes", "no")

    @property
    def tradeable(self) -> bool:
        return self.status in ("active", "open") and bool(self.ask_c)


def _get(path: str, tries: int = 3) -> dict:
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(f"{BASE}{path}", headers=UA)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError,
                json.JSONDecodeError) as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"Kalshi read failed after {tries} tries: {last}")


def _cents(v) -> Optional[int]:
    """A dollar string like '0.5200' to 52. None stays None -- a missing price
    must never become a zero, because a zero looks like a free contract."""
    if v is None or v == "":
        return None
    try:
        return int(round(float(v) * 100))
    except (TypeError, ValueError):
        return None


def _fp(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def quote(ticker: str) -> Quote:
    m = _get(f"/markets/{ticker}").get("market", {})
    return Quote(
        ticker=ticker,
        status=(m.get("status") or "").lower(),
        bid_c=_cents(m.get("yes_bid_dollars")),
        ask_c=_cents(m.get("yes_ask_dollars")),
        ask_size=_fp(m.get("yes_ask_size_fp")),
        result=(m.get("result") or "").lower(),
    )


def market_url(event_ticker: str) -> str:
    """The page he lands on when he clicks the button.

    Verified in a real browser 2026-08-12: `.../kxmlbgame/mlb-game` redirects
    to this shape, and `kxmlbgame-26aug121840pitmia` loaded the Pittsburgh at
    Miami page. Lower case matters.
    """
    return ("https://kalshi.com/markets/kxmlbgame/professional-baseball-game/"
            + event_ticker.lower())
