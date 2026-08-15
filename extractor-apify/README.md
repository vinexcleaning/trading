# extractor-apify

**Which social platforms are worth paying a vendor for, decided by spending as
close to nothing as possible.**

Owned by the `extractors` chat. Created 2026-08-14 from
`coordinator/mailbox/extractors/001`.

Three questions, in the order they are cheapest to answer:

1. **Bluesky is free.** `social-signal/PLATFORMS.md` records it as closed. That
   is wrong, and the correction is in `reports/BLUESKY.md`.
2. **One paid trial across X, TikTok and Instagram**, inside Apify's $5 free
   credit, asking the same question of each so the answers are comparable.
3. **Is Apify the right vendor at all** — against Bright Data, ScrapingBee,
   Zyte, Firecrawl and ScraperAPI.

---

## ⚠ The credential rule

The Apify token lives at **`C:\Users\vinig\keys\apify.txt`** — **outside this
repo, which is public.** It is read at runtime, never copied here, never
printed, never logged, never put in an error message.

`tests/test_no_secrets.py` enforces that. It scans **every file** in this
folder, not only `.py`, because the incident it exists to prevent was a token
pasted into a chat and the things in a repo that most resemble a chat are the
Markdown files. It carries one planted violation per credential shape, so a
guard that has quietly stopped working fails loudly.

```bash
py -3 -m pytest extractor-apify\tests -q
```

## What is here

| file | what it does |
|---|---|
| `src/probe_bluesky.py` | asks 11 Bluesky routes whether they answer logged out |
| `src/ua_test.py` | does Bluesky serve an honest client, or only a browser string |
| `src/bluesky_fetch.py` | collects posts and reply threads. Free, keyless |
| `src/unit_control.py` | re-scores the sibling corpus so platforms are compared on the same unit |
| `src/score_corpus.py` | gate + rubric + the shuffled placebo |
| `PREREGISTRATION_BLUESKY.md` | written before any post was scored |
| `reports/` | the findings |

Everything uses `py -3`. No venv, no dependencies outside the standard library.

## Out of scope, deliberately

**Google Maps.** It is the largest thing on Apify by user count and it is local
business data — that belongs to **`Vinex-OS`**, not this repo (`CLAUDE.md` §7).
Noted and stopped.

**Going round any platform's stated rules.** Buying from a vendor is a
different act from evading a robots policy, and the line does not move because
a vendor is willing to stand on the other side of it.
