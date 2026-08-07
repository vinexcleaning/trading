# DECISIONS.md — tennis-paper-forward

Every judgment call taken without asking, with the conservative option chosen
and the reason written down. Per CLAUDE.md §2.

---

## D1 — Paper-only is enforced, not promised (2026-08-06)

**Decision:** the package cannot place an order, by construction rather than by
configuration.

Three independent layers, any one of which would be sufficient: a GET-only host
allowlist with no order path on it (`src/safety.py`); a refusal to start if any
Kalshi credential is present in the process environment; and a source-level test
that greps every file for order-shaped tokens and fails the build.

**Why not just "don't call the order endpoint":** because the live bot in this
repo already needed a `TRADING_DISABLED` kill switch bolted on after the fact,
and a kill switch is a thing that can be deleted. A package with no signing code
in it cannot be re-enabled by mistake.

---

## D2 — Latency is modelled by deferring the fill one whole tick (2026-08-06)

**Decision:** a decision made on tick *t* fills against the book observed on
tick *t+1*, and the price difference is recorded as `slippage_cents`.

**The alternative considered and rejected:** the 50–150 ms random draw plus 200
ms on taker fills, from the backtest-realism rules in `youtube-signal`. That
number is right for a millisecond tape. This runner polls once a minute, so a
synthetic millisecond draw here would be theatre laid over a much larger real
delay. Deferring a whole tick is strictly more conservative, and it is measured
rather than assumed.

**Measured on the first live run:** mean slippage −0.10c, median 0.0c, n=93.

---

## D3 — SofaScore live scores are OFF by default (2026-08-06)

**Decision:** no live score feed. `momentum` reads price momentum from this
project's own recorded Kalshi tape and nothing else.

**Why:** `www.sofascore.com/robots.txt` returns **HTTP 403** (checked
2026-08-06). GUARDS #14: a host that serves no readable `robots.txt` is
**UNDECIDABLE**, not permitted. The sibling `social-signal` session put the
principle plainly — *"a User-Agent string is not consent."*

The repo's own `kalshi-inplay-bot/sofascore_feed.py` does use it, with its own
note that *"Sofascore's terms don't invite automated collection."* That is a
decision already taken elsewhere; it is not a precedent this project inherits.

**The cost, stated rather than hidden:** without a score feed, no bot can see
the actual match state — sets, games, who is serving. `momentum` is therefore
price momentum only, and the brief's third-set and after-break fields inform
the *pre-match* read rather than a live one. This is the single largest
capability this project does not have.

**The override exists and is explicit:** `TPF_ALLOW_UNDECIDABLE_SOURCES=1`.
That is the user's call, not mine.

---

## D4 — The Match Charting Project has no LICENSE file (2026-08-06)

**Decision:** used anyway, read-only, cached locally, not redistributed.

`JeffSackmann/tennis_MatchChartingProject` returns 200 with 399 stars and
**`license: null`**. `Aneeshers/tennis-sackmann-archive` carries a LICENSE that
GitHub classifies as `NOASSERTION`.

**Reasoning:** both are public repositories whose stated purpose is
distribution of tennis data for analysis, retrieved through GitHub's own raw
endpoint, which serves no `robots.txt` (404). Nothing is republished — the
cached CSVs are gitignored. If the intent were to publish derived data, this
would need a real answer first.

---

## D5 — Surface is derived from the archive, and declines rather than guesses (2026-08-06)

**First version:** a hand-written regex table of tournament names → surface.
It resolved **100% of ATP and WTA** matches and **17.8% of ITF**, which is 73%
of everything Kalshi lists. A hand-written table was never going to enumerate
the ITF circuit.

**Decision:** build the lookup from the archive's own `tourney_name` →
`surface` record, keyed on the **venue** with the prize-money prefix stripped —
`M25 Kursumlijska Banja` and `M15 Kursumlijska Banja` are the same court.
4,845 venues indexed.

**The guard that matters:** a venue that has genuinely hosted more than one
surface (Antalya: 94.3% clay over 18,797 past matches) resolves only if
agreement is ≥80% over ≥2 events. Otherwise the brief says **unknown**, and
says why. A guessed surface is worse than a missing one: a bot can reason about
a null and cannot reason about a plausible wrong answer.

---

## D6 — Entry conviction bars were calibrated on the first live tick (2026-08-06)

**Decision:** bars set to favourite 2.0 · underdog 2.0 · brief-led 2.5 ·
momentum 2.5 · unconstrained 3.5.

**Why this is not fitting:** the first live tick's conviction *distribution* was
inspected with **zero outcome data in existence** — no match had settled, and
none could have. What was calibrated is how often each bot fires, not whether
firing pays. Three bots would otherwise have accumulated n≈0 over the whole run
and been untestable by construction; `unconstrained` was firing on 29% of the
pool and would have exhausted its bankroll every tick.

**Why it is still worth flagging:** it is the one parameter in
PREREGISTRATION.md §9 chosen after seeing live data of any kind. It is recorded
there in the same table as everything else rather than being quietly folded in.

---

## D7 — Variable sizing was accepted, with three guards (2026-08-06)

**Requested mid-build:** every bot chooses its stake from its own confidence.

**The concern, raised and overridden by the request:** this is precisely how the
live bot in this repo lost money fastest. It sized by dollars —
`qty = int(stake / price)` — so a falling price bought more contracts, and
re-entering a collapsing market martingaled automatically: 12 → 20 → 32
contracts, −$7.56 on one match in fifty minutes. Confidence-based sizing has the
same divide-by-price inside it.

**Decision:** implemented, with three guards, all pre-registered and all tested:

1. **a re-entry may never exceed the first entry's contract count.** This alone
   refuses the 12 → 20 → 32 sequence, and there is a test that asserts the
   unguarded sizer would still produce it — a guard whose failure mode cannot be
   demonstrated is not a guard.
2. total open exposure is capped at the bankroll, so a losing run shrinks its
   own sizing rather than growing it.
3. a hard per-trade ceiling in contracts and in bankroll fraction.

---

## D8 — Kelly sizes on a probability blended toward the market (2026-08-06)

**Found on the first live tick:** the archive's elo made a favourite a 95.2%
chance against an 83c ask. Full Kelly on a 12-point disagreement is 0.70, so
**every** trade pinned to the 6% cap and the stake carried no information at
all — which would have made "sizing skill" unmeasurable, since a constant cannot
correlate with anything.

**Decision:** the probability Kelly is given is
`0.35 × model + 0.65 × market`.

**Why 0.35, and why it is not a fitted number:** this repo has already measured
that a far better tennis model — 50 features, 1.5 million matches — loses the
accuracy contest to the bookmakers by +0.01922 Brier on n=2,645. A model that
loses to the market does not get to outvote it. The weight was chosen before any
outcome existed and is declared in PREREGISTRATION.md §9. It will not be tuned
against results; that is the failure this repo has recorded forty-five times.

**What it does not touch:** selection. A bot still decides *whether* to enter on
its own raw read of the brief. Only *how much* is blended. Keeping those apart
is the whole point of §5 of the pre-registration.

**Effect:** stake fraction now spans 0.5%–6.0%, median 2.9%, with 21 of 113
entries at the cap instead of all of them.

---

## D9 — Candidates are committed in order of conviction, not alphabetically (2026-08-06)

**The bug:** the first version deliberated and committed in pool order, which is
alphabetical by event ticker. A bot that exhausts its bankroll inside one tick
therefore bought whatever came first in the alphabet, and the bankroll cap fell
on the alphabetically-last ideas. That is `sorted()` doing the selection while
looking exactly like selection.

**Decision:** two phases. Everything is deliberated and logged, then entries are
ranked by conviction and queued until the money runs out. Candidates that miss
out are logged as `deferred_no_bankroll`, so the record distinguishes *did not
want it* from *wanted it and was full*.

---

## D10 — A void is its own state (2026-08-06)

**Decision:** a match that closes without a readable settlement is marked
`voided`, with `pnl_cents = None`, and is excluded from every mean.

**Why:** folding a void into a loss is a silent selection effect, and
retirements and walkovers are not rare in ITF tennis. The count is reported
beside every bot's n.

---

## D11 — The deliberation log is throttled, and what that costs (2026-08-06)

**The problem:** 16 bots × ~123 matches = 1,968 deliberations per tick at
~2 KB each is **3.3 MB per tick**, about 4.6 GB a day. That fills the laptop
inside a week and buries the decisions that matter under repetition.

**Decision:** every entry, re-entry, deferral and exit is written in full,
always, and fsynced. A **pass** is written in full on first sight of a match and
thereafter only when the verdict materially changes — a different action, or
conviction moving by ≥0.5. Unchanged repeats are counted, not written, and the
count is attached to the next record that is.

**What this preserves:** the pre-registration guarantee is untouched. Every
action and every first look is on the platter before the match finishes. What is
dropped is literal repetition.

**Measured:** 1,968 deliberations → 35 written lines on a steady-state tick.

Logs also rotate at 250 MB with four generations kept, and `analyse.py` reads
every generation — otherwise it would silently analyse the tail of the run and
report it as the whole thing.

---

## D12 — An allowlist entry was added to a shared test (2026-08-06)

`common/tests/test_no_fee_reimplementation.py` was **already failing** on
`extractor-upgrade/src/cases.py` before this project existed. The three hits are
quoted prose inside case descriptions; the module computes no fee.

**Decision:** added the allowlist entry with a written reason, which is the
mechanism that test documents for exactly this case. A repo-wide guard left red
stops being read. Flagged in STATUS.md rather than fixed silently.

---

## D13 — What was NOT built, and why

| not built | why |
|---|---|
| live match scores | D3 — `robots.txt` is 403, so UNDECIDABLE |
| an LLM in the decision loop | it must run unattended for a week on a laptop with no key and no per-decision cost. The reasoning is deliberative and fully logged; swapping in a model later needs only `Mentality.consider` |
| serve speed, aces, first-serve % as live inputs | not in any free live feed. They are in the brief as career aggregates only |
| a compounding bankroll | a fixed bankroll makes sizing skill measurable against a constant denominator. Compounding confounds it with path order |
| trading the mirror side as "sell" | Kalshi lists both sides, so buying the other market's YES is the same trade with a clean fill model. Shorting would need a second execution model for no new information |
---

## D14 — The lock is re-asserted EVERY TICK, not just at startup (2026-08-07)

**Found the hard way:** six `python.exe` entries matching this project were
alive on the dev machine at once.

**Counted correctly, that is THREE runners, not six.** A venv's
`Scripts\python.exe` on Windows is a launcher stub that re-execs the real
interpreter, so every runner shows up **twice** — a parent with 0 CPU seconds
waiting on a child that does the work. Stated because the raw count is what
`check.bat` and [deploy/LAPTOP_SETUP.md](deploy/LAPTOP_SETUP.md) steps 6 and 8
put in front of a human, and a person comparing process lists needs to know that
two lines per runner is normal.

Three is still three too many, and at least two were **actively ticking** — the
run log shows tick 168 and tick 169 written 0.1 seconds apart by different
processes, which is the concurrency proving itself.

**Cause:** me. I ran `rm -f data/.runner.lock` before each development restart,
which is exactly what the startup guard is there to prevent. The guard worked
and I bypassed it.

**But it exposed a real defect for the laptop.** A lock checked once at startup
is a greeting, not a lock. Two realistic ways a second writer gets in
afterwards:

- somebody deletes a lock they believe is stale while the owner is alive —
  and [deploy/LAPTOP_SETUP.md](deploy/LAPTOP_SETUP.md) itself tells them how,
  for the case where it genuinely is stale
- the Task Scheduler watchdog fires in a window where the lock file is briefly
  absent

Two runners then share one `state.json`. **The corruption this produces is the
worst kind, because the file is never malformed** — the write is atomic, so it
is simply whichever process wrote last, silently discarding the other's
positions. Nothing looks wrong.

**Decision:** `assert_still_own_lock()` runs at the top of every tick. If the
lock names another pid, the runner stops with a message that says the guard is
working. If the lock has vanished, it re-takes it rather than dying.
`release_lock()` now also refuses to delete a lock it does not own.

**Three tests**, including a source-level one asserting the check is actually
*called* in the run loop and that `LockLost` is handled before the generic
`except Exception` that keeps the runner alive through errors. Verified by
guard-rot: removing the call makes the test fail.

**Consequence for the data:** every paper result produced on the desktop before
2026-08-07 04:20 is discarded. Six writers shared one state file, so the
positions in it are not a coherent record of anything. The clean run starts
from zero. No conclusion had been drawn from it.

---

## D15 — The reasoning log was 5.5x too large to survive the run (2026-08-07)

**Measured after 2.5 hours:** `reasoning.jsonl` at **222 MB**, growing at
**780 MB/day**, against a 1 GB rotation budget. At that rate the earliest
decisions would have been rotated off the disk **before the run reached fifty
matches** — silently destroying the one asset this project exists to create.

**Two causes, both fixed:**

1. **The re-log trigger was too fine.** A pass was rewritten whenever conviction
   moved half a point, and conviction moves whenever the price ticks. 93% of all
   records were repeated passes. Now a pass is rewritten only when the action
   changes, when conviction crosses that mentality's entry bar, when it moves by
   ≥2.0, or on a six-hourly heartbeat.
2. **Repeated passes carried full prose.** 3.8 KB each. A repeat now writes a
   compact record — about 400 bytes — carrying which tactics fired, in which
   direction, with what weight, but not the rendered rationale.

**What is NOT throttled, and this is the pre-registration guarantee:** the first
look at every match by every bot, and every entry, re-entry, deferral and exit,
is always written in full with everything in it, and fsynced, before the result
exists.

**Result:** 141 → 40 lines/tick, 780 → ~143 MB/day, and after widening the
heartbeat to six hours a full week sits at roughly a third of the rotation
budget instead of 5.5x over it.

**The general lesson, which is GUARDS #13 wearing different clothes:** the
runner reported healthy ticks and correct counts the entire time. Nothing
alerted. The defect was only visible by looking at the size of the file.
