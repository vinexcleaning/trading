# The wide recorder is live — 19 market families to 3,438, on the first night

**Launched 2026-08-18 05:14 UTC.** These are the first real cycles, read back
off the tape rather than predicted.

---

## What is on tape after the first cycles

| | before | now |
|---|---|---|
| Kalshi families recorded at all | **19** | **3,438** |
| Kalshi families recorded at full order-book depth | 19 (`bot-hunt`) | 19 **+ 36 more** |
| markets on tape in one sweep | ~1,359 listed / 719 probed | **83,698** |
| categories with nothing recorded | crypto, economics, financials, commodities, politics, elections, entertainment, companies | **none** |

`bot-hunt`'s 19 families are **untouched**. This adds; it does not replace, and
it writes its own database files.

## Coverage, by category, off the tape

| category | series | markets |
|---|---:|---:|
| Sports | 918 | 42,126 |
| Elections | 593 | 11,387 |
| Financials | 486 | 10,050 |
| Entertainment | 308 | 6,609 |
| **Crypto** | **78** | **4,010** |
| **Economics** | **240** | **3,183** |
| Politics | 478 | 2,107 |
| **Commodities** | **37** | **1,288** |
| Science and Technology | 127 | 917 |
| Climate and Weather | 100 | 887 |
| Mentions | 30 | 533 |
| Companies | 36 | 394 |
| (unclassified) | 2 | 202 |
| World / Social | 5 | 5 |

**The bolded rows had zero tape before tonight.** His ask was *crypto, weather,
economics, anything* rather than sports alone; the sports row is now 12% of
what is being recorded rather than all of it.

## The two tiers, and what each actually cost

| | tier A — depth | tier B — breadth |
|---|---|---|
| stores | the **whole ladder**, both sides, as JSON | top of book with sizes |
| families | 36 | 3,438 |
| requests per cycle | 900 | ~785 |
| **measured cycle time** | **257 s and 338 s** | **940 s** (first cycle writes everything) |
| interval | 600 s | 1,800 s |
| database | `data/wide_depth.db` | `data/wide_top.db` |

**Two database files, not one.** Two writers on one SQLite died here with
`database is locked` inside 19 minutes on 2026-08-09. Analysis joins them with
`ATTACH`, which costs nothing.

## The tape was read back, not just counted

A row count is not a result — GUARDS #12 exists because a parse bug wrote real
row counts with empty content for 1h45m and was caught by accident. So:

**A real ladder, off the tape:**

```
KXINXU-26AUG18H1000-T7654.9999   bid 97.0  ask 99.0  levels 20/1  depth5 1050/1000
  ...[85.0, 1.0], [90.0, 111.11], [96.0, 1000.0], [97.0, 50.0]
```

Twenty price levels with sizes on the YES side. That is what makes *"what would
it cost to put $500 into this thin market"* answerable by walking the book
rather than by reading the top price — which was his explicit question.

**And a structural check, run on the recorded ladders rather than on live
data:** every stored YES ladder must be strictly ascending in price.
**1,270 ladders checked, 0 violations.** That is SF008's canary passing on its
first night, and it is the cheapest evidence available that the two sides are
not being confused for each other.

## What is NOT established by any of this

- **Nothing about whether any of these markets is worth trading.** Not one
  strategy has been screened. This is tape, not a result.
- **Nothing about disk over a month.** These are the first cycles. The real
  number comes from `w_cycle` after 24 hours and replaces the projection in
  `SHAPE.md`. The measured change rate — 2.5% of markets move in 300 seconds —
  says it should be small, and `devig`'s finding that Kalshi is 0.53% of every
  row in their 65 GB says disk was never the wall for book data.
- **Nothing about whether the two recorders are competing for request rate.**
  `w_health.http_ok` and the non-200 count are where that would show, and
  nobody has looked yet. `devig`'s warning stands: the 15 requests/second
  ceiling is **recorded, not verified**.
- **A family absent from the tier list is a recording priority, not a verdict**
  (GUARDS #15). The drop list is re-measured on every rebuild and names every
  family it excluded, with counts, in `TIERS.md`.
