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
