# HANDOFF.md — extractor-apify

<!-- COORDINATOR-STATE
doing: paid trial on X/TikTok/Instagram is built and waiting on a Bright Data API key
left: run preflight, then the 5,000-record free trial, then score it on the same rubric
needs: yes - the Bright Data API KEY (not the account, which exists) saved to C:\Users\vinig\keys\brightdata.txt - steps in extractor-apify/GET_THE_TOKEN.md, five minutes, no card
-->

**Owner: the `extractors` chat.** Created 2026-08-14 from
`coordinator/mailbox/extractors/001`. Bluesky work 2026-08-14; the paid trial
built 2026-08-18.

---

## Where this got to

**Job 1 — Bluesky. DONE.** It is open, free, permitted in writing, and needs no
login. `PLATFORMS.md` had it recorded as closed and that is corrected inline.
The content answer is a clean null: **3,671 posts, zero carrying a claim with a
real number behind it.** `reports/BLUESKY.md`.

**Job 3 — the vendor question. DONE.** `reports/VENDORS.md`. Apify is real and
is the wrong place to start; Bright Data gives 5,000 records a month free.

**Job 2 — the paid trial. BUILT, and blocked on one credential.**

## ⚠ The blocker, precisely

**The account exists. The API key does not.** Those are different things — the
key is what lets a script use the account, and only he can create it.

Checked, not assumed: `C:\Users\vinig\keys\` does not exist, `BRIGHTDATA_TOKEN`
is unset, and nothing under his home directory matches `*bright*` or `*brd*`.

**`GET_THE_TOKEN.md` is the five-minute click-by-click**, verified against
Bright Data's current documentation on 2026-08-18 rather than written from
memory. No payment details at any point.

The moment the key lands:

```bash
py -3 extractor-apify\src\brightdata.py preflight
py -3 extractor-apify\src\brightdata.py run
```

`preflight` **spends nothing** — it reads the account, says which scraper it
would use for each platform and why, prints the exact request, and stops.

## What is in this folder

| file | what it is |
|---|---|
| `src/probe_bluesky.py` | 11 Bluesky routes, logged out. 6 answer |
| `src/ua_test.py` | 7 clients × 2 hosts × 2 tries. Not User-Agent filtering |
| `src/bluesky_fetch.py` | the collector. Walks time windows, because the cursor 403s |
| `src/unit_control.py` | re-scores the sibling corpus so platforms compare on one unit |
| `src/score_corpus.py` | gate + rubric + the shuffled placebo |
| **`src/brightdata.py`** | **the paid-trial client. Preflight first, hard budget cap, discovers dataset ids** |
| `tests/test_no_secrets.py` | credential guard. Every file, not just `.py` |
| **`tests/test_brightdata_safety.py`** | **the money guard. Budget cap and ambiguity refusal, both with planted violations** |
| `PREREGISTRATION_BLUESKY.md` | written before any post was scored |
| **`PREREGISTRATION_PAIDTRIAL.md`** | **written before any record was pulled** |
| `GET_THE_TOKEN.md` | the five minutes only he can do |
| `reports/BLUESKY.md` · `reports/VENDORS.md` | the findings |

**17 tests pass.** Run them with an explicit temp dir — Windows refuses to clean
the shared pytest one:

```bash
py -3 -m pytest extractor-apify\tests -q -p no:cacheprovider
```

## Three things the money guard actually enforces

Not comments — tests, each with a planted violation, because a guard nobody has
tested against a real violation is a guard nobody knows still works.

1. **It cannot spend past 5,000 records.** Spend is counted on records
   **returned**, not requested, because billing is per delivered record and
   counting requests would let an under-delivering run quietly buy a second
   helping. The check runs **before** each request. One test seeds the allowance
   as fully spent, replaces `trigger()` with a function that raises, and asserts
   the run returns cleanly having never called it.
2. **It refuses to guess which scraper to use.** Bright Data does not publish
   the dataset ids for X/TikTok/Instagram discovery — four documentation pages
   were read and none carries them — so the client asks the account. **If two
   scrapers match, or none does, it stops.** A test plants two matching X
   entries and asserts nothing is chosen.
3. **The key never enters this repo.** Read at runtime from outside it. The
   guard knows Bright Data's UUID shape *and* knows not to fire on a bare UUID,
   because snapshot ids look identical and a guard that cries wolf gets
   suppressed.

## Two findings that are not about any platform and matter more

**1. The sibling rubric half-survives a placebo.** 4,000 Reddit threads with the
words shuffled inside each document still score **5.6 per 100** recommend-grade
against **11.4** real. About half of what it calls good, it calls good on
vocabulary alone. **Nothing was adjusted.** `DECISIONS.md` D006.

**2. The rubric's sample-size component is 37% false positives on Reddit** — it
fires on phrases like *"30 days"*. Reddit's real rate is **6.3 per 100** of what
clears the gate, not 10.0. The claim survives; the headline was inflated by a
third. This is why the paid trial pre-registers **reading every hit** rather
than reporting the pattern count.

## Next, in order

1. He creates the API key (`GET_THE_TOKEN.md`).
2. `preflight` — free, and it is also the first real test of whether the free
   tier actually covers these three scrapers.
3. `run` — 5,000 records, $0.
4. Score on the same gate and rubric, **read every sample-size hit**, report
   cost per item that survives reading.

## Rules this folder is under

- **Keys live outside the repo**, at `C:\Users\vinig\keys\`, read at runtime.
- **`py -3`.** No venv, standard library only.
- **Google Maps is out of scope** — it is `Vinex-OS` work.
