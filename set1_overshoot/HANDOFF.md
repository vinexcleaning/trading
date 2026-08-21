# HANDOFF.md — Kalshi tennis set-1 study

2026-08-01 18:20. Unit of observation is **the match**. Kalshi data
**2026-05-25 → 2026-08-01**, 19,782 matches, 5 series.

## 1. THE FOUR THINGS ASKED FOR, UP FRONT

**1. θ_labelled vs the 3.05 pp prediction — and which branch.**
θ_labelled = **−5.75 pp** [−9.71, −1.79], p = 0.0062, **n = 479** matches,
2026-05-25 → 07-26. Against the pre-registered ceiling of 3.05 pp it is **1.9×**,
which puts it in the **"presume noise until it survives an untouched holdout"**
branch. **It did not survive:** train +7.21 pp / net +3.365 ¢ → holdout +3.57 pp /
net **+0.311 ¢**. Verdict: **presumed artifact**, exactly as pre-registered.

**2. Coverage achieved, and the join canary.**
**Zero additional coverage.** Task 1 is blocked by two independent, verified
findings (§3). Labels remain the 2,887-match external set → 479 events (13.9% of
3,436). The join canary is **UNTESTABLE**: labelled events show residual +0.0597
vs unlabelled +0.0166 (diff +4.31 pp, **z = +2.15**, MDE 5.60 pp). So the labelled
subsample *does* look different and I **cannot rule out** that the −5.75 pp is a
selection effect of which matches got labelled.

**3. Does any subset clear 3.61 pp with a CI excluding zero?**
**No. 0 of 10** margin buckets, after **0 of 25** time/tier buckets. Median MDE
across margin buckets **9.9 ¢** against a ~2 ¢ target.

**4. Train/holdout decay on candidates.**
Label-verified: **+3.365 ¢ → +0.311 ¢**. No margin bucket qualified for a
holdout test.

## 2. VERDICT

The undershoot is real (θ = −2.42 pp, p = 0.0009, n = 3,436) and uncollectable
against a 3.61 pp bar. The one candidate that looked like it might clear — the
label-verified subsample — is 1.9× what its own mechanism can explain, decays to
near zero on holdout, and sits on a join that fails to pass its canary. Tasks 3
and 4 were skipped by rule (building on a null; and blocked data).

## 3. RETRACTIONS AND DISPROVEN PREMISES

**Task 1 is impossible as specified — two independent blockers:**

1. The Flashscore actor's `dayOffsets` enum is **−7 to +7**. My window needs
   **−68 to 0**. It structurally cannot backfill.
2. Apify returns **"Monthly usage hard limit exceeded"** — no actor runs at any
   price. **The approved $3.44 cannot be spent.** The "$0.001 × 3,436 events"
   costing was also wrong in principle: Flashscore bills per *match returned per
   day pulled*, not per event selected, so full coverage would have been ~$20.

**Two of my own claims from the last handoff, retracted:**

3. **"ATP is the thinnest book — median 30 lots, 3 ¢ spread."** **Wrong.** That
   came from a single 68-minute window at 07:00 UTC when ATP markets had just
   opened. On a full day (22,395 ATP snapshots vs 1,857 before): ATP median
   spread **1.0 ¢**, median top size **312**. Within the 25–75 ¢ band: Challenger
   1,872 lots, WTA 1,192, ITF-W 420, ITF-M 388, **ATP 298** — ATP is thinnest by
   size but ties for the *tightest* spread, and ITF has the *widest* (2 ¢). The
   "liquidity inversion" headline was a time-of-day artifact.
4. **"Median 106 contracts at the touch."** Same cause. Full day: **564**.

**Other premises checked:**

5. tennis-data.co.uk refreshed: still ends **2026-07-26**. No new labels. Its
   WTA file contains a corrupt date (**2029-07-20**) — flagged, not used.
6. Stale 3.70 / 1.197 values: **narrative-only.** Every net figure recomputes the
   bar from data; the only code constant was an unused variable. **No verdict
   changed.** Audit baselines updated to 3.61 / 1.170 so they now act as a
   forward regression test. One truth-set file on disk; all six readers current.

## 4. RESULTS TABLE

| Claim | n + unit | Date range | Value | MDE | Verdict |
|---|---|---|---|---|---|
| θ, `deep:30@38` | 3,436 matches | 05-25→08-01 | −2.4153 pp, p=0.0009 | 2.16 ¢ | real, confirmed |
| θ label-verified | 479 matches | 05-25→07-26 | **−5.75 pp** [−9.71,−1.79] | 5.71 ¢ | **presumed artifact** |
| — its holdout | 192 matches | 07-06→07-26 | net **+0.311 ¢** | 8.93 ¢ | decays |
| Label join canary | 604 vs 2,832 | 05-25→08-01 | z = **+2.15** | 5.60 pp | **UNTESTABLE** |
| Margin 6-2/6-3 | 160 matches | 05-25→07-26 | eff +8.15, bar +3.58, net +4.56 ¢ | 9.5 ¢ | UNTESTABLE |
| Margin 6-4/7-5 | 190 matches | 05-25→07-26 | eff +4.12, bar +3.66, net +0.47 ¢ | 9.5 ¢ | UNTESTABLE |
| Margin 7-6 tiebreak | 93 matches | 05-25→07-26 | eff +1.84, bar +3.47, net −1.63 ¢ | — | loses |
| Set 1 = 6–8 games | 99 matches | 05-25→07-26 | eff **+10.86**, bar +3.66, net +7.20 ¢ | 11.3 ¢ | UNTESTABLE |
| Set 1 = 11+ games | 157 matches | 05-25→07-26 | eff +2.77, bar +3.60, net −0.83 ¢ | — | loses |
| Best-of-5 (Slam men) | 73 matches | 05-25→07-26 | eff +6.22, bar +3.19, net +3.03 ¢ | 14.7 ¢ | UNTESTABLE |
| Margin buckets clearing | 10 buckets | 05-25→07-26 | **0** (0.25 by chance) | — | null |
| Cost bar, fade | 3,436 matches | 05-25→08-01 | **3.6104 pp** = 1.170 + 1.000 + 1.441 | — | CONFIRMED |
| Depth at touch, full day | 64,898 snapshots | 08-01 06:58–18:15 | median **564** lots | — | new |
| Best bid rises per minute | 150 markets | 08-01 | median **6.1%** of minutes | — | new |

There **is** a monotone gradient — effect falls 10.86 → 5.58 → 2.77 pp as set 1
gets longer, and 8.15 → 4.12 → 1.84 pp as the margin narrows. Mechanistically
sensible (the market over-reacts more to a blowout). Every cell is inside its
noise band, and the same shape appeared in the segmentation that produced
0 of 25.

## 5. CANARIES AND CONTROLS

| Guard | Reading | Status |
|---|---|---|
| Audit: headline numbers recomputed | **15 recomputed, 14 CONFIRMED** | 1 baseline updated (detector, restored labels) |
| Selection canary, live universe | 0.4969, z = −0.88 | PASS |
| Guard-rot (known-bad rules) | last_price +140.4, OI +15.7, volume +10.0 | all FAIL as required |
| Label-join canary | z = +2.15, MDE 5.60 | **UNTESTABLE** |
| spread>15 ¢ mask | z = −6.34 | FAIL — real composition effect |
| plausible / play-window / vol24 / liquidity | — | UNTESTABLE (4 rules) |
| G1 / G2 / G2b orientation gates | −2.29 / +0.21,+0.55 / −0.34 pp | all PASS |
| Synthetic null / positive control | −0.59 pp / +4.04 pp | PASS |
| P&L decomposition identity | +0.0000 ¢ | exact |
| Test suite | **51/51** | PASS |
| Depth recorder (content-level, ×5 today) | 98.8% non-empty, 20 levels/side, prices in (0,1), 3 s old | alive |

## 6. NOW CLOSED

| Question | Number |
|---|---|
| Does fixing the labels rescue the trade? | **No.** −5.75 pp is 1.9× its mechanism ceiling and decays to +0.311 ¢ on holdout |
| Can labels be extended? | **No.** Apify capped; `dayOffsets` −7..+7; Sackmann 404; tennis-data ends 07-26 |
| Does set-1 margin concentrate the effect? | Directionally yes, statistically no — 0 of 10 buckets clear, median MDE 9.9 ¢ |
| Is ATP the thinnest book? | **No — retracted.** 1.0 ¢ spread, 312 lots on a full day |
| Is trade-through a generous fill assumption? | No. Bid rises 6.1% of minutes; consistent with the 55–88% fill rates over 5–60 min windows |
| Did the wrong cost bar change any verdict? | **No.** Narrative-only; no computation used it |

## 7. STILL OPEN

**Blocked on quota:** all Apify actors (account hard limit). Task 1 labelling,
Task 4 serve order, point-by-point features.
**Blocked on the desktop:** v3 backtest dedupe field; copy-trading wallet ranking
timing; recorder `None`-price check. See `BLOCKED_ON_DESKTOP.md`.
**Skipped by rule:** Task 3 (conditional recovery) — both Task 1 and Task 2 are
null, and building a model on a null effect is how this project produced its
false positives.
**Not resolvable with public data:** order-level queue priority (Kalshi publishes
aggregate size per price, not order priority), so the fill model is bounded above
and cannot be tightened further.

## 8. RUNNING

| ID | Process | Writes | If the machine sleeps |
|---|---|---|---|
| b2bryu65m | my depth recorder (since 06:58, 79–120 markets, 0.55 s pacing) | `data/depth/<date>/<hh>/depth.jsonl`, 64,898 snapshots | **irrecoverable gap** |
| PID 22612 | `crypto/src/recorder.py` — **not mine**, untouched | `crypto/data/…` | irrecoverable gap |

## 9. NEXT THREE ACTIONS

1. **Restore Apify quota, then label via Flashscore day-by-day** (~$20, not
   $3.44; needs a source that reaches −68 days — Flashscore's actor does not, so
   `crawlstone/tennis-scraper` by date or `tennisexplorer` by date are the
   candidates). Only path to raising label coverage above 13.9%.
2. **v3 backtest dedupe grep on the desktop** (~10 min). One grep voids or clears
   a 14,162-market result set.
3. **Stop the tennis strategy line.** With 3,436 events, sd 45 ¢, and n ≈ 3,970
   needed for a 2 ¢ edge, the sample cannot resolve the question. More slicing
   has negative expected value; more data accrues at ~1,900 matches/week.

## 10. WHAT THE COORDINATING CHAT HAS WRONG

1. **"$3.44 buys the full label set."** No. Apify is hard-capped so nothing runs,
   and the costing model was wrong anyway (~$20, billed per match-day).
2. **"Flashscore can backfill."** Its `dayOffsets` is −7 to +7.
3. **"ATP is the thinnest book, 30 lots at 3 ¢."** My error, now retracted — a
   68-minute sample. Full day: 312 lots at 1.0 ¢.
4. **"Median 106 lots at the touch."** Also that sample. Full day: **564**.
5. **"The label-verified reading is in noise territory."** Correct, and now
   confirmed: it decays +3.365 → +0.311 ¢ and its join canary is UNTESTABLE at
   z = +2.15. Treat −5.75 pp as **presumed artifact**, not a finding.
6. **"8 withdrawn positives."** I have not been able to reproduce that count from
   anything in this repo and did not carry it as fact; what I can verify is that
   every positive *this session* has died.
7. **The monotone margin gradient will look like a result.** It is not one —
   0 of 10 buckets clear and median MDE is 9.9 ¢ against a 2 ¢ target. A monotone
   pattern across an ordered variable is more credible than a lone cell, but at
   this power it is indistinguishable from noise.

---

## Phase 6 — the maker test. Where it got to, 2026-08-20

**Read `MAKER_DATA_AUDIT.md` first: I answered mailbox 017's data question
"no", and it was wrong.** The exchange still serves per-market trades *and*
one-minute bid/ask candles for settled markets back to **2026-06-14**, which is
**35,994 markets = 17,997 matches**. Nobody had asked it.

### Running right now

`src/p6_maker_pull.py --start 2026-06-14 --end 2026-08-21 --candles-only`,
logging to `data/pull_candles.log`. Read-only, no credentials, 6 requests a
second against a measured ceiling of 15, and eight other jobs share this
machine's quota. **Resumable** — if it dies, run the same command again and it
skips what is already in `pulled`.

**⏳ Time matters here and it does not usually.** The retention floor advances
one day per day. Every day this is not finished, one more day of the study's
window becomes permanently unbuyable.

### The pipeline, in order

| step | file | state |
|---|---|---|
| 1 | `p6_maker_pull.py --candles-only` | **running**, ~3 h |
| 2 | `p6_state.py --build` | works; rerun after step 1 finishes |
| 3 | *(to write)* dump the tickers where the rule fires | not started |
| 4 | `p6_maker_pull.py --trades-for <file>` | not started |
| 5 | `p6_maker_fill.py` | written and tested; fill rates meaningless until 4 |

**Do not skip to step 4 with the whole universe.** Measured: 616 candle rows
against 4,011 trade rows per market, so trades for everything is ~28 GB and
nearly all of it belongs to markets where the rule never fires.

### Three faults already found and fixed, all by looking at numbers

1. **Paths start at `t0`.** `p1_state` stores `src_arr[t0:t0+PATH_MIN]`, so
   column *j* is minute *t0+j* and `deep:30@38` means 38 minutes **into the
   match**. My first version indexed the whole market-life array, which would
   have searched a dormant pre-match book and still produced numbers.
2. **`find_play_window` needs its density floor passed explicitly** — the
   signature defaults to off. With it off the median "match" ran 1,093 minutes.
3. **`count_fp`, not `count`.** The trade object has no `count` key, so the
   obvious spelling writes 0.0 for every trade.

### What is measured and holds

- **Takers buy ~74% of the time on BOTH tickers of a match**, 126 of 126
  events. So resting an **ask on the favourite** (R2) is the same position as a
  **bid on the underdog** (R1) and sits where the flow is. Both are computed;
  neither is chosen in advance.
- **A first replication signal:** on 235 matches that fired `deep:30@38`, the
  underdog won **66.8%**. The original study reported **66.09%** on a different
  and earlier window. That is reassuring about the rebuilt pipeline, and it is
  **not** a result — the breakeven is 67.19% and no fill model has run.

### What would make this stop

`PREREGISTRATION_MAKER_FADE.md` §10, five criteria, written before any result.
The one most likely to bite: **fewer than 1 match in 5 getting any fill kills
it regardless of the profit.**

<!-- COORDINATOR-STATE
doing: pulling 17,997 tennis matches of minute-by-minute prices so the fade can be re-tested as a maker; pipeline built and tested, waiting on the pull
left: rerun p6_state, dump the tickers that fire, pull trades for those only, then run the three arms and the two placebos
needs: no
-->
