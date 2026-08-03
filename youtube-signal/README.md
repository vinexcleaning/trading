# youtube-signal

Reads YouTube transcripts and extracts the substance — tools, sites, methods,
specific claims — so you don't have to watch the videos.

**Status: Phase 1 (retrieval) complete.** 470 videos gated, 263 passing, 439
transcripts cached, 43 channels expanded. No scoring or extraction yet.
See `HANDOFF.md` for what passed, what failed, and what to do next.

**Runs on 0 YouTube Data API units.** yt-dlp searches and enumerates channels with
no key. Keyless search can filter to the past 12 months but cannot sort by date.

## Run

Phase 1, in order (`run_retrieval` ~3 min, `run_gates` ~20 min):

```bash
C:\Users\gianf\trading\youtube-signal\.venv\Scripts\python.exe C:\Users\gianf\trading\youtube-signal\src\run_retrieval.py
```

```bash
C:\Users\gianf\trading\youtube-signal\.venv\Scripts\python.exe C:\Users\gianf\trading\youtube-signal\src\run_gates.py
```

```bash
C:\Users\gianf\trading\youtube-signal\.venv\Scripts\python.exe C:\Users\gianf\trading\youtube-signal\src\measure.py
```

Re-apply changed gate logic from cached transcripts (seconds, no network):

```bash
C:\Users\gianf\trading\youtube-signal\.venv\Scripts\python.exe C:\Users\gianf\trading\youtube-signal\src\reclassify.py
```

Phase 0 (premise verification, no API key needed, ~4 minutes):

```bash
C:\Users\gianf\trading\youtube-signal\.venv\Scripts\python.exe C:\Users\gianf\trading\youtube-signal\src\phase0.py
```

Quota-ledger self-test:

```bash
C:\Users\gianf\trading\youtube-signal\.venv\Scripts\python.exe C:\Users\gianf\trading\youtube-signal\src\test_quota.py
```

## Layout

| path | what |
|---|---|
| `channels.json` | The four seed channels, **pinned by ID**. Never resolve a channel by name. |
| `src/db.py` | SQLite schema: videos, channels, retrieval_hits, retrieval_log, drops, transcripts |
| `src/queries.py` | Query families F1 (beginner) / F2 (insider) / F3 (date-windowed) |
| `src/retrieval.py` | Paced, logged, throttle-instrumented yt-dlp access. All network goes through here. |
| `src/gates.py` | G1 transcript / G2 18-month age / G3 on-topic |
| `src/run_retrieval.py` | Steps 3–5: families × 3 runs, union, Jaccard |
| `src/run_gates.py` | Step 6: gates + channel expansion |
| `src/reclassify.py` | Re-apply gates from cached transcripts. No network. |
| `src/measure.py`, `src/measure_addendum.py` | Step 7 measurement and its two corrections |
| `src/validate_g3*.py` | Measures G3's error rate against hand judgments |
| `src/quota.py` | YouTube Data API quota ledger, hard-halts at 9,500 of 10,000 units. **Never yet used.** |
| `src/transcripts.py` | Transcript fetch, two independent paths (youtube-transcript-api, yt-dlp) |
| `src/channels.py` | Channel stats and the >5× drift guard. **Contains no name resolver, by design.** |
| `src/phase0.py` | Phase 0 premise verification |
| `reports/` | Committed. Run reports and findings JSON. |
| `data/` | Gitignored. SQLite DB, cached transcripts. |

## Constraints

- **Must run from a residential IP.** YouTube blocks datacenter ranges for
  transcript fetching. Never deploy to a cloud VM.
- The YouTube Data API allows 10,000 units/day, resetting midnight US/Pacific.
  `search.list` costs 100 units; everything else costs 1. `src/quota.py` logs
  every call and refuses to cross 9,500.
