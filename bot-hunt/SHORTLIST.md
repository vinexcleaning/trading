# SHORTLIST.md — Step 2 output

**Measured 2026-08-04.** This does **not** re-derive
[`market-selection/SHORTLIST.md`](../market-selection/SHORTLIST.md) (2026-08-02,
built on an 8.87M-trade 24 h tape). It extends it, re-verifies what has gone
stale, and adds the two dimensions that pass changed or could not see.

**It also overturns that file's #1 entry, on a measurement that file never
made.** Details in §1.

---

## The two changes to the framework, and why each was forced

### Change 1 — dimension D is asked twice, not once

`market-selection`'s **D** is *"free data about the underlying thing"*. Under
that reading esports scores zero, and it really does: re-verified today,
Oracle's Elixir **404**, HLTV **403**, vlr.gg **402**, PandaScore **403**,
GRID **404**.

But the only strategy in any corpus attached to this repo that has a **public
wallet and a reconciled four-line P&L** needs no domain data at all. It de-vigs a
sharp sportsbook and quotes that number (PRIOR_ART §1a). So D is now scored on
two axes and both are printed:

| | question | who it favours |
|---|---|---|
| **D-domain** | is there free data about the underlying event? | MLB (Statcast), weather (NWS) |
| **D-ref** | is there a free, **sharper reference price**? | anything Pinnacle quotes |

**D-ref was verified by fetching today.** `guest.api.arcadia.pinnacle.com`
returns live priced markets, free and unauthenticated, with `maxRiskStake`
limits and period-level lines: **27,582** priced soccer markets, **3,728**
tennis, **1,920** baseball, **643 esports**, **1,509** American football. Only
**3 of 3,195** cached repo archives in `signal-github` use that endpoint.

### Change 2 — dimension E is measured on RETRIEVABLE events, not on a rate

`market-selection` scored E from the 24 h tape as *settlements per week*. That is
the right quantity if history is retrievable. **It is not.**

Measured today, four independent ways (`src/probe_listing_depth.py`): Kalshi's
market listing hard-stops at a shared calendar boundary. `status=settled`,
`min_close_ts` at −365 days, no status filter, and a window placed entirely
before the boundary all return the same earliest `close_time`.

> **13 of 18 candidate families share the identical earliest date, 2026-05-25.**
> A shared calendar boundary across unrelated sports is a **retention cutoff**,
> not a season start.

So E is re-scored as **retrievable settled events**, against LEDGER **K014**:
**481** events to detect a 5 pp edge at 80% power, **2,084** to clear a 2.4¢
cost bar. Unit is the **event** (one match), never the market — a 3-way soccer
ladder is 3 markets and **one** observation. GUARDS #8.

---

## 1. ⛔ THE PRIOR #1 IS DEAD, on dimension E

`market-selection` ranked **South American / Mexican soccer** first, on 40–101
settlements per week and 100% two-sided uptime. Both of those numbers are right
and I reproduced the uptime live today (100% two-sided on 4 of 5 families,
every cycle). **The family still fails**, because a rate you cannot retrieve is
not a sample:

| series | retrievable settled **events** | vs K014's 481 | earliest retrievable |
|---|---|---|---|
| KXMLSGAME | **53** | **0.11×** | 2026-05-25 |
| KXARGPREMDIVGAME | **42** | 0.09× | 2026-07-24 |
| KXLIGAMXGAME | **28** | 0.06× | 2026-05-25 |
| KXDIMAYORGAME | **21** | 0.04× | 2026-06-03 |
| KXCOPADOBRASILGAME | **8** | 0.02× | 2026-08-01 |
| **all five together** | **152** | **0.32×** | |

**152 matches against a 481 bar, and 0.07× the cost bar.** The mechanism was
never tested because the sample to test it with does not exist.

This is worth stating plainly because it is the second time the same shape has
appeared: `market-selection`'s own **K005** retraction was *"celebrating the
wrong axis"* — seven weather families cleared a capacity bar with 66 settlements
against 481 needed, so their depth decided nothing. **The prior #1 entry
repeated that error in its own shortlist**, on the axis its own `killed.md`
names as KILL 5.

The irony is exact: this is the one family where the sharp reference price is
also **backfillable** — football-data.co.uk's `PSCH`/`PSCD`/`PSCA` are Pinnacle
**closing** odds, 94–96% populated back to 2012 and current to 2026-08-03/04.
**The reference side has 14 years. The Kalshi side has 152 matches.**

---

## 2. The ranking, on measured A / B / C / D / E

Ranked by *how much of a real test each supports*, not by how promising it
sounds. `2S` = two-sided uptime measured by this session's recorder.

### #1 — Esports (CS2, LoL, Valorant), BOTH venues

| | Kalshi | Polymarket |
|---|---|---|
| **A** 2S uptime, live | **100%** on KXCS2GAME / KXLOLGAME / KXVALORANTGAME, every cycle | cs2 **85%**, dota-2 **94%**, valorant **92%** |
| **B** depth | 21,236 at touch on KXCS2GAME (prior sweep) | dota-2 top market **$51,029/24 h, 1.0¢ spread, 2,458 × 4,068**; valorant **18,060 × 41,270** |
| **C** cost | 1.0¢ spread, `quadratic` (no maker fee) | 0.1¢ tick, taker only |
| **D-domain** | **ZERO** — data layer verifiably collapsed | same |
| **D-ref** | **Pinnacle esports free: 81 matchups, 643 priced markets** | same |
| **E** | **CS2 1,648 events (3.43×)**, LoL 719 (1.49×), Valorant 500 (1.04×) | — |

**Mechanism.** The counterparty is US/global retail betting on esports through a
prediction market. The sharp price forms at Pinnacle, which most of that
counterparty does not read and cannot access. The error persists because
bridging it requires an odds pipeline nobody is paid to build for a book this
size — and, measured here, **almost nobody has: 3 of 3,195 repos use the free
Pinnacle endpoint at all.**

**Why it is #1: it is the only entry with an existence proof.** Someone ran
exactly this design on Polymarket esports with a public wallet: **+$8,293
arbitrage, −$3,184 unhedged residual, +$4,973 net over 3,858 fills and $96k
volume.**

**The honest case against, and it is severe:**
- **The same author switched it off.** Win rate **50.2 → 48.3 → 43.4** monthly as
  competition and fees arrived. Feb +$2,506, March +$390, stop. Five months ago.
- **38% of gross went to the unhedged residual**, from adverse selection on
  stale quotes. That term appears in no fee model in this repo and is the
  mechanism S008/S009 already found fatal on tennis.
- ⚠ **It cannot be backtested.** Pinnacle esports is live-only and no free
  historical esports odds source exists (all five probed today are dead). The
  1,648 retrievable CS2 events have a Kalshi price and a result but **no
  contemporaneous reference price**. This entry is **forward-test only**, and
  the recorder started 2026-08-04 21:27 UTC is the entire apparatus.

### #2 — Tennis ITF / WTA / ATP on Kalshi

| | |
|---|---|
| **A** | **100%** two-sided every cycle on all four families |
| **B** | 135k–177k within 5¢ (prior sweep) |
| **C** | 1.0¢ spread; **no maker fee on ITF/Challenger**, maker fee on ATP/WTA (S025: those two hold 34.4% of tennis volume on 5.8% of markets) |
| **D-ref** | **Pinnacle tennis free — 352 matchups, 3,728 priced markets, including period-1 handicaps** |
| **E** | **ITF men 8,000 events (16.6×)**, ITF women 7,636 (15.9×), WTA 974 (2.02×), ATP 942 (1.96×) |

**By far the largest retrievable sample on the exchange — 17,552 settled events
across the four families, 36× the K014 bar.**

**The honest case against, and it is close to decisive:**
- **T012 already tested this hypothesis and it failed.** Kalshi is
  indistinguishable from the Betfair close at r **0.9878**, MAD **1.95¢** against
  a 2.44¢ round-trip; where the two disagree by more than it costs to act,
  Kalshi is closer **49.1% [42.7, 55.6]** and all 14 segments cross zero.
- **S008/S009**: all 15 maker fill configurations net-negative, adverse selection
  exceeding price improvement at every window.
- **The historical reference is still missing.** T014 stands: tennis-data.co.uk
  stopped carrying Pinnacle in 2026 (coverage 5.1%), and **no free ITF source
  exists at all** — and ITF is where 15,636 of the 17,552 events are. So the
  large sample and the free reference price **do not overlap**: ATP/WTA has the
  reference and 1,916 events; ITF has 15,636 events and no reference.
- Settlement path is unmodelled: **these series settle on who ADVANCES**, so a
  walkover pays with zero play.

### #3 — MLB first-inning (`KXMLBRFI`)

| | |
|---|---|
| **A** | 100% two-sided every cycle |
| **B** | **301,578 at the touch, 2.28M within 5¢** — the deepest book on the list |
| **C** | 2.24¢ bar; `>tick` = **0.00**, the book sits at the minimum tick essentially always |
| **D-domain** | **the best anywhere** — Statcast verified today at 4,438 rows × 119 columns for one day; MLB StatsAPI 200 |
| **E** | **905 events, 1.88×** |
| **D-ref** | **none, and that is the entry's whole point** — the only MLB family with no matching entry in DraftKings' free prop list |

**Retained over the other MLB families for one reason**: it is the only one where
the counterparty has no free screen to copy. `KXMLBGAME` is already efficient
(0.37¢ vs de-vigged DraftKings, 0 of 26 over the bar) and `KXMLBF5TOTAL` has a
free reference.

**Case against:** the mechanism is *an assertion about how the counterparty
prices, with no evidence* — `market-selection`'s own words. A book pricing the
moneyline to 0.37¢ is unlikely to misprice its own first innings by 2 pp.
`>tick = 0.00` is simultaneously a maker kill and a taker cost floor. And
301,578 at the touch may be one maker who withdraws under adverse flow.

⚠ **A live regression that touches this entry:** `site.api.espn.com` returned
**403 on 7 of 7 leagues** today. `market-selection` used that feed on 08-02 to
find 3,699 priced DraftKings props, and that finding is what killed its original
#1 mechanism and established `KXMLBRFI`'s no-reference property. The `sports.core
.api.espn.com` v2 path still returns 200. **The no-reference claim rests on a
feed that no longer answers and needs re-establishing before it is quoted.**

### #4 — Polymarket weather

Included at low confidence, as a **cheap kill**, not a candidate.

- **A: 15% two-sided** across 40 tokens per cycle — nearly as dead as Kalshi
  weather (0% on 11 of 11 city families).
- A specific claim exists to test: a wallet reported taking NO at 70–95¢ on
  **London** weather, ~$24,729 over 2,930 trades in a year. It is selection-on-
  outcome by a third party who found the wallet **by its profit** (W015: below
  ~20 markets/wallet the entire spread in wallet performance is sampling noise),
  but it is **on-chain and therefore checkable**, which nothing else in this
  category is.
- **D-domain is perfect** (NWS 200) and, as `killed.md` proves, that does not
  matter when there is no counterparty.

---

## 3. Killed, with reasons

| family | killed on | reason |
|---|---|---|
| **South American / Mexican soccer** | **E** | 152 retrievable settled events vs a 481 bar. §1. The prior #1. |
| **Colombia `KXDIMAYORGAME`** | **D + E** | 21 events, and its free reference does not exist: `COL.csv` is byte-identical to `POL.csv` (sha `b9d1c59553b70628`) and its own League column reads **Ekstraklasa**. |
| Kalshi weather, all 11 city families | **A** | 0% two-sided on fresh markets. D at maximum and irrelevant. Recorded here as a live negative control: 42% / 67% against 100% elsewhere. |
| `KXMVESPORTSMULTIGAMEEXTENDED`, `KXMVECROSSCATEGORY` | **A** | 82.9% of Kalshi's market universe, >500k trades, **no public book at all**. Combinatorial parlays. |
| all crypto ladders | **D** + LEDGER C010 | four inputs, everyone has all four; no model beats the mid with a validated positive control. |
| golf | **D + E** | strokes-gained behind DataGolf (403, paid); 7 settlements/week. |
| MLB props (HR / KS / HIT / TB / HRR) | **B** | 50–644 contracts at the touch. `KXMLBHIT`'s median bid is 50 contracts — a $25 position at 50¢. |
| `KXMLBGAME`, `KXMLBF5TOTAL` | **D-ref** | already track a free reference to 0.37¢. |
| naive cross-venue Kalshi↔Polymarket | **C + mechanism** | 0 of 66 net-positive against a 6.75¢ two-venue floor here; independently, ~52% of pairs light up a naive screen and collapse to −0.9¢..+1.9¢ once resolution-equivalence is enforced. **The phantoms have HIGH token overlap, not low.** |
| economics / one-off politics | **E** | 22–48 settlements against 481. |

---

## 4. GATE CHECK

> *If nothing clears A, go back to Step 2.*

**A is cleared, on live measurement, by esports, tennis and MLB on Kalshi and by
esports on Polymarket.** Proceeding.

But the gate that actually binds is not A. It is the **conjunction**:

| entry | A | B | C | D-ref | E | **backtestable today?** |
|---|---|---|---|---|---|---|
| Esports | ✅ | ✅ | ✅ | ✅ | ✅ 3.4× | ❌ **no historical reference price** |
| Tennis ITF | ✅ | ✅ | ✅ | ❌ (ITF) | ✅ 16.6× | ❌ no reference for ITF |
| Tennis ATP/WTA | ✅ | ✅ | ⚠ maker fee | ✅ live only | ⚠ 2.0× | ⚠ Betfair only — **already done, T012 null** |
| MLB RFI | ✅ | ✅✅ | ✅ | n/a by design | ⚠ 1.9× | ✅ **yes** |
| S. American soccer | ✅ | ✅ | ✅ | ✅✅ 14 years | ❌ **0.3×** | ❌ n too small |

**No entry has all five *and* a runnable historical test.** The one with the
best evidence (esports) is forward-test only; the one with the best history
(soccer) has no sample; the one with the best sample (ITF) has no reference.

That is the honest Step 2 output, and it determines Step 5: **the only
pre-registered test that can be run to completion on retrievable data is a
structural one that needs no external reference price.** See
[PREREGISTRATION.md](PREREGISTRATION.md).

---

## 5. Recording, started before this file was written

`src/record.py`, PID launched **2026-08-04 21:27 UTC**, 10-minute cycles,
`data/record.db`. All three sources are live-only and none can be backfilled.

Covers 18 Kalshi series, 8 Polymarket tag slugs and 6 Pinnacle sports
(~326,000 priced Pinnacle records in the first 4 cycles). It deliberately
records a **superset** of what survives above, including two known-dead weather
families as a negative control on the instrument itself.
