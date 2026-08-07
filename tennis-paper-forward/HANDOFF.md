# HANDOFF — tennis-paper-forward

**Built 2026-08-06, desktop `C:\Users\vinig`.** Running and accumulating.
Designed to be moved to the laptop and left for a week.

---

## State: BUILT, TESTED, RUNNING. Nothing is blocked.

| | |
|---|---|
| tests | **49 pass** in this package; **52 pass** across `common/` |
| live ticks | steady state **~12 s** against a 60 s poll |
| pool | ~248 markets → **~123 matches** (ATP 10 · WTA 9 · Challenger 13 · **ITF 91**) |
| bots | **16** — 5 mentalities × 3 exit modes + 1 no-trade control |
| paper positions | filling, exiting and re-entering correctly |
| settled matches | **0 of 50** — nothing had settled yet at handoff |
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
src/analyse.py     the pre-registered gates and the 16-way BH-FDR
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

## Where the honest limits are

1. **50 matches decides nothing about P&L.** Under BH across 16, the MDE is
   **22.8c** against a 3.6c cost bar. ~2,000 settled matches per bot would be
   needed. Pre-registered as UNTESTABLE; `analyse.py` leads with it.
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
3. **At 50 settled matches** the runner stops itself. Run `-m src.analyse` and
   read PREREGISTRATION.md §3 before §6.
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
