# DECISIONS.md — bot-hunt

Conservative choices taken without asking, per CLAUDE.md §2. Each one names what
was given up.

---

### D1 — Do NOT re-run Step 2 from scratch. Extend `market-selection/` instead.
**2026-08-04.** The brief says every previous attempt derived everything from
scratch and lays out Steps 2–3 as if no market selection existed. **One does**,
dated 2026-08-02, built on the full 24 h exchange-wide tape (8,867,978 trades,
2,205 series) with a pre-registered kill gate. It is not referenced in
`STATUS.md`'s thread tables, which is presumably why the brief did not know.

Re-deriving it would have burned the session and produced a worse measurement
than the one on disk. **Given up:** an independent replication of its numbers.
Mitigated by re-verifying the load-bearing ones live (§ PRIOR_ART 4b) and by
recording forward.

### D2 — Treat dimension D as "is there a free SHARPER REFERENCE PRICE", not only
### "is there free data about the underlying thing".
**2026-08-04.** `market-selection`'s D asks for domain data and therefore scores
esports zero — its data layer really has collapsed (re-verified today: Oracle's
Elixir 404, HLTV 403, vlr 402, PandaScore 403, GRID 404).

But the only strategy in any corpus here with a public wallet and a reconciled
four-line P&L needs **no domain data at all** — it de-vigs a sharp sportsbook and
quotes that. The original D cannot see that mechanism. Both readings are kept
and reported separately rather than one replacing the other.

### D3 — Start recording before finishing the analysis.
**2026-08-04 21:27 UTC.** Pinnacle's guest API, Kalshi's book and Polymarket's
book are all live-only. Recording accrues in wall-clock time and cannot be
backfilled, so it starts the moment a source is identified, not when the
shortlist is final. **Given up:** a tidier record set — the recorder covers a
superset of what will survive Step 2, deliberately.

### D4 — Record a KNOWN-DEAD family as a negative control.
`KXHIGHNY` and `KXHIGHCHI` are in the recorder purely as a control. All 11
Kalshi weather city families measured 0% two-sided on fresh markets. If the
recorder ever reports them healthily two-sided, **the recorder is wrong, not the
market.** Cycle 1: 42% and 67% against 100% on 14 other families — the control
fires. GUARDS #4 applied to an instrument rather than to a result.

### D5 — Re-list live markets every cycle; never record from a static dump.
`market-selection`'s recorder picked tickers once and never re-listed, so
settled books read as absent counterparties. It reported NPB two-sided uptime at
27.9% where a fresh probe read 100%, and **more than half its kills were wrong.**
Costs one extra list call per series per cycle. Worth it.

### D6 — Hash every download and check its own content column.
football-data.co.uk returns HTTP 200 with the wrong country's file. Reproduced
today two ways: `COL.csv` ≡ `POL.csv` (sha `b9d1c59553b70628`, League column
"Ekstraklasa") and `KOR.csv` ≡ `NOR.csv` (sha `aa649e866b03d2ea`, "Eliteserien").
`src/probe_sources.py` prints byte-identical pairs as a named failure.
**Consequence accepted:** `KXDIMAYORGAME` (Colombia) has no free reference line
and is recorded but not cheaply testable.

### D7 — After a dimension-A probe returns a kill, re-probe with a different
### sampling rule before writing the kill down.
**2026-08-04.** Recorder cycle 1 read Polymarket esports at 11 quoted tokens of
95 and 0% two-sided, which kills the family. It was the probe: `tag_slug=esports`
ordered by 24 h volume returns mostly `acceptingOrders=false` events (96 of 156).
Per-game slugs at the same minute: `dota-2` 51 two-sided of 60 with $51,029/24 h
at a 1.0¢ spread. **Third occurrence of this failure mode in this repo, and it
fails silently and always toward a kill.** Fixed with `active=true` + per-game
slugs. Belongs in `GUARDS.md`.

### D8 — Do the historical work on the backfillable pair, not on the live-only one.
**2026-08-04.** Measured today: Pinnacle **closing** odds (`PSCH`/`PSCD`/`PSCA`
in football-data.co.uk) are 94–96% populated and current to **2026-08-03/04** for
Mexico, Argentina, Brazil and MLS, back to 2012. Kalshi's public trade tape
re-bisected today reaches **71 days, earliest 2026-05-25**. The two windows
overlap for three series Kalshi actually trades.

So Steps 4–6 run on that overlap now, rather than waiting weeks for the live
Pinnacle recorder. The live recorder keeps running because it is the only way to
get *intraday* reference prices and the only asset that cannot be recovered
later.

> ⚠ **A prior claim may be wrong and is flagged rather than corrected.**
> `market-selection/WHAT_IS_LEFT.md` calls the tape "THE DECAYING ITEM",
> retaining exactly 69 days and rolling forward one day per day, with the
> pmxt overlap "gone by 2026-08-19". It bisected the boundary to **2026-05-25**
> on 08-02. I bisect it to **2026-05-25** on 08-04. Two days of wall clock, same
> boundary — so the window **grew** from 69 to 71 days rather than rolling.
> Two points is not enough to overturn the claim; it is enough to stop treating
> the 08-19 deadline as established. **Re-bisect before acting on it.**

### D9 — No money, no order endpoints, simulated fills only.
Every call in `bot-hunt/` is public and unauthenticated. There is no
authenticated code path in `src/venues.py` by construction. Standing instruction,
recorded so it is auditable.

---

## 2026-08-06 — the de-vig test (H11)

**D10. Ran the de-vig test on MLB even though MLB was Step 6's negative
control.** Given up: the ability to use "it worked on MLB, therefore the
machinery is broken" as an error check. Taken instead: three internal placebo
controls (mismatched pair, stale reference, two-sided coherence) which run on
the same events and so cannot be separately underpowered. Why this way: MLB is
the only family that simultaneously has a joinable reference price, a stable
cost bar, and a real forward event rate. The conservative alternative — refuse
to test at all — forfeits the only runnable version of the shortlist's #1
mechanism. Control DATA is not reused; a hard 2026-08-05T00:00:00Z boundary
enforces it.

**D11. `worst_case` de-vig is primary, not the better-fitting `power`.** Given
up: statistical fit. Why: RESULTS_CROSSVENUE measured that the de-vig method
choice decides most of the apparent tail, and the one author with a reconciled
live P&L reported his Shin implementation "ran hot on favourites". A method that
manufactures the tail under test is not a neutral instrument.

**D12. Derived the game start from the ticker rather than from `close_time`.**
`close_time` on a live Kalshi MLB market is start + exactly 72 h; on a settled
one it is the real settlement instant. Given up: a field that is right for
settled markets and would have been simpler. Why: the third Kalshi time field to
mislead this repo, after Amendment A1 and LEDGER T010. Verified exact against
Pinnacle's independent `starts_utc` on 22 of 22 jointly-listed games.

**D13. Sorted the recorder's book probes by `close_time` ascending instead of
raising the 60-market cap.** Given up: coverage of the far-out games in
large families. Why: raising the cap costs API budget on the one process that
must never be starved (C018 puts the unauthenticated ceiling at 15 req/s), and a
pre-match strategy trades the games about to start. The old arbitrary ordering
left some MLB tickers with 1 snapshot in 214 cycles.

**D14. Recorded `q = 0` with its rule-of-three upper bound (0.18) and used the
UPPER bound for every timeline.** Given up: the more decisive-sounding point
estimate. Why: a point estimate of zero on n=17 is not a measurement of zero,
and every event-count in RESULTS_DEVIG.md is therefore the optimistic one.

---

## 2026-08-06 — the full-programme audit (root-level work, logged here)

**D15. Fixed T022 (non-deterministic dedupe) in `kalshi-tennis` without being
able to run it.** Given up: execution proof. `kalshi-tennis/data/` is
**laptop-only and empty on this desktop**, so the change is verified by AST parse
and an isolated determinism test, not by a real run. Why this way: the previous
behaviour was *non-deterministic* — two runs on identical data could keep
different rows — and a fixed, outcome-blind rule is strictly better than a rule
that cannot be reproduced to be audited. Every sort column is a pre-match feature
or identifier; none is outcome-derived, which is the condition GUARDS #1 exists
for. Marked "FIXED, unrun" in the ledger rather than "FIXED".

**D16. Corrected T021's severity DOWN rather than "fixing" it.** The ledger
wording ("sorts variants on mean_pnl over the full sample with no holdout") reads
like a selection step. Reading the code shows it orders only the printed table,
with Benjamini-Hochberg applied across every segment. Given up: a tidy
"defect closed" line. Why: silently changing behaviour to match a wrong
description would have been worse than correcting the description.

**D17. Did NOT rush the weather or crypto pulls to finish inside one session.**
Given up: completing task (a) in this turn. The Kalshi candlestick endpoint runs
~1.4 s per call and the irreplaceable recorder is live; C018 puts the
unauthenticated ceiling at 15 req/s and the standing rule is not to run a second
heavy puller beside the recorder. Two heavy pullers were therefore **sequenced,
not parallelised**, and the weather pull left running.

## 2026-08-14 — the recorders got a watchdog, and Bovada taught us a new failure shape

**D18. Registered both recorders with the shared watchdog, and wrote a
single-instance lock FIRST because the watchdog's safety argument requires one.**
Given up: nothing. The recorders had died four times (2.5 h, 13.6 h, 19 h, and a
machine reboot on 2026-08-12 at 06:03) and were in **neither** runner registry,
which `CLAUDE.md` §10 says leaves a job "either unwatched or unrestarted" — they
were both. `runners/install.ps1` already registers a task that fires **at startup
and every ten minutes**, so the reboot case is fixed by one registry entry and no
new code.

**But `runners/README.md` states the watchdog's entire safety case as a
precondition on the runner, not on itself:** *"Every test already holds its own
single-instance lock and refuses to start twice."* **`record.py` did not hold
one.** Registering it as-is would have silently broken that argument, and the
failure it invites has already happened here — two writers on one SQLite died
with `database is locked` inside 19 minutes. So the lock was written first,
keyed on the DATABASE rather than the process, because the two recorders write
different files and both must be allowed to run.

⚠ **One trap inside the lock, worth the line it costs:** the POSIX idiom for "is
this pid alive", `os.kill(pid, 0)`, **maps to TerminateProcess on Windows** for
any signal that is not a CTRL event. A liveness check written from muscle memory
would have killed the recorder — the one process here whose data cannot be
re-pulled at any price. It asks the kernel via `OpenProcess` instead.

**Verified rather than assumed, because inferring from a script is how eight of
the nine errors in `coordinator/REFLECT.md` happened:** the lock was tested three
ways on a throwaway database (clean start releases it; a live holder blocks the
second start **and survives it**; a dead pid's lock is taken over and says so),
and then the EU recorder was **actually killed** and the watchdog **actually
restarted it** — new process, 54 rows in its first cycle, no errors.

**D19. Did NOT restart the main recorder to give it a lock file.** Given up:
consistency between the two. It has been running since before the lock existed,
the watchdog already detects it as alive, and restarting costs a cycle of tape
against no benefit that is not already covered. It picks the lock up on its next
restart.

**D20. Backed the Bovada poller off from 5 minutes to 20 after making ourselves
the problem.** Given up: a faster answer today. See `RESULTS_RETAIL_CENSUS.md` —
after ~15 fetches in a few minutes the **control** endpoint stopped answering
too, which is the signature of us being throttled rather than of an empty board.
Polling a host that has just gone quiet, faster, is how a temporary throttle
becomes a permanent block — and a blocked host then looks exactly like a dead
route, which is the specific mistake this project keeps making.

**D21. Took the conservative option on the queue rather than waiting for an
answer.** I had asked whether to finish R1 or go straight at the newly-found
player props. No answer came, so I finished R1 — it was already built, needed no
settled games, and could only cost hours. **It died the same day.** Had I
switched to the props first, R1 would still be open and the props would have been
started on a premise (a fat margin means room) that R1 has now refuted for a
third time. **The cheap thing that can end an idea goes first.**

**D22. Did NOT write the prop de-vig pre-registration yet.** Given up: a head
start. It is a NEW IDEA under `CLAUDE.md` §2, which says a new idea gets a plan
and then a pause — and the plan is worth more after he has said whether he wants
it, because he knows things about these sports that would change what the
parameters are. **Writing it now would also make it look decided.**

## 2026-08-18 — the factory chat wants the recorder wider, and the props idea got a plan

**D23. Told the factory chat NOT to widen by adding series, and gave it the
arithmetic instead of an opinion.** The recorder is already **129% over its own
interval** (median cycle 775 s against 600 s; 156 of the last 200 overran) and
already discards **47 of every 100 markets it lists** to the 60-per-series cap —
`KXITFMATCH` sees 21% of its own board. **Adding a 21st series buys 60 probes and
costs every other series cycle time.** The lever is concurrency: at 719 requests
in 775 s we are using **0.93 requests a second against a recorded ceiling of 15**,
about 6%. Coordinated in `STATUS.md` because that is the only channel I am
allowed — mailbox writes are restricted to my own slug.

**D24. ⚠ Corrected my own disk advice inside the same hour, before anyone read
it.** I first wrote that disk limits the widening — 65.4 GB, 4.92 GB/day, ~130
days left. **Then I looked at what is in the 65 GB and it inverts the advice.**
`k_book`, the Kalshi order book, is **0.53% of all rows**. `pin_matchup` holds
**16.0 M rows each carrying a ~1,841-byte JSON blob — about 29.5 GB** — because
**11,660 Pinnacle fixtures are re-serialised every cycle** whether or not
anything changed. **Widening Kalshi ten times costs about 3 GB.** The wrong
version was replaced rather than softened, and the estimate is labelled as
sampled-not-scanned because a full scan of a 16 M-row table on a live 65 GB file
does not finish in two minutes.

**D25. Wrote `PREREGISTRATION_PROPS.md` before any number, and put the free
kill-test first.** The props reference is **intermittent** — 62 priced markets on
2026-08-14, **zero** on 2026-08-18 with the control passing. So `prop_watch.py`
measures *when* props exist before anything is priced. **If they are live for
under two hours before first pitch, Kalshi's ladder and Pinnacle's line barely
coexist, there is no window to act in, and P1 is over for free.** Same shape as
the retail test, which died on day one for the cost of two page-loads.

**D26. Added control N4, which the retail test did not need.** Kalshi quotes a
**ladder** of thresholds; Pinnacle quotes **one line**. Comparing them requires
interpolation, and **interpolation is the one step here that can manufacture an
edge out of nothing.** N4 runs the same interpolation between Kalshi's own
adjacent rungs — a venue that cannot disagree with itself. Anything it finds is
instrument, not signal.

**D27. Registered `prop_watch` in the coordinator registry only, not the
watchdog.** Given up: strict compliance with "both registries". The watchdog
restarts anything it finds stopped, which is right for a continuous recorder and
**wrong for a 48-hour job that is supposed to end** — it would restart it
forever. Same treatment as `crypto-tape-pull` and `crypto-15m-opens`, and the
reason is written into the entry so the next drift report does not read it as a
mistake.

## 2026-08-20 — totals, and the finding that came out of nearly getting one wrong

**D28. Ran the totals price-comparison before the totals model, and closed three
families in an hour.** Mailbox 021 asked for props then totals. Props were
unavailable (the board is empty overnight), so totals went first rather than
waiting — `KXMLBTOTAL`, `KXMLBF5TOTAL`, `KXMLBTEAMTOTAL`, **109 rungs, nine
games, none clearing.** Same day, same machinery, no settled game used.

**D29. ⚠ I nearly reported a 2.79¢ gap as tradeable, and catching it produced
the best result of the session.** Team totals showed Pinnacle's fattest margin
anywhere (5.44 out of 100) and the largest apparent disagreement — 2.79¢ against
a 1.68¢ fee, i.e. **above the bar.** The qualifying test said no, so I looked at
why instead of trusting the flag.

**It was not a disagreement. It was Kalshi's own spread.** Bid 32, ask 36, sharp
fair 33.21 — buying the over costs 2.79¢ over fair *and* buying the under costs
1.21¢ over fair, at the same time, which is exactly what a spread is.

**Measured across all three families: the sharp fair sits INSIDE Kalshi's
bid–ask on 76 of 109 rungs — 70 out of 100 — and the share rises with the
spread** (57% at 1¢, 68% at 2¢, 78% at 3¢). **That supersedes "the gap is too
small" as the explanation for every null in this study**, and it predicts where
the next venue-vs-venue test will fail before it is run. Recorded as **BH020**.

**What made the difference was that the arithmetic had two sides and only one
was checked.** A gap above the fee looks like a trade until you price the other
direction. **Both sides are now always printed** — that is what N2 was for, and
this is the first time it earned its place.

**D30. Corrected my own "1.7× under the bar at its worst" the same hour.** True
of game totals, false of team totals, which exceed the bar and are dead for the
different reason above. Corrected in place rather than softened.

**D31. Struck through the untested list rather than deleting from it.** §4 had
listed first-five and team totals as untested; both were tested an hour later.
They are struck through, not removed — **a list of untested things is only useful
if you can see what came off it and when.**
