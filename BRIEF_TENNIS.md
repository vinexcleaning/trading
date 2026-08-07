# Tennis paper test — brief

**As of 2026-08-07.** Overwritten at the end of every session, so this is always the latest. **The 50-match run FINISHED and has been analysed.** No money was ever involved: no keys, no order-placing code, and a test fails the build if any appears.

**What it is.** **16 tennis bots** — five styles × three exit rules, plus one that only watches — reading the same live tennis matches on Kalshi, each writing down its reasoning and stake **before** knowing the result. It hit 50 finished matches in 11 hours, not the week I expected, and stopped itself. **The 32 you may see elsewhere is the COMBINED total: 16 tennis + 16 baseball**, counted as one search because you read them side by side.

**RESULT: no bot made a claim that stands up. 0 of 16.** Thirteen came back "can't tell", three never traded at all. That is what was predicted in writing before it ran.

**The one number worth keeping: it costs 4.8 cents per contract to get in and out** (2.7 fees + 2.1 the buy/sell gap). That is *higher* than the 3.6 cents this repo has been assuming, and it is measured, not estimated. **Any tennis edge smaller than 4.8 cents is unreachable**, and every edge this repo has ever found was smaller than that.

**Three bots briefly showed a "real" profit and it was false.** They had won 2 bets out of 2 — which happens 25% of the time with coin flips — and the maths reported that as near-certainty. My own written plan had predicted this exact trap and I had not built the check into the code. It is built now, and it can only ever make results stricter, never better.

**A second false signal, same shape.** The fills looked like they were coming in *better* than expected. They weren't: the system refuses any fill that moves more than 3 cents against it, so the bad fills were being thrown away and never counted. 208 of them. Good-looking number, produced by my own code.

**What went right.** 538 checks over 11 hours with no gaps, no crashes and no double-running. The five styles genuinely pick different matches, not the same ones in different hats. Player and surface data covered 90–100% of matches.

**Still open.** No live scores — the site that has them tells automated readers to stay out, so bots see prices only. Player form data stops 1 June (now 67 days stale). One style never placed a single bet in 11 hours.

**What I need from you: one decision.** Getting a real answer on profit needs about **2,250 finished matches per bot** — at the observed rate, roughly **three weeks** of continuous running, not one. I have restarted it to keep collecting. **Say if you would rather stop it here.** Otherwise the next step is moving it to the laptop so it can run undisturbed: 15 minutes, `tennis-paper-forward/deploy/LAPTOP_SETUP.md`.
