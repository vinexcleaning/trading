# WHICH COST BAR APPLIES WHERE

**Written 2026-09-01 by the dictator chat, closing `C105`, which had sat open
since 2026-08-14.** The ask was: *"three tennis cost bars are now live — say
which applies where, once, somewhere central."* This is that page.

**Read this before quoting any "clears the cost bar" sentence.**

---

## The finding: they are not three measurements of one thing

They are **three different things sharing a name.** Nothing was measured
wrongly. The bars differ because they answer different questions, and none of
them says so on the label.

| bar | where it is used | what is IN it | sample |
|---|---|---|---|
| **2.40¢** | P2 copy-trading, `copytrade_tests_v2.py:42`, `GO_NO_GO.md`, `MORNING_REPORT.md` | not recorded — described only as "user's measured Kalshi tennis round trip" | not recorded |
| **4.14¢** | P1 backtest, ledger `C004` **SETTLED** | 0.52¢ spread + **2.00¢ modelled slippage** + 1.62¢ fees | 2.94M live candles |
| **4.79¢** | `tennis` chat, measured forward 2026-08-09 | 2.12¢ spread + 2.67¢ fees, **no slippage term at all** | 81 matches |

## The two things that actually separate them

**1. Whether you SELL or HOLD TO SETTLEMENT.** This is the big one and it is
never stated. Kalshi charges a fee on entry, and a second one only if you sell
early. Holding to settlement pays **one** fee. Computed from
`common/kalshi_fees.py` at the full tennis rate (verified live today —
`KXATPMATCH` has `fee_multiplier = 1.0`, so **the half-fee baseball finding
does not touch tennis**):

| price | fee, entry only | fee, entry + exit |
|---|---|---|
| 30¢ | 1.47¢ | 2.94¢ |
| 50¢ | 1.75¢ | **3.50¢** |
| 70¢ | 1.47¢ | 2.94¢ |
| 85¢ | 0.89¢ | 1.79¢ |
| 95¢ | 0.33¢ | 0.67¢ |

> ⚠ **At 50¢ the round-trip fee ALONE is 3.50¢ — more than the entire 2.40¢
> bar, before a penny of spread.** So 2.40¢ cannot be a round-trip number at
> mid prices, whatever its label says. It is only coherent as a
> **hold-to-settlement** bar. Its own fee component was never written down, so
> this is inference from arithmetic, not from its source.

**2. Whether slippage is included, and whether it was measured.** `4.14¢`
carries **2.00¢ of modelled slippage — the single largest component, and it is
an assumption, not a measurement.** `4.79¢` carries none. That one difference
is most of the gap between them.

## What to do with this

- **Never write "clears the cost bar".** Write which bar and what it assumes:
  *"clears 2.40¢, which assumes the position is held to settlement"*.
- **A result that clears 2.40¢ has NOT cleared 4.14¢.** The recorded case:
  the price-matched copy-trading result (+5.09pp) clears 2.40 comfortably and
  4.14 only marginally. The headline `+7.23pp` copy-trading number in
  `MORNING_REPORT.md` is measured against **2.40¢, the weakest-provenance bar
  of the three** — that is the load-bearing use and it is the one to check.
- **If a strategy sells out early, no bar under about 3.5¢ can be right at
  mid prices.** The fee alone eats it.
- **`4.14¢`'s slippage is assumed.** Same class as `SLIPPAGE_C = 1.0` in
  `mlb-paper` (filed as mailbox `mlb/024`). Neither has been measured, and
  `livedesk`'s real fills are the first data able to measure either.

## The reusable lesson

**A cost bar with no stated exit assumption is not a number.** Every bar
quoted anywhere in this repo should carry three things or it should not be
quoted: **held or sold · slippage in or out · what it was measured on.**

This is the same shape as the defect `reopen` recorded separately: *a column
whose meaning changes partway down the table, with one label on it.*

## What this page does NOT settle

- **Which bar is RIGHT.** They measure different things; all three can be
  correct for their own question. Choosing one requires knowing whether the
  strategy sells early, which is a per-strategy fact.
- **Whether 2.40¢'s components were ever recorded anywhere.** They are not in
  any artifact I could find. If someone finds the original working, this table
  should be corrected rather than trusted.
- **Whether the 2.00¢ slippage in 4.14¢ is realistic.** Unmeasured. It is the
  largest single term in that bar.
