"""Kalshi's public read-only API, plus the four field traps in this repo's log.

READ ONLY BY CONSTRUCTION. There is no signing code, no key loading, and no
POST anywhere in this module or anywhere in mlb-paper. The order endpoint is
not imported, not wrapped and not reachable.

Traps, each of which has already produced a wrong number somewhere here:

  C024  `volume`, `yes_bid`, `yes_ask`, `last_price`, `open_interest` are
        None on every live market. The live fields are `volume_fp`,
        `yes_bid_dollars`, `yes_ask_dollars`, `open_interest_fp`. Reading the
        old names returns None and sums silently to ZERO.
  new   `/orderbook` returns its data under `orderbook_fp` with keys
        `yes_dollars` / `no_dollars`, not `orderbook.yes`. Same failure mode.
        The touch sizes are on the market object anyway
        (`yes_bid_size_fp` / `yes_ask_size_fp`), so /orderbook is not needed.
  bot-hunt  `close_time` on a LIVE MLB market is the game start plus exactly
        72 hours. On a SETTLED market Kalshi rewrites it to the true
        settlement instant. Anchoring a live market on close_time anchors 69
        hours after first pitch. Start is derived from the TICKER here.
  bot-hunt  the Athletics broke a club-name join once ("A's" -> "a s", under a
        length-4 floor). The code map below is exact and complete for 30 clubs
        with the known aliases; an unmappable code is reported, never guessed.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BASE = "https://api.elections.kalshi.com/trade-api/v2"
ET = ZoneInfo("America/New_York")
UA = {"User-Agent": "trading-research/1.0 (personal research)"}

# KXMLBTOTAL-26AUG072145TBSEA-9  ->  date 26AUG07, hhmm 2145, blob TBSEA
TICK = re.compile(
    r"^(?P<series>KX[A-Z0-9]+?)-(?P<yy>\d{2})(?P<mon>[A-Z]{3})(?P<dd>\d{2})"
    r"(?P<hhmm>\d{4})(?P<blob>[A-Z]+)(?:-(?P<suffix>.+))?$")
MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}

CODE = {
    "ARI": "Arizona Diamondbacks", "ATL": "Atlanta Braves",
    "BAL": "Baltimore Orioles", "BOS": "Boston Red Sox",
    "CHC": "Chicago Cubs", "CWS": "Chicago White Sox",
    "CHW": "Chicago White Sox", "CIN": "Cincinnati Reds",
    "CLE": "Cleveland Guardians", "COL": "Colorado Rockies",
    "DET": "Detroit Tigers", "HOU": "Houston Astros",
    "KC": "Kansas City Royals", "KCR": "Kansas City Royals",
    "LAA": "Los Angeles Angels", "LAD": "Los Angeles Dodgers",
    "MIA": "Miami Marlins", "AZ": "Arizona Diamondbacks", "MIL": "Milwaukee Brewers",
    "MIN": "Minnesota Twins", "NYM": "New York Mets",
    "NYY": "New York Yankees", "OAK": "Athletics", "ATH": "Athletics",
    "PHI": "Philadelphia Phillies", "PIT": "Pittsburgh Pirates",
    "SD": "San Diego Padres", "SDP": "San Diego Padres",
    "SF": "San Francisco Giants", "SFG": "San Francisco Giants",
    "SEA": "Seattle Mariners", "STL": "St. Louis Cardinals",
    "TB": "Tampa Bay Rays", "TBR": "Tampa Bay Rays",
    "TEX": "Texas Rangers", "TOR": "Toronto Blue Jays",
    "WSH": "Washington Nationals", "WAS": "Washington Nationals",
}
# Longest first so SEA is not eaten by SE and CWS not by CW.
CODES_BY_LEN = sorted(CODE, key=len, reverse=True)


def get(path, tries=4, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
    url = f"{BASE}{path}" + (f"?{q}" if q else "")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < tries - 1:
                time.sleep(2 ** i)
                continue
            raise
        except Exception:
            if i < tries - 1:
                time.sleep(2 ** i)
                continue
            raise


def markets(series, status="open"):
    out, cur = [], None
    while True:
        d = get("/markets", series_ticker=series, status=status,
                limit=1000, cursor=cur)
        out += d.get("markets", [])
        cur = d.get("cursor")
        if not cur:
            break
        time.sleep(0.25)
    return out


def cents(v):
    """A `*_dollars` decimal string -> integer cents. None stays None."""
    if v is None:
        return None
    try:
        return int(round(float(v) * 100))
    except (TypeError, ValueError):
        return None


def size(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def split_codes(blob):
    """'TBSEA' -> ('TB','SEA'). Kalshi lists AWAY first, then HOME."""
    for a in CODES_BY_LEN:
        if blob.startswith(a):
            b = blob[len(a):]
            if b in CODE:
                return a, b
    return None, None


def ticker_parts(ticker):
    """Parse a Kalshi MLB ticker. Start time comes from HERE, not close_time."""
    m = TICK.match(ticker)
    if not m:
        return None
    d = m.groupdict()
    mon = MONTHS.get(d["mon"].upper())
    if not mon:
        return None
    away, home = split_codes(d["blob"])
    if not away:
        return None
    hh, mm = int(d["hhmm"][:2]), int(d["hhmm"][2:])
    try:
        # The time in the ticker is US EASTERN, not UTC. Reading it as UTC put
        # every game 4 hours early and made the Pinnacle join reject 100% of
        # candidates as "wrong day of the series". Verified two ways: TB@SEA
        # ticker 26AUG07-2145 against Pinnacle's startTime 2026-08-08T01:45Z
        # (exactly 240 min), and `close_time` on every live market equals the
        # ET-converted start plus exactly 72 h.
        local = datetime(2000 + int(d["yy"]), mon, int(d["dd"]), hh, mm,
                         tzinfo=ET)
        starts = local.astimezone(timezone.utc)
    except ValueError:
        return None
    return {
        "series": d["series"], "away": away, "home": home,
        "starts": starts, "suffix": d["suffix"],
        "event_key": f"{d['series']}-{d['yy']}{d['mon']}{d['dd']}"
                     f"{d['hhmm']}{d['blob']}",
        "game_key": f"{starts.date().isoformat()}:{away}@{home}",
    }


def touch(m):
    """(bid, ask, bid_size, ask_size) in cents/contracts, or None."""
    b, a = cents(m.get("yes_bid_dollars")), cents(m.get("yes_ask_dollars"))
    if not b or not a:
        return None
    return b, a, size(m.get("yes_bid_size_fp")), size(m.get("yes_ask_size_fp"))


if __name__ == "__main__":
    mk = markets("KXMLBGAME")
    ok = bad = 0
    for m in mk:
        p = ticker_parts(m["ticker"])
        if p:
            ok += 1
        else:
            bad += 1
            print("UNPARSED", m["ticker"])
    print(f"KXMLBGAME parsed {ok}, unparsed {bad}")
    for m in mk[:3]:
        p = ticker_parts(m["ticker"])
        print(p["game_key"], p["starts"], "close_time =", m.get("close_time"),
              "<- note the 72h offset", "touch =", touch(m))
