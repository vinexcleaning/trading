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
