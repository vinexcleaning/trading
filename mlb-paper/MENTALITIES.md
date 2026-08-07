# The five MLB mentalities, and where each one came from

**Derived, not copied.** None of these is a tennis mentality with the nouns
changed. Baseball has a different information clock, a different price driver
and a different market structure, and each of the five below exists because of
something specific that was measured or read this session.

Sources used, in order of how much work each did:

| source | what it contributed |
|---|---|
| **live measurement** (`reports/market_census.json`, `reports/target_choice_multiplicative.json`) | the cost bars, the depth, the vig, and the 0-of-58 de-vig result that sets the bar all five must clear |
| **social-signal** (`social.db`: 39,629 posts, 12,846 comments) | what people who actually trade baseball say they watch — 287 posts carry ≥4 baseball terms; the useful material is in the comments, not the titles |
| **signal-github** (`github.db`: 3,165 scored repos) | 8 baseball repos, one of them a live production Kalshi MLB bot whose headline design decision is stated in its own README |
| **`mlb/PROGRESS.md`** (this repo, 2026-08-02) | the data availability audit — what is free, what is a day ahead, what is live-only |
| **youtube-signal** (`signal.db`, `signal_kalshi_edge.db`) | the de-vig procedure and the cost arithmetic; **nothing baseball-specific**, and that absence is reported rather than papered over |
| **`SCOREBOARD.md`** | the 909 games and 148 price-pattern strategies that are already dead, so none of these rebuilds one |

## What the cross-check against SCOREBOARD ruled out before anything was built

**148 price-pattern strategies on 909 MLB games: 0 came out positive.** Random
side −5.75¢. Every one of them was price-versus-price.

> **So no mentality below is allowed to look at the price pattern.** Not price
> bands, not drift, not staleness, not volume, not the shape of the move. Each
> one is a statement about *baseball*, and the price enters only at the end, as
> the thing being compared against. That is the single biggest structural
> difference from everything this repo has tested on MLB.

Also ruled out by measurement rather than by taste (see `TARGET_CHOICE.md`):
first-inning (`KXMLBRFI`) on a 6.5¢ cost bar and 2 contracts at the touch, and
any strategy that needs Kalshi to disagree with Pinnacle at a moment when both
books exist — because **0 of 58 markets across 10 games disagree by more than
cost, and the hindsight-picked best is still −1.63¢.**

## The two claims in the corpus that flatly contradict each other

Recorded rather than resolved, because both are unsupported assertions by
anonymous commenters and the test is what settles it.

- *"MLB is the toughest sport for any model because the regular season variance
  is brutal… whales might have edge on the prop side but ML is hard to beat in
  baseball because the books are too sharp on it."* — r/PredictionMarkets
- *"Baseball is the most model-friendly sport… large sample of games daily, less
  variance per game than basketball, and the lines are softer because fewer
  whales care about baseball."* — r/Polymarket

**The measurement sides with the first.** Pinnacle's MLB moneyline overround is
2.55 pp with a $2,500 limit and Kalshi tracks it to within a cent. "Softer lines"
is not what a 2.55 pp book looks like. The second claim is kept on the page
because it is the belief that would make this whole test worth running, and it
should be visibly wrong if it is wrong.

---

# M1 — THE STARTER IS THE GAME, SO ONLY *NEW* STARTER NEWS CAN PAY

**One line.** A baseball line is built on the two listed starting pitchers, so
the only pitcher information worth anything is what the market has not yet
absorbed: a scratch, a debut, short rest, or a starter whose last three outings
look nothing like the season line the price is anchored on.

**Rationale.** Everyone knows the starter's ERA — it is the most public number
in the sport, and `SCOREBOARD.md` already records that on the tennis side
"rankings are the most public information in tennis, so the price already knows".
The asymmetry is not in the number, it is in the **freshness** of the number.
A pitcher's season ERA is a 25-start average; his last three starts are a
3-start average; when those two disagree sharply the market is pricing the
slower one.

**Evidence.**
- `SCOREBOARD.md` p5: *"Starting pitcher — **NEVER TESTED** — and it is the
  single biggest driver of a baseball line."*
- **Pinnacle prices this structurally.** Its market key is `s;0;m` on a matchup
  whose participants carry a `pitcher` field, and the book voids on a change of
  listed pitcher. A market that voids on an event is a market telling you that
  event is the dominant variable.
- Corpus, r/PredictionMarkets: *"starting pitcher injuries day-of, bullpen usage
  decisions, weather"* named as the three things a model must handle.
- `mlb/PROGRESS.md`, verified by pulling: probable pitchers are on
  `statsapi.mlb.com` **a day ahead** (7 of 8 games), and `/people/{id}/stats?
  stats=gameLog&group=pitching` returns every start with innings, earned runs,
  strikeouts and **pitch count** — re-verified working this session, 25 splits
  returned for a live probable.

**Target.** `KXMLBGAME` (moneyline).
**What kills it.** If the scratch / debut / short-rest / recent-form-divergence
flags add nothing on top of the de-vigged Pinnacle price, it is dead — and
Pinnacle sees all four of them too, which is why the honest prior is low.

---

# M2 — WHO WINS IS A COIN FLIP; HOW MANY RUNS IS A PHYSICS PROBLEM

**One line.** Trade the total, never the winner, and only when the ballpark and
the air agree with each other: elevation, temperature, and wind direction
*relative to the outfield*.

**Rationale.** A baseball is a projectile. Air density falls with temperature
and altitude, and a ball carries measurably further in thin warm air; a 10-knot
wind off the plate is worth more than most lineup changes. This is the one
input in the whole brief that is a **forecast** rather than a fact, which means
it updates on the weather service's clock rather than the betting market's.

**Evidence.**
- `SCOREBOARD.md` p5: *"Ballpark, weather, wind — **NEVER TESTED**."*
- **Measured this session, and it is the strongest quantitative argument for
  totals:** Pinnacle's overround on MLB totals is **4.01 pp against 2.55 pp on
  the moneyline**, and its maximum stake is **$1,875 against $2,500**, on the
  same games at the same instant. A sharp book charges more and risks less
  where it is less certain.
- **Measured this session:** `KXMLBTOTAL` carries a median **1,029 contracts at
  the touch** against **68.5** on the moneyline — 15×, at the same 2.0¢ spread
  and the same 3.0¢ cost to enter.
- **The data exists, free and permitted.** `statsapi.mlb.com` publishes each
  venue's `defaultCoordinates`, `elevation` **and `azimuthAngle`** — the park's
  compass orientation, which is what turns "wind 250° at 3 kt" into "blowing in
  from right field". Verified live: PNC Park, azimuth 116.0, elevation 780 ft.
- **The weather source survived the robots gate and the two obvious ones did
  not.** `api.open-meteo.com` and `api.weather.gov` are both `User-agent: * /
  Disallow: /` and are refused. NOAA's **Aviation Weather Center**
  (`aviationweather.gov`) publishes no robots.txt at all and serves **TAF**, a
  24–30 h forecast of wind direction, wind speed, gusts and precipitation, free
  and unauthenticated, for every major airport. Verified live against KPIT.

**Target.** `KXMLBTOTAL`.
**What kills it.** Pinnacle also reads the weather. If the park-and-air view
never disagrees with the de-vigged total by more than 3.0¢, there is nothing
here — and the 0-of-38 result in `TARGET_CHOICE.md` §4 says that is exactly what
happens at a *randomly chosen* moment. The bet is that it is not true at every
moment.

---

# M3 — THE BULLPEN IS THE THIRD OF THE GAME NOBODY REPRICES

**One line.** A starter throws five or six innings; the rest is thrown by
relievers whose availability was decided **yesterday**, and yesterday is public,
boring and slow.

**Rationale.** This is the clearest candidate for information that is *fully
public and still under-weighted*, because it is expensive to compute and
uninteresting to look at. An extra-inning game, a doubleheader, or three
consecutive one-run games empties a bullpen. Nobody's headline number changes.
The market's anchor — the listed starter — is unaffected.

**Evidence.**
- `SCOREBOARD.md` p5: *"Lineups, rest, bullpen usage — **NEVER TESTED**."*
- Corpus, r/PredictionMarkets, in a thread about a 415-pick whale-copying
  record: *"starting pitcher injuries day-of, **bullpen usage decisions**,
  weather"* — named as a driver the poster believes whales have an edge on.
- **Exactly computable, free.** `statsapi.mlb.com/api/v1/game/{pk}/boxscore`
  returns each team's `bullpen` roster and every pitcher's appearance with pitch
  count, so days-since-last-appearance and rolling three-day pitch load are
  arithmetic on data that is already published. No estimate, no scrape.
- The mechanism has a documented cousin in this repo: the crypto and tennis
  threads both died on *"a real effect smaller than the cost of reaching it"* —
  bullpen fatigue is the one candidate here whose effect size in the baseball
  literature is measured in tenths of a run per game, which is a **large**
  quantity relative to a half-run total line. That is the reason to test it and
  also the reason to expect the market already knows.

**Target.** `KXMLBTOTAL`.
**What kills it.** If the fatigue score is uncorrelated with the residual
between Kalshi's total and the de-vigged Pinnacle total, it is dead.

---

# M4 — BE EARLY OR BE NOTHING

**One line.** Kalshi lists a game up to four days out; the sharp book does not
appear until about a day out. If Kalshi is ever wrong it is wrong **before
Pinnacle shows up**, and that is the only window this repo has never looked at.

**Rationale.** This is the mentality that directly attacks the result in
`TARGET_CHOICE.md` §4. That measurement — 0 of 58 markets disagree with the
sharp line by more than cost — was taken at a moment when **both books existed**.
It is a statement about the overlap, not about the whole life of the market.
Before the overlap, Kalshi's price is anchored by nothing except its own order
flow.

**Evidence.**
- **Measured this session, and it is the entire basis of the mentality:**
  `KXMLBGAME` lists **49 events across 4 distinct game dates**. Pinnacle's MLB
  book lists **13 games across roughly one day**. There is a two-to-three-day
  window in which Kalshi quotes a game and no sharp reference is published at
  all.
- Corpus, r/Kalshi: *"sports markets move fast on news… so the price you see at
  noon isn't necessarily the price 2 hours before tipoff."*
- Corpus, r/algotrading, on a market-making bot: *"informed traders show up on
  wide spreads too sometimes, right before a lineup news drop or injury report,
  **when the book hasn't repriced yet and retail hasn't either**."*
- **The measurement instrument this needs already exists here.** Corpus,
  r/Kalshi, on a 180-signal model: *"CLV is exactly the right metric — short-term
  ROI is too noisy at 180 signals."* An early entry can be scored against the
  de-vigged sharp line **the moment it appears**, which arrives days before
  settlement and has far more statistical power per game than a win/loss.

**Target.** `KXMLBGAME`, scored on **both** settlement and closing-line value.
**What kills it.** Two things, either alone: the early quote is wide enough that
the cost of entering exceeds whatever CLV is earned; or the early Kalshi price
is already an unbiased estimate of the eventual sharp line, in which case CLV is
zero by construction.

---

# M5 — THE LINEUP CARD IS THE LAST FREE INFORMATION OF THE DAY

**One line.** Lineups post two to four hours before first pitch, cannot be
backfilled, and are the last scheduled, timestamped repricing event of the day —
so the question is not *what does the lineup say* but **how fast does Kalshi
move when it drops.**

**Rationale.** M4 is the early end of the information clock; this is the late
end. A star resting, a catcher's day off, or a full platoon lineup against a
same-handed starter is a genuine change in run expectancy arriving at a known
moment, after most of the day's volume has already traded. Pinnacle sees it too
— so this is deliberately a **latency** hypothesis, not an information one, and
it is the more honest form of the claim.

**Evidence.**
- `mlb/PROGRESS.md`, measured by pulling: *"Lineups: **0 of 8 games for tomorrow
  → LIVE-ONLY**, post ~2–4 h before first pitch."* This is the only input in the
  brief that is genuinely unbackfillable, which is why it has never been tested
  and why it needs a recorder running from day one.
- `SCOREBOARD.md` p5: *"Lineups… **NEVER TESTED**."*
- Corpus, r/PredictionMarkets, on venue choice: *"the lineup-news quote is the
  real tell. A market can show 2¢ spreads at rest and **gap to 8¢ the second
  team news drops** if nobody's quoting size into it."* — the same commenter
  says that gap, not the headline fee, is the number to watch.
- **Free and exact:** `statsapi.mlb.com/.../boxscore` returns `battingOrder` as
  nine player ids the moment the card is posted, and each player's season line
  is on the same API, so "who is missing and how good are they" is arithmetic.

**Target.** `KXMLBGAME`.
**What kills it.** If Kalshi's price has already moved by the time the lineup is
observable from a 60-second poll, there is no latency to trade, and the honest
answer is that the market is faster than the API. That is a real and likely
outcome and it will be reported as a finding rather than as a failure.

---

## What is deliberately NOT here

| not built | why |
|---|---|
| anything about the **price pattern** | 148 of them on 909 games, 0 positive. Rebuilding one would be the single most predictable waste in this repo |
| **first-inning (`KXMLBRFI`)** | 6.5¢ cost bar, 2 contracts at the touch, no reference price to check against, and the best published model beats the base rate by 0.003 Brier |
| a **full win-probability model** | it is the same shape as the tennis Stage 0–5 model, which lost to the bookmakers by +0.019 Brier on 2,645 matches. The production MLB bot found in the corpus reached the same conclusion independently: `mmoore07129/mlb-kalshi-bot` is **"Pinnacle-primary, model-fallback-only"** — its own model is a veto, not a price |
| **umpire tendency** | `statsapi` does publish officials, but pre-game population was not confirmed and the effect size in public work is small relative to a 3.0¢ bar. Listed as a later addition, not silently dropped |
| **Statcast pitch-level features** | permitted (`baseballsavant.mlb.com` passes robots) and genuinely rich, but it is a modelling project, not a mentality. Left as the obvious extension if any of M1–M3 shows a pulse |

## The absence worth stating

**The YouTube corpus contains nothing baseball-specific.** 38 videos read,
484 claims: zero mention MLB, a starting pitcher, or a total. The Kalshi/
Polymarket-targeted corpus contributes the *procedure* — de-vig the sharp
consensus, compare, trade only on positive net edge — and nothing about the
sport. `ask.py --tested "NRFI"`, `"umpire"`, `"park factor"` all return empty
across every corpus.

That absence is weak evidence — 38 of ~1,200 gated videos are read — but it is
consistent: **the public retail material on prediction markets is about crypto
and politics, and the public baseball material is about sportsbooks.** The
overlap this project sits in has almost nothing written about it, which cuts
both ways and is why none of the five above rests on a video claim.
