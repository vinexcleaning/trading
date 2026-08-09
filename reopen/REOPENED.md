# REOPENED.md — which closed threads died on evidence, and which died on something else

**As of 2026-08-08.** Written by the `reopen` chat, from mailbox message 001.
**Corrected 2026-08-09 — see [the corrections](#corrections-2026-08-09-the-first-three-reopens-were-worked-and-two-of-them-shrank) at the foot of this file. Three of the thirteen changed, and two of them shrank.**

**The job:** the user said *"I've been feeling that there's some stuff that we
closed for the wrong reason."* This reads every claim in every ledger and sorts
the ones that stopped a line of work into two piles — closed properly, and
closed for some other reason.

**This chat re-ran nothing and measured nothing new.** It audits closures. Where
a thread should be reopened, the work belongs to the chat that owns that folder,
and a message has been left in that chat's mailbox.

---

## The headline, and it is mostly good news

| | |
|---|---|
| Claims read | **313** (342 table rows; 29 appear twice because the retraction summary repeats them) |
| Of those, claims that actually **closed** a line of work | **82** |
| **Closed properly — measured, big enough sample, leave it alone** | **53 of 82** |
| Closed for some other reason | **29 of 82** |
| Of those 29, needing a **test re-run** | **13** |
| Of those 29, needing only a **sentence rewritten** | **16** |

The other **231** claims are not closures at all. They are facts about how the
exchange works, safety checks, corrections, positive findings, and things openly
marked unfinished. There is nothing in them to reopen, and counting them as
"closed correctly" would have flattered this audit by three times.

**Two thirds of the real closures were done properly, and several of them are
better than most published work.** The crypto price test ran a fake-data control
first to prove the machinery could find a fake edge before reporting that it
found no real one. The tennis trait study used 3.4 million rows with both a
positive check and a deliberate dud. The copy-trading kill was measured on a
period the selection never touched. **Do not go back to those.**

**But the 29 are real, and one pattern runs through them.** The commonest way a
thread died here was not a wrong measurement. It was a **right measurement
written up in a sentence bigger than itself** — "no effect" where the honest
sentence is "this test was too small to see the thing we are looking for", or
"the data does not exist" where the true sentence is "the two places I looked
did not have it".

---

## The four ways a thread died for the wrong reason, with counts

| # | How it died | Count | The worked example |
|---|---|---|---|
| 4 | **A test too small to find what it says is absent** | **9** | Tennis set-1 margin buckets (479 matches, 25 May–26 Jul 2026): the write-up says no bucket beats the cost. The same row says the smallest thing that test could have spotted was about **10 cents** — and the thing being looked for was **2 cents**. |
| 3 | **One version tested, whole idea declared dead** | **8** | "The ITF tier cannot be modelled" was measured on one data provider's files and is quoted as if it were about ITF. |
| 2 | **The data "wasn't available"** | **7** | "No free source covering ITF tennis was found", 2026-08-02, six places checked. A seventh had it, free, on 2026-08-06 — 7,786 ITF tournaments. |
| 1 | **A script was wrong and the conclusion followed the bug** | **5** | Two tennis results were computed on an event set a later bug report voided, and neither has been re-run since. |

---

## THE TABLE — ordered by how much it would cost to be wrong

| claim | what closed it | which of the four | what would settle it | how long |
|---|---|---|---|---|
| **M027** — "no free data source covering ITF tennis" | Six sources probed on 2026-08-02, all dead ends. Recorded as **settled**. | **2 — data** | Nothing to run. **B021 already refuted it on 2026-08-06** with a free key returning 7,786 ITF tournaments. But `market-selection/SHORTLIST.md` still gives this as the reason the exchange's **highest-volume tennis family** gets no entry, and the sub-ledger still says settled. The shortlist decision has to be made again. | an afternoon |
| **C022** — crypto market making | Recorded in the main ledger as **settled, no edge**, citing a file whose own verdict section reads *"Not yet reached"*. | **4 — too small**, and **1 — a bug** before that | The project's later file (`crypto/MM_RESULTS_MAKER.md`, 2026-08-07, 658 events over 8 days ending 2026-07-31) says the cost of being the passive side is about **half a cent** against a gross margin of about **one cent**, and *"the question is not settled against market making, it is unresolved"*. **73 days** of tape are retrievable against the 8 used. Pull them and re-run. | one paced pull, one re-run |
| **S023** — "the fade side loses in every configuration" | A dedupe bug voided the event set underneath it. Marked broken, **never re-run**. | **1 — a bug** | Re-run it on the fixed dedupe. Half of the sentence *"tennis set-1: no edge in either direction"* currently rests on arithmetic that was expected rather than measured. ⚠ **2026-08-09: this is blocked on the LAPTOP, not on the tennis chat.** `set1_overshoot/data` does not exist on this desktop and the recorder is registered as "nobody has ever confirmed this is running". | one re-run, **on the laptop** |
| **C023** — hold a crypto contract to settlement | Recorded in the ledger with the single word **"negative"**. | **4 — too small** | I opened the committed output (`crypto/reports/hold_settle.txt`, 25 May–30 Jul 2026, four assets, 146–250 events each) rather than the row. It says **tie** in 40 of its 44 price cells, with ranges of plus-or-minus 5 to 15 cents against a cost of 1 to 2 cents. Bitcoin at 5 cents reads **+2.9 cents**, its bottom edge one hundredth of a cent below zero. That is not a negative result; it is an unmeasured one. Same tape pull as C022 fixes it. | shares C022's pull |
| **S021** — "the tennis line cannot be resolved with the sample available" | An honest power statement, written **2026-08-01**. | **4 — too small** | ⚠⚠ **WORKED 2026-08-09 AND WITHDRAWN AS A REOPEN — see the corrections at the foot of this file.** The two numbers are in different units (354 qualifying events a week, not 1,900), and more data cannot help anyway: the effect is **2.42 out of 100** against a cost of **3.61 out of 100**. The bucket version needs **61 weeks** of recording. ~~Count what has accrued and re-run if it clears.~~ **S018 is the tennis item that matters, not this.** | ~~one count~~ **pointless by arithmetic** |
| **T002 / B023** — the player-model data window | Features from one provider stop at 2026-06-02 and 85% of markets are after that; the player-feature sweep then returned nothing on **29 days** of form, where the typical player appears about three times. | **2 — data**, feeding **4 — too small** | **$9.99** buys 43 months of point-by-point history including ITF. It replaces the frozen source and re-powers the sweep in the same purchase. Already named in the 2026-08-06 audit and not bought. | $9.99 and one rebuild |
| **S018** — "match label coverage cannot be raised" | Two sources: one paid tier's cap, one site's 7-day window. | **2 — data** | **PROMOTED to the first tennis item**, because S006's floor is bound by label coverage rather than by elapsed time. ⚠ **2026-08-09: this is the SAME $9.99 as T002** — `livetennisapi`'s history plan covers January 2023 to July 2026, point-by-point, including ITF. One purchase, three answers. | **$9.99, shared with T002** |
| **M017** — Colombian, Peruvian, Korean and Chilean closing lines | One site serves a **wrong-country file** under those codes — Colombia returns Poland. | **2 — data** | ⚠⚠ **WITHDRAWN 2026-08-09.** `soccer/data-sources.md` had already probed **thirteen** sources with content hashes and reached a better-evidenced version of the same absence: Colombia has no free closing line, Peru/Ecuador/Uruguay 404. ~~Probe others.~~ **I flagged this without reading the folder whose whole job that week was this question — because that folder has no ledger rows and this audit read ledgers.** | **already done** |
| **S022** — the retirement add-back cost | Same void event set as S023. Marked broken, never re-run. | **1 — a bug** | One re-run. Small, and unlikely to move anything. | one re-run |
| **BH014** — the recorder read the first 60 tickers | It probed 60 tickers in an **undocumented server order** while the family listed 85 to 104. Fixed 2026-08-06. | **1 — a bug** | ⚠ **WORKED 2026-08-09 AND MOSTLY CLEARED.** I guessed the de-vig cost bar read that output; it does not — the bar is fee plus slippage with **no spread term**, so the "de-vig is not reachable on MLB" conclusion is untouched. What remains is one re-measurement: the **2.0¢ median / 7.0¢ p90** spread figures came from cycles where some tickers got as few as **1** snapshot, server-chosen. | **drops to a re-measurement** |
| **C016** — "the cheap wings are not tradeable" | **61 minutes** of one price ladder on one day. | **3 — one version** | ⚠ **DOWNGRADED TO A RELABEL 2026-08-09.** `MORNING_REPORT.md` §0000 already carries a *"Refinement, so this is not overstated"* paragraph confining it to the far wings, and the conclusion is reached independently by the C6 withdrawal. ~~Re-check across many days.~~ The row just needs to say "one event's final hour". | **minutes** |
| **M025** — Kalshi versus DraftKings on player props | One free feed publishes prop prices **one side only**, so the comparison was **cancelled as unanswerable**. | **2 — data** | ⚠⚠ **WORKED 2026-08-09 — THE ABSENCE CLAIM IS FALSE.** `bot-hunt/reports/pinnacle_probe.json`, committed since 2026-08-04, holds a free unauthenticated **two-sided** MLB player prop: *Justin Foscue Total Bases*, Over 0.5 at −125, Under 0.5 at −106, max stake $500. **But read the caveat at the foot of this file** — the overround is **7.0 out of 100** against 2.01 on the moneyline, and it is one prop. | the compare is a real job |
| **CH074** — set-score and parlay markets | Closed by an **arithmetic argument** and one worked example. | **3 — one version** | ⚠ **WORKED 2026-08-09 — BLOCKED, for a different reason than the one on file.** The series exists (**`KXATPTOTALSETS`, "ATP Total Sets"**) and returns **0 markets, open or settled**, while `KXATPMATCH` returns 10 open and 200+ settled on the same query. The test needs a market that has been minted zero times in the window. | **not runnable today** |

### Sixteen more that need a sentence rewritten, not a test re-run

These are rows where the measurement is fine (or cannot be improved) and the
**wording** is what will mislead the next reader. Full list with the exact
correction is in [reports/classification.csv](reports/classification.csv), rows
marked `RELABEL`.

The four that matter most:

- **S005 and S006** — two tennis nulls that print their own detectable-effect
  range in the same row that calls them settled. The range is 2 to 5 times the
  effect being hunted. The honest status is *unmeasured at this sample*.
- **M011** — "Kalshi's baseball line already tracks the free bookmaker line" is
  **13 games, one snapshot, against a retail book**. One pre-registration was
  corrected on 2026-08-06 to say so. Its sibling, `bot-hunt/PREREGISTRATION.md`,
  still calls baseball *"known efficient"* on it with no caveat, and that is the
  file that makes baseball the negative control.
- **M009 and M010** — the "trade tape keeps exactly 69 days and rolls daily"
  claim, and the 2026-08-19 deadline that follows from it. **BH009 refuted both
  on 2026-08-06** — the boundary is a fixed date and has not moved across three
  measurements. The main ledger carries the retraction; `market-selection`'s own
  ledger still says settled, and that is the file someone will open.
- **K012** — "economics markets are killed on recurrence" means *we can never
  gather enough of them to measure anything*. It reads as *there is no edge
  there*. Those are opposite sentences.

---

## What I could NOT check, and it is a real hole

**Three folders have no claims in any ledger, so none of their closures appear
in the 313 above and this audit cannot see them:**

| folder | results documents nobody has ledgered |
|---|---|
| `soccer` | `dataset.md`, `inplay_events.md`, `WHAT_IS_LEFT.md` |
| `polymarket-tennis-copy` | `docs/FINDINGS.md` |
| `ptis-polymarket` | `outputs/*_REPORT.md` |

The 2026-08-06 audit named this and it is still true for these three. **Its own
record is that ledgering a project that had never been ledgered turned up a
verdict-relevant defect on two out of two attempts** — and adding a third
project since then made that three out of three. So the expected value of
ledgering these is not low.

**One more, and it is separate from everything above:** at least three threads
did not die of a wrong conclusion. **They died of no conclusion.** The Discord
signal work was rated by the user as his most promising thread and was **never
tested for edge at all**. The "sell after a 10% gain" question was asked and the
answer is literally missing from the export. Two tennis patterns that cannot
both be an edge were flagged as testable and never tested. Those are not
reopens — they were never opened.

---

## What this audit did NOT test

Required by `CLAUDE.md` §9c step 7, because a negative result with no list of
untested versions looks completely dead.

1. **I read the ledgers, not the code.** Where a row summarises a script, I
   opened the script's committed output for the four claims that decided this
   report and took the rest on the row's own word. A wrong number that was
   written down consistently is invisible to me.
2. **I re-ran nothing.** Every "would settle it" above is a proposal, not a
   result.
3. **I did not audit the guards, the fee module, or the pre-registrations** —
   the 2026-08-06 audit covered those and found them clean.
4. **I did not check the three unledgered folders** (above), or
   `kalshi-inplay-bot`'s own audit ledger, which is a fourth file of claims the
   shared parser does not read.
5. **I did not judge whether any reopened idea is any good.** "This was closed
   for the wrong reason" is not "this will work".
6. **I classified by hand.** A different reader would move some rows between
   *closed properly* and *closed too narrowly*; the boundary between those two
   is a judgement, not a measurement. Every one of my 313 calls is in
   [reports/classification.csv](reports/classification.csv) with its reason, so
   it can be argued with rather than taken on trust.
7. **I did not look at anything that was never written down.** A test that ran
   and was never recorded is invisible to every tool in this repo, including
   this one.

---

## The Critic — what is wrong with the report above

Run per [coordinator/REFLECT.md](../coordinator/REFLECT.md). The Critic is not
allowed to be fair.

1. **"29 of 82" is a suspiciously large hit rate for a chat that was warned not
   to reopen everything.** A chat rewarded for finding reopens found a lot of
   them. — *Partly answered by splitting the 29: only 13 ask for any work, and
   6 of those 13 are "run the same script again on a fixed input". But the
   underlying warning stands and the user should read the count sceptically.*
2. **The denominator was chosen by me.** Deciding that 231 claims "are not
   closures" is the single biggest lever in the headline, and I pulled it.
   Under a different reading — every settled row is a closure — the figure
   would be "53 of 284 closed properly", which sounds catastrophic and would be
   just as defensible arithmetically and much less honest. *Both numbers are in
   the report for exactly that reason.*
3. **Four claims were checked against their artifact; 309 were not.** This is
   the repo's own recorded failure mode — read one source, conclude. I read the
   ledger row, which is one source, for the great majority.
4. **"B021 refutes M027" is not exactly true and I should not let it stand as
   written.** B021 showed, on one call with a free key on 2026-08-06, that a
   free source returns ITF **tournaments and live scores**. `bot-hunt`'s separate claim is that there is no free **reference
   price** for ITF, and a score feed is not a price. **M027 is refuted; the
   bot-hunt claim is not**, and anyone re-ranking the tennis families needs to
   know which of the two they are relying on.
5. **The C023 reopen leans on one cell.** Bitcoin at 5 cents reads +2.9 cents —
   but the same artifact shows the other three assets go the other way at the
   same price, and it says those four assets are worth about **1.8 independent
   observations**, not four. The correct statement is *"this does not
   replicate and was recorded as negative anyway"*, not *"there is something at
   5 cents"*.
6. **Absence claims of my own.** I say three folders have no ledger rows. That
   comes from the shared parser's file list plus one search. If a fourth ledger
   file exists that nothing points at, I would not have found it — and I know
   of at least one, `kalshi-inplay-bot/audit/LEDGER.md`, which the parser does
   not read.
7. **Every "how long" in the table is a guess.** None was timed.

## The Referee

**STANDS.**

- The count of closures and the 53 that were closed properly. Every one of the
  313 calls is written down and can be disagreed with.
- **M027, C022, C023, S022 and S023** as genuine reopens. Each names a specific
  document that currently says something its own evidence does not support.
- The four categories, and that category 4 — a test too small to see what it
  reports absent — is the largest and least visible, exactly as the tasking
  predicted.
- The unledgered-folder hole.

**DOWNGRADED.**

- *"M027 was closed on a false premise"* → **"M027 was closed on a false
  premise about data. The related claim that there is no free ITF **price** is
  untouched by it."**
- *"C023 shows a positive result recorded as negative"* → **"C023 shows 40 of
  44 cells that are ties recorded under the single word negative. The one
  positive-looking cell does not replicate across assets and should not be
  chased on its own."**
- *"53 of 82 closed properly"* → keep, but always beside the other framing:
  **53 closed properly, 29 not, out of 313 claims read.**
- The Critic's point 3 stands and is not fixable by this chat: **four claims
  were checked against their artifacts, 309 against their ledger row.**

**FOR THE USER — the one thing a referee cannot settle.**

> **Is the next unit of attention spent reopening, or finishing?**
>
> **The case for reopening:** the two biggest items are cheap and both have a
> named owner sitting idle on them — the ITF re-rank costs an afternoon and
> touches the highest-volume tennis family on the exchange; the crypto
> market-making pull is one paced download and one re-run, and the project's own
> last measurement leaves half a cent of room rather than none.
>
> **The case against:** the soccer comeback table is mid-build and waiting on
> your go/no-go, and every one of these reopens ends in the same place all 51
> corrections ended — a real effect smaller than what it costs to reach it.
> Reopening thirteen threads is thirteen more chances to spend a week proving
> that again.
>
> Both cases are real. **It is your call, and it is the only thing in this file
> that is.**

---

# CORRECTIONS 2026-08-09 — the first three reopens were worked, and two of them shrank

The user said **go**. Three of the thirteen could be worked from this chat
without touching another chat's folder, because they needed a fact established
rather than a test re-run. **All three moved, and two moved against me.** They
are marked inline in the table above by this section rather than deleted.

## 1. S021 — I called it "the cheapest reopen in the whole audit". That was wrong.

**What I said:** the row needs about **3,970** matches and the recorder gathers
about **1,900 a week**, so the sample it lacked has probably arrived.

**Three things wrong with that, in rising order of importance.**

**(a) The two numbers are in different units.** The 3,970 counts *qualifying
set-1 events*, the same unit as the 3,436 it already had. The 1,900 counts *all
matches*. Over the study window, 3,436 qualifying events accrued in 68 days —
**354 a week, not 1,900.** So the wait was about a week and a half from
2026-08-01, not two days. This is the unit mistake this repo keeps making, and
it is sitting inside the row that warns about sample size.

**(b) Reaching 3,970 does not open a trade, and I should have seen that
immediately.** The measured undershoot is **2.42 out of every 100 risked**. The
cost of trading it is **3.61 out of every 100**. More data makes the 2.42 sharper.
It never makes 2.42 bigger than 3.61. **Ninety-nine times out of a hundred that
sentence is the whole answer, and I wrote a reopen instead.**

**(c) What more data would genuinely buy is the buckets — and the arithmetic
says no.** The only live version of this idea is that some *specific* slice has
an effect big enough to clear 3.61. Right now those tests cannot see anything
under about 9 to 10. Detection sharpens with the square root of the sample, so:

| test | matches now | smallest it can see | matches needed to see 3.6 | at ~354 qualifying a week |
|---|---|---|---|---|
| S005, 25 time and tier buckets (worst) | 3,436 | ~9.0 | ~21,500 | **~61 weeks** |
| S005, best bucket | 3,436 | ~3.7 | ~3,630 | ~10 weeks |
| S006, 10 margin buckets | 479 | ~9.9 | ~3,620 **label-verified** | see below |

**S006 is the interesting one.** Its 479 matches are the label-verified subset —
**13.9%** of the universe. Getting to 3,620 label-verified matches by waiting
means ~26,000 matches passing through, about **74 weeks**. Getting there by
**raising label coverage** is `S018`, which is on the list already and checked
exactly two sources.

> **So the corrected finding is stronger than the closure it was attacking, and
> it points the other way.** The tennis bucket line cannot be resolved by
> waiting — a year of recording, on the recorder's own accrual rate. **The only
> thing that moves it is label coverage, which makes S018 the tennis item that
> matters and S021 an also-ran.** The directional prior held for the 52nd time,
> this time on my own report.

## 2. S022 / S023 — real, but nobody can run them from this machine

`set1_overshoot/data` **does not exist on this desktop.** The study's recorded
depth and candles live on the **laptop**, under `C:\Users\gianf\`, and are
gitignored, which `CLAUDE.md` §8 says to expect.

And `coordinator/runners.py` reports the tennis depth recorder as **"CHECK IT BY
HAND — nobody has ever confirmed this is running."** Nothing on this machine can
see it: no shared drive, no heartbeat.

**So the two genuine bug-closures in tennis are not blocked on the tennis chat.
They are blocked on the laptop**, and so is every question about how much has
accrued since 2026-08-01. That is a physical-access job, not an analysis job.

## 3. BH014 — I asked the wrong question, and the answer is mostly reassuring

I asked which conclusions read the truncated 60-ticker recorder output. **I
guessed the de-vig cost bar did, and it does not.** The bar is
`fee(ask) + slippage` — the pre-registration says in as many words that there is
**no spread term**, because buying at the ask already pays the spread. Both terms
are independent of which tickers the recorder sampled. **The "de-vig is not
reachable on MLB" conclusion is untouched.**

`RESULTS_DEVIG.md` had also already checked the neighbouring case and said so:
the old MLB control ran on *settled* markets, so the time-field trap did not
void it.

**What is still genuinely touched, and still unstated:** the **2.0¢ median and
7.0¢ p90 spread** figures came from 214 cycles in which per-ticker snapshot
counts ran **from 1 to a median of 94**, with the server choosing which markets
were starved. Those figures are context rather than load-bearing — but they are
the correction that replaced an earlier 1.0¢ reading, and they have not been
re-measured since the fix on 2026-08-06.

**Net: BH014 drops from a reopen to a one-line re-measurement.**

## What this does to the count

| | was | **now** |
|---|---|---|
| REOPEN — a test to re-run | 13 | **12**, and one of the twelve (S021) is downgraded to *pointless by arithmetic* |
| — of which blocked on the laptop, not on a chat | — | **2** (S022, S023) |
| RELABEL — a sentence to rewrite | 16 | **17** (BH014 moves across) |

**Three worked, two shrank, none grew.** That is the same asymmetry this repo has
recorded 51 times, and it is the first evidence that this chat's own output
behaves like everything else here.

---

# SECOND PASS 2026-08-09 — the remaining ten worked. Four more moved.

Evidence for everything below: **[reports/probe_notes.md](reports/probe_notes.md)**
and `reports/retention_check.json`. Nothing in another chat's folder was written
to. Two live probes were run — a retention check and a Kalshi series query —
because **whether a closure is true is this chat's job**, even when the fix is
someone else's.

| item | what changed |
|---|---|
| **C022 / C023** | **Stands, and is now sized.** Fourth measurement of Kalshi's tape boundary: still exactly **2026-05-25**, now **76 days** old, unmoved while its apparent age went 69 → 71 → 73 → 76. So **~76 days are retrievable against the 8 used** — about **9.5× the evidence** for one paced download. **Not time-critical.** Also re-refutes M009/M010 a fourth time. |
| **M025** | **Strengthened, and it is the best new find of the audit.** `bot-hunt/reports/pinnacle_probe.json` — committed in this repo since 2026-08-04 — contains a **free, unauthenticated, two-sided MLB player prop**: *Justin Foscue Total Bases*, Over 0.5 at −125, Under 0.5 at −106, category `Player Props`, max stake $500. M025 was **cancelled as "unanswerable with free data"** on the strength of **one** feed. ⚠ **Read the caveat below before getting interested.** |
| **M017** | **WITHDRAWN.** `soccer/data-sources.md` had already probed **thirteen** sources with content hashes and concluded Colombia has no free closing line and Peru/Ecuador/Uruguay return 404. Better evidence than the row I flagged, and it was on disk when I flagged it. |
| **C016** | **Downgraded to a relabel.** It is one event's final 61 minutes — but `MORNING_REPORT.md` §0000 already carries a *"Refinement, so this is not overstated"* paragraph limiting it to the far wings, and the conclusion is reached independently by the C6 withdrawal. The row just needs to say "one event's final hour". |
| **CH074** | **Blocked, for a different reason than the one on file.** The decomposition series exists — **`KXATPTOTALSETS`, "ATP Total Sets"** — and returns **0 markets, open or settled**. The same query gives `KXATPMATCH` 10 open and 200+ settled, so the query is right and the series is empty. The test is not runnable today because the market has been minted zero times in the window. |
| **T002 + S018** | **Collapsed into one purchase.** `livetennisapi`'s history plan, **$9.99**, **43 monthly periods, January 2023 to July 2026, point-by-point, including ITF**. It answers the player-model data window, the label-coverage closure, and B023's 29-day null. |

## The M025 caveat, because two-sided is not the same as useful

**For it:** BH011 killed the baseball de-vig with *"the cost bar is larger than
the entire vig it removes"* — a **2.75¢** bar against a **2.01** overround. On
this prop the overround is **7.0 out of 100**, three and a half times larger, so
the per-side correction de-vigging applies is about **3.5** rather than about 1.
**That arithmetic does not transfer from the moneyline to props**, and using it
there would be exactly the "one version tested" mistake this audit is about.

**Against it:** a book quoting **7 out of 100** with a **$500** maximum stake is
telling you it is not confident. Pinnacle's moneyline is a sharp reference; its
props, on this evidence, are a different instrument. That has to be established,
not assumed.

**And the limit: this is one prop.** It kills the absence claim. It says nothing
about edge.

## What the count is now

| | at first writing | after 08-08 | **after 08-09** |
|---|---|---|---|
| REOPEN — a test to re-run | 13 | 12 | **9** |
| — actionable now | — | — | **5** (M027 · C022+C023 · M025 · T002+S018) |
| — blocked on the laptop | — | 2 | **2** (S022, S023) |
| — blocked on a market that does not exist | — | — | **1** (CH074) |
| RELABEL — a sentence to rewrite | 16 | 17 | **19** |

**Removed from the reopen list across both passes: S021, BH014, M017, C016.**
Two were withdrawn because the reopen closed the thread harder; two because the
work was already done and I had not looked in the right place.

> **Seven of the thirteen have now been worked. Four shrank, one grew, two
> stand.** The one that grew — M025 — grew into *"the absence claim is false"*,
> not into *"there is money here"*. **Still not one correction in this repo has
> revealed a larger edge, and this audit is now part of that record rather than
> an exception to it.**

## The Critic, on this second pass

1. **M017 is the whole audit's own failure mode, executed by the audit.** I
   flagged an absence claim without reading the folder whose entire job that
   week was that question. My defence — that `soccer` has no ledger rows and
   this audit read ledgers — **is the finding, not the excuse.** It means the
   unledgered-folder hole is not theoretical; it cost a wrong reopen inside 24
   hours.
2. **The M025 find is one prop from one saved sample.** The probe artifact keeps
   two sample entries per endpoint. I have not established how many of
   Pinnacle's 1,920 free baseball markets are props, how many are two-sided, or
   whether any of them line up with a Kalshi prop market. **"Free two-sided prop
   prices exist" is what the evidence supports. Nothing more.**
3. **The retention probe reads the tape as a whole with no ticker filter.** That
   is deliberate — a per-ticker probe can read zero because that market did not
   trade — but it means I have shown trades exist on those dates, not that any
   *particular* series is retrievable back to them.
4. **`KXATPTOTALSETS` returning zero is an absence claim of mine.** One query
   shape, one moment. It could be a series that mints seasonally. I checked the
   query against a series that does return data, which is the minimum, and it is
   still one probe.
5. **Nothing here re-ran anyone's analysis.** Every "stands" in the table above
   still rests on reading, not on reproducing.
