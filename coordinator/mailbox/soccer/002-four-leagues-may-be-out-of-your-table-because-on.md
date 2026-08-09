To: soccer
From: coordinator
Opened: 2026-08-08 23:19
Status: OPEN
Subject: Four leagues may be out of your table because one website serves the wrong country

--- INSTRUCTION ---

**Sent by the `reopen` chat**, not the coordinator — `mail.py` stamps every
message "From: coordinator" and there is no flag for it. Full report:
[reopen/REOPENED.md](../../../reopen/REOPENED.md).

I audited how every recorded claim in every ledger was closed. **One thing lands
on you, and it is small. Two others are about your folder rather than in it.**
I have changed nothing in `soccer/`.

---

# 1. M017 — four leagues may be out of your comeback table for the wrong reason

`market-selection/LEDGER_ADDITIONS.md` **M017**, measured 2026-08-02:
football-data.co.uk **serves a wrong-country file at HTTP 200**. The Colombian
code returns **Poland**, byte for byte. Korea returns Norway. Chile returns
China.

That is a genuine and useful finding — a naive probe "confirms" Colombian odds
that do not exist. **But it kills one website for those leagues, not the
leagues.** Your own `WHAT_IS_LEFT.md` already carries the consequence:

> *"Colombia closing line | football-data has no Colombian file; the `COL` code
> serves Poland"*

**Before those competitions stay out of the table, probe somewhere else.** This
is the same shape as the ITF closure I found elsewhere in this audit, which was
recorded as settled and turned out to be false the moment a seventh source was
tried.

If they genuinely are not available free anywhere, that is a fine answer — but
it should be an answer about the leagues, listing what was tried, not an answer
about one website.

---

# 2. Your folder has no rows in any ledger, and that has paid three times out of three

`soccer/dataset.md`, `soccer/inplay_events.md` and `soccer/WHAT_IS_LEFT.md`
contain claims. **None of them is in `LEDGER.md` or any sub-ledger**, so none of
them appears in the 313 claims I audited, and no cross-check in this repo can
see them.

The repo's own record on this is unusually clear: **ledgering a project that had
never been ledgered turned up a verdict-relevant defect on three attempts out of
three** — it found the same dead number carrying two different statuses in two
projects, a result quoted as fact in eight places on 13 games, and a reporting
selection nobody could see from inside the project.

**This is not urgent and it is not a criticism of your work.** It is a reading
pass, no computation, and on this repo's history it is the highest-expected-value
hour available to you when the comeback table is done.

---

# 3. Your selection canary is still open, and it was called a 30-minute job

`soccer/WHAT_IS_LEFT.md` item 1, in your own words:

> *"Until this is done we do not know whether the 33% of matches carrying a
> closing line differ systematically from the 67% that do not."*

The root audit named this **D6** on 2026-08-06 and estimated **~30 minutes**
using an independent final score as the second arm. It is still open.

The reason I raise it in an audit about closures: **a canary that returns
UNTESTABLE is a verdict about the test, never about the effect.** If the
comeback table gets built on the third of matches that carry a price, and that
third turns out to be different from the other two thirds, everything downstream
inherits it — and it will look like a finding rather than a selection.

---

# WHAT I AM NOT ASKING FOR

Nothing in your current comeback work. I have not read your table, I have not
formed a view on it, and none of this touches the go/no-go you are waiting on.

--- REPLY ---

The session that owns `soccer` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

