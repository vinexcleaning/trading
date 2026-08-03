# Paid options considered and declined

Everything below was declined per the no-paid-data rule. Cost figures are publicly
listed prices; nothing was purchased and no payment details were used anywhere.

## Kalshi historical order book / depth feed
**Cost:** ~$50–500/mo retail tiers; institutional quoted on request
(depthfeed.com, kalshibacktest.com, oddpool.com).
**What it buys:** the one thing genuinely unobtainable free — historical book depth.
Phase 0 confirmed Kalshi's API exposes only the *current* book, with no historical
depth endpoint.
**Worth it?** **The only option with a real argument, and still not yet.** It would
immediately answer the question blocking the weather thesis — is there depth at the
touch? — instead of waiting days. But our own recorder produces the same data for free;
the only cost is wall-clock time (~3 days). Buy this *after* deciding weather is worth
pursuing, not to decide whether it is.

## Kalshi per-trader position scraper
**Cost:** ~$30–50/mo (e.g. Apify Kalshi leaderboard/profile actors).
**What it buys:** leaderboard and profile data for opted-in accounts.
**Worth it?** **No.** The leaderboard is opt-in, so the population is self-selected, and
a scraper cannot see anything that is not already public. Phase 0 confirmed the public
trade feed carries **no account identifier of any kind**, so identity-level copy trading
on Kalshi is impossible at any price short of Kalshi choosing to sell it. Tonight's
Phase 6 result independently suggests wallet identity is the wrong thing to buy: the
persistent edge came from price-band exposure, not from who was trading.

## CF Benchmarks BRRNY / RTI licensed feed
**Cost:** licence-gated, quoted on request.
**What it buys:** the exact settlement index for Kalshi crypto markets at full frequency.
**Worth it?** **No, and it matters less than it looks.** Settlement is the 60-second mean
of the RTI, and three free spot venues reproduce it closely — at one instant tonight
Coinbase 63,888.00 / Kraken 63,902.30 / Bitstamp 63,891.73 against the Deribit BTC index
at 63,895.08, a spread of ~$14 on ~$64k (0.02%). Against a 3.5¢ cost bar that residual
is irrelevant. Paying to remove it buys nothing tradeable.

## Polymarket / Polygon indexer paid tier
**Cost:** $0–250/mo depending on volume.
**What it buys:** faster, higher-limit access to on-chain wallet history.
**Worth it?** **No.** The free Polymarket data API plus the existing local tape
(1.64M fills → 264,074 positions across 1,872 markets) already exceeds what tonight's
analysis consumed. The binding constraint is validation, not data volume.

## Professional economic forecast consensus (Bloomberg / Reuters survey)
**Cost:** enterprise pricing.
**What it buys:** the consensus forecast the brief hypothesises retail ignores.
**Worth it?** **No, and now moot.** Economics families are killed on recurrence, not on
forecast quality: `KXCPI` has 23 settlements and `KXFED` 22, against a 481-settlement
requirement to detect a 5pp edge. A better forecast cannot fix an unvalidatable sample.

## Paid high-resolution weather model access
**Cost:** ~$100–1,000+/mo.
**What it buys:** sub-hourly forecast updates and proprietary ensembles.
**Worth it?** **No.** The mechanism needs the *observation* channel, not a better
forecast — we want to price what the station has already recorded, and NWS/METAR
observations are free and immediate. HRRR/GFS/GEFS ensembles are free anyway.

---

## Recommendation

**Spend nothing now.** The one purchase with a genuine argument (historical Kalshi depth)
would only accelerate a question the free recorders answer in about three days, and it
should not be bought until the weather liquidity question is known to be worth answering.
If after ~3 days of recording the weather books show real depth at the touch, buying
history to extend the backtest becomes a reasonable and bounded expense — on the order of
one month's retail tier, not an institutional contract.
