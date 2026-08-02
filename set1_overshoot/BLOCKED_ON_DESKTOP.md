# BLOCKED_ON_DESKTOP.md

Selection-leak checks that cannot be run from this laptop. The code lives on the
desktop under `C:\Users\vinig\kalshi` and siblings; the only profile here is
`gianf`, and `C:\Users\gianf\kalshi` is the unrelated Stage 0–5 tennis project.

Confirmed absent by recursive search of `C:\Users\gianf` for
`v3|copytrad|copy_trad|wallet|structural|backtest`: only four Polymarket files
matched, none of them the work below.

**The test to run in every case is the same one that caught the Phase 0 bug:**

```python
from leakguard import assert_side_choice_neutral, assert_selection_neutral
assert_side_choice_neutral(kept_won, "name")        # null exactly 0.50
assert_selection_neutral(mask, outcome, implied)    # residual must not shift
```

Copy `src/leakguard.py` and `tests/test_leakguard.py` across first.

---

## 1. v3 structural-event backtest — PRESUME VOID until checked

**Why it is the highest risk item.** It deduped mirrored Kalshi markets, which
is exactly the operation that failed here, on the same exchange, in the same
sport, over a 14,162-market pull.

Find the dedupe and answer one question: **which field orders it?**

| if it sorts on | P(kept wins) measured here | verdict |
|---|---|---|
| `last_price_dollars` | 0.9989, z = +140 | catastrophic, results meaningless |
| `open_interest_fp` | 0.5558, z = +15.7 | void |
| `volume_fp` | 0.5356, z = +10.0 | void — identical to the Phase 0 bug |
| ticker / name / API order | ~0.50 | clean |

Grep targets:

```
sort_values.*volume | sort_values.*open_interest | sort_values.*last
nlargest | idxmax | drop_duplicates | groupby(...).head(1)
```

Then run the canary on its universe and record the z.

**Also check**: if it splits results by orientation (which side of the mirror is
the favourite), re-run that split. A 25 pp gap between the two halves is the
signature; a pooled number can look almost innocent while both halves are wrong.

## 2. Copy-trading / wallet work — check the ranking field and its timing

The favourite–longshot conclusion depended on which fills entered the sample, so
the selection rule is load-bearing.

Check, in order:

1. **How wallets were ranked.** If by realised PnL, win rate, ROI or any
   lifetime aggregate, the ranking is computed after the outcomes it is used to
   select on. The correct form is a rank computed on a strictly earlier window,
   evaluated out of sample on a later one.
2. **How trades or fills were selected.** Any filter on trade size, fill price,
   or "was this trade profitable" is post-settlement.
3. **Which side of a market a fill was attributed to**, and whether that
   attribution used the settled price.
4. **Survivorship among wallets**: are wallets that stopped trading, or went to
   zero, still in the sample? If the wallet list was pulled *now*, wallets that
   blew up may be absent, which inflates every aggregate.

The null for a wallet ranking is not 0.50. It is: *a ranking built on window A
must not predict outcomes in window A better than it predicts window B.* Use
`assert_selection_neutral` with the outcome and the market-implied probability.

## 3. Kalshi order-book recordings — check before trusting, unrelated axis

Carried forward from `crypto/BLOCKED_ON_DESKTOP.md` because it is still open and
would invalidate the recordings independently of any selection issue:

Kalshi's legacy price fields now return `None`. Any desktop code reading
`yes_bid` / `yes_ask` / `last_price` / `volume` / `open_interest` from
`/markets` is silently getting `None`; the live values moved to
`yes_bid_dollars` / `yes_ask_dollars` / `volume_fp` / `open_interest_fp`. Check
`kalshi_client.py` and `record_data.py`. If the recorders have been writing
`None`, the recorded books are worthless — same shape as this project's earlier
orderbook-parser corruption, where row counts were right and content was empty.

## 4. Crypto — only the laptop copy was audited

`C:\Users\gianf\crypto\src` audited and clean on this axis (§ SELECTION_AUDIT.md
rows 24–27). The desktop holds the ~1.77M recorded trades, the 27,083-observation
recorder dataset and the 94 live trade records. Any analysis built on those
needs the same audit; in particular, **the 94 live trade records are the only
ground truth on realised fills**, and if they were selected by outcome in any
way, every fill-model calibration derived from them inherits it.

---

## Run order on the desktop

1. Copy `leakguard.py` + tests; run `pytest`.
2. v3 backtest dedupe → one grep, one canary. Fastest way to void or clear a
   whole result set.
3. Copy-trading wallet ranking → the timing question in §2.1.
4. `None`-price check on the recorders (§3) — one grep, and it gates everything
   Tier B.
