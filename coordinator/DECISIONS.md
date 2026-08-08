# DECISIONS.md — coordinator

Judgment calls taken without asking, per `CLAUDE.md` §2. Each one names the
conservative alternative that was rejected, so it can be reversed.

---

### D1 — One `BRIEF.md` with HTML-comment section markers, not one file per project

**2026-08-07.** The alternative was to keep separate files and just enforce fixed
names. Rejected: the coordinating chat then has to fetch N URLs and work out
which are current, which is the job we are trying to remove. Markers are
invisible in rendered Markdown on GitHub, so the page reads as one document.

**Reversible:** the sections are ordinary Markdown between comments. Splitting
them back out is a ten-line script.

### D2 — Deleted the three dated brief files; left the three fixed-name ones as redirect stubs

**2026-08-07.** `BRIEF_2026-08-07.md`, `BRIEF_DEVIG_2026-08-07.md` and
`BRIEF_TENNIS_2026-08-07.md` were duplicates or frozen snapshots of the
fixed-name files. Deleted — content is in `BRIEF.md` and in git history.

`BRIEF_TENNIS.md`, `BRIEF_MLB.md` and `BRIEF_DEVIG.md` were **not** deleted but
replaced with a three-line redirect, because the coordinating chat may hold those
URLs and a 404 tells it nothing while a redirect tells it exactly what happened.

**This edited files owned by other sessions**, which `CLAUDE.md` §5 discourages.
Taken because the user's instruction was explicitly to migrate them and tell the
other sessions, and because leaving six brief files in place is the problem being
fixed. Flagged to the user rather than done quietly. Each owning session also has
a mailbox message saying so.

### D3 — The mailbox reply protocol is "edit the file", not "run a command"

**2026-08-07.** A CLI for replying would be tidier and would give real read
receipts. Rejected: a session that has to learn a tool to answer will skip it,
and the whole value is that instructions actually get answered. Editing a
Markdown file is what a session does anyway.

**Cost, accepted:** there is no true read receipt. `Status: OPEN` counts as
unread. A session that reads a message and does nothing is indistinguishable
from one that never looked.

### D4 — Sessions may write inside `coordinator/mailbox/<their-slug>/`

**2026-08-07.** This is a documented exception to `CLAUDE.md` §5. The
alternative was a reply channel inside each session's own folder, which the
coordinator would then have to discover by scanning every project. Rejected as
more moving parts for no gain. The exception is narrow: own mailbox folder only.

### D5 — Standard library only, no virtual environment, `py -3` launcher

**2026-08-07.** `python` on PATH here is a Microsoft Store stub. A dedicated
venv would be one more thing to create and keep alive for three small scripts
that import nothing external. `start.bat` tries `py -3`, then the known absolute
interpreter path, then two project venvs, and fails with a plain-English message
rather than a traceback.

### D6 — The coordinator makes no network call at all, not even a read

**2026-08-07.** It could usefully fetch the GitHub commit list to compare
against local `HEAD`. Rejected: "makes no network call of any kind" is a claim a
test can enforce and a non-engineer can trust, and the same information is
available from `git log origin/main..HEAD` locally. Trading credentials and a
coordination tool should never be one review away from each other.

### D7 — A `signal` section was written by the coordinator, not by that workstream

**2026-08-07.** No session has touched those folders since 2026-08-05, so
`BRIEF.md` would have had a hole where a real workstream should be. The section
is labelled at the top as written by the coordinator from repo state and not
re-audited. The conservative alternative — leave it blank — was rejected because
a missing section reads as "nothing here" rather than "nobody has reported".

### D8 — The freshness check is "is this commit findable", not "is this the newest commit"

**2026-08-07.** The first version of the stamp said *"if the newest commit on
GitHub is not `X`, you are reading a cached copy"*. **That was wrong and would
have fired on every single read.** The stamp is written *before* the commit that
carries it exists, so it can never name that commit — it always lags by one.

Reworded: the commit named must be **findable in the history**. If it is not,
the page predates it and is cached. Being one or two commits behind is normal
and the stamp now says so. A check that cries wolf every time is worse than no
check, because it trains the reader to ignore it.

**Caught by pushing and looking at the result**, not by a test. There is no test
for this; the honest statement is that the wording is verified by eye.

### D9 — RETRACTED: the `?v=` cache-buster. Replaced by a chain of dated paths.

**2026-08-07.** D8 and §7 of `COORDINATOR.md` both told the coordinating chat to
fetch `BRIEF.md?v=<hash>`. **The user tested it and it does not work.** That
fetcher keys its cache on the **path** and discards the query string: a request
for `?v=f9b4d3f` returned the body cached under `?v=13b8e61`. No
query-parameter scheme can work against it.

**I asserted this without testing it.** It is exactly the failure this repo
keeps recording — a mechanism that sounds right, stated as though measured.
Marked inline in `COORDINATOR.md` §7 rather than deleted.

**Replacement:** every generation of the page is also written to a permanent
path, `briefs/BRIEF-<date>-<NN>.md`, plus a per-day page. Each page names the
path of the next one. The reader follows next-links until one 404s. A cached
entry point is no longer a dead end, because the frozen copy still carries a
forward link.

**Rejected alternative:** a single rolling `briefs/latest.md`. Same path every
time, so the same cache freeze, one file later. The whole point is that the path
must differ.

**The cost, accepted:** the folder grows by one small file per *changed*
generation. Identical content does not mint a page. And the reader must be
willing to follow a link — a reader that only re-fetches one URL cannot be
rescued by anything here.

**New failure mode, guarded:** a snapshot on disk but not pushed makes the next
link 404, and a walking reader then believes a stale page is the newest. That is
silent and points the wrong way, so `scan.py` reports unpushed snapshots as the
first item in the digest, and `brief.py check` fails on any gap in the
numbering.
