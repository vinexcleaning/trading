# RESULTS_DEVIG.md — H11 feasibility. **No settlement has been touched.**

**2026-08-06.** Fills in the two numbers
[PREREGISTRATION_DEVIG.md](PREREGISTRATION_DEVIG.md) §9 deliberately left blank:
the **qualifying rate `q`** and the **event count**. Raw:
`reports/devig_power.json`, `reports/mlb_scope.json`.

**This file contains no return, no P&L, no win rate and no settlement outcome.**
`src/devig_power.py` never opens a `result` field. Everything below is a
property of two live price feeds and a fee schedule.

---

## 1. The headline is arithmetic, not statistics

**Kalshi's cost bar to take an MLB moneyline is larger than the entire vig being
removed from Pinnacle.**

| quantity | measured | source |
|---|---|---|
| Pinnacle MLB overround — **the whole thing de-vigging removes** | **2.01 pp** (p10 1.94, p90 2.36) | recorder, 304,383 moneyline rows |
| Kalshi `KXMLBGAME` quoted spread at the touch | ~~**2.0¢ median**, p90 7.0¢~~ → **1.0¢ median, p90 2.0¢** — see the box below | recorder, ~~12,720~~ **18,828** post-fix snapshots |

> ### ⚠⚠ THE 2.0¢ FIGURE WAS WRONG, AND IT WAS MY OWN CORRECTION. WITHDRAWN 2026-08-09.
>
> This file used 2.0¢ / 7.0¢ to "correct" `RESULTS.md`'s claim that `KXMLBGAME`
> is **1.0¢ at every lead**, on the grounds that its 1.0¢ came from candles and
> "the strategy pays the touch". **It is the other way round.**
>
> Those figures came from the **starved recorder** (BH014): `record.py` probed
> only the first 60 of 85–104 listed markets in Kalshi's undocumented order, and
> on MLB the ones it dropped were the **sooner-closing, more liquid** markets.
>
> | | snapshots | median | mean | p90 |
> |---|---|---|---|---|
> | pre-fix (what this file used) | 12,780 | 2.0¢ | 3.13¢ | 7.0¢ |
> | **post-fix** | **18,828** | **1.0¢** | **1.32¢** | **2.0¢** |
>
> Coverage evenness confirms the mechanism — snapshots per ticker p25 went
> **25 → 94**. **`RESULTS.md` was right all along.**
>
> *Against the tidy version:* the two windows are not the same population — the
> fix orders by `close_time` ascending, so post-fix deliberately skews to
> soonest-closing markets. **That is the correct population for a pre-match
> strategy**, which is why 1.0¢ is the number to quote, but neither figure is
> "the" spread for every MLB market.
>
> **No verdict in this file moves.** The cost bar is `fee(ask) + slippage` with
> **no half-spread term** (`PREREGISTRATION_DEVIG.md` §2.3), so it never depended
> on this, and a tighter book makes the venue gap *smaller*, not larger. Found
> because the `reopen` chat asked for one re-measurement rather than accepting
> the number.
| Kalshi taker fee at 50¢ (`common/kalshi_fees.py`) | **1.75¢** | quadratic, peaks at 50¢ — exactly where moneylines sit |
| **cost bar at the ask, 1¢ slippage** | **2.75¢** at 50¢, 2.12¢ at 20¢/80¢ | §2.3 of the pre-registration |

De-vigging a two-way market with a 2.01 pp overround moves each side by roughly
**1 pp**. To clear a **2.75¢** bar, Kalshi's ask would have to sit **2.75¢ or
more below** a fair value that is itself only a 1-point adjustment to a book
this project has measured agreeing with Kalshi to within 0.4–2¢ on four separate
occasions.

> **You are trying to detect a mispricing several times larger than the total
> quantity your instrument estimates.** That is not a power problem that more
> events fix. It is the shape of the answer.

## 2. `q`, measured

Pre-registered rules exactly: exact game-start join, one entry per event,
`worst_case` de-vig primary, cost from `common/kalshi_fees.py`, anchor windows
from the ticker-derived start, Pinnacle `isLive` observations discarded, and the
disjointness boundary at 2026-08-05T00:00Z.

| anchor | de-vig | slippage | events with aligned quotes | **events firing** | **q** |
|---|---|---|---|---|---|
| −24 h | **worst_case** | **1.0¢ (primary)** | **17** | **0** | **0.000** |
| −24 h | worst_case | 0.5¢ | 17 | 0 | 0.000 |
| −24 h | worst_case | **0.0¢** | 17 | **1** | 0.059 |
| −24 h | power | 0.0¢ | 17 | 1 | 0.059 |
| −24 h | multiplicative | 0.0¢ | 17 | 1 | 0.059 |
| −6 h | any | any | 4 | 0 | 0.000 |
| −2 h | any | any | 0 | — | — |

**The distribution is more informative than the count**, because it does not
depend on a threshold. Taking each event's **most favourable** observation in
the whole −24 h window — i.e. the best case available to a strategy that could
time its entry perfectly:

| best per-event net gap (`edge − cost`), primary cell | value |
|---|---|
| median | **−2.61¢** |
| p75 | −1.91¢ |
| p90 | −1.51¢ |
| **maximum over all 17 events** | **−0.91¢** |

**Not one event in the sample has a positive net gap at any moment in its
24-hour pre-match window**, even choosing the entry with hindsight.

> **The honest bound on 17 events.** `q = 0` with n = 17 has a 95% upper limit of
> **3/17 ≈ 0.18** by the rule of three. `q` could genuinely be as high as 18%.
> Everything in §4 uses that upper bound, not the point estimate, so the
> timeline is the **optimistic** one.

## 3. Answering the three questions directly

### 3.1 Does the recorder capture what is needed? **Yes for MLB, with four gaps, two now fixed.**

| leg | state |
|---|---|
| Kalshi MLB order-book touch | ✅ 12,720 snapshots, 120 tickers, **100.0% two-sided**, both sides stored raw, no mid computed anywhere |
| Pinnacle MLB moneyline | ✅ 304,383 period-0 price rows, `maxRiskStake` and `isLive` stored |
| the join key | ✅ `k_names` (added 2026-08-06 00:23) carries `yes_sub_title`; the club code in the ticker is exact |
| settlement | ⚠ **not in the recorder, by design** — it must be pulled separately by `pull_kalshi_soccer.py`, **within Kalshi's ~69-day retention window**, or the outcomes are gone. Nothing currently schedules that. **This is the one unbuilt piece.** |

**Gap 1 — FIXED.** `record.py` probed `mkts[:60]` in whatever order Kalshi's
`/markets` returned, which is undocumented. `KXMLBGAME` lists 85–104 markets
against that cap, so ~40 got no book on a given cycle and *which* 40 was decided
server-side. Measured: snapshots per MLB ticker ran **min 1, p25 25, median 94**
over 214 cycles — some markets were nearly starved and nothing said so. Now
sorted by `close_time` ascending, so the games about to start are never the ones
dropped.

**Gap 2 — FIXED (Amendment D1).** The club-name join dropped the **Athletics**:
Kalshi writes `A's`, which normalises to `a s`, length 3, under the length-4
floor that exists to stop a one-character name swallowing the sample. 5 of 53
events lost. Replaced with an exact 30-club code map keyed on the ticker suffix;
join went **17 → 21 events**, and it also makes Pinnacle's aggregate props
(`Home Runs (15 Games)`) unmatchable, which the name test could not see.

**Gap 3 — a trap, not a bug, and it is the third of its kind here.**
`close_time` on a **live** Kalshi MLB market is the game start plus **exactly
72 h** — 94 of 94 active markets. On **settled** markets Kalshi rewrites it to
the real settlement instant, 2.4–3.2 h after start. Anything anchoring a live
market on `close_time` anchors **69 hours after first pitch**. After Amendment
A1 (`close_time` is settlement, not start) and LEDGER T010
(`occurrence_datetime` is at or after match end), this is the third Kalshi time
field to mislead this repo. The design derives the start from the ticker and
verifies it against Pinnacle's independent `starts_utc` — **exact on 22 of 22**
jointly-listed games.

> ✅ **The old MLB control is NOT damaged by this.** It ran on *settled* markets,
> whose `close_time` is the true settlement instant, so its −24 h anchor really
> was ~21 h before first pitch. I checked this specifically because the opposite
> would have voided [RESULTS.md](RESULTS.md)'s control gate. It did not.

**Gap 4 — the recorder was DOWN for 2.5 hours** when this session started
(last cycle 2026-08-06T15:13Z, no process alive at 17:41Z, no error written).
Restarted, and restarted again at 17:51Z to pick up Gap 1's fix. It had been
launched from a prior session's shell and died with it; it now runs detached.
**Nothing monitors it.** Recorded here because this is the one asset that cannot
be bought back later.

### 3.2 How many events until it is testable on MLB?

**Two different answers, because the powerful test is not the one that was
asked for.**

The rate is not the constraint. MLB plays **~15 games a day** and, inside the
window where both venues have listed a game, the join is essentially complete —
the 31 currently-unjoined events are all games from 2026-08-08 on, which
**Pinnacle has not listed yet**, not games that failed to match. That resolves
itself daily.

**Stage A — is the de-vigged reference a better forecast than Kalshi's price?**
The paired-Brier test, which uses every event rather than only the qualifying
tail. On the pre-registration's placeholder dispersion it needs **≈ 440 events
≈ 30 MLB days ≈ early September 2026** — comfortably inside this season. Its
true `σ_Δ` still has to be measured, and cannot be until settlements exist.
**This is reachable.**

**Stage B — the gated P&L test, the one actually asked for.** Using the
**optimistic** `q = 0.18`:

| detectable edge | trades needed | events needed | MLB days | seasons |
|---|---|---|---|---|
| 2¢ | 4,900 | 27,222 | 1,815 | **11.2** |
| 3¢ | 2,178 | 12,100 | 807 | **5.0** |
| **5¢** | **784** | **4,356** | **290** | **1.8** |
| 8¢ | 306 | 1,700 | 113 | 0.7 |

Turned around — what the *available* baseball can detect:

| horizon | events | trades at q = 0.18 | **smallest edge detectable** |
|---|---|---|---|
| rest of the 2026 regular season (~55 days) | ~825 | 145 | **11.6¢** |
| a full 162-game season | 2,430 | 428 | **6.8¢** |
| three full seasons | 7,290 | 1,283 | **3.9¢** |

The largest net gap observed on any event, choosing the entry with hindsight, is
**−0.91¢**. Nothing in the data suggests an effect within an order of magnitude
of what even three seasons could resolve.

> **Stage B is not reachable on MLB. Not this season, and not on any horizon
> worth planning around.** It is not close, and the reason is §1: a 2.75¢ cost
> bar against a 2.01 pp total vig. Stated plainly so it is not rediscovered in
> six weeks.

**And there is no historical shortcut.** Pinnacle publishes no historical
endpoint at any price, and of every free historical sharp-odds source probed in
[DATA.md](DATA.md), the only one that works — `football-data.co.uk`'s Pinnacle
closing odds — is **soccer only**. Baseball is forward-only.

### 3.3 MLB was the negative control. Does using it as the test family break the design?

**Partly, in one specific way, and it is fixable. See
[PREREGISTRATION_DEVIG.md](PREREGISTRATION_DEVIG.md) §4 for the full argument.**

- **Not broken:** the control is **spent**, not permanently reserved. It gated
  one candle-based run of H1–H9 and reported PASS. A control is a role a dataset
  played in one experiment, not a property the family carries forever.
- **Not broken:** the **data** is not reused. The control ran on hourly candles
  from settled markets ending at a latest game start of **2026-08-04T23:40Z**;
  H11 runs on the recorder's live book and refuses any game starting before
  **2026-08-05T00:00Z**. Different table, different instrument, different
  variable, zero shared events — asserted in code.
- **Broken:** the family can no longer generate its own null. You cannot hold
  *"MLB is efficient, so a hit here is an artifact"* and *"MLB is where I expect
  the edge"* at once. **Three internal controls replace it** — a mismatched-pair
  placebo (the gate), a stale-reference placebo, and a two-sided coherence check.
  Internal controls are stronger here anyway: they run on the same events, so
  they cannot be separately underpowered.
- **Broken:** the prior now runs against the test, so the pre-registration sets
  an **asymmetric bar** — a positive H11 must clear all six of Stage A, BH-FDR,
  a CI above cost, a clean placebo, PLATEAU-not-PEAK, and the sealed holdout.

> **The clean way to do this**: run it on MLB, because MLB is the only family
> that has a joinable reference price, a stable cost bar and a real forward
> event rate at the same time — and treat its known efficiency as a **difficulty
> setting, not a disqualification**. An edge found on the family this project
> pre-declared efficient would be its strongest result ever. No edge is the
> expected outcome and is a fifth confirmation that Kalshi is the sharp line.

## 4. What this does NOT say

1. **It does not say the strategy loses.** No settlement has been joined. It
   says the gate almost never fires, and that when it might, the sample needed
   to prove anything is multi-season.
2. **17 events.** The recorder has run ~44 hours. Every number here is a
   feasibility measurement on a small forward sample, and `q = 0` carries an 18%
   upper bound.
3. **It says nothing about Polymarket**, which pays makers a rebate instead of
   charging them a fee — the one structural difference that moves the §1
   arithmetic, and the venue where the only reconciled live P&L in any corpus
   here was actually earned, **passively**.
4. **It says nothing about non-moneyline markets.** `KXMLBTOTAL` (249 tickers)
   and `KXMLBRFI` (71) are recorded and unjoined, and Pinnacle prices totals.

## 5. The single next thing

**Build the settlement puller and schedule it.** Every other leg is recording;
outcomes are the only leg with a deadline, because Kalshi's window is ~69 days
and closed markets 404 for good. Stage A cannot run without them, and Stage A is
the only stage that is reachable.

Then, in order: **Stage A on MLB at ~440 events (early September)** · the
**Polymarket leg**, where the fee arithmetic in §1 is different · and
`KXMLBTOTAL`, which has a reference price and has never been looked at.
