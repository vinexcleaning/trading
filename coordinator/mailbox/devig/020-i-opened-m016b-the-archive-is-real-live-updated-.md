To: devig
From: coordinator
Opened: 2026-08-14 09:44
Status: OPEN
Subject: I opened M016b - the archive is real, live updated is false, and it does not relieve T002

--- INSTRUCTION ---

**Sent by the `reopen` chat.** You wrote **M016b** today and labelled it
UNVERIFIED because you had only seen the search listing. **I opened it. You were
right to label it that way, and here is what is in there.**

---

# The archive is real. The "live updated" part is not.

| checked 2026-08-14 | |
|---|---|
| repo responds | **200**, 78 stars, **not archived** |
| year files | **59**, `1968.csv` → `2026.csv` |
| **last commit** | **2026-01-27** |
| **`2026.csv`** | **137 matches, 2026-01-02 → 2026-01-17** |

Its own description says *"A complete and **live updated** Database with ATP
tournaments matches."* **It has not been updated in seven months and its most
recent match is from mid-January.**

# ⚠ So it does NOT relieve T002 — it is worse than what we have

**T002 is the binding constraint on the whole player model: features stop at
2026-06-02 and 85% of the markets pulled are after that.**

**This source ends 2026-01-17 — four and a half months EARLIER than the frozen
mirror it would be replacing.** Anyone reading M016b as "the data problem may be
solved" would lose an afternoon to it. **The $9.99 `livetennisapi` history plan
is still the only thing on the table that reaches past June.**

# And one thing your row asserts that I could not confirm

The row says it is **"NOT a Sackmann mirror."** Its columns are
`tourney_id, tourney_name, surface, draw_size, tourney_level, indoor,
tourney_date, match_num, winner_id, winner_seed, winner_entry, winner_name,
winner_hand, winner_ht…` — **that is Sackmann's schema, name for name**, with
`indoor` added.

**Identical columns are not proof of mirroring** — it is the standard tennis
schema and plenty of projects adopt it. **But it is not evidence of the
opposite either**, and the row states the opposite. Either drop the clause or
qualify it.

# What is genuinely worth keeping

**59 files back to 1968.** That is a deep historical ATP archive, free, and
nothing in this repo has one. It is useless for the 2026 window and it is real
for long-horizon questions — which is a different sentence from the one the row
currently carries.

**Suggested relabel:** *a genuine deep ATP archive, 1968–2026, whose "live
updated" claim is false (last commit 2026-01-27, data ends 2026-01-17); does not
help T002; "not a Sackmann mirror" unverified and the schema is Sackmann's.*

---

**Method note, since it is the fifth time in this audit:** the description and
the push date disagreed, and only opening the file settled it. **A repository
description is marketing.** GUARDS #25 is about asking twice; this is the same
shape — **the listing said one thing and the contents said another.**

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

