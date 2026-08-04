# PRIOR_ART.md — what has already been tried, by whom, with what evidence

**Step 1 output.** Written 2026-08-04. Sources: this repo's own `market-selection`,
`LEDGER.md` and `GUARDS.md`; the `signal-github` corpus (4,017 repos, 3.4 GB of
whole-repo source on disk); the two `youtube-signal` corpora (746 + 470 videos);
the `social-signal` corpus (39,629 Reddit posts, 12,846 comments, of which
**5,641 posts and 1,991 comments are prediction-market** rather than general
algo-trading).

**Nothing in this file is a finding of mine.** It is other people's work, plus a
small number of things I verified by fetching today, each marked `VERIFIED`.

---

## 0. THE THING THE BRIEF DID NOT KNOW ABOUT

The brief says *"every previous attempt derived everything from scratch"* and
sets out Steps 2 and 3 as if no market selection existed.

**A complete market-selection pass already exists in this repo, dated
2026-08-02**, in [`market-selection/`](../market-selection/). It is not
mentioned anywhere in `STATUS.md`'s thread tables. It ran:

| what it measured | scale |
|---|---|
| exchange-wide Kalshi trade tape | **8,867,978 trades, 2,205 series, a full 24 h** |
| continuous depth recorder | 8,827 snapshots, 153 series |
| one-shot depth sweep | top 300 families |
| free-data probes | verified by fetching |
| pre-registered kill gate | fixed in `DECISIONS.md` **while the tape was still downloading** |

Its outputs are [`SHORTLIST.md`](../market-selection/SHORTLIST.md) (4 families
ranked), [`killed.md`](../market-selection/killed.md) (6 kill classes with
reasons), [`data-availability.md`](../market-selection/data-availability.md) and
[`WHAT_IS_LEFT.md`](../market-selection/WHAT_IS_LEFT.md).

**Re-running Step 2 from scratch would have been the single most expensive
mistake available in this session.** Step 2 below therefore *extends* it and
re-verifies what has gone stale, and says so line by line.

Two things in it are worth carrying forward on their own:

- **It corrected 19 of its own 37 kills.** Its wide sweep picked tickers from a
  02:12 UTC dump and probed them 5.5 h later; the markets had settled, and *a
  settled book reads as no counterparty*. More than half its kills were wrong,
  including the busiest family on the exchange. **A false kill on dimension A is
  the most expensive error in this whole design**, and it has already happened
  once here. It happened to me again today — see §4.
- **Its two-sided uptime figures are a 06:38–08:30 UTC snapshot, not a
  24-hour average.** Its own heartbeat found exchange-wide two-sided uptime
  moving between **97.4% and 80.0%** with a trough near 11:00 UTC. Any single
  probe of dimension A is a measurement of an hour, not of a market.

---

## 1. Which prediction markets do people report trading PROFITABLY, with
##    verifiable evidence rather than a claim?

Across all four corpora, **exactly one** account survives the test of "public,
itemised, reconciled, and reporting its own losses". Everything else is a claim.

### 1a. THE ONE — Polymarket esports, cross-venue, passive-only

`r/algotrading` **`1u17e2v`**, 2026-06-09, public wallet, blog write-up, four
reconciled lines. *(Recorded here without the author's handle; the permalink is
in `reports/read_weather_arb.txt`.)*

| line | amount |
|---|---|
| Arbitrage | **+$8,293** |
| Directional (the unhedged residual) | **−$3,184** |
| Cancelled matches | −$134 |
| **Net realised** | **+$4,973** |

3,858 fills · ~$96k volume · 47.5% win rate (sub-50 by design — the hedge leg
sits on the less likely side and the profit is locked across the pair).

**The mechanism, and it is the important part.** No prediction at all. De-vig
sharp sportsbook odds → that is fair value → post *limit* orders on Polymarket
esports at a minimum 7% edge. Passive only, never crossing: *"in these wide
markets the ask sits way above fair value, so crossing the spread to buy would
wipe the edge out."*

**It needs no esports domain data whatsoever.** The fair value comes from
another market's price.

**And its author switched it off.** Win rate went **50.2 → 48.3 → 43.4** monthly
as competition arrived and Polymarket introduced fees; February +$2,506, March
+$390, then off. He names the causes: adverse selection on stale quotes
(*"faster market makers picking off my stale quotes"*), a sign-flip bug, and
*"a devig method (Shin's) that ran hot on favourites."*

> This is the cleanest statement of the whole programme's recurring shape yet
> found: **a real, measured, positive gross edge, killed by execution and
> decay** — and reported by the person who lost the money.

### 1b. Claims that do NOT survive

| claim | where | why it is not evidence |
|---|---|---|
| "Nearly 3,000 weather trades later, this strategy continues to perform" — a wallet taking NO at 70–95¢ on **London** weather, ~$24,729 over 2,930 trades in a year | r/Polymarket `1vbtle2` | A **third party reviewing a wallet they found by its profit.** Textbook selection-on-outcome (W015: below ~20 markets/wallet the *entire* spread in wallet performance is sampling noise). No cost accounting, no interval, no denominator of wallets examined. ~$8.44/trade. It is a **lead**, not a result — and it is checkable on-chain, which is why it is in the shortlist rather than the bin. |
| "Is there actually an information edge left on Polymarket" → weather + wallet tracking | r/PredictionMarkets `1sl138t` | The post carries a **referral link** to a paid tool and the top comment says so. Promotional. |
| "$1.3M / $550k / $373k betting sports on Polymarket" | many r/sportsbook, r/Polymarket posts | Leaderboard screenshots. `1uo6uhz` measured what these are: a large share of 95%+ win-rate records are **farmed by only ever buying 95–99¢**, which is unfollowable — *"you can't get filled at 99c at size, and you're risking 99 to make 1."* |
| "$50 → $500 → $0 over 814 trades, −$115 of it fees" | youtube-signal | A real itemised account, and it is **negative**. Counted as evidence, of the other sign. |

### 1c. The strongest NEGATIVE result found anywhere

`r/PredictionMarkets` **`1ubletl`**, 2026-06-21 — ten months of resolved
Polymarket history (Sept 2025 → July 2026), **ten independent strategies, all
failed**, methodology and code published.

The bar the author used is the same one this repo uses: a bootstrap CI excluding
zero **and** beating the ~2% round-trip.

| strategy | result |
|---|---|
| favourite–longshot bias | longshots ≤0.20 implied 0.73%, **actual 1.15%** — if anything *under*priced, the opposite of the racetrack. PnL interval −1.5% to +0.4% |
| calibration | 0.90–1.00 bucket: mean price 0.982, actual 0.9765. *"When the crowd says 98 it means 98."* |
| momentum | 84% hit rate → **0.541** once measured on *early* rather than near-resolution prices. A pure convergence artifact |
| 8-agent LLM forecasting swarm | Brier **0.38** vs the market's **0.30**. Also failed to run 29% of the time |
| smart-money copy trading | early-vs-late return correlation **0.035** across 157 wallets; the **top 15 lost 13.6%** out of sample (−$47,590 on $349,158, CI −0.47 to −0.01, entirely below zero) |
| negRisk Dutch book | 1–7% overround **collapsed to ~1¢** once walked against real depth |
| UMA settlement lag | real discount of 0.3–1.7%, **smaller than the ~2% cost**. "A parking fee, priced correctly" |
| crypto round-number bias, illiquid markets, re-slices | all straddle zero |

Two structural facts from it worth keeping:

- **The base rate is ~17% YES** across 648 liquid (≥$10k volume) markets, CI
  13.9–19.8%. Polymarket questions are shaped *"will this dramatic thing happen
  by this date"* and dramatic things mostly don't. Reframes every "this looks
  cheap" instinct.
- **Granularity killed an edge twice and created one never.** The negRisk edge
  vanished only on real depth; the momentum edge vanished only on early prices.

### ⚠ 1d. It directly CONTRADICTS this repo's W001, and the disagreement matters

| | `wallet-copy-study` **W001/W002** | r/PredictionMarkets `1ubletl` |
|---|---|---|
| wallet-skill persistence | Spearman **ρ 0.157–0.433, positive in all 36 cells** | early-vs-late return **ρ 0.035** |
| top-decile forward excess | **+2.567pp [2.19, 2.96]** | top 15 **−13.6% [−47%, −1%]** |
| n | 1,028–1,778 wallets | 157 wallets |
| selection rule | activity-based, 3 split points | activity-based, one split |

**I trust W001's number over this one** — 7–11× the wallets, three independent
split points, and a null-strategy canary that scores 0.0pp. But the *practical*
verdicts agree completely, which is the part that should govern: W003/W004 say
the copyable fraction (+0.937pp) is **smaller than the spread** (≥1.0pp) and
W005 says it decays to −0.135pp. Both studies say **do not build the copy bot.**

Recorded as a disagreement rather than resolved, per CLAUDE.md §5.

---

## 2. Which markets are widely reported DEAD, and why?

### 2a. Measured in this repo, on the full tape (`market-selection/killed.md`)

| kill | families | mechanism |
|---|---|---|
| **No book at all** | `KXMVESPORTSMULTIGAMEEXTENDED`, `KXMVECROSSCATEGORY` | **82.9% of Kalshi's entire 419,828-market universe** and >500k trades in 24 h, with **zero** public book. Combinatorial parlays minted on demand — real trades, no resting limit order book. **A high trade count is not a counterparty.** |
| **One-sided** | 11 of 11 weather city families + `KXFOXNEWSMENTION`, `KXTRUMPSAY`, `KXTRUTHSOCIAL`, `KXAFLGAME`, 2 NEXTTEAM ladders | 0% two-sided on 4 fresh markets each. The NWS API is free, complete and *is the settlement product* — dimension D at maximum — and it does not matter. Reproduces LEDGER **C016**. `KXHIGHDEN`/`KXHIGHTPHX` are the named exceptions. |
| **Cost implausible** | `KXLIGAEXPTOTAL` (57¢ spread, ~30 pp needed), `KXLIGAEXPGAME`, `KXUSLTOTAL` | For scale, the largest genuine effect in the whole archive is 2.42 pp. |
| **Everyone has the same inputs** | all crypto ladders | price, strike, time, vol — all four free from Binance/Coinbase/Kraken/Deribit. LEDGER **C010** + positive control **C008**. |
| **Free data layer collapsed** | esports, golf | see §3c — and **this kill is the one I reopen**. |
| **Too rare to validate** | economics, one-off politics | **481 settlements** needed for a 5 pp edge (K014). `KXCPI`/`KXFED`/`KXGDP` have 22–48. |

### 2b. Reported dead by other people

- **News/headline arbitrage on Polymarket: gone.** Consistent across dozens of
  posts. *"By the time I read a headline, formed an opinion, and placed a trade,
  the price had already moved."*
- **Copy trading: gone, and for a stated reason.** *"Copying the people who set
  the price means paying the price they set."* Cited: Gómez-Cram et al.
  (Apr 2026), **~3% of Polymarket accounts drive essentially all price
  discovery** — so by the time their trade is on-chain the price already reflects
  it. Independently, an LBS study of 1.72M accounts (via youtube-signal) reaches
  the same 3%.
- **Cross-venue Kalshi↔Polymarket: mostly phantom.** Two independent accounts in
  one thread. A live snapshot of **~130 contracts quoting two-sided on both
  venues** lit up **~52% of pairs** on a naive net-of-fees screen; after
  filtering to genuine resolution-equivalence the gap **collapses to −0.9¢ to
  +1.9¢** and the cleanest identical pairs are negative. A second bot ran **233
  screens, zero fills.**
  > The phantoms have **HIGH** token overlap, not low: *"who will **run** for the
  > nomination"* vs *"will X **win** the nomination"* share almost every word.
  > **Token overlap is a recall net, not a precision filter**; the kill is the
  > resolution triplet — verb, deadline, source.
  This corroborates `market-selection`'s own **0 of 66 MLB cross-venue trips
  net-positive** against a 6.75¢ two-venue fee floor.

### 2c. A settlement-risk class this repo has no model for

From a poster tracking 750+ Kalshi settlements: **Kalshi tennis series settle on
who ADVANCES** — a walkover pays out with zero play. `kalshi-inplay-bot` and
`set1_overshoot` trade `KXATPMATCH`/`KXWTAMATCH` and model no such path. Same
source: *"'closed' is not 'settled'* — count only `finalized`."

Corroborating, r/Kalshi: *"Kalshi settled Denmark vs Ukraine as 'Denmark win' —
match was officially abandoned."* **Resolution-source risk is a real cost term
that appears in no fee model anywhere in this repo.**

---

## 3. What has been publicly TESTED and FAILED?

Beyond §1c's ten, from the corpora:

| tested | result | source |
|---|---|---|
| Polymarket 5-minute crypto, 346,094 windows | every price band loses −1.6 to −6.5pp against price+fee; momentum inverts monotonically; the Chainlink–Binance lag is **−0.4pp on 5,826 entries** and its profitable version was **a measurement artifact** | social-signal, 4,604-window study |
| "96.83% win rate" on Polymarket 5-min BTC, 12,272 periods | arithmetically real, **uncapturable**: 95% of profits go to bots, 60-second window, and the **Chainlink oracle lags Binance** so bots front-run the print | youtube-signal `8u6jy8v56ww` |
| A 400k-view YouTube strategy, rebuilt over 16 years / 1,700 trades | **−23%** against the video's +40% on 100 trades. *"The exact 100 trades shown in the video do appear… a short lucky stretch inside a much longer downtrend."* Reversing every signal raised the win rate to 61% and left expectancy at −0.01, *"because when you reverse a strategy, you aren't reversing the costs."* | social-signal |
| Retail RSI backtest, walk-forward over 19 folds | **199% → 5%** out of sample; the engine attributes **75% of the return to curve fitting**. Adding ATR / volatility-scaled momentum / Butterworth filters: **1,500% → 7%** | youtube-signal `lIMu8ysJW68` |
| Maker-only quoting on Kalshi tennis, 15 fill configurations | **all 15 net-negative**; adverse selection exceeds price improvement at every window | this repo, **S008/S009** |
| Kalshi 15-minute market making, by someone who built the whole apparatus | *"almost every edge that looked real in-sample decayed out-of-sample within a few weeks as the market makers on the other side sharpened up"* | signal-github, `artyomderkach-bit` |

### ⚠ 3a. The tension the extractors surfaced and neither side can dismiss

- `signal-github` concluded **maker-only quoting** is "the one strategy whose
  income is not required to overcome a fee first" — reasoning from **fee
  schedules**.
- youtube-signal `rrKRhjye1sw`, a 20-year professional: *"If you're new, be a
  market TAKER, not a market maker."* Your resting offer is taken **only** when
  it is good for the other side. You are filled only in the states where you
  were wrong.

**Both are right. Maker economics win on fees and lose on adverse selection, and
adverse selection appears in no fee model.** The esports arb author in §1a
measured this term directly and it cost him **$3,184 of an $8,293 gross** — 38%.
That is the first *number* anyone in these corpora has put on it, and it is the
single most useful quantity in this file.

### 3b. The Kalshi liquidity-provider question, now resolved as CONTESTED

`STATUS.md` records this as *"deliberately left unverified"* because
`papers.ssrn.com` is behind a Cloudflare interstitial. **The originating post is
in the local corpus** (`r/quant` `1rodanx`, score 137, 46 comments stored) and
does not need SSRN.

Claim: over Kalshi's full 2025 NFL moneyline season, passive LPs *"aren't
neutralizing inventory and capturing spread. They're accumulating directional
outcome exposure that persists through settlement"* — a sportsbook/insurer
return profile, not a market-making one.

The best rebuttal (score 7) is serious and should travel with the claim:

1. residual inventory through resolution is normal in episodic markets;
2. *"profitability correlates with managing flow imbalance" **is** the market
   making thesis*;
3. trade data alone cannot see off-platform hedging — *"you're measuring gross
   not net"*;
4. sportsbooks set the line, CLOB LPs are price-takers.

The author's answer to (3) is the load-bearing one and it is structural:
**there are no correlated NFL futures venues, so the gross/net distinction
collapses when no hedging instrument exists.**

**Status: CONTESTED, not settled.** But whichever way it resolves, it says the
same thing about design: on a binary event contract **there is no hedge**, so a
maker's P&L is terminal outcome exposure, not spread capture.

---

## 4. Which tools and data do people with real results actually use?

### 4a. VERIFIED TODAY BY FETCHING — the finding of this step

**Pinnacle's guest API serves live, priced markets free and unauthenticated.**
`guest.api.arcadia.pinnacle.com/0.1/...`, browser UA + the public web client's
`X-API-Key`. Measured 2026-08-04 21:2x UTC:

| sport | id | matchups | **priced straight markets** | bytes |
|---|---|---|---|---|
| Soccer | 29 | 4,456 | **27,582** | 14.8 MB |
| Tennis | 33 | 352 | **3,728** | 2.0 MB |
| Baseball | 3 | 867 | **1,920** | 1.1 MB |
| American football | 15 | 377 | **1,509** | 0.8 MB |
| **E Sports** | **12** | **81** | **643** | 0.3 MB |
| Basketball | 4 | 89 | 637 | 0.3 MB |
| Golf | 17 | 87 | 87 | 0.05 MB |
| MMA | 22 | 22 | 33 | — |

Every record carries American prices, `period`, `points`, `cutoffAt`, `status`
and **`limits: maxRiskStake`** — the sharp book's own capacity signal. Period 1
handicaps are present (`s;1;s;-1.5`), i.e. **set-level and half-level lines**,
not just moneylines.

Why this matters more than anything else probed today:

- It is **the fair-value input** for the only mechanism in §1a with a
  reconciled live P&L, and for youtube-signal's three-number check
  (`edge = fair probability − price − cost`, fair probability = *de-vigged sharp
  consensus*, not your own model).
- `kalshi-tennis` **T014** recorded that tennis-data.co.uk *"stopped carrying
  Pinnacle in 2026"* and coverage collapsed to 5.1%, forcing the Betfair close
  as benchmark. **That is true of the historical CSV and remains true.** Live
  Pinnacle is a different object and is available. T014 is not retracted; a
  route it was thought to close is open going forward.
- **It cannot be backfilled.** No historical endpoint exists at any price. Per
  the brief, recording started the day it was identified — **2026-08-04
  21:27 UTC**, `src/record.py`, and it is running.

### 4b. VERIFIED TODAY — what is dead, and one live regression

| source | status today | note |
|---|---|---|
| `site.api.espn.com` scoreboard | **403 on 7 of 7 leagues** | ⚠ **REGRESSION.** `market-selection` used ESPN's free feed on 08-02 to find 3,699 priced DraftKings props, and that finding **killed its own #1 mechanism**. The endpoint now 403s. The `sports.core.api.espn.com` v2 path still returns 200. **Anything resting on the ESPN prop feed needs re-verifying before it is quoted.** |
| Oracle's Elixir (LoL) | **404** | S3 bucket still gone |
| HLTV (CS2) | 403 | Cloudflare |
| vlr.gg API | **402 Payment Required** | |
| PandaScore | 403 | key required |
| GRID.gg | 404 | |
| the-odds-api | **401** | free tier needs a key → `PAID_OPTIONS.md` |
| Liquipedia LoL | **200, 475 KB** | alive |
| bo3.gg | 200, 9,950 chars of text | alive |
| Leaguepedia cargoquery | 200 but **372 bytes** on a 20-row query | reproduces the prior session's reading |
| MLB StatsAPI | 200 | |
| Statcast (one day) | **200, 4,438 rows × 119 cols** | |
| NWS points | 200 | |
| ClubElo | 200, 593 rows | |
| football-data.co.uk MEX/ARG/BRA/USA/JPN | 200, League column correct | |
| `archive.pmxt.dev` | 200, real archive index | `r2v2.pmxt.dev/` root 404s |

### ⚠ 4c. THE FOOTBALL-DATA TRAP, REPRODUCED EXACTLY

The brief warns it. It is real, and both halves are confirmed two independent
ways — sha256 of the body **and** the file's own League column:

| requested | sha256 (16) | League column says |
|---|---|---|
| `COL.csv` | `b9d1c59553b70628` | **Ekstraklasa** (Poland) |
| `POL.csv` | `b9d1c59553b70628` | Ekstraklasa |
| `KOR.csv` | `aa649e866b03d2ea` | **Eliteserien** (Norway) |
| `NOR.csv` | `aa649e866b03d2ea` | Eliteserien |

**Byte-identical, HTTP 200, no error of any kind.** `src/probe_sources.py`
hashes every download and reads the League column on every tabular file, and
prints byte-identical pairs as a named failure. This is now a reusable guard —
it belongs in `GUARDS.md`.

Consequence carried forward: **`KXDIMAYORGAME` (Colombia) has no free reference
line.** It is in `market-selection`'s #1 entry and is not testable the cheap way.

### 4d. ⚠ MY OWN FALSE KILL, RECORDED BECAUSE IT NEARLY COST THE BEST LEAD

Recorder cycle 1 queried Polymarket with `tag_slug=esports` and read **11 quoted
tokens of 95, 0% two-sided.** On dimension A that kills the family — and it would
have killed the one mechanism in §1a with a reconciled live P&L.

**It was the probe.** `esports` and `league-of-legends` ordered by `volume24hr`
return mostly `acceptingOrders=false` events (**96 of 156**) — settled
blockbusters ahead of live thin markets. Queried by the *specific game* slug at
the same minute:

| slug | two-sided / probed | best market |
|---|---|---|
| `dota-2` | **51 / 60** | $51,029/24h, **1.0¢ spread**, 2,458 × 4,068 at the touch |
| `valorant` | **54 / 60** | $8,807, 1.0¢, 18,060 × 41,270 at the touch |
| `cs2` | **23 / 27** | $3,173, 4.3¢ |

The same bug also made Polymarket **tennis** read 18% two-sided, when a
correctly-slugged probe finds *National Bank Open: Shang vs Rublev* at
**$467,617/24 h with a 1.0¢ spread and 25,348 × 5,667 at the touch.**

Fixed in `record.py` (`active=true`, per-game slugs) and the recorder restarted.
**Same shape as `market-selection`'s stale-ticker bug, which produced 19 wrong
kills, and as `killed.md`'s own opening correction.** Three occurrences now:
**a dimension-A probe that samples the wrong markets fails silently and always
in the direction of a kill.**

---

## 5. What remains GENUINELY untested

Everything below is untested *after* accounting for all of the above.

1. **A sharp-reference-price strategy on a family where the reference is free
   and the prediction market is NOT already tracking it.** §1a proves the design
   worked once, on Polymarket esports, and decayed. It has never been tested
   against Kalshi's South American soccer, where `market-selection` measured
   100% two-sided uptime, ~2.0¢ cost bars and 40–101 settlements/week, and where
   Pinnacle now provably quotes live.
   > The honest prior is bad: the same hypothesis failed on tennis (**T012**,
   > Kalshi ≡ Betfair at r 0.9878) and on MLB moneyline (0.37¢, 0 of 26 over the
   > bar). It is on the list because it is **cheap to close**, not because it is
   > likely to pay.
2. **Adverse selection as a measured term rather than an assumption.** §1a puts
   it at 38% of gross. Nothing in this repo has ever measured it prospectively;
   S009 measured it retrospectively on tennis and found it exceeded price
   improvement, without sizing it.
3. **Whether Kalshi's own two-sided uptime is diurnal enough to change a
   ranking.** `market-selection` flagged this against itself and never ran the
   24-hour profile. The recorder now started will produce it.
4. **Polymarket weather.** All 11 Kalshi weather families are one-sided. Nobody
   has measured whether *Polymarket* weather is, and there is a specific
   (weak, selection-biased) claim about a London weather wallet to check against.
   First reading: **15% two-sided**, but see §4d before trusting any single
   probe.
5. **`KXMLBRFI`** — the only MLB family with no matching entry in DraftKings'
   free prop list, 301,578 contracts at the touch. Its mechanism is *an
   assertion about how the counterparty prices, with no evidence*, in
   `market-selection`'s own words.

## 6. What is CLOSED and must not be re-run

Crypto forecasting · crypto market making · exchange-wide market making · tennis
set-1 · wallet copy trading · ladder arbitrage · the BTC 15-minute family ·
Kalshi weather (one-sided, dimension A) · the combinatorial parlay families (no
book at all) · naive cross-venue screens without a resolution-equivalence gate.

---

## 7. Reading found what scoring could not, again

Five threads read in full produced: the only reconciled live P&L in any corpus
(§1a), the 38% adverse-selection number, the ten-strategy null (§1c), the
resolution of the SSRN LP question without SSRN (§3b), and the
resolution-equivalence trap that explains two other people's zero-fill results
(§2b). **None of it is visible to any scorer** — `1ubletl` scores **6** on
Reddit and `1uo6uhz` scores **0**.
