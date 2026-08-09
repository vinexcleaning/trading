# REOPENED.md — which closed threads died on evidence, and which died on something else

**As of 2026-08-08.** Written by the `reopen` chat, from mailbox message 001.

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
| **S023** — "the fade side loses in every configuration" | A dedupe bug voided the event set underneath it. Marked broken, **never re-run**. | **1 — a bug** | Re-run it on the fixed dedupe. Half of the sentence *"tennis set-1: no edge in either direction"* currently rests on arithmetic that was expected rather than measured. | one re-run |
| **C023** — hold a crypto contract to settlement | Recorded in the ledger with the single word **"negative"**. | **4 — too small** | I opened the committed output (`crypto/reports/hold_settle.txt`, 25 May–30 Jul 2026, four assets, 146–250 events each) rather than the row. It says **tie** in 40 of its 44 price cells, with ranges of plus-or-minus 5 to 15 cents against a cost of 1 to 2 cents. Bitcoin at 5 cents reads **+2.9 cents**, its bottom edge one hundredth of a cent below zero. That is not a negative result; it is an unmeasured one. Same tape pull as C022 fixes it. | shares C022's pull |
| **S021** — "the tennis line cannot be resolved with the sample available" | An honest power statement, written **2026-08-01**. | **4 — too small** | It says it needs about **3,970 matches** and that the recorder gathers about **1,900 a week**. That was a week ago. Count what has accrued and re-run if it clears. | one count, then one re-run |
| **T002 / B023** — the player-model data window | Features from one provider stop at 2026-06-02 and 85% of markets are after that; the player-feature sweep then returned nothing on **29 days** of form, where the typical player appears about three times. | **2 — data**, feeding **4 — too small** | **$9.99** buys 43 months of point-by-point history including ITF. It replaces the frozen source and re-powers the sweep in the same purchase. Already named in the 2026-08-06 audit and not bought. | $9.99 and one rebuild |
| **S018** — "match label coverage cannot be raised" | Two sources: one paid tier's cap, one site's 7-day window. | **2 — data** | Probe a third and a fourth. The signal chat found free soccer goal-time data this week that nobody thought existed, which is the same shape of mistake. | a few hours |
| **M017** — Colombian, Peruvian, Korean and Chilean closing lines | One site serves a **wrong-country file** under those codes — Colombia returns Poland. | **2 — data** | That kills that one site for those leagues. It does not kill the leagues. Probe others before they stay out of the soccer comeback table. | a few hours |
| **S022** — the retirement add-back cost | Same void event set as S023. Marked broken, never re-run. | **1 — a bug** | One re-run. Small, and unlikely to move anything. | one re-run |
| **BH014** — the recorder read the first 60 tickers | It probed 60 tickers in an **undocumented server order** while the family listed 85 to 104. Fixed 2026-08-06. | **1 — a bug** | Nobody has said which earlier conclusions read that truncated output. Name them. | a reading pass |
| **C016** — "the cheap wings are not tradeable" | **61 minutes** of one price ladder on one day. | **3 — one version** | Re-check across many days of recorded books instead of one hour. | one query |
| **M025** — Kalshi versus DraftKings on player props | One free feed publishes prop prices **one side only**, so the comparison was **cancelled as unanswerable**. | **2 — data** | Check whether any other free feed publishes both sides. | a few hours |
| **CH074** — set-score and parlay markets | Closed by an **arithmetic argument** and one worked example. | **3 — one version** | The test that argument proposed — comparing the two set-score prices against the match price at prices you could really pay — was never run. | one analysis run |

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
