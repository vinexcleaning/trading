# Where the de-vig idea stands — 7 August 2026

**1. Dead — but not for the reason I first gave.** I wrote that the cost of trading is bigger than the bookmaker's whole margin. **That argument is wrong and I retract it:** the margin is what you strip off to work out the true price, not a cap on how wrong Kalshi can be. What actually settles it is a measurement — across **1,460 price comparisons on 30 baseball games, the two venues never disagreed by more than 2.77 cents**, and acting costs 2.75.

**And a second session reached it independently.** The MLB paper-test found **0 of 58 markets worth trading across 10 games**, best case (picked with hindsight) still **−1.63¢**. It also tested over/under totals — a family I had never looked at, carrying a **57% wider** bookmaker margin. Still nothing. Two codebases, three market types, same answer. More games will not rescue this.

**One honest limit:** every test uses Pinnacle, the sharpest book in the world. A *retail* book with a fat margin on a market Kalshi quotes tightly has never been tested. The one comparison of that kind in the archive rests on 13 games and proves nothing either way.

**2. The cheaper version is on track and decides ~6 September.** Instead of trading, just ask whether the sharp price *predicts* better than Kalshi's. 30 games joined, 17 already settled, ~14/day arriving. Needs ~440. If Pinnacle is not the better forecaster, no version of this idea can work and the thread closes for good.

**3. Weather — closed, no edge.** The model scored +0.43¢; plain climatology scored **+1.37¢** and a model that guesses 50% on everything scored **+1.01¢**. When a model that knows nothing beats yours, you have measured the gate, not a forecast. The reason: at the moment these markets open, **93% of prices are offers at 95–100¢ against a 46% actual win rate, with nobody bidding.** That is a placeholder, not a price.

**4. Crypto market making — running now, ~45 min out.** On one day it looked like +0.87¢/contract. Then shuffling away the maker/taker labels entirely scored **higher** (+1.35¢), and "just buy YES" that day scored **+3.87¢**. It was the market going up, not a maker edge. Re-running on **664 markets instead of 29**. Two of my own tooling bugs were caught on the way — including one that would have priced four million trades at zero and invented a large fake profit.

**Net: nothing here is alive except the September forecast test.**
