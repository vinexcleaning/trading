# TASK 3 — the extractors pointed at extraction, verified by running

`social-signal` already did the scraper half of this brief
(`reports/T4b_existing_extractors.md`) and reached the conclusion that decides
it: **existence is not the question.** Scrapers exist for everything. X was
killed on *terms* and TikTok/Instagram on *measured substance*, and a working
tool reopens neither. This covers what it did not.

Full tables: `reports/T3_sources.md` (gitignored).

---

## 1. Four new sources are open, two are explicitly closed, and one closure is worth reading

Every candidate got three checks, in this order, and **the third is the one
prior sessions skipped** — which is why prior sessions listed sources that
turned out to be 404 or 403:

1. **ROBOTS** — does the host's own machine-readable statement permit it
2. **LIVE** — does it return bytes, right now, with no key
3. **CONTENT** — does what came back contain what it claims

| source | kind | robots | HTTP | content | what came back |
|---|---|---|---|---|---|
| **Hacker News, official Firebase API** | forum | **permits** | 200 | PASS | 500 story ids |
| **Discourse `/latest.json`** | forum | **permits** | 200 | PASS | 30 topics |
| **PodcastIndex `search/byterm`** | podcast | **permits** | 200 | PASS | 12,440 bytes, keyless |
| **arctic-shift (Reddit archive)** | forum | **permits** | 200 | PASS | re-verified, still open |
| Hacker News, Algolia index | forum | *no robots.txt* | 200 | PASS | 586 stories on "polymarket" |
| SEC EDGAR full-text search | filings | *no robots.txt* | 200 | PASS | 23,684 bytes |
| Kalshi `/exchange/status` | venue | *no robots.txt* | 200 | PASS | `{"exchange_active":true,…}` |
| **Lobsters** | forum | **FORBIDS** | 200 | PASS | 25 stories — *not taken* |
| **iTunes / Apple Podcasts** | podcast | **FORBIDS** | 200 | PASS | `Disallow: /search*` |

**Four sources are open today that no extractor here uses:** Hacker News,
any Discourse forum, the open podcast directory, and SEC EDGAR.

### `PodcastIndex` is keyless, and Apple is not the way in

The probe was written expecting PodcastIndex to demand a key. It returned
**12,440 bytes with no header at all**, and `robots.txt` permits it. Apple's
directory — which would have been the obvious first stop — carries
`Disallow: /search*` and `Disallow: /*/lookup?`, so it is closed. **The open
door and the obvious door are different doors**, which is the same shape as
`arctic-shift` replacing Pushshift.

Podcasts matter here because a podcast is a **10–90 minute source with a
transcript-shaped audio track and no visual layer at all** — precisely the
material where transcript-only extraction loses nothing, unlike the video
corpus where 4.9% of runtime is screen-only.

### ⚠ Lobsters refuses, and it refuses AI specifically

```
User-agent: *
Crawl-delay: 1
Disallow: /

Content-Signal: ai-input=no, ai-train=no, search=yes
```

`/t/programming.json` returns **200 and 12,772 bytes of perfectly good data**.
It was not taken. `Content-Signal: ai-input=no` is not ambiguous and is not a
technical obstacle — it is a statement, in a machine-readable field, that this
content is not for AI input. Recorded here because a future session will find
that endpoint working and needs to know it was already looked at and declined.

---

## 2. ⚠ My own robots parser produced a FALSE FORBID, and the fix matters beyond this file

The first run reported **Hacker News's official API as forbidden.** It is not.

```
# hacker-news.firebaseio.com/robots.txt
User-agent: *
Allow: /*.json$
Allow: /*.json?*$
Disallow: /
```

The JSON API is **explicitly allowed** and only the HTML is not. My parser read
the `Disallow` and ignored the `Allow`, so it called a documented public API
off-limits.

> **This is the mirror image of the false-kill problem this session has now hit
> three separate times** — a probe sampling the wrong thing and failing toward
> the conservative answer. Here it failed toward *refusal* instead of toward
> *death*, and refusing something you are permitted to use costs exactly as
> much as using something you are not.

Fixed to the actual standard: **longest match wins between `Allow` and
`Disallow`**, with `*` and `$` wildcards. Re-running flipped two rows —
HN Firebase FORBIDS → **permits**, iTunes permits → **FORBIDS** (`Disallow:
/search*`, which the naive parser had missed in the other direction).

**A robots check that does not implement `Allow` is not a robots check.** That
belongs in `GUARDS.md`.

---

## 3. Chapter detection needs no new source at all

**396 of 1,197 video descriptions already in the database carry three or more
chapter markers — 33.1%.**

YouTube chapters live in the description. The descriptions are already on disk.
A chapter list is an **author-written table of contents**: the cheapest possible
answer to *which ninety seconds of this forty minutes matter*, and a strictly
better `watch_segment` seed than the phrase list in `frames.cues()`, because the
author wrote it and the phrase list is guessing.

**A third of the corpus has been carrying a free table of contents that nothing
reads.** That is the highest ratio of value to work found in this task, and it
required no network call, no new dependency and no permission from anybody.

---

## 4. Ranking and credibility scoring — the brief's premise holds

11 GitHub searches across misinformation detection, source-credibility ranking,
claim verification, learning-to-rank and reciprocal rank fusion; results,
liveness, licence and last push in `reports/T3_sources.md`.

The brief is right that this is solved-ish and that reinventing it is waste —
but **Task 1 changes what "it" is.** The measured gap in this project's rubric
was never the ranking function:

| what the corpus needed | is it a ranking problem? |
|---|---|
| staleness — is the library still alive | **no**, it is one API call |
| polarity — is the cost side named or accounted for | **no**, it is a parser bug |
| denominator — is there an `n` at all | **no**, it is an absence, and absences do not embed |
| unreachable components with weights | **no**, it is a code defect |

An off-the-shelf credibility model would have improved **none of the six
defects Task 1 found.** Adopting one before the instrument was graded would
have swapped a known-bad rubric for an unknown one — which is the trade
`social-signal/src/rubric_audit.py` refused to make, for the same reason.

**So the recommendation is: do not adopt one yet.** The thing worth taking from
that literature is not a model, it is the *evaluation discipline* — and the
labelled test set built in Task 1 is that discipline, already in the repo,
already run.

---

## 5. What would actually be worth building next, ranked

1. **Read chapters out of the descriptions.** Free, offline, 33.1% coverage,
   already-owned data, and it improves `watch_segments` — the number that
   decides whether extraction beat watching.
2. **Point `youtube-signal`'s pipeline at podcasts via PodcastIndex.** Same
   rubric, same reader, longer-form material, no visual layer to miss, and
   permitted in writing.
3. **Hacker News as a fifth corpus.** Permitted by an explicit `Allow`, keyless,
   and its trading and market-microstructure threads are the demographic that
   states an `n`.
4. **Discourse forums.** Every Discourse instance exposes `/latest.json` and
   `/t/<id>.json`. Quant communities run on Discourse.
5. **Nothing from the credibility-model literature, yet.** See 4.
