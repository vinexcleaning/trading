# Pre-registration — the player-feature study

**Written before any result was computed.** GUARDS #10. Committed before
`t6_features.py` was run for the first time, so that the analysis choices below
cannot have been made after seeing which of them worked.

## The question the user asked

> *"In individual tennis games there's a lot of different stuff that plays into
> a role. Things like the floor, things like how they play in their last few
> games, how they played against this opponent before, how good is their
> serving, how good are their double faulting."*

The premise is right and worth taking seriously: this repo has shown Kalshi
tennis is efficient **in aggregate**, which does not by itself mean every
sub-population is efficient. That is exactly verdict **D** from the forensics —
the one branch that was worth acting on. It was refuted for *one* strategy
family (in-play momentum). It has never been tested for **pre-match player
features**, which is a different question on different information.

## What is actually available, decided before analysis

| feature the user named | available? | why |
|---|---|---|
| recent form (last few games) | **YES** — built from the corpus itself | `markets.parquet` carries `player` for all 14,162 markets |
| head-to-head | **YES**, but thin | same source; only ~29 days of window |
| rest / fatigue | **YES** | days since that player's previous match in-window |
| round (qualifying vs main draw) | **YES** | parseable from `title` |
| tier (ATP/Ch/WTA/ITF-M/ITF-W) | **YES** | `tournament` |
| **surface ("the floor")** | **NO** | Kalshi's market records carry no tournament name, only tier. `livetennisapi` has surface per tournament but there is no join key. **Stated as a gap, not worked around.** |
| **serve %, double faults, aces** | **NO** | the free feed carries scores only, no match statistics. Would need the paid history plan, and possibly not even then |

## The primary test, fixed now

**Target: the calibration residual `outcome − implied`, not the raw win rate.**
GUARDS #1's filter form. A feature that selects strong favourites moves the win
rate legitimately; to be an *edge* it must move the residual.

- **Implied** = the opening mid price of that market, in [0,1].
- **Unit of observation: the event (match), not the market.** Kalshi lists two
  mirrored markets per match. Their residuals are exactly anti-correlated, so
  using both would double n for free and halve the standard error dishonestly.
- **Dedupe by ticker order (alphabetical).** NEVER by volume, open interest or
  last price — that is the S011 bug that voided four phases of work.
- **All features are computed from matches whose `close_ts` is strictly earlier
  than the current match's `open_ts`.** No same-day leakage, no future results.
- **Split: time-ordered 70/30.** Train = first 70% of events by `open_ts`,
  holdout = last 30%. Any feature that survives train must be re-tested on
  holdout, and the holdout number is the one reported.
- **BH-FDR at 5% over the entire family of tests**, counted across every feature
  and every bucket examined — one denominator, per GUARDS #11.
- **A permutation null**: shuffle the outcome within tier and re-run the whole
  pipeline, to confirm the machinery does not manufacture significance.

## The economic bar, fixed now

A statistical residual is not an edge. To be tradeable it must clear
**spread + entry fee + exit fee**, computed per bucket from
`common/kalshi_fees.py`. The prior tennis work put this at **≈3.6–5c per
contract**. A residual of +2pp on a 50c contract is worth 2c and **does not
clear**. This is written down now so that a positive-but-small result cannot
later be described as promising.

## Declared in advance: what would count as a finding

1. A feature whose residual coefficient is significant on **train**, survives
   **BH-FDR**, holds the **same sign and rough magnitude on holdout**, and whose
   implied cents per contract **exceeds the bucket's cost bar**.
2. Anything less is a null and will be reported as one.

## The prior, stated honestly

Across this repo, **45 corrections, every one shrank the edge, not one ever
revealed a larger effect.** Eight apparent positives have died. The base rate
for this study returning a real tradeable edge is low, and the most likely
outcome is another null. That is not a reason to skip it — it is the reason to
fix the analysis choices before running it.
