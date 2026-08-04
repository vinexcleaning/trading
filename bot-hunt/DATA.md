# DATA.md — Step 3 output

**Every row here was produced by FETCHING, on 2026-08-04.** Two prior sessions in
this repo listed sources that turned out to be 404 or 403, so nothing is
recorded from a link, a memory or a README. Raw evidence:
`reports/sources_probe.json`, `pinnacle_probe.json`, `historical_probe.json`,
`overlap_probe.json`, `listing_depth.json`, `dimension_e.json`.

---

## 1. The reference-price layer — the finding of this step

### `guest.api.arcadia.pinnacle.com` — ALIVE, FREE, UNAUTHENTICATED

Requires a browser User-Agent and the public web client's `X-API-Key`. No
account, no payment, no rate-limit headers observed.

| sport | id | matchups | priced straight markets | bytes | coverage |
|---|---|---|---|---|---|
| Soccer | 29 | 4,456 | **27,582** | 14.8 MB | full |
| Tennis | 33 | 352 | **3,728** | 2.0 MB | full, incl. **period-1** handicaps |
| Baseball | 3 | 867 | 1,920 | 1.1 MB | full |
| Am. football | 15 | 377 | 1,509 | 0.8 MB | full |
| **E Sports** | **12** | **81** | **643** | 0.3 MB | full |
| Basketball | 4 | 89 | 637 | 0.3 MB | full |
| Golf | 17 | 87 | 87 | — | outright only |
| MMA | 22 | 22 | 33 | — | |

| field | present |
|---|---|
| American price per participant | ✅ |
| `points` (handicap / total line) | ✅ |
| `period` (0 = full, 1 = first set/half) | ✅ |
| `cutoffAt` | ✅ |
| `status` (open / closed) | ✅ |
| **`limits: maxRiskStake`** | ✅ — the sharp book's own capacity signal |

| property | value |
|---|---|
| licence | none stated; public web-client endpoint |
| update frequency | continuous (a `version` counter increments per market) |
| timestamp quality | `cutoffAt` is exact; **the observation time is the fetch time**, so the recorder stamps it |
| **backfills?** | **NO.** Live-only. No historical endpoint exists on this API. |

> **This is why the recorder started at 2026-08-04 21:27 UTC**, before the
> shortlist was written. Recording accrues in wall-clock time and is the only
> thing in this project that cannot be recovered by working harder later.

**Prevalence check:** only **3 of 3,195** cached whole-repo archives in
`signal-github` reference this endpoint, against 129 that use the keyed
`the-odds-api` and 82 that merely name Pinnacle.

### Historical sharp odds — PARTIAL, and the split matters

| source | status | verdict |
|---|---|---|
| **football-data.co.uk `PSCH`/`PSCD`/`PSCA`** | **200** | **Pinnacle CLOSING odds.** 94–96% populated, **2012 → 2026-08-03/04**. The only free historical sharp line found. Soccer only. |
| sportsbookreview.com root / odds / API | **503** | down at probe time |
| sportsbookreview.com `/consensus/` | 200, 1.29 MB, 11,541 odds-shaped tokens | **current** consensus, not historical |
| oddsportal | 200, only 16 odds tokens | JS-rendered; not a data source without a browser |
| oddsshark, covers | 200, mentions downloads | current lines |
| aussportsbetting | **403** Cloudflare | |
| betfair historicdata | **403** | |
| the-odds-api | **401** | key required → `PAID_OPTIONS.md` |

**Consequence, and it is the binding one for this project:** the sharp reference
is backfillable **for soccer only**. For tennis, esports, baseball and
basketball it is **forward-recording only**.

---

## 2. Kalshi — retention measured, not assumed

Two endpoints, two retentions, and the distinction has not been drawn in this
repo before.

| endpoint | reaches back | measured by |
|---|---|---|
| `/markets/trades` (the tape) | **71 days, earliest 2026-05-25** | bisection today |
| `/markets` (the listing — supplies **result**, strikes, close time) | **also 2026-05-25** | 4 independent queries |

The listing is what turns a trade into a labelled observation, so **the shared
boundary is the real constraint.** `status=settled`, `min_close_ts` at −365 days,
no status filter, and a window placed entirely before the boundary all return the
same earliest `close_time`, and **13 of 18 unrelated candidate families share the
identical date.**

> ⚠ **This contradicts `market-selection/WHAT_IS_LEFT.md`**, which calls the tape
> "THE DECAYING ITEM", retaining exactly 69 days, rolling one day per day, with
> a hard deadline of 2026-08-19. It bisected the boundary to **2026-05-25** on
> 08-02; I bisect it to **2026-05-25** on 08-04. Two days of wall clock, no
> movement — the window **grew** 69 → 71 days.
>
> **Two observations are not enough to overturn the claim.** They are enough to
> stop treating the 08-19 deadline as established. **Re-bisect before acting on
> it.** Recorded in `DECISIONS.md` D8.

### Retrievable settled EVENTS (the unit of observation), vs LEDGER K014

K014: **481** events for a 5 pp edge at 80% power; **2,084** to clear a 2.4¢ bar.

| series | markets | **events** | mkts/event | vs 481 |
|---|---|---|---|---|
| KXITFMATCH | 16,000 | **8,000** | 2.00 | **16.63×** |
| KXITFWMATCH | 15,272 | **7,636** | 2.00 | **15.88×** |
| KXCS2GAME | 3,297 | **1,648** | 2.00 | **3.43×** |
| KXWTAMATCH | 1,948 | 974 | 2.00 | 2.02× |
| KXATPMATCH | 1,884 | 942 | 2.00 | 1.96× |
| KXMLBGAME | 1,814 | 907 | 2.00 | 1.89× |
| KXMLBTOTAL | 11,163 | 908 | 12.29 | 1.89× |
| KXMLBRFI | 905 | 905 | 1.00 | 1.88× |
| KXLOLGAME | 1,463 | 719 | 2.03 | 1.49× |
| KXVALORANTGAME | 1,000 | 500 | 2.00 | 1.04× |
| KXMLBHR | 16,000 | 477 | **33.54** | 0.99× |
| KXMLSGAME | 159 | 53 | 3.00 | 0.11× |
| KXARGPREMDIVGAME | 126 | 42 | 3.00 | 0.09× |
| KXLIGAMXGAME | 84 | 28 | 3.00 | 0.06× |
| KXDIMAYORGAME | 63 | 21 | 3.00 | 0.04× |
| KXCOPADOBRASILGAME | 24 | 8 | 3.00 | 0.02× |

> **`KXMLBHR` is the clearest illustration of GUARDS #8 on this page:
> 16,000 markets and 477 events — 33.5 markets per observation.** Quoting the
> market count would overstate the evidence by 33×.

### Price history

`/series/{s}/markets/{t}/candlesticks`, hourly. **Different schema from the
market object**: on a candle, `yes_bid` is a live nested dict with
`open_dollars`/`close_dollars`; on a market it is dead and you must read
`yes_bid_dollars`. `STATUS.md` names four files that read candles correctly and
says explicitly not to "fix" them.

---

## 3. Polymarket

| | |
|---|---|
| books | CLOB `/book?token_id=` — public, no key |
| markets | Gamma `/events?tag_slug=&closed=false&active=true` |
| depth | 38–233 levels vs Kalshi's 20-level server cap |
| tick | 0.1¢ |
| **backfills?** | touch: no. Book: `archive.pmxt.dev` returns **200** with a real archive index; `r2v2.pmxt.dev/` root **404**. |

**Two-sided uptime, this session's recorder (each cycle samples ≤40 tokens):**

| tag slug | two-sided |
|---|---|
| baseball / mlb | 100% |
| soccer | 100% |
| dota-2 | **94%** |
| valorant | **92%** |
| cs2 | **85%** |
| tennis | 42% |
| **weather** | **15%** |

> ⚠ **`tag_slug=esports` and `league-of-legends` are UNUSABLE queries.** Ordered
> by `volume24hr` they return mostly `acceptingOrders=false` events (96 of 156)
> — settled blockbusters ahead of live thin markets — and read as **0%
> two-sided**. That produced a false kill on the highest-value lead in the
> project. Query the **specific game slug** with `active=true`. `DECISIONS.md` D7.

---

## 4. Domain data, re-verified

| source | status | note |
|---|---|---|
| MLB StatsAPI | **200** | |
| Statcast (one day) | **200**, 4,438 rows × 119 cols | richest free data anywhere on the list |
| NWS points | **200** | perfect for a market with no counterparty |
| ClubElo | **200**, 593 rows | |
| Liquipedia LoL | **200**, 475 KB | the only living esports source |
| bo3.gg | **200**, 9,950 chars | |
| Leaguepedia cargoquery | 200 but **372 bytes** on a 20-row query | reproduces the prior reading |
| **Oracle's Elixir (LoL)** | **404** | S3 bucket deleted |
| **HLTV (CS2)** | **403** | Cloudflare |
| **vlr.gg API** | **402** | Payment Required |
| **PandaScore** | **403** | key required |
| **GRID.gg** | **404** | |
| **`site.api.espn.com` scoreboard** | **403 on 7 of 7 leagues** | ⚠ **REGRESSION** — see below |
| `sports.core.api.espn.com` events | **200** | the v2 path still works |

> ### ⚠ The ESPN regression is load-bearing and is flagged, not fixed
> `market-selection` used ESPN's free feed on **2026-08-02** to find 3,699
> priced DraftKings player props across 6 games, 100% priced. **That finding
> killed its own #1 mechanism** and is what established `KXMLBRFI`'s
> no-free-reference property, which is the entire basis of shortlist entry #3.
> Two days later the endpoint returns **403 on every league tried**. The `core`
> v2 path still answers. **Anything resting on the ESPN prop feed must be
> re-established before it is quoted again.**

---

## 5. ⚠ The trap, reproduced exactly

football-data.co.uk returns **HTTP 200 with the wrong country's file**.
Confirmed two independent ways — sha256 of the body **and** the file's own
`League` column:

| requested | sha256 (16) | rows | League column says |
|---|---|---|---|
| `COL.csv` | `b9d1c59553b70628` | 1,999 | **Ekstraklasa** (Poland) |
| `POL.csv` | `b9d1c59553b70628` | 1,999 | Ekstraklasa |
| `KOR.csv` | `aa649e866b03d2ea` | 1,999 | **Eliteserien** (Norway) |
| `NOR.csv` | `aa649e866b03d2ea` | 1,999 | Eliteserien |

Byte-identical, no error of any kind. `src/probe_sources.py` hashes every
download, reads the `League`/`Div` column on every tabular file, and prints
byte-identical pairs from different URLs as a **named failure**.

**This belongs in [GUARDS.md](../GUARDS.md) as a 13th guard**: *a 200 is not a
correct file; hash it and check its own content column.*

Consequence: **`KXDIMAYORGAME` (Colombia) has no free reference line** and is
excluded on D as well as E.

---

## 6. What is recording now

`src/record.py`, started **2026-08-04 21:27 UTC**, 10-minute cycles, WAL +
120-second busy timeout, into `data/record.db` (gitignored).

| source | what | why it must be live |
|---|---|---|
| Pinnacle | 6 sports, matchups + every priced straight market | no historical endpoint at any price |
| Kalshi | 18 series, full L2 touch + 5¢ depth, **re-listed every cycle** | no historical book endpoint; markets 404 after retention |
| Polymarket | 8 game-level tag slugs, touch + 5¢ depth | touch is not archived |

Health is content-level, never a row count (GUARDS #12): non-empty fraction,
two-sided fraction and level counts per source per cycle. Two known-dead weather
families ride along as a **negative control on the instrument** — they read
42%/67% against 100% elsewhere, which is what a working recorder should say.
