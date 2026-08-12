To: reopen
From: coordinator
Opened: 2026-08-11 14:33
Status: DONE
Subject: Keep going - and take the live-money bot's 122 claims next, ahead of the two hypothesis ledgers

--- INSTRUCTION ---

**Keep going. The user has seen the first results and wants the rest.**

Your first pass paid: **S018 refuted — a free set-1 label source nobody had
checked** — and two more shrank on inspection, which is the correct direction
and not a disappointment.

# THE PRIORITY IS THE ONE NOBODY HAS READ

Your own words: the largest chunk waiting is **`kalshi-inplay-bot/audit/LEDGER.md`,
122 claims, the live-money bot's own audit, and nobody has ever read it.**

**Do that next, ahead of the two HYPOTHESIS_LEDGER files.** Three reasons and
they are all in your own notes:

1. **It is the only project in this repo about money that actually moved.** A
   wrong closure there costs more than a wrong closure anywhere else.
2. **You expect heavy overlap** in the other two with S001–S025 and C001–C027,
   so their marginal value is low. Say so and defer them explicitly rather than
   working them because they are next in the list.
3. `idea.py` can now see all 122 of them — that file is on the search list and
   the archive is **636 claims across 7 files**. Before yesterday a clean
   "nothing found" could have meant "the parser skipped that table shape".

# THE THING YOUR AUDIT IS BEST AT, AND IT IS CATEGORY 4

Categories 1 to 3 — a bug, a missing feed, over-generalising — are visible once
someone looks. **Category 4 is invisible: a test too small to detect what it
declares absent.** *"We found no effect"* and *"our test could not have found
this effect"* are the same sentence on the page and opposite in meaning.

**That is where the live-money audit is most likely to be wrong**, because a bot
with a few hundred real trades has very little power and its write-ups will
read like verdicts. For every null in there: **the smallest effect that test
could have seen, against the size of effect that would have mattered.** Where
the second is smaller, the claim is *unmeasured*, not closed.

# TWO THINGS YOU HAVE ALREADY LEARNED THAT SHOULD SHAPE THE REST

**Reopening can close something harder, and that counts as paying.** S021 is
your example — the two numbers were in different units and it did not matter
anyway. Report those as wins, not as wasted passes.

**You corrected four of your own calls.** Keep doing that in the open. The
`devig` chat nearly repeated M024's original mistake while checking M024, and
caught it. That is the same shape.

# WHAT I HAVE PUT TO THE USER

All three of yours are with him now: the laptop recorder check, the **$9.99**
tennis history, and yes/no on widening the tennis test. **Do not wait on them** —
they gate specific items, not the audit. Park those and work the 122.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both. Three
lists, third one said out loud even when empty.

**Your whole job is finding where somebody concluded too fast**, so being caught
doing it yourself is the obvious way to fail. It has already happened once —
the audit caught itself — and that is the standard, not the exception.

**No statistics words to the user.** Money, or out of 100.

--- REPLY ---

The session that owns `reopen` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


**DONE 2026-08-11.** All **122** claims in `kalshi-inplay-bot/audit/LEDGER.md`
audited. Write-up, Critic and Referee at the foot of
[reopen/REOPENED.md](../../../reopen/REOPENED.md).

**Totals now: 609 distinct claims across seven ledger files; 446 audited, 163
deferred with a reason each. 136 closures examined, 91 of them — two thirds —
closed properly.**

**The two hypothesis grids are deferred explicitly, as you asked**, on the stated
expectation of heavy overlap with S001–S025 and C001–C027. `soccer/LEDGER_SOCCER.md`
appeared between passes (39 rows unread, 2 merged into the root ledger and
classified) and is the obvious next target — it is the newest work in the repo
and the only folder whose claims have never been cross-checked against anything.

**Six findings, and category 4 was where it paid, as you predicted:**

1. **C066 is M001.** The orderbook parse bug was diagnosed, quarantined and
   covered by nine regression tests here on **2026-07-30** — three days before
   `market-selection` "independently reproduced it on 85 markets", and six days
   before it stopped being stated as a blocker in the crypto documents. **The
   fix was on disk with tests the whole time.**
2. **C011 and C012 — the live bot's two gates are fitted to noise.** The entry
   gate is 125 markets split five ways (~25 a bucket); the 38¢ stop comes from
   137 matches where the whole range across every width is 2.3 cents. Both
   already BROKEN, and **C108 says the folder is configured for real money**.
3. **C088 — "consensus copying is REJECTED" on 0 accepted resolved entries.**
   Category 4 in its purest form; the ledger's own words are "a null-by-no-data".
4. **Four claims marked "no artifact anywhere" have settled artifacts one folder
   away** — C009→T012, C010→T006, C117→S010/S025/M008, C106b→B027. And **C042 is
   the third live copy of the dead +7.05pp number** (K015 = W011).
5. **C061 vs C096.** Your #1-ranked lead, weather-versus-the-mid, has a prior
   measurement in a project nobody cites: a weather model scored against the
   prices you would have paid, on 600 sealed contracts, and it lost. **Different
   family and benchmark, so it changes the prior rather than answering the
   question** — but it should be read before a recorder is committed.
6. **C106c** — the ledger says itself that every negative result in P1 is about
   *price-visible* information and none of it tests whether the market prices
   the **score**. The forward tape built for that ran two days.

**Two disagreements with my own earlier work, recorded rather than skipped:**

- **My classifier had the bug this chat exists to catch.** 34 claim ids mean two
  different claims depending on the file — `crypto` and `kalshi-inplay-bot` both
  number C001–C117 — and I keyed on the id alone, silently applying crypto's
  verdicts to 27 rows. Fixed by keying on (file, id). **`idea.py` searches the
  same merged view and has the same exposure**, which is in `coordinator` 003.
- **I read 122 rows and zero artifacts this pass.** Both of my best findings in
  earlier passes came from opening an artifact instead. That is the standing
  weakness and it is stated in the Critic.

**One thing for the user, and the Referee would not resolve it:**
`kalshi-inplay-bot` is in **no chat's folder list**, so three reopens have
`nobody` as owner — including the two live-money gates and a private key. Either
the folder gets an owner, or the gates get a warning where a trader would see
it.
