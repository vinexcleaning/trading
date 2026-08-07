# BRIEF.md — the whole picture, one page

One section per project. **Every session overwrites only its own section**, via
`py -3 coordinator\brief.py write <slug> --file <body.md>`. Nothing else in this
file is touched by that command.

This is the file the coordinating chat reads. `STATUS.md` stays the detailed
channel between sessions; this is the short channel out. Plain English, no
acronyms, no jargon. If a number matters, say whether bigger is better.

<!-- STAMP -->
> **Generated 2026-08-07 13:34, on top of commit `13b8e61`.**
> **Freshness check:** if `13b8e61` does not appear in this repo's commit
> history on GitHub, you are reading a cached copy — stop and refetch.
> Being one or two commits behind the newest is normal and expected:
> this page is always written just before the commit that carries it.
> Cache-busting URL, always safe to use:
> `https://raw.githubusercontent.com/vinexcleaning/trading/main/BRIEF.md?v=13b8e61`
<!-- /STAMP -->

---

<!-- SECTION:coordinator updated=2026-08-07T13:16 -->
## How to read this page

**This file replaced six separate `BRIEF_*.md` files on 2026-08-07.** They were
drifting into a pile — three fixed-name ones and three dated duplicates — and
working out which was current was itself a job. Now there is one page. Each
session overwrites **only its own section**, through a command that physically
cannot reach another section.

**Two things this page can tell you that GitHub cannot**, because a session
reading it is sitting on the actual machine:

- whether work exists on disk that has **not been pushed** — if so, you are
  reading an older picture and the coordinator will say so by name;
- whether a project **did work it has not written up** — its last commit newer
  than its section here.

**The freshness stamp at the top is the safety catch.** It names the commit this
page was generated at. If that is not the newest commit on GitHub, you are
reading a cached copy. A stale page that announces its own staleness is safe; a
silent one is not.

**What this page is not.** It reports state, not truth. Every claim below was
written by the session that did the work and is that session's responsibility.
Nothing here has been re-audited by the coordinator. Claims get tested in
`LEDGER.md` and `GUARDS.md`, and that has not changed.

**Instructions now travel through files, not copy-paste.** Give an instruction
to the coordinator session once; it files it to whichever sessions need it, and
each replies in the same file. The honest limit: the coordinator can *leave* a
message, it cannot *deliver* one. A session reads its mail when it next starts,
or when you say "check your mail" in that window. A session already mid-task
will not see it until it finishes.

**It holds no credential, makes no network call of any kind, and cannot place a
trade.** A test fails the moment any of that changes.

Design and the full list of what it cannot do:
[coordinator/COORDINATOR.md](coordinator/COORDINATOR.md).

_Section `coordinator` last written 2026-08-07 13:16._
<!-- /SECTION:coordinator -->

---

<!-- SECTION:tennis updated=2026-08-07T13:16 -->
## Tennis — paper forward test

_Written by the `tennis-paper-forward` session. Migrated verbatim from `BRIEF_TENNIS.md` on 2026-08-07; not re-audited by the coordinator._

**As of 2026-08-07 (evening).** Overwritten at the end of every session, so this is always the latest. Still collecting, now past 106 finished matches on the way to a target of 2,500. No money is involved: no keys, no order-placing code, and a test fails the build if any appears. **It calls no AI model — it is plain arithmetic, and running it costs nothing.**

**Job 1 — refresh the stale player data. Done, with a real limit.** The free Sackmann mirror **cannot be refreshed: it is frozen.** I re-downloaded every 2026 file and compared them byte for byte against what we already had — identical, and the original source is still deleted. So I found the one free source that *is* current, tennis-data.co.uk, which publishes weekly and permits this in its own robots file. **Player form went from 67 days stale to 4**, with 938 of 984 new results merged.

**The catch, stated plainly: that source covers the main tour only.** Challenger and lower-tier events are **87% of the matches Kalshi actually lists**, and no free current source covers them. So this fixes form for about **one match in eight**. The rest is exactly as stale as it was.

**Along the way I found the name matching was quietly dropping 3 in 10 results** — and dropping them hardest for the *best-known* players, because of hyphens (Auger-Aliassime), two-word surnames (De Minaur) and double initials (Cerundolo J.M.). Fixed; misses are now 3–6%. Where two players genuinely share a surname and initial it refuses to guess.

**Job 2 — the style that placed zero bets. It is a BUG, not correct caution, and it could never have traded.** Over 13,089 decisions its best score was 1.90 against a threshold of 2.50. Its maximum *possible* score was 1.88. **No market condition could have made it buy anything.**

**The cause:** it was being penalised for the player-history data being old — but that style ignores player history entirely. It trades price movement on our own recorded prices. It was being charged for something it never uses. Fixed: it has now placed **24 bets**, and it still correctly refuses moves too small to cover the cost of trading.

**What that cost us:** three of the sixteen bots contributed nothing to the first 50-match run while still counting toward the statistical bar — so the test was harder to pass than the search actually justified. Conservative direction, but not deliberate.

**What I need from you: nothing.** It is running with both fixes. Two things to know: the profit question still needs about 2,250 matches per bot (roughly three weeks), and moving it to the laptop takes 15 minutes whenever you want it off your desktop — `tennis-paper-forward/deploy/LAPTOP_SETUP.md`.

_Section `tennis` last written 2026-08-07 13:16._
<!-- /SECTION:tennis -->

---

<!-- SECTION:mlb updated=2026-08-07T13:16 -->
## Baseball — paper forward test

_Written by the `mlb-paper` session. Migrated verbatim from `BRIEF_MLB.md` on 2026-08-07; not re-audited by the coordinator._

**As of 2026-08-07.** This file is overwritten at the end of every baseball session, so it is always the latest state and there is only ever one of it. Nothing in it is stale.

**What I built.** A baseball version of the tennis paper test. Sixteen bots, no real money anywhere, all watching the same games on Kalshi. Each has a different way of thinking about a game: the starting pitcher, the weather and the ballpark, how tired the bullpen is, betting early before the professional bookmakers post a price, and reacting quickly when the team sheets come out. Everything they look at is free — official baseball data and government weather. Every bot writes down its reasoning before the game starts, so nothing can be rewritten afterwards. It runs on its own and comes back after a restart.

**The first thing it already tells us, before any game has finished.** Kalshi's baseball prices already match the sharpest bookmaker in the world to within about a penny. I checked 58 markets and not one was off by enough to cover the cost of trading. So these bots are not trying to beat Kalshi — they have to beat professionals. I have written down in advance that I expect all five ideas to fail, and how I will know.

**Your question about the other two markets: no, they are not better.** The "249 over/under markets recorded and never looked at" is really about 23 games. That market lists eleven different price levels for the same game, so the count was inflated about elevenfold. The first-inning market costs more than twice as much to trade and has almost nothing available to buy, so I dropped it. I kept over/under alongside the main market, because weather and tired pitchers change how many runs are scored much more than they change who wins.

**One thing settled itself.** I set a stricter standard that applies to the tennis test as well as this one, and flagged it rather than changing their files. The tennis session checked my working, agreed, put it in their code — and found a number I had got wrong. I have corrected it and said so. Note for anyone reading across projects: where that standard mentions 32, that is the **combined** number of bots across baseball and tennis together, not either test's own count of 16.

**What's open — one small question.** That wrong number: should it count in the running tally of corrections this project keeps? I have left it out, because the tally is about promising results shrinking, and this was a cost being restated. Either answer is fine; tell me if you want it counted.

**Nothing needs doing.** To see how it is going, run `mlb-paper\deploy\check.bat`. The first line says either ALIVE or STALE. That is the only command you need.

_Section `mlb` last written 2026-08-07 13:16._
<!-- /SECTION:mlb -->

---

<!-- SECTION:devig updated=2026-08-07T13:34 -->
## De-vig, weather, and crypto market making

**As of 2026-08-07.** This section is rewritten at the end of every session, so nothing in it is stale. Fuller versions: `bot-hunt/RESULTS_DEVIG_WHERE.md`, `kalshi-market-scan/docs/RESULTS_WEATHER_VS_ASK.md`, `crypto/MM_RESULTS_MAKER.md`, `crypto/PREREGISTRATION_MAKER_VIABILITY.md`.

**1. De-vig is CLOSED — but not for the reason I first gave.** I wrote that the cost of trading is bigger than the bookmaker's whole margin. **That argument is wrong and I retract it:** the margin is what you strip off to work out the true price, not a cap on how wrong Kalshi can be. What settles it is a measurement — across **1,460 price comparisons on 30 baseball games, the two venues never disagreed by more than 2.77 cents**, and acting costs 2.75.

**A second session reached the same place independently.** The MLB paper-test found **0 of 58 markets worth trading across 10 games**, best case (picked with hindsight) still **−1.63¢**. It also tested over/under totals — a market type I had never looked at, carrying a **57% wider** bookmaker margin. Still nothing. Two codebases, three market types, same answer. More games will not rescue this.

**One honest limit:** every test used Pinnacle, the sharpest book in the world. A *retail* book with a fat margin on a market Kalshi quotes tightly has never been tested. The one comparison of that kind in the archive rests on 13 games and proves nothing either way.

**2. The cheaper version is on track and decides ~6 September.** Instead of trading, just ask whether the sharp price *predicts* better than Kalshi's. 30 games joined, 17 already settled, ~14/day arriving. Needs ~440. If Pinnacle is not the better forecaster, no version of this idea can work and the thread closes for good.

**3. Weather — CLOSED, no edge.** The model scored +0.43¢; plain climatology scored **+1.37¢** and a model that guesses 50% on everything scored **+1.01¢**. When a model that knows nothing beats yours, you have measured the gate and not a forecast. The reason: at the moment these markets open, **93% of prices are offers at 95–100¢ against a 46% actual win rate, with nobody bidding.** That is a placeholder, not a price.

**4. Crypto market making — one real finding, and I got ahead of it once.** On 658 markets and 4.9 million trades, getting picked off costs a maker about **0.5¢ per contract, negative on every one of the eight days measured**. That is the number this project has wanted for weeks. **Whether market making makes money is still unknown.** I first called it encouraging, then found I had counted 96 fifteen-minute markets in a day as 96 independent facts when they all ride the same Bitcoin move; correcting that widened the uncertainty **fivefold** and the answer became "cannot tell". Adding more data also made the pick-off cost **worse**, not better.

**5. The one live money question is set up and written down in advance — not yet run.** Does a resting order earn enough spread to cover that 0.5¢? **Correction to something I told the user: the order book is free but is NOT being recorded for crypto** — the recorder covers five other markets and crypto is not one. That was the difference between "needs weeks" and "runs now", and I had it wrong until I checked. What rescues it is a public archive holding **24 days of full order-book history for Bitcoin markets**, which nobody had checked for crypto. Plan committed before any number exists: `crypto/PREREGISTRATION_MAKER_VIABILITY.md`. I expect it to fail and said why in advance. **Awaiting a go-ahead; nothing is running.**

**Net: de-vig closed, weather closed. Two things alive — the September forecast test, and the resting-order test above. One idea queued but NOT started: a retail book with a fat margin, which has a known blocker (the free retail feed found so far quotes only one side, so it cannot be de-vigged at all).**

_Section `devig` last written 2026-08-07 13:34._
<!-- /SECTION:devig -->

---

<!-- SECTION:signal updated=2026-08-07T13:16 -->
## Signal hunting — GitHub, YouTube, social

_Written by the `coordinator` session from repo state on 2026-08-07, **not** by
a session that did the work. No session has touched these folders since
2026-08-05. Treat it as a pointer, not a report — if this matters, ask for a
session to be opened on it and it will write its own section._

**Nothing is running here and nothing is waiting on you.** Three search tools
were built, all produced results, and all are paused.

- **GitHub search.** 3,165 repositories scored for zero core API calls; 4 read
  in full. The headline lesson is a negative one worth remembering: **stars do
  not predict substance** — the correlation is effectively zero at that sample
  size, and an earlier positive figure was itself the mistake. Reading found
  five real defects that every computed score had missed.
- **YouTube search.** 38 videos read for nothing spent. Nine usable findings,
  one of which **contradicts our own market-making thesis** and has not been
  reconciled.
- **Social search.** Tripling the sample returned exactly nothing. That is a
  result, not a failure.

**The one open item that could still change an answer:** the exchange's rulebook
has never been read, because it defeats both plain fetching and a real browser.
Until it is read, the question of whether automated trading is permitted there
rests on a membership agreement that is silent on the point.

_Section `signal` last written 2026-08-07 13:16._
<!-- /SECTION:signal -->
