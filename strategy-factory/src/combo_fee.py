"""WHAT A COMBO'S FEE REALLY SAVES - and where it stops saving anything.

Mailbox 013 section 2 reports a fee saving that reaches 8.09 cents on a
six-leg parlay of 70-cent games and calls it *"the first structural advantage
this project has found that is real, is in his favour, and nobody here knew
about."* The direction is right. **The size is not, for two separate reasons,
and at two legs the sign is wrong as well.**

REASON ONE - THE LEGS WERE CHARGED THE WRONG RATE.

The table charges 0.07 on the legs. **Baseball per-game families are HALF fee**
- `KXMLBGAME` and `KXMLBTOTAL` both return `fee_multiplier 0.5` from the live
API, which is the fact this folder corrected on 2026-09-02 and which mailbox
012 restated correctly. **Combos are NOT half fee**: every `KXMVE*` series
returns `fee_multiplier 1`. So a baseball parlay pays FULL fee while its own
legs pay HALF, and charging the legs full fee doubles the number the combo is
being compared against.

REASON TWO - THE TWO SIDES ARE NOT THE SAME BET.

"Fee buying legs" adds up the fee on six separate 70-cent contracts. That
position risks 420 cents and can pay 600. The combo risks 11.76 cents and can
pay 100. Comparing the fee on 11.76 cents of risk with the fee on 420 cents of
risk is not a comparison of two ways to do one thing.

**The like-for-like version is a ROLL**: stake the combo's price on the first
leg, put everything it returns on the second, and so on. That has exactly the
combo's payoff - 100 cents if every leg lands, nothing otherwise - so its fee
is the honest thing to put beside the combo's.

    (it is a BENCHMARK, not an alternative he could take: the games are
    simultaneous, so nothing can actually be rolled from one into the next.
    That is itself the real argument for combos - they are the only way to
    hold this position at all - but it is a different argument from fees.)

AND THE THIRD FRAMING, WHICH IS THE ONE HE WILL ACTUALLY FEEL:
**fee as a share of the money put at risk.** A combo is cheap per contract
because it is cheap per contract - but a dollar buys a great many of them.

    py -3 strategy-factory/src/combo_fee.py
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common.kalshi_fees import fee_rate_cents  # noqa: E402

# Both read from the live /series endpoint on 2026-09-15, not assumed:
#   KXMVESPORTSMULTIGAMEEXTENDED  fee_multiplier 1    -> 0.07
#   KXMVECROSSCATEGORY            fee_multiplier 1    -> 0.07
#   KXMLBGAME, KXMLBTOTAL         fee_multiplier 0.5  -> 0.035
COMBO = Decimal("0.07")
HALF = Decimal("0.035")
FULL = Decimal("0.07")


def combo_price(each_c, n):
    return (each_c / 100.0) ** n * 100.0


def roll_fee(each_c, n, leg_rate):
    """Fee of the only position with the combo's exact payoff."""
    p = each_c / 100.0
    return sum(float(fee_rate_cents(each_c, leg_rate)) * p ** k
               for k in range(n))


def block(title, leg_rate):
    print("\n" + title)
    print("%-6s %-7s %-9s %-10s %-11s %-11s %s"
          % ("legs", "each", "combo", "combo fee", "rolled fee", "difference",
             "who is cheaper"))
    for n in (2, 3, 4, 6, 8):
        for each in (50, 60, 70, 80, 90):
            c = combo_price(each, n)
            if c < 0.1:
                continue
            fc = float(fee_rate_cents(c, COMBO))
            fr = roll_fee(each, n, leg_rate)
            print("%-6d %-7d %-9.2fc %-10.3fc %-11.3fc %+-11.3fc %s"
                  % (n, each, c, fc, fr, fc - fr,
                     "the legs" if fc > fr else "the combo"))
        print()


def main():
    print("=" * 74)
    print("THE FEE ON A COMBO AGAINST THE FEE ON THE SAME BET BUILT FROM LEGS")
    print("=" * 74)
    block("BASEBALL LEGS - half fee (0.035), combo full fee (0.07)", HALF)
    block("FULL-FEE LEGS - tennis, football, mixed (0.07 both sides)", FULL)

    print("=" * 74)
    print("WHERE THE TWO-LEG ADVANTAGE DISAPPEARS, ON BASEBALL LEGS")
    print("=" * 74)
    prev = None
    for tenth in range(300, 951):
        each = tenth / 10.0
        fc = float(fee_rate_cents(combo_price(each, 2), COMBO))
        fr = roll_fee(each, 2, HALF)
        now = fc > fr
        if prev is not None and now != prev:
            print("  crossover at legs priced about %.1fc: below that the "
                  "combo is cheaper, above it the LEGS are" % each)
        prev = now

    print("\n" + "=" * 74)
    print("FEE AS A SHARE OF THE MONEY PUT AT RISK")
    print("=" * 74)
    print("%-6s %-7s %-9s %-12s %s"
          % ("legs", "each", "combo", "fee/contract", "fee per $1 staked"))
    for n, each in ((1, 70), (2, 70), (3, 70), (4, 70), (6, 70), (6, 80),
                    (6, 90)):
        c = combo_price(each, n)
        f = float(fee_rate_cents(c, COMBO if n > 1 else HALF))
        print("%-6d %-7d %-9.2fc %-12.3fc %.2f%%" % (n, each, c, f, 100 * f / c))
    print("\n  A single baseball leg at 70c pays 1.05%% of what is staked.")
    print("  A six-leg parlay of the same games pays 6.18%% - about SIX TIMES")
    print("  as much for every dollar risked. Both numbers are true; they")
    print("  answer different questions, and neither one alone is the answer.")


if __name__ == "__main__":
    main()
