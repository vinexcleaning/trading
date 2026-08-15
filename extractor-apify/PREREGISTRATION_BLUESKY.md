# PREREGISTRATION_BLUESKY.md

Written **2026-08-14, before any post was scored.** What had happened before
this file existed: `src/probe_bluesky.py` was run, 11 routes were tested for
whether they answer at all, and 25 posts for the word `kalshi` were printed to
check the payload had text and timestamps in it. **No post has been put through
the rubric.** That peek is recorded here rather than hidden, because a
pre-registration that omits what was already seen is worth nothing.

---

## The question

**Is Bluesky worth collecting from, measured the same way every other platform
in this repo has been measured?**

Not "does it return posts" — it does. The question is whether what comes back
carries claims with numbers attached, or whether it is another discovery layer
like Mastodon: a name, a link, and no argument.

## The hypothesis, stated so it can fail

**H-BS1.** Bluesky post text, scored on its own, behaves like Mastodon and not
like Reddit: it clears the on-topic gate at a high rate and reaches
recommend-grade at close to zero.

**H-BS2.** Expanding a Bluesky post into its reply thread moves it materially
toward Reddit. If it does not, Bluesky is a discovery layer and should be
weighted as one.

**What would make me drop it:** if fewer than 1 post in 100 clears the gate,
Bluesky is not worth the code that fetches it, whatever its reply threads do.

## The unit of observation

**One thread.** Root post plus every reply reachable at depth 6, concatenated —
the same unit `reddit_score.py` uses. Post-only is also computed and reported
separately, because the two are different objects and averaging them would hide
exactly the effect being tested.

**A count of posts is not a count of observations.** A thread of 40 replies is
one thread.

## The sample

- **Terms, fixed now, and narrow on purpose** — `PLATFORMS.md` records three
  separate retrieval failures in this repo, all from widening the net:
  `kalshi` · `polymarket` · `prediction market` · `prediction markets` ·
  `event contract` · `manifold markets` · `kalshi bot` · `polymarket bot` ·
  `predictit` · `betfair exchange`
- **Volume:** up to 1,000 posts per term, cursor-paginated, capped at 6,000
  posts total.
- **Threads expanded:** every post with 1 or more replies, capped at 800 thread
  fetches.
- **Date range:** whatever the search returns — Bluesky search is
  recency-ordered by default and the range is recorded after collection, not
  chosen.

## The control, because a pipeline that finds an edge in noise is broken

Two, and the first one is the important one.

**Control 1 — the unit control.** `social.db` holds 41,552 Reddit posts with
12,846 comments attached, and 19,281 Mastodon posts with **zero** comments
attached. So the published 35x gap between them compares Reddit *threads*
against Mastodon *posts*. Before Bluesky is compared to anything, Reddit is
re-scored **post-text-only** and the gap re-measured. If most of the gap
disappears, the platform ranking in `PLATFORMS.md` is measuring the unit of
observation and not the platform.

**Control 2 — the shuffled placebo.** The same gate and rubric are run over
Bluesky text with the words shuffled within each document. Every component in
`rubric.py` is a phrase pattern, so shuffling should collapse the multi-word
ones. If shuffled text scores anywhere near real text, the instrument is
counting single words and every rate it has ever produced is suspect.

## What gets reported either way

- How many items came back, how many cleared the gate, how many reached
  recommend-grade, split post-only and thread.
- **How many carried a sample size** — the `S3` component — because that is the
  bar the mail set, and it is the one thing that separates a study from an
  opinion.
- The best single item, quoted, with its link.
- **A list of what was NOT tested.** Required by `CLAUDE.md` §9c Step 7 and it
  is written whether the result is positive or negative.

## What this cannot answer

Bluesky's population is small and skews technical and American-political. A
null here does not transfer to X, and a positive here does not either. The
platforms are compared on the same terms and the same rubric; they are not
claimed to be the same population.
