# Do the maker-fee tennis series hold the liquidity?

**Measured 2026-08-03.** Answers the question the `signal-github` session left
explicitly open in commit `e3b87d7`: Kalshi charges makers on `KXATPMATCH` and
`KXWTAMATCH` — the tennis series this repo trades — and *"whether those series
also hold most of the liquidity is left explicitly unmeasured rather than
guessed."*

Reproduce: `common/measure_tennis_maker_liquidity.py` (public API, paced).

## Answer: no — but they are ~6× more traded per market

| | Series | Markets | % of count | Volume | % of volume |
|---|---|---|---|---|---|
| **Charges makers** | 2 | 3,864 | **5.8%** | 3,312,057,054 | **34.4%** |
| Taker-only | 40 | 62,830 | 94.2% | 6,320,848,359 | 65.6% |

**Maker-fee series are 5.9× more traded per market than their share of the
count implies.** They are not "most" of the liquidity — but they are far from
the 9% that a market count would suggest.

## By series

| Series | Maker fee? | Markets | % count | Volume | % volume |
|---|---|---|---|---|---|
| `KXATPMATCH` | **YES** | 1,898 | 2.8% | 2,106,536,050 | **21.9%** |
| `KXITFMATCH` | no | 17,434 | 26.1% | 1,907,598,712 | 19.8% |
| `KXITFWMATCH` | no | 15,166 | 22.7% | 1,861,489,028 | 19.3% |
| `KXATPCHALLENGERMATCH` | no | 5,272 | 7.9% | 1,798,219,061 | 18.7% |
| `KXWTAMATCH` | **YES** | 1,966 | 2.9% | 1,205,521,004 | **12.5%** |
| `KXWTACHALLENGERMATCH` | no | 1,324 | 2.0% | 382,387,836 | 4.0% |
| `KXATPSETWINNER` | no | 4,386 | 6.6% | 105,798,370 | 1.1% |
| `KXWTASETWINNER` | no | 3,940 | 5.9% | 70,155,990 | 0.7% |

The five main match series hold **92.2%** of tennis volume. Everything else —
set winner, exact score, game totals and spreads, doubles — is a long tail
carrying under 8% between them, despite being a third of the market count.

## What it means for a maker strategy

- **Two thirds of tennis volume (65.6%) sits where makers pay nothing.** That
  is the favourable reading, and it is the one S010 implies.
- **But the single most liquid series charges.** `KXATPMATCH` alone is 21.9% of
  volume. Any maker strategy concentrating on the deepest book pays the fee.
- **`fee_type` and depth point in opposite directions.** The fee-free series are
  ITF and Challenger — numerous, and collectively liquid, but individually thin.
  The fee-bearing series are few and deep. Choosing on fee alone pushes you
  toward the thinner book.

This does not resurrect the maker case. S008 found all 15 maker configurations
net-negative, S009 found adverse selection already exceeding maker price
improvement, and the `high_sweep` re-run (2026-08-03) left every realistic-fill
row at −1.30 to −2.42¢/contract *after* the maker fee was correctly zeroed on
90.4% of that dataset. Fees were never the binding constraint.

## Confirms and refines S010

S010 says Challenger + ITF are ~91% of the tennis book. **Measured by count:
94.2% taker-only** — S010 is right. **By volume: 65.6%.** Both are true; they
answer different questions, and the count is the one that gets quoted.

## Method notes

**Volume comes from `volume_fp`, not `volume`.** The `/markets` object carries
`volume_fp`, `volume_24h_fp` and `open_interest_fp` — floating-point strings.
Reading the old `volume` name returns `None` and sums silently to **zero**,
which is what the first run of this script did across all 42 series. That is
the renamed-field trap in LEDGER C024 and the `*_dollars`/`*_fp` note in
STATUS.md. The script now **raises** if `volume_fp` is absent and **aborts** if
the total is zero, so a schema change cannot masquerade as a finding.

**Series selection is by ticker prefix, not substring.** A substring filter on
`ATP|WTA|ITF` pulls in twelve non-tennis series, because `KXNEWTAYLOR`
("Taylor Swift album"), `KXNEWTARIFFS`, `WTAX` ("Wealth tax") and `KXLOWTAUS`
("Lowest temperature in Austin") all contain `WTA`. **LEDGER T017 is a
retraction caused by exactly this class of hand-written tennis regex**, so the
filter here uses explicit prefixes plus a title check and prints every
exclusion. The headline is robust to the choice: 34.4% either way, because the
false positives are negligible by volume.

**Unit.** `volume_fp` is reported as-is and used only in ratios, so whether it
denominates contracts or dollars does not affect any figure here.
