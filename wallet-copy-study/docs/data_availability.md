# Data availability — Phase 0

Written 2026-08-01. Every claim below traces to a record in `data/probe_0*.json`,
produced by `src/probe_00_endpoints.py` … `src/probe_04b_join.py`. Nothing here is
taken from documentation; where documentation and observation disagree, the
observation is recorded and the documentation is marked wrong.

---

## Summary of what is retrievable

| Source | Reachable | Coverage | Hard limit |
|---|---|---|---|
| Goldsky **orderbook** subgraph | yes | **2022-11-21 → 2026-04-28** | stale, ~3 months behind; 1000 rows/page |
| Goldsky activity / pnl / positions subgraphs | **no — 404** | — | deleted upstream |
| data-api `/trades` (global tape) | yes | **~10 minute rolling window** | `offset` cap 10,000 |
| data-api `/activity?user=` | yes | full wallet history by time | `offset` cap **5,000** |
| data-api `/positions?user=`, `/value?user=` | yes | current only | no history |
| CLOB `/markets`, `/sampling-markets` | yes | current books/metadata | cursor paging |
| CLOB `/trades` | **no — 401** | — | requires API credentials |
| Gamma `/markets` | yes | all markets, 3.26M ids | **most filters silently ignored** |

### The two that decide the study's shape

1. **The subgraph is the only source of historical fills, and it stops at
   2026-04-28.** Prior probing found the same date; it has *not* resolved in the
   intervening period. Self-reported head is block 87,814,766,
   `hasIndexingErrors: false` — it is not erroring, it is simply not advancing.
   3.4 years of history is ample for ranking and persistence testing, but the
   study cannot observe anything in the most recent ~3 months.
2. **The live tape is ~10 minutes deep.** `/trades` at `offset=0` returned
   06:07:09Z; at the `offset=10000` cap it reached back only to 05:59:57Z. So
   there is no way to bridge the subgraph's 3-month gap by accumulating the tape
   retrospectively — only by recording forward.

---

## The fee regime break (not anticipated by the brief)

**Polymarket charged no fee for 91% of its on-chain history.** Fills carry
`fee = 0` from the start of the sample through **2026-01-07**, and fees appear
from **2026-01-08** onward.

```
2023-10 .. 2026-01-07   fee != 0 on  0.00% of sampled fills
2026-01-08              fee != 0 on 57.00%
2026-01-09              fee != 0 on 70.60%
2026-02-28              fee != 0 on 84.80%
2026-04-01              fee != 0 on 96.60%
```

Bisected to a single day (`probe_03_regime.json:fee_switch_bisect`). Coverage then
ramps over ~3 months rather than switching on completely — consistent with a
per-market rollout, not a global flag.

**Why this matters more than it looks.** The ranking window is almost entirely a
zero-fee regime. Any wallet whose historical P&L looks good earned it *without
paying the fee we would have to pay to copy it*. The economic bar below applies
to us and did not apply to them. This puts a regime break inside the persistence
test, and Phase 4a's split points must be chosen with it in view — a split that
straddles 2026-01-08 is comparing two different games.

The usable post-fee on-chain window is **2026-01-08 → 2026-04-28, about 16
weeks.** That is the only period in which observed wallet behaviour was formed
under the cost structure a copier would face.

*Sampling caveat:* each day's figure is the first 1,000 fills after 00:00 UTC
(`orderBy: timestamp, asc`), not a random sample of the day. 2026-01-14 reads
0.00% while its neighbours read 53–68%; that is most likely a midnight burst of
fills in fee-exempt markets, not a fee holiday. The switch-on date is robust
(six consecutive zero days before, seven non-zero after); the per-day *levels*
are not precise.

---

## Fee formula — verified, and the documentation is wrong

Two candidate forms were tested head-to-head against the on-chain `fee` field on
**n = 5,362** fee-bearing fills (2026-04-23 → 2026-04-28):

| Form | Median relative error | Within 1% |
|---|---|---|
| **A: `0.10 × min(p, 1−p)` per share** | **7.71 × 10⁻⁸** | **100.0%** |
| B: `0.07 × p × (1−p)` per share (published) | 9.84 × 10⁻¹ | 0.0% |

Zero fills miss form A by more than 1%. Implied rate solved per fill: **1000 bps
on 5,338 of 5,362**. Form A is confirmed independently of the prior claim; the
published schedule is wrong, as the brief warned.

**Decoding note.** `OrderFilled` amounts describe what the **maker** gave and
received, and the fee is charged on the maker's leg in whichever asset the maker
*receives*:

- `makerAssetId == 0` → maker paid USDC, received tokens → maker **bought**,
  fee denominated in outcome tokens: `rate × min(p,1−p) × shares / p`
- `takerAssetId == 0` → maker paid tokens, received USDC → maker **sold**,
  fee denominated in USDC: `rate × min(p,1−p) × shares`

Both reduce to the same economic cost. An earlier pass inverted this and got
median relative error 0.96 — recorded here because it is exactly the kind of
sign error that would have silently poisoned every downstream cost number.

### The economic bar

One-way taker fee, cents per share. Holding to settlement pays this once (no exit
fee); round-tripping pays it twice.

| Price | Polymarket one-way | Round trip | Kalshi | Poly ÷ Kalshi |
|---|---|---|---|---|
| 10¢ | 1.00¢ | 2.00¢ | 0.63¢ | 1.59× |
| 25¢ | 2.50¢ | 5.00¢ | 1.31¢ | 1.90× |
| 50¢ | **5.00¢** | 10.00¢ | 1.75¢ | **2.86×** |
| 75¢ | 2.50¢ | 5.00¢ | 1.31¢ | 1.90× |
| 90¢ | 1.00¢ | 2.00¢ | 0.63¢ | 1.59× |

A copied wallet must therefore beat its own entry price by **at least 1.00pp at
10¢/90¢ and 5.00pp at 50¢** before spread and slippage, just to break even
holding to settlement. Polymarket is more expensive than Kalshi at every price
point, and since only Polymarket has public wallets, copy trading means paying
this bar.

---

## Address space — the join works, with one contaminant

Phase 1 needs wallet identity to carry between the subgraph (historical fills)
and the data API (P&L cross-check). It does:

- **16 of 16** subgraph `maker` addresses that the data API recognises came back
  with `proxyWallet == the queried address`. Subgraph maker addresses *are*
  proxy wallets. Same address space, no translation needed.
- Direct confirmation on one address whose history reached back far enough for
  the `transactionHash` sets to intersect. The other 15 show no tx overlap only
  because `/activity` returns the newest rows and those wallets' recent activity
  postdates the subgraph cutoff.

**Contaminant: the taker leg contains infrastructure, not just users.** The two
heaviest taker addresses have **no data API record at all**:

| Address | Share of fills | data-api record |
|---|---|---|
| `0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e` | 29.8% | none |
| `0xc5d563a36ae78145c45a50134d48a1215220f80a` | 5.9% | none |

The first also appears as taker in the oldest fill in the entire sample
(2022-11-21) — a long-lived operator/relayer contract. The taker leg is *not*
uniformly a relayer (994 distinct takers in 5,000 fills), so takers cannot be
discarded wholesale, but any address with a large fill share and no data API
record must be excluded as infrastructure. This is a Phase 2 exclusion and is
structural, not performance-based.

---

## Gamma filter integrity — verify every filter before trusting it

Confirmed: **most Gamma filters are silently ignored**, returning the unfiltered
first page. Tested by comparing returned ids against an unfiltered call:

| Filter | Behaviour |
|---|---|
| `tag_slug=nba` | **ignored** — returned "Will Jesus Christ return before GTA VI?", Harvey Weinstein sentencing |
| `slug_contains=bitcoin` | **ignored** — returned byte-identical rows to `tag_slug=nba` |
| `closed=false` | **ignored** |
| `active=true` | **ignored** |
| `liquidity_num_min=1000` | **ignored** |
| `closed=true` | **works** — all returned rows genuinely closed |
| `order=` / `ascending=` | **works** |

Two different filters returning identical row sets is the signature: the
parameter is dropped and the default page is served. Only `closed=true` and the
ordering parameters were observed to do anything.

**Default ordering is oldest-first.** `/markets?limit=5` returns ids 540817…
created 2025-05-02, identical to `ascending=true`; `ascending=false` returns ids
3258394… created 2026-08-01. This is precisely the trap the brief flags — a prior
false positive came from sampling closed 2023 sports markets because the endpoint
returned oldest-first. **Every Gamma call in this study must pass explicit
`order`/`ascending` and must re-verify semantics on the returned rows.**

---

## Sample composition (to be filled before any analysis)

Per the brief, no analysis proceeds until the sample's date range and composition
are reported. Established so far: date range **2022-11-21 → 2026-04-28**, with a
zero-fee sub-period ending 2026-01-07 covering 91% of it. Market-type and
volume composition is the first step of Phase 1.

---

## Consequences for the study design

1. **Two regimes, not one.** Pre-2026-01-08 (zero fee, 91% of history) and
   post-2026-01-08 (fee-bearing, ~16 weeks). Persistence must be tested within a
   regime as well as across the full history, or a regime change will be read as
   skill decay.
2. **No live validation possible from history alone.** The subgraph's 3-month lag
   plus the tape's 10-minute depth means a forward test requires recording the
   tape prospectively. Phase 4c's decay curve must be built from subgraph fills
   plus reconstructed book state, not from the live tape.
3. **The `/activity` offset cap of 5,000 bounds per-wallet history.** For
   high-frequency wallets this truncates to recent activity only, so data-api
   P&L validation will be possible for low/medium-frequency wallets and partial
   for the rest.
4. **Wallet analysis should be anchored on the maker leg**, which is cleanly
   joinable and free of the operator contamination found on the taker leg —
   while remembering that a real user can also be a taker, so taker-side fills
   are included subject to an infrastructure-address exclusion.
