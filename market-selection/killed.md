# killed.md — what was eliminated, and why

Dimension A is the kill switch. **A market with no counterparty is untradeable
at any edge size.** A prior study found weather markets with perfect free
settlement data going back to 2003 and zero fills; that result is reproduced
below with a mechanism attached.

Cost is **not** a kill switch — a large enough edge beats any cost — so
families are only killed on cost when the cost is so large that the required
edge is not plausibly attainable, and that is said explicitly each time.

## The gate, pre-registered

Fixed in [DECISIONS.md](DECISIONS.md) D8 **while the trade tape was still
downloading**, so it could not be fitted to the result. A family survives only
if it clears **all three**:

| Gate | Threshold |
|---|---|
| trades per day | ≥ 100 |
| distinct markets traded per day | ≥ 20 |
| two-sided quote uptime | ≥ 50% |

Evidence: the exchange-wide public trade tape, the continuous depth recorder
(85 families × 20 cycles), a one-shot depth sweep over the top 300 families by
trades/day, and a fresh re-probe of everything the sweep called dead.

---

## ⚠ First, a correction to my own kill list

The wide sweep picked tickers from a market dump taken at 02:12 UTC and probed
them ~5.5 h later. Short-lived families had already settled the markets it
chose, and **"no depth" on a settled market is a closed book, not an absent
counterparty**.

It called 37 families dead. Re-probed against fresh listings:

| Outcome | Count |
|---|---|
| **REVIVED — the sweep was wrong** | **19** |
| One-sided only | 16 |
| Confirmed no book | 2 |

**More than half the initial kills were wrong**, including **KXBTC15M — the
single busiest family in the tape at 1.19 M trades**, which is in fact quoted
two-sided at a 0.1¢ spread. Nothing below is killed on the stale probe alone.

---

## KILL 1 — No order book at all (the hardest kill)

| Series | Trades in tape | Open markets | Sampled | Two-sided | Any depth |
|---|---|---|---|---|---|
| **KXMVESPORTSMULTIGAMEEXTENDED** | **510,281** | 200 | 4 + 3 | **0** | **0** |
| **KXMVECROSSCATEGORY** | **136,326** | 200 | 4 + 3 | **0** | **0** |

These two are **82.9% of Kalshi's entire 419,828-market universe** (267,739 +
80,097) and they generate over half a million trades in the tape. And they have
**no public book whatsoever** — not a wide book, not a one-sided book, nothing,
across two independent probes hours apart on different tickers.

**Why:** they are combinatorial multi-leg parlays minted on demand. The trades
are real but they are not the product of a resting limit order book, so there
is nothing to place an order into and nothing to be filled against. Series-level
24 h volume reads **0.0** and two-sided quoting reads **0.1%**.

**Verdict: dead for any strategy that requires placing an order.** High trade
count is not a counterparty. This is the single most important thing the raw
trade counts get wrong, and it disqualifies the largest thing on the exchange.

---

## KILL 2 — One-sided books: the weather result, reproduced with a mechanism

Sixteen families quoted on **one side only** across 4 fresh markets each.
Eleven of them are weather:

| Series | Trades in tape | Open now | Sampled | Two-sided |
|---|---|---|---|---|
| KXHIGHLAX | 7,579 | 12 | 4 | **0%** |
| KXRAIN | 5,677 | 20 | 4 | **0%** |
| KXHIGHTSFO | 3,501 | 12 | 4 | **0%** |
| KXTEMPAUSH | 3,333 | 10 | 4 | **0%** |
| KXHIGHTSEA | 3,220 | 12 | 4 | **0%** |
| KXTEMPLAXH | 3,115 | 10 | 4 | **0%** |
| KXHIGHTLV | 2,172 | 12 | 4 | **0%** |
| KXTEMPNYCH | 1,834 | 10 | 4 | **0%** |
| KXTEMPDCH | 1,059 | 10 | 4 | **0%** |
| KXTEMPCHIH | 982 | 10 | 4 | **0%** |
| KXFOXNEWSMENTION | 6,876 | 15 | 4 | **0%** |
| KXTRUMPSAY | 4,693 | 17 | 4 | **0%** |
| KXTRUTHSOCIAL | 3,579 | 10 | 4 | **0%** |
| KXAFLGAME | 4,644 | 18 | 4 | **0%** |
| KXNEXTTEAMMLB | 2,106 | 200 | 4 | **0%** |
| KXWNBANEXTTEAM | 581 | 48 | 4 | **0%** |

**This is the mechanism behind the earlier zero-fill result.** The NWS API is
free, complete, and is the exact product Kalshi settles on — dimension D is
perfect. It does not matter. There is a price on one side and nothing on the
other, so a resting order sits unfilled and a marketable order has nothing to
lift. It reproduces LEDGER **C016** ("the cheap wings have an ask but no bid",
0 of 61 minutes two-sided) in a completely different category.

Note the correction inside this group: **KXHIGHDEN and KXHIGHTPHX revived**
(100% and 75% two-sided on fresh markets). Weather is not uniformly dead — it
is dead in most cities and quoted in a few. Killed as a *family*; the exceptions
are named.

**Verdict: killed on dimension A, with dimension D at its maximum.** This is
precisely why A is the kill switch and D is a ranking input.

---

## KILL 3 — Cost so high the required edge is implausible

Not killed for having a cost. Killed because the edge required is larger than
anything this project has ever measured as real.

| Series | Median spread | Cost bar at 50¢ | Edge needed |
|---|---|---|---|
| **KXLIGAEXPTOTAL** | **57.0¢** | 29.91¢ | ~30 pp |
| **KXLIGAEXPGAME** | **51.0¢** | 27.09¢ | ~27 pp |
| **KXUSLTOTAL** | **18.0¢** | 10.72¢ | ~11 pp |
| KXUSL1HTOTAL | 65.0¢ (n=3) | — | — |
| KXNPBSPREAD | 9.0¢ | ~6.3¢ | ~6 pp |

For scale, the largest genuine effect in the entire archive is the set-1 tennis
undershoot at **2.42 pp**, and it was uncollectable against a 3.61 pp bar. A
family needing 27 pp is not a candidate.

**Verdict: killed on C, stated as a cost kill, not a counterparty kill.**

---

## KILL 4 — Killed on dimension D: everyone has the same four numbers

| Family | Trades/day | Book quality | Why killed |
|---|---|---|---|
| **KXBTCD, KXETHD, KXBTC, KXBTC15M and the 15-minute crypto ladders** | up to **1.19 M** | tight, two-sided, 0.1–1.0¢ | **Four inputs total — price, strike, time, volatility — and every participant has all four.** Verified live: Binance (`data-api.binance.vision`), Coinbase, Kraken and Deribit's full options chain are all free and open. LEDGER **C010** already measured the consequence: no model beats the mid on 250 events, with a positive control (**C008**) proving the test would have found a 5% bias. |
| KXBTC15M specifically | 1,191,657 | 0.1¢ spread but **57 contracts at the touch** | additionally structurally dead per LEDGER: `floor_strike` equals the prior window's settlement in **99.86%** of 6,261 markets, so every contract is minted at the money on the peak of the fee curve |
| **KXPGATOUR / KXLPGATOUR / KXKFTOUR / KXPGATOP5/10/20** | 26,256 | excellent — 0.6¢ spread, 24,247 at touch, 690k within 5¢ | **The highest 24 h dollar volume on the exchange (23.2 M) and the free data is scores, not skill.** Strokes-gained — the only golf statistic with real predictive content — is behind DataGolf (**403, paid**). Every free GitHub PGA scraper found is stale (most recent push 2025-03-13). ESPN's golf scoreboard gives the leaderboard, which is the answer, not a forecast. |
| **KXLOLGAME / KXVALORANTGAME / KXCS2GAME** | 18,703 / 59,328 / 24,626 | tight, 1.0¢, two-sided | **The free data layer collapsed.** Oracle's Elixir — the canonical free LoL dataset — returns `NoSuchBucket`: the S3 bucket is deleted. HLTV (CS2) is **403 Cloudflare**. vlr.gg's API is **402 Payment Required**. Leaguepedia responds but returned 372 bytes on a 20-row query. Polymarket shows the scale of what is being given up: **$15.1 M/24 h on Esports** at a **30¢ median spread**. |

**These are the painful kills.** All three have a genuine counterparty, tight
books and real depth. They fail on D, which is the dimension that decides
whether a private view is possible at all.

---

## KILL 5 — Too thin to validate (dimension E)

Families clearing A but settling too rarely to ever accumulate evidence.
LEDGER **S021** is the reference: the tennis line needed n ≈ 3,970 events for a
2¢ edge. A family settling a handful of times a week cannot reach that in a
lifetime of the strategy.

Examples from the settlement scan (events closing in the next 7 days):
KXGOVFLNOMR (18 markets/day traded, **below the 20-market gate**), KXSAVEACT
(6/day), KXSENATEMID (18/day and 33% two-sided), KXMI13D (36 trades/day).

The one-off political and novelty series — KXGREENLAND, KXIRANDEMOCRACY,
KXPAHLAVIHEAD, KXDOED, KXCITRINI, KXELECTIRAN, KXGAMBLINGREPEAL — each have
**1–2 markets and effectively no volume**. They are interesting, they are
fee-free (`fee_multiplier = 0`), and they are unvalidatable. Killed on E.

---

## KILL 6 — Killed by omission, and named as such

The continuous recorder covers **85 families**; the one-shot sweep reached
**300**; the tape shows **~1,841 series trading**. That leaves roughly
**1,500 families measured on trades/day only, with no depth measurement at
all**.

**These are not killed. They are unmeasured**, and writing them up as kills
would be dishonest. They are excluded from the shortlist because a shortlist
entry requires evidence, not because evidence against them exists. The full
per-series trade counts are in `reports/family_scorecard.json` for whoever
picks this up.

The largest unmeasured families by trades/day are listed in
[WHAT_IS_LEFT.md](WHAT_IS_LEFT.md).

---

## Not killed, and explicitly retained despite looking bad

| Family | Looks bad because | Retained because |
|---|---|---|
| KXNPBGAME / KXNPBTOTAL | the stale sweep read 0% two-sided | fresh probe: **100% two-sided**, 2,043 contracts at touch. The sweep was wrong. |
| KXMLBNEXTTEAM | 25% two-sided, 7¢ spread | 200 open markets; the low reading is a sampling artifact of a long-tail ladder, not established |
| Tennis (ITF / Challenger) | its data source was deleted | it is the largest sports counterparty on the exchange, 100% two-sided at a 1¢ spread with **no maker fee**. Killed on D would be premature; see SHORTLIST for the honest case against. |
