# Where the de-vig idea stands

**As of 2026-08-07.** This file is overwritten at the end of every session, so nothing in it is stale. Fuller versions: `bot-hunt/RESULTS_DEVIG_WHERE.md`, `kalshi-market-scan/docs/RESULTS_WEATHER_VS_ASK.md`, `crypto/MM_RESULTS_MAKER.md`.

**1. Dead — but not for the reason I first gave.** I wrote that the cost of trading is bigger than the bookmaker's whole margin. **That argument is wrong and I retract it:** the margin is what you strip off to work out the true price, not a cap on how wrong Kalshi can be. What actually settles it is a measurement — across **1,460 price comparisons on 30 baseball games, the two venues never disagreed by more than 2.77 cents**, and acting costs 2.75.

**And a second session reached it independently.** The MLB paper-test found **0 of 58 markets worth trading across 10 games**, best case (picked with hindsight) still **−1.63¢**. It also tested over/under totals — a family I had never looked at, carrying a **57% wider** bookmaker margin. Still nothing. Two codebases, three market types, same answer. More games will not rescue this.

**One honest limit:** every test uses Pinnacle, the sharpest book in the world. A *retail* book with a fat margin on a market Kalshi quotes tightly has never been tested. The one comparison of that kind in the archive rests on 13 games and proves nothing either way.

**2. The cheaper version is on track and decides ~6 September.** Instead of trading, just ask whether the sharp price *predicts* better than Kalshi's. 30 games joined, 17 already settled, ~14/day arriving. Needs ~440. If Pinnacle is not the better forecaster, no version of this idea can work and the thread closes for good.

**3. Weather — closed, no edge.** The model scored +0.43¢; plain climatology scored **+1.37¢** and a model that guesses 50% on everything scored **+1.01¢**. When a model that knows nothing beats yours, you have measured the gate, not a forecast. The reason: at the moment these markets open, **93% of prices are offers at 95–100¢ against a 46% actual win rate, with nobody bidding.** That is a placeholder, not a price.

**4. Crypto market making — ran on 658 markets and 4.9 million trades. One real finding, and I got ahead of it once.** Getting picked off costs a maker about **0.5¢ per contract, and it was negative on every single one of the eight days measured.** That is the number this project has wanted for weeks. **Whether market making actually makes money is still unknown** — I first reported it as encouraging, then found I had counted 96 fifteen-minute markets in a day as 96 independent facts when they all ride the same Bitcoin move. Correcting that widened the uncertainty **fivefold** and the answer became "cannot tell". Adding more data also made the picked-off cost **worse**, not better. Two of my own bugs were caught on the way, one of which would have priced four million trades at zero and invented a large fake profit.

**Net: the de-vig thread is closed, weather is closed. Two things are alive — the September forecast test, and whether a resting order earns enough spread to cover that 0.5¢. The second needs weeks of days rather than hundreds of 15-minute windows, plus the order book, which is free and already being recorded.**
