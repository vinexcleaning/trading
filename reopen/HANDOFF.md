# HANDOFF — reopen

<!-- COORDINATOR-STATE
doing: nothing running - the audit is filed, the user said go, and the three items this chat could work without touching another folder are worked
left: the other chats execute their mail; two tennis items are blocked on the laptop and nobody has confirmed that recorder is alive
needs: yes - two things only the user can do: go to the laptop and check record_depth.py is running, and decide on the $9.99 tennis history purchase
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
