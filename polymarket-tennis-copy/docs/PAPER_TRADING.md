# Paper trading: assumptions and limits

**Nothing in this system places a real order.** There is no signing key, no
order-placement code path, and no venue write API in the provider. Paper trading
is simulation, and its results are labelled as such everywhere they appear.

---

## How a simulated fill is produced

1. A signal qualifies (every alert gate passes).
2. The configured **execution delay** is applied to the signal's detection time
   — not to the wallet's trade time. The follower's clock starts when the system
   *noticed*, which is the honest starting point.
3. The price at that moment is resolved through the tiered evidence model. If no
   usable price exists, **the entry is refused** rather than filled at a guess.
4. Available depth is probed first, so the risk manager can cap the stake to what
   is actually fillable.
5. The fill price is estimated by walking the real order-book ladder when a
   snapshot exists, otherwise from a modelled spread + slippage.
6. Fees are applied if configured.
7. The position opens, with the evidence tier and data confidence recorded on the
   row.

Refusals are stored as `rejected` paper trades with a reason, not discarded. A
strategy that looks good only because impossible fills were assumed is not a
strategy, so the refusals are part of the result.

## Exit strategies

| Strategy | Rule |
|---|---|
| `hold_to_resolution` | Settle at $1 or $0 (default) |
| `follow_wallet_exit` | Exit when **every** source wallet has exited |
| `profit_target` | Fixed profit target |
| `stop_loss` | Fixed stop |
| `fixed_hold` | Time-based |
| `consensus_gone` | Exit when agreement disappears |
| `wallet_reduces` | Exit when a source wallet trims |
| `trailing_stop` | Configurable trailing logic |

Resolution is checked **first and unconditionally**: once a market settles, every
strategy closes at $1 or $0 regardless of its own rule.

`follow_wallet_exit` requires *all* source wallets to be out. One member of a
consensus leaving should not close a position the rest of the group still holds.

## Risk controls (defaults)

| Control | Default |
|---|---|
| Stake per signal | $5 |
| Max exposure per market | $20 |
| Max total open exposure | $50 |
| Max simultaneous positions | 10 |
| Daily loss cap | $25 |
| Duplicate entries per signal | Disabled |

Also enforced structurally:

- **No martingale.** Size never increases after a loss.
- **No confidence-scaled sizing.** A high score does not buy a bigger stake.
- **No position above modelled depth.** If the book cannot absorb the stake, the
  stake is reduced and the row is flagged `stake_reduced_for_liquidity`.

These are simulation defaults chosen to be conservative. They are **not**
recommendations for real money.

## The headline comparison

Every closed paper trade records `wallet_roi` and `roi_gap_vs_wallet`
(follower minus wallet). Aggregated, this is the measured **cost of being late** —
the number the whole product exists to produce.

## Why simulated results will differ from real execution

- Queue position and hidden liquidity are not observable.
- Latency is a single configured constant, not a distribution.
- Fills are instantaneous at the delay; real partial fills take time.
- The follower's own market impact beyond the visible ladder is not modelled.
- Fees are venue- and market-specific; the default is 0 bps.
- A real operator faces outages, rate limits and rejected orders.

Treat paper P&L as an upper bound on what the same rules would have produced
live.
