# HANDOFF

Wallet copy-trading feasibility study. Read-only public data, simulated fills
only. No funded wallet, no order placement, nothing live.

**Location:** `C:\Users\gianf\wallet-copy-study` (self-contained, git-initialised).
**Interpreter:** `C:\Users\gianf\AppData\Local\Programs\Python\Python312\python.exe`
**Last updated:** 2026-08-01, during overnight run.

---

## RETRACTION — "72% of the edge lives in exits" WAS WRONG

**Retracted 2026-08-01, exit study stage 1.** The 2.38pp gap between wallet edge
and copier buy-and-hold was reported as the portion of the edge living in the
wallets' exits. It is not. It is **almost entirely an accounting artifact**: a
**gross** wallet edge was compared against a **net** copier return, so the gap is
mostly just the fee the copier pays and the wallet was never charged.

```
gap = wallet_edge - copier_buy_and_hold
    = (realised_per_share - outcome)  +  fee(entry_px)
      \____ exit component ____/         \__ artifact __/
```

For the ~80% of positions held to settlement, `realised == outcome`, so the
entire gap on those is the fee term. Measured:

| Group | Gap | **Exit component** | Fee artifact | Exit share of gap |
|---|---|---|---|---|
| Top decile | 2.484 | **−0.106** | 2.590 | **−4.3%** |
| Bottom decile | 2.669 | −0.070 | 2.739 | −2.6% |
| All eligible | 2.329 | −0.167 | 2.496 | −7.2% |
| Everyone | 2.270 | −0.134 | 2.404 | −5.9% |

**The genuine exit component is slightly NEGATIVE.** These wallets' sells left
them marginally worse off than holding to settlement would have. Since
`exit_component = frac_sold × (exit_price − outcome)` and mean `frac_sold` is
0.194, they sell about 0.55pp below eventual settlement value when they sell.

**Consequently: none of the gap is capturable, because the gap was never exit
skill.** Copying exits is significantly *worse* than buy-and-hold at zero delay,
before any latency is added:

| Spread assumption | Top-decile delta (full replication − buy & hold) | CI95 | p |
|---|---|---|---|
| none | **−0.505pp** | [−0.643, −0.373] | 0.0005 |
| 0.5pp/leg | −0.602pp | [−0.739, −0.469] | 0.0005 |
| 1.0pp/leg | −0.698pp | [−0.837, −0.565] | 0.0005 |

**18 of 20 tests significant under Benjamini-Hochberg FDR at 5%.** Every
`exit_delta` test is significant and negative, in all four groups and all three
spread assumptions.

*What this does not change:* the verdict (`EDGE, SLOW DECAY — do not build`) and
the persistence result stand. What changes is the reason the copier captures only
+0.937pp of a +2.567pp wallet edge — it is the **fee**, not forgone exit skill.
That is a better answer, and it closes off the follow-up this study previously
recommended as its highest-value next step.

### Exit decay and the mechanical benchmark (full books, 3,200 tokens)

Complete books pulled for 3,200 tokens (10,755,763 fills, 54 truncated).
**Balanced panel: n is constant at 2,879 across every delay**, so nothing here is
composition drift — the trial run had n falling 811→692 and that flaw was fixed
before the final run.

| Delay | n | Buy & hold | Copy exits | **Delta** | CI95 | p |
|---|---|---|---|---|---|---|
| 0s | 2,879 | +3.436 | +1.201 | **−2.235** | [−3.36, −1.23] | 0.0005 |
| 10s | 2,879 | +0.781 | −1.333 | **−2.114** | [−3.21, −1.08] | 0.0005 |
| 60s | 2,879 | +0.686 | −1.351 | **−2.037** | [−3.14, −1.01] | 0.0005 |
| 300s | 2,879 | +0.427 | −1.567 | **−1.995** | [−3.10, −0.97] | 0.0005 |

**Exits show no latency decay either.** The delta is a flat ~−2pp drag whatever
the delay. With spread at 60s: −2.537pp (half) and −3.037pp (full), all
p=0.0005. **12 of 13 tests significant under BH-FDR at 5%.**

#### The mechanical hold rule — the benchmark for exits

Sell H seconds after entry, no wallet selection at all:

| Hold | Return | **vs buy & hold** | CI95 | p |
|---|---|---|---|---|
| 60s | −0.311 | **−3.548** | [−4.74, −2.34] | 0.0005 |
| 300s | −0.209 | −3.446 | [−4.61, −2.20] | 0.0005 |
| 1800s | +0.118 | −3.120 | [−4.31, −1.89] | 0.0005 |
| 7200s | +0.254 | −2.983 | [−4.14, −1.83] | 0.0005 |
| 86400s | +1.714 | −1.523 | [−2.43, −0.62] | 0.0005 |

**Shorter holding is strictly worse, monotonically.** This refutes the
tail-risk-avoidance hypothesis outright: exiting early is not a free reduction in
variance, it is a cost, and the cost grows the earlier you exit.

#### Duration-matched: is there timing skill?

Mechanical exit fired at the *same* holding period the wallet actually used —
identical exposure window, different exit instant:

| | value |
|---|---|
| mechanical at matched hold | +3.139pp |
| **wallet minus mechanical** | **−0.401pp** CI[−1.03, +0.24] **p=0.224** |

**No timing skill.** At matched exposure, the wallet's chosen exit instant is
indistinguishable from an arbitrary one, and points slightly the wrong way.

### REFINEMENT — entries DO decay for these selected wallets

One number here revises an earlier conclusion and should not be buried. The
buy-and-hold column falls **+3.436 → +0.781 → +0.686 → +0.427pp** from 0s to
300s. That is ~3pp of entry decay inside five minutes, on a constant panel.

The main study reported entry decay as *flat to 1800s* and concluded latency was
irrelevant. That was measured **unconditionally**, over all 2.23M buys in the
market panel. Conditioned on the selected wallets' signals, entries **do** decay,
and most of it goes in the first ten seconds.

*Limitation, stated rather than smoothed over:* this subsample is positions with
sells, in tokens where a top-decile wallet sold — not a random sample of their
entries. It is suggestive, not a clean replacement for the unconditional curve.
**It does not change the verdict** (at 60s, +0.686pp is already below the ≥1.0pp
spread), but "latency is irrelevant" is too strong as previously stated, and the
honest version is: *latency is irrelevant to the unconditional population, and
costs roughly 2.7pp in the first ten seconds for selected-wallet signals.*

### Anatomy: it is neither timing skill nor tail-risk avoidance

`exit_component = frac_sold × (exit_price − outcome)` splits cleanly by what the
position eventually did. Top decile, period 2, 8,600 positions with sells:

| Slice | n | Contribution | CI95 | Mean exit price |
|---|---|---|---|---|
| Eventual **winners** | 4,125 (48%) | **−23.988pp** | [−24.73, −23.20] | 0.7277 |
| Eventual **losers** | 4,475 (52%) | **+21.196pp** | [+20.56, +21.86] | 0.2489 |
| **Net** | 8,600 | **−0.476pp** | [−1.02, +0.04] | 0.4786 |

The two halves are enormous and they very nearly cancel. These wallets sell
winners at 0.73 that go on to settle at 1.00, and sell losers at 0.25 that go on
to settle at 0.00. Cutting losses earns +21.2pp; taking profit early gives back
−24.0pp. **Net −0.48pp, and not significant for the top decile alone (p=0.066).**

Crucially, **the top decile is no better at this than everyone else** (net
−0.476pp vs −0.426pp for the full population). Whatever their skill is, it is
not in the exits.

By entry price the effect is signed but small: **+1.63pp** CI[0.82, 2.40] on
longshots (0.0–0.2) and **−2.85pp** CI[−3.90, −1.76] at mid-price (0.4–0.6),
where there is most left to lose by selling early. By holding period it is mostly
noise. **10 of 20 tests significant under BH-FDR at 5%.**

So the answer to "timing skill or merely shorter holding" is **neither** — it is
a symmetric disposition pattern that nets to approximately zero, slightly
negative.

---

## SECOND MAJOR FINDING — ranking inside the fee era gives a different top decile

Every earlier ranking drew period 1 from history that was **91% fee-free**. Ranked
entirely inside the fee-bearing era instead (P1 = 2026-01-08→03-01,
P2 = 2026-03-01→04-28, both fees live, 368 wallets qualifying at ≥20 markets):

| | value |
|---|---|
| Top-decile overlap with the fee-free-history ranking | **7 of 36** |
| Jaccard | **0.092** |
| Fee-era top-decile wallets **not even eligible** before | **23 of 36** |
| Persistence within the fee era (Spearman ρ) | 0.2565 |
| Top decile P1 → **P2 excess** | +6.441 → **+0.513pp** |
| Bottom decile P2 | −1.136pp |

**The rankings are nearly disjoint**, and out-of-sample excess collapses from
+3.549pp (long history) to **+0.513pp** inside the fee era. Persistence itself
survives — ρ is still positive at 0.257 — but the wallets it identifies are
different ones, and what they retain is far smaller.

The fee-era exit component is also negative: **−0.268pp** CI[−0.544, +0.008] for
the fee-era top decile, with an exit-copy delta of −0.653pp. Same direction as
the long-history result. **6 of 7 tests significant under BH-FDR at 5%.**

*Caveat stated plainly:* eight weeks per sub-period. These sample sizes are not
equivalent to the long-history runs and the point estimates are correspondingly
soft. The composition finding (Jaccard 0.092) is the robust part; the +0.513pp
is the soft part.

---

## PREMISES DISPROVEN SO FAR

**1. "Polymarket charges a fee on the history we would rank wallets on." FALSE.**
Fills carry `fee = 0` for **91% of on-chain history**. Fees switch on
**2026-01-08** (bisected to the day: six consecutive zero days before, seven
non-zero after). Wallets ranked on pre-break history earned their P&L *without
paying the fee a copier now faces*. Only ~16 weeks of fee-bearing history exists
inside subgraph coverage. Consequence: persistence must be tested at the regime
cut as well as calendar cuts, or a cost-structure change will read as skill
decay. This was not anticipated by the brief.

**2. "The published fee schedule is right." FALSE, and confirmed independently.**
`0.10 × min(p, 1−p)` per share fits **100.0%** of 5,362 fee-bearing fills within
1% (median relative error 7.71e-08). The documented `0.07 × p × (1−p)` fits
**0.0%**. See `docs/data_availability.md`.

**3. "The prior study's +7.05pp naive benchmark can be used as a reference."
UNVERIFIABLE, therefore void.** A recursive search of `C:\Users\gianf` found no
copy-trading study and no wallet dataset — only an unrelated Kalshi/Polymarket
market-making project in `C:\Users\gianf\crypto`. Its selection logic cannot be
audited. Phase 3 recomputes the benchmark from scratch. (Decision D9.)

**4. "`enable_order_book` identifies tradable markets." FALSE.** It reports
*current* tradability and is false for essentially every resolved market.
Requiring it produced **zero eligible markets**. See D4.

---

## STUDY COMPLETE — verdict in `COPY_TRADING_VERDICT.md`

# EDGE, SLOW DECAY — but the copyable part is smaller than the spread

**Do not build the bot.** Wallet skill is real and persists out of sample
(+2.567pp excess, CI[2.19, 2.96]). The edge does **not** decay with latency —
the copy return is flat from 0s to 1800s, so a bot buys nothing. But **72% of
the edge lives in exits, not entries**, and the remaining copyable +0.937pp
(CI[0.53, 1.38]) is entirely consumed by a spread whose *lower bound* is 1.0pp.
Net: **−0.063pp**, at zero delay, before slippage and reflexivity.

All nine phases are done. Every deliverable named in the brief exists:
`COPY_TRADING_VERDICT.md`, `docs/wallet_criteria.md`, `docs/data_availability.md`,
`DECISIONS.md`, and twelve JSON reports under `reports/`.

**Highest-value follow-up:** record the CLOB book prospectively and measure the
true effective ask. The 1.0pp spread haircut is a lower bound derived from trade
prices because the subgraph carries no book; if a patient limit order can do
materially better, +0.937pp becomes a thin but real edge. ~~Second: test copying
exits.~~ **Done — see the retraction above. Exits are worth nothing and copying
them destroys value, so that avenue is closed.**

---

## Detail — persistence EXISTS

**Phase 4a does not fail.** Rank correlation between period-1 and period-2 wallet
performance is **positive at every cut point and every sample-size threshold**,
and it *rises* with the number of observations per wallet — which is what real
skill measured with less noise looks like, and not what a leaderboard artifact
looks like.

It survived both rival explanations:

| Scenario | Spearman ρ range | Top decile P2 (best cut) |
|---|---|---|
| A — all wallets, unit = market | 0.162 – 0.353 | +3.058pp CI[2.00, 4.13] |
| B — market makers removed | 0.144 – 0.349 | +3.158pp CI[1.91, 4.42] |
| C — unit = (wallet, series, day) | 0.174 – 0.437 | +3.314pp CI[2.01, 4.57] |
| **D — both corrections (the honest test)** | **0.157 – 0.433** | **+3.549pp CI[2.00, 5.08]** |

- **Market makers are not the explanation.** Phase 2 removed 721 of 2,500
  wallets (682 MM fingerprints, 41 too large to copy). ρ barely moved.
- **Pseudo-replication is not the explanation.** Collapsing to
  (wallet, series, day) — so 288 BTC up/down 5-minute markets in one day stop
  counting as 288 independent draws — *strengthened* the result slightly.
- **The pattern is symmetric.** Top decile +6.21 → +3.55pp, bottom decile
  → −2.6 to −3.8pp. Noise regresses both deciles to the same mean; this does not.
- **Survivorship is small.** Survivor-minus-quitter period-1 excess is +0.82pp
  and +0.32pp at two cuts and *negative* at the other two. It is not driving it.
- Everything above is **excess over the entry-price-bucket benchmark**, so
  favourite-longshot exposure is already netted out.

**The verdict is therefore NOT "NO PERSISTENCE".** It hinged on Phase 4c, which
has since run: the excess above is measured at *the wallet's own fill price*, and
a copier gets a later price plus spread plus fee. The answer is `EDGE, SLOW
DECAY` — decay is flat to 1800s — but the copyable remainder is below the spread.

**Consistency of the headline number across all three cuts** (selection always on
period 1 only):

| Cut | Top-decile excess | **Copier (buy & hold)** | Gap (edge in exits) |
|---|---|---|---|
| 2025-01-01 | +3.953 [3.47, 4.42] | **+1.981 [1.45, 2.52]** | 2.330 |
| 2025-07-01 | +2.567 [2.19, 2.96] | **+0.937 [0.53, 1.38]** | 2.380 |
| 2026-01-08 (fee regime) | +2.068 [1.30, 2.82] | **−0.135 [−0.93, 0.63]** | 2.614 |

The gap is the most stable quantity in the study (2.33 / 2.38 / 2.61pp), and the
copier return **declines monotonically to negative** at the cut whose period 2
lies entirely in the fee-bearing era — negative *before* any spread is charged.

### Favourite-longshot bias still exists, but is ~2pp not ~7pp
Pooled edge by entry-price bucket on the wallet panel (n=1,450,999 wallet-market
observations): longshots lose (0.10–0.40 → −0.57 to −1.12pp gross), favourites
win (0.60–0.95 → +1.01 to +2.24pp gross). Net of fee the favourite band is
+0.43 to +1.17pp. So the bias is real and directionally as described, but far
smaller than the +7.05pp the prior attempt reported.

---

## STATE: what is done, what is running, what is next

### Done
- **Phase 0 complete.** `docs/data_availability.md`, probes 00–09, raw results in
  `data/probe_0*.json`.
- **Universe enumerated:** 2,108,796 markets from the CLOB (2,134 pages, 1,152s)
  → `data/markets_clob.jsonl` (2.04 GB). Composition in
  `data/markets_clob_stats.json`.
- **Market sample drawn:** 2,529 markets, 41 strata, seed 20260801 →
  `data/sample_markets.jsonl`, composition in `data/sample_composition.json`.

- **Wallet panel built:** 2,500 wallets, **14,082,296 fills** (1,533s, 73 wallets
  truncated at the 80k cap) → `data/wallet_fills.jsonl` (~4 GB).
  **Content verified real, not just non-empty:** all 10 expected keys; prices
  strictly inside (0,1), median 0.4900, zero out-of-range; shares all non-zero;
  both sides present; timestamps span 2023-05-13 → 2026-04-28; `fee_usd`
  non-zero on 25.0% of rows, consistent with the 2026-01-08 regime break; zero
  degenerate rows.
- **Positions reconstructed:** **1,746,750** positions. 99.27% settled, 2.55%
  flagged, 89.2% held to settlement, hedge rate 17.9%, only 6 fills with a token
  missing from the universe map.
- **Market panel built:** **2,778,373 fills** across 2,529 markets (258 with no
  fills, 1 truncated). The 80/20 buy-vs-sell skew confirms mint matches dominate.
- **All nine phases run.** Phase 5 deliberately skipped — it is gated on an
  actionable window existing, and none does.

### Nothing is running. Nothing is left on the ladder.

Remaining work is the two follow-ups named above (prospective book recording;
testing exit-copying), both of which need wall-clock time this session did not
have.

---

## Key facts a successor needs

**The economic bar** (one-way taker fee, cents/share; settlement pays no exit fee):

| Price | Polymarket | Round trip | Kalshi | Poly ÷ Kalshi |
|---|---|---|---|---|
| 10¢ / 90¢ | 1.00¢ | 2.00¢ | 0.63¢ | 1.59× |
| 25¢ / 75¢ | 2.50¢ | 5.00¢ | 1.31¢ | 1.90× |
| 50¢ | **5.00¢** | 10.00¢ | 1.75¢ | **2.86×** |

**Data limits that constrain everything:**
- Orderbook subgraph covers **2022-11-21 → 2026-04-28** and is still stale
  (~3 months behind; `hasIndexingErrors: false`, it simply is not advancing).
  Activity / pnl / positions subgraphs all **404**.
- Live tape is **~10 minutes deep**, `offset` capped at 10,000. The subgraph gap
  cannot be bridged backwards, only by recording forward.
- `/activity?user=` caps at `offset` 5,000.
- **Gamma filters are mostly silently ignored** (`tag_slug`, `slug_contains`,
  `closed=false`, `active=true`, `liquidity_num_min`). Only `closed=true` and
  `order`/`ascending` work. **Default ordering is oldest-first** — the exact trap
  that produced a prior false positive. Verify every filter on returned rows.

**Accounting rules, each forced by a measurement (see DECISIONS.md):**
- **Maker leg only** — the taker also appears as a maker in the same transaction
  in 298/298 cases, so counting both legs double-counts.
- **Per-token, never per-market-net** — 218/298 transactions have all makers on
  one side (mint/merge matches).
- **The metric is `realised value per share − average entry price`**, never a win
  rate, and always **excess over the entry-price-bucket benchmark**.
- **Unit of observation is a MARKET**, never a trade. 21 bets on one match is one
  observation.

---

## Sample composition (report before believing any result)

**Eligible universe: 874,943 markets** (clean settlement + inside subgraph
coverage + dated).

| | eligible | sampled (2,529) |
|---|---|---|
| other | 348,734 (40%) | 994 (39%) |
| crypto up/down 5m | 258,543 (30%) | 557 (22%) |
| sports | 171,744 (20%) | 574 (23%) |
| crypto other | 63,024 (7%) | 225 (9%) |
| politics | 18,963 (2%) | 129 (5%) |

By year (eligible): 2023 3,370 · 2024 13,545 · 2025 219,467 · 2026 638,561.

**Known deviation from proportionality, deliberate:** the sample is
pre-regime-weighted (1,529 pre / 1,000 post) against an eligible set that is
post-weighted (252,200 pre / 622,743 post). Cause is the per-stratum floor of 20
and ceiling of 250 with 36 pre-regime months against 4 post-regime months. This
buys coverage of the long history for persistence testing at the cost of exact
proportionality. Any headline number must be reported per regime, not pooled.

---

## Blocked / not attempted

- **Forward validation of the decay curve.** Needs the live tape recorded
  prospectively; the subgraph's 3-month lag plus the tape's 10-minute depth make
  it impossible from history alone. Not started — would need wall-clock time.
- **Second-source settlement cross-check.** Intended check (Gamma by
  `clob_token_ids`) returns an empty list, so CLOB `tokens[].winner` is currently
  single-sourced. Gamma by `condition_ids` is untested and is the obvious next
  attempt. Logged as an open audit item, not a blocker.

---

## API courtesy note

Per the overnight instruction, two other sessions share the **Kalshi** API. This
study touches **Polymarket only** (Goldsky subgraph, CLOB, data-api) and never
Kalshi, so there is no contention with them. The wallet pull was already ~35%
complete with 6 workers when the instruction arrived; it was allowed to finish
rather than discarded, and everything after it runs single-threaded. Goldsky has
returned no 429s at any point. (Decision D10.)
