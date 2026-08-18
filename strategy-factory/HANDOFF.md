<!-- COORDINATOR-STATE
doing: recorder LIVE since 2026-08-18 05:14 UTC - now 55 families at full order-book depth and 3,438 at top of book, against the 19 recorded before; 17 strategy specs written, one for every testable category
left: build the screening engine with its placebo arm; then answer four unchecked assumptions that could void four specs outright, from rules text already on tape
needs: yes - which markets does he actually know something about that the numbers would not tell us? Not which he likes - which ones behave differently, and why. It is the one input this repo cannot generate and all three other idea sources are already running.
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
- **17 strategy specs**, validated, across three of the four required sources and **every one of the 13 testable categories**.
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
