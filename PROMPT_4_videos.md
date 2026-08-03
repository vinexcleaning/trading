# CLAUDE CODE PROMPT — Read the video backlog, free, unattended

Paste into a fresh Claude Code session in `C:\Users\gianf\trading`.
**No user input required. Blocked → record it → move on. Never wait for an answer.**

Runs in parallel with `PROMPT_1_github_bots.md` and `PROMPT_2_reddit_discord.md`.
Those write to `signal-github/` and `signal-community/`; this one writes to
`youtube-signal/`. **Stage explicit paths when committing — never `git add -A`.**
Three sessions have already cross-contaminated commits in this repo.

---

## WHAT THIS IS

The retrieval and ranking are **done**. 11,277 videos known, 683 transcripts cached
locally, 553 gated and ranked by a free keyword proxy. Six have been read in full.

**Your entire job is to read more of them and write what you find into
`youtube-signal/KNOWLEDGE.md`.** No new searching is needed and none is wanted.

**Cost: $0.** You read the transcripts yourself, in-session. There is no API key on
this machine and none is needed. Do not ask for one. Do not suggest buying one.

### Read these first, in this order
1. `youtube-signal/KNOWLEDGE.md` — what is already known. **Do not re-derive it.**
2. `.claude/skills/youtube-signal/SKILL.md` — the scoring rules and the traps.
3. `youtube-signal/HANDOFF.md` — what is untrusted.

### Already read — do not read again
`vT0qMNgOkxo`, `xl6kdezWXUo`, `yxfTHAGfaDc`, `1vfhSTtDky0`, `_BfpVLXB2Qw`,
`ZZTeNLZUvBw`. The DB knows; `load_extraction.py` will tell you if you duplicate.

---

## WHAT THE USER ACTUALLY WANTS FROM THIS BATCH

Not more explanations of how market making works — that is covered. **He wants
material he can act on.** Prioritise, in order:

1. **Building a Kalshi or Polymarket bot** — real steps, real code, real API calls
2. **Where to get historical data to backtest**, free sources first
3. **How to build a backtest that models costs**, not one that ignores them
4. **Whether a strategy is worth testing** — and if a video's edge dies after fees,
   say so; that is the finding, not a failure
5. **How much can be automated end to end**, and where a human must click

A video that says "use this website, here is the endpoint, here is what it costs"
beats a beautifully-produced explainer. Weight accordingly.

---

## THE LOOP — one video per turn, no exceptions

Context cost is **quadratic** if you hold transcripts in context. Reading 15 in one
session costs ~2.7M tokens instead of ~244k. So:

```
python youtube-signal/src/dump_transcripts.py <video_id>     # one only
  → read it
  → write youtube-signal/reports/extractions/<video_id>.json
  → python youtube-signal/src/load_extraction.py <that file>
  → move to the next video and DO NOT refer back to the previous transcript
```

Rebuild the knowledge file every 3–4 videos:
`python youtube-signal/src/build_knowledge.py`

**Target 12–15 videos.** If context gets tight, stop and write the handoff — a
sloppy extraction is worse than a missing one, because it silently pollutes a file
other sessions trust.

### Picking the next video

```
python youtube-signal/src/coverage.py          # subject gaps, top-ranked unread
```
Ranked list: `youtube-signal/reports/substance_ranking.json` (553 videos, sorted).
Prefer 5–40 minutes. **Skip the 681-minute one** — it does not fit a context window
and needs chunking nobody has built.

**Biggest gaps right now: Polymarket (141 videos held, 1 read), trading bots (92
held, 1 read), copy trading (26 held, 1 read).**

---

## SCORING — the rules that make the output trustworthy

**S — substance, 0–10.** S1 names the cost side +3 · S2 separates backtest from
live +2 · S3 states a sample size +2 · S4 explains the mechanism +2 · S5 names
specific tools/steps +1

**H — honesty, −10 to +11.** H1 shows a failure without selling a fix +3 · H1b
failure that sets up the sale +1 · H2 verifiable artifact +3 · H3 claim carries
n+period+capital +2 · H4 names own weakness +1 · H5 discloses own tools +2 ·
**H6 performance claim with no denominator −4** · H7 sells without the mechanism −2
· H8 urgency/scarcity −1

**NEVER average S and H.** A 22-minute advert whose fee arithmetic is correct
scores S=8, H=+6 and is worth absorbing. Averaging destroys both signals. The
system's most useful extraction so far came from a wall-to-wall sales funnel.

**HARD RULE: every scored component needs a timestamp and a verbatim quote under
15 words.** No quote, no score. `load_extraction.py` enforces it and will reject
you — do not fight it, fix the evidence.

**Claim types set the shelf life:** mechanism/concept/math never expire ·
procedure 12mo · tool_rec 4mo · spec (price/fee/API) 3mo · result 3mo.
Get this right; the knowledge file auto-flags expired specs from it.

**Verdicts** are computed for you: `ABSORB` (S≥4) · `RECOMMEND` (educational: S≥5,
H≥0, under 20 min, `teaching_quality` good or excellent) · `ABSORB_AND_RECOMMEND` ·
`ABSORB_RESULTS_DISCOUNTED` (H<0) · `SKIP`.

**`watch_segments` are the specific ranges needing eyes — usually a chart or code
on screen.** Zero segments is a *good* outcome; it means fully extracted. Never
mark the whole video.

Copy the shape of an existing file in `youtube-signal/reports/extractions/`.

---

## ALSO DO, IF CONTEXT ALLOWS

**Verify tools.** 16 of 23 are unchecked.
`python youtube-signal/src/verify_tools.py` checks URLs and GitHub repos (size and
last push — a README-only repo is dead, not evidence). Then reputation-check the
notable ones by web search and record verdicts in `src/tool_reputation.py`.

Four verdicts: `POSITIVE` (independent corroboration) · `MIXED` · `NEGATIVE` ·
`NO_FOOTPRINT`. **`NO_FOOTPRINT` IS NEVER `POSITIVE`** — absence of complaints
about a small tool is absence of evidence. Vendor blogs, affiliate "review" sites
and crypto Medium posts are the vendor talking, not corroboration.

**Search name variants before concluding anything.** Auto-captions garble product
names — a bot transcribed as "Creo" is actually "Kreo", and checking the wrong
spelling would have produced a false `NO_FOOTPRINT`.

**Cross-reference.** A tool praised in a recent video whose repo died two years ago
is exactly the finding this system exists to produce. Write conflicts down; never
average them away.

---

## OUTPUTS

- `youtube-signal/KNOWLEDGE.md` — gitignored, local. **The deliverable.**
- `youtube-signal/reports/extractions/*.json` — gitignored
- Code changes committed, explicit paths only

## AT THE END

Update `youtube-signal/HANDOFF.md`:
1. How many videos read, and which
2. **What is now actionable that was not before** — the point of this batch
3. The numbers, including bad ones. Which S/H components never fired, with counts —
   a rule that never triggers is a bug or a bad rule, not a neutral result
4. **Built vs actually ran on real data** — keep separate
5. What is wrong, unfinished or untrusted — **this section matters most**
6. The single next thing to do, and why

Append a short section to repo-root `STATUS.md`. Artifacts and numbers, not
narration. Do not narrate the session.
