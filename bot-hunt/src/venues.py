"""Shared, paced, READ-ONLY public clients for Kalshi and Polymarket.

Public unauthenticated endpoints only. No order placement, no credentials, no
authenticated path exists in this module by construction.

Everything here is inherited from `market-selection/src/kalshi_api.py` and
`poly_depth.py` rather than rewritten, because both encode traps that cost
prior sessions real time:

  * Kalshi's legacy integer-cent fields (`yes_bid`, `yes_ask`, `last_price`,
    `volume`, `open_interest`) return **None on every market**. Read the
    `*_dollars` / `*_fp` names. GUARDS #12.
  * The orderbook response has exactly one top-level key, **`orderbook_fp`**.
    Code reading `orderbook` / `yes` / `no` gets an empty book from a 200 on
    every market, liquid or not. Two sessions concluded "depth is not public"
    from this.
  * Both Kalshi sides are quoted as BIDS. A YES ask is `1 - best NO bid`.
  * Kalshi list endpoints null out bid/ask; quotes only come off the
    per-market orderbook endpoint. (Independently reported by a Reddit
    cross-venue bot author, and consistent with the field-name policy above.)
"""
from __future__ import annotations

import time

import requests

KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
CLOB = "https://clob.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
UA = {"User-Agent": "bot-hunt-research/1.0"}

# C018: 15 req/s sustained is fine unauthenticated; 25 r/s => 56% rejection.
# This is a research crawl, not a trading loop, so it runs far below that.
PACE = 0.12
_last = {"t": 0.0}


def _throttle(pace: float = PACE) -> None:
    dt = time.time() - _last["t"]
    if dt < pace:
        time.sleep(pace - dt)
    _last["t"] = time.time()


def get(url: str, params=None, tries: int = 5, timeout: int = 30, pace: float = PACE):
    r = None
    for i in range(tries):
        _throttle(pace)
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


# ---------------------------------------------------------------- Kalshi ----

def k_get(path: str, params=None, **kw):
    return get(KALSHI + path, params, **kw)


def k_paginate(path: str, params, key: str, max_pages: int = 10_000):
    params = dict(params or {})
    seen = set()
    for _ in range(max_pages):
        r = k_get(path, params)
        if r is None or r.status_code != 200:
            return
        d = r.json()
        items = d.get(key) or []
        yield from items
        cur = d.get("cursor")
        if not cur or cur in seen or not items:
            return
        seen.add(cur)
        params["cursor"] = cur


def fnum(v, default=None):
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def series_of(ticker: str) -> str:
    return ticker.split("-")[0] if ticker else ""


def k_orderbook(ticker: str, depth: int = 20):
    """Returns (yes_bid_levels, no_bid_levels) as [(price_cents, size)] or
    (None, None) on a non-200. Levels arrive ASCENDING; best bid is last."""
    r = k_get(f"/markets/{ticker}/orderbook", {"depth": depth})
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


def k_touch(yes_levels, no_levels):
    """(yes_bid_c, yes_ask_c, bid_size, ask_size). Never price at the mid —
    buying YES lifts the ask, which is 100 - best NO bid. GUARDS #7."""
    yb = yes_levels[-1] if yes_levels else None
    nb = no_levels[-1] if no_levels else None
    return (yb[0] if yb else None,
            (100.0 - nb[0]) if nb else None,
            yb[1] if yb else None,
            nb[1] if nb else None)


def k_depth_within(levels, best, cents_band: float, side: str) -> float:
    """Total size within `cents_band` of the touch on one bid ladder."""
    if best is None:
        return 0.0
    lo = best - cents_band if side == "yes" else best - cents_band
    return sum(sz for p, sz in levels if p >= lo)


# ------------------------------------------------------------ Polymarket ----

def p_book(token_id: str):
    r = get(CLOB + "/book", {"token_id": token_id}, pace=0.25)
    if r is None or r.status_code != 200:
        return None
    return r.json() or {}


def p_touch(bk):
    """(bid_c, ask_c, bid_size, ask_size, n_bid_levels, n_ask_levels).

    Polymarket quotes real bids and asks (unlike Kalshi's two bid ladders), so
    the ask is the ask. Prices are dollars in [0,1]; sizes are contracts.
    """
    if not bk:
        return (None,) * 6
    bids, asks = bk.get("bids") or [], bk.get("asks") or []
    bb = max((float(x["price"]) for x in bids), default=None)
    ba = min((float(x["price"]) for x in asks), default=None)
    bsz = sum(float(x["size"]) for x in bids if bb is not None
              and float(x["price"]) == bb)
    asz = sum(float(x["size"]) for x in asks if ba is not None
              and float(x["price"]) == ba)
    return (None if bb is None else bb * 100.0,
            None if ba is None else ba * 100.0,
            bsz, asz, len(bids), len(asks))


def p_depth_5c(bk):
    if not bk:
        return 0.0
    bids, asks = bk.get("bids") or [], bk.get("asks") or []
    bb = max((float(x["price"]) for x in bids), default=None)
    ba = min((float(x["price"]) for x in asks), default=None)
    d = 0.0
    if bb is not None:
        d += sum(float(x["size"]) for x in bids if float(x["price"]) >= bb - 0.05)
    if ba is not None:
        d += sum(float(x["size"]) for x in asks if float(x["price"]) <= ba + 0.05)
    return d


def p_gamma(path: str, params=None):
    return get(GAMMA + path, params, pace=0.25)
