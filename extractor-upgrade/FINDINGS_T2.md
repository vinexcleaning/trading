# TASK 2 — vision: built, validated, and pointed away from YouTube

**Two findings, and the first one decides the second.**

---

## 1. Every route to a YouTube frame is named in a `Disallow` line

Fetched 2026-08-04.

`https://www.youtube.com/robots.txt`, under `User-agent: *`:

```
Disallow: /get_video
Disallow: /get_video_info
Disallow: /file_download
Disallow: /youtubei/
Disallow: /api/
```

`https://i.ytimg.com/robots.txt`, under `User-agent: *`:

```
Disallow: /sb/
```

- `/get_video`, `/get_video_info`, `/file_download` — the video-stream routes.
- `/youtubei/` — the InnerTube API. **This is what `yt-dlp` calls**:
  `yt_dlp/extractor/youtube/_base.py:806` builds
  `https://{host}/youtubei/v1/{ep}`.
- `/sb/` on the image CDN — the **storyboard** path, which was the cheap route:
  storyboards are pre-made thumbnail grids covering a whole video, obtainable
  with no video download and no ffmpeg. They are disallowed too.

There is no fourth route. Frame acquisition from YouTube is closed.

### Why that is decisive here rather than a technicality

`social-signal` already took this exact position, in writing, and killed the
top-priority platform on it:

> With a browser User-Agent, `reddit.com/r/algotrading/.rss` returns **200 and
> 54 KB** and `x.com/kalshi` returns **200 and 200 KB**. **The constraint is not
> technical.** The content is one GET away and is not taken, because a site's
> machine-readable statement of who may crawl it says nobody may, and **a
> User-Agent string is not consent.**

X, TikTok, Instagram and Reddit's own JSON API were all dropped on that
standard. Applying it to Reddit and not to YouTube would make it a preference,
not a standard. It is applied.

### ⚠ It lands on a sibling project, not just on this task

`youtube-transcript-api` — the library `youtube-signal` uses for all 1,135
cached transcripts — fetches from **`https://www.youtube.com/youtubei/v1/player`**
(`youtube_transcript_api/_settings.py:2`). **That is the same `Disallow: /youtubei/`
line.** `/api/` is also disallowed and `/timedtext_video` is disallowed by name.

**This is a finding about `youtube-signal`'s existing pipeline, surfaced by a
task that was only supposed to add frames.** It is stated, not acted on: I have
not stopped anything, changed anything in that project, or deleted any cached
transcript. It is the user's call, and the two options are not equivalent —
transcripts are the entire basis of 38 reads, 484 claims and a 190,000-character
knowledge file.

> The honest framing: **the project has been operating on one side of a line it
> drew itself on the other side of.** Whichever way that resolves, it should
> resolve deliberately rather than by nobody having checked.

---

## 2. So the pipeline was built and validated, and points at local files

`src/frames.py` is complete and tested end to end. It does not fetch from
YouTube.

| stage | what it does |
|---|---|
| `cues()` | picks the seconds worth a frame from three independent signals: recorded **claim timestamps**, the reader's own **`watch_segments`**, and a narrow set of **demo phrases** ("as you can see", "let me show you", "here's my account"). Deduplicated onto a 4-second grid, claims winning ties, capped at 40. |
| `extract()` | one `ffmpeg` seek-before-decode per timestamp, so a 20-minute file costs milliseconds a frame rather than a full decode |
| `contact()` | lays the frames out as a single labelled sheet — the comparison a reader needs is *between* frames, and one sheet costs a fraction of forty separate reads |
| `ScreenEvidence` | screen-derived findings stored **separately** from transcript-derived ones, with `spoken` and `shown` as distinct fields and an `agreement` field (`CONFIRMS / CONTRADICTS / ADDS / ABSENT`) that may only be filled by someone who looked at the frame |

`ffmpeg` arrives via `pip install imageio-ffmpeg` — a bundled static binary, no
system install, no PATH change.

### The self-test proves the loop closes, with no network at all

`python src/frames.py --selftest` builds a synthetic video with known text at
known seconds, cuts the frames, and produces a sheet. **It now renders 5 of 5**,
including the case the whole exercise exists for: the tile at `t=0s` says
`SPOKEN: I made 40 percent this month` and the tile at `t=5s` says
`SCREEN: Total P/L -18.4%`.

The first run rendered **4 of 5**, and the blank one is the useful part.

> The missing scene was the one containing a `%`. Bisected against ffmpeg
> directly: `"Total 18%"` → a **1,002-byte blank**, `"Total 18 pct"` → a
> 3,007-byte image with text — **and both with exit code 0 and an empty
> stderr.** Escaping as `\%` does not help. Moving the caption into
> `textfile=` does not help either. The cure is `expansion=none`, which turns
> off drawtext's text-expansion layer entirely: same string, 4,471 bytes.
> (A third trap on the way: a Windows drive letter's colon is a separator
> inside a filter string, so the textfile path must be relative with `cwd` set.)
>
> **All three failures were silent, and the one that mattered was caught by
> looking at the image.** That is, in miniature, the argument for vision: a
> well-formed, zero-exit, empty result that no return-code check can see. It is
> the same shape as `bot-hunt`'s thirteenth guard — *a 200 is not a correct
> file* — and it now has a canary: `frames.is_flat()` measures the frame's own
> pixel standard deviation and flags anything featureless, so the pipeline can
> never again report a successful extraction of nothing.

---

## 3. Would vision have changed anything? — the measurement, run anyway

Full table: `reports/T2_vision_value.md`.

| | |
|---|---|
| videos read | 38 |
| flagged `visual_dependent` by their reader | **22 (58%)** |
| total runtime | 9.8 h |
| runtime inside a `watch_segment` | **29 min = 4.9%** |
| videos needing **zero** segments | 13 of 38 |
| claims whose own text says the evidence was on screen | **8 of 484 = 1.7%** |
| **test-set labels that required a frame** | **0 of 24** |

**0 of 24.** Every label in the Task 1 test set was fixed by arithmetic on
stated numbers, a live API call, an external primary source, or two statements
in the same transcript disagreeing with each other.

> **The bias in that number runs AGAINST vision and must be stated.** The test
> set was built from cases whose answer is independently verifiable — and a
> claim that can *only* be settled by looking at a screen is exactly a claim
> whose answer cannot be independently verified, so it could never have been
> included. 0 of 24 is a real number about a set that structurally excludes the
> cases vision exists for.

So the defensible statement is narrower than "vision does not help":

- **Stale technology** — vision is unnecessary. An API call beats a screenshot,
  is free, and is legal.
- **Denominator-free claims** — vision is unnecessary. The defect is an
  *absence*, and an absence is not on the screen either.
- **A spoken number the screen contradicts** — vision is the only instrument
  there is, and **8 recorded claims currently rest on frames nobody checked.**

One of those eight is already a screen-versus-reality contradiction that a
reader caught by eye and no transcript could have produced:

> *"polymarket.com's own wallet statistics are unreliable — the creator's own
> wallet displayed a **100% win rate** against a real 50–60%."*

That is the shape the brief predicted, found once, in the corpus, without a
frame pipeline. **It is one instance, not a rate**, and one instance is not
grounds for building a fleet.

---

## 4. What would unblock this

In descending order of how quickly it could happen:

1. **A local file.** `python src/frames.py --video FILE --id VIDEO_ID` runs
   today, against any video the user already has on disk.
2. **A licensed or permissively-licensed archive.** Anything shipping video
   under CC-BY with a direct download, or an archive whose `robots.txt` permits
   it. `arctic-shift.photon-reddit.com` is the precedent — `social-signal`
   found the permitted mirror of a forbidden source and used that.
3. **Written permission from a creator.** The corpus's most valuable sources
   are small channels (8 views, 43 views, 141 views) whose authors are
   reachable. That is a human action, not a technical one.
4. **A paid API that licenses the content.** None found; nothing logged in
   `PAID_OPTIONS.md` because nothing was found to log.

**Not recommended:** routing through a third-party mirror or downloader site.
`social-signal` already rejected that reasoning for X — *"mirrors are the same
act with an extra hop"* — and it is the same act here.
