# Depth and fill realism — live tennis order books

> ## ⚠ RETRACTED MEDIANS — this is a 65-minute window at market open
>
> **LEDGER S013.** The window below is 06:58–08:04 UTC, i.e. the first hour of
> the trading day. Depth at the touch builds through the session, so every
> median on this page is measured at its daily minimum. Re-measured over the
> **full day** (64,898 snapshots, 06:58–18:15):
>
> | Statistic | Stated here | Full day | Status |
> |---|---|---|---|
> | Median size at the touch | **106 contracts** | **564** | **RETRACTED (S013)** |
> | ATP spread / depth | 3¢ / 30 lots | **1.0¢ / 312 lots** | **RETRACTED (S012)** |
>
> **The reading below is unaffected in direction — it gets stronger.** The
> conclusion "the touch is not thin, so the maker result is limited by adverse
> selection rather than by depth" holds *a fortiori* at 564. What must not be
> reused is any **number** on this page, and in particular the ATP-is-thinnest
> claim, which reversed: ATP is not the thinnest book, and the tier contrast
> this window appeared to show is largely an artefact of when it was sampled.
>
> Anything that cites these medians as evidence of tier variation is citing a
> retracted fact — see `PREREGISTRATION_PARTB.md`, which used them to justify
> lifting the Phase 3 gate.

- snapshots: **6,344**, markets: **121**
- window: 06:58:08 to 08:03:56 UTC on 2026-08-01 — **65 minutes, at the open**
- empty books: 4

**Scope limit:** these are markets open today; the backtest is on markets settled
25 May – 1 Aug. This calibrates the *size distribution*, which is a structural
property, not a replay of historical fills.

## Depth at the touch, by series

| series | snapshots | median spread ¢ | median size at best bid | p10 size | p90 size |
|---|---|---|---|---|---|
| KXATPCHALLENGERMATCH | 432 | 1.0 | 1,822 | 420 | 3,303 |
| KXATPMATCH | 1,857 | 3.0 | 30 | 1 | 1,007 |
| KXITFMATCH | 1,537 | 2.0 | 367 | 4 | 1,834 |
| KXITFWMATCH | 1,449 | 2.0 | 400 | 5 | 2,460 |
| KXWTAMATCH | 1,060 | 2.0 | 265 | 2 | 1,787 |

## What this does to the Task 1b fill rates

Task 1b requires the book to trade **through** a resting price, which implies the
whole queue at that level cleared. That is already the pessimistic assumption for
**one** contract. At size S the order also has to be small relative to what
clears, so the relevant statistic is the size resting at the touch.

| order size (contracts) | snapshots where touch size >= order | share |
|---|---|---|
| 1 | 6,024 | 95.1% |
| 10 | 4,231 | 66.8% |
| 50 | 3,747 | 59.1% |
| 100 | 3,256 | 51.4% |
| 250 | 2,409 | 38.0% |
| 500 | 1,515 | 23.9% |
| 1,000 | 864 | 13.6% |

Median size at the touch: **106 contracts**. p10 1, p90 1,185.

**Reading.** The touch is not thin. A median of 106 contracts resting means
the 1-contract assumption in Task 1b is not the binding limitation at retail size;
an order of 100 contracts sits inside the touch in 51% of snapshots. So the maker
result does **not** get rescued or destroyed by size at these levels — it stays where
it is, at −0.205 ¢/opportunity, limited by adverse selection rather than by depth.

That is worth stating plainly because it closes a hypothesis: *'the maker line only
fails because the fill model is unrealistic'* is **false**. The fill model is
optimistic about queue position, but depth at the touch is ample, and the loss is
driven by which fills arrive, not how many.