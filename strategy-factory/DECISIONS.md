# DECISIONS — strategy-factory

Every judgment call taken instead of asking, with **the conservative option I
rejected**, so any of them can be reversed by someone who disagrees.
`CLAUDE.md` section 2: take the conservative option, log it, keep going.

Newest at the bottom. Nothing here is deleted; a reversed decision gets a
follow-up entry saying so.

---

## D1 — 2026-08-18 — The folder is `strategy-factory/` and nothing else is touched

**Decision.** All work lives in `strategy-factory/`. `bot-hunt/` is read and
never written. `livedesk/` is not opened at all.

**Rejected.** Adding the new series to `bot-hunt/src/record.py`'s
`KALSHI_SERIES`, which is the obvious one-line change and would have been
faster.

**Why.** `bot-hunt` belongs to the `devig` chat and its recorder holds the 62 GB
tape that is the best asset in this repo. That file already documents a second
recorder process dying inside 19 minutes with `database is locked`, and the fix
was a separate database file rather than a longer timeout, "because a timeout
only has to be wrong once, and the thing it kills is the process whose data
cannot be re-pulled at any price." Editing the running recorder's series list
would restart it. The factory writes `strategy-factory/data/wide.db` and shares
nothing.

---

## D2 — 2026-08-18 — The factory IMPORTS `bot-hunt/src/venues.py` rather than copying it

**Decision.** `census.py`, `shape.py` and `wide.py` put `bot-hunt/src` on
`sys.path` and `import venues`. No HTTP client is written in this folder.

**Rejected.** A self-contained client in `strategy-factory/src/`, which would
have made the folder independent and satisfied "work only inside your own
folder" more literally.

**Why.** `venues.py` encodes four traps that each cost a prior session real
time: the `*_dollars` field names, `orderbook_fp` as the single top-level key,
both Kalshi sides being quoted as bids, and the pacing that keeps this under
Kalshi's unauthenticated limit. A copy would drift away from all four, and the
fee formula reaching 17 copies is exactly what happens when this repo copies
shared code. Reading another chat's module is not writing to its folder.

**The cost, and how it is paid.** A paper-only test that walks only
`strategy-factory/src` would certify a package whose actual network code it
never read. So `tests/test_paper_only.py` was extended to scan
`bot-hunt/src/venues.py` too, and to FAIL if that file is missing rather than
passing on an empty scan.

---

## D3 — 2026-08-18 — Tier B reads the LIST endpoint, not the orderbook endpoint

**Decision.** Wide coverage is recorded from `/markets`'s `yes_bid_dollars` /
`yes_ask_dollars` / `yes_bid_size_fp` / `yes_ask_size_fp`, one request per
series. Full ladders are walked only on tier A.

**Rejected.** Walking the orderbook on every market, which is what
`bot-hunt/src/record.py` does and is unambiguously the higher-quality read.

**Why.** It is not affordable. 835,422 open markets at roughly 0.35 s per
orderbook request is **81 hours for a single pass.** The list endpoint returns
1,000 quotes per request.

**And it was checked, not assumed.** `venues.py`'s own docstring says "Kalshi
list endpoints null out bid/ask". `src/verify_list_quotes.py` measured it on
168 markets across 23 categories: **100% of bids and 94% of asks agreed with
the per-market orderbook within one tick**, and there was not a single case of
the list being blank while the book was quoted. The 6% are one-tick moves
between two requests made 200 ms apart in live markets, plus the two parlay
families where the list quote is stale against an empty book. The docstring is
stale; the finding is in `reports/RESULT_LIST_QUOTES.md` and has been filed to
`devig`, whose folder that file lives in.

**What tier B therefore cannot answer.** Anything needing depth: capacity,
book shape, walking $500 into a thin market. That is precisely what tier A is
for, and no analysis may mix the two — the `src` column on every `w_top` row
records which endpoint it came from.

---

## D4 — 2026-08-18 — Change-only writes, with a forced heartbeat

**Decision.** A tier B row is written only when the quote changed from the last
one recorded for that ticker, plus a full snapshot every 12th cycle.

**Rejected.** Writing every row every cycle, which is simpler and makes the
tape trivially uniform.

**Why.** Disk is named in `STRATEGY_FACTORY.md` as the most likely thing to
actually break. Most Kalshi markets do not move for hours.

**The failure mode it creates, and the two things that stop it.** "Nothing
changed" and "the recorder was down" look identical in a change log. So every
cycle writes a `w_cycle` row whether or not anything changed — gaps in the tape
are explicit and countable — and every 12th cycle writes every row regardless.
GUARDS #12 is why: a parse bug wrote real row counts with empty content for
1h45m and was caught by accident.

**A third failure it also had to fix.** The recorder seeds its change detector
from the tape on startup. Without that, a watchdog restarting it every ten
minutes would write a full snapshot every ten minutes and the rule would
quietly stop saving anything — a saving that silently stops is worse than one
that was never claimed.

---

## D5 — 2026-08-18 — The two parlay families are dropped by name as well as by measurement

**Decision.** `KXMVECROSSCATEGORY` and `KXMVESPORTSMULTIGAMEEXTENDED` are
excluded from the recorder.

**Rejected.** Letting the quote measurement decide alone, which is the more
principled rule and the one applied to every other family.

**Why.** They are **751,943 of the exchange's 835,422 open markets** — 90% —
and are combinatorial multi-leg products. A single quoted leg would drag all
614,573 markets of one family into the recorder and consume the whole disk
budget. The measurement already drops them; the name check is a second lock so
that a single stray quote cannot undo it.

**Recorded as a real cost, not waved away.** If a strategy is ever written for
parlay pricing, this decision is what blocks it, and it is a one-line change to
reverse. The drop list in `reports/TIERS.md` names them with their counts for
exactly that reason.

---

## D6 — 2026-08-18 — The best-of-N table was re-derived, and it disagrees with the plan

**Decision.** `src/bestofn.py` recomputes the null in this folder, by two
independent methods (simulation and an exact binomial tail), on the real fee
function. Where it disagrees with `coordinator/STRATEGY_FACTORY.md`, this
folder uses its own number and says so.

**Rejected.** Quoting the coordinator's table, which is what the plan expects
and which agrees with mine on the column that matters most.

**Why, and what the disagreement is.** The "typical best" column reproduces
almost exactly (10.0 vs 10.1, 18.0 vs 17.9, 26.0 vs 25.6, 30.0 vs 29.5). The
"reaches +30%" column does not:

| | plan says | measured here |
|---|---|---|
| ONE zero-skill strategy reaches +30% over 100 bets | 1 in 10,000 | **1 in 2,289** |
| best of 2,000 zero-skill strategies reaches +30% | 37 in 100 | **58 in 100** |

The plan's number can only be reproduced by charging the fee **twice** — on
entry and again on exit. `common/kalshi_fees.py` says in
`roundtrip_cost_cents` that "exit_cents=None means held to settlement, which
pays the entry fee only", and Kalshi charges nothing at settlement. For a
buy-and-hold strategy, which is the default shape in this repo, the fee is paid
once.

**Which way it moves the argument: the dangerous way.** The best-of-N hazard is
roughly **four times larger** than the plan states. This does not weaken the
plan's conclusion — it strengthens it — but a number this load-bearing being
wrong in the safe-looking direction is worth a ledger row, and it gets one.

I have not tried to reconstruct exactly what the coordinator's simulation did,
and I am not claiming to know. I am reporting what this folder measured, twice,
by two methods that agree with each other.

### ⚠ D6 CORRECTED 2026-08-19 — my correction was wrong too, and my diagnosis was worse

`coordinator` mailbox 002 did the arithmetic exactly and I reproduced it before
accepting it. **The exact answer is 1 in 4,893 and 34 in 100.** Mine said 1 in
2,289 and 58 in 100; the plan said 1 in 10,000 and 37 in 100. Everyone was
wrong once.

**The error is the DENOMINATOR, and it is one line.** Buying a contract at 50
cents takes **52 cents** out of the account — the price *and* the fee. So "+30%"
means turning 52 into 67.6, which needs **68** wins of 100. I divided by the 50
cents of contract price instead, which needs 67. **One win of difference halves
the answer.** Theirs is the right definition: the user means "I turned $100 into
$130", and $100 is what left his account. Checked at 1, 5, 20 and 100 contracts
per order — the per-order fee rounding does not move the threshold.

**And the part I got more wrong than the number.** I wrote that the plan's
figure "can only be reproduced by charging the fee twice", because charging it
twice gives 1 in 10,920 — very close to their 1 in 10,000. **It was not what
happened.** Their figure was a Monte Carlo estimate off **two hits in 20,000
runs**. I found *a* way to reproduce a number and asserted it was *the* way, and
the closeness of the match is exactly what made it persuasive. That is the
repo's recorded failure mode — read one source, conclude — wearing the costume
of a verification.

**What survives, and one thing is better than before:** the user's own claim is
**right at the true number**. A single pre-specified strategy showing +30% over
100 bets happens 1 time in 4,893, so it really is not luck. The whole danger
sits in the selection — best of 2,000 gets there 34 times in 100 — which is
precisely the thing the forward test exists to strip out.

**One concrete change to how this folder works, taken from their diagnosis
rather than mine:** `bestofn.py` now prints the **hit count** next to every
simulated tail probability and says out loud when the count is too small to
trust. Both wrong versions of this number survived because a rate was written
down without the count behind it.

---

## D7 — 2026-08-18 — `python` is `py -3`, and this folder has no virtual environment

**Decision.** Everything runs on `py -3`. No `.venv` was created.

**Rejected.** A `.venv`, which the session prompt suggested and which eight
folders here have.

**Why.** The only third-party import on the whole path is `requests`, which
`py -3` already has — `bot-hunt`'s `venues.py` needs nothing else, and every
other import is standard library. A virtual environment that adds nothing is
one more thing that can be the wrong interpreter later, and this repo already
has a document sending a reader to a Python path on a machine that is no longer
the primary one. If a dependency ever appears, a `.venv` gets created then and
this entry gets its reversal note.

### ⚠ D7 REVERSED, same day, for a reason I had not looked at

**`runners/runners.json` takes an `exe` field described as "interpreter,
relative to dir", and every existing entry is `.venv\Scripts\python.exe`.**
There is no way to register a runner as `py -3`, and the alternative —
hard-coding an absolute interpreter path — is forbidden by `CLAUDE.md`
section 10 for a reason this repo has already paid: `wallet-copy-study`'s
handoff names a Python path on a machine that is no longer the primary one, and
following it fails.

The shared watchdog is the thing that prevents the failure `devig` describes
in `STATUS.md`: four recorder deaths, the last **19 hours** after a reboot, on
data that cannot be re-pulled at any price. **A recorder that the watchdog
cannot restart is the whole risk this project is supposed to avoid.**

So `strategy-factory/.venv` now exists, created with `--system-site-packages`
so that `requests` comes from the existing install and nothing is downloaded.
`strategy-factory\.venv\Scripts\python.exe -m pytest strategy-factory/tests -q`
passes — 15 tests — which is also what the registry's `verify` field runs
before it will install anything.

**The original reasoning was not wrong; it was answering the wrong question.**
"Do I need a venv for my dependencies" is no. "Do I need one for the watchdog
to be able to restart my recorder" is yes, and that is the question that
mattered.
