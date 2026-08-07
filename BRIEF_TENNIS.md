# Tennis paper test — brief

**As of 2026-08-07 (evening).** Overwritten at the end of every session, so this is always the latest. Still collecting, now past 106 finished matches on the way to a target of 2,500. No money is involved: no keys, no order-placing code, and a test fails the build if any appears. **It calls no AI model — it is plain arithmetic, and running it costs nothing.**

**Job 1 — refresh the stale player data. Done, with a real limit.** The free Sackmann mirror **cannot be refreshed: it is frozen.** I re-downloaded every 2026 file and compared them byte for byte against what we already had — identical, and the original source is still deleted. So I found the one free source that *is* current, tennis-data.co.uk, which publishes weekly and permits this in its own robots file. **Player form went from 67 days stale to 4**, with 938 of 984 new results merged.

**The catch, stated plainly: that source covers the main tour only.** Challenger and lower-tier events are **87% of the matches Kalshi actually lists**, and no free current source covers them. So this fixes form for about **one match in eight**. The rest is exactly as stale as it was.

**Along the way I found the name matching was quietly dropping 3 in 10 results** — and dropping them hardest for the *best-known* players, because of hyphens (Auger-Aliassime), two-word surnames (De Minaur) and double initials (Cerundolo J.M.). Fixed; misses are now 3–6%. Where two players genuinely share a surname and initial it refuses to guess.

**Job 2 — the style that placed zero bets. It is a BUG, not correct caution, and it could never have traded.** Over 13,089 decisions its best score was 1.90 against a threshold of 2.50. Its maximum *possible* score was 1.88. **No market condition could have made it buy anything.**

**The cause:** it was being penalised for the player-history data being old — but that style ignores player history entirely. It trades price movement on our own recorded prices. It was being charged for something it never uses. Fixed: it has now placed **24 bets**, and it still correctly refuses moves too small to cover the cost of trading.

**What that cost us:** three of the sixteen bots contributed nothing to the first 50-match run while still counting toward the statistical bar — so the test was harder to pass than the search actually justified. Conservative direction, but not deliberate.

**What I need from you: nothing.** It is running with both fixes. Two things to know: the profit question still needs about 2,250 matches per bot (roughly three weeks), and moving it to the laptop takes 15 minutes whenever you want it off your desktop — `tennis-paper-forward/deploy/LAPTOP_SETUP.md`.
