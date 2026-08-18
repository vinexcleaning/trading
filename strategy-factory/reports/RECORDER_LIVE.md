# The wide recorder is live — 19 market families to 3,438, on the first night

**Launched 2026-08-18 05:14 UTC.** These are the first real cycles, read back
off the tape rather than predicted.

---

## What is on tape after the first cycles

| | before | now |
|---|---|---|
| Kalshi families with **any** price on tape | **19** | **3,438** |
| Kalshi families with the **full order-book ladder** on tape | 19 (`bot-hunt`) | 19 **+ 36 more** |
| markets captured in one sweep | ~1,359 listed / 719 probed | **83,698** |
| categories with nothing recorded | crypto, economics, financials, commodities, politics, elections, entertainment, companies | **none** |

> ⚠ **The first two rows are not the same measurement, and "19 to 3,438" would
> be flattering if read as one.** `bot-hunt` records its 19 at full depth,
> alongside Pinnacle and Polymarket on one clock. This records 3,438 at **top
> of book only** and 36 at depth, Kalshi alone. The honest sentence: **families
> with any price history at all went from 19 to 3,438; families with a full
> order book went from 19 to 55.**

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
economics, anything* rather than sports alone.

Sports is **42,126 of the 83,698 markets recorded on 2026-08-18 — about
half**, not the eighth an earlier draft of this file claimed. That draft
counted **families** (918 of 3,438, which is 27%) and then wrote the answer as
a share of **markets**. Both numbers are real and they are not the same
number: **by families sports is about one in four; by markets it is about one
in two.**

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

**And the structural check — SF008's canary, run on the recorded tape.** A bid
at or above an ask is impossible on a functioning exchange, and on Kalshi both
sides are quoted as bids with the YES ask derived as 100 minus the best NO bid,
so a crossing means the two ladders have gone inconsistent.

| | snapshots checked | crossed |
|---|---:|---:|
| tier A, both sides sized above zero | 1,800 | **0** |
| tier B, top of book | 83,698 | **0** |

**85,498 snapshots on 2026-08-18, not one crossed book.**

> ⚠ **An earlier draft of this file reported a different check under the same
> name.** It verified that each stored ladder is ascending in price — 1,270
> ladders, 0 violations — and called that "SF008's canary". It is not.
> Ascending order is how the endpoint returns the levels, so that check is
> close to tautological: it would catch a parse error and nothing else. Worth
> keeping for exactly that reason, worth nothing as evidence about the market.
> The table above is the real canary; the ladder check is a parse check and is
> labelled as one.

## What is NOT established by any of this

- **Nothing about whether any of these markets is worth trading.** Not one
  strategy has been screened. This is tape, not a result.
- **Nothing about disk over a month.** These are the first cycles. The real
  number comes from `w_cycle` after 24 hours and replaces the projection in
  `SHAPE.md`. WARNING - the change rate this project has measured is NOT the
  right one for this tape. The 2.5%-in-300-seconds figure in `SHAPE.md`
  (measured 2026-08-18 across two full sweeps) was computed over **all 768,262
  markets present in both sweeps, including the ~700,000 parlay markets that
  essentially never move** - and those are exactly the markets this recorder
  drops. The change rate over the 83,698 markets actually recorded will be
  **higher, probably much higher**, so any disk projection resting on 2.5% is
  an underestimate and should not be quoted. What replaces it is
  `w_cycle.n_changed` on the second and later cycles, which needs no new
  measurement. `devig`'s separate finding - Kalshi is **0.53% of every row** in
  their 65 GB database, measured 2026-08-18 - still says disk was never the
  wall for Kalshi book data, and that is the reassuring half.
- **Nothing about whether the two recorders are competing for request rate.**
  `w_health.http_ok` and the non-200 count are where that would show, and
  nobody has looked yet. `devig`'s warning stands: the 15 requests/second
  ceiling is **recorded, not verified**.
- **A family absent from the tier list is a recording priority, not a verdict**
  (GUARDS #15). The drop list is re-measured on every rebuild and names every
  family it excluded, with counts, in `TIERS.md`.

---

# The Critic and the Referee

`CLAUDE.md` §6b. The Critic is not allowed to be fair; the Referee produces
three lists and never resolves a real disagreement. Both were run on this file
before it went anywhere.

## 1. STANDS

- **The list endpoint carries a real quote.** 168 markets across 23 series and
  every category, 2026-08-18. What makes it survive: **zero** cases of the
  failure that would kill it — the list blank while the book was quoted — and
  the one place it does fail was found and is named rather than averaged away.
- **The best-of-N correction.** What makes it survive: **two independent
  methods that agree** — a simulation and an exact binomial tail with no
  simulation in it — both on `common/kalshi_fees.py`, the repo's only fee
  implementation.
- **90% of Kalshi's open markets are two parlay families.** What makes it
  survive: it is a census, not a sample. 784,814 open markets, exact counts.
- **The recorder is running and the tape is real.** What makes it survive: it
  was **read back**, not counted — a stored ladder shows 20 priced levels with
  sizes, and 85,498 snapshots contain not one crossed book.

## 2. DOWNGRADED — rewritten here, not merely flagged

- **was:** "Kalshi families recorded: 19 → 3,438."
  **now:** "Families with **any** price history went from 19 to 3,438. Families
  with a **full order book** went from 19 to 55."
  **because:** `bot-hunt`'s 19 are full depth alongside Pinnacle and Polymarket
  on one clock. These 3,438 are top-of-book, Kalshi alone. Reporting one number
  invites the reader to assume the stronger measurement.

- **was:** "Sports is now 12% of what is being recorded."
  **now:** "Sports is about **one in four by families** (918 of 3,438) and
  about **one in two by markets** (42,126 of 83,698)."
  **because:** I counted families and wrote the answer as a share of markets.
  Two real numbers, and neither is 12%.

- **was:** "1,270 ladders checked, 0 violations — SF008's canary passing on its
  first night."
  **now:** "SF008 is **85,498 snapshots, 0 crossed books**. The ladder-ascending
  check is a **parse check**, near-tautological because that is the order the
  endpoint returns, and it is labelled as one."
  **because:** they are different checks and I gave the weak one the strong
  one's name. That is how a tautology gets cited later as evidence about a
  market.

- **was:** "Disk should be small — the measured change rate is 2.5% in 300
  seconds."
  **now:** "That 2.5% was measured over **all 768,262 markets**, including the
  ~700,000 parlay markets that never move — **exactly the markets this recorder
  drops.** The rate over the 83,698 actually recorded will be higher, so any
  projection resting on 2.5% is an underestimate and should not be quoted."
  **because:** the measurement's population is not the recorder's population.
  The replacement needs no new work: `w_cycle.n_changed` from cycle 2 onward.

## 3. FOR THE USER — genuinely unresolved

**One item, and it is not a disagreement.** Three of the four idea sources are
running — market-structure reasoning, the extractors, and the claims `reopen`
found were closed for the wrong reason. The fourth is his, and nothing here can
substitute for it:

> **Which markets does he actually know something about that the numbers would
> not tell us?** Not which he likes — which ones *behave differently*, and why.
> A league where the favourite means something different. A competition where
> teams stop trying once they are through. A time of day when the price moves
> for a reason that is not news.

**Nothing else is unresolved, and that is said out loud rather than left off.**
The one place two chats could have disagreed — `devig`'s ask for concurrency
before breadth — is not a disagreement about a fact. Their arithmetic is right
and it is in `STATUS.md`; this recorder declines the concurrency **because of
their own warning**, and gets its headroom from one request per sweep instead.
Nothing there needs him.
