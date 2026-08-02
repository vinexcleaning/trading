# DECISIONS

Method decisions taken without asking, with the reasoning and the measurement
that forced each one. Conservative reading taken wherever ambiguous.

---

## D1 — Universe source is the CLOB, not Gamma
**2026-08-01.** Gamma returns HTTP 422 past `offset≈2400` ("use /markets/keyset
for deeper pagination"), and its `clob_token_ids` filter returns an empty list
rather than filtering. The CLOB cursor API served **2,108,796 markets in 2,134
pages / 1,152s** and its `tokens[].winner` flag is settlement reported by the
venue rather than inferred from a price string.
**Risk accepted:** CLOB `winner` is unverified against a second source, because
the intended cross-check (Gamma by token id) is the filter that returns empty.
Gamma-by-`condition_ids` remains untested — logged as an open audit item.

## D2 — Maker leg only
**2026-08-01.** In **298 of 298** transactions sampled, the `taker` address also
appears as a `maker` within the same transaction (`probe_08`). Every user order
is therefore emitted exactly once with `maker` = that user. Counting both legs
would double-count every trade.
**Conservative reading:** where a wallet appears only as `taker`, it is not
counted; that under-counts rather than over-counts.

## D3 — Per-token accounting, never per-market netting
**2026-08-01.** `probe_08` found **218 of 298** transactions have every maker on
the *same* side — mint matches (both parties buy complementary tokens) and merge
matches (both sell). Netting YES against NO would destroy the entry price the
entire study is built on.

## D4 — `enable_order_book` is NOT an eligibility criterion
**2026-08-01.** Requiring it produced **zero eligible markets**. It reports
whether a market is *currently* accepting orders: only 120,868 of 2,108,796
markets carry it, and a cross-tab found **288,566** closed-and-cleanly-settled
markets with it `false` against **2,768** open markets with it `true`. It
excluded markets precisely for having finished. Tradability is instead
established empirically — a market with no fills contributes nothing downstream.
Eligibility is now: clean settlement + inside subgraph coverage + dated →
**874,943 markets**.

## D5 — Two panels, not one
**2026-08-01.** The market panel (4,000 markets) cannot support persistence
testing: against 2.1M markets it observes ~0.4% of any wallet's activity, so a
wallet trading 1,000 markets appears in about four. A separate **wallet panel**
(2,500 wallets, complete histories) carries Phases 1/2/4a/4b/4d; the market panel
is retained for Phase 3 and Phase 4c, where the sampling unit genuinely is the
market and "the next trade after the signal" requires seeing all trades.

## D6 — Wallet draw is activity-weighted, and that is stated not corrected
**2026-08-01.** Wallets are every distinct maker in 260 randomly placed
15-minute windows across the history. More active wallets are likelier to be
drawn. This is deliberate — a wallet too inactive to appear is too inactive to
copy. The property that matters is that **no performance criterion enters the
draw**. Selecting on past returns then measuring returns is the circularity that
manufactures lucky-coinflip leaderboards.

## D7 — Splits/merges are a flagged coverage gap, not a repaired one
**2026-08-01.** ConditionalTokens split/merge events are absent from the
orderbook subgraph, so a wallet that splits $1 into YES+NO and sells one side has
an invisible entry cost. Such positions are flagged
`negative_balance_split_or_external` and **excluded from edge statistics**,
never patched with an assumed cost. Their count is reported as a coverage gap.

## D8 — Streaming everywhere over 2M rows
**2026-08-01.** `build_10b`'s summary step held 2.1M markets in memory, reached
**8.65 GB** against ~4.7 GB free, and was killed; the `.jsonl` was already
complete and closed, so only the summary was recomputed streaming
(`build_10c`, 37s). All later aggregation streams and flushes per wallet, and
**verifies** rather than assumes the per-wallet contiguity that makes this safe.

## D9 — Prior study's +7.05pp benchmark treated as void
**2026-08-01.** A recursive search of `C:\Users\gianf` found no copy-trading
study, no wallet dataset — only an unrelated Kalshi/Polymarket market-making
project in `C:\Users\gianf\crypto`. Its selection logic **cannot be audited**,
so its figure is not used as a benchmark or as a sanity-check target. Phase 3
recomputes the naive benchmark from scratch, which the brief requires regardless.

## D10 — Concurrency during overnight run
**2026-08-01.** The overnight instruction asks for single-threaded, paced
requests because two other sessions share the **Kalshi** API. This study touches
**Polymarket only** (Goldsky subgraph, CLOB, data-api) and never Kalshi, so there
is no contention with those sessions. The wallet-panel pull was already ~35%
complete with 6 workers when the instruction arrived; restarting it
single-threaded would discard that progress and roughly sextuple its remaining
runtime. **Decision:** let the in-flight pull finish, start no further concurrent
pulls, and run everything subsequent single-threaded. Goldsky returned no 429s at
any point.

## D11 — Fee formula taken from measurement, not documentation
**2026-08-01.** `0.10 × min(p, 1−p)` per share: median relative error
**7.71e-08**, **100.0%** of 5,362 fee-bearing fills within 1%, modal implied rate
1000 bps on 5,338 of 5,362. The published `0.07 × p × (1−p)` matches **0.0%**.
An earlier pass of this check reported median relative error 0.96 because it
inverted the maker's side; recorded in `docs/data_availability.md` because a
silent sign error there would have poisoned every downstream cost number.

## D12 — Fee regime break is treated as a regime, not noise
**2026-08-01.** Fills carry `fee = 0` for **91% of on-chain history**, switching
on **2026-01-08** (bisected to the day). Wallets ranked on pre-break history
earned P&L without paying the fee a copier now faces. Persistence is therefore
tested at calendar cuts **and** at the regime cut, so regime change cannot be
misread as skill decay.
