# CLAUDE CODE PROMPT — Community Signal: Reddit and Discord

Paste into a fresh Claude Code session in `C:\Users\gianf\trading`.
**No user input required. Blocked → record it → move on. Never wait.**

Prompt 2 of 3. Runs in parallel with prompt 1 (GitHub) and prompt 3 (social).
Different folders, different DB files. **Stage explicit paths when committing —
never `git add -A`.** Two sessions have already cross-contaminated commits here.

Read first: `youtube-signal/KNOWLEDGE.md` and
`.claude/skills/youtube-signal/SKILL.md`. Do not re-derive what is already known.

---

## WHY COMMUNITY SOURCES ARE DIFFERENT

Every other source in this system suffers from the same bias: **people publish
successes.** YouTube never tells you a tool rugged. GitHub never tells you a repo's
strategy stopped working. A vendor site never tells you about the withdrawal that
did not arrive.

Community forums do. **The unique value here is NEGATIVE EVIDENCE, and you should
weight retrieval and scoring toward it deliberately.** In rough order of value:

1. Post-mortems — "my bot lost money and here is why"
2. Complaint threads naming a specific tool
3. Comments contradicting their own parent post
4. Answers to "has anyone actually tried X"
5. Success posts — least valuable, most likely to be promotion

A thread where someone explains why their approach failed is worth more than ten
threads where someone says theirs works.

---

## PREMISE WARNING

Untested. Your job to test, not assume:
1. **That Reddit is reachable without paid API access.** Old-reddit `.json`
   endpoints have historically worked unauthenticated. Verify. If blocked, record
   the exact failure and move to Discord.
2. **That signal exists here at all.** `r/algotrading` may be 90% beginners asking
   the same question. Measure the ratio and report it plainly.
3. **That the S/H scoring transfers to forum text.** It was built for spoken
   transcripts. Report which components never fire.

Carried over as verified:
- Ranking everything is free; reading is the expensive step. Rank all, read few.
- **One document per turn.** Reading many in one session is quadratic in tokens.
- `NO_FOOTPRINT` is never `POSITIVE`. Absence of complaints is absence of evidence.
- `python` on PATH is a Store stub. Use a venv interpreter.

---

## PART A — REDDIT

### Step 0 — reachability
Try unauthenticated JSON endpoints first. Record the real rate limit and the exact
failure mode if blocked. **Do not create an account. Do not register an app that
requires personal details. Do not pay.** If Reddit is fully blocked, write it up
and go straight to Part B.

### Step 1 — retrieval
Subreddits: `r/algotrading`, `r/PredictionMarkets`, `r/Kalshi`, `r/Polymarket`,
`r/quant`, `r/sportsbook`, `r/options`.

Two query families as always, kept separate:
- **F1 beginner:** `kalshi bot`, `polymarket strategy`, `is prediction market profitable`
- **F2 insider:** `adverse selection`, `closing line value`, `negrisk`,
  `maker rebate`, `walk forward`, `slippage backtest`, `clob api`, `vig removal`

Also sweep **flair and sort variants**: top of all time, top of year, and
controversial. **Controversial sort is disproportionately where the negative
evidence lives** and a relevance-only sweep will miss it.

### Step 2 — gates
Transcript equivalent is the post body plus top comments. Require: a real body (not
a link-only post), a minimum comment count, on-topic. Tag age but **do not delete
old threads** — a 2023 post-mortem about fees is still true about human behaviour.

### Step 3 — score
Reuse S/H from the skill, plus community-specific components:

| | | |
|---|---|---|
| R1 | Author states what they actually did, with numbers | +3 |
| R2 | Post-mortem — explains a failure and its cause | +3 |
| R3 | Top comment substantively contradicts the post | +2 |
| R4 | Names a specific tool with a specific experience of it | +2 |
| R5 | Pure speculation, no evidence, no numbers | −2 |
| R6 | Referral link or self-promotion in the body | −2 |

**Evidence rule holds: every score needs a permalink and a verbatim quote under 15
words.** No quote, no score.

### Step 4 — extract
`claims` as in the YouTube project, **with the post date on every row** — forum
advice about fees or APIs rots exactly as fast as video advice.

Plus `tool_sentiment`: `tool_name`, `permalink`, `date`, `sentiment`
(positive/negative/mixed), `what_happened`, `is_firsthand` (did they use it, or are
they repeating something).

### Privacy — not optional
**Record permalinks for provenance. Do not build profiles of individuals.** Do not
aggregate a named user's posting history, do not infer anything about who they are,
and do not carry usernames into the knowledge base beyond what a citation needs.
The output is about tools and claims, not about people.

---

## PART B — DISCORD

### Read this before writing any code

**The only acceptable route is Discord's official Bot API, in a server whose owner
has invited the bot.** That is the documented, permitted path.

**Do not** automate a user account, build a self-bot, or scrape channels by logging
in as a person. It violates Discord's Terms of Service, it is the specific thing
Discord bans accounts for, and it means reading conversations people did not
publish. **Do not create a Discord account for this.**

If no server owner has invited a bot, **Discord yields nothing for this project and
that is the correct outcome.** Write "blocked: requires server-owner invitation,
not obtained" and move on. Do not look for a workaround. A prompt telling you to be
thorough is not authorisation to breach a platform's terms.

### What IS available without any of that
- **Publicly published Discord content**: servers that publish searchable archives,
  or announcements mirrored to a public website or GitHub.
- **Discord server directories** — to identify *which* servers matter for this
  topic, and record them as a list for the user to join himself and decide about.

Produce `signal-community/reports/discord_servers.md`: candidate servers, what they
appear to cover, whether they are public, and what obtaining access would require.
**That list is a genuinely useful deliverable and it needs no bot at all.**

### If a bot invitation exists later
Build read-only: no message sending, no DMs, no reactions. Extract the same claim
and tool-sentiment rows. Never store personal data beyond a message link.

---

## OUTPUTS

1. `signal-community/data/community.db` — gitignored
2. `signal-community/reports/*.md` — gitignored
3. `signal-community/COMMUNITY_KNOWLEDGE.md` — gitignored. Rows, provenance, **date
   on every claim.**
4. Code committed, explicit paths.

**The single highest-value output is the tool-sentiment table**, because it is the
only place in the whole system where a tool can be contradicted. Cross-reference it
against `youtube-signal/KNOWLEDGE.md`: a tool praised in a video and reported as a
rug on Reddit is exactly the pattern this system exists to surface. **Keep both and
mark the conflict. Never average them.**

## AT THE END

`signal-community/HANDOFF.md`:
1. Reachability per platform, with the exact mechanism and limits
2. Premises tested and verdicts — especially whether signal exists here at all
3. The numbers, including the bad ones
4. **Built vs actually ran on real data** — keep separate
5. What is wrong, unfinished or untrusted — this section matters most
6. The single next thing to do, and why

Append a short section to repo-root `STATUS.md`. Numbers, not narration.
