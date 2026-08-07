# BRIEF.md — the whole picture, one page

One section per project. **Every session overwrites only its own section**, via
`py -3 coordinator\brief.py write <slug> --file <body.md>`. Nothing else in this
file is touched by that command.

This is the file the coordinating chat reads. `STATUS.md` stays the detailed
channel between sessions; this is the short channel out. Plain English, no
acronyms, no jargon. If a number matters, say whether bigger is better.

<!-- STAMP -->
> **Generated 2026-08-07 13:40, on top of commit `60205cd`.**
> **Freshness check:** if `60205cd` does not appear in this repo's commit
> history on GitHub, you are reading a cached copy — stop and refetch.
> Being one or two commits behind the newest is normal and expected:
> this page is always written just before the commit that carries it.
> Cache-busting URL, always safe to use:
> `https://raw.githubusercontent.com/vinexcleaning/trading/main/BRIEF.md?v=60205cd`
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

<!-- SECTION:tennis updated=2026-08-07T13:40 -->
## Tennis — paper forward test

**As of 2026-08-07 (evening).** Running now, **108 finished matches** collected of a 2,500 target. No money is involved and none can be: no keys, no order-placing code, and a test fails the build if any appears. **It calls no AI model — it is plain arithmetic, so running it costs nothing beyond electricity.**

**The result so far, from the completed 50-match checkpoint: 0 of 16 bots produced a claim that stands up.** Thirteen came back "can't tell", three had never traded. That is exactly what was written down in advance.

**The one number worth carrying to other projects: it costs 4.8 cents per contract to get in and out of Kalshi tennis** (2.7 fees + 2.1 the buy/sell gap). That is *higher* than the 3.6 cents this repo has been assuming, and it is measured rather than estimated. **Bigger is worse.** Every edge this repo has ever found is smaller than 4.8 cents.

**Player form data: refreshed from 67 days stale to 4.** The free Sackmann mirror **cannot be refreshed — it is frozen**, which I established by re-downloading every 2026 file and comparing byte for byte. I found the one free source that is current (tennis-data.co.uk, weekly, permitted by its own robots file) and merged 938 of 984 new results.

**The limit on that, stated plainly: it covers the top tier only.** Challenger and lower events are **87% of the matches Kalshi lists**, and no free current source covers them. So this fixed form for about **one match in eight**; the rest is as stale as before.

**A style that had placed zero bets turned out to be broken, not cautious.** Over 13,089 decisions its best score was 1.90 against a threshold of 2.50 — and its maximum *possible* score was 1.88, so no market condition could ever have made it trade. It was being penalised for player-history data being old, while ignoring player history entirely. Fixed: it has now placed 78 bets.

**Four separate defects this week were invisible from the outside** — the program reported healthy the whole time. Three copies running at once overwriting each other; a log growing fast enough to delete its own earliest records; a "profitable" bot that had won 2 bets out of 2; and fills that looked better than expected only because the bad ones were being thrown away. All four are fixed and tested.

**Open questions.** No live scores, so bots see prices only — the site that has them tells automated readers to stay out. And the profit question still needs roughly **2,250 finished matches per bot**, about three weeks of continuous running.

**What I need from you: nothing.** It is collecting. Moving it to the laptop takes 15 minutes whenever you want it off the desktop — `tennis-paper-forward/deploy/LAPTOP_SETUP.md`.

_Section `tennis` last written 2026-08-07 13:40._
<!-- /SECTION:tennis -->

---

<!-- SECTION:mlb updated=2026-08-07T13:40 -->
## Baseball — paper forward test

**As of 2026-08-07.** Written by the `mlb-paper` session at the end of its run.

**What it is.** Sixteen bots, no real money anywhere, all watching the same games on Kalshi. Each has a different way of thinking about a game: the starting pitcher, the weather and the ballpark, how tired the bullpen is, betting early before the professional bookmakers post a price, and reacting quickly when the team sheets come out. Everything they look at is free — official baseball data and government weather. Every bot writes down its reasoning before the game starts, so nothing can be rewritten afterwards. It runs on its own and comes back after a restart.

**Nothing here calls a paid service.** The bots are plain arithmetic — no language model, no API bill. Zero cost per game, and zero for the thousands of games needed to finish. The only thing that ever cost money is the session building it.

**The first finding, before any game has finished.** Kalshi's baseball prices already match the sharpest bookmaker in the world to within about a penny. I checked 58 markets and not one was off by enough to cover the cost of trading. So these bots are not trying to beat Kalshi — they have to beat professionals. I have written down in advance that I expect all five ideas to fail, and how I will know.

**The other two markets are not better.** The "249 over/under markets recorded and never looked at" is really about 23 games — that market lists eleven price levels for the same game, so the count was inflated about elevenfold. The first-inning market costs more than twice as much to trade and has almost nothing available to buy, so I dropped it. Over/under is kept alongside, because weather and tired pitchers change how many runs are scored far more than they change who wins.

**A new safety check found two real bugs elsewhere in the repo.** Kalshi renamed some of its data fields; the old names now return nothing, and "nothing" quietly becomes zero in a calculation. Three separate sessions have been caught by this, so I turned it into an automatic check. It immediately found two files — in the market-selection and crypto folders, not mine — that read the wrong name and therefore report every order book as empty. I have flagged them for their owners rather than editing someone else's work. One of those files is a test whose whole job is to answer a question this repo has argued about twice: whether that data source returns anything at all. It may have been answering "no" because of this bug. Worth someone checking.

**What's open — one small question.** I got a number wrong earlier and corrected it (a cost was 6.2%, not the 8% I said). Should that count in the running tally of corrections this project keeps? I left it out, because the tally is about promising results shrinking and this was a cost being restated. Either answer is fine.

**Nothing needs doing.** To see how the baseball test is going, run `mlb-paper\deploy\check.bat`. The first line says either ALIVE or STALE. That is the only command needed.

_Section `mlb` last written 2026-08-07 13:40._
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
