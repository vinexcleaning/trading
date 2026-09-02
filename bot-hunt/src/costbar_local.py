"""The cost bar these analyses should have been using all along.

⚠ AUDIT PASS 4, ITEM 3, 2026-09-02. `props_n3.py`, `totals_n3.py`,
`totals_family_n3.py` and `retail_n3.py` all set

    bar = fee_rate_cents(ask)

which is **the fee alone** -- no spread, no slippage -- while
`engine.cost_bar_cents` is half-spread + slippage + fee. The audit is right that
this is too permissive.

**In those runs it did no damage, and the reason is worth stating precisely:**
every one of them concluded that nothing qualified, and a permissive bar makes a
null HARDER to reach, not easier. So the conclusions stand.

**But it was more permissive than I realised.** `RESULTS_PROPS_N3.md` reported
four sell-side candidates, one of which cleared by **0.03c**. Against a bar that
included the half-spread it would not have flagged at all -- so the fee-only bar
was generating candidates I then had to argue away one at a time.

WHY HALF THE SPREAD
--------------------
Buying at the ask IS crossing the spread, so a strategy measured against the ASK
has already paid it and adding a full spread would double-count. What the
half-spread measures is the cost relative to the MID -- the right unit for
comparing families, and what an edge quoted against a mid has to beat. This
module therefore takes the side explicitly rather than guessing.

This is deliberately NOT a new fee implementation: the fee comes from
`common/kalshi_fees.py`, the repo's only one, and the Polymarket fee from
`common/costbar.py`. GUARDS #6.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent))
from common.kalshi_fees import fee_rate_cents  # noqa: E402

# Slippage beyond the touch. 0.0 is correct for touch-size trades and is the
# honest default here: every one of these analyses reads only the top of book,
# so it has no evidence about what walking deeper would cost. Anything that
# survives at size must be re-costed with a real number rather than this one.
DEFAULT_SLIPPAGE_C = 0.0


def bar_cents(ask_c: float, bid_c: float | None = None,
              slippage_c: float = DEFAULT_SLIPPAGE_C) -> float:
    """Cost to act, in cents, against a MID-quoted edge.

    fee(ask) + half the quoted spread + slippage. If no bid is available the
    spread term is dropped and the result is the old fee-only bar -- which is
    then reported as such rather than silently passing for a full cost.
    """
    fee = float(fee_rate_cents(ask_c))
    if bid_c is None or ask_c is None or ask_c <= bid_c:
        return fee + slippage_c
    return fee + (ask_c - bid_c) / 2.0 + slippage_c


def describe(ask_c: float, bid_c: float | None = None,
             slippage_c: float = DEFAULT_SLIPPAGE_C) -> str:
    fee = float(fee_rate_cents(ask_c))
    if bid_c is None:
        return f"{fee:.2f}c fee only (no bid recorded)"
    half = (ask_c - bid_c) / 2.0
    return (f"{fee + half + slippage_c:.2f}c = {fee:.2f}c fee "
            f"+ {half:.2f}c half-spread + {slippage_c:.2f}c slippage")
