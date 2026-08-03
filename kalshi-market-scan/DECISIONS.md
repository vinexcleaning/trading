# Decisions log

Ambiguities resolved conservatively, per the standing instruction. Newest last.

---

**D-001 — Recorders poll REST, not WebSocket.**
Kalshi's WebSocket requires an RSA-signed handshake even for public market-data
channels. This project holds no credentials and will not create any. Cost: book rows
are snapshots rather than deltas and carry no exchange event timestamp (`event_ns` is
null on book rows; `recv_ns`/`write_ns` are always present). Accepted — the alternative
is introducing a credential path into a no-real-money codebase.

**D-002 — Assume the standard 0.07 fee multiplier everywhere, including S&P/Nasdaq.**
The master prompt and a 2022 Kalshi blog post say S&P 500 / Nasdaq-100 use a halved
0.035 multiplier. The live API contradicts this: `KXINX`, `KXNASDAQ100` and all 48
`KXINX*`/`KXNASDAQ100*` variants report `fee_multiplier: 1`. `kalshi.com/fee-schedule`
and the fee PDF returned HTTP 429 on every attempt, so the authoritative document was
never read. Conservative choice: **use 0.07 for every series.** This raises the cost bar
rather than lowering it, and it deliberately removes the stated reason to favour index
range markets. Revisit only after reading the live fee schedule.

**D-003 — `fee_multiplier: 0` series are treated as genuinely zero-fee but ignored.**
Nine series report a zero multiplier. Rather than assume a data defect, take it at face
value — but all nine are one-off or annual, so they fail the ≥50-settlements
recurrence bar regardless. No modelling effort spent.

**D-004 — Combo filtering is a hard non-null check, not a heuristic.**
A market is a combo iff `mve_collection_ticker` is non-null. 87.0% of open markets
qualify. Every flow/volume analysis drops these before aggregating. Chosen over
inferring combos from ticker patterns because the field is explicit and exact.

**D-005 — Recorder budget set to 8 req/s against a measured ~15 req/s wall.**
Measured 15 req/s → 0% 429, 25 req/s → 56% 429. Running at roughly half the measured
ceiling so that (a) hours-long unattended operation does not degrade, and (b) ad-hoc
analysis queries can share the budget. Observed 1,947 requests with 0 × 429.

**D-006 — Market index is authoritative over the series index.**
`/series?category=` returns 7,493 series but omits the `KXTEMP*` weather families
entirely, and `/series/KXTEMPDCH` does not resolve — yet
`/markets?series_ticker=KXTEMPDCH` returns markets. Any screen driven off the category
listing silently misses the highest-prior family on the exchange. All universe work
therefore enumerates **markets** and derives series from ticker prefixes.

**D-007 — Empty feeds during 07:00–09:00 UTC are recorded, not worked around.**
`trading_active: false` during the daily halt. Rather than pause recorders or
special-case the gap, `/exchange/status` is sampled every 30 s into
`source=kalshi_status` so every gap in the data is attributable after the fact. A gap
with `trading_active: false` is expected; a gap without one is a recorder defect.

**D-008 — Perp data comes from OKX and Deribit, not Binance or Bybit.**
Binance futures returns HTTP 451 and Bybit HTTP 403 from this host (geographic
restriction). OKX swaps and Deribit perpetuals are reachable, free and unauthenticated,
and supply funding rate, basis, mark price and open interest — everything Phase 5 asks
of perps. Noted because it means perp results are venue-specific and not
Binance-comparable.

**D-009 — `KXBTC15M` is modelled as an at-the-money up/down contract, not a strike ladder.**
Each market's `floor_strike` equals the previous window's `expiration_value`, so the
contract is "will BTC be ≥ its level 15 minutes ago". Consequence: entry sits at
P ≈ 0.50 where the quadratic fee is maximised (3.50¢ round trip), and the cheap tails
are structurally unreachable at entry. Recorded here because it reframes Phase 5 from
"find a directional edge" to "find a directional edge worth more than 3.5 points",
which is a materially harder claim.

**D-010 — Report `breakeven_edge` at C=100 contracts, not C=1.**
Kalshi ceils the fee to the whole cent per fill, so at C=1 every price from 10¢ to 90¢
rounds to the same 1¢ and the quadratic shape vanishes. Quoting per-contract cost at
C=100 shows the real curve. Flagged because a C=1 table makes the tails look no cheaper
than the middle, which would misdirect the entire cost-bar analysis.
