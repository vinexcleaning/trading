# RESULTS — where this repo is flying blind on Kalshi baseball

**2026-08-14.** Mailbox 018, second job. **Apparatus only. No edge is claimed
anywhere in this file and no settled game is used.**

> ### ⚠ The inference that must NOT be drawn from any of this, stated first
>
> *"No free sharp reference exists for this market"* is **not** evidence that
> the market is mispriced. That is **M024's retracted argument**, and `RESEARCH`
> refused it explicitly and correctly. It is equally consistent with **nobody
> trading the market at all** — and it **removes the cheap way of finding out
> you are wrong.** A market with no reference is not an opportunity; it is a
> place where a mistake would be expensive to detect.

---

## 1. The board, and how much of it can be checked

Measured **2026-08-14 06:20 UTC** against Kalshi's live listing and Pinnacle's
free guest feed, read minutes apart.

| | |
|---|---|
| Kalshi baseball series listed by the exchange | **178** (of 3,403 sports series) |
| of those, with open markets right now | **110** |
| open baseball markets | **4,291** |
| of those, quoted on both sides | **2,105** |

**Split by whether a free sharp price exists at all:**

| | markets | two-sided |
|---|---|---|
| **HAS a free reference** — game winner, totals, spread, team totals, first-3/5/7 innings | **605** | 605 |
| **NO free reference** — 102 other series | **3,686** | 1,500 |

> **86 out of every 100 open baseball markets on Kalshi have no free sharp price
> to check them against.** Not "are mispriced" — **cannot be checked**, cheaply
> or at all.

---

## 2. ⚠ But one of `RESEARCH`'s absences is wrong, and it is the useful part

**The instruction states, from `RESEARCH`:** Pinnacle's free feed carries *"79
two-sided baseball props in three kinds only — Exact Scores 66, Next Run 11,
Futures 2. **No first-inning run line, no strikeout line, no first-five
total.**"*

**Read today, the same free endpoint carries all three of those things.**

| Pinnacle free guest feed, 2026-08-14 06:20 UTC | count |
|---|---|
| Exact Scores | 190 |
| **Player Props** | **12 parents → 62 two-sided priced markets** |
| Double Result | 10 |
| Next Run | 10 |
| **first-five-innings totals** (`total p1`) | **105** |
| **first-five-innings moneyline / spread** | **90 / 102** |

**The player props are exactly the families that were called blind:**

```
Grayson Rodriguez Total Strikeouts     George Kirby Total Strikeouts
Gavin Williams  Total Strikeouts       Peter Lambert Total Strikeouts
Shohei Ohtani   Total Home Runs        Cal Raleigh   Total Home Runs   …
```

**And they join to Kalshi by player name:**

| Kalshi series | its markets | distinct players | Pinnacle players | **overlap** |
|---|---|---|---|---|
| `KXMLBKS` — strikeouts | 149 | 20 | 11 | **10** |
| `KXMLBHR` — home runs | 45 | 21 | 51 | **13** |

Kalshi's most common strikeout title is **"George Kirby: 9+ strikeouts?"**.
Pinnacle's free feed prices **"George Kirby Total Strikeouts"**, both sides.
**That is a two-sided sharp reference against a Kalshi market, free, today.**

> **This is the fourth false absence found in a week**, and the first that was
> not mine — C024, M024, my own retail census, and now this. Every one had the
> same shape: **one read, one endpoint, one moment, and a confident "there is
> none".** None was a reasoning failure.
>
> **In fairness to `RESEARCH`, the honest reading is that the feed changed, not
> that they were careless.** A free feed's contents move with the calendar, and
> theirs may have been read on a day with no listed props. **Which is exactly
> why an absence needs a date attached and a re-read before it is cited** — and
> theirs was cited, six days later, to say where we are blind.

---

## 3. What this opens, and what it explicitly does NOT

**⚠ This is NOT R1 and must never be folded into it.**
`PREREGISTRATION_RETAIL.md` §1 says so in advance: *"A wide Pinnacle prop is
still Pinnacle. This file is about a retail book… that is exactly how an idea
gets recorded as tested when it was not."* R1 is Bovada versus Kalshi. **This is
a different test with a different reference and needs its own pre-registration.**

**What is genuinely new:** every de-vig null in this repo was measured on the
**game winner** — the single most-traded, most-arbitraged market on the board,
where Kalshi was measured tracking Pinnacle to within **2.77¢** (1,460 paired
readings, 30 games, 2026-08-05 to 2026-08-11). **Whether that tightness survives
on a player strikeout line is unmeasured.** It plausibly does not: props are
thinner, and Pinnacle's own prop margin was measured 2–3× its moneyline margin.

**But "plausibly does not" is the exact inference this repo keeps getting wrong**
— a fat margin is a reason to look, never evidence of room. The only thing that
would show anything is a measured disagreement, on games held back.

**Cost to find out: roughly nothing.** Both feeds are free, both are already
wired, the join works on player name today at 10 and 13 players, and no game has
to settle for the first, cheapest question — *do the two prices even disagree?*

---

## 4. What this did NOT test

`CLAUDE.md` §9c step 7.

- **Whether the overlap holds tomorrow.** One reading, one moment. 10 and 13
  players is a joinable set, not a sample.
- **Whether the two are the same question.** Kalshi asks *"9+ strikeouts?"*;
  Pinnacle prices *over/under a line*. **If the lines differ the comparison is
  invalid**, and the points were not read in this pass.
- **Depth.** Nothing here measures what size sits at Kalshi's ask, or Pinnacle's
  limit.
- **The other 102 blind series.** Awards, season leaders, next-team, debuts —
  3,686 markets that nothing here even attempts to reference.
- **Any non-Pinnacle reference for the blind families.** Bovada's 467 two-sided
  markets were not searched for strikeout or home-run props, and four other
  permitted bookmakers were never parsed at all.
