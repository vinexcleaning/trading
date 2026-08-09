# HANDOFF — reopen

<!-- COORDINATOR-STATE
doing: nothing running - the first pass over all 342 recorded claims is finished and filed
left: re-audit after the owning chats answer, and audit the three folders that have no ledger rows once someone ledgers them
needs: yes - reopen thirteen threads now, or finish the soccer table first? Both cases are in reopen/REOPENED.md and it is the only thing in there I cannot decide
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
