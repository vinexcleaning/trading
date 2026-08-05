"""
t1d_outcomes.py - resolve the last eight tickers.

Eight markets were traded after the final settlement pull at 2026-07-28
20:08, so they carry no settlement row. Six are closed round trips (bought
and sold the same quantity), so their P&L is fully determined by the fills
and no outcome is needed. Two carry an open residual and do need the result:

    KXITFMATCH-26JUL28OLIVER-VER   10 contracts @ 60c
    KXITFWMATCH-26JUL28SAIPER-SAI   8 contracts @ 74c

Neither is in _settled_all.json. They are pulled from Kalshi's public,
unauthenticated market endpoint - read only, no key, and 28 Jul is inside the
~69-day window. Result cached to out/late_outcomes.json so this never has to
run twice.
"""
from __future__ import annotations
import json, os, sys, time
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
CACHE = os.path.join(OUT, "late_outcomes.json")

TICKERS = [
    "KXITFMATCH-26JUL28OLIVER-VER",
    "KXITFWMATCH-26JUL28SAIPER-SAI",
    "KXITFMATCH-26JUL28DUSFIL-FIL",
    "KXITFMATCH-26JUL28HUELEI-LEI",
    "KXITFMATCH-26JUL28STOBAE-STO",
    "KXITFWMATCH-26JUL28AGUHAR-AGU",
    "KXITFWMATCH-26JUL28KULFRO-FRO",
    "KXWTAMATCH-26JUL27EALZHE-ZHE",
]

BASE = "https://api.elections.kalshi.com/trade-api/v2/markets/"


def fetch(tk):
    req = urllib.request.Request(BASE + tk, headers={"User-Agent": "python-urllib"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


if __name__ == "__main__":
    got = {}
    if os.path.exists(CACHE):
        got = json.load(open(CACHE, encoding="utf-8"))
    for tk in TICKERS:
        if tk in got:
            print(f"{tk:42s} cached  {got[tk]}")
            continue
        try:
            m = fetch(tk).get("market", {})
            got[tk] = {"result": m.get("result"), "status": m.get("status"),
                       "close_time": m.get("close_time"),
                       "last": m.get("last_price_dollars")}
            print(f"{tk:42s} {got[tk]}")
        except Exception as e:
            print(f"{tk:42s} FAILED {type(e).__name__}: {e}")
        time.sleep(0.4)
    json.dump(got, open(CACHE, "w", encoding="utf-8"), indent=1)
    print(f"\nwritten {CACHE}")
