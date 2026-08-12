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
| **C022** — crypto market making | Recorded in the main ledger as **settled, no edge**, citing a file whose own verdict section reads *"Not yet reached"*. | **4 — too small**, and **1 — a bug** before that | ⚠⚠ **WITHDRAWN 2026-08-09 — I MISSED A FILE.** `crypto/RESULTS_MAKER_VIABILITY.md` (2026-08-08) closed this on evidence the day before I wrote: **17,325 fills, 1,161 events, 23 days**, net **−0.853¢/contract**, range **[−1.632, −0.185]**, excluding zero. Capture alone is **−1.226¢** — there is no spread being captured to set against the pick-off cost, so it fails one step earlier than my framing assumed. I read the 08-07 file and stopped. ~~The project's later file (`crypto/MM_RESULTS_MAKER.md`, 2026-08-07, 658 events over 8 days ending 2026-07-31) says the cost of being the passive side is about **half a cent** against a gross margin of about **one cent**, and *"the question is not settled against market making, it is unresolved"*. **73 days** of tape are retrievable against the 8 used. Pull them and re-run.~~ | ~~one paced pull~~ **closed on evidence** |
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


---

# THE FIRST REOPEN TO PAY, 2026-08-09 — S018 is REFUTED by the tennis chat

Recorded here within hours of the promotion, because a reopen nobody acted on is
worth the same as one nobody found, and this one was acted on.

**The chain:** withdrawing S021 (waiting cannot work) is what promoted **S018**
(label coverage, closed after two sources) to the first tennis item. The tennis
chat took mailbox 007 and **refuted the closure the same afternoon** — commit
`8ca40df`.

**What they found.** `tennis-data.co.uk` publishes **one workbook per season**
carrying, per match, the date, both players, surface, round, and **games won by
each player in every set**. That is exactly the set-1 margin S006 buckets on.
Free, weekly, and **because the files are per-season the plus-or-minus-7-day
objection that closed S018 does not apply at all** — it reaches back years.

Measured on S006's own window, 25 May – 26 Jul 2026: **1,062 labels against the
479 S006 used.**

**Their own three limits, which are the reason this is honest:**

1. The labels are not yet joined — the join rate needs the laptop universe.
2. **Main tour only.** No Challenger, no ITF, against a live Kalshi pool that is
   73–87% ITF.
3. **1,062 is 29% of the ~3,620 needed.** It moves the smallest visible effect
   from about **9.9** to about **6.6** — against a cost bar of 3.61.

> **Their words, and the right ones: "REFUTED, not resolved. Shortens the wait,
> does not end it."**

**A free extra they found in the same file:** `PSW`/`PSL` are **Pinnacle closing
prices**, historical and already joined to results — the de-vig reference `devig`
and `mlb` have been looking for.

## What this settles about the audit itself

**Category 2 — "the data wasn't available" — is the category that pays.** Both
worked examples are now confirmed: the ITF absence claim was false (B021), and
the tennis label absence claim was false (this). **Two for two, on closures that
had each checked two or three sources and then written the sentence as though it
were about the world.**

**And it is still not an edge.** The floor moves from 9.9 to 6.6 against a 3.61
bar. The thread is more measurable than it was this morning and it is not
resolved. That is the fourth thing this audit has produced that shrank on
contact, and the first that shrank *after* someone acted on it.

---

# THE REPLIES CAME BACK, 2026-08-09 — four of my calls were wrong, and four paid

`devig`, `tennis` and `soccer` all answered. **This section is the score, and the
wrong calls go first because they are mine.**

## Four calls the owning chats overturned

### 1. ⚠⚠ I hardened a claim that had already been retracted

I put **BH011** in the "leave these alone" list and gave the reason as *"the cost
bar is bigger than the whole vig — that is arithmetic, not a small sample."*

**`devig` had retracted exactly that argument on 2026-08-07, before I wrote it.**
Their correction is right: the overround is what you **strip** to estimate fair
value; **it does not bound the edge.** If Kalshi's ask sat 8 cents below de-vigged
fair, the edge would be 8 cents on a market with a 2-out-of-100 overround.

**The conclusion survives on a measurement, and that is what to quote:** across
**1,460 paired observations on 30 games the two venues never disagreed by more
than 2.77 cents**, against a 2.75-cent cost.

> **An audit that hardens a retracted claim is the one failure this exercise
> cannot afford, and I did it.** Corrected in `classification.csv`.

**And it voids an argument I made two messages later.** My case for reopening
**M025** said: *"the vig on this prop is 3.5× larger, so the per-side correction
is larger, so BH011's arithmetic does not transfer."* **That reasoning is built
on the same retracted premise and is withdrawn.** The conclusion — that BH011
does not transfer to props — still holds, but for a different reason: BH011's
real evidence is a **measurement of moneyline agreement on 30 MLB games**, which
says nothing about props. **M025 survives as "the absence claim is false" and
nothing more.**

### 2. C022 was already closed on evidence and I missed the file

I called it the second-biggest reopen in the audit. **`crypto/RESULTS_MAKER_VIABILITY.md`,
dated 2026-08-08, closed it the day before I wrote:** the resting-order test on
**17,325 fills, 1,161 events, 23 days** of replayed book — net **−0.853 cents a
contract**, range **[−1.632, −0.185]** clustered on days, **excluding zero**.
Capture alone is **−1.226 cents**: a trade-through fill means the book moved away
before you traded.

**So it fails one step earlier than my "half a cent against one cent" framing
assumed — there is no spread being captured to set against the pick-off cost.**

**I read the 2026-08-07 file, saw the 08-08 filename in a directory listing, and
did not open it.** Same error as M017, four days apart. **WITHDRAWN — C022 is
closed on evidence.**

### 3. My "CH074 is blocked, the market has been minted zero times" was wrong

I probed **`KXATPTOTALSETS`**, found it genuinely empty, and generalised to the
idea. **`KXATPSETWINNER` has 112 open and 200+ settled markets; `KXWTASETWINNER`
has 104 and 200+.** Verified today.

**That is an absence claim from one query, in an audit whose entire subject is
absence claims from too few sources.** My own Critic flagged the risk in writing
and I published it anyway. **CH074 goes back on the list as actionable** — and
`tennis` points out it is testable *forward* on the recorder already running,
which sidesteps the missing history entirely. They will not start unasked because
it widens a running pre-registered test.

### 4. My "count the recorder" ask for S021 confused two recorders

`tennis` counted — **362 settled matches, 1,205 a week** — and then **correctly
refused to apply it**, because those are match-winner markets on a different
recorder, a different window and a different question from `set1_overshoot`'s
set-1 universe. Their words: *"treating my 362 as progress toward S021's 3,970
would be exactly the error this repo has already paid for twice"* — `K015 = W011`.

**They are right and I set them up to make that mistake.** S021 stays withdrawn
for the arithmetic reason, which is unaffected.

## Four that paid

| item | what came back |
|---|---|
| **C023** | `devig` agrees entirely: *"you are entirely right and the row was dishonest."* Rewritten as **UNDERPOWERED, not demonstrated negative**, with my warning carried into the row verbatim — **do not chase the 5-cent cell**. |
| **S018** | **REFUTED by `tennis` the same afternoon.** `tennis-data.co.uk` publishes one workbook **per season** with games won by each player in every set — free, reaching back years, so the ±7-day objection that closed it never applied. 1,062 labels against the 479 in use. **"REFUTED, not resolved"**: main tour only against a 73–87% ITF pool, and it moves the smallest visible effect from ~9.9 to ~6.6 against a 3.61 bar. |
| **BH014** | I downgraded this to "a one-line re-measurement". **It withdrew a claim.** The 2.0¢/7.0¢ spread `devig` had used to *correct* `RESULTS.md` was itself an artifact of the starved recorder: post-fix it is **1.0¢ median, 2.0¢ p90** on 18,828 snapshots. **BH013 is withdrawn as their own bad correction.** And the truncation was **biased** — on MLB and LoL the *sooner-closing* markets were the ones dropped, the worst direction for a pre-match strategy. **I under-valued this item.** |
| **M027 + the four sentences** | All done. M027 marked **superseded**, with my scores-are-not-prices caution written into the row rather than the reply. M011's correction copied into `bot-hunt/PREREGISTRATION.md`; M009/M010 marked retracted with the 2026-08-19 deadline explicitly killed; C025 upgraded; five over-broad sentences narrowed inline with originals struck through. |

## And the coordinator fix changed the denominator

`coordinator` acted on my message about `ledger.py` reading three of the five
files it listed. **Commit `aaf5e06`: "ledger.py read 342 claims and there were
596 — idea.py was under-reading by 43%."**

It now reads **six** files. **532 distinct claims, against the 313 this audit
read.**

| | |
|---|---|
| audited | **313** |
| **deferred, named not dropped** | **219** — the 97-row set-1 hypothesis grid, 95 rows of the live-money bot's own audit, 27 crypto rows |
| parser noise | 6 |

**The coverage check caught this rather than reporting a stale count**, which is
what it was built for. The 219 are now listed in `classify_closures.py` with a
reason each, and the check still fails on anything neither classified nor named.

⚠ **One small defect in the fix, reported to `coordinator`:** the widened parse
reads the first column of two prose tables in `LEDGER.md` as claim ids — the M011
citation table at line 494, whose first column is a filename. **So 596/538 is
overstated by five.**

## Where the thirteen stand now

| | first writing | **now** |
|---|---|---|
| REOPEN — a test to re-run | 13 | **11** |
| — actionable | — | **4** (M027 done · **M025** · **CH074** · T002) |
| — blocked on the laptop | — | **2** (S022, S023) |
| RELABEL | 16 | **17** |
| withdrawn by this chat | — | **S021, BH014→relabel, M017, C016, C022** |

> **The scoreboard, stated so it cannot be read kindly: eight of the thirteen
> have been worked. Four paid, four of my calls were wrong, and one of the wrong
> ones was defending a retracted claim.** The audit's own error rate on worked
> items is **50%**. That is the number to hold against anything else in this
> file.

---

# THE LIVE-MONEY LEDGER, 2026-08-11 — 122 claims nobody had read

Mailbox 002 sent me to `kalshi-inplay-bot/audit/LEDGER.md` ahead of the two
hypothesis grids, for the right reason: **it is the only project in this repo
about money that actually moved.**

**Running totals across everything audited: 446 of 609 claims read, 136 of them
closed a line of work, and 91 — two thirds — were closed properly.** The 163
still unread are named in `classify_closures.py` with a reason each.

## ⚠ FIRST — my own tool had the bug this chat exists to catch

**Thirty-four claim ids mean two different things depending on which file you
are in.** `crypto` C010 is *"no model beats the Kalshi mid"* on 250 events. This
ledger's C010 is *"a player model lost to the bookmaker"*. Same id, different
claim, different project.

**My classifier keyed on the id alone**, so it silently applied `crypto`'s
verdicts to 27 of these rows and reported them as already-audited. **The audit of
things-concluded-too-fast concluded too fast about its own coverage.** Fixed —
it now keys on (file, id) — and reported to `coordinator`, because **`idea.py`
searches the same merged view and has the same exposure**: a prior-work check for
"C010" returns two unrelated claims.

## The six findings

### 1. The bug that blocked crypto for six days was already fixed here, three days earlier

**C066:** the orderbook parser unwrapped a non-existent `"orderbook"` key, so
every book snapshot for ~1.8 hours was an empty marker with correct row counts.
**Diagnosed, quarantined, and covered by nine regression tests, on 2026-07-30.**

**That is `M001`** — which `market-selection` re-discovered on **2026-08-02** and
"independently reproduced on 85 markets", and which then sat as a stated blocker
in the crypto market-making documents until **2026-08-06**.

> **The fix was on disk with tests the entire time.** This is the clearest
> measurement of what an unread ledger costs: six days of a blocked thread, and
> a wrong premise repeated in three documents.

### 2. The live bot's two gates are fitted to noise, and the bot is configured for real money

| | |
|---|---|
| **C011** — the primary entry gate | a price-bucket table from **125 settled markets split five ways** — about **25 observations a bucket**, and the decisive bucket carries the account |
| **C012** — the 38¢ stop | a "smooth optimum" across **137 matches** where **the entire range across every width tested is 2.3 cents**. The optimum is inside the noise. |
| **C108** | `gui.py --live --bankroll 125 --stake-pct 5`, private key present, 5 open positions with resting take-profits |

The ledger already marks both **BROKEN**. Trading is **off** and nothing is
scheduled, so this is not an emergency — **it is a trap laid for whoever turns it
back on.** The 14,162-market tape that would re-derive both is on disk.

### 3. "Consensus copying is REJECTED" — on zero accepted entries

**C088.** The main setting produced **0 accepted resolved entries in all five
niches**, and the headline reads as a rejection. The ledger says so itself:
*"the main setting is a null-by-no-data."*

**That is category 4 in its purest form — a verdict with no measurement under
it.** The unfiltered crypto control losing **$40.17 on $40** is real and damning;
it should carry the sentence instead.

### 4. Four claims marked "no artifact anywhere" whose artifacts exist one folder away

| claim | what it says | where the answer is |
|---|---|---|
| **C009** | Kalshi tracks Betfair at r=0.9878 — *"no Betfair data, script or output anywhere on this machine"* | **T012**, n=809, SETTLED, same numbers |
| **C010** | a player model lost to the bookmaker, artifact **NONE** | **T006**, SETTLED, same numbers |
| **C117** | *"whether the tennis series charge maker fees is unrecorded anywhere and is the cheapest open question in the corpus"* | **S010**, **S025** and **M008** — answered three times over |
| **C106b** | Kalshi tennis calibration, *"none preserved"* | **B027**, 6,519 events |

**C009 is load-bearing:** it is the stated reason to expect no favourite-longshot
bias on Kalshi. It has been carried as unverified while a settled version sat in
`kalshi-tennis`.

**And C042 is the third copy of the dead +7.05pp number** — `K015` = `W011`,
recomputed from scratch at +2.09 and **−0.29 net**. Two projects had already
killed it; this one still calls it the claim that reframes its whole
copy-trading thread.

### 5. The repo's biggest open lead has a prior measurement that failed, and nothing cites it

The 2026-08-06 audit ranks **"measure weather's edge against the mid"** as item
**#1** — *"the largest genuinely-unexplored lead in the repo"*. **C061** in this
ledger says the same: unmeasured, blocked.

**C096, a week earlier, in a project neither of them references, scored a
weather model against the prices you would actually have paid, on 600 contracts
held back and sealed — and the model LOST.** Its forecasts were wrong by
**0.2048** where the market's were wrong by **0.1690**; lower is better, so the
market won and it was not close. **C097** then mixed the two, 89% market and 11%
weather, and the tiny improvement vanished once the test counted **each weather
event once instead of each contract** — the range of what it could really be ran
from slightly negative to slightly positive, so the gate did not pass.

**This does not settle the question** — different family (daily temperature, not
hourly ladders), different benchmark (ask, not mid), different model. **It
changes the prior**, and it is worth reading before a recorder is committed to it.

### 6. The real thesis was never tested, and the ledger says so

**C106c**, in its own words: *"this reframes every negative result in P1. All of
C001–C007 concern **price-visible** information, which the market prices
correctly. None of it tests whether the market prices the **score** correctly."*

**The forward tape built to test it ran for two days and stopped.**
`tennis-paper-forward` is now recording live matches with a brief per match,
which is the same shape.

### Also: two known, unfixed defects feeding a frozen forward list

**C082** — the follower model disagrees with the wallet's own outcome on **42.4%**
of traded-out positions, and one affected wallet (**33.7%**) **is in the frozen
follow list** while the forward verdict is **pooled**. **C083** — `holding_seconds`
measures entry to a metadata finalisation timestamp, 160 hours on single
matches, contaminating **100%** of the headline candidate's record. Both must be
fixed **before** that forward record is ever scored.

## What this ledger gets right, and it is most of it

**91 of 136 closures across everything audited were closed properly, and this
file contributes the best examples in the repo:**

- **C027** is how a category-4 row should read: *"a null at n=25 markets, i.e.
  very low power. It rules out a large edge, not an edge."*
- **C077** — 42,652 wallets, one match = one call, **0 discoveries** and **fewer**
  nominally-significant wallets than chance predicts.
- **C079** — the edge is real and **dies inside 15 seconds**, with the null
  expectation computed at each delay. That is the mechanism behind every negative
  result above it.
- **C072** simulates the **screen**, not the strategy. **C074** shows a gate
  flipping a wallet from fail to pass with no record changing. **C090** preserves
  invalidated runs instead of deleting them.
- **C036** caught its own pseudo-replication: 2 distinct violations counted 55
  times, and it says so.

## The Critic and the Referee on the live-money pass

### The Critic

1. **I read 122 ledger rows, not 122 artifacts.** Every "closed on evidence"
   above rests on what that row says about itself. The two biggest findings in
   my earlier passes both came from opening an artifact instead — and I opened
   **none** here.
2. **C066 = M001 is the strongest claim in this section and it is an identity
   argument, not a re-run.** I matched two descriptions of the same parse error
   in two files. I did not verify that the fix in `kalshi-inplay-bot` would have
   fixed `market-selection`'s reader, which is a different codebase.
3. **"Nobody had read it" is an absence claim.** I infer it from the coordinator
   saying so and from `ledger.py` not having parsed the file. Someone could have
   read it without leaving a trace.
4. **The weather point (C061 vs C096) is the one most likely to be over-read.**
   Different family, different benchmark, different model, and I say so — but
   the sentence "the biggest lead has a prior measurement that failed" will
   travel further than the caveat attached to it.
5. **My own ID-collision bug means every count I published before today was
   computed on a table with 27 wrong entries.** The 313-claim pass was not
   affected — those files have no collisions — but I did not verify that until
   after I found the bug.
6. **`nobody` owns three of the reopens.** `kalshi-inplay-bot` is in no chat's
   folder list in `chats.json`. Filing a reopen to nobody is filing it nowhere.

### The Referee

**STANDS.**

- **C066 = M001.** Two files describe the same parse error, three days apart,
  and the second one says it was "independently reproduced". Whatever the fix
  portability, the *diagnosis* existed and was not found.
- **C011 and C012.** The ledger already calls both BROKEN; I added only the
  consequence, which is C108 — the bot is configured for real money.
- **C088.** "Rejected" against "0 accepted resolved entries" is the ledger's own
  wording in both halves.
- **The four cross-reference rows** (C009, C010, C117, C106b). Each names an
  artifact as missing; each has a settled counterpart with matching numbers.
- **The 91-of-136 count**, with the stated limit that it is row-level.

**DOWNGRADED.**

- was: *"the repo's biggest open lead has a prior measurement that failed"*
  now: **"the repo's biggest open lead has a prior measurement, on a different
  weather family against a different benchmark, that failed. It changes the
  prior. It does not answer the question, and it should be read before a
  recorder is committed, not instead of one."**
  because: the Critic is right that the short version will travel and the
  caveat will not.
- was: *"122 claims nobody had read"*
  now: **"122 claims that no tool could read and that nothing in the repo
  cites"** — which is what I can actually show.

**FOR THE USER — genuinely unresolved. One, and it is a real disagreement.**

> **Does `kalshi-inplay-bot` belong to anybody?**
>
> **One side:** it is dormant, trading is off, and its claims are historical.
> Leave it unowned and let the audit's notes stand as the record.
>
> **The other side:** it holds the live bot's two gates, both fitted to about
> 25 and 137 observations, and a private key, and a config that says
> `--live --bankroll 125`. **The next person to turn it on inherits both gates
> and neither is flagged in the code.** Three of my reopens have `nobody` as
> the owner because `chats.json` gives that folder to no chat.
>
> **What would settle it:** you assign the folder to a chat, or you say it stays
> dormant and the gates get a warning comment where a trader would see it.
> **I cannot decide this and neither can the coordinator — it is about money
> that could move.**
