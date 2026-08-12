# PREREGISTRATION — MLB paper-only forward test

**Written 2026-08-07, before the runner produced a single decision and before
any settlement outcome existed on disk.** Nothing below was chosen after seeing
a result. Amendments go in §11 with their date and reason; the text above §11 is
never edited.

Related: [MENTALITIES.md](MENTALITIES.md) · [TARGET_CHOICE.md](TARGET_CHOICE.md)
· [../GUARDS.md](../GUARDS.md) · [../LEDGER.md](../LEDGER.md) ·
[../SCOREBOARD.md](../SCOREBOARD.md) ·
[../tennis-paper-forward/PREREGISTRATION.md](../tennis-paper-forward/PREREGISTRATION.md)
· [DECISIONS.md](DECISIONS.md)

---

## 1. What is being tested

**Sixteen bots** trade the same pool of Kalshi MLB games on paper. Five
mentalities × three exit modes, plus one no-trade control.

| mentality | target market | hold to settle | exit once | exit and re-enter |
|---|---|---|---|---|
| **M1 starter** — only *new* pitcher news | `KXMLBGAME` | `starter__hold` | `starter__exit-once` | `starter__free` |
| **M2 park+air** — elevation, temperature, wind out | `KXMLBTOTAL` | `park-air__hold` | `park-air__exit-once` | `park-air__free` |
| **M3 bullpen** — rest days and 3-day pitch load | `KXMLBTOTAL` | `bullpen__hold` | `bullpen__exit-once` | `bullpen__free` |
| **M4 early** — the window before the sharp line exists | `KXMLBGAME` | `early__hold` | `early__exit-once` | `early__free` |
| **M5 lineup** — latency around the lineup drop | `KXMLBGAME` | `lineup__hold` | `lineup__exit-once` | `lineup__free` |
| **control** | — | `control__no-trade` — logs the intended trade, takes none | | |

Every bot sees **the same pool of games** and enters **freely**: none is forced,
every bot may decline every game on any day, and a bot that declines everything
for a week is a valid outcome that will be reported as such.

**Target market is fixed per mentality, before any return exists**, and the
reason is in [TARGET_CHOICE.md](TARGET_CHOICE.md) §5: run-shaped information
goes to the runs market and winner-shaped information to the winner market.
Running every mentality against both markets would double the bot count to 32
and the joint denominator to 48 for no gain in mechanism.

**No money is involved and none can be.** No credential is read, no key file is
opened, no order endpoint is imported. `tests/test_paper_only.py` walks every
source file in this package and fails if order-shaped code appears.

---

## 2. The unit of observation

**A settled game.** Not a fill, not a tick, not a market row, and **not a
ladder rung**.

`KXMLBTOTAL` lists a median of **11 strikes per game** (measured; max 13).
Eleven rungs are eleven views of one run total, not eleven observations. GUARDS:
*a 10-strike ladder is one temperature reading, not ten markets.* Every
interval in this test is **clustered on the game**, and any per-market count
that appears in a report is labelled a market count, never an n.

`KXMLBGAME` lists two mirrored markets per game, one per club. They are folded
to one on **first ticker alphabetically** — never on volume, which is the
dedupe field that voided three phases of earlier tennis work (GUARDS #1).

**Expected rate:** ~15 games a day are listed; Kalshi carries 49 game-events
across 4 dates at any moment. A bot entering 30% of the pool accrues about
**4–5 settled games a day**.

---

## 3. ⚠ THE JOINT MULTIPLICITY CORRECTION — ONE DENOMINATOR OF 32

This is the part that is deliberately different from how the two tests would be
run separately.

> **There is ONE Benjamini–Hochberg family across BOTH forward tests, and its
> denominator is 32: sixteen tennis bots and sixteen MLB bots, at q = 0.10.**

`tennis-paper-forward/PREREGISTRATION.md` §6 declares a denominator of **16**
over its own bots. **That is superseded.** Correcting each test inside itself
and then reading the two results side by side is a 32-way search reported as two
16-way searches, and it is the exact error this repo has already recorded twice
(`wallet-copy-study` R5: testing against zero gave 54 of 206 "significant" in a
pure null; the paired test gave 0 of 249).

Consequences, all of them accepted in advance:

- **Cancelled, zero-entry and control bots stay in the denominator** as
  `CANCELLED` / `NO-ENTRY` rows. It cannot shrink because a bot never fired
  (crypto's convention, GUARDS #11).
- **Both tests are reported together or not at all.** A tennis result published
  alone under a 16-way correction would be reported at the wrong bar.
- **The denominator is 32 even if one test is stopped early.** Stopping a test
  after seeing its results and then dropping it from the denominator is the
  same error wearing different clothes.
- If either test later adds a bot, the denominator rises and **every previously
  reported p-value is recomputed**. It never falls.

Effective per-test α at the most conservative BH rank is **0.10 / 32 =
0.003125**, giving `z = 2.955` and a power constant `k = z_α/2 + z_β = 3.797`
at 80% power.

---

## 4. ⚠ THE HONEST POWER CALCULATION, STATED BEFORE THE RUN

**This test cannot decide whether any of these bots makes money. Not in a week,
not in a month, not this season.** Arithmetic, written here so the result
cannot later be read as a verdict.

Per-game profit per contract on a near-coin-flip market has
sd ≈ **50¢** (100 × √(p(1−p)) at p ≈ 0.5; MLB moneyline mids measured at a
median of 49.25¢, so this is the right regime, and it is *worse* than tennis's
45¢ because tennis in-play prices sit at 85–97¢).

| settled games per bot | MDE at α = .05 alone | **MDE under the joint BH across 32** |
|---|---|---|
| 20 | 31.3¢ | **42.5¢** |
| 50 | 19.8¢ | **26.9¢** |
| 100 | 14.0¢ | **19.0¢** |
| 200 | 9.9¢ | **13.4¢** |
| 500 | 6.3¢ | **8.5¢** |
| 2,000 | 3.1¢ | **4.2¢** |

The measured cost to enter and hold to settlement on both `KXMLBGAME` and
`KXMLBTOTAL` is **3.0¢**. So:

> **To resolve an edge the size of the cost bar, under the joint correction,
> needs about 4,004 settled games PER BOT.** At 4–5 games a day that is roughly
> **two and a half years**. `bot-hunt` reached the same order independently by a
> different route: 4,356 events ≈ 1.8 seasons for a 5¢ edge.

**Therefore the P&L endpoint is pre-registered as UNTESTABLE.** It will be
reported with its interval and its MDE printed beside it, and the word "works"
will not appear next to it. GUARDS #21: UNTESTABLE is a verdict about the test,
never about the effect.

---

## 5. What IS decidable — the primary endpoints

These are the gates. They are decidable because their variance is small, and
they are the questions this run exists to answer.

### P1 — Closing-line value against the de-vigged sharp line
**The primary endpoint.** For every entry, CLV = (de-vigged Pinnacle fair value
at the last observation before first pitch) − (the executable Kalshi price the
bot actually paid), in cents, signed so positive means the bot bought below
where the sharp line ended.

**Why this and not P&L.** It is what the one relevant piece of external advice
in the whole corpus says: *"CLV is exactly the right metric — short-term ROI is
too noisy at 180 signals."* (r/Kalshi, on a 180-signal model.) And its variance
is roughly **an order of magnitude smaller** than settlement P&L, because the
outcome noise is removed.

**Power:** at sd ≈ 3¢, under the joint BH across 32, the MDE is **1.61¢ at
n = 50** and **1.14¢ at n = 100**; **n = 130 resolves 1.0¢.** This is the only
endpoint in either test that is properly powered inside a month.

**Gate.** A mentality is interesting if its mean CLV is positive with a
game-clustered interval that excludes zero under the joint BH, **and** exceeds
that bot's own realised entry cost.

**Pre-registered prediction, as a number so it can be wrong:** every bot lands
between **−3.0¢ and +0.5¢**, and the modal result is a small negative equal to
about half the spread. Reason: [TARGET_CHOICE.md](TARGET_CHOICE.md) §4 measured
**0 of 20 moneyline and 0 of 38 totals markets** disagreeing with the de-vigged
sharp line by more than cost, with hindsight-picked bests of −1.82¢ and −1.63¢.
If Kalshi already *is* the sharp line, CLV is the spread you paid, negative.

**The one bot this prediction may be wrong about is `early`,** because that
measurement was taken where both books exist and `early` trades where only one
does. If any bot has positive CLV it should be that one, and if a bot other than
`early` has positive CLV, suspect the CLV timestamp before celebrating.

### P2 — Is the early window real?
Paired, per game: (de-vigged Pinnacle fair at first appearance) − (Kalshi mid at
T−48 h), and the same at T−24 h, T−6 h, T−1 h.
**Gate:** report the paired mean and its game-clustered interval at each lead.
**Pre-registered prediction:** the mean is indistinguishable from zero at every
lead, and its *dispersion* falls monotonically as first pitch approaches. A
non-zero mean at T−48 h that vanishes by T−6 h is the only shape that supports
M4, and it is not what I expect.

### P3 — Does Kalshi lag the lineup drop?
For every game where a lineup posts while the runner is watching: the Kalshi
mid at the last tick before the card appears, and at +1, +5, +15 and +60
minutes.
**Gate:** report. This is a measurement of the market, not of a bot, and it is
decidable at n ≈ 30 games because the quantity is a price change, sd ≈ 2¢.
**Pre-registered prediction:** **no detectable move at +1 or +5 minutes** and a
move smaller than the 2.0¢ spread by +60. Kalshi's MLB book quotes 2.0¢ at the
touch with 68.5 contracts on it, which is not what an unwatched book looks like.
**If this comes back showing a large, slow drift after the card posts, that is
the single most interesting result this run can produce, and it should be
attacked before it is believed.**

### P4 — What does it actually cost to trade this market?
Realised round-trip cost per contract = entry fee + exit fee + spread paid +
measured slippage between the decision tick and the fill tick.
**Power:** sd ≈ 2¢, so under the joint BH the MDE is **1.07¢ at n = 50**.
**Pre-registered prediction: 2.5¢ to 3.5¢ for hold-to-settle** and **5.5¢ to
7.0¢ round trip**, consistent with the census. **A number below 2.0¢ is a bug
until proven otherwise** — it means the fill model has gone optimistic, which is
how a +14.4% tennis result became −24.3%.

### P5 — Does the brief exist for the games Kalshi lists?
Report, do not threshold: % of games with both probable pitchers announced at
each lead time; % with a usable park index (n ≥ 30); % with TAF coverage of
first pitch; % with a lineup posted at T−3 h; % with a Pinnacle reference.
**Pre-registered predictions:** probables ≥ 90% at T−24 h and **below 60% at
T−48 h**; TAF coverage **near 100% inside T−24 h and near 0% beyond T−30 h**
(a TAF is a 24–30 h product — measured); lineups **0% at T−12 h**; Pinnacle
reference **below 40% at T−48 h**. If probables come back above 90% at T−48 h,
suspect the schedule hydrate of back-filling rather than celebrate.

### P6 — Do the five mentalities differ, or is this one bot in five hats?
Pairwise Jaccard overlap of the sets of games each mentality entered, and the
correlation of their conviction scores.
**Gate:** report. Median pairwise Jaccard **below 0.5** means five instruments;
**above 0.8** means the labels are decoration and the 32-way correction is
measuring one thing many times.
**Pre-registered prediction:** `park-air` and `bullpen` overlap most (both trade
totals on the same games); `early` is near-disjoint from `lineup` **by
construction**, because they trade different windows of the same game and a
game entered early is not re-entered late by the same bot.

### P7 — Does the machinery survive unattended?
≥ 95% of expected ticks completed; zero double-runner incidents; the state file
resumes cleanly across at least one deliberate reboot; the two recorders already
running on the laptop untouched; and the heartbeat visible in one command.
**Pre-registered prediction:** pass — with the explicit note that
`bot-hunt`'s recorder **died for 2.5 hours with zero bytes in its error log and
nothing noticed**, which is why P7 is a gate and not an assumption.

---

## 6. Separating sizing skill from selection skill

| | metric | what it answers |
|---|---|---|
| **selection** | mean CLV and mean P&L per **contract**, every settled game weighted equally | did it pick well? |
| **sizing** | stake-weighted mean minus equally-weighted mean | did betting more on its better ideas help? |
| **sizing, direct** | corr(stake fraction, realised per-contract outcome), clustered on game | is its confidence informative at all? |

**Power on the correlation:** at n = 50 only |r| ≥ 0.39 is detectable at 80%
power; at n = 20, |r| ≥ 0.59. **Sizing skill is UNTESTABLE at this sample size**
and is reported as an estimate with its interval.
**Pre-registered prediction:** the sizing term is indistinguishable from zero
and its sign is a coin flip.

---

## 7. Secondary endpoint — the P&L, reported and not believed

For each of the sixteen MLB bots:

- mean profit per contract, **game-clustered** bootstrap 95% interval
- the same, stake-weighted
- n settled games entered, and the MDE at that n under the joint 32
- the **naive benchmark beside it**: buy the home side of every game in the pool
  and hold, and buy every `Over` rung nearest the Pinnacle main line and hold
- that bot's own realised cost bar at its own average entry price
- results split by **quoted spread bucket** (≤2¢ / 3–4¢ / 5–8¢ / >8¢), because
  the tennis "heavy favourite edge" was +1.18¢ where the spread was ≤2¢ and
  +7.92¢ where it was >8¢ — that shape is the spread, not an edge

Three-valued verdict per bot, never two:

| verdict | condition |
|---|---|
| **SURVIVES** | joint-BH-adjusted interval excludes zero **and** the point estimate clears that bot's own cost bar |
| **UNDERPOWERED** | interval includes zero but the point estimate is largely retained |
| **COLLAPSES** | the point estimate itself goes away |

**Pre-registered prediction:** every bot lands between **−10¢ and +2¢** per
contract, **no bot survives the joint BH**, and the modal verdict is
UNDERPOWERED. The archive is 55 strategies and 0 that work, with 45 corrections
of which every single one shrank the edge.

**Pre-registered prediction on the exit modes:** `hold` beats `exit-once` beats
`free`. The archive measured the same tennis signal at −2.29¢ held and −9.36¢
with a stop-loss and profit ladder attached, and the stop-loss alone moved one
test from +0.62¢ to −3.77¢. **If `free` wins, that is the most interesting
result this run could produce and it should be attacked, not published.**

---

## 8. Guards that must pass, or the run is void

| # | guard | how it is enforced here |
|---|---|---|
| — | **paper only** | no credential read, no key path, no order endpoint imported; `tests/test_paper_only.py` walks every file and fails on order-shaped code, and is itself run against a planted violation (GUARDS #9) |
| 1 | selection canary | the moneyline dedupe reads ticker order only; `tests/test_selection.py` asserts no outcome-bearing field is consulted |
| 2 | result leak | any market carrying a settlement `result`, and any game whose start is in the past, is filtered from the pool **before** any bot sees it; the count is logged every tick |
| 6 | exact-decimal fees | `common/kalshi_fees.py` only; `common/tests/test_no_fee_reimplementation.py` fails on a copy |
| 7 | **fill at the ask, never the mid** | the engine has no mid; the brief's field is `mid` and is used only for reporting, and `tests/test_no_mid_fill.py` asserts no fill path reads it |
| 8 | effective sample size | every interval clustered on **game**; ladder rungs are never counted as observations |
| 11 | one BH denominator | **32**, fixed here, before any result, across both tests |
| 12 | content-level health | % of markets carrying an ask, zero-ask count, stale-book count, asserted every tick |
| 13 | assert content, not the call | every upstream response is checked for the fields about to be read; `volume_fp` / `yes_bid_dollars` / `orderbook_fp` are the four renamed fields that have already produced silent zeros here |
| 18 | structural invariant | on `KXMLBGAME`, the two clubs' YES bids summing above 100¢ is impossible and is alerted; on `KXMLBTOTAL`, a lower rung priced **below** a higher rung is impossible and is alerted |
| 20 | **placebo** | the **mismatched-pair placebo** from `TARGET_CHOICE.md` runs on every reporting cycle. A wrong join manufactured 44% and 82% qualifying rates and edges up to +24.76¢. **Any positive result that does not clear its own placebo by a wide margin is a join error and is reported as one.** |

**Void conditions.** If the result-leak filter fires on a game a bot had already
traded, or if the placebo's qualifying rate is not far below the real one, the
run is void and restarted.

---

## 9. What would make me doubt a positive result

Written now, so it cannot be rationalised later.

1. **Any bot beating its cost bar on P&L at n < 500.** The MDE says that cannot
   be resolved; a "significant" result there is a fluke or a leak.
2. **A CLV result that is positive for a bot other than `early`.** §5/P1 explains
   why `early` is the only one with a mechanism for it. For any other bot, check
   the CLV reference timestamp first.
3. **A result that strengthens as the filter gets more precise.** GUARDS #10 —
   monotone strengthening is contamination until proven otherwise.
4. **`free` beating `hold`.** It contradicts the archive's measurement of the
   same mechanism twice.
5. **Any bot whose edge lives in wide quotes.** Split by spread bucket, always.
6. **A number landing suspiciously close to an archive number.** GUARDS #16 — go
   and find the line of code that put it there.
7. **`bullpen` or `park-air` beating Pinnacle.** Pinnacle prices baseball totals
   for a living with a $1,875 limit; a free API and a wind vector beating it
   should be assumed to be a bug in the wind vector.

---

## 10. Fixed parameters, declared before the run

| parameter | value | why this one |
|---|---|---|
| decision windows | T−48 h, T−24 h, T−6 h, T−3 h, T−90 min, T−30 min | one per mechanism; `early` may only act at T−48/−24, `lineup` only at T−90/−30 |
| poll interval | 300 s | a baseball line moves on discrete news, not continuously; faster buys nothing and costs politeness on a free public API |
| fill timing | the **next** tick's book | a decision cannot fill at the price that triggered it |
| pending intention max age | 900 s | across a restart, an old intention must not fill against a moved book |
| depth cap | 25% of shown top-of-book size | never consume size the book did not show |
| bankroll | $500 per bot, never topped up | a losing run shrinks its own sizing |
| stake fraction | 0.5% to 6% of bankroll | |
| Kelly | quarter | |
| take profit / stop | ±12¢ | symmetric, so the exit modes are not secretly directional |
| re-entry cooldown | 3,600 s | the live tennis bot re-entered a falling market after 24 s, three times |
| max entries per game | 2 (`free` only) | |
| **re-entry size cap** | **never larger than the first entry** | refuses the 12 → 20 → 32 martingale that cost −$7.56 in 50 minutes |
| max contracts per entry | 25 | |
| park index floor | n ≥ 30 games at the venue | below it the index is noise and `park-air` must decline |
| wind floor | TAF must cover first pitch | an observed METAR at T−24 h is not a forecast; `park-air` declines when `taf_covers_game_time` is false |
| conviction bars | set from the FIRST live tick's conviction distribution, with **zero outcome data available**, so that every bot can fire at all | recorded in DECISIONS.md with the distribution they were set from |

---

## 11. Amendments

*Each entry gets a date, a reason, and what it changed. The text above §11 is
never edited.*

### A1 — 2026-08-07. Two pre-registered predictions failed within hours. Both recorded, neither used to change a gate.

**§5/P5 predicted probable pitchers "below 60% at T−48 h."** Measured on the
first 13 briefs at that lead: **85%**. The prediction said that a high number
should make me suspect the schedule hydrate of back-filling rather than
celebrate. It was checked: `probablePitcher` comes off the schedule endpoint at
request time and carries no historical fill-in, and the 15% that are missing are
the games where the club genuinely has not announced. **The prediction was
simply wrong** — MLB clubs announce probables further ahead than I assumed.

**§5/P4 predicted 2.5–3.5¢ hold-to-settle.** Measured: **2.18¢**, made of a
0.50¢ spread paid, −0.02¢ slippage and a 1.70¢ fee.

> That number first came back as **1.68¢**, which tripped P4's own
> *"below 2.0¢ is a bug"* alarm. **The alarm was right and the bug was in the
> report, not the engine**: `report.py` was computing slippage and fees and had
> simply omitted the spread paid, which §5/P4's own definition names. The fill
> model was correct throughout — `_exec_price` pays the ask, and
> `tests/test_guards.py` proves it never touches a mid. Fixed, and recorded
> here because the guard catching the analyst rather than the engine is the
> case that usually goes unrecorded.

**Why 2.18¢ is still below the predicted range, and it is not an error.** The
prediction was built on the **population** median spread of 2.0¢
(`reports/market_census.json`). The realised spread paid is **1.0¢**, because
the bots **decline the wider quotes** — a wider quote makes their own net edge
fail their own cost bar. That is a genuine selection effect and it runs in the
*opposite* direction to the esports finding, where a strategy that had to trade
every qualifying event paid the mean rather than the median.

**Both numbers will be reported side by side**: the realised cost, which is only
available to a strategy allowed to decline, and the population cost, which is
what a forced strategy would pay.

**No gate, threshold, bar or denominator was changed by this amendment.**

### A2 — 2026-08-07. The tennis session ACCEPTED the joint denominator of 32, and corrected one of my numbers.

`dcc1a78`. §3's declaration stands and is now implemented on both sides:
`tennis-paper-forward` moved `N_HYPOTHESES` 16 → 32 in code, kept
`N_OWN_BOTS = 16` so each bot reports its MDE jointly and alone, and renamed its
output fields to `bh_pass_q10_of_joint32` so a stale reader cannot confuse the
two. Its amendment A3 records it. **Nothing in §3 changes.**

**One number of mine was wrong and is corrected.**
[../JOINT_MULTIPLICITY.md](../JOINT_MULTIPLICITY.md) said moving from 16 to 32
widens the MDE by *"about 8%"*. It is **6.2%** — verified three times now, from
`k(16) = 3.5760` against `k(32) = 3.7968`. The **tables** in both that file and
§4 here were always right; only that one line of prose was wrong. Struck through
there rather than deleted.

The correction makes the joint denominator **cheaper** than I advertised, so it
does not weaken the case for it. It is an accuracy fix on a **cost**, not on an
effect, and it does **not** belong in the programme's tally of 45 edge-shrinking
corrections.

**No gate, threshold, bar or denominator was changed by this amendment.**

### A3 — 2026-08-12. A DEFECT FIX to M1, found by another session, and the record is SPLIT at this instant.

**What was wrong.** §1 and `MENTALITIES.md` describe M1's third trigger as *"a
starter whose **last three outings** differ from his season line by more than
1.50 earned runs per nine."* **The code did not implement that.**
`starter_profile` computes `recent_era` from however many prior starts exist,
guarded only by `rec_ip > 0` — **one third of an inning qualified.**

So a pitcher with **one** career start and one bad outing produced a divergence
of 13.75, which at 2.75¢ per unit became a **41.7-cent adjustment**, and the bot
declared a 67-cent market worth 99. And the *same* pitcher was also charged the
debut penalty: **the debut flag exists because recent form is unreliable, and
the code then trusted recent form computed from that same single game.**
Double-counted, in opposite directions.

**The fix.** The form-divergence term now requires **≥ 3 prior career starts
AND ≥ 12 innings** behind it. A large divergence on less than that is recorded
as `form_divergence_IGNORED_only_N_starts` and contributes nothing.

**Why this is a defect fix and not a parameter tune**, which matters because
tuning after seeing a result is what §10 forbids: the pre-registered rule says
*three outings*. One outing is not three. The code was not doing what was
written down, and making it do so is not a choice about performance.

**Blast radius, measured rather than asserted: 3 of 44 recorded `starter`
entries** had the form term driven by a pitcher with fewer than three career
starts. (`livedesk` reported 9 of 43 *involving* a low-start pitcher; only 3
had the form term actually fire on one. Their number is the wider set, mine the
narrower cause.)

> **⚠ THE RECORD IS SPLIT HERE AND THE TWO HALVES ARE NEVER MERGED.**
> Entries before 2026-08-12 are **arm A** (uncapped, unfloored form term);
> entries after are **arm B**. Every future report shows both, separately, with
> their own n. Nothing is re-run and nothing is deleted. Merging them would let
> pre-fix results be laundered into a post-fix claim — and the point of
> splitting is that I changed a live test **after** seeing which bot was
> winning, which is a fact a reader must be able to see rather than a detail to
> smooth over.

**What is NOT changed, and is the user's call rather than mine.** M1 still has
**no ceiling** on the adjustment. A 41.7¢ adjustment on a market whose entire
range is 100¢ is arguably a defect in itself, but capping it is a **new
parameter**, not the implementation of something already written. Recorded here
as an open question instead of quietly added.

**No gate, threshold, bar or denominator was changed by this amendment.**
