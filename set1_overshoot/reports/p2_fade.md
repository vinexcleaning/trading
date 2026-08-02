# The other side — fading the favourite after the dip

Phase 2 found a **significant undershoot**: the favourite wins less often than the
dipped price implies. That makes the favourite the wrong side to buy and raises the
obvious question of whether the underdog is the right one. This file answers it.

Fill is `100 - favourite_bid` plus 1c slippage — the executable NO side of the same
market, verified in `reports/p0_mirror.txt` to cost the same as the sibling market's
YES side to within 0.00c at the median.

| entry rule | n | implied | observed | mis pp | 95% CI | p(1s) | fill | fee | breakeven | net c | net 95% CI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| deep:12 | 5,390 | 0.4597 | 0.4681 | +0.84 | [-0.41, +2.09] | 0.0999 | 48.4 | 1.60 | 0.4996 | -3.148 | [-4.433, -1.887] |
| deep:30@38 | 3,436 | 0.6353 | 0.6595 | +2.42 | [+0.89, +3.92] | 0.0011 | 65.7 | 1.44 | 0.6714 | -1.195 | [-2.683, +0.281] |
| deep:20@38 | 4,188 | 0.5608 | 0.5826 | +2.18 | [+0.80, +3.59] | 0.0011 | 58.3 | 1.54 | 0.5986 | -1.598 | [-2.989, -0.196] |
| deep:25 | 4,052 | 0.5730 | 0.5982 | +2.52 | [+1.05, +3.96] | 0.0004 | 59.5 | 1.56 | 0.6109 | -1.272 | [-2.693, +0.203] |
| cp | 3,524 | 0.5568 | 0.5553 | -0.14 | [-1.59, +1.27] | 0.5841 | 57.9 | 1.41 | 0.5926 | -3.725 | [-5.181, -2.301] |
| fixed | 3,335 | 0.4825 | 0.4984 | +1.59 | [+0.06, +3.15] | 0.0258 | 50.6 | 1.53 | 0.5214 | -2.304 | [-3.859, -0.752] |

## Verdict on the fade

Best cell: **deep:30@38**, net **-1.195 c/contract**, 95% CI [-2.683, +0.281].

**0 of 6 configurations have a positive mean net expectancy. 0 of 6 have a
confidence interval entirely above zero.**

So the miscalibration is real and it does point at the underdog, but it is
smaller than the cost of taking the position in every single configuration. The
reason is arithmetic rather than bad luck. After the dip the underdog is the
*expensive* side — around 66c on the best-targeted rule — so the fee sits near
its maximum and the fill eats most of the payout. A 2.5pp edge cannot pay for a
65.8c fill plus 1c of slippage plus 1.4c of fee, which together demand a 67.2%
win rate against the 66.1% actually observed.

The best cell's interval does reach slightly above zero ([-2.683, +0.281]), which
means the data cannot rule out a very small positive expectancy there. It also
cannot rule out a loss three times that size, the point estimate is negative, and
this is the best of six cells chosen after the fact. That is not an edge; it is
the shape a null takes when you look at it from the profitable direction.

## How big would the miscalibration have to be?

| entry rule | observed underdog win rate | breakeven win rate | shortfall (pp) |
|---|---|---|---|
| deep:12 | 0.4681 | 0.4996 | -3.15 |
| deep:30@38 | 0.6595 | 0.6714 | -1.20 |
| deep:20@38 | 0.5826 | 0.5986 | -1.60 |
| deep:25 | 0.5982 | 0.6109 | -1.27 |
| cp | 0.5553 | 0.5926 | -3.72 |
| fixed | 0.4984 | 0.5214 | -2.30 |

The shortfall column is the whole study in one number: it is how many percentage
points of additional mispricing the market would have to be offering before this
trade broke even, before any profit at all.