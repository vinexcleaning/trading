# RESULTS — the retail bookmaker census, and a failure shape we had not met

**2026-08-13 / 2026-08-14.** Apparatus only. **No settled game is used anywhere
in this file and no edge is claimed in it.** It answers one question — *which
retail bookmakers will actually give us two-sided prices on games Kalshi trades*
— and reports one thing we learned the hard way while answering it.

---

## 1. The list

`CLAUDE.md` §9c step 1: *a blocker reported without the list of what was tried is
not a blocker.* Robots is checked **first** and is a hard gate; a book that
disallows us is recorded and **not fetched**.

| book | robots | HTTP | payload | two-sided? |
|---|---|---|---|---|
| **Bovada** | **ALLOWED** — wildcard disallow is empty | 200 | 946 KB | **467 of 467 markets** |
| MyBookie | ALLOWED | 200 | 822 KB | 395 price tokens, not parsed |
| BetUS | ALLOWED | 200 | 570 KB | 64 tokens, not parsed |
| BetOnline | ALLOWED | 200 | 345 KB | 17 tokens, not parsed |
| Bookmaker | ALLOWED | 200 | 226 KB | 54 tokens, not parsed |
| Everygame | ALLOWED | **404** | — | — |
| ESPN / DraftKings | **FORBIDDEN** — names `anthropic-ai`, disallows `/` | **not fetched** | — | — |
| the-odds-api | **FORBIDDEN** — robots unreadable, treated as no | **not fetched** | — | — |

**Coverage against Kalshi**, measured once at **2026-08-13 05:20 UTC**:

| | |
|---|---|
| Kalshi open MLB games with both clubs resolved | 22 |
| Bovada MLB events | 9 |
| overlap | **9 — every game Bovada listed** |
| of those with a two-sided Bovada moneyline | **9 of 9** |
| Bovada's margin | **4.34–4.73, median ~4.5 out of 100** |
| Pinnacle's margin, same market | **2.01** |

**The 22-versus-9 is a timing difference, not a coverage gap.** Bovada posts the
next slate; Kalshi lists days ahead.

> ### ⚠ The bug that nearly turned this into "0% — route dead"
>
> The first pass read `competitors[].description`. The field is
> **`competitors[].name`**. Every event returned `None` for both clubs — a bug
> in the reader, not a statement about Bovada — the join therefore matched
> nothing, and the write-up was one sentence from declaring the route closed.
>
> **That is the same shape as C024 and M024 — an absence manufactured by reading
> the wrong field — for the third time in one week.** It was caught by the
> arithmetic refusing to add up (9 events with 2 competitors each cannot also be
> "1 with two named clubs"), **not by being careful.**

**And the robots checker itself had a fail-open bug** on its first version: a
non-200 on `robots.txt` returned "NO ROBOTS FILE" and it then **fetched anyway**.
That mislabelled ESPN as unrestricted, when ESPN in fact names `anthropic-ai` and
disallows everything — its robots file merely 403s to us as well. **A permission
check that cannot read the permission must not conclude permission.** It now
fails closed.

---

## 2. ⚠ The new failure shape: HTTP 200 with an empty body

**2026-08-14, 05:39–06:00 UTC.** Bovada's MLB coupon answered **HTTP 200 with a
two-byte body — `[]`.** No error, no 429, no redirect, no retry header. Read at
face value that says *"Bovada lists no MLB games"*, which is one short step from
*"the retail route is dead"*.

**It was not true.** Pinnacle listed **twelve MLB games** the same second, eleven
of them starting later that day.

**The discriminator is a control endpoint on the same host in the same second:**

| Bovada coupon | bytes | events |
|---|---|---|
| `baseball/mlb` | **2** | 0 |
| `football/nfl` | 625,438 | 17 |
| `tennis` | 1,926,596 | 160 |

So the connection was fine, we were not blocked, and that one coupon was
genuinely empty at that hour.

> **The rule this is worth generalising into:** *an empty payload is evidence of
> an empty board only after a control endpoint on the same host has returned a
> full one.* Without that second call, **absence of data and absence of access
> are the same bytes** — and this project has now manufactured three false
> absences by not making it.

**Then we became the problem.** After roughly fifteen fetches in a few minutes
the **control** endpoint stopped answering too. That is our own throttle, not
Bovada's board — so the poller was backed off from 5 minutes to 20. Polling a
host that has just gone quiet, faster, is how a temporary throttle becomes a
permanent block, and a blocked host looks exactly like a dead route.

---

## 3. What is running, and what it will answer

`src/retail_n3.py` waits for Bovada's MLB board to populate and then runs
**R1's N3 arm on day one** — the measurement `PREREGISTRATION_RETAIL.md` §7 names
as the reason to run R1 at all:

> *"Bovada disagreeing with Pinnacle by more than the cost bar on the same games
> … measurable on day one, before any settlement."*

**No settled outcome is used, so nothing in it can be a result-dependent
choice.** It strips each book's own margin three ways — proportional, power and
Shin, with Shin solved numerically rather than from a remembered closed form —
and compares the two fair values against the fee at Kalshi's live ask.

**Both outcomes are useful, which is what makes it worth running:**

- **If the two books land inside the cost bar of each other**, Bovada's fat
  margin is just a fat margin — the retail book charging more for the same
  opinion — and **R1 cannot work however many games accrue.** That kills it
  before a fortnight of accrual, which is `PREREGISTRATION_RETAIL.md` §6's point.
- **If they disagree by more than the bar**, the retail book carries information
  the sharp one does not, and R1 is worth its full run.

**Expected, and recorded before the answer exists:** the first. Kalshi has been
measured tracking Pinnacle to within **2.77¢** on this exact market —
`RESULTS_DEVIG_WHERE.md`, **1,460 paired readings across 30 MLB games, taken
between 2026-08-05 and 2026-08-11**, largest disagreement 2.77¢ against a 2.75¢
cost bar. A loose retail book does not make Kalshi loose.

⚠ **One snapshot on 9–11 games is a LOOK, not a conclusion** (`CLAUDE.md` §9c
step 7). A single reading that clears the bar would justify running R1 properly.
It would not be a finding.

---

## 4. What this did NOT test

`CLAUDE.md` §9c step 7. Nothing here is a negative result yet, but the list is
written now so that it exists before one arrives — a dead idea with no such list
looks completely dead, and this repo has already killed a live idea that way.

**Not tested, and each is a live way this could still work:**

- **The four other bookmakers that answered and permit us.** MyBookie, BetUS,
  BetOnline and Bookmaker returned 226 KB–822 KB of HTML each and **were never
  parsed** — only Bovada has a reader. Between them they may quote games Bovada
  does not, and they may disagree with each other, which is itself a signal.
- **Every market except the moneyline.** Bovada's 467 two-sided markets include
  totals, run lines, spreads and three-way books. Only the plain
  who-wins-the-game price is being compared, because that is the one Kalshi
  quotes — but Kalshi's board is not only game winners.
- **Any sport except baseball.** Bovada's tennis coupon returned 1.9 MB and 160
  events in the same minute the baseball one was empty. Tennis is the family
  with 16 bots already running against it.
- **Any hour except one.** The coverage figures are a **single reading at
  05:20 UTC on 2026-08-13**. A retail book's board changes shape through the
  day, and a slate measured at 1 a.m. is measured at its thinnest.
- **How long a disagreement survives.** Even a real gap is worthless if it closes
  before it can be traded. Nothing here measures persistence.
- **Depth at the price.** Neither what Bovada would actually accept, nor what
  size sits at Kalshi's ask.
