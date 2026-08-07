# Baseball — where things stand

**As of 2026-08-07.** This file is overwritten at the end of every baseball session, so it is always the latest state and there is only ever one of it. Nothing in it is stale.

**What I built.** A baseball version of the tennis paper test. Sixteen bots, no real money anywhere, all watching the same games on Kalshi. Each has a different way of thinking about a game: the starting pitcher, the weather and the ballpark, how tired the bullpen is, betting early before the professional bookmakers post a price, and reacting quickly when the team sheets come out. Everything they look at is free — official baseball data and government weather. Every bot writes down its reasoning before the game starts, so nothing can be rewritten afterwards. It runs on its own and comes back after a restart.

**The first thing it already tells us, before any game has finished.** Kalshi's baseball prices already match the sharpest bookmaker in the world to within about a penny. I checked 58 markets and not one was off by enough to cover the cost of trading. So these bots are not trying to beat Kalshi — they have to beat professionals. I have written down in advance that I expect all five ideas to fail, and how I will know.

**Your question about the other two markets: no, they are not better.** The "249 over/under markets recorded and never looked at" is really about 23 games. That market lists eleven different price levels for the same game, so the count was inflated about elevenfold. The first-inning market costs more than twice as much to trade and has almost nothing available to buy, so I dropped it. I kept over/under alongside the main market, because weather and tired pitchers change how many runs are scored much more than they change who wins.

**One thing settled itself.** I set a stricter standard that applies to the tennis test as well as this one, and flagged it rather than changing their files. The tennis session checked my working, agreed, put it in their code — and found a number I had got wrong. I have corrected it and said so. Note for anyone reading across projects: where that standard mentions 32, that is the **combined** number of bots across baseball and tennis together, not either test's own count of 16.

**What's open — one small question.** That wrong number: should it count in the running tally of corrections this project keeps? I have left it out, because the tally is about promising results shrinking, and this was a cost being restated. Either answer is fine; tell me if you want it counted.

**Nothing needs doing.** To see how it is going, run `mlb-paper\deploy\check.bat`. The first line says either ALIVE or STALE. That is the only command you need.
