# universe.md — every market family on both venues

Pulled 2026-08-02 from public unauthenticated endpoints. Every number is
measured; nothing is from documentation. Where a field the documentation
describes does not exist, that is stated rather than substituted.

Artifacts: `reports/kalshi_universe.json` (3,074 series),
`reports/poly_universe.json` (1,157 tags), `data/kalshi_markets_open.jsonl`
(419,828 rows), `data/poly_events.jsonl` (2,100 events).

---

## Headline shape

| | Kalshi | Polymarket |
|---|---|---|
| Open markets | **419,828** | 31,487 (inside the 2,100 highest-volume events) |
| Events | 229,030 | 2,100 crawled of an unknown larger total |
| Families | 3,074 series | 1,157 tags |
| Traded in the last 24 h | 1,291 series | not measured this session |
| Tick | 0.1¢ or 1¢, structural, see below | **0.001 or 0.01** (0.1¢ / 1¢) |
| Fee | `0.07·C·p(1−p)`, rounded up per order | `0.10·min(p, 1−p)` |

**Kalshi's market count is a mirage.** Two exotic parlay series are 82.9% of it:

| Series | Markets | Share | Cumulative |
|---|---|---|---|
| KXMVESPORTSMULTIGAMEEXTENDED | 267,739 | 63.8% | 63.8% |
| KXMVECROSSCATEGORY | 80,097 | 19.1% | **82.9%** |
| KXMIDTERMMOV | 3,939 | 0.9% | 83.8% |
| KXNASDAQ100U | 2,800 | 0.7% | 84.5% |
| KXMIDTERMVOTETURN | 2,756 | 0.7% | 85.1% |

Both are `Exotics`, both carry **0.0 in 24 h volume at the series level and
0.1% two-sided quotes**. They are combinatorial leg-bundles minted on demand.
Excluding them, Kalshi has **71,992 open markets across 3,072 series**, which
is the number to carry forward.

Verified for duplicates before use: 419,828 rows, 419,828 distinct tickers,
**0 duplicates** — the cursor pagination did not cycle.

---

## Kalshi by category

| Category | Series | Markets | Events | 24h volume | Median 2-sided % | Maker-fee series |
|---|---|---|---|---|---|---|
| **Sports** | 785 | 32,769 | 4,366 | **36,987,445** | 90.9 | 56 |
| Elections | 625 | 11,341 | 2,216 | 3,037,889 | 100.0 | 0 |
| Entertainment | 302 | 6,632 | 519 | 2,293,056 | 100.0 | 7 |
| Crypto | 78 | 4,005 | 106 | 1,835,982 | 100.0 | 1 |
| Politics | 451 | 2,013 | 503 | 1,534,961 | 100.0 | 0 |
| Climate and Weather | 83 | 691 | 109 | 1,276,436 | 83.3 | 0 |
| Mentions | 61 | 1,018 | 62 | 1,074,710 | 100.0 | 0 |
| Economics | 205 | 3,014 | 332 | 670,390 | 100.0 | 10 |
| Science and Technology | 111 | 743 | 127 | 445,333 | 100.0 | 1 |
| Financials | 302 | 8,374 | 487 | 390,996 | 100.0 | 3 |
| Commodities | 29 | 828 | 32 | 373,804 | 92.6 | 0 |
| Companies | 33 | 346 | 44 | 14,731 | 100.0 | 0 |
| World / Social | 5 | 5 | 5 | 28 | 100.0 | 0 |
| **Exotics** | 2 | **347,836** | 220,091 | **0** | **0.1** | 0 |

Sports is **74% of exchange-wide 24 h volume**. Everything else together is
about a third of Sports alone.

---

## Contract structure

`market_type` is `binary` on every market inspected. `strike_type` distinguishes
the families:

| strike_type | What the contract is |
|---|---|
| `structured` | a named outcome — team/player wins, tournament placing |
| `greater` / `greater_or_equal` / `less` | a threshold ladder on a number (BTC ≥ $120,000) |
| `custom_strike` | free-form, with `rules_primary` carrying the text |

Ladder families (`greater`) are the ones where the bucket-sum and monotonicity
arbitrage checks apply — both already run and both null (LEDGER C001, C002).

---

## Tick size — the field does not exist, the structure does

`tick_size` is **absent from the market object on all 419,828 markets**. So is
`tick_size_dollars`, `min_tick`, and `response_price_units`. Any code reading
those gets `None` on every market. The real tick is in
`price_level_structure` + `price_ranges`:

| price_level_structure | Markets | Step |
|---|---|---|
| `deci_cent` | 348,428 | 0.1¢ across the whole range |
| `linear_cent` | 63,207 | **1¢ across the whole range** |
| `tapered_deci_cent` | 8,193 | 0.1¢ below 10¢, **1¢ from 10–90¢**, 0.1¢ above 90¢ |

`deci_cent` is dominated by the two parlay series, so among markets that
actually trade, **`linear_cent` (1¢) is the normal case** and the tapered
structure applies to a small set including KXBTC15M and KXLPGATOUR/KXKFTOUR.

This was cross-checked against reality: prices quoted in the depth recorder use
one decimal place only on exactly the series the structure says are
`deci_cent`/`tapered` (KXPGATOUR, KXMLB, KXPRESNOMD, KXBTCY, KXLPGATOUR,
KXKFTOUR, KXGOVFLNOMR, KXSENATEMID, KXMI13D) and zero decimal places on all the
`linear_cent` ones (KXMLBGAME, KXBTCD, KXWTAMATCH, KXATPMATCH, KXITFMATCH …).
Structure and observation agree.

**Why it matters for dimension C:** the tick is the floor on the spread and the
spread is most of the cost bar. "The book sits at the tightest possible quote"
means a 1¢ spread on a `linear_cent` family and a 0.1¢ spread on a `deci_cent`
one — a tenfold difference in what "already tight" implies.

---

## fee_type — read from `/series`, not from documentation

| fee_type | Series | Markets | 24h volume |
|---|---|---|---|
| `quadratic` | 2,994 | 417,443 | 20,930,774 |
| **`quadratic_with_maker_fees`** | **78** | 2,172 | **29,004,988** |
| `None` | 2 | 213 | 20,848 |

Only **78 of 3,074 series charge a maker fee** — but those 78 carry **58% of
exchange-wide 24 h volume**. Liquidity and maker fees coincide.

This independently reproduces LEDGER **S010** at the family level. The tennis
split is exact:

| Series | fee_type |
|---|---|
| KXATPMATCH, KXWTAMATCH | `quadratic_with_maker_fees` |
| KXITFMATCH, KXATPCHALLENGERMATCH | `quadratic` — **no maker fee** |

So resting orders are free of maker fees on Challenger/ITF and charged on
ATP/WTA, exactly as S010 recorded. Documentation's "maker fee is 25% of taker"
remains wrong.

### 11 series carry `fee_multiplier = 0`

If the multiplier means what it says, these are **fee-free**:

| Series | Title | Markets | 24h volume |
|---|---|---|---|
| **KXBTCY** | BTC price range EOY | 28 | **157,554** |
| KXGDPYEAR | Annual GDP | 154 | 39,288 |
| KXGREENLAND | Greenland purchase | 2 | 8,284 |
| KXETHY | ETH price EOY | 18 | 1,880 |
| KXIRANDEMOCRACY | Will Iran become a democracy in 2026? | 1 | 1,590 |
| KXCITRINI | Will the Citrini scenario materialize? | 1 | 1,105 |
| KXLAYOFFSYINFO | Tech layoffs | 1 | 323 |
| KXELECTIRAN, KXDOED, KXGAMBLINGREPEAL, KXPAHLAVIHEAD | novelty one-offs | 1–2 each | ≈0 |

Only KXBTCY has meaningful volume. **This is unverified as an economic fact** —
`fee_multiplier=0` has not been checked against a real fill, and this project
has been burned twice by trusting a field's name (`enable_order_book` in W016,
the legacy price fields in GUARDS #12). Treated as a hypothesis, not a finding.

---

## Settlement sources

Declared on the series object. The distribution says what kind of exchange this
is: the most common settlement sources are **news organisations**, not data
feeds.

| Source | Series citing it |
|---|---|
| ESPN | 631 |
| The Wall Street Journal | 599 |
| Reuters | 593 |
| the Associated Press | 486 |
| The Washington Post | 484 |
| The New York Times | 483 |
| CNN | 478 |
| Fox News | 455 |
| Politico | 452 |
| ABC / MSNBC / CBS / Axios | 444 / 415 / 397 / 384 |
| Fox Sports | 370 |
| Bloomberg (News + terminal) | 312 + 147 |

Sports families settle on ESPN and Fox Sports; the "Mentions" families settle on
a *set* of named outlets, which makes them adjudication markets rather than
data markets.

---

## The legacy-field trap, confirmed live

Of 200 sampled open markets, these fields were non-null on **zero**:

`yes_bid` · `yes_ask` · `no_bid` · `no_ask` · `last_price` · `volume` ·
`open_interest` · `liquidity`

The values live in `yes_bid_dollars`, `yes_ask_dollars`, `last_price_dollars`,
`volume_fp`, `volume_24h_fp`, `open_interest_fp`, `liquidity_dollars`,
`yes_bid_size_fp`, `yes_ask_size_fp`. GUARDS #12 predicted this; it is now
confirmed on the live API as of 2026-08-02. **Any recorder still reading the
old names is writing nulls at full row count.**

---

## Polymarket

Crawled `/events` (not `/markets`) because tags — the only family-like key the
venue exposes — are returned on events and not on the market stub inside
`/markets`.

**Coverage is truncated and this is not optional to state.** gamma caps `limit`
at 100 regardless of what you send, and returns **HTTP 422 at offset 2100**.
The crawl is ordered by 24 h volume descending, so what is held is the
**top 2,100 events by volume, 31,487 markets** — the low-volume tail is absent.
For market *selection* that is the right 2,100, but no count below is a total.

Of those 31,487 markets: **24,779 live** (`acceptingOrders` AND a future
`endDate`), **18,130 two-sided right now**.

| Tag | Markets | Events | Live | 24h volume | 2-sided % | Spread med / p75 / p90 (¢) |
|---|---|---|---|---|---|---|
| Sports | 14,379 | 744 | 9,812 | **19,390,883** | 63.9 | 4.0 / 50.0 / 96.0 |
| Games | 9,161 | 581 | 6,010 | 16,471,049 | 71.2 | 4.0 / 67.0 / 97.0 |
| Esports | 2,606 | 125 | 1,359 | 15,067,101 | 73.1 | **30.0** / 76.9 / 95.0 |
| league of legends | 1,387 | 51 | 883 | 14,096,412 | 79.9 | **44.0** / 86.0 / 96.0 |
| Politics | 7,976 | 534 | 6,889 | 13,706,107 | 38.4 | **1.1** / 4.0 / 11.0 |
| Geopolitics | 1,526 | 214 | 1,001 | 13,645,824 | 54.7 | 2.0 / 4.0 / 15.9 |
| Iran | 686 | 84 | 430 | 12,226,083 | 56.0 | 2.0 / 7.0 / 25.0 |
| Israel | 364 | 47 | 247 | 7,242,030 | 48.4 | 1.0 / 3.0 / 5.3 |
| Trump | 1,161 | 121 | 861 | 5,499,889 | 68.0 | 3.0 / 12.0 / 50.0 |
| Recurring | 2,292 | 216 | 2,118 | 4,497,478 | 69.7 | 1.0 / 3.0 / 7.0 |
| Soccer | 7,082 | 403 | 4,276 | 3,123,441 | 61.6 | 3.0 / 49.0 / **98.0** |
| Elections | 5,794 | 283 | 5,252 | 3,117,994 | 28.9 | 1.0 / 2.8 / 5.3 |
| Crypto | 1,190 | 141 | 1,023 | 2,735,696 | 78.4 | 2.2 / 5.0 / 23.6 |
| Weather | 1,804 | 177 | 1,638 | 2,409,320 | 67.6 | 1.0 / 3.0 / 6.0 |
| Daily Temperature | 1,716 | 156 | 1,584 | 2,271,673 | 67.5 | 1.0 / — / 6.0 |

Tags overlap heavily (a market tagged `Iran` is usually also `Geopolitics` and
`World`), so these rows **do not sum** to the 31,487 total. They are views, not
a partition.

### What the spread distribution says

The p90 column is the story. **Sports, Games, Soccer and Esports all have p90
spreads of 95–98¢** against median spreads of 3–4¢. That is not a wide market;
that is a bimodal one — a small set of liquid headline markets and a long tail
of markets quoted 1¢ bid / 99¢ ask, which is precisely the shape LEDGER T015
identified on Kalshi (39.8% of held-out markets wider than 10¢, with a 50¢
"mid" nobody trades at). Any Polymarket study that averages across a tag
without conditioning on spread will be measuring the tail.

Politics and Elections are the opposite: median 1.0–1.1¢, p90 5–11¢. Tight
throughout.

---

## Cross-venue, at the family level

| | Kalshi | Polymarket |
|---|---|---|
| Fee at 50¢ | 1.75¢ | **5.00¢** (2.86×) |
| Fee at 10¢/90¢ | 0.63¢ | 1.00¢ (1.59×) |
| Minimum tick, liquid families | 1¢ | 0.1¢ |
| Maker fee | zero on 2,996 of 3,074 series | none |
| Depth access | **free, 20 levels/side, unauthenticated** | free via CLOB `/book` |

Polymarket's finer tick is a genuine advantage that its fee more than
cancels at mid prices: a Polymarket market must be **3.25¢ tighter** at 50¢
just to match Kalshi's total cost. Near the wings (10¢/90¢) the fee gap narrows
to 0.37¢ and the finer tick can win.

---

## What was NOT enumerated, and why

- **Polymarket below the top 2,100 events by volume** — gamma 422s at offset
  2100. Would need a different crawl axis (by tag, by date) to complete.
- **Kalshi settled/closed markets** — the API is a ~69-day window and closed
  markets 404 (STATUS.md). Only open markets are enumerable.
- **Per-market Polymarket depth** — the CLOB `/book` endpoint exists and is
  public but was not swept this session; see WHAT_IS_LEFT.md.
