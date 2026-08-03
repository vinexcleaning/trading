# youtube-signal

Reads YouTube transcripts and extracts the substance — tools, sites, methods,
specific claims — so you don't have to watch the videos.

**Status: Phase 0 only.** Premises verified, nothing downstream built.
See `HANDOFF.md` for what passed, what failed, and what to do next.

## Run

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
| `src/quota.py` | YouTube Data API quota ledger, hard-halts at 9,500 of 10,000 units |
| `src/transcripts.py` | Transcript fetch, two independent paths (youtube-transcript-api, yt-dlp) |
| `src/channels.py` | Keyless search and channel-stat pulls via yt-dlp |
| `src/phase0.py` | Phase 0 premise verification — the entry point |
| `src/test_quota.py` | Proves the quota halt fires |
| `src/probe_nate*.py` | Evidence for the "Nate Tokens" name correction |
| `reports/` | Committed. Run reports and findings JSON. |
| `data/` | Gitignored. SQLite DB and recorded transcripts. |

## Constraints

- **Must run from a residential IP.** YouTube blocks datacenter ranges for
  transcript fetching. Never deploy to a cloud VM.
- The YouTube Data API allows 10,000 units/day, resetting midnight US/Pacific.
  `search.list` costs 100 units; everything else costs 1. `src/quota.py` logs
  every call and refuses to cross 9,500.
