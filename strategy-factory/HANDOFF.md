<!-- COORDINATOR-STATE
doing: recorder LIVE since 2026-08-18 05:14 UTC - 55 families at full order-book depth (European soccer and Valorant pinned on his own domain knowledge) and 3,438 at top of book; 22 specs, every testable category covered, 6 of them soccer built on his own answers
left: build the screening engine with its placebo arm; then answer four unchecked assumptions that could void four specs outright, from rules text already on tape
needs: no - his six soccer answers arrived and are all turned into specs. Next question comes after the screening engine produces something to ask about.
-->

# HANDOFF — strategy-factory

**Session 1, 2026-08-18.** Started from
[`coordinator/prompts/SESSION-2026-08-18-strategy-factory.md`](../coordinator/prompts/SESSION-2026-08-18-strategy-factory.md).

---

## Where this got to

**Stage 1 (WIDEN) is the whole session, because it is the only irreversible
one.** Kalshi's history window is roughly 69 days and rolling; a closed market
404s forever. Strategy work in September is limited by what got recorded this
week, so nothing else was allowed to go first.

### Measured, in this order

| | |
|---|---|
| Kalshi series listed on the exchange | **13,133** |
| series with at least one open market | **3,439** |
| open markets, exchange-wide | **~785,000–835,000** (it churns) |
| of which two combinatorial parlay families | **751,943 — about 90%** |
| `bot-hunt` records | **19 series at full depth** |

**The parlay finding is the one that changes the plan.** Ninety per cent of the
exchange's open markets are `KXMVECROSSCATEGORY` and
`KXMVESPORTSMULTIGAMEEXTENDED`, multi-leg products that almost never carry a
counterparty. Any "record everything" design drowns in them. Dropped by
measurement *and* by name, with the count written out in `reports/TIERS.md`,
because a family silently missing from a recorder is indistinguishable from a
family that does not exist.

### The measurement that made breadth affordable

`bot-hunt/src/venues.py` states as an inherited trap that Kalshi's list
endpoints null out bid/ask. **They do not.** `/markets` carries
`yes_bid_dollars`, `yes_ask_dollars`, `yes_bid_size_fp`, `yes_ask_size_fp` for
up to 1,000 markets per request, and on 168 markets across 23 series those
agreed with the per-market orderbook on **100% of bids and 94% of asks**, with
**zero** cases of the list being blank while the book was quoted.

| | per-market orderbook | list endpoint |
|---|---|---|
| markets per request | 1 | up to 1,000 |
| one pass over every open market | **~81 hours** | **~10 minutes** |
| gives depth | the whole ladder | top of book only |

Full method and the one place it fails: `reports/RESULT_LIST_QUOTES.md`. Filed
to `devig` as mailbox 021 and answered in `STATUS.md`.

---

## What is built and passing

- **`src/census.py`** — every series, every open market, one orderbook probe
  per live series.
- **`src/shape.py`** — two full exchange sweeps, measuring what carries a quote
  and how much moves between them, so the recorder's disk cost is arithmetic
  rather than a guess.
- **`src/tiers.py`** — builds the recorder's tier list from those measurements
  and writes the drop list in full.
- **`src/wide.py`** — the two-tier recorder. Own database, own single-instance
  lock, change-only writes with a forced heartbeat.
- **`src/verify_list_quotes.py`**, **`src/bestofn.py`**, **`src/spec.py`**,
  **`src/seed_specs.py`**, **`src/categories.py`**,
  **`src/seed_specs_breadth.py`**.
- **`PREREGISTRATION_HOLDON.md`** — the soccer descendant, sealed before any 2026/27 European price exists.
- **`QUESTIONS_FOR_HIM.md`** — six specific soccer questions, batched.
- **22 strategy specs**, validated, across **all four** required sources and **every one of the 13 testable categories**. SF018-SF022 come from his own domain knowledge.
- **15 tests passing**, including a paper-only guard extended to scan
  `bot-hunt/src/venues.py` (which runs inside this process) and a local
  GUARD #23 field-name check with the real bug as its planted violation.

---

## THE RECORDER IS RUNNING — launched 2026-08-18 05:14 UTC

**Two processes, two database files, registered in both registries.**

| | tier A — depth | tier B — breadth |
|---|---|---|
| what it stores | the **whole order-book ladder**, both sides, as JSON | top of book with sizes |
| families | **55** that `bot-hunt` does not record at depth (36 before the category quota) | **3,438** on tape |
| cost per cycle | 1,200 requests, **measured 1,172 ladders in 378 s** | ~785 requests, **measured 883-1,533 s** |
| interval | 600 s | 1,800 s |
| database | `data/wide_depth.db` | `data/wide_top.db` |

**Two files, not one, and it is a hard constraint rather than a preference:**
two writers on one SQLite died here with `database is locked` inside 19 minutes
on 2026-08-09, and `kalshi_cycle` holds one write transaction for 340–1,400 s.
Analysis joins them with `ATTACH`, which costs nothing.

**Registered as `factory-wide-depth` and `factory-wide-top` in BOTH**
`runners/runners.json` and `coordinator/runners.json`. The two lists were
compared after editing and agree in both directions. `devig`'s recorders died
four times for want of exactly this, the last for **19 hours** after a reboot.

**After 18 hours, off the tape rather than predicted: 1,010,740 top-of-book
rows across 3,438 families and 144,558 distinct markets, plus 99,949 full
ladders.** Every category that had nothing now has tape. Sports is about one
market in two and one family in four — it used to be everything. Measured disk:
**about 20 GB a month**, against the 40 GB limit written into
`PREREGISTRATION.md` §5 before any of it ran. Read back and spot-checked in
`reports/RECORDER_LIVE.md`: **85,498 snapshots, not one crossed book.**

### What it is NOT doing, and why

**It is serial.** `devig` measured that a concurrency pool of 8–10 would fix
their recorder's overrun, and they are right. **This one stays serial anyway**,
because their own warning applies harder here: the 15 requests/second ceiling is
*recorded, not verified*, my process shares the unauthenticated quota with the
one holding 65 GB that cannot be re-pulled, and breadth here comes from one
request per **sweep** rather than per market — so the rate is not where my
headroom has to come from.

---

## ⚠ MAILBOX 001 WAS MISSED AT THE START, AND TWO OF ITS WARNINGS HAD COME TRUE

`coordinator/mailbox/factory/` did not exist when this session checked, so it
concluded there was no mail. **The message landed at 00:33 while work was in
progress**, and the folder's README was created at 01:01 **without listing the
directory again** — writing a README into a folder holding an unread
instruction. Read and answered at the end; `Status: DONE`.

It names one failure mode in his own words: *"I tell the factory chat to find me
a bunch of strategies. Instead we'll end up doing it to find me one really good
market and find all the strategies within that market."* **It had already
happened twice by the time it was read.**

**In the recorder, which is the version I had not thought of.** Tier A allocates
full order-book depth on a single score. The first allocation gave
**Financials 12 slots and Sports 8, and ZERO to crypto, weather, politics,
companies, science and mentions** — and crypto settles in minutes, weather
same-day, making them the two fastest categories to get a real answer from.
Fixed with a per-category quota in `tiers.py`. Now **55 families**, largest
category holds 5, measured at 1,172 ladders in 378 s inside a 600 s interval.

**In the specs.** 8 specs across **4 of 13** testable categories. Fixed by a
breadth pass, SF009–SF017, one per uncovered category. `spec.py --coverage`
now **exits non-zero** while any testable category has zero, so this cannot
silently recur.

**Three artefacts now enforce breadth instead of intending it:**

| | |
|---|---|
| `reports/CATEGORIES.md` | every category, a verdict, and a **written reason** — including for the hopeless ones, because a category dismissed without a reason is one that was skipped |
| `reports/VARIABLES.md` | what could move the price in each category, written **before** SF009–SF017. Anything added after a result gets a dated `LATE:` tag; there are none |
| `reports/COMPLETENESS-01.md` | what was not covered, and what becomes next cycle's work |

**Four assumptions are named as unchecked and two can void a spec outright** —
whether Kalshi's NFL spread has a push (kills SF009), whether more than one
person can be pardoned (kills SF012), whether Pyth is free (SF013), and whether
company KPI ladders are one observation per earnings report (SF015). All four
are queries against `w_names.rules_primary`, already on tape.

---

## ⚠ WHAT IS NOT DONE, stated plainly

1. **No strategy has been screened.** Stage 3 does not exist yet. That is
   deliberate — the gates in `PREREGISTRATION.md` section 6 have to pass first,
   and gate 4 (a placebo arm run once on real tape) needs tape that only
   started accruing tonight.

2. **The screening engine has no code.** Next session's first job. It must
   carry the placebo arm in its first commit, not added later.

3. **The disk projection in `reports/SHAPE.md` is a projection.** Replace it
   with the real `w_cycle` numbers after 24 hours. On the measured change rate
   (2.5% of markets move in 300 s) the whole exchange at this cadence is well
   under a gigabyte a day, and `devig`'s correction — Kalshi is 0.53% of every
   row in their 65 GB — says disk was never the wall for Kalshi book data.

4. **Nobody has checked what the recorders do to each other's request rate.**
   `w_health.http_ok` and the non-200 rate are the numbers to look at, and the
   first person to look should look there rather than at cycle time.

---

## MAIL 002 AND 003, ANSWERED 2026-08-19

**002 — my best-of-N correction was itself wrong, and my diagnosis was worse.**
`coordinator` did the arithmetic exactly; I reproduced it before accepting it.
**The exact figures are 1 in 4,893 and 34 in 100.** The plan said 1 in 10,000
and 37; I said 1 in 2,289 and 58. **Everyone was wrong once.**

The error is the **denominator**, not the fee: buying at 50c takes **52c** out
of the account, so +30% needs **68** wins of 100 rather than 67, and one win
halves the answer. Verified at 1, 5, 20 and 100 contracts per order.

⚠ **And the part that matters more than the number.** I wrote that the plan's
figure *"can only be reproduced by charging the fee twice"*, because doing so
gives 1 in 10,920 — close enough to be convincing. **It is not what happened**;
theirs was a Monte Carlo estimate off two hits in 20,000 runs. **I found *a* way
to reproduce a number and asserted it was *the* way**, which is this repo's
recorded failure mode wearing the costume of a verification. `bestofn.py` now
prints the **hit count** beside every simulated tail and says out loud when it
is too small to trust — their fix, not mine. Corrected inline in `LEDGER.md`
F002 (PARTLY RETRACTED banner), `DECISIONS.md` D6, `STATUS.md` and `BRIEF.md`.

**What survives is better than either wrong version:** the user's own claim is
**right at the true number**. One strategy picked in advance showing +30% over
100 bets is about 1 in 4,893 — genuinely not luck. The danger is entirely in
the picking.

**003 — his domain knowledge, and it does not point where this repo works.**
Soccer most of all (*"everything Europe related, I know"*), tennis's format but
not its players, Valorant as his only esport, and baseball *"literally close to
nothing"* — which is where the live money is.

- **`KXUCLGAME`, `KXEPLGAME`, `KXVALORANTGAME` pinned to the full-depth tier**,
  each with its reason written beside it in `tiers.py`. Confirmed on tape within
  one cycle: 21, 25 and 25 ladders. Pins are taken **before** the category
  quota, so they displace score-filled families and can never displace a
  category's guaranteed share — and `reports/TIERS.md` says which three went.
- **Not duplication of `bot-hunt`.** Its EU recorder stores `depth5_*`, a
  *summary*; tier A stores the whole ladder level by level, which is exactly
  what `soccer/CLOSED.md` item 2 was blocked on.
- **`SF018` + `PREREGISTRATION_HOLDON.md`** — the one live descendant of the
  closed soccer work, pre-registered **before** any 2026/27 European price
  exists, with the selection effect named in section 0 and the fee (nine times
  bigger at this end of the book) named as its likeliest killer.
- **`QUESTIONS_FOR_HIM.md`** — six specific questions, batched.
- **Nothing was narrowed onto soccer.** Soccer went from 1 spec to 2 of 18; the
  depth tier went from 55 families to 55. The pins displaced, they did not
  expand.

---

## MAIL 004 — HIS SIX SOCCER ANSWERS, AND THEY CAUGHT A SPEC I HAD WRITTEN WRONG

**The headline is that three of his six answers say the same thing: the variable
is the CLUB, not the league table.**

> *"Real Madrid's the type of team that if they score the first goal, they're
> gonna keep trying to score. But Manchester United, it's very likely that if
> they score the first goal, they're gonna park the bus no matter who they're
> playing against."* — and *"a better team with better players will sometimes
> park the bus even playing against the worst team."*

**`SF018` was written on top-third / bottom-third of the domestic table.** A
league-wide average mixes clubs that do opposite things to the price of the side
that is ahead, and would have reported a null. **That is the repo's most
expensive recorded mistake — a sweep over price and market features used to
close a question about individual players — arriving in a new sport**, and the
only reason it is a correction rather than a retraction is that **no number
existed yet.**

Recorded as **amendment A2** of `PREREGISTRATION_HOLDON.md`, numbered and dated,
old wording left visible. **A2 also names what the change costs:** the sample
shrinks to each club's own matches; clubs with no history are **excluded and
counted as excluded**, never defaulted to the league average; and the label is
built from matches **before** the traded match only, or it is look-ahead. New
drop rule — if the label cannot be built for 60 of 100 fired matches, the answer
is **UNMEASURABLE**, not negative.

### All six became specs, and both "I don't know" answers did work

| his answer | spec |
|---|---|
| Q1 rotation · Q2 fixture load | **SF019** — measures games in the last 10 days, **not** line-up changes |
| Q3 per-club behaviour | **SF018 v2** |
| Q4 *"I have no idea"* | **SF022** — the seven-competition comparison, ours to answer |
| Q5 line-up news | **SF020** — a diagnostic, because he hedged it himself |
| Q6 goals and player stats | **SF021** — his Arsenal rule as written |

**Q1's most skippable sentence is its most useful:** *"They might put the same
team though. It might not put them at full effort."* A line-up-based variable
scores that match as full strength and is **wrong**, so SF019 measures fixture
load instead. His season gradient — near zero early, growing as the table
settles — is written in as a **prediction stated in advance**, which tests his
rule rather than tuning a parameter.

**Q2 is where he pre-empted us**, warning unprompted that the obvious version
(already-qualified teams rest players) is wrong. **A domain expert telling you
your unwritten spec is wrong is worth more than a confirmation.**

`KXEPLTOTAL` and `KXUCLTOTAL` pinned to full depth. **No baseball player-prop
spec written** — `devig` has a free kill-test running on exactly that, and
`STATUS.md` offers to stay off it or take a piece.

**⚠ And one relayed number that is two measurements.** `KXMLBTOTAL` as *"2,212
tickers"* against my census's 165: `bot-hunt` has **2,469 cumulative tickers ever
seen**, 165 **open right now**. It matters for sample size — a totals ladder is
~11 strikes on one game, so 2,469 tickers is on the order of **225 games**. That
is LEDGER K003 exactly. `SF021`'s unit is the **match**.

**Nothing narrowed.** Soccer went from 2 specs to 6 of 22; the depth tier stayed
at 55 families. Coverage still 13 of 13.

---

## The judgment calls, in one line each

Full reasoning and the rejected option in `DECISIONS.md`.

| | |
|---|---|
| **D1** | Work only in `strategy-factory/`. `bot-hunt` read, never written. |
| **D2** | Import `venues.py` rather than copy it — and extend the paper-only test to scan it. |
| **D3** | Breadth from the list endpoint, depth from the orderbook, never mixed. |
| **D4** | Change-only writes, with a heartbeat so "quiet" and "dead" stay distinguishable. |
| **D5** | The two parlay families dropped by name as well as by measurement. |
| **D6** | The best-of-N table re-derived here, and it disagrees with the plan. |
| **D7** | No virtual environment — **reversed the same day.** The shared watchdog's registry takes an interpreter path and there is no way to register `py -3`, so `.venv` exists purely so the recorder can be restarted automatically. |

**One more, taken after reading `devig`'s section in `STATUS.md`:** their
arithmetic that a concurrency pool of 8–10 would fix the existing recorder is
right, and **this recorder is still serial anyway.** Their own warning is the
reason — the 15 requests/second ceiling is *recorded, not verified*, and my
process shares the unauthenticated quota with the one holding 65 GB that cannot
be re-pulled. Breadth here comes from one request per **series** instead of per
market, which needs no extra rate at all.

---

## Two corrections this session owes the repo

**1. The best-of-N table in `coordinator/STRATEGY_FACTORY.md` understates the
danger by about four times.** Re-derived by simulation and by an exact binomial
tail, which agree:

| | plan | measured here |
|---|---|---|
| one zero-skill strategy reaches +30% over 100 bets | 1 in 10,000 | **1 in 2,289** |
| best of 2,000 reaches +30% | 37 in 100 | **58 in 100** |

The plan's figure needs the fee charged twice. `common/kalshi_fees.py` says
`exit_cents=None` means held to settlement and pays the entry fee only, and
Kalshi charges nothing at settlement. **This strengthens the plan's conclusion
rather than weakening it**, which is exactly why it had to be said out loud —
a load-bearing number that is wrong in the comfortable direction is the kind
nobody re-checks.

**2. I read the dead Kalshi field names on the first census run and the
repo-wide guard did not catch me.** `volume_dollars`/`volume` are both absent;
the live names are `volume_fp`, `open_interest_fp`, `liquidity_dollars`. Every
volume in the first census came back null and printed as `0`, which reads as a
finding about the exchange.

**The gap is worth someone's attention:**
`common/scan_legacy_kalshi_fields.py` classifies a file as venue-reaching if it
has a URL literal, calls `.json()`, or imports a known venue client. This folder
reaches Kalshi via `sys.path` plus `import venues`, which matches none of the
three, so it was scored as not touching the wire. **Any folder that imports a
sibling's client that way is invisible to GUARD #23.** Defended locally in
`tests/test_live_field_names.py`; the repo-wide fix is `common/`'s.

**Separately, `common/tests/test_no_legacy_kalshi_fields.py` is RED and it is
not this folder.** 13 unadjudicated files across `bot-hunt`, `crypto`,
`kalshi-market-scan`, `livedesk`, `market-selection`. Verified by running the
scanner and grepping for `strategy-factory`: zero hits.

---

## THE ONE THING NEEDED FROM THE USER

Three of the four idea sources in the plan are running: my own reasoning about
market structure (5 specs), the extractors (1 spec, from a GitHub repo read in
full and a YouTube method with timestamps that independently describe the same
mechanism), and the `reopen` chat's claims closed for the wrong reason (2
specs).

**The fourth is his domain knowledge, and it is the only input this repo cannot
generate.** The specific ask, which is deliberately narrow so it can be
answered in a couple of minutes on a phone:

> **Which markets do you actually know something about that the numbers would
> not tell us?** Not "which do you like" — which ones do you know behave
> differently. A league where the favourite means something different. A
> competition where teams stop trying once they are through. A time of day when
> the price moves for a reason that is not news.

Everything else proceeds without him. He does not need to answer before the
recorder runs, and the recorder does not wait on him.

---

## Next session, in order

1. **Launch the recorder.** Tiers, dry run, run. Register in both registries.
2. Confirm from `w_cycle` after 24 hours what the tape actually costs per day,
   and replace the projection in `reports/SHAPE.md` with it.
3. Build stage 3, the screening engine, **with the placebo arm in the first
   commit** — real bid, real ask, real fees from `common/kalshi_fees.py`, and
   entry priced by walking the recorded ladder.
4. Re-derive the no-skill range machinery the way `tennis` prints it for all 17
   of its bots, so a forward result never appears without one beside it.
5. Check `coordinator/mailbox/factory/` — it did not exist until this session
   created it.
