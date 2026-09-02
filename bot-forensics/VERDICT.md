# VERDICT — Tasks 3, 4 and 5

Companion to [FINDINGS.md](FINDINGS.md), which covers Tasks 1 and 2.

---

## Task 3 — the live configuration, run over the 14,162-market backtest

**Every configuration tested loses, on every tier, on train and on holdout, in
both arms. Nothing is close to the cost bar.**

The bot's own decision function — `tennis_engine.evaluate()` — was imported and
called, not reimplemented. The night's `Config` was reconstructed from the dated
comments in that file plus the order record (FINDINGS.md). Execution and exits
use `backtest/engine._walk`, the same causal replay the 480-config sweep used:
buy at the next candle's ask + 1c, stop-before-target on same-candle ties, exact
Decimal fees, hold to settlement if neither fires. One position per event, and
the portfolio cap enforced.

### Arm A — real set scores

`backtest/data/sofascore_matches.jsonl` gives real set boundaries for 1,406
matches, so `require_set_resolved`, `ahead_on_sets` and `min_set_margin` are
evaluated for real rather than proxied by price.

| configuration | c/trade ALL | train | **HOLDOUT** | $/match | t |
|---|---|---|---|---|---|
| NIGHT (as it ran) | −5.64 | −5.80 | **−5.52** | −11.74 | −13.6 |
| NIGHT floored at 25c | −7.16 | −7.48 | **−6.91** | −2.69 | −12.3 |
| NIGHT + the 60c floor only | −6.78 | −5.83 | **−7.60** | −0.89 | −6.4 |
| NIGHT + the 38c stop only | −5.63 | −5.82 | **−5.46** | −11.75 | −13.6 |
| NIGHT + no stop at all | **−4.59** | −5.39 | **−3.58** | −3.04 | −8.7 |
| CURRENT (post 3 Aug) | −6.47 | −5.96 | **−7.38** | −0.59 | −4.7 |

### Arm B — the one that matters, because Arm A cannot see ITF

**`sofascore_matches.jsonl` contains ATP (254), Challenger (913) and WTA (239)
and NOT ONE ITF MATCH.** ITF is 10,261 of the 13,658 market views, ~76% of
Kalshi's tennis book, and **64 of the 108 matches the bot actually traded**. A
test that cannot see ITF is not decisive, so a second arm replaces the score
gate with a price proxy — "the mid has climbed ≥10c above the opening line" —
and runs on all 13,658 views.

| configuration | ALL tiers | **ITF only** | ATP/Ch/WTA | ITF HOLDOUT |
|---|---|---|---|---|
| NIGHT (as it ran) | −8.08 | **−9.13** | −7.82 | **−8.77** |
| NIGHT + the 60c floor | −8.20 | −8.89 | −7.85 | −8.46 |
| NIGHT + no stop | −8.40 | −7.65 | −7.85 | −7.33 |
| CURRENT (post 3 Aug) | −7.70 | **−9.49** | −7.55 | −8.79 |

ITF-only, NIGHT config: **6,135 trades on 2,599 matches, −$1.98 per match,
t = −26.0.** The holdout alone is 2,510 trades on 1,045 matches at t = −16.0.
This is not an underpowered null. It is a large, precisely measured loss.

Proxy validation: on ATP/Ch/WTA the proxy arm reads 0.7–3.3c worse than the
true-score arm. Even crediting the proxy the full 3.3c, ITF lands at ≈ −5.8c.

Sensitivity to the proxy threshold, ITF only: climb ≥0c −9.71 · ≥5c −9.55 ·
≥10c −9.13 · ≥15c −8.58 · ≥20c −8.84 · ≥30c −9.72. **There is no threshold at
which it turns.**

### Where it ranks

Metric is net cents per trade, the sweep's own.

| | c/trade |
|---|---|
| S2 buy-and-hold — the best thing anyone here has found | −2.29 |
| 480-config sweep, best of 480 | −4.90 |
| **the night's config, Arm A (ATP/Ch/WTA)** | **−5.64** |
| **the night's config, Arm B, all tiers** | **−8.08** |
| S5 **random entry** | −8.28 |
| **the night's config, Arm B, ITF only** | **−9.13** |
| S1, the v3 strategy | −9.36 |
| 480-config sweep, worst of 480 | −11.43 |

On the tiers with the tightest books it would have ranked about 55th of 481 —
better than most of the sweep, still 0 of 481 profitable. **On ITF, where it
actually traded, it sits between random entry and S1.** The configuration is not
distinguishable from throwing darts.

### The live 39 hours are consistent with this, not in tension with it

Live: −$0.064 per match, se $0.284, n = 108.
Backtest, CURRENT config, all tiers: −$0.755 per match, se $0.077.

Difference $0.69, se $0.294 → **t = 2.35**. The live window ran about two
standard errors better than its own backtest predicts. That is what a good run
looks like. It is not evidence of a different process, and it is the wrong
direction to be reassuring: the live sample is small enough that a 2σ good run
is unremarkable, and the backtest sample is large enough that its estimate is
the one to believe.

### Task 3's second half — the four findings rescued from a memory file

`high_sweep.py`, `high_entry.py` and `longshot.py` re-run and saved to
`out/rerun_*.txt`. Headlines:

- **`high_sweep`** — the only positive rows are the *optimistic* maker fill
  (+0.58c at 85–89c, +0.35c at 93–95c). The honest `maker-strict` arm is −1.30
  to −2.42c and taker is −1.50 to −2.21c. Unchanged from `HIGH_SWEEP_RERUN.md`.
- **`high_entry`** — one positive cell in the whole file: buy 96–97c, opened
  ≥60c favourite, **hold with no stop, +0.62c on n = 95.** Add an 80c stop to
  the identical trades and it becomes **−3.77c**.
- **`longshot`** — every configuration loses, −25% to −46% ROI. "Buy the
  collapsed favourite" is the worst thing in the file.
- **the breakeven bars**, now on disk: 85c needs 86.9%, 90c needs 91.6%, 95c
  needs 96.4%, 97c needs 98.2%.

> **One thing three independent files now agree on, and it contradicts the
> live bot's design: the stop loss is the single most expensive component.**
> `high_entry` −0.78c → −4.41c when a stop is added. `high_sweep`'s best rows
> are all hold-to-settlement. The 480-config sweep's S2 buy-and-hold (−2.29c)
> beats S1's exit ladder (−9.36c) by 7.07c. And in Arm A here, removing the stop
> is the single best change available (−6.47c → −4.59c). The live bot stopped
> out of **77% of its backtested trades** and 30 of 71 live ones.

### ⚠ Two corrections to the sentences above, from the `reopen` audit, 2026-09-01

**1. Every stop number here is a CEILING. The real damage was worse.**
`kalshi-inplay-bot/backtest/engine.py:265` fills a stop **at the stop price**
whenever the bid touched or crossed it — `close(i, stop_now - slip, ...)` — even
when the bid gapped straight through. Real markets do not fill you at a price
that never traded. **So −9.36c is the best case for stopping out, not the
measured cost of it.** That strengthens the conclusion rather than weakening it,
and it should never have been left implicit.

**2. The "−2.29c → −9.36c" sentence blames the stop for more than the stop.**
S1 carries a **+15c target with scale-out AND a disaster stop AND a structural
stop**, so the gap between it and S2 buy-and-hold is the whole exit ladder, not
the stop alone. **The conclusion survives on a clean isolation elsewhere**
(+0.62c → −3.77c when only the stop is added), so the direction and the ranking
stand — but *"the stop turned −2.29c into −9.36c"* is a loose mechanism claim and
should be quoted as **"the exit ladder"** unless the isolated figure is meant.

**Neither correction moves the verdict.** Stopping out is still the most
expensive component, on three independent files, and now on a ceiling estimate.

---

## Task 4 — the extractors

### The corpus could not answer this and had to be told so

`signal-github`'s 3,137-repo corpus returns **five** repos for "tennis". It was
retrieved with Kalshi/Polymarket terms behind a prediction-market topic gate, so
a repo that scrapes ITF draws and never says "Kalshi" is invisible to it by
construction. Adding tennis terms to `signal-github/src/queries.py` would push
them through that same gate and drop them. So Task 4 ran a separate narrow
retrieval (`src/t4_github.py`) reusing that project's cached authenticated
client, writing nothing into its database.

### ⚠️ Q3 — ITF: **the closed thread reopens**

A prior session closed the ITF work on the finding that **no free ITF data
source exists**. That is now false.

**`livetennisapi.com`** — eleven official client libraries on GitHub
(`livetennisapi/*`: Go, Swift, TypeScript, Python, n8n, Home Assistant, VS Code,
Dify, Node-RED, MCP, Codex), **every one pushed within the last two days**.
Verified directly, not from a README:

| check | result |
|---|---|
| `GET https://api.livetennisapi.com/api/public/v1/health` | **200 `{"status":"ok","version":"v1"}`** — no key needed |
| `GET .../v1/matches?status=live` | **401** — key required |
| coverage claimed | "ATP, WTA, Challenger and **ITF** — both singles and doubles — from one arbitrated feed" |
| free tier | "Free: live scores & current matches, players, fixtures and your usage" |
| paid | history $9.99 · **market odds $29.99** · AI win-probability + WebSocket $99.99 |
| historical tape | "point-by-point … 43 monthly periods, January 2023 through July 2026 — across ATP, WTA, Challenger and ITF" |

> **What is verified and what is not.** The service exists, is live, is actively
> developed, and *advertises* a free ITF tier. That the free tier actually
> returns ITF data is **not verified** — it needs an API key, which needs an
> account, which I will not create. This is an ADVOCACY signal (the vendor wrote
> the coverage claim), not a corroboration.
>
> **This is a decision for the user, and it is the highest-value item in this
> report.** If that free tier does return live ITF scores, the ITF thread was
> closed on a premise that is no longer true — though note Task 3 says the ITF
> *economics* are the worst of any tier, so reopening the data question does not
> reopen the strategy.

Also found: `carpsesdema/itf-tennis-scraper` (ITF men's singles, Python, 432
days stale) and `Mriganka-codes/tennis_data` (ATP/WTA/**Challenger** with odds
from tennisexplorer.com, every 6 hours via GitHub Actions — no ITF).

### Q1 — a working in-play tennis strategy with evidence: **no, and the field is crowded**

**32 distinct Kalshi/Polymarket tennis repos. 30 of them created in the last 180
days. 135 stars between all 32, and 129 of those belong to one repo.** Not one
publishes a settled P&L. Every repo that states its mode states **paper** —
descriptions run to "GBDT + Bayesian updater + Markov chain win probability,
paper trading via Kalshi", "hierarchical Markov match model, paper-mode
default", "paper and real trades". One claims "systematic mispricing on Kalshi"
with nothing attached, which is `signal-github`'s `trust_me_bro` shape exactly.
Repo-level detail stays in the gitignored `out/t4_github*` files; this repo is
public and the point here is the aggregate, not any individual.

> **The finding is the crowd, not any one repo.** Roughly thirty people
> independently built this exact bot in the last six months, and the count is
> still rising — five of the thirty-two were created in the last nine days.
> Nobody has shown it working. That is consistent with the adverse-selection
> result already in `STATUS.md` (finding #9, the 20-year professional's "be a
> taker, not a maker"): if the obvious in-play tennis trade were available, it
> would not survive thirty simultaneous discoverers.

### Q2 — score and odds sources

The YouTube corpora (1,135 videos, **39.8M characters** of transcript) name
exactly one class of free feed in this space: **The Odds API** free tier
("covered schedule odds scores, 30 minute" refresh), plus `odds-api.net` and
`sportsgameodds`. GitHub adds `Aneeshers/tennis-sackmann-archive`,
`tunjayoff/sofascore_scraper` (football), and several Flashscore scrapers.
Nothing found is faster or more reliable than Sofascore for live tennis; the
only thing that would be is `livetennisapi`'s $99.99 WebSocket tier.

> **A correction to `STATUS.md` found on the way.** `STATUS.md` says "Sackmann
> upstream is 404" and treats `kalshi-tennis/data` as the only copy. Checked
> against the GitHub API today: `JeffSackmann/tennis_atp`, `tennis_wta` and
> `tennis_slam_pointbypoint` **are** 404 — but **`JeffSackmann/tennis_MatchChartingProject`
> is live, 399 stars, pushed 2026-05-25**, and `Aneeshers/tennis-sackmann-archive`
> is a live third-party mirror of the ATP/WTA/Grand-Slam point-by-point data
> pushed **2026-06-25**. The blanket "upstream is 404" is too strong and the
> data is not unrecoverable.

### Q4 — overnight versus daytime in prediction-market sports books

**Nobody documents it.** One repo is even on the topic —
`RyanW1228/polymarket-microstructure-and-trading`, "Notes on manual trading,
liquidity, and inefficiencies in sports prediction markets" — and four GitHub
queries aimed squarely at it returned one result between them. In the YouTube
corpora, "overnight" appears 142 times across 75 videos and **every hit is
equity/futures session language** ("the overnight low", "don't trade the
overnight session", "make a million overnight"). Zero about prediction-market
sports books by hour.

### ⚠️ One contradiction found and resolved against the source

A video in the corpus (`ELpX7I0sPtc`) states that on prediction markets *"in
tennis, where medical withdrawals are common, prices settle at the number they
were at at the time of the withdrawal"*, and gives a worked example of a 99c
favourite retiring.

**That is false for Kalshi, and it is checkable from data already on disk.**
`_settled_all.json` holds 9,352 settled tennis markets: **4,676 `yes` and 4,676
`no`, exactly mirrored, and not one non-binary settlement.** A binary contract
cannot settle "at the number". Three markets closed with a last price between
10c and 90c — `KXITFWMATCH-26JUL23KUJCIO` closed at 43c/61c and settled `yes`
for the 43c side, which is the retirement signature: the price freezes and the
contract still resolves 0/100. The bot's own comment
(`tennis_engine.py:332`, "withdrawal resolves you to No") is the correct reading.

> Worth noting which way that cuts: a mid-match retirement pays a 43c holder
> **100**. It is a windfall for hold-to-settlement and invisible to a stop.
> Another small entry on the growing pile against the stop loss.

---

## Task 5 — the verdict

> ### **A and B, jointly. Not C as the primary cause, and D is refuted.**
>
> **Confidence: high that it is not D. Moderate-to-high on A+B over C.**

**A — variance.** The bot's whole life is −$6.92 over 108 matches, mean −$0.064,
95% CI at burst level **[−$0.97, +$0.78]**. The equity curve peaked at +$32.19,
and reordering the same 108 results at random reaches that peak **5.2%** of the
time. The before/after gap at the peak is exceeded by **27%** of random
reorderings of the same numbers, and a zero-drift process shows the same
rising-then-falling shape **85%** of the time. Splitting on the clock instead of
the curve: night +$0.799/match against day −$0.248, Welch p = 0.133; **0 of 13
permutation-tested buckets survive BH-FDR at 5%** (the *parametric* arm over 21
buckets reports 3, all at n = 4–6 and one of them a loss bucket — see
[FINDINGS.md](FINDINGS.md) "Which arm this 0 comes from" and ledger row
[B005a](../LEDGER.md#section-7--bot-forensics-the-night-the-live-tennis-bot-made-money);
the permutation arm is the correct test and supersedes it).

**B — a martingale that happened to win.** This is the part the user's memory of
"many trades, not one lucky win" was picking up, and it is the opposite of
reassuring. Twelve averaging-down sequences account for **−$16.43**; the other 94
matches are **+$9.63**. Before the peak there were **seven averaging-down
sequences and seven winners, +$6.63**. After it, the same mechanism lost about
$23, with SAGLEV alone (−$8.79) larger than all seven early wins combined. A run
of small wins terminated by one loss bigger than all of them is the martingale
signature, and while it is running it is indistinguishable from skill.

**C — the stale-score bug: real, measured, and a contributing mechanism rather
than the explanation.** Only **2.6%** of the repricing around a score change
falls *after* the bot's snapshot showed it (+4.68c before, +0.17c after, placebo
five minutes earlier +0.18c, n = 4,398). The bot was systematically entering
after the move it was meant to predict. But this makes the profitable stretch
*less* explicable, not more: C predicts a persistent negative drift, and the
first 60 matches were positive. C explains why the strategy has no edge. It does
not explain why one particular run went up.

**D — a real effect confined to a market condition the pooled backtest averages
away: refuted, and this is the strongest statement in the report.** Task 3 ran
the actual configuration over 13,658 markets. Every tier, every band, every
variant, train and holdout: negative. **The condition the user proposes — ITF,
overnight — is the *worst* cell in the whole test at −9.13c per trade, −$1.98
per match, t = −26.** And Task 2 shows the night/day comparison is confounded
against the night at source: overnight ITF-W books average a **7.16c** spread
against 1.17c on ATP. The bucket that looked better is the one with the worse
book.

### The one-sentence version

**The account did go up by about $30 in that window, the bot's own trades were
not what did it, the shape everyone remembers is the shape a fair coin makes,
and the mechanism that produced the run of small wins is the same one that
produced the −$8.79 that ended it.**

### What this does not say

- It does not say the bot is broken. It says the strategy has no edge, which the
  repo already knew from 14,162 markets and now knows from the live record too.
- It does not say the night's config was badly chosen. It ranked ~55th of 481 on
  the tightest-book tiers, which is *better* than most of the sweep. It is still
  0 of 481.
- The live window is 39 hours and 74 independent bursts. Nothing here could have
  detected an effect smaller than about $1 per match, and no such effect is
  claimed in either direction.

### What is actually worth doing next, in order

1. **Nothing to the bot.** `TRADING_DISABLED` stays. Task 3 is the second
   independent verdict on the same strategy.
2. **If anything is ever re-armed, delete the stop before anything else.** Four
   independent files now agree the exit ladder is the most expensive component,
   and the retirement mechanic quietly rewards holding.
3. **Decide the `livetennisapi` question.** It is the only finding here that
   opens something rather than closing it, and it costs one free signup to
   settle. Note it reopens *data availability*, not the trade.
4. **Correct `STATUS.md` on Sackmann.** A live mirror exists.
