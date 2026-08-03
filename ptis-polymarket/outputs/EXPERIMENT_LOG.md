# PTIS Experiment Log

This log is append-only. Invalid experiments remain visible.

## 2026-07-23 — Current-market shadow scans

**Research question:** Can recently observed public trades from preliminary
directional candidates pass a realistic follower execution filter using current
official order books and a $100 paper bankroll?

**Dataset:** Public Data API trades observed during this session, official Gamma
market metadata, official per-market fee schedules, and current CLOB level-2
books. The workspace is not yet a Git repository, so the code version is
recorded as `unversioned workspace`.

**Common assumptions:** $1 requested notional, no leverage, 2% maximum ordinary
trade risk, 20% maximum total exposure, 5% maximum per-market exposure, 10%
maximum per-trader exposure, maximum $0.03 spread, maximum $0.02 deterioration
from the observed trader price, full-fill requirement, and hold-to-resolution
as the eventual exit policy. No real orders were placed.

### Run 1 — Completed, no eligible signal

- Follower delay: 5 seconds
- Maximum source-trade age: 300 seconds
- Candidates: two preliminary directional wallets
- Result: 0 signals considered, 0 accepted
- Interpretation: neither wallet had a qualifying trade inside the strict
  five-minute observation window.
- Decision: retain as a valid negative observation.

### Run 2 — Invalidated

- Follower delay: 5 seconds
- Maximum source-trade age: 600 seconds
- Initial result: 1 accepted and 9 skipped
- Invalidity: the CLOB `base_fee` value was incorrectly converted into the
  dynamic fee formula rate. Gamma's time-stamped `feeSchedule.rate` is the
  correct formula input for this model.
- Decision: excluded from all performance calculations; record preserved.

### Run 3 — Completed, operational skips

- Follower delay: 5 seconds
- Maximum source-trade age: 600 seconds
- Result: 9 signals considered, 0 accepted
- Skip reasons: 8 missing archived fee schedules; 1 trader behavior filter
- Decision: make market and fee resolution automatic before execution.

### Run 4 — Invalidated

- Purpose: first scan with automatic market and fee resolution
- Partial records: 6 accepted, 1 price-deterioration skip
- Invalidity: the command window ended before the scan completed, leaving a
  partial run.
- Decision: excluded from all performance calculations; add a strict
  per-scan signal bound.

### Run 5 — Completed bounded paper scan

- Follower delay: 5 seconds
- Maximum source-trade age: 600 seconds
- Signal bound: 2
- Result: 2 considered, 2 accepted, 0 skipped
- Simulated open exposure including fees: $2.00025
- Interpretation: two current books passed the initial spread, deterioration,
  depth, fee, classification, and bankroll gates. This is evidence that the
  execution pipeline works, not evidence of profitability.
- Decision: keep the paper positions open in the research ledger and evaluate
  only as execution diagnostics. Their 99.6¢ and 99.9¢ entry prices leave too
  little possible upside for a cautious strategy. Add a minimum remaining-upside
  gate before the next strategy-eligible scan.

### Run 6 — Invalidated

- Purpose: first scan with the minimum three-cent remaining-upside gate
- Invalidity: the command window ended during a redundant fee-metadata refresh
  before any decisions were recorded.
- Decision: excluded; reuse valid session fee observations and retain the
  prospective refresh requirement for longer-running monitors.

### Run 7 — Completed strategy-eligible scan

- Follower delay: 5 seconds
- Maximum source-trade age: 600 seconds
- Signal bound: 2
- Result: 2 considered, 0 accepted, 2 skipped
- Decision: valid negative result. The exact skip reasons are preserved in the
  generated research status report. Do not relax filters to force trades.

## 2026-07-23 — Prospective first-seen monitoring

**Research question:** When selected public-wallet trades are polled
prospectively, how long after execution do they first become visible, and how
many remain paper-copyable under the execution and risk rules?

**Method:** Two sampled wallets were baselined before any signal could be
actioned. Only trades first appearing on later polls entered a persistent,
one-time evaluation queue. Interrupted monitor sessions were invalidated without
deleting their valid first-seen observations. Evaluation was resumed in bounded
batches. All portfolio exposure limits carried across batches.

**Evidence collected:**

- 26 genuinely new post-baseline trades
- Mean measured first-seen delay: 65.9 seconds
- Observed delay range: 33.6–260.3 seconds
- 9 accepted paper entries
- 14 rejected for insufficient remaining upside
- 3 rejected because the executable price moved too far
- $9.07582 open simulated exposure including fees
- 0 resolved positions and $0 realized P&L

**Interpretation:** Public visibility was materially slower than a five-second
assumption. Local processing used a five-second follower delay, but observed
end-to-end signal latency was dominated by when trades appeared in the public
polling route. The strategy is neither profitable nor unprofitable yet because
every accepted position remains unresolved.

**Decision:** Continue prospective paper monitoring. Do not report return, win
rate, or profit factor until official outcomes settle. Do not widen the
remaining-upside or price-deterioration filters to increase trade count.

## 2026-07-23 — Approximate one-week historical replay

**Research question:** Would the current shadow-copy logic have been profitable
over the prior week if outcomes were hidden until settlement?

**Window:** July 17–24, 2026 UTC.

**Method:**

- Six fixed sampled wallets; all were retained rather than selecting only the
  historical winners.
- Trader behavior was reconstructed strictly from trades before each signal.
- The first subsequent public BUY trade after 0, 5, 15, or 60 seconds served as
  the entry-price proxy.
- Entry prices were stressed by 0¢, 1¢, and 2¢.
- Historical outcomes were not available to signal selection and were joined
  only for hold-to-resolution settlement.
- $1 simulated positions and the $100 bankroll concentration limits were used.

**Data limitations:**

- Official historical level-2 books were unavailable.
- Current archived fee schedules were used as historical approximations.
- Wallets came from current-session leaderboards, creating retrospective
  selection bias.
- Only 6–11 trades entered the portfolio in realistic scenarios after behavior,
  resolution, tape, price, and risk filters.

**Results:**

- Theoretical 0-second scenarios lost about $8.46–$8.57.
- Five-second scenarios lost about $1.57–$5.32.
- Fifteen-second scenarios lost about $2.47–$7.20.
- Sixty-second scenarios ranged from a $2.60 loss to a $0.26 gain.
- The 60-second, 1¢ and 2¢ positive results used only six trades and had a 33.3%
  win rate.
- All six execution-eligible signals in the 60-second, 1¢ diagnostic came from
  one wallet; category metadata was unknown.

**Interpretation:** The result is fragile and statistically insufficient. The
small positive 60-second cases do not demonstrate an edge because nearby
scenario assumptions are negative, the sample is only six trades, and one
wallet supplies all eligible evidence.

**Decision:** Do not claim profitability and do not proceed to real money.
Continue prospective testing until at least 100 resolved, strategy-eligible
paper trades exist, with at least 30 from outside the dominant wallet and more
than one market category represented.

## 2026-07-24 — Specialist consensus historical replay

**Research question:** Does an outcome become historically copyable when
multiple current top-P&L traders from the same Polymarket category buy it within
six hours?

**Method:**

- Compared current top-10 PNL cohorts for Politics, Economics, Tech, Sports,
  and Crypto.
- Counted one equal vote per distinct wallet; trade size provided no extra vote.
- Rejected a condition when opposing tokens both reached consensus.
- Used 2, 3, and 4 wallet thresholds; 15- and 60-second delays; and 0¢, 1¢,
  and 2¢ adverse price stress.
- Revealed outcomes only for hold-to-resolution settlement.
- Added a second, strictly past-only directional gate: 30 prior observations,
  at least 75% buys, and a low rapid-reversal rate.

**Evidence collected:**

- 120,000+ archived wallet-history rows across the research database.
- Crypto was expanded to 84,129 cohort rows spanning March 9–July 24, 2026.
- The unfiltered crypto control generated 296 two-wallet consensus events;
  113 were resolved and 40 were copyable at 60 seconds plus 1¢.
- That control lost $40.1708 on $40 of requested notional and won 2.5%.
- Most accepted losses were short-duration crypto Up/Down contracts; 33 of 40
  fills were below 25¢.
- After the past-only directional gate, crypto produced seven two-wallet
  events, four resolved events, no 60-second fills, and no three-wallet events.
- The directional three-wallet main setting had no accepted resolved entries
  in any niche.

**Interpretation:** Broad agreement among current leaders is not a directional
edge. It largely captures liquidity, inventory, hedging, or linked behavior.
Filtering for directional behavior removes the damaging control pattern but
also removes nearly all testable consensus.

**Decision:** Reject broad leaderboard consensus copying. Keep the directional
consensus detector as a paper-only monitor, but do not deploy or fund it from
this evidence.
