# BLUESKY.md — it was never closed, and it is still not worth much

**As of 2026-08-14.** Pre-registered in `PREREGISTRATION_BLUESKY.md`, written
before any post was scored.

**Two separate answers, and they point in opposite directions:**

1. **The access answer is good.** Bluesky is open, free, permitted in writing,
   and needs no account. `social-signal/PLATFORMS.md` had it recorded as closed
   and that was wrong.
2. **The content answer is a null.** 3,671 posts produced **zero** items
   carrying a claim with a real number attached. Not "few". Zero.

---

## Part 1 — the access correction

`PLATFORMS.md` recorded Bluesky **closed** because
`public.api.bsky.app/xrpc/app.bsky.feed.searchPosts` returns **403**. That is
true and it reproduces today. **It is true of one host.**

| host | logged-out `searchPosts` |
|---|---|
| `public.api.bsky.app` | **403** |
| **`api.bsky.app`** | **200 — 100 posts, full text, timestamps, reply counts** |

**It is not User-Agent filtering.** `src/ua_test.py` runs seven clients against
both hosts, twice each — a browser string, an honest research string, a bare
project name, Python's default, `curl`, and an **empty** User-Agent. All seven
get 200 on `api.bsky.app`. All seven get 403 on `public.api.bsky.app`.

That matters because of the standard this repo already applies. Reddit's `.json`
and TikTok's `/tag` were closed here on the rule that *"a User-Agent string is
not consent"*. **Nothing is being talked round on Bluesky** — an honest client
that says what it is gets served, and the robots file agrees in words:

```
# Crawling the public parts of the API is allowed. HTTP 429 ("backoff")
# status codes are used for rate-limiting.
User-agent: *
Allow: /
```

**Six of eleven routes answer logged out**: post search, account search,
profiles, author feeds, popular custom feeds, handle resolution.

### Two constraints worth knowing before anyone builds on it

**The cursor does not work.** A search returns 100 posts and a cursor; feeding
that cursor back returns **403** — immediately, and again after waiting 20 and
60 seconds — while the same call without it returns 200 every time. `since` and
`until` **do** work, so the collector walks backwards in time in windows,
halving a window whenever it comes back full.

**The host drops requests at random.** Plain 403s and bare TCP timeouts, both
recovering on a retry a minute later. **That is very likely what produced the
original wrong entry** — one 403, taken at face value, closed a platform in this
repo's own documentation for ten days.

## Part 2 — what came back, and it is not worth having

**3,671 posts** over the four dense venue terms (`kalshi`, `polymarket`,
`prediction market`, `prediction markets`, `event contract`), covering
2025-07-11 to 2026-08-15. Scored on `social-signal/src/rubric.py` with the gate
copied verbatim from `reddit_score.py`, so the numbers land on the same axis as
everything already published.

| platform | items | collected | clear the gate | recommend-grade | **carry a real number** |
|---|---|---|---|---|---|
| **reddit** (post + comments) | 41,552 | by `social-signal`, to 2026-08-05 | 4,804 (11.6%) | **301** | **302** |
| **mastodon** (post only) | 19,281 | by `social-signal`, to 2026-08-05 | 2,607 (13.5%) | 4 | **9** |
| **bluesky** (post only) | 3,671 | here, 2026-08-14, posts dated 2025-07-11 → 2026-08-15 | 837 (**22.8%**) | 1 | **0** |

**The three corpora were collected at different times by different code**, and
only the rubric and the gate are shared. They are comparable on *what a document
contains*, not on *what the platform was talking about that week*.

**Bluesky clears the on-topic gate at nearly twice Reddit's rate and produces
nothing.** That is the Mastodon result again, on a third platform, and it is
now three for three: **high passage, no substance, and the binding constraint is
length.**

### Expanding the reply threads helps, and it is still nearly nothing

**322 of the 809 posts with replies were expanded**, pulling 1,997 replies. The
collector was stopped there — `api.bsky.app` drops requests often enough that
the remaining 487 would have taken hours for no likely change of answer. That is
a shortfall, not a finding, and it is stated rather than rounded away.

| unit | documents | clear the gate | recommend-grade |
|---|---|---|---|
| post alone | 3,671 | 837 (22.8%) | 1 |
| **thread (only the 322 with replies)** | 322 | **206 (64.0%)** | **1 (0.49%)** |

**So the thread unit roughly triples gate passage and quadruples the
recommend rate** — H-BS2 in the pre-registration was right in direction.
**And one item in 206 is still one item.** The direction is real; the size is
not worth building on.

### The single best item in the corpus, read in full

One thread is genuinely on topic, genuinely numeric, and worth quoting because
it is the whole ceiling of what this platform produced:

> A post arguing that Polymarket bot builders optimise the wrong variable —
> chasing a bigger edge per trade instead of frequency. It cites a bot running
> **113 trades an hour at an average size of $2.12**, reportedly turning that
> into **$500K in 5 months**.

That is a mechanism, a rate, a size and a period — which is why the rubric
scored it highest. **And it is a second-hand claim about somebody else's bot,
from an account that sells bot-building, with no artifact, no win rate and no
denominator on the $500K.** By this repo's own `H6`/`H2` standard it is a
performance claim you cannot check.

**It is worth reading. It is not worth acting on.** And it is the best of 3,671
posts.

### The one recommend-grade item is a false positive, and reading found it

The single item the rubric called recommend-grade is a **Craft CMS package
announcement**. It matched because the phrase *"a neutral audit event contract"*
contains the search term `event contract`. It has nothing to do with prediction
markets.

**So the honest count of recommend-grade items in 3,671 Bluesky posts is zero.**

### And all three "sample size" hits are the words "30 days"

The rubric's `S3` component fired three times. Read in full, all three are
duration phrases, not sample sizes:

| what fired | what it actually says |
|---|---|
| *"in prediction markets that fit the mandate of being under 30 days"* | a trading mandate |
| *"topics can only be offered if their outcome is at least 30 days away"* | a Canadian regulation |
| *"six possible events must happen within a 90 day period"* | the rules of one market |

### ⚠ "Zero" is an absence claim, so here is what would have shown it

**Three of the nine errors recorded in `coordinator/REFLECT.md` were absence
claims and all three were wrong.** So this one does not rest on the `S3`
pattern, which is a lexicon and can only see what it was written to see.

`S3` requires **two or more digits** next to a countable noun. It is blind to
single-digit counts, written numbers, win–loss records and "N out of M". A
second, wider pattern was run over the **905 gate-passing documents that did not
fire `S3`**, looking for exactly those shapes.

**It found 13 candidates. All 13 were read in full. None is a performance
claim.** They are: thread numbering (`7/11`, `8/10` — the post's own position in
a series), dates inside URLs, one French Revolution date range, and one
order-flow statistic (*"82 whale trades routed $300K over the last 24h"*) which
is a market observation, not anybody's record.

**So: zero of 3,671 posts carry a performance claim with a denominator, checked
by two patterns and then by reading every candidate either one raised.** The bar
the mailbox set was *13 Reddit threads producing one stranger's study of 4,604
resolved markets*. Bluesky produced nothing of that shape at 280 times the
volume.

### What the corpus IS full of

News reaction. The highest-engagement on-topic item in the whole corpus — 98
replies, 4,511 likes — is a news report that a Seattle judge barred Kalshi from
operating in Washington State. That is real and it is worth knowing, and it is
**journalism the wire already carried**, not analysis anyone did.

Component firing rates say the same thing precisely. Of everything that cleared
the gate: **S5 (names a tool or site) 11.0%**, **S1 (names the cost side) 5.9%**,
**S4 (gives a mechanism) 5.0%**, and then it falls off a cliff — **S2 0.1%,
B1 0.2%, B2 0.0%, B5 0.0%, H3 0.0%, H4 0.0%.**

**Nobody on Bluesky shows their working.**

## Part 3 — what this says about the instrument, not the platform

Two things fell out of the controls that matter more than the Bluesky answer,
because they apply to numbers already published in this repo.

### The rubric's `S3` is 37% duration phrases on Reddit too

Splitting `S3`'s pattern into its clauses across the Reddit corpus:

| | count | share |
|---|---|---|
| S3 fired | 479 | — |
| ...on a real countable unit (`n=`, "614 trades", "196 markets") | **302** | **63%** |
| ...**only** on a duration like "30 days", "14 Days Free" | **177** | **37%** |

**Reddit's real sample-size rate is 6.3 in 100 of what clears the gate, not the
10.0 the raw component count gives.** The claim survives — Reddit genuinely has
302 items carrying a countable denominator, and that is the finding — but the
headline number was inflated by about a third.

On Mastodon the same split gives **9 real out of 14**. On Bluesky, **0 out of
3**.

### Roughly half of "recommend-grade" survives destroying the word order

`src/unit_control.py`, on 4,000 Reddit threads with the words shuffled inside
each document so no phrase survives:

| | clear the gate | recommend-grade |
|---|---|---|
| real word order | 16.5 in 100 | **11.4 in 100** |
| **words shuffled** | 14.7 in 100 | **5.6 in 100** |

Some components are legitimately single-word, so this is not a broken
instrument. But it means **a recommend verdict is about a 2-to-1 signal over
vocabulary alone**, not the clean read the rate implies. **Nothing was
adjusted** — changing a rubric after seeing what it does to a corpus is how a
measurement becomes an opinion.

### The Reddit-vs-Mastodon gap is mostly real, and I expected it not to be

`PLATFORMS.md` compares Reddit *threads* against Mastodon *posts* —
`social.db` holds 12,846 comments and every one belongs to a Reddit post.
Re-scoring Reddit on post text alone moves the gap from **41× to 34×**.

**One part in six was the unit of observation. Five parts in six is the
platform.** The published conclusion stands, slightly smaller.

## What was NOT tested

Required by `CLAUDE.md` §9c Step 7, and written because a dead idea with no such
list looks completely dead.

- **Six of the ten pre-registered search terms** — `manifold markets`,
  `kalshi bot`, `polymarket bot`, `predictit`, `betfair exchange` and
  `event contract` beyond its first tranche. The four collected are the dense
  ones; the sparse ones were dropped when the host's flakiness made them slow.
  **A specialist community could live under a term not searched.**
- **487 of the 809 reply threads.** 322 were expanded before the host's
  flakiness made it not worth the wall-clock. The thread result rests on 322,
  and one recommend-grade item out of 206 is a number that could move.
- **Following accounts rather than searching text.** `searchActors` and
  `getAuthorFeed` both work logged out. Someone serious about prediction markets
  posts constantly and would be found by **who they are**, not by whether one
  post happens to contain a number. **This is the most likely place a positive
  is hiding and it was not tried.**
- **Custom feeds.** `getPopularFeedGenerators` answers. Other people have
  already built topic filters and none was read.
- **Quote posts and link-outs.** A post pointing at a Substack with the study in
  it scores nothing here and is worth everything.
- **Non-English.** No language filter was applied and no non-English term was
  searched.
- **Any date-weighting.** The corpus is heavily recent because search returns
  newest-first inside each window.

---

## The Referee — what stands, what is downgraded, what is his

Both checkers were run: `py -3 coordinator\reflect.py --file` on this draft, and
`--referee`.

### 1. Stands

- **Bluesky is open, free and permitted, and `PLATFORMS.md` was wrong.** What
  makes it survive: seven different clients including an empty User-Agent and
  `curl`, on two hosts, twice each, plus a robots file that permits it in words.
  This is not one measurement.
- **The search cursor is refused while the same call without it is served.**
  Retried at 0, 20 and 60 seconds. Reproducible on demand.
- **Zero of 3,671 posts carry a performance claim with a denominator.** Two
  different patterns were run — the rubric's own, and a wider one built to catch
  what the rubric is blind to — and **every candidate either raised was read in
  full**, 16 in total. That is the shape an absence claim has to have here.
- **The rubric's `S3` is 37% duration phrases on Reddit.** Arithmetic on the
  pattern's own clauses over 479 firings, not a judgment.

### 2. Downgraded

- **was:** "Bluesky is another discovery layer like Mastodon."
  **now:** "Bluesky looks like Mastodon on every measure taken, and the measures
  taken are all text-search-based. Following accounts and reading custom feeds
  were not tried, and both work logged out."
  **because:** the Critic's narrowing question. Searching text is one way in and
  I used only that one. Someone serious posts constantly and would be found by
  who they are.

- **was:** "Reddit has 479 items carrying a sample size, 10.0% of what clears
  the gate."
  **now:** "Reddit has **302**, **6.3%** of what clears the gate. The other 177
  fired only on a duration like *30 days*."
  **because:** splitting the pattern into its clauses and reading a sample.

- **was:** "the published Reddit-vs-Mastodon gap is confounded by the unit of
  observation."
  **now:** "it is confounded, and the confound is worth about one part in six —
  41× becomes 34×. **The published conclusion substantially stands.**"
  **because:** the control was run and it went against my hypothesis, not for
  it.

### 3. For the user — genuinely unresolved

**One, and it is a spending question, so it is his by definition.**

- **the question:** is a second free social platform worth the code that
  collects it?
- **one side says:** Bluesky costs nothing, is permitted in writing, and it
  carries live news reaction fast — the Washington State ruling on Kalshi was
  the highest-engagement item in the corpus. As a *tripwire* that something has
  happened, it works.
- **the other side says:** three platforms have now been measured and all three
  short-form ones produce nothing with a number in it. Adding a fourth
  discovery layer is the "collect more" move that `PLATFORMS.md` has already
  recorded failing three times.
- **what would settle it:** the account-following route, which was not tried and
  is free. If following 50 named prediction-market accounts for a fortnight
  produces even one item with a denominator, the answer changes.

**And one non-finding stated out loud rather than left off:** nothing in this
work disagrees with anything another session has published. The `PLATFORMS.md`
Bluesky row is corrected, not contradicted — its 403 measurement was accurate
and reproduces today.

## How to reproduce

```bash
py -3 extractor-apify\src\probe_bluesky.py      # which routes answer
py -3 extractor-apify\src\ua_test.py            # is it User-Agent filtering
py -3 extractor-apify\src\bluesky_fetch.py      # collect
py -3 extractor-apify\src\unit_control.py       # the unit + placebo controls
py -3 extractor-apify\src\score_corpus.py       # gate, rubric, placebo, top items
```
