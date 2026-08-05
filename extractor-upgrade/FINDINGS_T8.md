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

---

# The comment pass landed — and it did not go how I said it would

3,272 comments across 374 threads. **3,886 items scored.**

## 1. Comments did not rescue the corpus. They diluted it.

| | non-SKIP | rate |
|---|---|---|
| stories | 70 / 614 | **11.4%** |
| comments | 127 / 3,272 | **3.9%** |
| whole corpus | 197 / 3,886 | **5.1%** |

I predicted *"the substance is in the comments."* **Absolute yield nearly
tripled — 70 non-SKIP items became 197 — and the RATE more than halved.** Most
HN comments are short conversational replies with nothing for a substance rubric
to hold on to, and 88.5% SKIP became **94.9%**.

Both readings are true and they answer different questions. *"Is a comment worth
collecting?"* — mostly no, 25 comments per story to find 0.34 useful ones.
*"Is the comment pass worth running?"* — yes, it produced 127 items that did not
exist before, and the best of them are better than anything in the stories layer.

## 2. What the good comments actually contain

Every one of these lands on a thread this repo has already closed:

> **"I spent almost 6 years trading crypto. Our best month's volume was $6B.
> Nothing we tried with usual strategies worked consistently. Backtesting
> parameters, ML with smart feature selection, boosting, neural networks —
> everything failed out of sample."**
>
> A practitioner at $6B monthly volume reaching this programme's own core
> result, unprompted, on a different asset class. `S=7 H=6`.

> **"In backtesting it was phenomenal. While executing though, trading fees,
> slippage and other factors negated all the advantages."**
>
> The backtest-to-live collapse, stated in one sentence by someone it happened
> to.

> *On PredictIt's long shots:* **"PredictIt specifically encourages these long
> shots to be over weighted thanks to their $850 risk limit in any given
> market."**
>
> A **structural mechanism** for long-shot overpricing — a position limit that
> caps how much informed money can correct it. `youtube-signal` has the same
> bias measured on Kalshi (5¢ contracts resolve YES 4.18% across 72M trades) and
> **no mechanism attached to it.** This supplies one.

> *On a prediction-market microstructure paper:* **"an expected loss of 0.57¢ on
> a 1¢ contract implies an expected gain of 0.43¢ on a 99¢ contract, or a 5.75ppt
> edge… Small edges can be easily eaten [by the fee structure]."**
>
> Someone doing this repo's own cost-bar arithmetic in a comment box, and
> reaching the same place: the edge is real and smaller than the cost of
> reaching it.

## 3. ⚠ HN did NOT find a repo that GitHub search missed — and I nearly said it did

The obvious cross-corpus test: 90 GitHub repos are named across the HN corpus,
**18 trading-relevant, and 17 of those 18 are absent from `signal-github`'s
4,017.** That looked like a retrieval failure worth reporting.

**It is not, and checking killed it.** Only **two** of the 18 are
prediction-market repos at all:

| repo | status |
|---|---|
| `rodlaf/kalshimarketmaker` | **already in the corpus** — 226★, alive, pushed 2026-04-14 |
| `Gabagool2-2/polymarket-trading-bot-python` | **HTTP 404 — does not exist** |

The other 16 are Binance bots, `quantopian/zipline`, `awesome-quant`,
`OpenHFT/Chronicle-Queue` — things `signal-github`'s topic gate **correctly
excludes**. The dramatic-looking 17 is explained almost entirely by scope, not
by retrieval.

> **So the negative result is the finding, and it is a good one:
> `signal-github`'s six retrieval axes have complete coverage of the on-topic
> space as probed from outside.** Nobody had ever tested that from a corpus
> built independently, and it has now been tested and passed.
>
> Recorded because the 17-of-18 framing survived three of my own commands before
> I checked what the 17 actually were. **A striking ratio with a mixed
> denominator is not a finding.**

## 4. Where that leaves Hacker News

**Keep it, at low priority.** It is permitted, keyless, free, and it produced
four practitioner statements that land on closed threads — one of which supplies
a *mechanism* for a bias this repo had only measured. But 5.1% non-SKIP over
3,886 items is a thin seam, and the repo-overlap test says it adds no code
coverage at all.

Its real value is the one thing no other corpus here has: **people who traded
professionally, writing about why it stopped working, with no product to sell.**
