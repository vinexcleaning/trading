# POST_SETTLEMENT_FIELDS.md

Every field on a Kalshi market or event record whose value is only knowable at
or after settlement, or which keeps moving until then. Derived from the live
schema (`GET /trade-api/v2/markets`, 43 keys observed on a settled tennis
market) plus fields computed over a market's lifetime.

**The rule this document exists to enforce:** none of these may appear in a
filter, sort, dedupe, sample, join key, or any other decision about *which rows
enter an analysis*. Using them as a label is fine. Using them in output is fine.
Using them to choose the sample is the bug that voided Phase 2.

---

## Unsafe: value is only settled at settlement

| field | why it is unsafe |
|---|---|
| `result` | the outcome itself. Fine as a label, never as a selector of which rows to keep beyond "is it decided yet" |
| `settlement_value_dollars` | the payout. Same as `result` but numeric, so it slips into arithmetic more easily |
| `expiration_value` | the winning player's name. A string version of the answer |
| `settlement_ts`, `settlement_timer_seconds` | exist only once settled |
| `last_price_dollars` | **the single most dangerous field.** On a settled market this is the final trade, ~0 or ~100. Selecting the higher-`last_price` side picks the winner **99.89%** of the time (z = +140). Measured, not theorised |
| `previous_price_dollars`, `previous_yes_bid_dollars`, `previous_yes_ask_dollars` | the tick before the last one. Same problem, one step removed |
| `yes_bid_dollars`, `yes_ask_dollars`, `no_bid_dollars`, `no_ask_dollars` | on a *settled* record these are the final quotes, not live ones. Safe only when read from a candlestick at a stated timestamp |
| `yes_bid_size_fp`, `yes_ask_size_fp` | as above, final book state |

## Unsafe: monotone accumulators over the market's life

| field | why it is unsafe |
|---|---|
| `volume_fp` | **the Phase 0 bug.** Kalshi runs a separate order book per side, and trading concentrates in the side that is winning. Higher-volume side wins **53.56%** (z = +10.0) |
| `volume_24h_fp` | same mechanism, shorter window, still post-hoc when read off a settled record |
| `open_interest_fp` | **worse than volume.** Higher-OI side wins **55.58%** (z = +15.8) |
| `liquidity_dollars` | an accumulator in principle. Measured here at **50.31%** (z = +0.88), i.e. clean on this dataset — but it reads 0 on most settled tennis markets, so its innocence is an artifact of being empty, not a property to rely on |
| `updated_time` | last mutation; later for markets that stayed active longer |

## Unsafe: endpoints and durations

| field | why it is unsafe |
|---|---|
| `close_time` | the market's actual close, which for tennis is roughly the match end. A long match closes later than a short one that started at the same time. Safe as a *time coordinate* for a temporal split; unsafe the moment it is used to filter |
| `expiration_time`, `latest_expiration_time` | as above |
| `status` | `finalized` vs `active` distinguishes decided from undecided. Filtering to decided markets is required to have a label at all and does not select *which* outcome — the one member of this list that is routinely fine |
| **derived**: match duration, number of price changes, "did the price ever move" | not API fields but computed from the full series, so they are post-settlement by construction. In this project `dur_min` and the `plausible` filter are exactly this |

---

## Near-misses — the trap that actually caught me

**These field names are safe in one context and unsafe in another, and the name
does not tell you which.**

| pattern | safe | unsafe |
|---|---|---|
| `volume` | read from a **candlestick** at time *t*, used as a feature at time *t*. `stage0_audit.py:88` does this correctly (`volume_pre` from the last candle at or before the anchor) | read from a **settled market record** and used to choose a row. `p0_universe.py` did this and it voided Phase 2 |
| `open_interest` | same distinction | same |
| bid / ask / spread | from a candlestick at a stated timestamp | from a settled record, or from a "pre-match" anchor that is not actually pre-match. `stage4_kalshi_liquid.py` filtered on a spread taken from the file already known to be a look-ahead leak — a selection leak sitting on a feature leak |
| `close_time` | ordering matches in time | filtering matches |

The distinction is **when the value was observed**, never what it is called. A
field is safe if you can name the timestamp at which you knew it and that
timestamp precedes the decision. If you cannot name that timestamp, treat it as
post-settlement.

---

## Enforcement

`src/leakguard.py` provides two importable assertions:

- `assert_side_choice_neutral(kept_won)` — for picking one of two mirrored
  sides. Null is exactly 0.50.
- `assert_selection_neutral(mask, outcome, implied)` — for any filter. A filter
  may change *who* is in the sample; it may not change the calibration residual.

Both are wired into `p0_universe.py` and covered by `tests/test_leakguard.py`.
