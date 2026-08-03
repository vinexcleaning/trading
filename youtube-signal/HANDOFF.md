# HANDOFF — youtube-signal

Phase 0 only. 2026-08-02. Laptop `gianf`, residential IP.
Detail and evidence: `reports/phase0_2026-08-02.md`.

---

## 1. Premises tested

| # | Premise | Verdict | Evidence |
|---|---|---|---|
| 1 | Transcripts fetchable from this machine | **PASS** | 6/6 videos, both libraries, no bot-detection error |
| 2 | `YOUTUBE_API_KEY` exists | **FAIL** | Absent from env, user env, and every candidate `.env` |
| 3 | The four creator names are correct | **FAIL** | 3 of 4 misspelled; all 4 resolve once corrected |
| 4 | Scoring weights are right | **NOT TESTED** | Needs Phase 2 |
| 5 | 18-month cutoff is right | **PARTIAL** | 40/40 of Nates Tokens' newest uploads fall inside it |

**Transcripts (the gating premise) work.** `youtube-transcript-api` 6/6 and `yt-dlp`
6/6, identical snippet and word counts, zero `IpBlocked` / `RequestBlocked` /
`PoTokenRequired`. Both paths are kept; the fast one is default. Captions are
auto-generated — timestamps are reliable, punctuation and speaker labels are not.

**The API key is missing but blocks less than assumed.** `yt-dlp` searches YouTube
and enumerates channel uploads keylessly and quota-free — every channel number
below came from it. The unresolved question is whether keyless search can reproduce
`order=date` / `publishedAfter`, which query family **F3 Recent** needs.

**Corrected channel IDs — pin these, do not re-resolve by name:**

| prompt name | actual | channel ID | subs | median views |
|---|---|---|---|---|
| Nate Tokens | **Nates Tokens** | `UCEFnH0KShNRHb-NMeurBxQQ` | 30,200 | 1,400 |
| MindMathMoney | **Mind Math Money** | `UCTdlDD6JgJeplt4axozFmSQ` | 473,000 | 8,200 |
| Trading with DavidTech | **Trading with DaviddTech** | `UC7NJLsf6IonOy8QI8gt5BeA` | 1,440,000 | 27,000 |
| Patrick Dang | Patrick Dang | `UCLOzkJ9W9fntCGyYfUwMPew` | 405,000 | 10,000 |

Searching the bare string `"Nate Tokens"` returns **the wrong person** — `Nate B
Jones`, 309k subs, median 59k views — confidently, at rank 0. It was caught only
because the prompt's own `~30k subs / ~2k views` description contradicted it. All
five `@natetokens` handle variants 404.

## 2. Built vs. actually run on real data

| file | built | ran on real data |
|---|---|---|
| `src/transcripts.py` | yes | **yes** — 6 videos, both paths, incl. failure classification |
| `src/channels.py` | yes | **yes** — 4 channels resolved, ~840 uploads enumerated |
| `src/phase0.py` | yes | **yes** — twice, end to end |
| `src/quota.py` | yes | **yes, but only against a scratch DB.** Halt fires at 9,401+100 > 9,500, spend unchanged after refusal, unknown endpoint rejected. **It has never charged a real API call.** |
| `src/probe_nate*.py` | yes | yes — produced the name correction |

Nothing for Phases 1–5 exists. No retrieval, no gates, no scoring, no extraction,
no verification, no `signal.db` schema beyond `quota_ledger`.

## 3. Recall test

**Not run.** It is Phase 5 and depends on Phase 1 retrieval, which is not built.
No recall number should be quoted from this session.

What Phase 0 does establish: the target is real, correctly identified, and on
topic. Nates Tokens' recent uploads include *Polymarket Copytrade Bot Speed Test*
(703 views), *Polymarket Weather Trading Bot Built With Claude* (5,913), *FREE
Polymarket Backtesting Tool* (2,266) — the low-view/high-specificity profile the
system is meant to find.

## 4. Scoring components that never fired

**All of them.** S1–S5, H1–H10, C, and the n-check have never executed — the
scoring module is not written. The count for every component is 0, from absence,
not from failing to trigger. Premise 4 stays untested.

## 5. What is wrong, unfinished, or untrusted

1. **No API key.** Phase 1 as specified cannot run. Setup steps in §6.
2. **The quota ledger has never guarded a real call.** Its halt logic is proven in
   isolation; the integration — that every real call routes through `charge()`
   before being made — is unproven, because there are no real calls yet. This is
   the component the prompt says must be impossible to break by accident, and it
   is exactly the one still untested in situ.
3. **`resolve_by_search` produces confident wrong answers.** It picked the wrong
   human for "Nate Tokens" at rank 0 with 6/12 agreement. Do not use it for the
   Phase 5 recall seeds — use the pinned IDs. It is fine for discovery, where a
   wrong channel is just a bad candidate, and dangerous for identity.
4. **Upload counts are floors, not counts.** Capped at 200/channel. Median views
   are over that newest-200 sample and are biased toward recent performance.
5. **`Mind Math Money` is unverified beyond name and stats.** 473k subs against
   median 8,200 views is a low ratio; it resolved at 12/12 with a near-exact name,
   so it is probably right, but nobody checked it against a description the way
   Nate was checked. The prompt's "70-minute video" claim was not confirmed.
6. **Search results are not reproducible.** Two identical `ytsearch3` calls minutes
   apart returned different videos. Any Phase 1 retrieval metric will be noisy
   run-to-run, and the recall test needs to survive that.
7. **Premise 5 rests on one channel.** 40 videos from a single prolific creator is
   not an age distribution.
8. **The repo layout in the prompt does not match reality.** There is no
   multi-project parent repo. The only git repo is
   `C:\Users\gianf\kalshi\set1_overshoot` (a tennis study), so `youtube-signal`
   was created inside it, as a sibling of `src/`. `STATUS.md` at that repo root
   was appended to. If the intent was a true sibling at `C:\Users\gianf\kalshi\`,
   that folder is not under version control and the layout needs a decision.
9. **`is_generated` disagrees between the two transcript paths** on one video.
   Cosmetic now; it would matter if H-scoring ever weighted manual captions.

## 6. The single next thing to do

**Decide whether this needs the YouTube Data API at all — then get the key or drop it.**

It is first because everything in Phase 1 branches on it, and because the answer
may be "no", which would delete the entire quota problem the prompt is most worried
about. The concrete test is one afternoon of work: can `yt-dlp` reproduce
`order=date` and a 12-month window (family **F3**)? If yes, the pipeline runs at
zero quota and `src/quota.py` becomes dead code. If no, F3 needs the key and the
other three families still do not.

To get a key: Google Cloud Console → new project → **APIs & Services → Library** →
enable **YouTube Data API v3** → **Credentials → Create credentials → API key** →
copy it into `youtube-signal/.env` as:

```
YOUTUBE_API_KEY=<paste here>
```

`.env` is gitignored. Re-run `src/phase0.py`; it will validate the key with a
1-unit `videos.list` call and log it to the ledger.
