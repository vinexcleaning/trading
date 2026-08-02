# SHORTLIST.md — markets worth a week of work

Measured 2026-08-02. Four families, ranked. Numbers are from the 24 h
exchange-wide trade tape, the continuous depth recorder (144 series), a
one-shot depth sweep over the top 300 families, and free-data probes that were
verified by fetching.

**Tennis is not on this list despite having the best market metrics on the
exchange.** That decision is explained at the bottom, because it is the most
consequential judgement in this file.

> **The prior you should read this against.** LEDGER.md records ~41 corrections
> across five studies and **every one shrank the edge**. This session added four
> more with the same sign, including one where my own measurement went from
> "6 of 8 game sides beat the cost bar" to "0 of 26" once the sample was fixed.
> Nothing below is a finding. They are the four places where a finding is still
> *possible*.

---

## Scoring key

| Dimension | What it is |
|---|---|
| **A — counterparty** | THE KILL SWITCH. trades/day, distinct markets/day, two-sided quote uptime |
| **B — depth** | contracts at the touch, contracts within 5¢ |
| **C — cost** | median spread + fee ⇒ the edge required, in percentage points |
| **D — free domain data** | how much exists about the underlying, verified by fetching |
| **E — recurrence** | settlements per week; bounds what can ever be validated |

---

## 1. MLB player props — KXMLBKS, KXMLBHIT, KXMLBTB, KXMLBHRR, KXMLBHR

**The only family where rich free data exists AND no free public reference
price does.**

| Dim | Measurement |
|---|---|
| **A** | 100% two-sided across the depth recorder; 72–78 recorded snapshots each; 744–1,985 distinct markets traded/day |
| **B** | **thin: 122–403 contracts at the touch**, 7,600–66,000 within 5¢ |
| **C** | **1.0¢ median spread → 2.25¢ cost bar at 50¢ ⇒ ~2.3 pp of edge required.** `fee_type = quadratic`, **no maker fee** |
| **D** | **highest of any family on either venue.** Baseball Savant returns **2,923 rows × 119 columns for a single day** of Statcast; MLB StatsAPI's live feed is **885 KB for one game** (pitch-by-pitch, lineups, umpires, weather); Retrosheet back to 1871. All free, no key, backfillable |
| **E** | 11–12 events/day × 100–200 markets each |

**Hypothesis (mechanism).** A strikeout prop resolves on the interaction between
one starter's current pitch mix and the specific handedness and whiff profiles
of the nine hitters he will face — an object Statcast fully describes at pitch
level and that appears in no published number, because **ESPN's free odds feed
carries moneyline, spread and total only, and no props at all**.

**Why the error would persist.** There are 100–200 prop markets per game night
and each holds only ~$100–400 at the touch. The cost of pitch-level
infrastructure is fixed; the revenue per market is capped by depth. A
professional's return on that infrastructure is therefore poor while an
account small enough to be filled by 300 contracts is unaffected. **This is a
capacity moat, not an information moat** — it persists exactly as long as the
markets stay small, and it disappears the moment they grow.

**Recording:** all five families are in the continuous depth recorder
(72–78 snapshots each so far).

**The honest case against.**
- **Depth is the whole problem.** 122 contracts at the touch on KXMLBHIT means a
  ~$60 position at 50¢. Across 150 markets that is real, but it is an
  operations problem disguised as a strategy.
- **No free reference means no cheap validation.** Everything must be validated
  against realised outcomes, which needs n, which needs months.
- Sportsbooks price these props with the same Statcast data. The claim is not
  that we would know something *nobody* knows — only something *this
  counterparty* does not, and that is a much weaker claim.
- Props are where books set the widest true margins; a 1¢ quoted spread may be
  masking a wide *fair* spread, i.e. the resting orders may be stale rather
  than competitive.

---

## 2. MLB game-level derivatives — KXMLBRFI, KXMLBF5TOTAL, KXMLBTOTAL, KXMLBSPREAD

**Deep, rich data, and the moneyline next door is already proven efficient — so
this is where to look if you believe MLB at all.**

| Dim | Measurement |
|---|---|
| **A** | 100% two-sided across the recorder; 75–99 snapshots each |
| **B** | **deep. KXMLBRFI: 263,746 contracts at the touch, 2.29 M within 5¢.** TOTAL 15,944 / 315,293. SPREAD 8,573 / 1,242,839 |
| **C** | 1.0¢ median spread → **2.25¢ bar ⇒ ~2.3 pp**. `quadratic`, **no maker fee** on RFI/TOTAL/SPREAD |
| **D** | same as #1 — the richest free data anywhere |
| **E** | 38 events/day |

**Hypothesis (mechanism).** Kalshi's MLB *moneyline* is already within **0.37¢
(median, n=26 sides)** of the devigged DraftKings line and **never** exceeds the
cost bar — measured this session. But first-inning and first-five-inning
outcomes depend almost entirely on two starting pitchers and the top of each
lineup, a far narrower object than a full game, and one Statcast describes
directly. The hypothesis is that these derivatives are priced as a rule-of-thumb
share of the game total rather than modelled independently.

**Why the error would persist.** Derivative markets are numerous and secondary;
attention concentrates on the headline line. RFI in particular has enough depth
(263,746 at the touch) that capacity is *not* the constraint, which is unusual
and makes it the most scalable thing on this list.

**Recording:** all four in the continuous recorder.

**The honest case against.**
- **The mechanism is an assertion about how the counterparty prices, with zero
  evidence behind it.** I did not measure whether RFI is priced off the total.
- DraftKings *does* publish first-5 lines, so a free reference may exist for
  part of this family — which would likely kill it the same way the moneyline
  comparison killed the moneyline.
- The moneyline result is a warning, not an encouragement: the same book that
  prices the moneyline to 0.37¢ probably does not price its own derivatives
  2 pp wrong.

---

## 3. Liga MX / Argentina / Brazil Serie A soccer — KXLIGAMXGAME, KXARGPREMDIVGAME, KXCOPADOBRASILGAME

**The cheapest to test, by a wide margin. This is a one-day question, not a
week's work.**

| Dim | Measurement |
|---|---|
| **A** | 100% two-sided on the recorder; 3-way ladders fully quoted on **93 of 93** sampled events |
| **B** | Liga MX 30,742 at touch / 267,219 within 5¢; Argentina 1,032 / 64,627; Brazil 420 / 28,674 |
| **C** | 1.0¢ median spread → **1.97–2.20¢ bar ⇒ ~2.0 pp**. `quadratic`, no maker fee |
| **D** | **free Pinnacle CLOSING odds, backfillable to 2012**: Liga MX 4,437 matches, MLS 5,800, Argentina 5,928, Brazil Serie A 5,275. Plus StatsBomb events, ClubElo daily ratings, ESPN live DraftKings moneylines |
| **E** | Liga MX ~2–11 events/week per league |

**Hypothesis (mechanism).** Kalshi's counterparty on South American football is
US retail. The sharp price for these leagues forms at Pinnacle, which does not
accept US retail and is not bridged to Kalshi by any arbitrageur. If Kalshi's
pre-match price deviates from the Pinnacle close by more than the ~2.0 pp cost
bar, systematically, the deviation is collectable.

**Why the error would persist.** No participant has an incentive to bridge a
book this size across a venue boundary that a US retail user cannot cross in
the other direction.

**Recording:** Liga MX, Argentina, Brazil, Colombia all in the recorder.
KXMLSGAME is **not** — it has no open events (MLS between matchdays) and must
be added when the schedule resumes.

**The honest case against — and it is strong.**
- **LEDGER T012/T013 tested this exact hypothesis on tennis and it failed.**
  Kalshi was indistinguishable from the Betfair close (r = 0.9878, MAD 1.95¢
  against a 2.44¢ cost) and, where the two disagreed by more than it cost to
  act, Kalshi was closer **49.1% [42.7, 55.6]** of the time — a coin flip
  measured precisely, with all 14 segments crossing zero.
- The 3-way ladders are **internally consistent**: median overround +3.00¢ and
  **0 of 93** baskets net-profitable either way. That is a well-arbitraged book.
- MLB moneyline, tested this session against a free book, came back at 0.37¢.
  Two sports, two "Kalshi tracks the sharp line" results.
- **So the expected outcome is a null.** It earns its place only because the
  data is free, backfillable to 2012, and the test is a day's work — a cheap
  way to close the question rather than a promising lead.

---

## 4. NPB / KBO baseball — KXNPBGAME, KXNPBTOTAL, KXKBOGAME

**A real market with no free window into what the sharp price is.**

| Dim | Measurement |
|---|---|
| **A** | fresh probe: NPB **100% two-sided**, 2,043 contracts at touch; KBO 100% two-sided on the recorder |
| **B** | NPB 434–2,043 at touch, 6,717 within 5¢; KBO 420 / 8,936–35,816 |
| **C** | NPB 1.0–3.0¢, KBO 1.0¢ → **2.2–2.6¢ bar ⇒ ~2.3 pp**. `quadratic`, no maker fee. NPBSPREAD is 9.0¢ and is killed |
| **D** | **medium and must be built.** NPB official (`npb.jp`) and KBO official both return 200 but are HTML requiring scraping; `armstjc/Nippon-Baseball-Data-Repository` is live and pushed **2026-07-28**. **No Statcast equivalent, no free odds** |
| **E** | 17–19 events/day |

**Hypothesis (mechanism).** Kalshi lists Japanese and Korean baseball for a US
audience whose counterparty is unlikely to be reading Japanese- or
Korean-language sources. Language and time-zone friction is the moat.

**Why the error would persist.** The friction is structural: the data is not in
English, is not in an API, and the games settle while the US is asleep.

**Recording:** NPBGAME, NPBTOTAL, KBOGAME all in the recorder.

**The honest case against.**
- **There is no free odds reference at all.** The `KOR` file on
  football-data.co.uk is **Norway's Eliteserien**, and `JPN` is J-League
  *soccer*, not NPB baseball. Validation is against realised outcomes only.
- Asian bookmakers cover NPB and KBO heavily and sharply. "Nobody is watching"
  is almost certainly false — there simply is no free window into what the
  watchers think, which is a different and much worse situation.
- The scraper has to be built before anything can be measured, so the first
  week produces infrastructure, not an answer.
- Two of my own probes read NPB as having no book at all before a fresh probe
  revived it. The measurements here are younger and thinner than for MLB.

---

## Considered and NOT shortlisted, despite excellent market metrics

| Family | Market quality | Why excluded |
|---|---|---|
| **Tennis — ITF, Challenger, ATP, WTA** | **the best on the exchange.** Largest sports counterparty, 100% two-sided, 1.0¢ spread, **no maker fee on ITF/Challenger**, settles continuously | **No mechanism, therefore no entry.** Sackmann's ATP/WTA archive is **deleted** — the account now has exactly one public repo. **No free ITF source exists at all**: ITF's own API returns 212 bytes, ATP's Challenger archive 403, Sofascore 403, ESPN covers main tour only. ITF is ~76% of the book. And the microstructural route is already measured and negative: **S008 tested 15 maker configurations on tennis and every one was net-negative**, with adverse selection exceeding price improvement. Best market, no data, and the non-data route already closed. |
| **Crypto — KXBTCD, KXBTC15M, the 15-minute ladders** | 1.19 M trades/day, 0.1–1.0¢ spreads, two-sided | **Four inputs — price, strike, time, volatility — and everyone has all four.** C010 measured the consequence on 250 events with a validated positive control. KXBTC15M additionally has 57 contracts at the touch and is structurally dead (`floor_strike` = prior settlement in 99.86%). |
| **Golf — KXPGATOUR et al.** | **highest 24 h dollar volume on the exchange (23.2 M)**, 0.6¢ spread, 24,247 at touch | Free golf data is **scores, not skill**. Strokes-gained is behind DataGolf (**403, paid**); every free scraper found is stale. |
| **Esports — LoL, Valorant, CS2** | tight, 1.0¢, two-sided; Polymarket shows **$15.1 M/24 h** on the same content | **The free data layer collapsed.** Oracle's Elixir returns `NoSuchBucket`. HLTV 403, vlr.gg 402. |
| **Polymarket, all families** | deeper books than Kalshi (38–233 levels vs a 20-level server cap), 0.1¢ tick | **Cost.** `0.10·min(p,1−p)` is **2.86× Kalshi at 50¢**. On MLB moneyline the two venues have the *same* 1.00¢ median spread, so Polymarket is strictly worse. Cross-venue: **0 of 66** trips net-positive against a 6.75¢ two-venue fee floor. |

---

## What would make each of these fail — written before any strategy work

Pre-registered here, so that a later null is a measurement and not a
disappointment.

**1. MLB player props fail if** — the median depth at the touch is below ~200
contracts once measured over a full week rather than one snapshot (making the
capacity moat also a capacity ceiling for us); **or** the quoted 1¢ spread turns
out to be stale rather than competitive, so that a resting order is filled only
when it is wrong (S009's adverse-selection result, transplanted); **or** a
Statcast-based estimate lands within ~1 pp of the market on a held-out month.

**2. MLB game-level derivatives fail if** — DraftKings or any free feed
publishes first-5 and first-inning lines and Kalshi tracks them to under 1¢, the
way the moneyline already does (**this is the single fastest way to kill this
entry and it should be checked first**); **or** RFI's 263,746-contract touch
turns out to be one market maker who withdraws under adverse flow.

**3. South American soccer fails if** — Kalshi's pre-match price correlates with
the Pinnacle close above ~0.98 with MAD below the ~2.0¢ cost bar, which is
exactly what T012 found for tennis; **or** the disagreements split near 50/50 on
who is closer, which is exactly what T013 found. **I expect this outcome.**

**4. NPB/KBO fails if** — the scraper takes more than two days to produce a
clean historical panel; **or** the resulting model, benchmarked against realised
outcomes, does not beat the Kalshi mid by more than the ~2.3 pp bar on a
held-out period; **or** NPB depth at the touch proves as volatile as the two
conflicting readings this session suggest.

**All four fail together if** the pattern already visible in two independent
measurements holds generally: **Kalshi is the sharp line.** T012 found it for
tennis, this session found it for MLB moneyline at 0.37¢. If that generalises to
derivatives and to secondary leagues, none of these four has an edge and the
correct conclusion is that Kalshi is efficiently priced wherever a counterparty
exists — which would itself be the most valuable finding available, and would
be worth writing down as such rather than treated as a failure.
