# BLOCKED_ON_DESKTOP.md

Everything here requires the **desktop** machine (`C:\Users\vinig\kalshi` and its
siblings). None of it exists on this laptop — the only user profile here is
`gianf`, and `C:\Users\gianf\kalshi` is the unrelated tennis player-model project.

Confirmed against the prior audit (`Desktop\kalshi audit\LAPTOP_COPY.md`), which
lists these explicitly under "What is *not* here".

---

## A. Cannot be recreated anywhere — recorded only

**Kalshi order-book history is not retrievable from the Kalshi API.** There is no
historical-book endpoint; books exist only in whatever was recorded live. This is
the hard blocker of the session.

| item | size / scope | why it matters |
|---|---|---|
| Recorded Kalshi order books (`record_data.py`) | live recordings, ongoing | **The only possible Tier B (order-book replay) input for Kalshi.** Without it every Kalshi backtest is Tier A — an upper bound, not a tradeable number. |
| ~1.77M recorded trades, BTC + exchange-wide recorders | ongoing | counterparty fingerprinting, cancel-to-trade, depth-at-touch vs time-to-expiry |
| 27,083-observation recorder dataset | tennis-era, but same recorder | fill-model calibration, queue-position realism |
| 94 live trade records | — | the only ground truth on **realised** fees and actual fill prices; needed to verify the fee schedule empirically rather than from docs |

**Consequence for this session:** Phase 2 (microstructure, counterparty
fingerprint, depth-vs-expiry, adverse selection) and Phase 6 Tier B are
**Kalshi-blocked**. They are *not* Polymarket-blocked — Polymarket fills are
permanently public on-chain, which is why the session was reordered to lead with
Polymarket.

## B. Re-pullable here, but redundant to re-collect

Listed so the desktop copy is reused rather than duplicated. Not blocking.

| item | scope | note |
|---|---|---|
| ~6,271 settled `KXBTC15M` markets | back to 2026-05-25 | re-pullable from `/markets?status=settled`, but the desktop copy is already validated |
| 102,716 one-minute BTC/ETH candles, 100% coverage | 2026-05-25 → | re-pullable free; spot venues all reachable from here |
| Intraday volatility seasonality curve | derived | regenerable from the candles |
| v3 candlestick backtest + 14,162-market pull | tennis | not crypto; ignore for this project |

## C. Merge hazards to carry to the desktop session

1. **Never copy folder-over-folder.** The laptop `kalshi` and desktop `kalshi`
   share a name and zero files. Merge as siblings under one parent with a single
   git repo at the parent level.
2. **Kalshi legacy price fields now return `None`.** Any desktop code reading
   `yes_bid` / `yes_ask` / `last_price` / `volume` / `open_interest` from
   `/markets` is silently getting `None` — the live values moved to
   `yes_bid_dollars` / `yes_ask_dollars` / `volume_fp` / `open_interest_fp`.
   This is the same shape as the orderbook-parser corruption already in this
   project's history (correct row counts, empty content). **Check
   `kalshi_client.py` and `record_data.py` on the desktop before trusting any
   recording made after the API change.** If the recorders have been writing
   `None` prices, the recorded books are worthless and the blocker in §A is worse
   than it looks.
3. Prior work's fee assumptions should be re-derived against `src/fees.py` here —
   in particular whether the round-UP-to-cent behaviour was modelled. If fees
   were floored or computed in floats, every prior cost number is slightly wrong
   in the optimistic direction.

## D. What to run first on the desktop

1. Verify §C.2 — are the live recorders writing real prices or `None`? One grep.
2. If they are healthy, extend the recorders to the **hourly ladder series**
   (`KXBTC`, `KXBTCD`, `KXETH`, `KXETHD`, `KXSOLD`, `KXXRP`), which this session
   established use fixed round-number strikes and trade across the full price
   range. Prior recording covered only `KXBTC15M`.
3. Days of recording needed before Kalshi Tier B is viable: TBD from a power
   calculation in `docs/GO_NO_GO.md` (not yet written).
