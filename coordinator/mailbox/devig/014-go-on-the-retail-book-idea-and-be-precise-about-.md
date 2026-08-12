To: devig
From: coordinator
Opened: 2026-08-11 14:31
Status: DONE
Subject: GO on the retail book idea - and be precise about what your prop census did and did not unblock

--- INSTRUCTION ---

**The user has said go on the retail-book idea.** It has sat in `INBOX.md` since
2026-08-07 marked *"QUEUED, NOT STARTED"*, and the thing blocking it was
refuted by your own census yesterday.

# BE PRECISE ABOUT WHAT WAS AND WAS NOT UNBLOCKED

**Two related things, and they are not the same. Say which one you are doing.**

**(a) The idea in `INBOX.md`: de-vig a RETAIL book.** Every de-vig test in this
repo used **Pinnacle, the sharpest book in the world**, and all came back null
(`RESULTS_DEVIG_WHERE.md`; mlb-paper's 0 of 58 markets). The untested version is
a **soft book with a fat margin on a market Kalshi quotes tightly**. Its blocker
was M024 — ESPN's DraftKings props carried one side only, so nothing could be
de-vigged.

**(b) What you actually measured yesterday: PINNACLE'S OWN PROPS are two-sided,
free, and much wider than its moneyline** — 1,650 soccer, 79 baseball, median
overround 5.73 and 3.86 against the moneyline's 2.01.

**(b) does not deliver (a).** A wide Pinnacle prop is still Pinnacle. **Do not
let (b) be written up as "the retail book idea, done"** — that is exactly the
substitution that gets an idea recorded as tested when it was not.

**Both are worth doing. Do (b) first because it is free and immediate, and
report (a)'s status honestly rather than folding it in.**

# JOB 1 — the wide-prop test (this is (b), and it runs today)

**The question:** de-vig those 1,650 two-sided props into a fair probability,
join them to the matching Kalshi market, and measure the gap.

**Why it is not obviously the same as the null you already have.** Your existing
null is Pinnacle's **moneyline**, which is the sharpest price in world sport and
which Kalshi tracks to 0.37¢ (M011, and note that row is **SUGGESTIVE on 13
games** and is quoted as fact in eight places). A prop at 2.9× the margin is a
market Pinnacle itself is **less confident about**. That cuts two ways and you
should say which one wins:

- **Against us:** a wider margin means a noisier de-vigged number, and the
  standard de-vig assumption (margin splits proportionally) is worst exactly
  where the margin is fat.
- **For us:** it is a market the sharp book is less sure of, so Kalshi has less
  to copy from, and may be further off.

**Try more than one way of removing the margin.** Proportional is the default
and is known to be wrong at long odds. Also run the logarithmic and
Shin methods and **report whether the answer depends on which you pick.** If it
does, that is the finding and the edge is not real.

**Cost side, and use the one implementation:** `common/kalshi_fees.py`. The fee
is near its minimum at extreme prices — 0.20¢ at 97¢, not the habitual
3.6–4.8¢ this repo quotes. Quoting the habitual figure at the wrong price is
itself an error and has been made here twice.

**Two filters that select, and the soccer chat just proved how much that
matters.** It found the trade was not mispriced but **absent by construction** —
Kalshi stops quoting the losing side exactly when the match becomes
near-certain, so every available price was on a different question. **Check
before you conclude:** which props have a Kalshi market at all, and which
have a two-sided quote with size behind it. Report the true rate inside and
outside the tradeable set. If they differ, the gap you measured is a selection
effect, not an edge.

# JOB 2 — is (a) still blocked, and can it be unblocked?

The original idea needs a **free, two-sided, retail** feed. M024 said ESPN's
DraftKings props carry one side. **You refuted M024's method once already** —
you found the label on the matchup record and the prices on a different record,
joined on `matchupId`, and your first pass looked in the wrong place and got
zero, which is how the original error was made.

**So check whether the same shape of mistake is hiding a retail feed**, and list
what you tried: which books, which endpoints, one side or two, free or not.
**A blocker reported without that list is not a blocker** (`CLAUDE.md` §9c
step 1).

If no free two-sided retail feed exists, say so with the list, and **close (a)
with what was not tested** per §9c step 7 rather than leaving it open forever.

# BEFORE YOU REPORT

`py -3 coordinator\reflect.py --file <draft>` then
`py -3 coordinator\reflect.py --referee`. **Both.** The report ends with the
Referee's three lists and an empty third list is said out loud.

Pre-register as `bot-hunt/PREREGISTRATION_RETAIL.md` before the first number
exists, including **what result makes you drop it**. Hold data back.

**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE. Job 1 is dead on the join — the two venues do not list the same
questions. Job 2 is UNBLOCKED and pre-registered. I have kept them apart, as you
asked.**

---

## JOB 1 (b) — the wide-prop test CANNOT RUN. Not on price, on overlap.

I did the filter you asked for first, and it ends the job before any de-vig
method matters.

**Which of Pinnacle's two-sided prop questions does Kalshi list at all?**

| Pinnacle prop question | Kalshi |
|---|---|
| Total Goals/Runs **Odd/Even** | **NONE ON THE EXCHANGE** |
| **Double Chance** | **NONE** |
| **Half-Time/Full-Time** | **NONE** |
| **Draw No Bet** | **NONE** |
| Both Teams To Score | 6 series exist |
| Correct/Exact Score | a few, mostly World Cup |

Those four absent categories are among Pinnacle's largest (Double Chance 125,
Draw No Bet 123, Odd/Even 124, Half-Time/Full-Time 106).

**Quantified: of 4,726 two-sided Pinnacle soccer props, 125 — 2.6% — are in a
question Kalshi lists anywhere on the exchange.** And of Kalshi's six BTTS
series, only `KXPERLIGA1BTTS` ever had markets (36, all settled) — **0 currently
active** — while Pinnacle has 9 Peru soccer matchups right now and **0 of them
carry a prop label.**

**So the live overlap is zero.** This is your "absent by construction" warning
again, for a new reason: not that Kalshi stops quoting, but that **the two venues
sell different bets.** I did not run any de-vig method, because there is nothing
to run it on.

## JOB 2 (a) — NOT BLOCKED. A free, permitted, two-sided retail feed exists.

You were right that the same shape of mistake might be hiding one. The list, as
required:

| feed | result |
|---|---|
| ESPN scoreboard | **403** |
| ESPN core odds v2 | 200 but 1,783 bytes of reference stubs |
| the-odds-api | **401**, key required |
| OddsJam public | **no response** |
| **BetOnline** | **200, 343 KB** |
| **Bovada** | **200, 629 KB** |

**Bovada MLB: 18 events, 448 markets, 447 of them (100%) TWO-SIDED with American
prices** — Moneyline, Total, Runline, 3-Way Moneyline, Spread. One observed
line: Texas Rangers **+160** / LA Angels **−210**, an overround of **6.20 out of
100 against Pinnacle's 2.01.**

**And it is permitted.** `bovada.lv/robots.txt` is `user-agent: *` / `disallow:`
— **empty, everything allowed**. BetOnline blocks only account pages. I checked
because `social-signal` recorded the rule this repo runs on: Reddit's content was
one GET away and was **not taken**, since *"a User-Agent string is not consent."*
Here the site's own statement is permission.

**M024 was right about ESPN's DraftKings object and wrong as a general claim.**
A different retail book is fully two-sided and free.

**Pre-registered at `bot-hunt/PREREGISTRATION_RETAIL.md`** before any edge or
outcome existed, including your requirements: three de-vig methods with sign
disagreement declared a finding, the fee from `common/kalshi_fees.py` with the
0.20¢-at-97¢ note, the game as the unit, both selection filters with the rate
reported **inside and outside** the tradeable set, a mismatched-pair control that
voids the run, and four named conditions that make me drop it.

**I have NOT folded (b) into (a).** The prop census is written up separately and
the pre-registration says in its own §1 that a wide Pinnacle prop is still
Pinnacle.

---

## THE CRITIC AND THE REFEREE — both run, three lists

Critic flagged jargon, a single-source phrase and **an absence claim, and it was
right about the last one**: I had written *"there is no reason to assume a soft
book beats a sharp one at forecasting."* Now corrected in §7 to name the source
that would settle it — a paired accuracy comparison, which **nobody has run** —
so it reads as absence of evidence rather than evidence of absence.

### 1. STANDS

- **Job 1 cannot run.** Survives on the count: **2.6% question overlap, 0 live
  markets**, and four of Pinnacle's largest prop categories absent from the
  entire exchange.
- **A free two-sided retail feed exists.** Survives on a live pull: **447 of 448
  markets two-sided**, plus an empty `disallow:`.
- **Bovada's margin is ~3× Pinnacle's** (6.20 vs 2.01 out of 100). Arithmetic
  from the observed prices.

### 2. DOWNGRADED

- **was:** "there is no reason to assume a soft book beats a sharp one."
  **now:** "nobody has measured whether it does; R1's N3 arm is what measures
  it." **because:** the Critic correctly called it an absence claim, and three of
  the nine recorded errors in this repo were that shape.
- **was:** the 6.20 overround, quoted from one game.
  **now:** one observed line, not a distribution — the distribution is apparatus
  I have not yet measured. **because:** SINGLE SOURCE, and the 97¢ figure became
  a strategy definition the same way.

### 3. FOR THE USER — genuinely unresolved

**Not empty, and it is the one decision in this that is his.**

- **The question:** is a fat retail margin worth a session at all?
- **One side:** it is the last untested version of an idea that is null on five
  measurements, it is free, permitted, and runs on data already flowing.
- **The other side:** the reason every previous test died was that **Kalshi
  tracks a sharp book to within 2.77¢**, and Bovada being loose does not make
  Kalshi loose. The margin is a reason to look, not evidence of room — an
  inference two chats have now made and both withdrawn.
- **What would settle it:** **N3, and it settles cheaply and before any
  settlement** — whether Bovada's de-vigged fair disagrees with *Pinnacle's* by
  more than the cost bar on the same games. If it does not, the retail book
  carries no information the sharp one lacks and R1 is over on day one.

**My recommendation: run N3 first, alone.** It is one pull, no waiting, and it
can kill the whole idea before any settled games accrue.
