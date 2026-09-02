"""What Kalshi actually charges on the series this desk trades.

    py -3 livedesk\\src\\fees.py            # print the rate for each series

READ ONLY, one GET per series per session, then cached.

# WHY THIS EXISTS

**Kalshi charges HALF fee on the baseball game markets this desk trades.**
`fee_multiplier = 0.5` on `KXMLBGAME` and `KXMLBTOTAL`. `money.size_bet()`
called `fee_order_cents()` with no rate, so it used the full taker rate and
every fee, cost and break-even figure it produced was too high.

**Verified here against the live API on 2026-09-02, not taken on trust** —
mailbox 025 asked for exactly that, because this is the rare correction in this
repo that makes something look BETTER, and about 51 before it all shrank an
edge:

    KXMLBGAME    0.5      KXATPMATCH   1
    KXMLBTOTAL   0.5      KXNFLGAME    1

**In money it is pennies** — roughly 3 cents on a $2 stake. That is not the
reason to fix it. `breakeven_out_of_100` is the number on screen telling him
how many wins out of 100 he needs, and it was overstating the bar by about one
win in a hundred. **That is the figure he reasons with.**

# ⚠ THE MULTIPLIER IS READ, NEVER HARDCODED

Writing `0.5` into this repo would be the eighteenth copy of a fee fact that is
supposed to have exactly one home. Kalshi can change a series, and **only 19 of
144 baseball series are half-fee** — the per-game ones. Season-long markets
(`KXMLBWINS-*`, divisions, All-Star) are full fee, so **half-fee implies
baseball but baseball does not imply half-fee.** A rule keyed on the sport
would be wrong.

# ⚠ AND IT FAILS TOWARDS THE FULL RATE

If the series cannot be read, this returns the FULL rate. That overstates the
cost, which is the only safe direction: a bet is never made to look cheaper
than it is by a network error. The desk says on screen when it is guessing.
"""
from __future__ import annotations

import sys
from pathlib import Path

LIVEDESK = Path(__file__).resolve().parent.parent
COMMON = LIVEDESK.parent / "common"
if str(COMMON.parent) not in sys.path:
    sys.path.insert(0, str(COMMON.parent))

from common.kalshi_fees import SeriesFees, TAKER_RATE      # noqa: E402

#: series ticker -> SeriesFees, for this session only. Kalshi can change a
#: series; a process that runs for a day should not cache one for a week.
_CACHE: dict = {}

#: series we asked about and could not read. Kept apart from "not asked yet"
#: so a failure is visible rather than looking like an unvisited series --
#: confusing those two states voided a live position on 2026-08-16.
_FAILED: set = set()

#: Full rate, used when nothing is known. NEVER a guessed multiplier.
FULL = SeriesFees("<unknown>", "quadratic_with_maker_fees")


def series_of(ticker: str) -> str:
    """`KXMLBGAME-26AUG221915PITLAD-PIT` -> `KXMLBGAME`."""
    return str(ticker or "").split("-")[0].strip().upper()


def for_series(series: str, client=None):
    """(SeriesFees, known). `known` is False when we had to fall back."""
    series = (series or "").strip().upper()
    if not series:
        return FULL, False
    if series in _CACHE:
        return _CACHE[series], True
    if series in _FAILED:
        return FULL, False
    if client is None:
        return FULL, False
    try:
        obj = (client._get(f"/series/{series}") or {}).get("series") or {}
        fees = SeriesFees.from_api(obj)
    except Exception:
        _FAILED.add(series)
        return FULL, False
    _CACHE[series] = fees
    return fees, True


def for_ticker(ticker: str, client=None):
    """(SeriesFees, known) for the series a market ticker belongs to."""
    return for_series(series_of(ticker), client)


def rate_for(ticker: str, client=None):
    """(taker rate, known). This is what `size_bet` wants."""
    fees, known = for_ticker(ticker, client)
    return fees.taker_rate, known


def note_for(ticker: str, client=None) -> str:
    """One line for the screen. Silent at the full rate — that is the norm and
    a message every time would be noise. It speaks up for a discount, and it
    speaks up when it does not know."""
    fees, known = for_ticker(ticker, client)
    if not known:
        return ("fee rate for this market could not be read -- charging the "
                "FULL rate, so the cost shown may be a little high")
    if fees.fee_multiplier == 1:
        return ""
    return (f"Kalshi charges {float(fees.fee_multiplier):g}x fee on "
            f"{series_of(ticker)}, and that is in the numbers below")


def _reset_for_tests() -> None:
    _CACHE.clear()
    _FAILED.clear()


# ⚠ NO `__main__` BLOCK HERE, AND THAT IS THE PAPER-ONLY CANARY BEING RIGHT.
# The first version ended with a demo that built a `KalshiClient` to show the
# rates. `tests/test_paper_only.py` failed the build: **only `demo_exec.py` may
# construct a client**, and a convenience block in a fee helper is exactly the
# kind of second door that rule exists to keep shut. The CLI now lives in
# `tools/show_fees.py`, which is handed a client rather than making one.
