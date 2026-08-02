# PROGRESS

Wallet copy-trading feasibility study. Read-only public data, simulated fills
only. No funded wallet, no order placement.

Priority ladder: Phase 0 → 1 → 3 → 4a → 4c → 2 → 4b → 4d → 5.

---

## 2026-08-01 — Phase 0 complete

**Written:** `docs/data_availability.md`, probes `src/probe_00..04b`, raw results
in `data/probe_0*.json`.

### Findings

- **Subgraph coverage 2022-11-21 → 2026-04-28.** Still stale (~3 months behind);
  `hasIndexingErrors: false`, head block 87,814,766. Not erroring, just not
  advancing. Activity / pnl / positions subgraphs all **404** — orderbook is the
  only survivor.
- **Live tape is ~10 minutes deep**, `offset` capped at 10,000. Cannot bridge the
  subgraph gap retrospectively; only by recording forward.
- **Fee formula verified independently.** `0.10 × min(p, 1−p)` per share: median
  relative error 7.7e-08, 100% within 1%, n=5,362, modal implied 1000 bps. The
  published `0.07 × p × (1−p)`: 0% within 1%. Documentation is wrong, confirmed.
- **NEW — fee regime break at 2026-01-08.** Fills carry `fee = 0` for **91% of
  on-chain history**. Wallets ranked on pre-break data earned their P&L without
  paying the fee a copier now faces. Usable post-fee window is only ~16 weeks.
  This was not anticipated by the brief and changes how Phase 4a must be split.
- **Address join works.** Subgraph `maker` addresses are proxy wallets; 16/16
  data-api lookups returned `proxyWallet == queried address`.
- **Taker leg contaminated by infrastructure.** `0x4bfb41d5…` (29.8% of fills)
  and `0xc5d563a3…` (5.9%) have no data-api record at all; the former is taker on
  the oldest fill in the sample. Phase 2 exclusion, structural.
- **Gamma filters mostly silently ignored** — `tag_slug`, `slug_contains`,
  `closed=false`, `active=true`, `liquidity_num_min` all return the unfiltered
  page. Only `closed=true` and `order`/`ascending` work. **Default ordering is
  oldest-first** — the exact trap that produced a prior false positive.

### Corrected during this phase

- First fee check reported median relative error 0.96 and only 3.2% within 1%.
  Cause: the maker's side was inverted — `makerAssetId == 0` means the maker
  *paid* USDC, i.e. bought, and the fee is denominated in the asset the maker
  *receives*. Re-derived and re-run; the formula holds exactly. Recorded because
  a silent sign error here would have poisoned every downstream cost figure.

### Status of the prior study's +7.23pp / +7.05pp figures

The prior copy-trading work is **not present on this machine** — a recursive
search of `C:\Users\gianf` found only an unrelated Kalshi/Polymarket
market-making project (`C:\Users\gianf\crypto`), no copy-trading study, no
wallet dataset. Its selection logic therefore **cannot be audited**, so its
+7.05pp naive-benchmark figure cannot be used as a benchmark or as a
sanity-check target. Phase 3 recomputes the naive benchmark from scratch, which
is what the brief requires regardless.

### Next

Phase 1 — position reconstruction. Sample composition (market types, volume,
per-regime counts) is reported before any analysis, per the brief.

---

## 2026-08-01 — Phase 1 in progress

### Source decisions, each forced by a measurement

- **Universe comes from the CLOB, not Gamma.** Gamma's offset ceiling is ~2400
  ("use /markets/keyset for deeper pagination") and its `clob_token_ids` filter
  returns an empty list rather than filtering. The CLOB cursor API serves 1000
  markets/page at ~50k per 30s and its `tokens[].winner` flag is settlement
  reported by the venue.
- **Maker leg only.** probe_08: in **298 of 298** transactions the `taker`
  address also appears as a `maker` in that same transaction, so every user
  order is emitted exactly once with `maker` = that user. Counting both legs
  would double-count every trade. 10 of 12 top takers are recognised by the data
  API as real users; the 2 unrecognised are the operator contracts already
  flagged in Phase 0.
- **Per-token accounting, not per-market-net.** probe_08 also found **218 of
  298** transactions have every maker on the *same* side — mint matches (both
  parties buy complementary tokens) and merge matches (both sell). Netting YES
  and NO would erase the entry price the whole study is built on.

### Design correction: one panel was not enough

The market-drawn sample (4,000 markets) was built first and is **kept for Phase
3**, where the sampling unit genuinely is the market. It is **not** adequate for
Phases 4a/4b: the CLOB enumeration passed 1.27M markets, so 4,000 markets is
~0.4% of any wallet's activity, and a wallet trading 1,000 markets would appear
in about four of them. Persistence needs many *independent markets per wallet
per period*; that sample structurally cannot deliver it.

So a second **wallet panel** is being built: ~2,500 wallets, complete fill
histories. probe_09 confirmed the subgraph filters on `maker` at ~0.49s per
1000-row page (one wallet's full 8,530-fill history took 4.4s); `maker_in` is
rejected, so it is one wallet per query.

**How the wallet draw is biased, stated rather than hidden.** Wallets are all
distinct makers found in 260 randomly placed 15-minute windows across the
history. That is *activity-weighted* — a wallet trading more often is likelier
to be drawn. This is deliberate: a wallet too inactive to appear is too inactive
to copy. The property that matters is that **no performance criterion enters the
draw**, since selecting wallets on past returns and then measuring their returns
is exactly the circularity that manufactures a leaderboard of lucky coinflips.

---

## 2026-08-01 — STUDY COMPLETE

**Verdict: EDGE, SLOW DECAY — but the copyable part is smaller than the spread.
Do not build.** Full reasoning in `COPY_TRADING_VERDICT.md`.

All nine phases done. Phase 5 deliberately skipped: it is gated on an actionable
window existing, and it does not.

- **Persistence exists** — ρ 0.157–0.433, positive in all 36 tested cells,
  rising with sample size, surviving both market-maker removal and series-day
  clustering. Top decile keeps +2.567pp excess out of sample, CI[2.19, 2.96].
- **Decay is flat** to 1800s, so no bot is justified and no latency budget exists.
- **72% of the edge lives in exits** — gap of 2.33 / 2.38 / 2.61pp at three
  independent cuts, the study's most stable finding.
- **The copyable remainder is consumed by the spread** — +0.937pp against a
  ≥1.0pp spread lower bound, and −0.135pp at the most recent cut.
- **Retracted:** an intermediate −5.9pp copy return from a 1,944-signal slice,
  corrected to +0.937pp at full sample size. Recorded prominently in the verdict.

**Final validation:** 32 tests pass (including three that recompute real
positions from raw fills and assert the pipeline agrees); canary re-run after the
last code change gives −0.0pp pooled excess with random subsets straddling zero.

---

### Known coverage gap, to be quantified not patched

Splits and merges (USDC ↔ complete token sets) are ConditionalTokens events and
are **absent from the orderbook subgraph**. A wallet that splits $1 into YES+NO
and sells one side has an entry cost that is invisible here. Position
reconstruction flags these as `negative_balance_split_or_external` rather than
repairing them, and they are excluded from edge statistics and reported as a
coverage gap.
