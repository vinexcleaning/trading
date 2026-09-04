# Pre-registration — `bullpen-f5`, a negative control on a live bot

**Written 2026-09-04, BEFORE it placed anything.** The factory's `SF201`, routed
via mailbox 029. Registered under `CLAUDE.md` §10.

## The idea, and why it is the best thing anyone has sent this project

`bullpen` claims to read **reliever fatigue** and trades the **full-game** run
total. `bullpen-f5` runs **the same trigger** against the **first five innings**
total.

**Relief pitchers do not pitch the first five innings. So this must find
nothing.**

## ⚠ HOW TO READ IT — registered before it runs, because the temptation is real

| what happens | what it means |
|---|---|
| it loses money, or never clears the bar | **`bullpen` is measuring what it claims.** The control passed. |
| **it makes money** | **`bullpen` is MISLABELLED.** It is picking up the starter, the park, or the teams — and every number that bot has ever produced means something other than what it says. |

> **A profit here is BAD news, not good news, and nobody is to promote it.**

This repo has never run a negative control on a live bot. `GUARDS.md` #3 and #4
are exactly this shape.

## Hypothesis

**`bullpen-f5` returns nothing distinguishable from zero.** That is the
prediction, and it is a prediction of a null — which is the point.

## Unit of observation

**One game.** A market settles once.

## Sample and dates

Forward only, from this commit. **21 of 45 games in a live pool carry a
`KXMLBF5TOTAL` market**, and a dry run before it took a slot produced **1 entry
across the 9 games in its windows** — so it can fire. That check exists because
`rested` was dropped two days ago for being unable to fire at all, and `lineup`
sat at zero for three weeks before anyone noticed.

## How many games before it can be judged

**60 settled games.** At the observed rate that is roughly six weeks.

## What result makes us DROP it

- **It reaches +5 per 100 or better over 60 games.** That does not promote it —
  **it condemns `bullpen`**, and the correct response is to re-open every
  `bullpen` claim in `LEDGER.md`, not to trade this.
- **It cannot reach 60 games in ten weeks.** Then it is `lineup` again and it
  should be retired rather than left sitting.

## What would make me doubt a null

A null here is only informative if the trigger genuinely fires. **If it declines
almost everything, "found nothing" is indistinguishable from "never looked"** —
which is precisely the `lineup` failure. Entry count is reported beside the
result every time, never the return alone.

## The denominator

**20 → 21 bots.** Joint denominator 16 + 16 = 32 → **21 + 16 = 37** before
tennis's own five new entries, which take it further. Pinned by an assert and a
test. **Five slots remain before the count rises again.**

## What is NOT being tested

The other nine factory specs (`SF200`, `SF202`, `SF203`, `SF208`, `SF209`,
`SF212` and the rest) · the home-run family · the first-inning family ·
anything about whether `bullpen-f5` is tradeable, which it is not and is not
meant to be.
