# reopen — things closed for the wrong reason

**This folder audits closures.** Every other folder here runs tests. This one
reads what those tests concluded and asks a single question of each: *did this
thread die because it was measured and did not work, or did it die because a
script was wrong, a source was missing, one version was tested, or the test was
too small to see the thing it says is absent?*

**It reads every folder and writes only in this one.** When something should be
reopened, it files a message in the owning chat's mailbox and that chat does the
work. It never edits another chat's files and it never re-runs another chat's
tests.

## Why it exists

The user, 2026-08-09: *"I've been feeling that there's some stuff that we closed
for the wrong reason."* Two documented cases say he is right — a tennis thread
closed on "no free ITF data source exists" when one does (`B021`), and a crypto
thread that sat blocked for six days on "Kalshi's order book is not public" when
the real cause was a parse error reading a key that does not exist (`M001`).

## What is here

| file | what it is |
|---|---|
| [REOPENED.md](REOPENED.md) | **The report.** The table, the counts, the Critic and the Referee. Read this one. |
| [DECISIONS.md](DECISIONS.md) | Judgement calls taken without asking, and why |
| [HANDOFF.md](HANDOFF.md) | Where this got to, and what is left |
| `src/dump_claims.py` | Flattens every ledger into one file, using `coordinator/ledger.py` rather than a second parser |
| `src/screen_closures.py` | Orders the reading. Flags candidates for each of the four categories; decides nothing |
| `src/classify_closures.py` | **The audit itself** — every claim, its category, and what to do about it. Fails loudly if any claim is unclassified |
| `reports/classification.csv` | All 313 calls with reasons, so they can be argued with |
| `reports/all_claims.csv`, `reports/screen.csv` | Intermediate, regenerable |

Everything regenerates with `py -3` and no network:

```bash
py -3 reopen\src\dump_claims.py
py -3 reopen\src\screen_closures.py
py -3 reopen\src\classify_closures.py
```

## The result, in one line

**313 claims read; 82 of them closed a line of work; 53 of those 82 were closed
properly. 29 were not — 13 want a test re-run and 16 want a sentence rewritten.**
