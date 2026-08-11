# HANDOFF — reopen

<!-- COORDINATOR-STATE
doing: nothing running - the replies are in, four of my calls were overturned and corrected, and 219 newly-readable claims are named as unaudited
left: audit the 219 claims ledger.py can now see, starting with kalshi-inplay-bot's 95 (the live-money bot's own audit)
needs: yes - three for the user: check record_depth.py on the laptop, decide the $9.99 livetennisapi history, and say yes or no to tennis widening its running pre-registered test so the set-score comparison can run
-->

**As of 2026-08-08.** Written by the session that took mailbox message 001.

---

## What this chat is

It audits **closures**, not results. Every claim that stopped a line of work
gets sorted into *closed properly* or *closed for one of four other reasons*:
a bug, a missing data source, one version tested, or a test too small to see the
thing it says is absent.

**It reads every folder and writes only in `reopen/`.** Reopens go to the owning
chat's mailbox; that chat does the work.

## Where it got to

**The first full pass is done and filed.** [REOPENED.md](REOPENED.md) is the
report.

| | |
|---|---|
| Claims read | **313** distinct (342 table rows) |
| Of those, ones that closed a line of work | **82** |
| Closed properly | **53** |
| Closed for some other reason | **29** — **13** want a test re-run, **16** want a sentence rewritten |

Every one of the 313 calls, with its reason, is in
[reports/classification.csv](reports/classification.csv).

## Mail sent, and what each box owes back

| box | message | what it asks for |
|---|---|---|
| `devig` | `010` | Pull more crypto trade tape and re-run the maker test (the ledger says closed, the project says unresolved); re-rank the tennis families now the "no free ITF source" claim is known false; four wording fixes; say which conclusions read the truncated recorder output |
| `tennis` | `006` | Re-run the fade side and the retirement add-back on the fixed dedupe; count whether the forward recorder has reached the sample S021 said it needed; two wording fixes; the $9.99 tennis history; probe a third label source; run the parlay residual test |
| `soccer` | `002` | Probe a second source for Colombian, Peruvian, Korean and Chilean closing lines before those leagues stay out of the table |
| `coordinator` | `001` | `ledger.py` reads 3 of 5 ledger files; three folders still have no rows; `mail.py` cannot record who sent a message |

**Nothing here is blocked on those replies.** They are other chats' work.

## 2026-08-09 — the user said "go". What changed.

Three of the thirteen could be worked from this chat, because they needed a fact
established rather than a test re-run. **All three moved. Two moved against me.**
Full detail at the foot of [REOPENED.md](REOPENED.md).

| item | was | now |
|---|---|---|
| **S021** | "the cheapest reopen in the audit" | **withdrawn.** The two numbers are in different units (354 qualifying events a week, not 1,900), and more data cannot help regardless: the effect is 2.42 out of 100 against a 3.61 cost. The bucket version needs **61 weeks** of recording. |
| **S018** | fourth on the list | **first for tennis.** S006's floor is limited by label coverage, not by time — raising coverage is the only lever that moves it, and that closure checked two sources. |
| **BH014** | a reading pass | **mostly cleared.** I guessed the de-vig cost bar read the truncated output; it does not — the bar is fee plus slippage with no spread term. One re-measurement remains. |
| **S022 / S023** | tennis's job | **blocked on the laptop.** `set1_overshoot/data` is not on this desktop, and `runners.py` reports the depth recorder as never confirmed running. |

Follow-up mail filed: `tennis` **007**, `devig` **011**, both marked read-before.

**Revised counts: 12 reopens (one of them, S021, now pointless by arithmetic),
17 relabels, 2 of the 12 blocked on physical access to the laptop.**

## What is left for this chat

1. **Re-audit after the owning chats answer.** A reopen that nobody acted on is
   worth the same as one nobody found.
2. **Audit the three unledgered folders** — `soccer`, `polymarket-tennis-copy`,
   `ptis-polymarket`. Their claims are in no ledger, so they are not in the 313
   and this chat cannot currently see them. That job starts when someone
   ledgers them; it is not this chat's folder to write in.
3. **Read artifacts rather than rows.** Four of the 313 were checked against
   their committed output and 309 against their ledger row. The two biggest
   findings in the report both came from the four. That ratio is the single
   biggest weakness of this pass and the obvious way to improve the next one.
4. **The three threads that died with no conclusion at all** — the Discord
   signal work never tested for edge, the "sell after a 10% gain" question whose
   answer is missing from the export, and the two tennis patterns that cannot
   both be an edge. Those were never opened rather than wrongly closed, and
   nobody owns them.

## How to reproduce everything

No network, no credentials, reads only.

```bash
py -3 reopen\src\dump_claims.py
py -3 reopen\src\screen_closures.py
py -3 reopen\src\classify_closures.py
```

The last one **exits non-zero** if any claim has no classification, if a
classification points at a claim that does not exist, or if anything not closed
on evidence has no stated action. A silent gap in the audit of silent gaps would
be the obvious way to fail.

## Standing risk in this chat's own work

**It is rewarded for finding reopens.** 29 of 82 is a high rate and should be
read sceptically — which is why the 29 are split into 13 that ask for work and
16 that ask for a sentence, and why every call is written down rather than
summarised. The Critic section of [REOPENED.md](REOPENED.md) attacks this chat's
own report and is not allowed to be fair to it.

## 2026-08-09, second pass — the remaining ten worked

Evidence: [reports/probe_notes.md](reports/probe_notes.md),
`reports/retention_check.json`, `src/check_retention.py`.

| item | outcome |
|---|---|
| **C022 / C023** | **Stands, and sized.** Fourth measurement of Kalshi's tape boundary: still **2026-05-25**, now **76 days** old, unmoved while apparent age went 69 → 71 → 73 → 76. **~76 days retrievable against the 8 used — about 9.5×.** Not time-critical. Re-refutes M009/M010 again. |
| **M025** | **Strengthened.** `bot-hunt/reports/pinnacle_probe.json` (committed 2026-08-04) holds a free two-sided MLB player prop — *Justin Foscue Total Bases*, Over 0.5 −125 / Under 0.5 −106, max stake $500. The "unanswerable with free data" claim is false. **Caveat: 7.0 out of 100 overround against 2.01 on the moneyline, a $500 limit, and it is one prop.** |
| **M017** | **Withdrawn.** `soccer/data-sources.md` had already probed thirteen sources with content hashes. Better evidence than the row I flagged. |
| **C016** | **Downgraded to a relabel.** Its source document already carries a paragraph limiting it to the far wings. |
| **CH074** | **Blocked for a new reason.** `KXATPTOTALSETS` exists as a series and returns **0 markets**, open or settled, while `KXATPMATCH` returns 10 and 200+ on the same query. |
| **T002 + S018** | **One purchase.** `livetennisapi` history plan, $9.99, Jan 2023 – Jul 2026, point-by-point, including ITF. Answers T002, S018 and B023. |

**Counts: 9 reopens — 5 actionable, 2 blocked on the laptop, 1 blocked on a
market that does not exist, and 19 relabels.** Removed across both passes:
**S021, BH014, M017, C016**.

Mail: `devig` **012**, `tennis` **008**, `soccer` **004**.

### The finding that matters most about this chat's own method

**M017 was a wrong reopen, and the reason is the hole this audit named.**
`soccer` has no ledger rows; this audit read ledgers; so the answer to one of my
own reopens sat in a folder no ledger-based check can see. **Within a day of
writing that the unledgered folders were a hole, the hole produced a false
finding here.** That is the strongest argument available for ledgering the three
remaining folders, and it is an argument against this chat's own output.

### Running tally

**Seven of the thirteen have been worked. Four shrank, one grew, two stand.** The
one that grew — M025 — grew into *"the absence claim is false"*, not into
*"there is money here"*. **No correction in this repo has yet revealed a larger
edge, and that now includes this chat's corrections to itself.**

## 2026-08-09, the replies — four of my calls were wrong

`devig`, `tennis` and `soccer` all answered. Full detail at the foot of
[REOPENED.md](REOPENED.md).

**Overturned, and all four are mine:**

1. **BH011 — I hardened a retracted claim.** I listed it "leave alone" quoting
   the vig-bound argument, which `devig` had retracted on 2026-08-07 before my
   message. The overround does not bound the edge. **It also voids my own M025
   argument**, which used the same premise — M025 survives only as *"the absence
   claim is false"*.
2. **C022 — withdrawn.** `crypto/RESULTS_MAKER_VIABILITY.md` (08-08) closed it
   on evidence the day before I called it a reopen: 17,325 fills, 1,161 events,
   23 days, net −0.853¢, interval excludes zero. I read the 08-07 file and did
   not open the 08-08 one.
3. **CH074 — my "zero markets" was one query.** `KXATPSETWINNER` has 112 open
   and 200+ settled; `KXWTASETWINNER` 104 and 200+. It is runnable, and `tennis`
   can also do it forward. **An absence claim from one source, in this chat.**
4. **S021 — my "count the recorder" ask conflated two recorders.** `tennis`
   counted 362 and correctly refused to apply it; different market, window and
   recorder. The `K015 = W011` trap, and they caught it.

**Paid:** C023 (row rewritten UNDERPOWERED, my warning carried verbatim) ·
S018 (refuted, free per-season label source) · BH014 (the re-measurement I
under-valued **withdrew BH013**) · M027 and all four sentences.

**Error rate on worked items: 4 wrong of 8. Hold that against everything else
here.**

## The denominator moved

`coordinator` fixed `ledger.py` (`aaf5e06`) — *"read 342 claims and there were
596, idea.py was under-reading by 43%"*. It now reads six files: **532 distinct
claims against the 313 audited.**

The coverage check **failed loudly rather than reporting a stale count**. The
219 unaudited are now listed in `classify_closures.py` with a reason each:

| file | rows | note |
|---|---|---|
| `set1_overshoot/HYPOTHESIS_LEDGER.md` | 97 | expect overlap with S001–S025 |
| `kalshi-inplay-bot/audit/LEDGER.md` | 95 | **highest value — the live-money bot's own audit** |
| `crypto/HYPOTHESIS_LEDGER.md` | 27 | expect overlap with C001–C027 |

**That is the next pass and it is the whole job now.**

Also reported to `coordinator`: the widened parse reads five filename cells from
a prose table as claim ids, so 596/538 is overstated by five; and
`soccer/LEDGER_SOCCER.md` (which `soccer` created from my message) is still not
on the `SUB_LEDGERS` list, so `idea.py` remains blind to soccer.

Mail: `devig` **013**, `tennis` **009**, `coordinator` **002**.
