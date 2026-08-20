# STRATEGY_SPECS.md — the wrongly-closed claims, sorted into ideas and bookkeeping

**As of 2026-08-20.** Written by `reopen` from mailbox 005, which asked for the
51 wrongly-closed claims to be turned into strategy specs for the factory.

**Format follows [coordinator/STRATEGY_FACTORY.md](../coordinator/STRATEGY_FACTORY.md)
Stage 2:** id · market family · what it bets on · entry · exit · size · what
would make it wrong · who suggested it · date. Every spec carries its claim ID
and **one line saying what the original test did not cover**.

---

## ⚠ FIRST — the pond is smaller than the tasking thinks, and by a lot

`STRATEGY_FACTORY.md` calls the wrongly-closed claims *"a stocked pond nobody has
fished"* and counts them as one of four idea sources. **That framing overstates
what is in them by about five times, and saying so is this chat's job.**

**The current count is 48, not 51** — items came off as I withdrew my own bad
calls (S021, M017, C022) and one new one arrived (M016b). The number is not the
point. **What they are is the point.**

| what the 48 actually are | count |
|---|---|
| **A tradeable idea whose closure was wrong** | **9** |
| Dead anyway — a later result settled it, a guard rules the shape out, or the data window shut | **11** |
| **Not a strategy at all** — a wording fix, a bug record, a data-availability fact, an enabler | **28** |

**Twenty-eight of the 48 are bookkeeping.** "The parse bug that blocked crypto",
"three cost bars are in circulation", "this website serves the wrong country" —
all real, all worth fixing, **none of them a thing you can bet on**. They were
never strategies, and turning them into specs would produce 28 pieces of fiction.

**So the honest yield is 9 specs, not 51.** Nine already-worked ideas with data
mostly collected is still the best-value source in the factory. It is just not 51.

---

# THE SPECS — ranked by what changes if the closure was wrong, against what it costs to find out

## RS-01 · Hold a crypto ladder contract to settlement

| field | value |
|---|---|
| **id** | `RS-01` |
| **claim** | **C023** (crypto) |
| **market family** | `KXBTCD`, `KXETHD`, `KXSOLD`, `KXXRPD` — daily crypto ladders |
| **what it bets on** | That a contract bought at the ask in some price band and held to settlement pays more than it cost |
| **entry** | Buy at the **real ask** in a fixed price band (5/10/15/20/25/30/40/50/60/70/80/90¢) at a fixed point in the event's life |
| **exit** | **None — hold to settlement.** One fee, not two |
| **size** | Fixed contracts per event; report what the book actually fills at `depth5` |
| **what would make it wrong** | Any band whose day-clustered interval sits below zero; or a placebo arm with shuffled settlement labels producing the same shape |
| **suggested by** | `reopen`, from the audit |
| **date** | 2026-08-20 |

**Why the closure was wrong.** `LEDGER.md` records C023's effect as the single
word **"negative"**, with no sample and no dates. The committed artifact
(`crypto/reports/hold_settle.txt`, 25 May – 30 Jul 2026, four assets, 146–250
events each) says **TIE in 40 of its 44 price cells**. Only the 90¢ BTC band is
negative. The ranges run **plus-or-minus 5 to 15 cents against a cost of 1–2
cents** — the test could not see anything smaller than about five cents.

**What the original test did NOT cover:** enough days to resolve a 1–2 cent
effect. It is one pull, and about **76 days of trade tape are retrievable**.

> ⚠ **Do not chase the cell that looks best.** Bitcoin at 5 cents reads
> **+2.93 with a range of [−0.01, +6.13]**, and the other three assets go the
> *other* way at the same price. C026 puts the four assets at **about 1.8
> independent series, not four**. **This spec measures the family. It does not
> buy the 5-cent cell.**

**Cost:** one paced download plus one re-run. The tape boundary was re-measured
on 2026-08-09 and is a fixed calendar date, so it is not urgent.

---

## RS-02 · Does the weather model beat the price you would actually pay

| field | value |
|---|---|
| **id** | `RS-02` |
| **claim** | **C061** (kalshi-inplay-bot P2), against **C096/C097** (weather-market-bot) |
| **market family** | `KXTEMPDCH` first — the only family clearing both the power bar and the depth bar (K004) |
| **what it bets on** | That a persistence-plus-hour-of-day forecast estimates settlement better than Kalshi's own quote |
| **entry** | When the model's probability differs from the **ask** by more than the round trip costs, buy the side the model favours |
| **exit** | Hold to settlement — it settles on a published observation |
| **size** | Fixed; report depth at the touch, which K004 measured at 50-plus contracts for this family only |
| **what would make it wrong** | The model's error is no lower than the market's on a sealed split, **counted once per settlement hour rather than once per market** |
| **suggested by** | the 2026-08-06 audit ranked it #1 of ten; spec by `reopen` |
| **date** | 2026-08-20 |

**Why the closure was wrong.** C061 records this as *"unmeasured and blocked on
days of recorded books"*, and the root audit calls it **the largest unexplored
lead in the repo**. K002 shows the model genuinely beats climatology in four
cities. **The deciding comparison — against the market — was never run.**

**What the original test did NOT cover:** the market. It beat climatology, which
is a weak benchmark, and `MORNING_REPORT.md` says so itself.

> ⚠⚠ **READ THIS BEFORE SPENDING A RECORDER ON IT.** `C096`, in
> `weather-market-bot` a week earlier, ran a version of this test: a weather
> model scored against **real ask prices** on **600 held-back, sealed
> contracts** — and **the model lost.** Wrong by **0.2048** where the market was
> wrong by **0.1690**, lower being better. `C097` then blended them 89/11 and the
> improvement **vanished once each weather event counted once instead of each
> contract**.
>
> **Different family, different benchmark, different model — so it does not
> settle this.** It changes the prior hard, and **nothing in the repo cites it.**
> If RS-02 runs, it should be pre-registered *against* C096, not in ignorance of
> it.

**Cost:** a recorder job across many settlement cycles. **The most expensive spec
here and the one with the strongest prior against it.**

---

## RS-03 · The set-score decomposition against the match price

| field | value |
|---|---|
| **id** | `RS-03` |
| **claim** | **CH074** (chat archive) |
| **market family** | `KXATPSETWINNER`, `KXWTASETWINNER` against `KXATPMATCH`, `KXWTAMATCH` |
| **what it bets on** | That the set-score legs and the match price disagree by more than it costs to trade both |
| **entry** | At a fixed pre-match anchor, compute the gap between the match price and its decomposition at **executable** prices; enter only when the gap exceeds the two-leg cost |
| **exit** | Hold both legs to settlement — it is definitional or it is nothing |
| **size** | Whatever the thinner leg fills at. **Report it, because this is where it will die** |
| **what would make it wrong** | The gap sits inside the two-leg fee-plus-spread floor at every anchor — which is what C002's ladder arithmetic predicts |
| **suggested by** | the user, 2026-07-30, from his own observation of a 40% match price against a 20% "2-1" |
| **date** | 2026-08-20 |

**Why the closure was wrong.** CH074 was closed by **an arithmetic argument on
one worked example** — a parlay's edge is the product of its legs' edges, so the
decomposition cannot be less efficient than the match market. The argument is
sound. **The residual test it proposed, at prices you could really pay, was never
run.**

**What the original test did NOT cover:** any price. It was arithmetic, not a
measurement.

**Feasibility, checked twice on 2026-08-20 per GUARDS #25:** `KXATPSETWINNER`
**8 open, 200-plus settled and still paging**; `KXWTASETWINNER` the same. **The
settled history a backtest needs is there.** (I earlier reported this family as
having zero markets — that was one query against `KXATPTOTALSETS`, which really
is empty, generalised wrongly to the whole idea.)

> ⚠ **Guard check — #24.** Legging a decomposition is close to the "free money at
> the extreme end of a book" family. **Whether the second leg is quotable at all
> is the whole question**, so this spec reports the quote-existence rate at entry
> before it reports any edge.

**Cost:** one analysis run on settled history. **Cheapest of the top three.**

---

## RS-04 · The fade side of the tennis set-1 move

| field | value |
|---|---|
| **id** | `RS-04` |
| **claim** | **S023** (set1_overshoot) |
| **market family** | Kalshi tennis match markets, in-play after set 1 |
| **what it bets on** | The **opposite** side of the undershoot — fading the post-set-1 move rather than following it |
| **entry** | The six configurations `p2_fade.py` already implements, on the **outcome-independent** dedupe |
| **exit** | As configured; hold and laddered variants both reported |
| **size** | Fixed contracts; cost bar measured rather than assumed — see below |
| **what would make it wrong** | Every configuration stays negative once the edge term is recomputed on the clean event set. **`SELECTION_AUDIT.md` says the conclusion probably survives** |
| **suggested by** | `set1_overshoot`; flagged unre-run by the 2026-08-06 audit (D1) and again by this one |
| **date** | 2026-08-20 |

**Why the closure was wrong.** A dedupe bug (S011) voided the event set. S023 is
marked **BROKEN** and `SELECTION_AUDIT.md` row 7 says **NEEDS RE-RUN**. It never
was. **So half of "tennis set-1: no edge in either direction" is an expectation
rather than a measurement.**

**What the original test did NOT cover:** a valid event set. The edge term is
void; only the cost arithmetic carries the conclusion.

> ⚠ **Blocked on the laptop, not on a chat.** `set1_overshoot/data` does not
> exist on the desktop and `runners.py` reports the depth recorder as never
> confirmed running.
>
> ⚠ **And the cost bar has moved against it.** `tennis` measured the real round
> trip forward at **4.79 cents** (2.67 fee + 2.12 spread, 81 observations)
> against the **3.61** this study assumes — 33% higher, on a different pool, so
> directional. **A bigger bar makes a negative conclusion more likely, not less.**

**Cost:** one re-run, once someone is at the laptop.

---

## RS-05 · Kalshi player props against a two-sided free book

| field | value |
|---|---|
| **id** | `RS-05` |
| **claim** | **M025** (market-selection), which was **CANCELLED as unanswerable** |
| **market family** | `KXMLBKS`, `KXMLBHIT`, `KXMLBTB`, `KXMLBHRR` — Kalshi MLB player props |
| **what it bets on** | That Kalshi's prop price differs from a de-vigged sharp book by more than the round trip costs |
| **entry** | De-vig the two-sided book price; buy the Kalshi side that is cheaper by more than the cost bar |
| **exit** | Hold to settlement |
| **size** | Small. M019 measured prop depth at **122–403 contracts at the touch**, and the book caps its own side at **$500** |
| **what would make it wrong** | The de-vigged gap sits inside the cost bar at every prop type — the shape BH011 found on the moneyline |
| **suggested by** | `reopen`, from `bot-hunt`'s own committed probe |
| **date** | 2026-08-20 |

**Why the closure was wrong.** M024 recorded **0** prop entries carrying both
sides, and M025 was cancelled as *"unanswerable with free data"* — **measured on
one feed.** `bot-hunt/reports/pinnacle_probe.json`, committed 2026-08-04, holds a
free unauthenticated **two-sided** MLB player prop: category `Player Props`,
*Justin Foscue Total Bases*, **Over 0.5 at −125, Under 0.5 at −106**, max stake
**$500**. **The absence claim is false.**

**What the original test did NOT cover:** any book other than the one whose feed
publishes props one-sided.

> ⚠ **Three warnings, and the second is about my own reasoning.**
> **(a)** That book keeps **7.0 out of 100** on this prop against **2.01** on its
> moneyline — three and a half times wider, with a $500 cap. **A book quoting
> that wide is telling you it is not confident.**
> **(b)** I earlier argued the wider vig means "more room to be wrong in".
> **That used a premise `devig` had already retracted** — the overround is what
> you strip out; it does **not** bound the edge. **RS-05 rests on "the absence
> claim was false" and on nothing else.**
> **(c)** Re-running the other side of this **returns 403 today** — eleven
> scripts in `market-selection/` and `mlb/` send a blocked `User-Agent`. **Fix
> the header first or the run reports a false "none found".**

**Cost:** one probe plus one join. Cheap.

---

## RS-06 · Pre-match player features, on three years instead of 29 days

| field | value |
|---|---|
| **id** | `RS-06` |
| **claim** | **B023** (bot-forensics), enabled by **T002** and **S018** |
| **market family** | Kalshi tennis, pre-match, at the open |
| **what it bets on** | That a player's form and head-to-head add something to Kalshi's opening price |
| **entry** | The 2,008-cell pre-registered sweep, re-run on a longer history |
| **exit** | Hold to settlement, priced at the ask |
| **size** | Fixed |
| **what would make it wrong** | The sweep again finds fewer discoveries than its own shuffled-label null — which is exactly what it found on 29 days |
| **suggested by** | `bot-forensics`, which asked for this itself |
| **date** | 2026-08-20 |

**Why the closure was wrong.** B023 is recorded **SETTLED (null)**. The project
that produced it writes: *"B023 should be read as **'not demonstrated on 29 days
of form data'**, not 'player features cannot work.'"* On that window the median
player appears about **three times** and head-to-head reached **1.2%** coverage.

**What the original test did NOT cover:** a history long enough for "form" to
mean anything.

> **The enabler is a purchase and it is the user's.** `livetennisapi`'s history
> plan, **$9.99**, 43 monthly periods, January 2023 → July 2026, point-by-point,
> including ITF. **It answers T002, S018 and B023 at once.**
>
> ⚠ **There is no free substitute.** `M016b` recorded a free ATP database as
> *"live updated"*; I opened it on 2026-08-14 and its most recent match is
> **2026-01-17** — four and a half months *earlier* than the frozen source it
> would replace.

**Cost:** $9.99 and one rebuild. **Blocked on the user.**

---

## RS-07 · The tennis buckets, on the labels that turned out to be free

| field | value |
|---|---|
| **id** | `RS-07` |
| **claim** | **S005** and **S006** (set1_overshoot) |
| **market family** | Kalshi tennis, in-play after set 1, sliced by time, tier and set-1 margin |
| **what it bets on** | That some *specific* slice has an effect big enough to clear the cost bar even though the pooled effect does not |
| **entry** | The existing bucket grid, re-run with the enlarged label set |
| **exit** | As configured |
| **size** | Fixed |
| **what would make it wrong** | The smallest detectable effect stays above the cost bar. **Report the floor per bucket — the grid already does and the summary rows dropped it** |
| **suggested by** | `reopen`; the label source found by `tennis` |
| **date** | 2026-08-20 |

**Why the closure was wrong.** S005 and S006 are recorded **SETTLED (null)** —
"0 of 25" and "0 of 10 clear the bar". **The same rows state their own detection
floor: 3.7–9.0 cents and about 9.9 cents, against a target of about 2.** The test
could not have seen the thing it reports absent.

**What the original test did NOT cover:** any effect smaller than roughly its own
floor, which is two to five times the effect being hunted.

> **What changed:** `tennis` refuted S018 on 2026-08-09 by finding
> `tennis-data.co.uk`'s **per-season** workbooks, which carry games won by each
> player **in every set** — free, reaching back years, so the plus-or-minus-7-day
> objection never applied. **1,062 labels against the 479 S006 used.**
>
> ⚠ **Their own three limits, kept:** not yet joined; **main tour only, against a
> Kalshi pool that is 73–87% ITF**; and 1,062 is 29% of the roughly 3,620 needed,
> which moves the floor from about **9.9 to about 6.6** — **still above the 3.61
> bar.** **"REFUTED, not resolved" is their wording and it is the right one.**

**Cost:** one re-run once the labels are joined. **Honest expectation: this
sharpens a floor; it probably does not clear a bar.**

---

## RS-08 · Does the market price the SCORE, rather than the price history

| field | value |
|---|---|
| **id** | `RS-08` |
| **claim** | **C106c** (kalshi-inplay-bot) |
| **market family** | Kalshi tennis, in-play |
| **what it bets on** | That the price diverges from the match state — an underdog has won a set and is still priced under 30 |
| **entry** | Forward only: on a live score feed, enter when the market state and the score state disagree by a stated amount |
| **exit** | Hold, and a laddered variant, both reported |
| **size** | Fixed, paper only |
| **what would make it wrong** | The divergence sits inside the cost bar, or it is an artifact of feed latency — which **B008** already measured at **97.4% of the repricing complete before the bot could see the score** |
| **suggested by** | `kalshi-inplay-bot`'s own ledger, about itself |
| **date** | 2026-08-20 |

**Why the closure was wrong.** The strongest negative artifact in that corpus
(**C001**: 14,162 settled markets, holdout touched once, random-entry control,
about 9 cents lost per trade) is, in that ledger's own words, *"all of C001–C007
concern **price-visible** information, which the market prices correctly. None of
it tests whether the market prices the **score** correctly."*

**What the original test did NOT cover:** the score. The candlestick feed does
not carry one.

> ⚠ **The least cheap and the most honest of the nine.** Score-aware testing was
> abandoned because the available point-by-point source's set-end timing is
> accurate only to **plus or minus 5–15 minutes**, *"too loose for entry rules"*.
> **And B008's 97.4% is a direct measurement against it.** The forward tape built
> for this ran **two days** and stopped.
>
> **It is written down because it is the one live untested thesis in a project
> everything else has been measured to death — not because it is cheap.**

**Cost:** forward time and a score feed. `tennis-paper-forward` is already the
right shape.

---

## RS-09 · Are the far wings tradeable on any day but one

| field | value |
|---|---|
| **id** | `RS-09` |
| **claim** | **C016** (crypto) |
| **market family** | The crypto ladders, strikes far from the anchor |
| **what it bets on** | That the cheap far-wing contracts can be entered and exited at all |
| **entry** | Measure first: at what rate does a **two-sided** quote exist at each distance from the anchor, across many days |
| **exit** | Not applicable until availability is established |
| **size** | Not applicable |
| **what would make it wrong** | The far wings are one-sided on most days, as they were on the one day measured |
| **suggested by** | `reopen` |
| **date** | 2026-08-20 |

**Why the closure was wrong.** C016 is recorded as a structural fact — *"the
cheap wings have an ask but no bid"* — and it is **61 minutes of one ladder on
one day** (2026-08-01, 11 strikes).

**What the original test did NOT cover:** any other day.

> ⚠ **Guard #24 applies directly and may kill it before it starts.** "The market
> does not quote a near-certainty" was measured across **seven sports**, and the
> far wing is the same object seen from the other side. **The honest expectation
> is that C016 is right and one day was enough.** `MORNING_REPORT.md` §0000
> already carries a *"Refinement, so this is not overstated"* paragraph confining
> it to the far wings and reporting about **78% two-sided** on the liquid core.
>
> **Ranked last of the nine for that reason.** It is here because the measurement
> is one day, not because the conclusion is likely wrong.

**Cost:** one query over recorded books.

---

# ⚠ THE DUDS — wrongly closed, and dead anyway

**A resurrection list that is not honest about its own duds is worthless.**
Eleven of the 48 are genuinely dead despite the closure being poorly reasoned.

| claim | why it is dead anyway |
|---|---|
| **S021** | Withdrawn by me. Effect **2.42 out of 100** against a **3.61** cost — more data sharpens a known loss. The bucket version needs about **61 weeks** of recording. |
| **K001** | The null is 25 markets and underpowered — but **K013 kills `KXBTC15M` structurally**: minted at the money on 99.86% of 6,261 markets, pinning entry to the peak of the fee curve. Dead on arithmetic, not on the null. |
| **K012** | "Killed on recurrence" is a mislabel — but **22–48 settlements ever** against the **481** needed means it can never be validated at all. Unmeasurable is not the same as no-edge and it is just as final. |
| **M011** | 13 games, one snapshot, a retail book — but `RESULTS_DEVIG_WHERE` has since measured **1,460 paired observations on 30 games**, largest venue disagreement anywhere **2.77 cents against a 2.75 cent cost**. Settled properly since. |
| **C088** | "Rejected" on **0 accepted entries** is a null-by-no-data — but **C079** measured the thing underneath: informed flow is real and **dies inside 15 seconds**, against a roughly **66-second** public visibility delay (**C089**). Unreachable. |
| **C011, C012** | The live bot's two gates, fitted to about 25 and 137 observations. **Not strategies to resurrect — broken parameters in a dormant bot** whose whole family loses about 9 cents a trade (C001, B009, B010). |
| **C082, C083** | Real unfixed defects — in a copy-trading pipeline that **C077** already killed at 42,652 wallets with **0 discoveries and fewer nominally-significant wallets than chance predicts**. |
| **SO006** | The soccer selection canary. **Closed by retention, not evidence** — the matches fell out of Kalshi's roughly 69-day window and **cannot be rebuilt.** The generalised version was run instead (SO040/SO041). |
| **C001, C002** | Arb from 10.5 minutes — but the mechanism is structural: a 75-leg ladder carries a **roughly 1.9 cent fee floor**, so a violation must exceed about 2 cents to be worth anything and none did across **1,083 scans** (K007: 52 violations, **0 with tradeable size**). |
| **M027** | The ITF **data** claim was false and is corrected — but the **trade** is not unlocked. **B009** measured ITF as the worst tier of any: **−9.13 cents a trade on 6,135 trades**, with an untouched holdout agreeing. Data availability reopened; economics did not. |

---

# THE 28 THAT WERE NEVER STRATEGIES

Listed so nobody counts them twice. Every one is a real finding and **none of
them is a bet**: BH014 · C066 · SO014 · M009 · M010 · S022 · C009 · C010 · C042 ·
C106b · C117 · M015 · M016b · M017 · SO001 · T003 · T018 · S018 · T002 · B015 ·
BH010 · C025 · C105 · SO038 · C088 · K001 · K012 · M011 (the wording halves of
the last four).

They are wording fixes, bug records, data-availability facts, and **enablers** —
S018 and T002 enable RS-06 and RS-07. **All 43 with an owner have already been
filed to that owner**; `src/check_delivery.py` fails if that stops being true.

---

# HOW THIS SPLITS WITH `factory`, so nothing is written twice

**`reopen` writes specs ONLY from claims already in the ledgers.** Nine, above,
ids `RS-01`–`RS-09`. **It will not generate new ideas** — that is Stage 2's job
and this chat has no business doing it.

**`factory` should not re-derive any of the nine.** If a factory spec lands on
the same family it carries a different mechanism, or it cites the `RS-` id.

**Second job accepted:** `reopen` audits factory specs on arrival, the way it now
audits claims on arrival — each against the guards, against the 612 recorded
claims, and against the dud list above. **Volume is exactly when a bad premise
slips through.**

---

# 2026-08-20 — the second job started immediately: 31 factory specs audited

The factory had already written **31 specs**, so the audit-on-arrival job was not
waiting after all. New tool: **`src/audit_specs.py`**, read-only and repeatable.

**The specs are good.** SF002 names C014's retraction and is built not to repeat
it. **SF006 handles K012 exactly right** — it does not claim economics markets
have an edge, it says they were never recorded, and it drops the idea as
**unmeasurable rather than unprofitable** if the settlements do not accrue.
SF110 and SF111 are nulls written up as specs **so the factory does not
re-derive them as ideas**, which is the best structural decision in that folder.
**SF005 and RS-01 are the same claim and SF005 credits `reopen`** — the split
works.

## The one substantive catch

**SF004's thesis is the favourite-longshot bias.** It cites **B024** and states
the difference precisely — *"B024 bought at the ASK as a taker; this never
crosses"* — which is the best prior-work note in the folder.

**B024 is the favourite side. The long-shot side was measured on Kalshi and is
not cited:** **K009** (762 settled matches, aggregate **−0.67 out of 100**
against a 2.72% overround) and **B027** (tradeable books, **0 of 10 bands
deviate**).

⚠ **The caveat that stops this being a kill:** **K010** is marked OVERSTATED —
bucket ranges **±11 to 29 out of 100**. K009's *aggregate* carries the weight;
the *per-band* question is underpowered. **SF004 may still deserve screening; it
should say so rather than omit K009.**

## And a correction to this chat's own screen

The first version of `audit_specs.py` flagged **any** entry band reaching 90c and
caught **28 of 31** — useless, because most specs carry a wide "any price" band.
**Sharpened to narrow-and-extreme it catches two, and both are real** (SF004 at
3–15c, SF101 at 88–96c). **The first number would have been a frightening
headline that meant nothing**, and it is the same mistake as reading the set-1
grid's interval column without checking what it measured.
