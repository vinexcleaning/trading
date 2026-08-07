# HANDOFF — tennis-paper-forward

**Built 2026-08-06, desktop `C:\Users\vinig`.** Running and accumulating.
Designed to be moved to the laptop and left for a week.

---

## State: THE 50-MATCH RUN IS COMPLETE AND ANALYSED. Restarted toward 2,500.

### THE RESULT: 0 of 16 bots produced a claim that stands up

| verdict | bots |
|---|---|
| **SURVIVES** | **0** |
| UNTESTABLE | 13 |
| CANCELLED (never traded) | 3 — all three `momentum` variants |

Which is what §6 predicted in writing before the run: *"no bot survives BH, and
the modal verdict is UNDERPOWERED."*

### The five gates

| gate | result | prediction |
|---|---|---|
| **T1** machinery | **PASS.** 538 ticks, **zero** non-contiguous jumps, median 13.6 s, p95 15.2 s, **0 result leaks** | pass ✓ |
| **T2** brief coverage | ATP/WTA 87.5–100% both players, surface 100%; ITF surface **96.3%**, point-by-point **2.8%** | ITF <60% ✗ (A1), point-by-point <20% ✓ |
| **T3** cost to trade | **4.79c** = 2.67c fees + 2.12c spread, n=81 | 3.5–4.5c — **slightly under-predicted** |
| **T4** divergence | median pairwise Jaccard **0.083**; favourite vs underdog **0.000** | <0.5 ✓, favourite/underdog disjoint ✓ |
| **T5** execution gap | control (mid, zero fees) beats 9 of 12 bots by **12–23c**; n=21, CI [−25.8, +36.0] | gap larger than every edge ✓ |

**T3 is the number worth keeping.** 4.79c is *above* the 3.61c bar this repo has
been using, and it is measured rather than assumed. Every edge in the archive is
smaller than it.

**T5 caveat:** the control's picks are not identical to each bot's, so the gap
mixes execution cost with selection differences. The direction is consistent;
the level is noise at n=21.

**Spread split (exploratory):** −1.36c at ≤2c wide, −3.53c at 3–4c, −21.1c at
>8c. Losses grow with the spread — the opposite direction to the archive's fake
edges, which *grew* with it. Sanity check passes.

---

## ⚠ TWO FALSE SIGNALS THIS RUN PRODUCED, BOTH FROM MY OWN CODE

**1. Three bots reported SURVIVES on n=2.** `favourite__hold` at +16.83c with a
CI of **[16.80, 16.86]** — 0.06c wide. It had won both of its two bets, so every
bootstrap resample was positive and the interval **could not** cover zero. The
same row printed an MDE of 120.8c beside a "detected" 16.8c effect.
PREREGISTRATION §8 item 1 had predicted this exact failure before any data
existed; the code never implemented it. Fixed in amendment **A4** — and both new
guards can only turn SURVIVES into UNTESTABLE, never the reverse.

**2. Slippage looked favourable at −1.14c.** It is not price improvement: entries
are limited to ask+3c, so **208 runaway fills were refused** and never entered
the sample. The adverse tail is truncated at exactly +3c and the favourable tail
is not. Amendment **A5**. §8 item 6 said a suspiciously good number is where to
go looking for the line of code that made it — this was that line.

> Both are the same lesson as D14/D15: the run reported itself perfectly healthy
> throughout. Neither was visible in any status display.

---

## State of the machinery: BUILT, TESTED, RUNNING. Nothing is blocked.

| | |
|---|---|
| tests | **52 pass** in this package; **52 pass** across `common/` |
| live ticks | steady state **~12 s** against a 60 s poll |
| pool | ~248 markets → **~123 matches** (ATP 10 · WTA 9 · Challenger 13 · **ITF 91**) |
| bots | **16** — 5 mentalities × 3 exit modes + 1 no-trade control |
| paper positions | filling, exiting and re-entering correctly |
| settled matches | **50 of 50 reached, analysed, then restarted toward 2,500** |
| ⚠ earlier desktop data | **discarded.** Six runners shared one state file during development (D14). No conclusion was drawn from it. |
| money at risk | **none, and none is reachable** |

---

## What was built

```
src/safety.py      the only network call. GET-only, host+path allowlist,
                   refuses to start with Kalshi credentials in the environment
src/kalshi_read.py 7 tennis series; mirrored pairs deduped on TICKER ORDER;
                   tournament/round/surface parsed out of rules_primary
src/sackmann.py    ATP+WTA+Challenger+ITF history, elo, H2H, 4,845-venue
                   surface index, accent-folding name resolution
src/charting.py    point-by-point -> hold/break/after-break, WITH a matched control
src/brief.py       the pre-match brief; every rate carries its denominator
src/sizing.py      per-trade stake from confidence, with the anti-martingale guards
src/bots.py        five mentalities, three exit modes, the control, the tick loop
src/engine.py      paper fills at the ask/bid, fees from common/kalshi_fees.py
src/forward.py     the unattended runner: lock, atomic state, fsync, rotation
src/status.py      the one-command check
src/analyse.py     the pre-registered gates and the JOINT 32-way BH-FDR
deploy/            batch wrapper, Task Scheduler install/uninstall, setup guide
```

---

## Three things measured on the way that are worth keeping

### 1. Kalshi tennis markets DO carry the tournament — going forward

`SCOREBOARD.md` says surface "cannot be done backwards — no way to link Kalshi's
records to a tournament". True of settled markets. **Not true of open ones:**
`rules_primary` reads *"…in the 2026 ATP Montreal Round Of 32…"*, so tournament,
round and both surnames are all there while the market is live.

Joined to the archive's own venue→surface record, that gives **100% surface
coverage on ATP, WTA and ITF** and 84.6% on Challenger. SCOREBOARD's own note
said *"surface IS on every upcoming fixture. Start recording fixtures and this
becomes testable in about a month. Cheap."* This is that, and the recording has
started.

### 2. Being broken makes the next two games WORSE, against a matched control

From 185 charted players with ≥50 occasions of each, player-clustered bootstrap:

| after being broken, versus after a hold in the same matches | effect | CI95 | negative for |
|---|---|---|---|
| breaks back on the very next return game | **−3.33pp** | [−4.14, −2.52] | 138/185 |
| holds the next service game | **−5.55pp** | [−6.39, −4.72] | 157/185 |

The naive version — comparing against a player's all-games baseline — reads
−2.31pp and −4.03pp. **The matched control makes the effect BIGGER, not
smaller**, which is the opposite of what a confound usually does.

**Not a strategy.** It is a brief field, and the population mean is what a
player has to depart from before their own number says anything. It also has a
residual confound the control does not remove: being broken is more likely
during a stretch where the opponent is playing well.

### 3. Gross sub-100 ask sums are common on ITF, and still not tradeable

**13–16 of ~123 matches** on any given tick have both YES asks summing to under
a dollar, median **1c**. **Zero** of them beat the two-leg fee (~2.5c at those
prices).

This reproduces the archive's arbitrage result — *"52 real violations, 0 with
enough size to trade"* — on a market family it had not been measured on. It was
briefly mislabelled here as a stale-book alarm; the correct stale-book invariant
is `bid_sum > 100`, which fires on 1–2 matches per tick. GUARDS #18.

---

## Two defects found and fixed on 2026-08-07, both invisible from the outside

Worth reading before trusting any long unattended run, here or elsewhere.

**The lock was checked once at startup and never again.** Six runners were alive
at once — my fault, from deleting the lock between dev restarts — but a lock
checked once is a greeting, not a lock, and the laptop has two realistic ways to
reproduce it. Two runners share one `state.json`, and because the write is
atomic the file is **never malformed**: it is simply whichever process wrote
last, silently discarding the other's positions. Now re-asserted every tick,
with a source-level test that the check is actually *called* in the loop and a
guard-rot check that removing it fails the test. **D14.**

**The reasoning log would have destroyed itself before the run finished.** At
222 MB after 2.5 hours it was growing at 780 MB/day against a 1 GB rotation
budget — so the earliest decisions would have been rotated off the disk before
the fiftieth match settled. 93% of records were repeated passes at 3.8 KB each.
Now 40 lines/tick and ~143 MB/day, with first looks and every action still
written in full and fsynced. **D15.**

> Both were **completely invisible from the outside**: healthy ticks, correct
> counts, no alerts. The first was visible only in the process list, the second
> only in `ls -la`. GUARDS #13 in a new costume — assert the content, and the
> size of a growing file is content.

---

## Where the honest limits are

1. **50 matches decides nothing about P&L.** Under BH across the **joint 32**
   (this test's 16 plus `mlb-paper`'s 16 - see ../JOINT_MULTIPLICITY.md and
   amendment A3), the MDE is **24.2c** against a 3.6c cost bar. ~2,252 settled
   matches per bot would be needed. Pre-registered as UNTESTABLE; `analyse.py`
   leads with it. **Rule 2 binds: the two tests are reported together or
   neither is reported.**
2. **The archive stops 2026-06-01.** "Recent form" is form as of then, and gets
   one day staler per day. `staleness_days` is in every brief.
3. **No live scores.** SofaScore's `robots.txt` is 403 → UNDECIDABLE (GUARDS
   #14). So `momentum` is price momentum on our own tape, and no bot can see
   sets, games or who is serving. **This is the single largest missing
   capability.** Override is explicit: `TPF_ALLOW_UNDECIDABLE_SOURCES=1`.
4. **Sizing skill is also underpowered.** At n=50 only |r| ≥ 0.39 is detectable.
5. **73% of the pool is ITF**, so any pooled number is mostly an ITF number.
   Everything is reported split by tier.

---

## Next actions, in order

1. **Move it to the laptop** — [deploy/LAPTOP_SETUP.md](deploy/LAPTOP_SETUP.md),
   about 15 minutes. Step 6 and step 8 exist to prove the two recorders were not
   disturbed.
2. **Leave it for a week.** `deploy\check.bat` whenever you feel like it.
3. ~~At 50 settled matches~~ **DONE 2026-08-07.** `reports/results.json` holds it.
4. **Then decide whether to keep going.** Nothing about this design stops at 50
   — the target is a flag. If the T1–T5 gates come back clean, the cheapest
   useful thing is to raise `--target` and let it keep running, because the only
   thing standing between this and a real answer is sample size.

---

## Open questions this run does NOT answer

- whether any bot makes money (n)
- whether sizing by confidence helps (n)
- whether a live score feed would change any of it (D3)
- whether the `unconstrained` mentality's freedom is worth anything, or whether
  it just trades more — at handoff it was entering **~4× as often as any
  constrained bot**, which is the thing to watch first
