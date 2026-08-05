# HOW TO CALL THE EXTRACTORS MID-INVESTIGATION

**The whole point: a five-minute lookup that prevents a week of duplicated
work.** So the first thing on this page is the five-minute lookup, and the full
skill sessions come after it.

---

## THE FAST PATH — `ask.py`

One command. **Read-only, offline, no network, no API key, finishes in
seconds.** It queries the corpora that are already on disk:

| corpus | what is in it |
|---|---|
| youtube-signal ×2 | 38 read videos · **484 claims** · 112 tools · 36 methods |
| signal-github | 4,017 repos · **3,165 scored**, 2,882 live · classified by venue and kind |
| social-signal | 39,629 Reddit posts · 12,846 comments · 4,432 scored |
| the join | **240 entities** with cross-platform reputation verdicts |

```bash
C:\Users\vinig\trading\extractor-upgrade\.venv\Scripts\python.exe C:\Users\vinig\trading\extractor-upgrade\src\ask.py --tested "5 minute bitcoin"
```

### The four questions it is built for

**1. "Has anyone already tested this, and what happened?"**

```bash
.venv\Scripts\python.exe src\ask.py --tested "polymarket 5 minute btc"
```

Returns every matching **claim** with its type, its **denominator or the absence
of one**, its n-check verdict, and the S/H score and verdict of the source it
came from; every non-SKIP Reddit thread with a permalink; every scored repo.

> It prints `NO DENOMINATOR` in the same column as `n=12272`, because that is
> the single distinction the answer turns on. **A result claim with no
> denominator is not a test, it is an advertisement.** If nothing that comes
> back states an n, the honest answer to "has anyone tested this" is *no*.

**2. "Does a working backtester exist for this venue?"**

```bash
.venv\Scripts\python.exe src\ask.py --backtester kalshi
.venv\Scripts\python.exe src\ask.py --backtester polymarket
```

Venue is decided by **what the code imports**, never by the README — 32% of
repos that pass the topic gate import neither venue. Repos importing the
archived Polymarket v1 client are marked inline. It then prints the five checks
to run before trusting any of them (fee in-engine or bolted on; does the
backtest import the same fair-value function as the live engine; is there
latency; `filtfilt` versus `lfilter`; per-series maker fees).

**3. "What free data sources do people who publish real results actually use?"**

```bash
.venv\Scripts\python.exe src\ask.py --datasources
```

Every entry is **fetch-verified with the date of the check**, including the
three that look alive and are not, and the one that returns HTTP 200 and the
wrong file.

**4. "What do people say about this tool outside its own marketing?"**

```bash
.venv\Scripts\python.exe src\ask.py --tool OpenClaw
.venv\Scripts\python.exe src\ask.py --tool py-clob-client
```

Returns the cross-platform verdict, the platform count, and the **verbatim
evidence window** behind each stance — `ADVOCACY` kept separate from
`CORROBORATION`, so a stale repo somebody mentioned in passing reads as a stale
repo rather than as a contradiction.

Free-text across everything at once: `ask.py "kalshi market maker"`.

### What `ask.py` will not do

It does not fetch. **Absence in it is weak evidence** — 38 of roughly 1,200
gated videos are read, so "nothing found" means "nobody here has looked", not
"nobody has done it". That is exactly the trigger for a full session below.

---

## THE FULL SESSIONS — when the fast path comes back empty

Two skills exist and are invoked by name.

### `/github-signal`

**Ask a narrow question.** `--venue kalshi --kind market_maker --alive` returns
10 lines; "tell me about the corpus" returns 2,000.

```bash
python src/classify.py --venue kalshi --kind market_maker --alive --limit 10
python src/classify.py --venue polymarket --kind backtester
python src/classify.py --need "tennis|weather"     # regex over name + description
python src/shortlist.py                            # substance AND credibility
```

Everything except the final read is free and costs no model context. Whole
repos come from `codeload.github.com/<repo>/tar.gz/<branch>` — **the legacy URL
form; the documented `/refs/heads/` form times out from this network** — which
carries no rate-limit headers at all.

### `/youtube-signal`

```bash
$env:SIGNAL_DB = "kalshi_edge"          # selects the targeted corpus
.venv\Scripts\python.exe src\target_rank.py
.venv\Scripts\python.exe src\dump_transcripts.py <video_id>
# read it yourself, write reports\extractions\<id>.json, then:
.venv\Scripts\python.exe src\load_extraction.py reports\extractions\<id>.json
.venv\Scripts\python.exe src\build_knowledge.py
```

For a **new topic**, the engine is the query split: F1 beginner phrasing versus
F2 insider vocabulary. Measured, the two return near-disjoint sets (Jaccard
0.037) and F2's yield of sub-5,000-view videos beats F1's by 2.25×.

---

## THE COST MODEL — this is what actually bites

**The expensive resource is the context window, not API calls.** A source read
into context stays there for the rest of the session, so reading N documents in
one context costs roughly N²/2, not N. Reading 15 videos in one session
processed ~2.7M tokens against 244k of actual text.

| rule | why |
|---|---|
| **Never read something to find out whether it is worth reading.** | That is what the scores and `classify.py` are for. They read every file on disk and put not one byte in your context. |
| **One document per turn when reading.** | Dump it, extract it, write the JSON to disk, do not carry the source forward. |
| **Query the cache, never recompute.** | All HTTP is cached by URL. `classify.py` without `--reclassify` is instant; with it, ~10 minutes. |
| **`ask.py` before any skill.** | It costs one tool call and no network. |

---

## ⚠ THE SKILL FILES CARRY NUMBERS THEIR OWN PROJECTS HAVE SINCE RETRACTED

Checked against `STATUS.md` and `signal-github/HANDOFF.md` on 2026-08-04. **Do
not quote a number out of a SKILL.md without checking it against the project's
own handoff first.**

| where | what the skill says | what the project now says |
|---|---|---|
| `github-signal/SKILL.md` | `trust_me_bro` is **uncorrelated** with substance, rho +0.03, p 0.41 | **OVERTURNED at n=2,717: rho +0.064, p 0.0009 — weakly POSITIVE.** Flagged repos score *higher* on substance. It is an honesty signal, not a quality signal: discount the claims, not the tooling. |
| `github-signal/SKILL.md` | `rho(stars, S_strict) = −0.007, p = 0.73` at n=2,260 | −0.008, p 0.65 at **n=3,165** (full coverage). Same conclusion, different sample. |
| `youtube-signal/SKILL.md` | project root `C:\Users\gianf\trading\youtube-signal` | That is the **laptop**. The desktop `C:\Users\vinig\trading\youtube-signal` is primary. |

This is the `K015 = W011` shape again — a claim travelling between documents and
picking up a different status in each — and it is why `CLAUDE.md` §6 points at
the tally rather than freezing a number.

---

## ⚠ AND ONE THING THE RUBRIC DOES NOT TELL YOU

Every verdict in these corpora — `ABSORB`, `RECOMMEND`, `BUILD` — was produced
by an instrument that has now been graded against 24 known answers
(`FINDINGS_T1.md`). Two limits matter when you read one:

1. **Nothing in the stored verdicts asks whether the thing still works.** A
   Polymarket CLOB v1 tutorial is recorded as `BUILD_AND_RECOMMEND`. Both v1
   clients are archived. **`pip install py-clob-client` still succeeds**, so
   nothing warns you. Run the currency check:

   ```bash
   .venv\Scripts\python.exe src\verify_tech.py
   ```

2. **A stored verdict is not reproducible.** `read_video.verdict()` consumes a
   `teaching_quality` judgment that was never persisted. Treat the recorded
   verdict as a recorded fact, not as something you can re-derive.

---

## Worked example — the shape this is meant to replace

> A trading session is about to build a Polymarket 5-minute momentum backtester.

```bash
.venv\Scripts\python.exe src\ask.py --tested "polymarket 5 minute"
```

Comes back with, among others: a **96.83% win rate over "12,272 periods"** whose
qualifying subset's own n is **never stated**; a video explaining that each
5-minute market takes the underlying price at the interval open, so **you do not
need Polymarket data at all** — 1-minute candles of the underlying reconstruct
it; and a Reddit study of 4,604 windows finding **every price band loses against
price+fee** and momentum continuation **inverting** across 346,094 windows.

```bash
.venv\Scripts\python.exe src\ask.py --backtester polymarket
```

Comes back with the repos, the v1-client flags, and the `filtfilt` warning.

**Two commands, under a minute, no network.** The alternative is a week.
