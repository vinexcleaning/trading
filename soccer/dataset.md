# dataset.md — the joined match dataset

Built 2026-08-02. Artifact `data/dataset.json`, script `src/build_dataset.py`,
output `reports/dataset_build.txt`.

**160 matches**, one row each, spanning Liga MX, Argentina Primera, Copa do
Brasil, Colombia and MLS over 2026-05-24 → 2026-08-04 (Kalshi's ~69-day window).

---

## Structure: every feature carries a knowability stamp

Each feature is `{"value": …, "known_at": …}`. `assert_knowable()` refuses any
feature whose `known_at` is not **strictly before** the decision point, which is
set to **kickoff**.

**480 assertions, 0 violations.**

That is after the guard caught a defect in my own construction: the first
version stamped the closing line's `known_at` as the decision point itself and
**159 of 480 assertions failed**. They were right to fail — `known_at ==
decision_at` is not "known before". The bug was sloppy stamping, not a real
leak, and the fix was to stamp when the value was genuinely available
(kickoff − 10 min). Worth recording that the assertion earned its place on the
first run.

---

## Coverage — honestly

| Feature | Present | % of 160 |
|---|---|---|
| ESPN match identity + timeline | 160 | **100%** |
| Kalshi market tickers + results | 160 | **100%** |
| In-play events (goals/reds with price) | 97 | 60.6% |
| Final score | 53 | 33.1% |
| **Closing line** (`AvgCH/D/A`, de-viggable) | 53 | **33.1%** |
| **Pinnacle close** (`PSCH`) | **0** | **0.0%** |

Per league:

| League | Matches | With closing line | % |
|---|---|---|---|
| usa.1 (MLS) | 52 | 28 | 53.8% |
| mex.1 (Liga MX) | 28 | 12 | 42.9% |
| arg.1 (Argentina) | 43 | 13 | 30.2% |
| **col.1 (Colombia)** | 25 | **0** | **0.0%** |
| **bra.copa_do_brazil** | 12 | **0** | **0.0%** |

**A feature present on a third of matches is nearly useless and is labelled as
such.** The two 0% rows are structural, not accidental: football-data.co.uk has
no Colombian file (the `COL` code serves Poland), and Copa do Brasil is a cup
whose matches are absent from the Serie A file. The gaps *within* MEX/ARG/USA
are recency — the football-data file ends 2026-07-27 while Kalshi fixtures run
to 2026-08-04.

---

## ⚠ Pinnacle is gone from the 2026 data — a retraction of my own claim

`market-selection/SHORTLIST.md` ranked South American soccer first partly on
"free Pinnacle CLOSING odds, backfillable to 2012: Liga MX 4,437 matches,
Argentina 5,928, Brazil 5,275, MLS 5,800". Measured properly:

| League | 2022 | 2023 | 2024 | 2025 | **2026** |
|---|---|---|---|---|---|
| MEX | 100% | 99.4% | 99.4% | 90.0% | **0.0%** |
| ARG | 100% | 100% | 99.8% | 91.2% | **0.0%** |
| BRA | 100% | 100% | 100% | 88.4% | **0.0%** |
| USA | 100% | 100% | 100% | 97.2% | **0.0%** |

In the Kalshi window (≥ 2026-05-24) Pinnacle is present on **0 of 139** rows.

**This is LEDGER T014 happening again to a different site.** T014 recorded that
tennis-data.co.uk stopped carrying Pinnacle in 2026 and the real benchmark
became the Betfair close. football-data.co.uk has now done the same for
football. The historical claim is true; the claim as it applies to *the window
where Kalshi prices exist* is false.

**`AvgCH/AvgCD/AvgCA` (market-average close) is 100% populated**, including all
139 window rows, and is used instead. It is a consensus line rather than a sharp
one, which makes it a weaker benchmark — a deviation from the average is much
less interesting than a deviation from Pinnacle.

---

## Sanity checks (Task 5) — descriptive only

### 1. Kalshi pre-match price vs the closing line — the join is sound

| | |
|---|---|
| n | **32** matches with both a de-vigged book price and a Kalshi pre-match mid |
| correlation | **r = 0.9593** |
| mean (Kalshi − book) | **+0.47¢** |
| median \|Kalshi − book\| | **1.12¢** |
| p90 \|Kalshi − book\| | 3.95¢ |

The join is sound. And the result carries a second meaning the shortlist should
absorb: **Kalshi's soccer price sits a median 1.12¢ from the consensus close,
against a ~2.0¢ cost bar.** That is the same pattern as LEDGER T012 (tennis) and
this project's MLB moneyline measurement (0.37¢) — now on a third sport.

### 2. Home advantage

| League | n | Home win | Draw | Away |
|---|---|---|---|---|
| arg.1 | 13 | 61.5% | 23.1% | 15.4% |
| mex.1 | 12 | 50.0% | 8.3% | 41.7% |
| usa.1 | 28 | 64.3% | 17.9% | 17.9% |

Directionally right — home teams win most — but **n = 12–28 per league is far
too small to compare against an expected magnitude.** Liga MX's 8.3% draw rate
is implausibly low and is a small-sample artifact, not a finding.

### 3. Goal times, 15-minute buckets (n = 229)

| 0–14 | 15–29 | 30–44 | 45–59 | 60–74 | 75–89 | 90+ |
|---|---|---|---|---|---|---|
| 10.9% | 14.8% | 17.0% | **19.2%** | 13.1% | 16.2% | 8.7% |

Broadly as expected — rising through each half, a bulge around the 45–59 bucket
that absorbs first-half stoppage plus the start of the second. Nothing anomalous.

### 4. Does the price react to goals? Yes, unambiguously

229 goals, median move **+19.00¢**, positive on **94%**. Full description in
[inplay_events.md](inplay_events.md).

---

## ⚠ The selection canary is UNTESTABLE as built, and why

`GUARDS #1 check_selection` on the closing-line join returned **UNTESTABLE:
one arm is empty (with = 53, without = 0)**.

The reason is structural and is my construction's fault: the *outcome* I used
(final score) comes from **the same football-data row** as the odds. Every
match that has odds has an outcome and vice versa, so there is no "without"
arm to compare against.

Testing it properly needs an outcome from an **independent** source — ESPN's
final score, which is available on all 160 matches. That is a real gap, it is
cheap to close, and it is listed in `WHAT_IS_LEFT.md`. **Until it is closed, we
do not know whether matches with a closing line differ systematically from
those without**, and the 33% coverage makes that a live concern rather than a
theoretical one.

---

## What the dataset does not yet contain

Lineups, formations, referee, rest days, head-to-head and league position are
all **available** (see [data-sources.md](data-sources.md)) but are **not yet
joined onto these rows**. The pre-match recorder started this session is
accruing the live-only ones (lineups, referee) from now forward; the
backfillable ones (H2H, standings, rest) are derivable from data already on
disk and were not built for time.
