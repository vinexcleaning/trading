"""Shared, paced, read-only Kalshi public API client.

Public unauthenticated endpoints only. No order placement. No credentials.

Field-name policy (GUARDS.md #12): Kalshi's legacy integer-cent fields
(`yes_bid`, `yes_ask`, `last_price`, `volume`, `open_interest`, `liquidity`)
now return None on every market. Verified 2026-08-02: 0 of 200 markets had any
of them non-null. Everything here reads the `*_dollars` / `*_fp` names and
converts explicitly. Any recorder that reads the old names writes nulls.
"""
import time

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "market-selection-research/1.0"}

# C018: 15 req/s sustained is fine unauthenticated; 25 r/s gives 56% rejection.
# We run far below that -- this is a research crawl, not a trading loop.
PACE = 0.12

_last = [0.0]


def _throttle():
    dt = time.time() - _last[0]
    if dt < PACE:
        time.sleep(PACE - dt)
    _last[0] = time.time()


def get(path, params=None, tries=5, timeout=30):
    """GET with pacing and exponential backoff on 429/5xx."""
    url = BASE + path if path.startswith("/") else path
    r = None
    for i in range(tries):
        _throttle()
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
        except requests.RequestException:
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2.0 * (i + 1))
            continue
        return r
    return r


def paginate(path, params, key, max_pages=10_000, sleep=0.0):
    """Follow Kalshi's cursor pagination, yielding items."""
    params = dict(params or {})
    seen_cursors = set()
    for _ in range(max_pages):
        r = get(path, params)
        if r is None or r.status_code != 200:
            return
        d = r.json()
        items = d.get(key) or []
        for it in items:
            yield it
        cur = d.get("cursor")
        if not cur or cur in seen_cursors or not items:
            return
        seen_cursors.add(cur)
        params["cursor"] = cur
        if sleep:
            time.sleep(sleep)


def f(v):
    """Parse a Kalshi *_dollars / *_fp string to float. None-safe."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def cents(v):
    """*_dollars string -> cents float."""
    x = f(v)
    return None if x is None else x * 100.0


def series_of(ticker):
    """KXBTCD-26AUG02-B1200 -> KXBTCD. Kalshi tickers are SERIES-EVENT-STRIKE."""
    return ticker.split("-")[0] if ticker else ""


def orderbook(ticker, depth=20):
    """Full L2 book, PUBLIC and UNAUTHENTICATED.

    THE KEY NAME IS THE WHOLE STORY. The response carries exactly one
    top-level key, `orderbook_fp`, holding `yes_dollars` / `no_dollars`.
    There is no `orderbook` key and no `yes` / `no` key -- code reading those
    gets an empty book from a 200 response on every market, liquid or not.
    That is how one prior session concluded depth was not public, and this
    session's first probe reproduced the same error on 85 markets.

    Levels are [price_dollars, size_contracts] as strings, ASCENDING in price,
    max 20 a side. Both sides are quoted as BIDS: `yes_dollars` are bids to buy
    YES, `no_dollars` are bids to buy NO. A YES ask is therefore
    1 - (best no bid). Returns (yes_levels, no_levels) as [(price_c, size)].
    """
    r = get(f"/markets/{ticker}/orderbook", {"depth": depth})
    if r is None or r.status_code != 200:
        return None, None
    ob = (r.json() or {}).get("orderbook_fp") or {}
    def conv(rows):
        out = []
        for row in rows or []:
            try:
                out.append((float(row[0]) * 100.0, float(row[1])))
            except (TypeError, ValueError, IndexError):
                continue
        return out
    return conv(ob.get("yes_dollars")), conv(ob.get("no_dollars"))


def touch(yes_levels, no_levels):
    """(yes_bid_c, yes_ask_c, bid_size, ask_size) from the two bid ladders.

    Levels arrive ascending, so the best bid is the LAST element.
    GUARDS #7 / kalshi-mid-price-trap: buying YES lifts the ask, which is
    1 - best NO bid. Never price at the mid.
    """
    yb = yes_levels[-1] if yes_levels else None
    nb = no_levels[-1] if no_levels else None
    yes_bid = yb[0] if yb else None
    yes_ask = (100.0 - nb[0]) if nb else None
    return yes_bid, yes_ask, (yb[1] if yb else None), (nb[1] if nb else None)
