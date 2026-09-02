# THE VENUE MAP — what else exists, and what its fees are ON PAPER

**Desk research, 2026-09-01.** `coordinator` mailbox 010 split this job:
**the reading is mine, the fee verification is `devig`'s.**

---

## ⚠ READ THIS BEFORE USING ANY NUMBER BELOW

> **A fee you read in documentation is a CLAIM. A fee measured against real
> fills is EVIDENCE.**

**This repo has already proved its own reading wrong on exactly this point.**
LEDGER **C004** measured Polymarket's real charged fee on **4,310 on-chain
fills** at `0.10 × min(p, 1−p)` — and found the *documented* formula matched
**0.0% of them**. **BH025** read the docs three days ago and got a third number.

**So every fee on this page is tagged `DOCS-ONLY`** with the URL and the date I
fetched it. **None of it may enter an "executable after fees" column** until
`devig` measures it against fills. That is not caution for its own sake: an
assumed fee is how a fake edge survives review.

**Official APIs and published terms only.** Nothing here was obtained by
bypassing any access restriction.

---

## ⚠ THE FINDING THAT CAME OUT OF THIS, AND IT IS NOT ABOUT ANOTHER VENUE

**It is about Kalshi, it is measured rather than read, and it goes the
UNUSUAL direction — it makes a cost SMALLER.**

Kalshi publishes `fee_multiplier` on every series and **actually uses it**:

| multiplier | series | what it means |
|---|---:|---|
| 1.0 | 13,100 | standard 0.07 taker rate |
| **0.5** | **19** | **half fee — 0.035** |
| **0.0** | **14** | **genuinely free** |

**Every one of the 19 half-fee families is BASEBALL** — `KXMLBGAME`,
`KXMLBTOTAL`, `KXMLBKS`, `KXMLBRFI`, `KXMLBTB`, `KXMLBSPREAD` and 13 more.

**Verified against the live `/series/{ticker}` endpoint on 2026-09-01**, not
just off a census snapshot: `KXMLBGAME` returns `fee_multiplier=0.5`,
`taker_rate=0.035`, while `KXATPMATCH` and `KXINXU` return 1.0.

**At 50 cents that is 0.875c per contract instead of 1.75c. Half.**

`common/kalshi_fees.py` has supported this the whole time through
`SeriesFees.taker_rate`. **Nothing in the repo calls it that way** —
`mlb-paper` uses the bare `fee_order_cents(price, n)` at the default rate in
six places, and so did this engine until today. Filed to `STATUS.md` for `mlb`
and `livedesk`, the two projects that trade baseball.

**And the 14 zero-fee series are worth a look on their own**, because the
fee-curvature lens is trivially maximal where the fee is nought: `KXGDPYEAR`
(118 two-sided markets, on my full-depth tier), `KXBTCY` (28), `KXETHY` (18),
plus a dozen thin political ones.

### One docs-versus-API case, resolved by the API

Kalshi's own newsroom announced *"we're halving the fees for our S&P and Nasdaq
markets... from 1.75c to 0.875c per contract at the midpoint"* — dated
**2022-09-22**
([news.kalshi.com](https://news.kalshi.com/p/were-halving-the-fees), fetched
2026-09-01). **The live API says `KXINXU` and `KXNASDAQ100U` are multiplier
1.0 today.** The announcement is either about a superseded product or has since
been reversed. **The API won; the news post is a claim.**

---

## KALSHI — the venue this repo already trades

| | |
|---|---|
| **regulator** | CFTC-designated contract market (US) |
| **fee formula** | `0.07 × contracts × p × (1−p)`, **times the series `fee_multiplier`** |
| **maker fee** | only on `fee_type = quadratic_with_maker_fees` — **130 of 13,133 series**, at 25% of taker |
| **settlement fee** | **none** — *"There is no settlement fee"* |
| **rounding** | rounded **UP per ORDER**, not per contract |
| **order book** | yes, public and unauthenticated |
| **history** | ~69-day rolling window; a closed market 404s |
| **source** | [help.kalshi.com fees](https://help.kalshi.com/en/articles/13823805-fees), [fee schedule PDF](https://kalshi.com/docs/kalshi-fee-schedule.pdf), [API fee rounding](https://docs.kalshi.com/getting_started/fee_rounding) — fetched 2026-09-01 |
| **status** | **EVIDENCE**, not docs-only — this repo's `common/kalshi_fees.py` was resolved empirically against real fills |

**The no-settlement-fee line is an independent confirmation of something this
folder argued from the code**: `DECISIONS.md` D6 held that a buy-and-hold pays
the entry fee only. Kalshi's own help centre says so in as many words.

---

## POLYMARKET — and the fee is PER CATEGORY, which nothing here knew

**⚠ DOCS-ONLY.** [docs.polymarket.com/trading/fees](https://docs.polymarket.com/trading/fees),
fetched **2026-09-01**.

Formula as published: **`fee = C × feeRate × p × (1 − p)`** — the same shape as
Kalshi's, with a **different coefficient per category**:

| category | taker rate | maker rate |
|---|---:|---:|
| Crypto | **0.07** | 0 |
| Sports | **0.05** | 0 |
| Economics · Culture · Weather · Other | 0.05 | 0 |
| Finance · Politics · Mentions · Tech | **0.04** | 0 |
| **Geopolitics** | **0** | 0 |

*"Makers are never charged fees. Only takers pay fees."* Fees round to 5 decimal
places; the smallest charged is 0.00001 USDC, so very small trades near the
extremes may pay nothing.

**Why this matters to the repo:** `BH025` recorded Polymarket sports as
`C × 0.05 × p × (1−p)`, which matches the Sports row — **but the repo has been
treating that as *the* Polymarket fee.** It is one of five different
coefficients, and crypto is 40% higher than sports.

**⚠ And it is still DOCS-ONLY.** C004 measured `0.10 × min(p, 1−p)` on 4,310
real fills and found the documented formula matched **none of them**. Whether
that gap has closed since is `devig`'s measurement to make, not mine to assume.

---

## THE REST — named, not characterised, because I could not verify them properly

**I am not going to fill this table from marketing pages.** What follows is a
list of what exists with the one thing I can honestly say about each. **Every
row needs its own docs fetch before it is worth anything**, and several are the
kind of "top 10" listicle that this repo's own `GUARDS.md` #25 warns about.

| venue | what it appears to be | verified? |
|---|---|---|
| **Polymarket US** | the CFTC-regulated domestic version | ⚠ third-party claim only — the fee table above is from the main docs, and whether the US entity differs is **unchecked** |
| **Limitless** | on-chain order-book exchange | **unverified** |
| **Manifold** | community forecasting, **play money** — so no fee question and no money question | listed to be ruled out |
| **Augur** | on-chain, long-standing | **unverified, and possibly dormant** |
| **Robinhood** | brokerage offering event contracts | **unverified** |
| **DraftKings** | sportsbook entering prediction markets | **unverified** |
| **OG.com** | licensed sports-trading platform | **unverified** |

**Source for the existence of this list only:**
[track360](https://track360.io/blog/prediction-market-operators-landscape-polymarket-kalshi-alternatives-2026),
[finextra](https://www.finextra.com/blogposting/31734/best-polymarket-alternatives-in-2026-kalshi-pariflow-manifold-amp-more),
[defirate](https://defirate.com/prediction-markets/) — fetched 2026-09-01.
**These are commercial listicles and several are affiliate-shaped. They are
adequate evidence that a venue EXISTS and adequate for nothing else.**

---

## What this map does NOT establish

- **No fee here except Kalshi's is evidence.** Polymarket's is a careful reading
  of official documentation that this repo has already caught being wrong once.
- **Nothing about whether any venue is worth trading.** Cross-venue pairs
  generate candidates fast, and **the count of pairs screened is what stops the
  best one being mistaken for a finding** — the best of 2,000 zero-skill
  strategies typically looks like +29.5%.
- **Nothing about legal or geographic eligibility**, which I have deliberately
  not summarised from third-party pages.
- **Nothing about the seven unverified venues** beyond that they appear to
  exist.

## What should happen next

1. **`devig` measures the Polymarket per-category rates against real fills**, as
   they are already doing for the sports coefficient.
2. **`mlb` and `livedesk` apply the 0.5 baseball multiplier** — see `STATUS.md`.
3. **One docs fetch per unverified venue**, each recording API availability,
   order-book access, min/max size, settlement rules and the published fee with
   its URL and date. That is a bounded job and it is next on this folder's list.
