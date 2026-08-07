# Tennis paper test — brief

**As of 2026-08-07.** This file is overwritten at the end of every session, so what you are reading is always the latest. Nothing below is older than the date on this line.

**No money can be touched.** There are no keys and no order-placing code anywhere in it, and a test fails the build if any appears.

**What it is.** **16 tennis bots** — five styles × three exit rules, plus one that only watches and never buys — all reading the same live tennis matches on Kalshi. Every bot writes down its reasoning and how much it would stake **before** it knows the result. It is running now and needs about a week to reach 50 finished matches.

**About the 32: that is the COMBINED total, 16 tennis + 16 baseball.** A separate session built a matching baseball test. Because you will read the two side by side, they count as one search of 32 rather than two searches of 16. That makes the bar for claiming anything stricter, which is the whole point of doing it.

**What 50 matches CAN answer:** what it really costs to get in and out of this market, whether the five styles actually pick different matches or are the same bot in five hats, and whether the thing survives a week alone on a laptop.

**What it CANNOT answer: whether any bot makes money.** That is not caution, it is arithmetic. With 50 matches we could only detect an edge of about 24 cents per contract, and trading costs about 3.6 cents. Getting a real answer needs roughly **2,250 finished matches per bot**. Any profit figure before then is noise wearing a number.

**Still open.** No live scores — the site that has them tells automated readers to stay out, so no bot can see the score, only the price. Player history stops on 1 June, so anything called "recent form" is ten weeks old and ageing. Three quarters of the matches are the lowest tier, so most numbers will mostly describe that tier.

**Two bugs found and fixed, both of which looked perfectly healthy from the outside.** Three copies were running at once and silently overwriting each other's results; and the reasoning log was growing fast enough to delete its own earliest records before the test could finish. Neither showed up in any status display — they were only visible in the process list and the file size.

**What I need from you:** nothing yet. When you want it on the laptop it is about 15 minutes: `tennis-paper-forward/deploy/LAPTOP_SETUP.md`. Two of its steps exist purely to prove your two recorders were not disturbed.
