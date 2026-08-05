# HANDOFF — extractor-upgrade

**Session 2026-08-04. Cost $0.00.** No key purchased, no quota consumed beyond
free unauthenticated limits and the GitHub token that already existed in
`signal-github/.env`. Every database touched was opened `mode=ro` in the URI, so
this project cannot have caused a lock-contention failure in a sibling.

Working directory `C:\Users\vinig\trading\extractor-upgrade`, own `.venv`.

| read this | for |
|---|---|
| **[FINDINGS_T1.md](FINDINGS_T1.md)** | the rubric graded against 24 known answers — the main result |
| **[FINDINGS_T2.md](FINDINGS_T2.md)** | vision: built, validated, and why it does not point at YouTube |
| **[FINDINGS_T3.md](FINDINGS_T3.md)** | four new open sources, one explicit refusal, one parser bug of mine |
| **[HOW_TO_CALL.md](HOW_TO_CALL.md)** | how another session calls this mid-investigation |
| **[PAID_OPTIONS.md](PAID_OPTIONS.md)** | $0.00, and the list of what was looked for |
| **[DECISIONS.md](DECISIONS.md)** | 11 conservative calls taken without asking |

---

## The one-paragraph version

The rubric was graded for the first time. **The model read is the instrument
(74% exact on 24 labelled cases); the mechanical lexicon is a ranker that
should never have been allowed to emit a verdict (42%).** Six defects were
measured, the two mechanically fixable ones were fixed and re-tested, and the
ceiling on the rest was stated rather than tuned away. Vision was built and
validated end to end, and then pointed away from YouTube, because **every route
to a frame is named in a `Disallow` line** — a finding that lands on the
existing transcript pipeline too. Four new sources are open and unused. One
command now answers the four questions offline in seconds.

---

## What is runnable

Interpreter: `extractor-upgrade\.venv\Scripts\python.exe`.

```bash
python src/ask.py --tested "polymarket 5 minute"   # THE ONE TO REMEMBER. offline, seconds.
python src/ask.py --backtester kalshi
python src/ask.py --datasources
python src/ask.py --tool py-clob-client

python src/validate_rubric.py --v2      # the 24-case grading, A vs B vs C
python src/population_check.py          # did v2 fix a rubric or memorise 24 cases
python src/verify_tech.py               # rebuild the currency table from GitHub + PyPI
python src/unify_currency.py            # join liveness onto social-signal's entity table
python src/vision_value.py              # would vision have changed anything
python src/find_sources.py              # probe every candidate source, robots first
python src/frames.py --selftest         # prove the frame loop, no network at all
python src/frames.py --video FILE --id VIDEO_ID   # the real thing, on a local file
```

Reports land in `reports/` (gitignored — they carry per-document judgments about
named creators and pseudonymous accounts). Caches land in `data/` (gitignored).

---

## The numbers, in one place

| | |
|---|---|
| labelled test cases | **24**, across 4 corpora, 17 banded |
| pipeline as recorded | **17/23 = 74%** exact · false RECOMMEND 2 · **stale 0/2** |
| mechanical lexicon | **10/24 = 42%** · false RECOMMEND 6 · stale 0/2 |
| rubric v2 | **13/24 = 54%** · false RECOMMEND 5 · **stale 2/2** |
| population check | **594 of 5,567 = 10.7%** change action — a fix, not a rewrite |
| components never firing | **H9, H10** (LLM, n=38) · **H1b** (lexicon, n=4,432) |
| components firing on ~everything | **S5 95% · S4 92% · H4 87%** (LLM) |
| components the prompt never declares | **6 of 21** — B1–B5 and H10 |
| videos read / flagged visual_dependent | 38 / **22 (58%)** |
| runtime inside a `watch_segment` | **29 min of 9.8 h = 4.9%** |
| test-set labels needing a frame | **0 of 24** |
| descriptions carrying ≥3 chapter markers | **396 of 1,197 = 33.1%** |
| entities given a live currency verdict | **176**, 148 ALIVE, **2 provably gone** |
| new sources open and unused | **4** |

---

## ⚠ Things a sibling session needs to know

### 1. `youtube-signal`'s transcript fetcher is on a `Disallow` endpoint

`youtube-transcript-api` calls `https://www.youtube.com/youtubei/v1/player`
(`_settings.py:2`). `youtube.com/robots.txt` has `Disallow: /youtubei/` under
`User-agent: *`, and also `Disallow: /api/` and `Disallow: /timedtext_video`.

**Nothing was stopped, changed or deleted.** This is stated because
`social-signal` killed Reddit's own JSON API, X, TikTok and Instagram on exactly
this standard and wrote *"a User-Agent string is not consent"*. The project has
been on one side of a line it drew itself on the other side of. It is the user's
call, and the options are not equivalent — transcripts are the basis of 38
reads, 484 claims and a 190,000-character knowledge file.

### 2. Both SKILL.md files quote numbers their own projects have retracted

| where | says | project now says |
|---|---|---|
| `github-signal/SKILL.md` | `trust_me_bro` uncorrelated with substance, rho +0.03 p 0.41 | **overturned at n=2,717: rho +0.064, p 0.0009, weakly POSITIVE** |
| `github-signal/SKILL.md` | stars rho at n=2,260 | full coverage is n=3,165 |
| `youtube-signal/SKILL.md` | project root `C:\Users\gianf\…` | that is the **laptop** |

The `K015 = W011` shape again. **Not edited** — they are sibling files.

### 3. Two numbers where this session refines rather than contradicts a sibling

- **`bot-hunt` is right about Pinnacle.** `guest.api.arcadia.pinnacle.com/0.1/sports`
  returns 401 with no header *and 403 with the public guest key*, but
  `/0.1/sports/29/matchups` returns **200 and 1.7 MB with no header at all**.
  The index is gated; the endpoint that matters is not. A future session
  probing `/sports` first would wrongly conclude the API is dead.
- **`oracleselixir.com` returns HTTP 200** (3,919 bytes, a shell) against
  `bot-hunt`'s recorded 404. Different URLs, so not a contradiction — but
  whoever needs esports data should check the data path rather than either line.

### 4. `Polymarket/agents` — 3,761 stars, archived, 637 days cold

Already in `social-signal`'s table as a CONTRADICTION. Now confirmed by the
owner's own API flag on a dated, re-runnable check, and still a PASS in
`signal-github`'s corpus with 693 archived repos referencing it.

---

## What I got wrong, in this session, and fixed

Recorded because the ratio matters more than the count.

1. **`unify_currency.py` v1 counted every 404 as death** and killed three live
   API hosts whose base URL has no handler.
2. **v2 patched that with a path-segment heuristic** and immediately killed
   `api.elections.kalshi.com/trade-api/v2`, a versioned API base this repo is
   recording against right now. A heuristic written to fix a false kill produced
   another one on its first run. The rule now has no heuristic in it: **a 404
   never establishes death.**
3. **`find_sources.py`'s robots parser ignored `Allow:`** and reported Hacker
   News's official, explicitly-permitted JSON API as forbidden. Fixed to
   longest-match-wins with wildcards. **A robots check that does not implement
   `Allow` is not a robots check.**
4. **`rubric_v2`'s currency table matched the alias `agents`** — from
   `Polymarket/agents` — and flagged five sources stale for containing an
   ordinary English word.
5. **`frames.py`'s selftest rendered a blank frame with exit code 0**, because
   `%` kills ffmpeg's `drawtext` silently. Caught by looking at the image.
6. **I created a venv at the repo root** before creating one in this folder.
   `C:\Users\vinig\trading\.venv` now contains `pillow` and `yt-dlp`. It was
   bare beforehand and nothing in the repo references it, but it is not mine and
   the change is recorded rather than hidden.

Every one of 1–4 is the same shape the repo has now recorded five times: **a
probe that samples the wrong thing fails silently, and always toward the
conservative answer.** Two of mine failed toward "dead" and one toward
"forbidden".

---

## Three candidates for GUARDS.md

1. **A robots check that does not implement `Allow:` is not a robots check.**
   Longest match wins, with `*` and `$`. A naive parser calls a documented
   public API forbidden.
2. **A 404 never establishes that something is dead.** An API base with no
   handler returns 404 while perfectly healthy. Only no-DNS, an owner-set
   archive flag, and HTTP 410 do.
3. **A zero exit code is not a rendered artifact.** ffmpeg returned 0 and wrote
   a blank frame. `frames.is_flat()` is the canary. Sibling of `bot-hunt`'s
   *"a 200 is not a correct file — hash it and check its own content column."*

---

## Single next action

**Read the chapter markers out of the 396 descriptions already on disk.** Free,
offline, no permission needed, 33.1% coverage, and it improves `watch_segments`
— the number that decides whether extraction beat watching. Everything else on
the list either needs a decision from the user (the transcript-endpoint
question, a creator's permission for frames) or is a new corpus.
