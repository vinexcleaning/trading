# DECISIONS — signal-github

Method decisions taken without asking, with the measurement that forced each
one. Conservative reading taken wherever ambiguous.

> **Written 2026-08-08 by the `social-signal` session**, on instruction from the
> coordinator (`coordinator/mailbox/signal/005`), because `CLAUDE.md` §10 lists
> this file as missing and the `signal` slug owns this folder. **It is
> reconstructed from `HANDOFF.md`, `CORRECTIONS.md` and the git log, not written
> by the session that took the decisions.** Where a decision's reasoning was not
> recorded at the time, that is said rather than invented. A session that
> returns to this folder should correct anything misread here.

---

## D1 — Depth comes from `codeload` archives, not the git-tree API
**2026-08-03.** The core REST budget is 60 calls/hour unauthenticated and the
git-tree call returns **paths only**. `codeload.github.com/<repo>/tar.gz/<branch>`
returns the whole tree *and* the text of every file in one request, carries no
`X-RateLimit-*` headers, and `/rate_limit` reads identically either side of a
download. Measured: 1,397 archives in **367 seconds** against ~23 hours at 60
tree-calls/hour.
**Use the legacy URL form.** The documented `/tar.gz/refs/heads/<branch>` path
times out from this network; `/tar.gz/<branch>` returns in ~0.3 s. Do not
"modernise" it.

## D2 — The scorer reads every file, after a truncation nobody had stated
**2026-08-03.** Because each file used to be its own request, the scorer read
the **30 largest files capped at 400 KB** — and S1 and S2 were both decided on
that window. `dump_repo.py`, the read step, had the same bug: **every repo "read
in full" in the previous session was read from a sample of itself.** Limits
raised to 400 files / 4 MB.

## D3 — Stars are not used for ranking, and the correction was withdrawn
**2026-08-03 → 08-04.** At n=40 the correlation with substance was −0.019; at
n=105 it was **+0.241 (p 0.013)** and the project withdrew its "stars carry no
information" claim on that basis. At n=2,260 it is **−0.007, p 0.73**, and the
bump decays monotonically across nested subsamples.
**The original claim is reinstated and the withdrawal was itself the error.**
Concretely: 58 repos with 50+ stars score ≤3 strict, and 86 repos with ≤2 stars
score ≥8.

## D4 — Size is normalised out before anything is ranked
**2026-08-04.** `rho(tree_files, S_strict) = +0.593` — the strict score was 59%
explained by **file count**, which is mechanical and gameable. `size_adjust.py`
fits it out (rho → 0.12). Validated against an external fact: of 19 repos that
provably model Kalshi's maker fee correctly, the raw score put **0** in its top
25 and the adjusted one **5**.

## D5 — `trust_me_bro` measures honesty, not substance
**2026-08-03 → 08-08.** Recorded as *uncorrelated* with substance at n=822
(+0.029, p 0.41); at **n=2,717** it is weakly **positive** (+0.064, p 0.0009),
median `s_adj` +0.19 against −0.20.
**Interpretation, and it is the right one:** making a results claim at all
requires having built something. The flag discounts a repo's *claims*, never its
code. `shortlist.py` must combine the axes because they are genuinely different
questions.
*(This decision propagated: `social-signal` had been treating the flag as
evidence against a tool and corrected it — `social-signal/DECISIONS.md` D12.)*

## D6 — Fee correctness is judged per series, never against a constant
**2026-08-03/04.** Corrections C1, C1a and C2. Kalshi's maker rate is one
quarter of taker with a multiplier defaulting to **zero**, and only **130 of
12,396 series** charge makers — but those are the liquid ones, including
`KXATPMATCH` and `KXWTAMATCH`.
**C1a is the subtle one:** applying the published maker rate *without checking
the series' `fee_type`* is wrong, and only repos careful enough to model maker
fees at all can make that error. Two of the most rigorous repos in the corpus do,
on 15-minute crypto series where **zero** maker fee applies. Invisible to any
constant-vs-schedule check, **because the constant is correct.**

## D7 — A no-README repo is gated on its code, not dropped
**2026-08-03.** 77 repos had been dropped purely for having no fetchable README,
a real false-negative channel: a repo with an on-topic codebase and no README was
invisible to the topic gate. `run_gates.py` now reads the code, paths included,
since a file named `kalshi_client.py` is itself a venue term.

## D8 — Reading is the deliverable; scoring only decides what to read
**Throughout.** 4 repos read in full produced **6 defects invisible to every
computed component**, in repos scoring 9 and 10 — a fee model contradicting its
own instrument metadata, an MIT badge with no licence, a "self-learning" feature
the README elsewhere calls a placeholder, 42 of 104 files committed `.pyc`.
**Recorded bias:** repos are selected for reading *by* the strict score, and
rigorous repos score well *because* they are rigorous, so **the corpus is almost
certainly less honest than the repos read.**

---

## Open audit items

- **The KalshiEX Rulebook has never been read** and is the only open item that
  could change the venue answer. `kalshi.com/regulatory/rulebook` yields 581
  characters from 145 KB of HTML and an empty body in a real browser.
- **Polymarket's terms are not retrievable** — `/tos` returns 200, sets the
  correct page title and renders the homepage body. "Read it in a browser" is
  withdrawn.
- **The strict scorer is a second draft, not a validated instrument.** S4 cannot
  work by keyword and should be treated as noise.
- **Two databases, two machines**, both correct and not comparable. Always state
  which machine a coverage figure came from.
