# Hacker News — a fifth corpus, and two bugs of mine on the way there

`src/hn.py`. Cost $0.00, no key. Writes only to `data/hn.db`; no sibling
database is opened for writing anywhere in this project, and four sibling
Python processes were live throughout.

---

## The permission is two different answers, and they are not treated the same

```
hacker-news.firebaseio.com/robots.txt
    User-agent: *
    Allow: /*.json$        <- the API is EXPLICITLY permitted
    Allow: /*.json?*$
    Disallow: /               only the HTML is not

hn.algolia.com/robots.txt     404 — no robots.txt is served at all
```

**Every byte of content comes from the Firebase endpoint.** Algolia is used only
to turn a search term into a list of integer ids — no text, no author, no
comment reaches the corpus through it — because a host serving no `robots.txt`
is **undecidable**, not permitted.

That distinction is enforced by construction rather than by discipline, because
this project has now got it wrong in *both* directions inside one week: a false
kill (counting a bare-host 404 as death) and a false forbid (ignoring an
`Allow:` line and calling HN's own API off-limits).

---

## ⚠ Two bugs of mine, and the second is the dangerous kind

### 1. The query design was self-defeating

Algolia **AND-matches every term**, so a long insider phrase matches nothing.
Probed directly rather than guessed:

| query | hits |
|---|---|
| `adverse selection market making` | **0** |
| `adverse selection` | 20 |
| `market making` | 1,343 |
| `de-vig sportsbook` | **0** |
| `walk forward backtest overfitting` | 1 |
| `walk forward` | 79 |

Long phrases are how a human *describes* a concept and are not how a search
index is *queried*. The insider family returned 51 stories against the beginner
family's 117 for that reason alone. Rewritten to short terms; the insider family
now returns 298.

### 2. My own dedup decided the headline number

`collect()` skipped any id it already held, so a story found by **both** query
families was recorded under whichever family reached it first. That makes the
F1–F2 overlap **structurally zero regardless of what the corpus contains**.

The first run duly returned **Jaccard 0.000**.

> **I was one commit from writing that up as "the fourth independent corpus to
> reproduce the near-disjoint finding", beside `youtube-signal`'s 0.037 and
> `signal-github`'s 0.032 / 0.033 / 0.036.**
>
> It would have been a **fabricated corroboration of this programme's own
> result** — produced by a line of my code, and agreeing with three prior
> measurements, which is precisely the moment a number is least likely to be
> questioned. Nothing about it would have looked wrong.

Membership now lives in its own table so a story can belong to both families,
and the corpus was dropped and rebuilt.

---

## What the corpus actually says

| | |
|---|---|
| stories | **607** |
| F1 beginner / F2 insider | **312 / 298** |
| in **both** families | **3** |
| **F1 ∩ F2 Jaccard** | **0.005** |

**The direction reproduces on a fourth corpus with a completely different
retrieval engine.** The beginner and insider vocabularies find near-disjoint
sets.

> **The magnitude does not reproduce, and I am not claiming it does.** 0.005 is
> about seven times lower than the prior three, and the most likely reason is
> that **I wrote both term lists myself** and made them more vocabulary-disjoint
> than the video families were. A number whose inputs I chose is not an
> independent replication of a number somebody else measured. What survives is
> the direction — which is the part the retrieval design actually rests on.

### The corpus is stories only, and that is most of what is wrong with it

| verdict under rubric v2 | n |
|---|---|
| SKIP | **537 (88.5%)** |
| ABSORB | 33 |
| ABSORB_AND_RECOMMEND | 33 |
| BUILD_AND_RECOMMEND | 3 |
| ABSORB_RESULTS_DISCOUNTED | 1 |

Comments were skipped for speed — they are ~25× the requests. **On HN a story is
usually a headline and a URL with no body text at all**, so a substance rubric
has almost nothing to read.

**537 of 607 scoring SKIP is not a finding about Hacker News. It is a finding
about collecting the wrong half of it.** The substance is in the comment threads
— which is also where `social-signal` found its contradictions on Reddit — and
that pass is running.

The one thing the stories layer does surface for free is the **Launch HN for
Kalshi itself** (`33696486`, 148 points, **165 comments**) — the venue this whole
programme trades, announced by its founders, with 165 replies from people who
had no reason to be polite. That thread alone is worth the comment pass.

---

## Honest cost of the collection

- One Algolia call timed out (`market making`, the single highest-yield insider
  term at 1,343 hits) and the run continued with **0 stories from it**. The
  corpus is missing that term and no retry was attempted.
- 607 stories from 20 queries at 40 hits each = a hard ceiling of 800; the
  binding constraint is Algolia's `hitsPerPage`, not the corpus.
- Neither number is a sample of Hacker News. They are a sample of twenty
  searches I chose.
