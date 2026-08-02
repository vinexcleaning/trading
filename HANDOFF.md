# HANDOFF.md — market-selection session, 2026-08-02 (overnight)

Scope: **select markets.** No strategy was tested and no prior study re-run.
All new work is in `market-selection/` plus a shared `common/` module.
Full detail: [SHORTLIST.md](market-selection/SHORTLIST.md),
[killed.md](market-selection/killed.md),
[universe.md](market-selection/universe.md),
[data-availability.md](market-selection/data-availability.md),
[DECISIONS.md](market-selection/DECISIONS.md),
[LEDGER_ADDITIONS.md](market-selection/LEDGER_ADDITIONS.md),
[WHAT_IS_LEFT.md](market-selection/WHAT_IS_LEFT.md).

---

## 1. THE SHORTLIST

Ranked by **how cheaply the remaining question can be closed**, not by appeal.
93 of 153 depth-covered families survived the pre-registered kill switch.

### 1 — South American / Mexican soccer · KXLIGAMXGAME, KXARGPREMDIVGAME, KXLIGAMXTOTAL, KXDIMAYORGAME, KXCOPADOBRASILGAME

| Series | trades/day | mkts/day | settles/wk | 2-sided uptime | spread med/p90 | bid size | depth 5¢ | cost bar |
|---|---|---|---|---|---|---|---|---|
| KXLIGAMXGAME | 156,942 | 17 | 40 | 100.0% (n=126) | 1.0/2.0¢ | 18,062 | 332,644 | **1.97¢** |
| KXARGPREMDIVGAME | 31,195 | 40 | 101 | 100.0% (n=72) | 1.0/1.0¢ | 1,032 | 68,360 | 2.05¢ |
| KXLIGAMXTOTAL | 26,663 | 36 | 40 | 100.0% (n=102) | 1.0/1.0¢ | 2,761 | 64,960 | 2.23¢ |
| KXDIMAYORGAME | 25,010 | 26 | 74 | 100.0% (n=102) | 2.0/2.0¢ | 664 | 52,775 | 2.52¢ |
| KXCOPADOBRASILGAME | 21,576 | 26 | 67 | 100.0% (n=72) | 1.0/2.0¢ | 420 | 40,003 | 2.09¢ |

**Edge needed ~2.0 pp.** No maker fee. **D: free Pinnacle CLOSING odds back to
2012, de-viggable** — Liga MX 4,437 matches, Argentina 5,928, Brazil 5,275,
MLS 5,800.
**Mechanism:** Kalshi's counterparty is US retail; the sharp price forms at
Pinnacle, which does not accept US retail and is not bridged to Kalshi.
**Case against:** T012/T013 tested this exact hypothesis on tennis and it
failed. **I expect a null.** It ranks first because it is a one-day test.
*Colombia has no free Pinnacle line — see §5 R9.*

### 2 — MLB first-inning and game derivatives · KXMLBRFI, KXMLBTOTAL, KXMLBSPREAD, KXMLBF5TOTAL

| Series | trades/day | mkts/day | settles/wk | 2-sided | spread | bid size | depth 5¢ | cost bar |
|---|---|---|---|---|---|---|---|---|
| KXMLBRFI | 40,889 | 30 | 208 | 100.0% (n=120) | 1.0/1.0¢ | **301,578** | **2,280,909** | 2.24¢ |
| KXMLBTOTAL | 154,517 | 314 | 202 | 100.0% (n=126) | 1.0/1.0¢ | 7,802 | 306,989 | 2.24¢ |
| KXMLBSPREAD | 68,341 | 178 | 202 | 100.0% (n=108) | 1.0/1.0¢ | 8,734 | 1,590,111 | 2.21¢ |
| KXMLBF5TOTAL | 27,314 | 156 | 202 | 100.0% (n=99) | 1.0/2.0¢ | 971 | 11,132 | 2.23¢ |

**Deepest books on the list — capacity is not the constraint.** D is the richest
free data anywhere (Statcast 2,923 rows × 119 cols for one day; StatsAPI live
feed 885 KB per game).
**Mechanism:** **KXMLBRFI is the only MLB family with no matching entry in
DraftKings' free prop list** (34 types scanned).
**Case against:** the mechanism is an assertion with no evidence; 1st-5-Innings
lines ARE free, so KXMLBF5TOTAL is probably already referenced.

### 3 — MLB player props · KXMLBHR, KXMLBKS, KXMLBHIT, KXMLBHRR, KXMLBTB

| Series | trades/day | mkts/day | settles/wk | 2-sided | bid size | cost bar |
|---|---|---|---|---|---|---|
| KXMLBHR | 25,378 | 456 | 1,976 | 100.0% (n=102) | 5,360 | **1.29¢** |
| KXMLBKS | 23,641 | 308 | 323 | 100.0% (n=102) | 644 | 2.24¢ |
| KXMLBHIT | 12,461 | **742** | 1,942 | 100.0% (n=102) | **50** | 2.25¢ |
| KXMLBHRR | 9,230 | **917** | 1,929 | 100.0% (n=87) | 118 | 2.24¢ |
| KXMLBTB | 8,016 | **821** | 1,835 | 100.0% (n=87) | 295 | 2.21¢ |

**Up to 1,976 settlements/week — nothing else accumulates evidence that fast.**
**But thin: 50–644 contracts at the touch.**
**Mechanism (downgraded mid-session):** DK's free prop prices are **one-sided**,
so the feed gives a price but not a fair probability; Statcast supports building
one.
**Case against:** my own measurement of this was **inconclusive** — see §5 R10.

### 4 — NPB / KBO baseball · KXNPBGAME, KXKBOGAME, KXNPBTOTAL

| Series | trades/day | mkts/day | settles/wk | 2-sided | spread | bid size | cost bar |
|---|---|---|---|---|---|---|---|
| KXNPBGAME | 48,960 | 30 | 108 | **27.9% (n=129)** ⚠ | 2.0/4.0¢ | 435 | 2.75¢ |
| KXKBOGAME | 17,487 | 25 | 94 | 94.4% (n=90) | 1.0/2.0¢ | 421 | 2.25¢ |
| KXNPBTOTAL | 13,087 | 49 | 87 | 35.9% (n=78) | 2.0/12.0¢ | 34 | 2.65¢ |

⚠ **The NPB uptime figures are contradicted by a fresh probe (100% two-sided,
2,043 at the touch) and are an artifact of my own recorder — see §5 R11.**
**Mechanism:** language and time-zone friction.
**Case against:** no free odds reference exists at all; Asian books cover these
sharply; the scraper must be built before anything can be measured.

### Excluded despite the best market metrics on the exchange

**Tennis** (KXATPMATCH 248,880/day, KXITFMATCH 243,522, 100% two-sided, 1.0¢,
**no maker fee on ITF/Challenger**, 309–524 settles/week) — **no mechanism.**
Sackmann deleted; **no free ITF source exists at all**; and S008 already found
all 15 tennis maker configurations net-negative.
**Crypto** (KXBTC15M 1,753,887/day) — four inputs everyone has; C010 settled it.
**Golf** (lowest cost bar on the exchange, 0.76¢) — free data is scores, not
skill; 7 settlements/week.
**Esports** (KXCS2GAME 64,572/day, 21,236 at touch) — free data layer collapsed.
**Polymarket, all families** — 2.86× Kalshi's fee at 50¢ with the same 1.0¢
median spread on MLB.

---

## 2. KILL REASONS

**Kill 1 — no order book at all.** KXMVESPORTSMULTIGAMEEXTENDED (510,281 trades)
and KXMVECROSSCATEGORY (136,326) are **82.9% of Kalshi's entire 419,828-market
universe** and have **zero quotes on either side**, on two independent probes
hours apart. They are combinatorial parlays minted on demand: the trades are
real but there is no resting book to place an order into. **High trade count is
not a counterparty.**

**Kill 2 — one-sided books. The weather result, reproduced with a mechanism.**
Sixteen families quoted on one side only across 4 fresh markets each; eleven are
weather/temperature (KXHIGHLAX, KXRAIN, KXTEMPAUSH, KXHIGHTSFO, KXHIGHTSEA,
KXTEMPLAXH, KXHIGHTLV, KXTEMPNYCH, KXTEMPDCH, KXTEMPCHIH), plus
KXFOXNEWSMENTION, KXTRUMPSAY, KXTRUTHSOCIAL, KXAFLGAME, KXNEXTTEAMMLB,
KXWNBANEXTTEAM. The NWS API is free, complete and is the exact settlement
product — **dimension D at maximum, and it does not matter.** (KXHIGHDEN and
KXHIGHTPHX revived and are named as exceptions.)

**Kill 3 — cost so high the required edge is implausible.** KXLIGAEXPTOTAL 57¢
spread (~30 pp needed), KXLIGAEXPGAME 51¢ (~27 pp), KXARGNACBGAME 50¢ (~27 pp),
KXUSLTOTAL 18¢, KXUSLGAME 7¢. For scale the largest genuine effect in the whole
archive is 2.42 pp.

**Kill 4 — dimension D.** Crypto (four inputs everyone has), golf (strokes-gained
paywalled at 403, every free scraper stale), esports (Oracle's Elixir bucket
deleted, HLTV 403, vlr.gg 402).

**Kill 5 — too thin to validate.** KXGOVFLNOMR, KXSAVEACT, KXSENATEMID, KXMI13D
and the one-off novelty series (1–2 markets each, fee-free, unvalidatable).

**Kill 6 — killed by omission, and named as such.** The tape shows **2,205
series trading**; the recorder covers 153 and the sweep reached 300. **~1,900
families were measured on trades/day only.** They are **not killed, they are
unmeasured**, and writing them up as kills would be dishonest.

---

## 3. WHAT IS RECORDING

| What | Where | Since | State |
|---|---|---|---|
| **Broad depth recorder** — 231 markets, 85 families, 20 levels/side | `market-selection/data/depth_broad/<date>/<hh>/depth.jsonl` | 06:38 UTC (v4 with live re-listing from 08:25) | alive; **8,827 snapshots** before the fix at 90.8% non-empty / 90.5% two-sided, and **99.6% / 97.4% on the first cycle after it** — 0 invalid, 0 bad prices, 0 crossed books throughout |
| **pmxt L2 mirror** | `market-selection/data/pmxt/` | complete 08:10 UTC | **662/662 files, 63.0 GB, every file content-validated** |
| **Decaying trade backfill** (see §5 R6) | `market-selection/data/tape_pmxt_window/` | 07:17 UTC | 2026-05-25 **complete (3,447,536 trades, 1.1 GB)**; 05-26 in progress; ~11 h to finish 05-27→06-11 |
| Tennis depth recorder, PID 17892 | `C:\Users\gianf\kalshi\set1_overshoot\data\depth\` | 08-01 02:58 | **untouched**, verified alive |
| Crypto 15m opens, PID 24756 | `C:\Users\gianf\crypto\data\btc15m_opens\` | 08-01 13:42 | **untouched**, verified alive |

A content heartbeat runs every 30 minutes (`src/recorder_heartbeat.py`) and
checks content, not row counts.

**Added after this file was first printed — two-sided uptime is diurnal.**
Across seven heartbeats from 08:28 to 11:31 UTC the exchange-wide reading moved
between **99.6% and 86.5% non-empty** and between **97.4% and 80.0%
two-sided**, troughing near 11:00 UTC once the US sports book has settled
overnight. Every per-family uptime figure in §1 was measured in the favourable
**06:38–08:30 UTC** window and is a snapshot, **not a 24-hour average**. No
ranking changes — nothing approaches the 50% kill threshold — but a full-day
uptime profile is the cleaner measurement and has not been run.

---

## 4. RESULTS TABLE

| Measurement | n | Unit of observation | Date range |
|---|---|---|---|
| Kalshi universe | 419,828 markets / 3,074 series / 229,030 events | market | open at 2026-08-02 02:12 UTC |
| Polymarket universe | 31,487 markets in top 2,100 events / 1,157 tags | market | 2026-08-02 06:47 UTC (**truncated — gamma 422s at offset 2100**) |
| **Exchange-wide trade tape** | **8,867,978 trades / 2,205 series** | trade | **2026-08-01T06:35 → 2026-08-02T06:35 UTC (exactly 24 h)** |
| Depth recorder | 8,827 snapshots / 153 series | snapshot | 2026-08-02 06:38 → ongoing |
| Wide depth sweep | 262 series with open markets | series-snapshot | 2026-08-02 07:33 |
| Re-probe of dead families | 37 families | series-snapshot | 2026-08-02 07:45 |
| Cross-venue MLB | 66 game sides ≈ **40 independent games** | game side | 2026-08-02 07:05 |
| Kalshi vs DraftKings moneyline | 26 game sides = **13 games** | game side | 2026-08-02 07:55 |
| Kalshi vs DraftKings props | 105 props | player-threshold | **CANCELLED — confounded, see §5 R10** |
| 3-way soccer ladder sums | **93 fully quoted events** | event | 2026-08-02 07:50 |
| pmxt mirror | 662 hourly files | hour-file | 2026-05-14T14 → 2026-06-11T03 |
| Trade backfill | 3,447,536 trades (1 day complete) | trade | 2026-05-25 |
| Domain-data probes | 79 sources | source | 2026-08-02 |
| Soccer odds coverage | 28 country files | file | history to 2026-07 |
| MLB prop structure | 15 families × 14 markets | market | 2026-08-02 |
| Polymarket CLOB depth | 208 markets / 26 tags | market | 2026-08-02 07:25 |

---

## 5. RETRACTIONS

**As prominent as the findings, because there are more of them.**

### Premises in the tasking that are false

**R1. "archive.pmxt.dev has rolling 30-day retention and deletes itself
continuously."** **FALSE.** It is frozen. Files from 2026-05-16 still serve at
**78 days old**; every hour after 2026-06-11T03 is 404. Under 30-day retention
the surviving set would be the exact inverse of what is observed. Coverage is
**2026-05-14T14 → 2026-06-11T03, 662 files** — a capture that stopped, with its
back catalogue intact. Mirroring is insurance against an abandoned bucket, not a
race.

**R2. "One session found `/orderbook` empty and concluded depth is not public;
another recorded 20 levels a side."** Both saw what they reported and **both
were defeated by a key name.** Resolved in §9.

### My own corrections, this session — six, all shrinking the edge

**R3.** I reported **"0 of 60 non-empty orderbooks"**, including a market with
1.6 M in 24 h volume, and was about to conclude depth is not public. **My own
parser bug** — I read `["orderbook"]["yes"]`, which does not exist. 85 markets
probed wrongly before I caught it.

**R4.** I reported pmxt `frac_empty = 0.9998`. **Invalid** — computed over the
first 20,000 rows, which are nearly all deltas, and delta rows carry empty level
arrays by construction. On snapshot rows: 25.30% one side, 4.99% both.

**R5.** I printed a pmxt ladder of `(1.0, 2.0)` at every level on every market
and nearly reported it as degenerate. **The struct children are literally named
`"1"` and `"2"`**; iterating the dict yielded its keys.

**R6.** I claimed the depth recorder had "written nothing for 15 minutes" and
diagnosed a stall. **Wrong twice over**: the timestamp was Windows lazy metadata
on an open handle, and I had misread the clock by 25 minutes.

**R7.** My first cross-venue join matched **0 of 76** MLB markets and I could
have reported "the venues share no events". It was a nickname/city mismatch on
my side. Corrected to 66 of 76.

**R8.** **Kalshi vs DraftKings, MLB moneyline: at n=8 sides (4 games) I measured
median 3.74¢ with 6 of 8 exceeding the cost bar, including a 10.37¢ gap.** That
was a stale ESPN line plus a tiny sample. **At n=26 sides (13 games): median
0.37¢, max 1.94¢, 0 of 26 exceed the bar.** The correction took the effect from
"large" to "nothing".

**R9. I nearly put Polish league data behind a Colombian market.**
football-data.co.uk returns **HTTP 200 with a wrong-country file** for codes it
does not carry. Confirmed byte-identical by sha256: `COL ≡ POL ≡ BOL` (Poland),
`KOR ≡ NOR` (Norway), `CHL ≡ CHI ≡ CHN` (China). Status code, byte count and
column names all look healthy; only the `League` column and a content hash catch
it. **Colombia, Peru, Ecuador, Uruguay and Chile have no free Pinnacle line.**

**R10. I deleted my own top-ranked entry's mechanism.** SHORTLIST #1 originally
claimed *"no free public reference price exists for MLB player props"*. **False.**
ESPN's free odds object carries a `propBets` `$ref` resolving, unkeyed, to
**555–677 fully priced DraftKings props per game** (3,699 scanned across 6
games, **100% priced**, with line, current and **opening** price, covering
strikeouts, hits, total bases, HR, HRR, team totals and 1st-5-innings).
I then measured Kalshi vs DK on 105 props and got *median gap 4.55¢, 79%
exceeding the cost bar* — **and did not publish it**, because DK's prop entries
are one-sided, so the −3.52¢ mean signed gap is what a 4–7% vig looks like. A
de-vigging pass found **zero** two-sided prop lines. **Verdict: INCONCLUSIVE,
not suggestive.**

**R11. My recorder was measuring its own staleness.** It selected tickers from a
market dump captured once at 02:12 and never re-listed. Long-lived families were
fine; short-lived ones accumulated settled books, and **a settled book reads as
no counterparty**. KXBTC15M recorded **0.0% two-sided over 36 snapshots** while
a fresh listing showed it quoted two-sided at 0.1¢; KXNPBGAME recorded 27.9%
against a fresh 100%. **The recorder has been fixed to re-list live from the
API, and the fix is confirmed: the first cycle after it read 99.6% non-empty
and 97.4% two-sided, against 90.8% / 90.5% on the stale list.** The NPB and
BTC15M uptime figures in §1 predate the fix and are floors, not estimates.

**R12.** My own validator produced **three separate false FAILs** on the mirror:
absent parquet statistics read as "price out of range" (2 files), and a required
`orderbook_delta` that the archive's final 6 hours legitimately lack (they are
snapshot-only). All 8 recovered. *Not knowing is not the same as knowing it is
bad* — the UNTESTABLE/FAIL confusion from GUARDS #1, pointed the other way.

### Corrections to STATUS.md / LEDGER.md

**R13.** GUARDS #12 flagged the legacy price fields as *suspected* null.
**Confirmed:** `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, `last_price`, `volume`,
`open_interest`, `liquidity` were non-null on **0 of 200** open markets.

**R14.** `tick_size` **does not exist** on the Kalshi market object at all, nor
`tick_size_dollars`, `min_tick` or `response_price_units`, on any of 419,828
markets. The real tick is `price_level_structure` ∈ {`linear_cent` 1¢ (63,207),
`deci_cent` 0.1¢ (348,428), `tapered_deci_cent` (8,193)}.

**R15.** STATUS.md says "closed markets 404 and are gone". More precisely: the
window is **exactly 69 days** (trades present at 2026-05-25, zero at 05-24), and
**inside** it settled markets still resolve as `finalized` — 8 of 8 spot-checked
from 68 days ago.

> **Not one correction this session revealed a larger effect.** That is now
> ~47 across the archive with the same sign. All six of mine were found by
> trying to falsify my own claims.

---

## 6. CANARIES AND CONTROLS

| Guard | Ran? | Result |
|---|---|---|
| Content validation, not row counts (#12) | ✅ per row | **0 invalid of 8,827 rows**; 0 prices outside (0,100); 0 negative sizes; **0 crossed books**; 0 torn lines |
| Recorder collapse alarm (#12) | ✅ armed | fires below 5% non-empty after 300 rows; never fired |
| 30-minute content heartbeat (#12) | ✅ running | DEPTH OK on every check |
| Exact-decimal fee arithmetic (#6) | ✅ | `common/costbar.py` asserts 7 Kalshi reference points + Polymarket at import; float-dust regression asserted; 2.86× ratio re-derived |
| P&L/cost decomposition is an identity (#7) | ✅ | asserted in `cost_bar_cents`, residual < 1e-6 |
| Fill at the ask, never the mid (#7) | ✅ | every cross-venue and vs-book comparison priced at executable touch |
| Pre-registered gate before seeing numbers (#10) | ✅ | kill-switch thresholds fixed in DECISIONS.md **D8 while the tape was still downloading** |
| Pre-registered failure conditions (#10) | ✅ | written into SHORTLIST.md before any strategy work |
| Effective n stated (#8) | ✅ | cross-venue 66 sides ≈ 40 games; DK 26 sides = 13 games; props n=105 **cancelled** |
| Duplicate/pagination canary | ✅ | 419,828 rows → 419,828 distinct tickers, **0 duplicates** |
| Complete-tiling guard (C014's lesson) | ✅ | the 3-way soccer test refuses any event without a complete two-sided 3-leg tiling |
| Wrong-country content hash (new) | ✅ | sha256 across 13 country files caught 5 duplicates |
| Selection canary (#1) | ➖ n/a | no dedupe of mirrored sides was performed |
| Synthetic null / positive control (#3, #4) | ❌ **not run** | no model was fitted, so there was nothing to control. **If the next session fits anything, these are mandatory.** |
| Guard-rot test (#9) | ⚠ partial | fee reference points asserted at import; no known-bad-input test for the new guards |
| BH-FDR across the ledger (#11) | ➖ n/a | no hypothesis tests with p-values were run this session |

---

## 7. STILL OPEN

**Blocked on wall-clock only:** the trade backfill (~11 h left, resumable) and
the depth recorder (runs until stopped).

**Blocked on access:** exhaustive Sackmann mirror search (GitHub *code* search
needs a token — only 23 of 660 candidate repos were checked); Polymarket below
the top 2,100 events (gamma 422s at offset 2100); FBref and HLTV (403
Cloudflare); DataGolf strokes-gained (paid); stats.nba.com (connection reset);
FRED and the-odds-api (need keys); the 538 approval CSV (200 and 310 KB but
parses to 0 columns).

**Not run for time:** cross-venue on **politics** (where the venues most
plausibly disagree — Polymarket's politics book is larger and tighter at a 1.1¢
median on $13.7 M/24 h); cross-venue **persistence** (the gap distribution is
measured, its persistence is not); **reconstructing a book from the pmxt
deltas** (99.73% deltas; nothing has replayed snapshot+deltas yet — this is the
biggest piece of unbuilt machinery); depth for the ~1,900 unmeasured families;
verification that `fee_multiplier = 0` on 11 series is real.

**Carried from STATUS.md, untouched and still open:** the v3 backtest dedupe
field (CH057, ~100× the evidence base of anything else); the **desktop recorder
`None` bug — now MORE urgent, because this session confirmed all 8 legacy price
fields are null on 100% of sampled markets**; the live bot position-sizing
blowout (CH044, top standing financial risk).

---

## 8. NEXT THREE ACTIONS, by information gain per hour

1. **Kalshi vs the Pinnacle closing line on Liga MX / Argentina / Brazil.**
   ~2 hours. The data is free, de-viggable and backfilled to 2012 (15,640
   matches). It closes shortlist entry #1 outright, and by the T012 template it
   either finds the only mechanism on this list that survives or kills it. **Do
   this first.**
2. **One grep on the desktop: does `kalshi_client.py` / `record_data.py` read
   the legacy price field names?** ~10 minutes. This session proved those fields
   are null on 100% of markets. If the desktop recorders read them, **every book
   recorded on that machine is worthless** and it gates all Tier B work. The
   cheapest high-stakes check available anywhere in the project.
3. **Check whether any free feed publishes an MLB first-inning line.** ~30
   minutes. It is the single cheapest way to kill shortlist entry #2, and
   killing it is worth as much as confirming it.

*(Runner-up: keep the backfill alive. It loses one irrecoverable day per day.)*

---

## 9. WHAT THE COORDINATING CHAT HAS WRONG

**Kalshi order-book depth is free. It never needed to be bought.**
The `/markets/{ticker}/orderbook` response carries **exactly one top-level key**:

```json
{"orderbook_fp": {"yes_dollars": [["0.1200","100.00"], …],
                  "no_dollars":  [["0.1300","15.00"],  …]}}
```

There is **no `orderbook` key and no `yes`/`no` key**. Code reading those gets an
empty book from an HTTP 200 on *every* market, liquid or dead — which is exactly
the "returns empty, depth is not public" conclusion. **I reproduced the same
error on 85 markets before finding it.** The session that recorded 64,898
snapshots at 20 levels a side was reading `orderbook_fp.yes_dollars` and was
right. Live: **90.8% of snapshots carry depth, 90.5% two-sided.** `S013` stands;
mark "depth is not public" **RETRACTED**.

**pmxt is not an emergency; the trade tape is.** The archive is frozen, not
melting (§5 R1). The genuinely decaying asset is the **Kalshi trade tape, which
retains exactly 69 days and rolls daily.** The pmxt order-book window is
2026-05-14→06-11, so **its matching trades are expiring one day per day, and
2026-05-14→05-24 is already gone.** The whole overlap is unrecoverable by
**2026-08-19**. Depth without trades cannot answer what would have filled. A
backfill is running oldest-first; **if it stops, restart it before anything
else.**

**"Rich free data" is not the scarce input, and dimension D is not the binding
constraint anywhere it matters.** Weather has perfect free data — the exact NWS
product Kalshi settles on — and is quoted **one-sided**, so it is untradeable at
any edge. Crypto has four inputs and everyone has all four. Conversely, tennis
has the best market on the exchange and **no free ITF data at all**. The binding
constraint is a counterparty, and after that, a mechanism.

**Stop expecting Kalshi to be soft.** Three independent measurements now say
otherwise: Kalshi ≡ Betfair on tennis (T012), Kalshi ≡ DraftKings on MLB
moneyline at **0.37¢ median with 0 of 26 exceeding the cost bar**, and Kalshi's
3-way soccer ladders arbitrage-free on **93 of 93** events. Cross-venue against
Polymarket is **0 of 66** net-positive against a 6.75¢ fee floor. The working
hypothesis for the next week should be *"Kalshi is the sharp line"*, with the
shortlist as attempts to falsify it — not the reverse.

**Trade count is not a counterparty.** The two exotic parlay series generate
646,607 trades a day, are 82.9% of the entire market universe, and have **no
public order book at all**. Any ranking built on volume or trade count puts them
first.

---

*Committed and pushed. `market-selection/` holds 30 scripts, 30 reports and 6
documents; `common/` holds the shared fee/guard module (backlog #6).*
