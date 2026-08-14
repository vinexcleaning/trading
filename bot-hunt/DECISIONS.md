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
