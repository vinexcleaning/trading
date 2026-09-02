# HANDOFF — bot-forensics

Session 2026-08-05. Read-only against the live account's records. The bot was
not started, no order endpoint was touched, `TRADING_DISABLED` untouched.

## Read in this order

1. **[FINDINGS.md](FINDINGS.md)** — Tasks 1 and 2. The reconstruction, the
   config archaeology, the argmax null, the martingale, the score-lag
   measurement.
2. **[VERDICT.md](VERDICT.md)** — Tasks 3, 4 and 5. The backtest replay, the
   extractor results, the answer.
3. **[DECISIONS.md](DECISIONS.md)** — eight judgement calls taken without
   asking, conservative option each time.
4. **[REPRODUCTION.md](REPRODUCTION.md)** — a *second* session's independent
   re-run of all of the above (everything reproduced), the one reporting
   selection it found (B005a), and a line-by-line look-ahead audit of the
   decisive test.

## What is here

```
src/load.py           loaders + tier/event parsing. tier is by PREFIX (T017).
src/t0_survey.py      what is in the records
src/t0b_sides.py      how Kalshi books a sale. Settle this before any P&L.
src/t0c_botsig.py     bot vs manual, first attempt (notional) - WRONG, kept
src/t1_ledger.py      first ledger, on the wrong classifier - kept as evidence
src/t1b_edges.py      the three awkward rows, incl. the $14.51 misclassification
src/t1c_classify.py   the structural classifier
src/t1d_outcomes.py   8 tickers resolved from the public market endpoint
src/t2_master.py      TASK 1+2: the ledger, bursts, the peak, the stress test
src/t2b_nightday.py   the argmax null (200k perms) + clock buckets + BH-FDR
src/t2c_costbar.py    permutation p-values + cost bar per bucket from the tape
src/t2d_martingale.py multi-leg entries + the score-lag test with a placebo
src/t3_replay.py      TASK 3 arm A: tennis_engine.evaluate() on real set scores
src/t3b_proxy.py      TASK 3 arm B: price proxy, all 13,658 views, covers ITF
src/t4_github.py      TASK 4: narrow GitHub retrieval (signal-github can't see this)
src/t4b_verify.py     verifying the two findings that change a decision
src/t4c_youtube.py    TASK 4: query the two existing YouTube corpora, read-only
out/                  every run's stdout + the CSVs. Committed on purpose.
```

`.venv` here (pandas 3.0.5, numpy, pyarrow, scipy, requests). Run scripts from
`bot-forensics/`.

## The numbers a reader will want

| | |
|---|---|
| bot lifetime | **−$6.92**, 108 matches, 74 bursts, 95% CI [−$0.97, +$0.78] |
| equity peak | +$32.19 after 60 matches, 28 Jul 13:32 UTC |
| P(random reorder reaches that peak) | **0.052** |
| P(random reorder gives that before/after gap) | **0.272** |
| hand-traded P&L in the same window | **+$98.94** on 31 matches |
| martingale sequences | 12, **−$16.43**; the other 94 matches +$9.63 |
| martingale before the peak | **7 of 7 winners, +$6.63** |
| repricing already done when the feed updated | **97.4%** (n = 4,398) |
| buckets clearing BH-FDR 5% | **0 of 13** (permutation arm; the parametric arm over 21 buckets says 3 — see B005a) |
| backtest replay, ITF only | **−9.13c/trade**, −$1.98/match, t = −26.0 |
| backtest replay, ITF holdout | −8.77c, 1,045 matches, t = −16.0 |

## Open items, highest value first

1. **`livetennisapi.com` free tier — does it actually return ITF?**
   **The test is now written, tested and waiting on one free signup:
   [`ITF_CHECK.md`](ITF_CHECK.md) has click-by-click steps, and
   `src/t5_itf_probe.py` runs the check in 6 requests and prints
   PASS / FAIL / INCONCLUSIVE.** Endpoint paths are verified rather than guessed
   — `/matches`, `/tournaments`, `/players`, `/fixtures` and `/usage` all return
   **401, not 404**, so the routes exist and only want a key. Both failure paths
   (no key, bad key) are tested; the key is never printed, stored or committed.
   **Settling it needs an account, which is the user's to create — I do not
   create accounts.** It reopens *data availability* only; Task 3 (B009) says ITF
   economics are the worst of any tier, so this does not reopen the trade.
2. **`STATUS.md`'s "Sackmann upstream is 404" needs softening.** Three repos are
   404; `tennis_MatchChartingProject` is live at 399★ and a third-party mirror
   of the ATP/WTA data was pushed 2026-06-25.
3. **The stop loss.** Four independent files now say it is the most expensive
   component and one of them (`high_entry`) shows it turning +0.62c into
   −3.77c on identical trades. Nothing should be re-armed before this is
   addressed — but note nothing should be re-armed at all.
4. **`audit/LEDGER.md` R6 is closed** — `high_sweep`, `high_entry` and
   `longshot` outputs are on disk at `out/rerun_*.txt`.

## Traps hit while doing this, for whoever is next

- **`sell/no` in a Kalshi fill is a SALE of a YES you own, not a new short.**
  Settle this from the data before computing anything; it flips the sign of most
  of the record. Three independent confirmations are in `out/t0b_sides.txt`.
- **A settlement row's `fee_cost` is the cumulative TRADING fee for that ticker,
  not an extra settlement charge.** Verified equal to the sum of that ticker's
  fill fees. Double-counting it would have cost $59.72.
- **Splitting bot from manual on order size classified the single largest winner
  wrong** and would have halved the apparent bot total in the flattering
  direction. The rule has to be structural.
- **`_fills.json` is paginated and drops history.** It disagrees with the
  settlement record on 4 of 142 tickers, worst by $14.57. Prefer settlements.
- **`transcripts.snippets_json`, not `transcripts.text`.** The first YouTube
  scan looked for `text`, found nothing, and cleanly reported "0 hits" for all
  four questions. A canary term now asserts the scan is alive.
- **`signal-github`'s corpus cannot answer a tennis-data question** and adding
  terms to its `queries.py` would push them through a prediction-market topic
  gate that drops them. Use a separate retrieval; do not pollute that corpus.
- **`import autoscan` drags in `kalshi_client` → `requests` → the live
  order-signing path.** `t3_replay.py` execs the module's source up to the first
  dataclass instead, with the cut point asserted.

## What was NOT done

- No entry-level tick data for the live trades — the recorder tape covers
  27 Jul 23:01 → 28 Jul 13:49 only, so the 16:00–19:59 UTC cost bar is unmeasured.
- The score-joined backtest arm cannot see ITF at all; arm B's proxy is a proxy.
- ~~The `livetennisapi` free tier is unverified.~~ **SETTLED 2026-08-06: it
  returns 7,786 ITF tournaments on a free key.** See below.
- Nothing was changed in `kalshi-inplay-bot/`. Not one byte.

---

## 2026-08-06 session — ITF settled, player features tested

New: `PREREGISTRATION_T6.md` (written and committed *before* running),
`FINDINGS_T7.md`, and `src/t5_itf_probe.py` … `src/t9_upcoming.py`.

| | |
|---|---|
| ITF on the **free** tier | **7,786 tournaments** — the thread was closed on a false premise (B021) |
| vendor rate limit | advertised 1,000/day, **actually 100/day** (B022) |
| feature events built | **6,519**, leak-free; selection canary 0.5005, z = +0.09 |
| cells swept | **2,008**; **2** BH discoveries against **4.1** on shuffled data (B023) |
| the one survivor | wide-book artifact — +1.18pp on tradeable books, **~~−0.77c~~ −0.374c** net at ask (B024). ⚠ **CORRECTED 2026-09-01 to −0.374c** — the −0.770c charged `fee_order_cents(px, 1)`, the per-ORDER round-up, to orders of ONE contract in expectancy arithmetic; `common/kalshi_fees.py` names `fee_rate_cents` for exactly this case. Reproduced (n=261) then recomputed. **+0.396c of the old number was the rounding assumption, not economics.** The old figure is left visible per house rules. **B024 is unchanged** — still negative, and the cell's 6.06c mean spread is the killer, not the fee. Found by the `reopen` audit. |
| **calibration, tradeable books** | **0 of 10 bands deviate**, pooled **+0.03pp** (B027) |
| bugs in my own code, caught | **2**, both toward a false positive (B025) |

### Run order

    .venv\Scripts\python.exe src\t6_features.py      -> out/t6_features.csv
    .venv\Scripts\python.exe src\t7_sweep.py         -> the 2,008-cell sweep (slow)
    .venv\Scripts\python.exe src\t8_calibration.py   -> the calibration curve
    $env:LIVETENNIS_API_KEY="twjp_..."
    .venv\Scripts\python.exe src\t9_upcoming.py      -> the fixtures sheet

`out/t6_features.csv` is **deliberately not committed** — 1.8 MB and it carries
player names. It rebuilds in one command from data already on disk.

### Traps hit this session

- **`views.pkl` unpickles `engine.MarketView`**, so `backtest/` must be on
  `sys.path` before `pickle.load` or you get a bare `ModuleNotFoundError`.
- **`round` is a bad `itertuples` field name** — it silently fell through to a
  tuple index. Use `to_dict("records")`.
- **A permutation null must preserve whatever the cells select on.** Shuffling
  within tier while cells selected on price manufactured **1,010** false
  discoveries. Stratify on price too.
- **Never price an entry at the mid.** Worth 2–3c on these books — larger than
  anything measurable here.
- **The API throws transient 502s that are not auth failures.** The first
  version of `t5_itf_probe.py` reported "key rejected" on one.

### Next, highest value first

1. **The 29-day window is the binding constraint on everything weak here.**
   The history plan is **$9.99** for 43 months including ITF, and would let the
   whole feature study re-run on 3 years instead of 4 weeks. **B027 does not
   depend on it and stands either way.**
2. **Record fixtures daily.** Surface is on every fixture but cannot be joined
   retrospectively. A month of recording unlocks surface analysis.
3. **Rotate the API key** — it was pasted into a chat. No script here writes it
   to disk or commits it.
4. **Nothing to the bot.** `TRADING_DISABLED` stays.
