# Where the de-vig idea stands

**As of 2026-08-07.** This file is overwritten at the end of every session, so nothing in it is stale. Fuller versions: `bot-hunt/RESULTS_DEVIG_WHERE.md`, `kalshi-market-scan/docs/RESULTS_WEATHER_VS_ASK.md`, `crypto/MM_RESULTS_MAKER.md`.

**1. Dead — but not for the reason I first gave.** I wrote that the cost of trading is bigger than the bookmaker's whole margin. **That argument is wrong and I retract it:** the margin is what you strip off to work out the true price, not a cap on how wrong Kalshi can be. What actually settles it is a measurement — across **1,460 price comparisons on 30 baseball games, the two venues never disagreed by more than 2.77 cents**, and acting costs 2.75.

**And a second session reached it independently.** The MLB paper-test found **0 of 58 markets worth trading across 10 games**, best case (picked with hindsight) still **−1.63¢**. It also tested over/under totals — a family I had never looked at, carrying a **57% wider** bookmaker margin. Still nothing. Two codebases, three market types, same answer. More games will not rescue this.

**One honest limit:** every test uses Pinnacle, the sharpest book in the world. A *retail* book with a fat margin on a market Kalshi quotes tightly has never been tested. The one comparison of that kind in the archive rests on 13 games and proves nothing either way.

**2. The cheaper version is on track and decides ~6 September.** Instead of trading, just ask whether the sharp price *predicts* better than Kalshi's. 30 games joined, 17 already settled, ~14/day arriving. Needs ~440. If Pinnacle is not the better forecaster, no version of this idea can work and the thread closes for good.

**3. Weather — closed, no edge.** The model scored +0.43¢; plain climatology scored **+1.37¢** and a model that guesses 50% on everything scored **+1.01¢**. When a model that knows nothing beats yours, you have measured the gate, not a forecast. The reason: at the moment these markets open, **93% of prices are offers at 95–100¢ against a 46% actual win rate, with nobody bidding.** That is a placeholder, not a price.

**4. Crypto market making — RAN, and it is the one thing that got more interesting, not less.** On 432 markets and 3.3 million real trades: posting orders instead of taking them is **significantly worse than having your side picked at random** — by **0.39¢ per contract**, and this time the odds of that being chance are under 1 in 10,000. That is the cost of getting picked off, and it is the exact number this project has been missing for weeks. **But it is smaller than the ~1¢ the spread pays**, which is the first time anything here has pointed toward a strategy rather than away from one. The raw profit looked like +0.50¢; ignore that — the market drifted up over those five days and anyone holding YES looked clever. Two of my own bugs were caught on the way, one of which would have priced four million trades at zero and invented a large fake profit.

**Net: the de-vig thread is closed, weather is closed. Two things are alive — the September forecast test, and now the question of whether a resting order captures enough spread to cover that 0.39¢. Answering the second needs the order book, which is free and which we have been recording all along.**
