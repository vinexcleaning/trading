# PAID_OPTIONS — extractor-upgrade

**Nothing in this project cost money. This file exists because the standing
rule says anything that would has to be logged, and because "nothing was found"
is only credible if the list of things looked for is written down.**

Total spent this session: **$0.00.** No API key was purchased, no service was
signed up for, no quota was consumed beyond free unauthenticated limits and the
GitHub token that already existed in `signal-github/.env`.

---

## Things that would cost money, and were therefore not used

| what | what it would buy | cost | verdict |
|---|---|---|---|
| **A licensed YouTube video source** | the only legal route to frames (Task 2) | none found | **Nothing to log.** Searched for a licensed or permissively-licensed archive of the kind of content this corpus holds. There is no product that sells you frames from an arbitrary creator's video. The blocker is permission, not price. |
| **Anthropic API credit for `read_video.py`** | batch reading instead of in-session reading | ~$0.02–0.05/video | **Not needed and the old handoff was wrong to call it a blocker.** The read is done in-session by the model at no marginal cost. `read_video.py` has still never executed. |
| **`the-odds-api`** | keyed odds feed; 129 repos in the GitHub corpus use it | from $0/mo (500 reqs) to $59+/mo | **Not needed.** `guest.api.arcadia.pinnacle.com/0.1/sports/<id>/matchups` returns 1.7 MB with no header at all, and Pinnacle is the sharp book the paid aggregators are aggregating. |
| **PodcastIndex paid tier** | higher rate limits | from $0 | **Not needed.** The keyless `search/byterm` endpoint returned 12,440 bytes and `robots.txt` permits it. |
| **Apify** | Instagram / TikTok / Flashscore actors | already at a monthly hard limit | **Not reopened here.** `social-signal` killed those platforms on terms and on measured substance, not on quota, so buying quota does not reopen them. |
| **SSRN / paywalled papers** | e.g. SSRN 6325658, the "Kalshi LPs are underwriting" argument | varies | **Left unverified, deliberately.** `papers.ssrn.com` returns 403 behind a Cloudflare interstitial and this project does not solve bot challenges. Recorded as unverified in `social-signal`, unchanged here. |
| **A commercial credibility / misinformation-scoring API** | an off-the-shelf replacement for the rubric | varies | **Recommended against on evidence, not on cost.** Task 1 measured six defects and **none of them is a ranking problem** — staleness is one API call, polarity is a parser bug, a missing denominator is an absence, and two components were unreachable code. Buying a model would swap a known-bad instrument for an unknown one. |

---

## Free things that are *rate*-limited, and how that was handled

| what | limit | what was done |
|---|---|---|
| GitHub API, unauthenticated | 60/hr | the existing `signal-github/.env` token raises it to 5,000/hr. No new token, no cost. |
| GitHub repo *contents* | — | not hit at all. `codeload.github.com/<repo>/tar.gz/<branch>` carries no rate-limit headers and was already the sibling's route. |
| PyPI JSON | none published | 5 packages checked, paced. |
| Every live probe in `find_sources.py` | varies | paced at 0.3 s, `robots.txt` fetched once per host and cached. |
| `unify_currency.py` | 176 entities | paced at 0.35 s and **cached to `data/entity_currency.json`**, so a re-run costs zero requests. |

---

## The one thing genuinely blocked by money — and it is not money

**Vision.** `src/frames.py` is complete, tested end to end, and needs a video
file. Every route to a YouTube frame is named in a `Disallow` line
(`FINDINGS_T2.md`). **No amount of money fixes that**, because nothing is being
sold. The unblocking actions are, in order: a local file the user already has;
a permissively-licensed archive; **written permission from a creator** — and
the most valuable sources in this corpus are 8-view, 24-view and 43-view
channels whose authors are reachable by email.

That is a human action, not a purchase.
