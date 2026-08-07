# DECISIONS.md

Ambiguities resolved without asking, per operating mode. Conservative reading
taken each time.

| # | ambiguity | conservative reading taken | why |
|---|---|---|---|
| 1 | "every asset with adequate ladder history" — which series? | `KXETHD`, `KXSOLD`, `KXXRPD` (the `greater` above/below ladders) | Direct analogues of `KXBTCD`, which produced the BTC result. Comparing like with like. `KXDOGED` excluded — no strike on any of 83,030 rows. |
| 2 | Panel size for non-BTC assets | 150 events × 6 strikes (vs BTC's 250 × 8) | API is shared with other sessions; three series at BTC's density would take ~3 h and risk 429s. 150 events still clears the 200-event floor when pooled and is stated as a limitation rather than hidden. |
| 3 | Effective-n for a single asset | report nominal n; effective-n applies only to CROSS-asset claims | Within one asset, windows are the unit and are not obviously correlated; the 1.81 figure is about agreement BETWEEN assets. |
| 4 | Task 6 costing with <200 windows | do not run; report accrual status only | "Never substitute an assumed entry price" and three bars have already been wrong-shaped. Underpowered costing would be a fourth. |
| 5 | `no_bid_size` / `no_ask_size` null in recorder rows | keep, do not treat as defect | Kalshi does not return NO-side sizes; YES sizes are present and the NO price is what the fade needs. Logged so a future session does not chase it. |
| 6 | Which "hourly" BTC series is the ladder | `KXBTCD` (above/below) not `KXBTC` (bucket) | Already established: `KXBTC` has 3× the spread but 1/29 the flow. |
| 7 | Whether to re-pull settled data that has grown | no | Audited clean this session; the window 2026-05-25 → 2026-08-01 is fixed for every test so far, and changing it mid-session would break comparability. |

---

## 2026-08-07 — the maker-viability test (M1)

**D1. Ran on the ARCHIVE, not on forward recording.** Given up: recency — the
archive is frozen at 2026-05-19 → 06-11 (M003), so this measures a window two
months old and cannot be extended by waiting. Taken instead: ~24 days of full L2
available **now**, against weeks of accrual for the same thing. Decided by
measurement, not preference: `src/probe_l2_crypto.py` found `KXBTCD` at 22,691
rows/hour and 16,449 distinct crypto tickers in a single sampled hour.

**D2. Did NOT add crypto to the shared recorder.** Given up: forward accrual, and
therefore any hope of extending the sample past 24 days. Why: `bot-hunt`'s
recorder already probes 18 series at a 60-market cap with cycles running
400–1,000 s, and **four other threads depend on it**. Adding 3–4 crypto series
adds ~180–240 orderbook calls per cycle and lengthens every cycle for everyone,
against C018's 15 req/s ceiling. If the archive window proves too short, the
right fix is a **separate** lightweight crypto book recorder, not a heavier
shared one.

**D3. Made the 60-second horizon primary and hold-to-settlement secondary.**
Given up: the number that looks most like a P&L. Why: §6b measured that
settlement-marking makes every fill in a day share one BTC trajectory — the
day-clustered CI was **7.78¢ against an event-clustered 1.36¢**, and a single
15-minute market moved the eight-day mean by 2.5¢. A 60 s horizon is not
swamped by the thing that is hardest to sample, and it is the horizon at which
"does the spread cover the pick-off" is actually a question. The
settlement-marked arm is reported beside it, and **if the two disagree in sign
that is the finding** — it would mean inventory, not adverse selection, is fatal.

**D4. Reported the event-clustered interval BESIDE the day-clustered one, with
the width ratio printed.** Given up: a cleaner table. Why: I quoted the narrow
one once already and it changed my conclusion. Printing both on the same line
makes a repeat visible rather than plausible.
