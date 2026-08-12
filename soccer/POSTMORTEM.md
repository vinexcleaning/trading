# POSTMORTEM.md — what went wrong, and what came out of it

**2026-08-11.** Written at the user's request before this folder goes quiet:
*"see what happened, what we did, what went wrong, what are some new ideas."*

The closure itself is in [CLOSED.md](CLOSED.md). This is the part about how the
work was done rather than what it found.

---

## 1. Four corrections in three days, and what would have caught each

**The list is the deliverable, not the apology.** Two of the four were caught
before anyone acted on them, and one was caught by a tool rather than by care.

### (a) Every price was from two minutes after a goal, and the headline did not say so

**What was reported:** *"Four times in five, nobody is bidding on the losing
side."*
**What was true:** that, measured only in the last twenty minutes of a match and
only just after a goal. Early in a match a market exists **93 times in 100**.

**What would have caught it earlier:** the script's own comment said plainly
that prices were read at the instant of a goal. The *report* dropped that
condition. **A number should carry the rule that produced it in the same
sentence, not in the file that made it.**

### (b) "No European league in the price sample" — false, and hidden three separate times

Kalshi had **66 settled Champions League markets inside the window all along.**
Three independent defects each hid them, and each one printed the same thing —
*"no fixture"*:

1. ESPN files qualifying rounds under a different competition code.
2. Exact-name matching joined **6 of 66** — "Kairat" against "Kairat Almaty".
3. A required kickoff timestamp that **53 of 66** of those matches do not carry.

**What would have caught it earlier:** the pipeline printed *"no ESPN fixture:
1,275"* as a bare count. **A drop counter with nothing to compare it against is
invisible.** Had it printed "expected ~66 Champions League, matched 6", it would
have been obvious on the first run. The Critic caught it eventually, at write-up
time, which is late but not too late.

### (c) A ten-year football rate compared against a two-month price sample

**What would have caught it earlier:** I did check whether the *years* matched
and found the game changed in 2022. **I did not check whether the
*competitions* matched until later** — and more than half the price sample was
World Cup and friendlies while the rate was 26 competitions. **Before comparing
two samples, list what is in each. Afterwards is a correction; beforehand is a
design.**

### (d) The over-reaction test counted quotes of 100 and 0 as if they were prices

It produced a tidy table in which the market looked perfectly calibrated. It was
an artifact. Nobody flagged it; it fell over only when I insisted on prices that
could actually be acted on, and the sample collapsed from 82 goals to 18.

**What would have caught it earlier:** the idea of "is this a real price" already
existed elsewhere in this folder and was simply not used here. **One
implementation of that test, used everywhere, instead of the same idea written
twice and correctly once.** That is GUARDS #6's rule about fee arithmetic applied
to a different thing.

### The pattern underneath all four

**Every one is the same failure: a number that lost the condition it was
measured under.**

| the number | the condition it lost |
|---|---|
| "no market four times in five" | *late in the match, just after a goal* |
| "no European league" | *under this competition code, with this name match* |
| the comeback rate | *these competitions, these years* |
| the price move after a goal | *only where a real quote existed* |

**A number and its condition have to travel together or the number is wrong the
moment it is quoted.** That is the single most useful thing this folder learned
about method, and it is cheaper to fix than any of the four individually.

---

## 2. What outlives the folder

Already filed outside `soccer/`, per the closing instruction:

- **[GUARDS.md](../GUARDS.md) #24** — the market does not quote a
  near-certainty; a strategy shaped *"buy the thing that is 97% to happen,
  cheaply"* fails on **availability**, not on price.
- **[LEDGER.md](../LEDGER.md) Section 9** — the two claims that are not about
  soccer.

**Section 3 below strengthens #24 from one sport to seven.**

---

## 3. Does this transfer to other sports? Measured, not guessed

The user asked. Rather than reasoning about it, the same question was put to
every sport Kalshi runs per-game, using **only the price** — no scores, no
clocks, no sport knowledge:

> When the market itself says an outcome is nearly sure, how often can you
> actually buy it?

*Near-certain* = somebody bidding 95 cents or more. *Buyable* = there is an
offer below 100 you could hit. Both read off one-minute candles in the five
hours before each market closed, on 2026-08-11. **And a control, because otherwise this measures
nothing**: the same fraction at middling prices, 40 to 70 cents, in the same
markets. A thin book would show few offers everywhere.

| sport | buyable when NEARLY SURE | buyable when IN DOUBT |
|---|---|---|
| soccer | **29 in 100** | 100 in 100 |
| basketball (women) | 31 in 100 | 100 in 100 |
| basketball | 37 in 100 | 100 in 100 |
| hockey | 51 in 100 | 100 in 100 |
| baseball | 53 in 100 | 100 in 100 |
| tennis (men) | 56 in 100 | 100 in 100 |
| tennis (women) | 67 in 100 | 100 in 100 |
| american football | too few — off-season, 1 minute | 100 in 100 |

`reports/other_sports_probe.txt`, measured **2026-08-11** on **284 settled
markets** across those sports — 3,238 near-certain minutes and 33,802 middling
ones. **Every sport is buyable on every single one of its 33,802 middling
minutes**, which is what makes the left-hand column mean something.

**Three things fall out, and the first is the answer to the question asked.**

**It is market-maker behaviour, not soccer.** Every sport shows the same shape:
a perfect 100 in 100 while the outcome is in doubt, and between 29 and 67 once
it is nearly sure. The control rules out thin books — these are the *same
markets*, quoted freely minutes earlier. **The draw leg was not the cause**, so
the soccer-specific explanation is dead.

**Soccer was the worst sport to have tried this in.** 29 in 100 is the bottom of
the table. The idea picked, by chance, the hardest case.

**Tennis keeps quoting furthest into a near-certain state** — 56 and 67 in 100,
roughly twice soccer's rate. If a near-certainty strategy is ever attempted
again in this repo, tennis is where the *quote* survives.

### ⚠ What this does NOT say, and it matters

**Availability is necessary, not sufficient.** Soccer had a market early in a
match too, and the price was still bad. Being able to buy something is not
evidence that buying it makes money.

**This has no event state.** A 95-cent price could be a heavy pre-match
favourite rather than a late near-certainty. It measures quote availability
against price, which is what GUARDS #24 is about, and nothing more.

**These are not my folders.** `tennis` and `mlb` own the follow-ups.

### Handed over, one question each

- **→ `tennis`.** No draw exists, so there is no double-chance bet at all — but
  quotes survive furthest here. **Does a player two sets up at 95 cents stay
  buyable, and is the price any good?** What would answer it: match state from
  the existing tennis pipeline joined to per-minute Kalshi quotes, the same
  shape as `soccer/src/price_by_minute.py`. `clock_map.py` is not needed —
  tennis is scored in points and games rather than against a running clock, so
  the displayed-minute problem it solves does not arise.
- **→ `mlb`.** **Baseball has no clock that ends the game** — there has been a
  pitch clock since 2023, but nothing runs the game out — **so does a quote
  survive further into a near-certain state because nothing forces the end?**
  53 in 100 against soccer's 29 says it partly does. What would answer it: half-inning state joined to quotes, and the
  comparison is against soccer's 29.
- **→ whoever takes basketball.** The worst two rows on the table, 31 and 37 in
  100. Probably the least promising place to look, and cheap to confirm.

---

## 4. The live descendant, in one paragraph

**The reverse trade.** Not betting against the team that is behind, but backing
a side to hold on or to come back — a cheap contract instead of a 97-cent one.
Nothing here kills it: the mechanism that killed the original is *"nobody quotes
a near-certainty"*, and this buys the **uncertain** side, which is exactly where
quotes are a clean 100 in 100 in every sport measured. Its loss is capped at
what you paid, which is the opposite risk shape to the one that has already
blown up once in this repo. The football behind it is solid — a side that goes
one goal up between the 20th and 35th minute wins **72.6 times in 100 if it is a
strong team (1,562 matches)** and **59.6 if it is weak (944)**. **What would
answer it:** Premier League or Champions League group-stage prices, which this
69-day window did not contain; team strength taken from each club's domestic
form rather than from within a competition; the fee at the cheap end, which is
nearly nine times what it is at 97 cents (1.74 against 0.20); and a fresh
pre-registration on the 2025–2026 years that have never been opened.
**`PREREGISTRATION_COMEBACK.md` does not cover it** — it is the opposite bet and
reusing it would be dishonest.

---

## 5. What actually went right, briefly

Recorded because a post-mortem that only lists failures teaches the wrong
lesson:

- **The user's own hypothesis was the one thing predicted in advance and it held.**
  At the 25th minute a goal up, a strong side is caught 7 times in 100 and a
  weak side 24.
- **The canary's failure was predicted in writing before it was run**, in the
  file header and the git history.
- **Two of the four corrections were caught before anyone acted on them**, one
  of them by `reflect.py` rather than by care — which is an argument for the
  tool, not for me.
- **The held-back years were never opened**, and the pre-registered test never
  ran because its premise failed first. That is the system working as designed.
