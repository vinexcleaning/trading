# Chapters — a free index, and a prediction of mine that failed

`src/chapters.py`, read-only, offline, zero network calls. Full table:
`reports/T7_chapters.md`.

| | |
|---|---|
| descriptions already on disk | **1,197** |
| satisfying YouTube's own chapter rule | **367 (30.7%)** |
| total chapters | **3,384** · median 8 per video |
| titles that predict screen content | **538 (15.9%)** |
| structural noise (intro/outro/sponsor) | 166 (4.9%) |
| videos already read that have chapters | **20 of 38** |

The rule is implemented rather than assumed: YouTube renders a chapter bar only
when the first stamp is `0:00`, there are at least three, and they are at least
10 seconds apart. My first pass counted any description with ≥3 timestamps and
got **396**; enforcing the actual rule gives **367**. The 29 difference are
videos whose descriptions mention times without ever producing chapters — and
the difference between *"the author wrote a contents list"* and *"the author
mentioned some times"* is exactly the distinction this programme keeps getting
wrong in the other direction.

---

## ⚠ The claim I made yesterday is not supported

In `FINDINGS_T3.md` I wrote that a chapter list is *"a strictly better
`watch_segment` seed than a phrase list, because the author wrote it and the
phrase list is guessing."*

**Measured: 2 of 19 `watch_segments` (11%) fall inside a chapter whose title
predicts screen content.**

That is not the agreement I predicted. n=19 is small, so this does not establish
that chapters are *worse* — what it establishes is that **the two signals are
measuring different things**, and my sentence assumed they were measuring the
same thing:

- a **chapter** indexes a *topic*, and spans ~2.5 minutes on a 20-minute video
- a **watch_segment** indexes a *moment that needs eyes*, and spans ~60 seconds

A 60-second P&L reveal can sit inside a chapter titled "Strategy explained"
without either label being wrong. **Chapters are a table of contents. They are
not a screen detector, and I wrote them up as one before measuring.** The claim
is withdrawn; the tool is not.

---

## What chapters ARE good for, measured

### 1. Retrieval with no transcript read at all

```bash
python src/chapters.py --search "p&l|live account|results|my account|balance"
```

Returns, among others — **none of these videos has ever been read**:

| video | chapter title, verbatim |
|---|---|
| `-F0dZ2GxSuA` | *"Live results after a few hours"* · **"3-hour results: $13 profit"** |
| `wJ3ZtOMKMDo` | *"my results after 24h of copytrade"* |
| `UhLJiW91pRI` | *"12-Hour Results: Uncovering Iran Market Whales"* |
| `lA9G7s1HKzM` | *"1st Test Results"* · *"2nd Results"* |
| `RaUZdZPVKsU` | *"Results Overview"* |

> **`-F0dZ2GxSuA`'s chapter title carries the result AND the period: "3-hour
> results: $13 profit".** A denominator, in a structured field, for free, on a
> video nobody has read. That is the shape the whole rubric exists to find, and
> it was sitting in a column that had been fetched and never queried.

The authors' own vocabulary for their screen sections, across 3,384 chapters:
`live` 78 · `code` 68 · `api` 64 · `setup` 63 · `results` 56 · `order` 41 ·
`profit` 40 · `demo` 30 · `dashboard` 27 · `backtest` 24 · `wallet` 21.

### 2. Labelling where the three permitted frames landed

The permitted frame sample sits at fixed 25/50/75% and cannot be moved. But
knowing which chapter each frame fell in turns a lottery ticket into a
**labelled** observation — and on the first video checked it immediately
sharpened an open finding:

> **`86AlV6174KI`** — the corpus's only perfect `S=10 B=10`.
> Its author labels the timeline:
> `5m21s Installing Claude Code & TraderDev MCP Server` ·
> `7m23s Running Your First Strategy Backtest` ·
> `13m41s Coding & Optimizing Your Strategy`.
>
> The permitted frames land at **~8m19s → "Running Your First Strategy
> Backtest"** and **~16m39s → "Coding & Optimizing Your Strategy"**.
>
> **Both frames show a man talking to camera against a garden wall.** No
> terminal, no code, no backtest.
>
> That does not prove the backtest is never shown — a chapter is 6 minutes long
> and a frame is one instant. But the video's `TENSION` flag now has a second,
> independent leg: an on-screen overlay reading **"NO CODE"**, and two frames
> that landed inside chapters named for code and backtesting and contained
> neither. Two free signals, pointing the same way, on the highest-scored video
> in the corpus.

**Chapters and frames cross-check each other, and neither costs a transcript
read.** That is the useful finding here — not the one I predicted.
