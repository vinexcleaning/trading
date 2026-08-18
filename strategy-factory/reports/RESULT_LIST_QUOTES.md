# The Kalshi list endpoint DOES carry a real quote — and a document in this repo says it does not

**Measured 2026-08-18 by `strategy-factory/src/verify_list_quotes.py`.**
Reproduce with:

```bash
py -3 strategy-factory/src/verify_list_quotes.py
```

---

## What the repo currently says

`bot-hunt/src/venues.py`, in the module docstring, in the list of inherited
traps that each cost a prior session real time:

> Kalshi list endpoints null out bid/ask; quotes only come off the per-market
> orderbook endpoint. (Independently reported by a Reddit cross-venue bot
> author, and consistent with the field-name policy above.)

## What is actually true today

`/markets` returns `yes_bid_dollars`, `yes_ask_dollars`, `no_bid_dollars`,
`no_ask_dollars`, `yes_bid_size_fp` and `yes_ask_size_fp` on every open market,
and those values agree with the per-market orderbook.

**168 markets, 23 series, deliberately spread across every category** —
baseball, tennis, esports, American football, weather, three crypto families,
two stock indices, inflation, Federal Reserve, a House race, and both of the
combinatorial parlay families:

| | |
|---|---|
| bid agrees with the orderbook, within one tick | **168 of 168 — 100%** |
| ask agrees with the orderbook, within one tick | **158 of 168 — 94%** |
| **list blank while the orderbook has a quote** | **0 of 168** |
| worst disagreement seen anywhere | **1 tick** |

The last two rows are the ones that matter. The failure that would have killed
this — the list quietly reporting nothing on markets that do have a book — did
not happen once.

### Where the 6% is, and it is not a defect

Every disagreement is one tick, and they concentrate in two places:

1. **Live markets that moved between the two requests.** The list quote and the
   orderbook are two separate HTTP calls about 200 ms apart. One ITF tennis
   market moved a cent in that window. That is not a wrong field, it is a
   market.
2. **The two parlay families.** `KXMVECROSSCATEGORY` and
   `KXMVESPORTSMULTIGAMEEXTENDED` show a **stale list quote against an empty
   orderbook** — 7 list quotes against 2 live books in one, 4 against 0 in the
   other. On those two families the list ask should not be trusted.

Those two families are excluded from the factory's recorder anyway, for an
unrelated and much larger reason (they are 90% of the exchange's open markets
and almost none of them have a counterparty — see `reports/TIERS.md`). But
**a family where the list quote is stale is a real caveat and it belongs beside
the finding, not buried under it.**

---

## Why it matters enough to write down

It is the difference between two worlds.

| | per-market orderbook | list endpoint |
|---|---|---|
| markets per HTTP request | 1 | up to 1,000 |
| one pass over every open Kalshi market | **~81 hours** | **~10 minutes** |
| gives depth | yes, the whole ladder | no, top of book only |

Recording the whole exchange was arithmetically impossible under the first
column and is routine under the second. That single fact is the reason the
factory can widen from 19 families to hundreds this week instead of arguing
about which twenty to pick.

**It does not replace the orderbook endpoint.** The list gives the top of book
and nothing else, so every question about depth — capacity, book shape, what
$500 actually costs in a thin market — still needs a ladder walk. That is what
the recorder's tier A is for, and every recorded row carries a `src` column
saying which endpoint it came from so the two can never be silently mixed.

---

## What I am NOT claiming

- **Not** that the docstring was wrong when it was written. Kalshi has changed
  its field names before — that is the whole reason `venues.py` warns about
  `*_dollars` and `orderbook_fp` in the first place. This is a measurement of
  today.
- **Not** that 168 markets settles it for all 13,133 series. It settles it for
  the 23 measured, and it found the one family type where it fails. A family
  being recorded for the first time should be spot-checked the same way.
- **Not** that top-of-book is as good as a ladder. It is strictly less
  information, and the tier split exists because of that.

---

## What should happen to the docstring

`bot-hunt/` belongs to the `devig` chat and this session does not edit it.
**Filed to `coordinator/mailbox/devig/` as a message, with this file as the
evidence.** The docstring is not merely stale — it is in a list of traps that
exists precisely so nobody re-derives them, so a wrong entry there is more
expensive than a wrong entry anywhere else in that file. It caused no harm to
`bot-hunt` itself, which correctly uses the orderbook endpoint for the depth it
needs; the cost is entirely to anyone who reads it and concludes that breadth
is unaffordable.
