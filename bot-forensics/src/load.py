"""
load.py - shared loaders for the live-account records in kalshi-inplay-bot/.

Nothing here writes. Every function returns a DataFrame.

The authoritative record of what happened is _fills.json (what actually
executed, with the fee Kalshi actually charged) plus _settlements.json /
_settle.json (what the leftover contracts resolved to). _trades.json and
_18h.json are the BOT'S OWN reconstructions and are treated as claims to be
checked, not as evidence.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

import pandas as pd

BOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                   "kalshi-inplay-bot")
BOT = os.path.abspath(BOT)


def _j(name):
    with open(os.path.join(BOT, name), "r", encoding="utf-8") as f:
        return json.load(f)


def _ts(s):
    """Kalshi ISO timestamps -> tz-aware UTC datetime."""
    if s is None:
        return pd.NaT
    return pd.to_datetime(s, utc=True, format="ISO8601")


# ----------------------------------------------------------------------
# tier / event parsing
# ----------------------------------------------------------------------

TIER_PREFIX = [
    ("KXATPCHALLENGERMATCH", "Challenger"),
    ("KXWTACHALLENGERMATCH", "Challenger"),
    ("KXATPMATCH", "ATP"),
    ("KXWTAMATCH", "WTA"),
    ("KXITFWMATCH", "ITF-W"),
    ("KXITFMATCH", "ITF-M"),
]


def tier_of(ticker: str) -> str:
    """Tier from the series prefix. PREFIX, never substring - T017 in LEDGER.md
    is a retraction caused by matching 'WTA' inside 'KXLOWTAUS'."""
    if not isinstance(ticker, str):
        return "OTHER"
    for pre, name in TIER_PREFIX:
        if ticker.startswith(pre):
            return name
    return "OTHER"


def is_tennis(ticker: str) -> bool:
    return tier_of(ticker) != "OTHER"


def event_of(ticker: str) -> str:
    """KXITFWMATCH-26JUL28SAGLEV-LEV -> KXITFWMATCH-26JUL28SAGLEV.

    One event = one match = one independent observation. The two mirrored
    markets (-SAG and -LEV) are the same match and must never be counted twice.
    """
    if not isinstance(ticker, str):
        return ticker
    parts = ticker.rsplit("-", 1)
    return parts[0] if len(parts) == 2 else ticker


def match_date_of(ticker: str):
    """The date embedded in the event ticker, e.g. 26JUL28 -> 2026-07-28."""
    m = re.search(r"-(\d{2})([A-Z]{3})(\d{2})", str(ticker))
    if not m:
        return None
    yy, mon, dd = m.groups()
    months = dict(JAN=1, FEB=2, MAR=3, APR=4, MAY=5, JUN=6,
                  JUL=7, AUG=8, SEP=9, OCT=10, NOV=11, DEC=12)
    if mon not in months:
        return None
    return datetime(2000 + int(yy), months[mon], int(dd)).date()


# ----------------------------------------------------------------------
# the records
# ----------------------------------------------------------------------

def fills() -> pd.DataFrame:
    """Every execution on the account that the API still returned.

    Sign convention, in CONTRACTS OF THE YES SIDE OF THIS TICKER:
      action=buy,  side=yes  -> +qty at yes_price
      action=sell, side=yes  -> -qty at yes_price
      action=buy,  side=no   -> buying NO. Economically this is short YES, but
                                on Kalshi it is a separate long position in the
                                NO market of the same event. Kept as its own
                                row with side='no' so nothing is netted across
                                sides by accident.
    """
    df = pd.DataFrame(_j("_fills.json"))
    df["t"] = _ts(df["created_time"])
    df["qty"] = df["count_fp"].astype(float)
    df["yes_px"] = df["yes_price_dollars"].astype(float)
    df["no_px"] = df["no_price_dollars"].astype(float)
    df["fee"] = df["fee_cost"].astype(float)
    # price paid/received per contract of the side actually traded
    df["px"] = df.apply(lambda r: r["yes_px"] if r["side"] == "yes" else r["no_px"], axis=1)
    df["signed"] = df.apply(lambda r: r["qty"] if r["action"] == "buy" else -r["qty"], axis=1)
    df["cash"] = -df["signed"] * df["px"] - df["fee"]   # cash flow to the account
    df["event"] = df["ticker"].map(event_of)
    df["tier"] = df["ticker"].map(tier_of)
    df["match_date"] = df["ticker"].map(match_date_of)
    df["key"] = df["ticker"] + "|" + df["side"]
    return df.sort_values("t").reset_index(drop=True)


def orders() -> pd.DataFrame:
    df = pd.DataFrame(_j("_orders.json"))
    df["t"] = _ts(df["created_time"])
    df["last_t"] = _ts(df["last_update_time"])
    df["initial"] = df["initial_count_fp"].astype(float)
    df["filled"] = df["fill_count_fp"].astype(float)
    df["remaining"] = df["remaining_count_fp"].astype(float)
    df["yes_px"] = df["yes_price_dollars"].astype(float)
    df["no_px"] = df["no_price_dollars"].astype(float)
    df["px"] = df.apply(lambda r: r["yes_px"] if r["side"] == "yes" else r["no_px"], axis=1)
    df["event"] = df["ticker"].map(event_of)
    df["tier"] = df["ticker"].map(tier_of)
    df["match_date"] = df["ticker"].map(match_date_of)
    return df.sort_values("t").reset_index(drop=True)


def settlements() -> pd.DataFrame:
    """_settlements.json and _settle.json are two pulls of the same endpoint at
    different times. Union them and dedupe on ticker."""
    rows = []
    for name in ("_settlements.json", "_settle.json"):
        try:
            for r in _j(name):
                r = dict(r)
                r["_src"] = name
                rows.append(r)
        except FileNotFoundError:
            pass
    df = pd.DataFrame(rows)
    df["t"] = _ts(df["settled_time"])
    df["yes_ct"] = df["yes_count_fp"].astype(float)
    df["no_ct"] = df["no_count_fp"].astype(float)
    df["yes_cost"] = df["yes_total_cost_dollars"].astype(float)
    df["no_cost"] = df["no_total_cost_dollars"].astype(float)
    df["fee"] = df["fee_cost"].astype(float)
    df["revenue"] = df["revenue"].astype(float)
    df["value"] = df["value"].astype(float)          # 100 if yes won, 0 if no
    df["event"] = df["ticker"].map(event_of)
    df["tier"] = df["ticker"].map(tier_of)
    df = df.sort_values("t").drop_duplicates(subset=["ticker"], keep="last")
    return df.reset_index(drop=True)


def outcomes() -> dict:
    """ticker -> 'yes'/'no'. Union of the two outcome caches."""
    out = {}
    for name in ("_outcomes.json", "_traded_outcomes.json"):
        try:
            out.update(_j(name))
        except FileNotFoundError:
            pass
    return out


def bot_trades() -> pd.DataFrame:
    """_trades.json - the BOT'S OWN trade log. A claim, not evidence."""
    df = pd.DataFrame(_j("_trades.json"))
    df["ts"] = _ts(df["t"])
    df["event"] = df["tk"].map(event_of)
    df["tier"] = df["tk"].map(tier_of)
    return df.sort_values("ts").reset_index(drop=True)


def log_18h() -> pd.DataFrame:
    df = pd.DataFrame(_j("_18h.json"))
    df["ts"] = _ts(df["t"])
    df["event"] = df["tk"].map(event_of)
    df["tier"] = df["tk"].map(tier_of)
    return df.sort_values("ts").reset_index(drop=True)
