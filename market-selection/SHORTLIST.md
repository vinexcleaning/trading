# SHORTLIST.md — markets worth a week of work

Measured 2026-08-02. Evidence: the **full 24 h exchange-wide trade tape
(8,867,978 trades, 2,205 series, 2026-08-01T06:35 → 2026-08-02T06:35 UTC)**, a
continuous depth recorder (8,827 snapshots, 153 series), a one-shot depth sweep
over the top 300 families, a fresh re-probe of everything that looked dead, and
free-data probes verified by fetching.

**93 of 153 depth-covered families survive the pre-registered kill switch.**
Four are ranked below.

> **⚠ Caveat on every two-sided-uptime figure in this file.** They were measured
> in a **06:38–08:30 UTC** window. A 30-minute content heartbeat run afterwards
> shows uptime is **diurnal**: across seven checks from 08:28 to 11:31 UTC the
> exchange-wide reading moved between **99.6% and 86.5% non-empty**, and between
> **97.4% and 80.0% two-sided**, with the trough around 11:00 UTC once the US
> sports book has settled overnight. The per-family figures below are therefore
> a snapshot of a favourable window, **not a 24-hour average**. Nothing here
> comes close to the 50% kill threshold, so no ranking changes — but a full-day
> uptime profile is the cleaner measurement and has not been run.

> **Read this against the prior.** LEDGER.md records ~41 corrections across five
> studies and **every one shrank the edge**. This session added **six more with
> the same sign**, including one that deleted the entire stated mechanism of
> what had been my top-ranked entry. Nothing below is a finding. These are the
> four places where a finding is still *possible*.

---

## ⚠ The three results that constrain everything below

Measured this session, before the ranking was written:

1. **Kalshi's MLB moneyline already tracks the free DraftKings line.** n = 26
   game sides (13 games): median |Kalshi mid − devigged DK| = **0.37¢**, p90
   0.75¢, max 1.94¢, and **0 of 26 exceed the cost bar**. This reproduces
   LEDGER T012 (Kalshi ≡ Betfair on tennis) for a second sport.
2. **ESPN's free feed publishes priced DraftKings player props** — 555–677 per
   game, 3,699 scanned across 6 games, **100% priced**, with line, current and
   *opening* price, covering Total Strikeouts, Hits, Total Bases, HR, HRR, Team
   Total Runs and 1st-5-Innings. **This killed my original #1 mechanism.**
3. **Kalshi's 3-way soccer ladders are internally consistent**: n = 93 fully
   quoted events, median ask overround **+3.00¢**, **0 of 93** baskets
   net-profitable in either direction.

So "we would know a price nobody else has" is false almost everywhere on Kalshi.
The four entries below are ordered by **how cheaply the remaining question can
be closed**, not by how exciting they sound.

---

## 1. South American / Mexican soccer

**Ranked first because it is the only entry whose question can actually be
answered this week, with free backfillable data.**

| Series | trades/day | mkts/day | settles/wk | 2-sided uptime | spread med / p90 | >tick | bid size | depth 5¢ | cost bar | fee |
|---|---|---|---|---|---|---|---|---|---|---|
| **KXLIGAMXGAME** | 156,942 | 17 | 40 | 100.0% (n=126) | 1.0 / 2.0¢ | 0.31 | 18,062 | 332,644 | **1.97¢** | quad |
| **KXARGPREMDIVGAME** | 31,195 | 40 | 101 | 100.0% (n=72) | 1.0 / 1.0¢ | 0.00 | 1,032 | 68,360 | 2.05¢ | quad |
| **KXLIGAMXTOTAL** | 26,663 | 36 | 40 | 100.0% (n=102) | 1.0 / 1.0¢ | 0.00 | 2,761 | 64,960 | 2.23¢ | quad |
| **KXDIMAYORGAME** | 25,010 | 26 | 74 | 100.0% (n=102) | 2.0 / 2.0¢ | 0.61 | 664 | 52,775 | 2.52¢ | quad |
| **KXCOPADOBRASILGAME** | 21,576 | 26 | 67 | 100.0% (n=72) | 1.0 / 2.0¢ | 0.33 | 420 | 40,003 | 2.09¢ | quad |

- **A** — 100% two-sided uptime on every one, over 72–126 recorded snapshots.
- **C** — **~2.0 pp of edge required.** No maker fee on any of them.
- **D** — **free Pinnacle CLOSING odds back to 2012, de-viggable**: Liga MX
  4,437 matches, Argentina 5,928, Brazil Serie A 5,275, MLS 5,800. Plus
  StatsBomb events, ClubElo daily ratings, and live DraftKings moneylines from
  ESPN's free feed.
- **E** — 40–101 settlements/week.

**Hypothesis.** Kalshi's counterparty on South American football is US retail.
The sharp price forms at Pinnacle, which does not accept US retail and is not
bridged to Kalshi by any arbitrageur. If Kalshi's pre-match price deviates from
the Pinnacle close by more than ~2.0 pp, systematically, that is collectable.

**Why the error would persist.** Nobody has an incentive to bridge a book this
size across a venue boundary a US retail user cannot cross in the other
direction.

**Recording:** all five in the continuous recorder. KXMLSGAME is **not** — it
has no open events (MLS between matchdays) and must be added when play resumes.

**The honest case against — and it is strong enough that I expect a null.**
LEDGER **T012/T013** tested this exact hypothesis on tennis and it failed:
Kalshi was indistinguishable from the Betfair close (r = 0.9878, MAD 1.95¢ vs a
2.44¢ cost) and, where the two disagreed by more than it cost to act, Kalshi was
closer **49.1% [42.7, 55.6]** of the time, with all 14 segments crossing zero.
The MLB moneyline result this session says the same thing for a second sport.
And the 3-way ladders are already well arbitraged. **This entry earns first
place because it is cheap to close, not because it is likely to pay.**

Note **KXDIMAYORGAME (Colombia) has no free Pinnacle line** — the
football-data.co.uk `COL` file is byte-identical to `POL` and contains Poland's
Ekstraklasa. It is recorded and listed, but it is *not* testable the cheap way.

---

## 2. MLB first-inning and game derivatives

**The deepest books on the list, and one market with no free reference.**

| Series | trades/day | mkts/day | settles/wk | 2-sided uptime | spread med / p90 | >tick | bid size | depth 5¢ | cost bar | fee |
|---|---|---|---|---|---|---|---|---|---|---|
| **KXMLBRFI** | 40,889 | 30 | 208 | 100.0% (n=120) | 1.0 / 1.0¢ | **0.00** | **301,578** | **2,280,909** | 2.24¢ | quad |
| **KXMLBTOTAL** | 154,517 | 314 | 202 | 100.0% (n=126) | 1.0 / 1.0¢ | 0.09 | 7,802 | 306,989 | 2.24¢ | quad |
| **KXMLBSPREAD** | 68,341 | 178 | 202 | 100.0% (n=108) | 1.0 / 1.0¢ | 0.09 | 8,734 | 1,590,111 | 2.21¢ | quad |
| **KXMLBF5TOTAL** | 27,314 | 156 | 202 | 100.0% (n=99) | 1.0 / 2.0¢ | 0.16 | 971 | 11,132 | 2.23¢ | quad |
| *(KXMLBGAME, for reference)* | 377,022 | 97 | 356 | 100.0% (n=132) | 1.0 / 2.0¢ | 0.13 | 20,887 | 1,290,590 | 2.25¢ | quad+maker |

- **B** — **KXMLBRFI holds 301,578 contracts at the touch and 2.28 M within
  5¢.** Capacity is not the constraint anywhere in this group, which is rare.
- **C** — ~2.2 pp required; **no maker fee** on RFI/TOTAL/SPREAD/F5TOTAL.
- **D** — the richest free data of any family on either venue: Statcast at
  **2,923 rows × 119 columns for a single day**, MLB StatsAPI's live feed at
  **885 KB per game**, Retrosheet to 1871.
- **`>tick` = 0.00 on KXMLBRFI** — the book sits at the minimum tick
  essentially always, so there is no room to improve the quote. That is a
  maker-strategy kill and a taker-cost floor at the same time.

**Hypothesis.** The moneyline is already efficient (0.37¢). But a first-inning
run depends almost entirely on one starting pitcher and the top three hitters —
a far narrower object than a full game, and one Statcast describes at pitch
level. **KXMLBRFI is the only MLB family with no matching entry in DraftKings'
free prop list** (34 prop types scanned; no first-inning type present).

**Why the error would persist.** First-inning is a secondary market priced off
the game total by convention rather than modelled independently, and unlike the
props there is no free screen for the counterparty to copy.

**Recording:** all four in the continuous recorder.

**The honest case against.**
- **The mechanism is an assertion about how the counterparty prices, with no
  evidence.** I did not measure whether RFI is priced off the total.
- **1st-5-Innings moneyline, run line and total ARE in the free DK feed**, so
  KXMLBF5TOTAL is probably already referenced and likely dies the way the
  moneyline did. Only RFI has the no-reference property.
- A book that prices the moneyline to 0.37¢ is unlikely to misprice its own
  first innings by 2 pp.
- 301,578 contracts at the touch may be one market maker who withdraws under
  adverse flow. A single snapshot cannot tell.

---

## 3. MLB player props

**Richest data anywhere; mechanism downgraded from "private view" to "better
de-vigging", which is a much weaker claim.**

| Series | trades/day | mkts/day | settles/wk | 2-sided uptime | spread med / p90 | >tick | bid size | depth 5¢ | cost bar | fee |
|---|---|---|---|---|---|---|---|---|---|---|
| **KXMLBHR** | 25,378 | 456 | 1,976 | 100.0% (n=102) | 1.0 / 1.0¢ | 0.00 | 5,360 | 59,639 | **1.29¢** | quad |
| **KXMLBKS** | 23,641 | 308 | 323 | 100.0% (n=102) | 1.0 / 2.0¢ | 0.15 | 644 | 19,612 | 2.24¢ | quad |
| **KXMLBHIT** | 12,461 | **742** | 1,942 | 100.0% (n=102) | 1.0 / 1.0¢ | 0.00 | **50** | 11,220 | 2.25¢ | quad |
| **KXMLBHRR** | 9,230 | **917** | 1,929 | 100.0% (n=87) | 1.0 / 2.0¢ | 0.14 | 118 | 7,872 | 2.24¢ | quad |
| **KXMLBTB** | 8,016 | **821** | 1,835 | 100.0% (n=87) | 1.0 / 2.0¢ | 0.15 | 295 | 7,403 | 2.21¢ | quad |

- **A** — 100% two-sided on all five, and **308–917 distinct markets traded per
  day**, the widest breadth on the exchange outside the parlays.
- **B** — **thin. 50–644 contracts at the touch.** KXMLBHIT's median bid is
  **50 contracts** — a $25 position at 50¢.
- **C** — ~2.2 pp, except KXMLBHR at **1.29¢** (its traded prices sit near the
  wings where the quadratic fee is small).
- **E** — up to **1,976 settlements/week**. Nothing else on this list can
  accumulate evidence at that rate.

**Hypothesis (revised, and weaker than the one I started with).** DraftKings'
free prop prices are **one-sided** — a single American price per milestone, with
**zero** two-sided over/under entries found. So the free feed gives a *price*
but not a *fair probability*. Statcast supports constructing the fair
probability directly; the counterparty copying the DK screen inherits DK's
margin.

**Why the error would persist.** 300–900 prop markets per game night, each
holding 50–644 contracts. The infrastructure cost is fixed and the revenue per
market is capped by depth, so a professional's return on it is poor. **A
capacity moat, not an information moat** — it lasts exactly as long as the
markets stay small.

**Recording:** all five in the continuous recorder.

**The honest case against.**
- **My attempt to measure this was inconclusive and I am reporting it as
  inconclusive, not as suggestive.** Kalshi-vs-DK on 105 matched props read
  median |gap| 4.55¢ with 79% exceeding the cost bar — but DK's prop entries are
  one-sided, so the −3.52¢ mean signed gap is what a 4–7% vig looks like. A
  de-vigging pass found **0** two-sided prop lines. The measurement cannot
  separate disagreement from margin.
- **Depth is the whole problem.** 50 contracts at the touch is an operations
  problem disguised as a strategy.
- The books price these props with the same Statcast. The claim is only that
  *this counterparty* is worse, which is much weaker.
- A 1¢ quoted spread may mean stale resting orders rather than competitive ones
  — filled only when wrong. That is S009's adverse-selection result waiting to
  happen.

---

## 4. NPB / KBO baseball

**Included with the lowest confidence of the four, and with a live measurement
conflict I could not resolve.**

| Series | trades/day | mkts/day | settles/wk | 2-sided uptime | spread med / p90 | bid size | depth 5¢ | cost bar |
|---|---|---|---|---|---|---|---|---|
| **KXNPBGAME** | 48,960 | 30 | 108 | **27.9% (n=129)** — *but see below* | 2.0 / 4.0¢ | 435 | 7,739 | 2.75¢ |
| **KXKBOGAME** | 17,487 | 25 | 94 | 94.4% (n=90) | 1.0 / 2.0¢ | 421 | 8,294 | 2.25¢ |
| **KXNPBTOTAL** | 13,087 | 49 | 87 | 35.9% (n=78) | 2.0 / 12.0¢ | 34 | 1,240 | 2.65¢ |

**⚠ The two-sided figures for NPB are contradicted by a fresh probe** which
found **100% two-sided with 2,043 contracts at the touch**. The cause is a flaw
in my own recorder: it selected tickers from a static market dump and never
re-listed, so short-lived markets accumulated as settled books, and a settled
book reads as no counterparty. **The recorder has been fixed to re-list live**,
but the NPB numbers above were collected before the fix and should be treated
as a floor, not an estimate.

**Hypothesis.** Kalshi lists Japanese and Korean baseball for a US audience
whose counterparty is unlikely to be reading Japanese- or Korean-language
sources. Language and time-zone friction is the moat.

**The honest case against.**
- **No free odds reference exists at all.** The `KOR` file on
  football-data.co.uk is **Norway's Eliteserien**; `JPN` is **J-League soccer**,
  not NPB baseball. Validation is against realised outcomes only.
- Asian bookmakers cover NPB and KBO heavily and sharply. "Nobody is watching"
  is almost certainly false — there is simply no free window into what the
  watchers think, which is worse.
- The scraper must be built first, so week one yields infrastructure, not an
  answer.
- My own measurements of this family have disagreed with each other twice.

---

## Excluded, despite excellent market metrics

| Family | Market quality | Why excluded |
|---|---|---|
| **Tennis — ITF, ATP, WTA, Challenger** | **the best on the exchange**: KXATPMATCH 248,880 trades/day, KXITFMATCH 243,522, KXITFWMATCH 180,378, KXWTAMATCH 180,049; 100% two-sided; 1.0¢ spreads; 135k–177k within 5¢; **no maker fee on ITF/Challenger**; 309–524 settlements/week | **No mechanism, therefore no entry.** Sackmann's ATP/WTA archive is **deleted** (the account now has exactly one public repo). ⚠ ~~**No free ITF source exists at all**~~ **— THAT IS FALSE, CORRECTED 2026-08-09 (LEDGER B021).** A **free** key returned **7,786 ITF tournaments** on 2026-08-06. The six sources probed on 08-02 (ITF's own API 212 bytes, Challenger archive 403, Sofascore 403, ESPN main-tour only) were simply not the whole set. **⚠ But read what it does and does not give before re-ranking:** B021 supplies **scores and tournaments, NOT PRICES.** **This entry's mechanism needs a reference PRICE, and that claim is untouched and still stands** — so the entry does not move on B021 alone. **And LEDGER B009 measured ITF economics as the worst of any tier** (≈9¢ lost per trade over 6,135 trades). **Data availability reopens. The trade does not.** ITF is ~76% of the book. And the non-data route is already closed: **S008 tested 15 maker configurations on tennis and every one was net-negative**, with adverse selection exceeding price improvement. |
| **Crypto** | KXBTC15M **1,753,887 trades/day** — the busiest family on the exchange; KXBTCD 301,072 | Four inputs everyone has. **C010** measured the consequence with a validated positive control. KXBTC15M additionally quotes only ~57 contracts at the touch and is structurally dead (`floor_strike` = prior settlement in 99.86%). |
| **Golf** | **the lowest cost bar on the exchange at 0.76¢**, 0.6¢ spread, 24,215 at the touch, 610k within 5¢ | Free golf data is **scores, not skill**. Strokes-gained is behind DataGolf (403, paid); every free scraper found is stale. Also only **7 settlements/week**. |
| **Esports** | KXCS2GAME 64,572/day at a 1.0¢ spread with 21,236 at the touch; KXLOLGAME 35,985 | **The free data layer collapsed**: Oracle's Elixir returns `NoSuchBucket`, HLTV 403, vlr.gg 402. |
| **Polymarket** | deeper books than Kalshi (38–233 levels vs a 20-level server cap), 0.1¢ tick | **Cost.** `0.10·min(p,1−p)` is **2.86× Kalshi at 50¢**, and on MLB the two venues have the *same* 1.00¢ median spread. Cross-venue: **0 of 66** trips net-positive against a 6.75¢ two-venue fee floor. |

---

## What would make each one fail — written before any strategy work

Pre-registered so a later null is a measurement, not a disappointment.

**1. South American soccer fails if** — Kalshi's pre-match price correlates with
the Pinnacle close above ~0.98 with MAD below the ~2.0¢ bar (what T012 found for
tennis); **or** the disagreements split near 50/50 on who is closer (what T013
found). **I expect this.** It is on the list because it is a one-day test, not
because it is likely to pay.

**2. MLB derivatives fail if** — a free feed publishes first-inning lines and
Kalshi tracks them under 1¢, as the moneyline already does (**check this
first — it is the cheapest kill available**); **or** RFI's 301,578-contract
touch proves to be one maker who withdraws under adverse flow.

**3. MLB props fail if** — median touch depth stays under ~200 contracts over a
full week (the capacity moat is also our ceiling); **or** the 1¢ spread turns
out to be stale rather than competitive, so resting orders fill only when
wrong; **or** a Statcast estimate lands within ~1 pp of the market on a
held-out month.

**4. NPB/KBO fails if** — the scraper takes more than two days to produce a
clean panel; **or** the model does not beat the Kalshi mid by more than ~2.3 pp
on a held-out period; **or** the fixed recorder confirms NPB two-sided uptime
below 50%.

**All four fail together if** the pattern now visible in three independent
measurements holds generally: **Kalshi is the sharp line.** T012 found it for
tennis; this session found it for MLB moneyline at 0.37¢ and found Kalshi's
3-way soccer ladders arbitrage-free on 93 of 93 events. If that generalises,
none of these four has an edge — and the correct output of the next week is to
write that down as the finding, not to keep slicing until something clears.
