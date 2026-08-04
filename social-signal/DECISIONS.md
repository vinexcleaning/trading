# DECISIONS

Method decisions taken without asking, with the reasoning and the measurement
that forced each one. Conservative reading taken wherever ambiguous.

Written retrospectively at the end of the 2026-08-04 session, after `CLAUDE.md`
§2 was re-read — the decisions below were taken and recorded in commit messages
and `HANDOFF.md` at the time, but not in this file, because this file did not
exist. That is itself the first thing to record.

---

## D1 — Reddit is collected from an archive, not from reddit.com
**2026-08-04.** The brief specified `reddit.com/*.json`. Measured:
`reddit.com`, `old.reddit.com` and `oauth.reddit.com` all return
`User-agent: *` / `Disallow: /`, and `.json` returns **403** to a bot UA and a
browser UA alike. `api.pushshift.io` returns 403 "Not authenticated".
`arctic-shift.photon-reddit.com` publishes a documented JSON API, its
`robots.txt` is `Disallow:` (empty, everything permitted), and it returns
`X-RateLimit-Reset` headers.
**Conservative reading:** with a browser User-Agent, `reddit.com/.rss` returns
**200 and 54 KB** — the block is not technical. Not taken anyway, because a
User-Agent string is not consent. A "cannot be done within the rules" result is
a real result.

## D2 — Entities are matched on an exact key or a URL, never a name search
**2026-08-04.** Both sibling projects recorded that free-text name resolution
returns a different project at rank 0, confidently. A compact key hitting more
than **3** repos is refused rather than resolved, and name-matched rows carry ⚠
in the report.
**Risk accepted:** `OpenClaw` still matched `daidue/OpenClaw` (0★), very likely
a different project — OpenClaw is also a game reimplementation. Flagged, not
adjudicated.

## D3 — ADVOCACY is separate from CORROBORATION
**2026-08-04.** The first verdict logic counted any positive stance against any
negative one, which made every ordinary tool with a critical comment a
"contradiction". A `CONTRADICTION` now requires someone **telling you to use it**
plus evidence against. A stale repo somebody mentioned in passing is a stale
repo.

## D4 — A Reddit negative needs ≥3 windows AND ≥10% share before it reaches a verdict
**2026-08-04.** Measured: `arxiv.org` scored `SCAM_ALLEGED` **twice against 309
neutral windows** and came out a CONTRADICTION; `archive.pmxt.dev` scored it
twice on the promotional post's own sentence *"charging devs for raw market data
is basically a scam"* — an accusation aimed at other vendors, counted against
the speaker. CONTRADICTION fell 25 → 10, AGREE_NEGATIVE 24 → 11.
**Chosen once and stated in the report, NOT tuned against the output.** A
threshold picked to produce a nicer table is a threshold that means nothing.
**Conservative reading:** raw counts stay in the table as evidence; the floor
gates the *verdict*, not the record.

## D5 — An accusation naming the entity as the victim is suppressed, not counted
**2026-08-04.** MetaMask came out a CONTRADICTION on three `SCAM_ALLEGED`
windows reading *"steal **from the linked** metamask account"* and *"the
remaining $1k usdt **in my** MetaMask to get stolen"*. The accusation is against
a third-party site; the wallet is the victim.
**Conservative reading:** the test is deliberately narrow — possessive and
source-marking constructions only. It will miss cases and will not invent any,
which is the right way round for something that **suppresses** evidence.
Suppressed windows are recorded as `NAMED_AS_VICTIM` rather than dropped, so the
count stays auditable. `predictionhunt.com` (8 scam windows of 17) survived it.

## D6 — The rubric was NOT patched after its defects were found
**2026-08-04.** Five reads produced five defects, including in the document the
scorer ranks highest. Tuning patterns until they fire correctly on five examples
you happened to read is the overfitting this programme exists to catch, and it
would swap a *known-bad* instrument for an *unknown* one.
**Consequence accepted:** the stance lexicon's precision is **UNKNOWN** and no
number is quoted for it anywhere. No verdict in `TOOL_REPUTATION.md` rests on
the proxy; it ranks what to read next and nothing else.

## D7 — The tool probe's comment leg is off by default
**2026-08-04.** `?subreddit=X&body=Y` returns
`422 {"error":"Timeout. Maybe slow down a bit"}` while the equivalent post
search returns 200 instantly. It is not a malformed request — the same call
without a subreddit returns 400 with a different message. My transport had been
retrying 422 at 5/10/15/20 s, which is how something whose own docstring says
"back off, never hammer" ends up hammering a volunteer research service.
**Decision:** 422 now backs off in minutes; the comment leg needs
`--tool-comment-search` to run at all. It is near-redundant anyway —
`reddit_stance.py` searches the local corpus offline for free.

## D8 — Collection was stopped at 125 of 400 threads on the first comment pass
**2026-08-04.** The archive was degrading and the remaining session budget was
better spent on analysis than on a 2.5-hour pull.
**Superseded the same session:** the user asked for it to be resumed, it ran
400/400 in **401 calls with 0 errors and one 422 in 21.5 minutes**, and the
corpus doubled. **The degradation was mine, not the archive's** — see D7.

## D9 — Discord author identities are salted per run and the salt is discarded
**2026-08-04.** `discord-trades-export/` names real private individuals and this
repo is PUBLIC (`CLAUDE.md` §7). Pseudonyms are generated from a salt created at
import and **never written anywhere**, so they cannot be reversed after the
process exits. No handle, user id, server name or message text reaches any
report.

## D10 — `STATUS.md` is edited at byte level with each substitution asserted unique
**2026-08-04.** Several sections of `STATUS.md` carry mojibake from an earlier
cp1252 round-trip. Decoding and re-encoding the file would either preserve that
or silently "fix" another session's text. Edits are byte-level and every
replacement asserts exactly one occurrence, so a stray match elsewhere aborts
rather than rewriting a sibling's entry.

---

## Open audit items

- **D2's `OpenClaw` row is unadjudicated.** One name match, plausibly the wrong
  project.
- **The stance lexicon has no precision estimate** (D6) and six known defects.
- **538 of 39,629 posts have their comments.** Stance and scoring run mostly on
  post text, which is the weaker half of the platform.
- **The tool probe has never run** in any form (D7).
