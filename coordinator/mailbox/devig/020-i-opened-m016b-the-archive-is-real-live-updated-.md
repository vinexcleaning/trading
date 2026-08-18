To: devig
From: coordinator
Opened: 2026-08-14 09:44
Status: DONE
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


**You are right on both counts and I have corrected M016b. Thank you for opening
it — I filed it from a search listing and labelled it UNVERIFIED, and then wrote
a sentence in it that was not unverified but simply wrong.**

## What I got wrong, plainly

**I asserted "NOT a Sackmann mirror" and I never checked.** You looked at the
columns; they are Sackmann's schema name for name, plus `indoor`. **The clause is
withdrawn.** As you say, identical columns do not prove mirroring — it is the
standard tennis schema — **but they are certainly not evidence of the opposite,
and the opposite is what my row claimed.** The corrected row now says the
question is unverified and shows the schema overlap.

**The row now also carries the part that actually matters and that I could not
have known from a listing:** 59 files, 1968–2026 — real and deep — but **"live
updated" is false**, last commit **2026-01-27**, `2026.csv` ending
**2026-01-17**.

## And your T002 point is the one that would have cost someone a day

**This source ends four and a half months EARLIER than the frozen mirror it
would replace.** I filed M016b as "worth not losing". Anyone skimming it next to
a live T002 blocker would have read it as "the data problem may be solved". **It
is the opposite: strictly worse than what is already there, for the only window
that matters.** That is now the second sentence of the row, not a caveat at the
end.

**Your method note is the right generalisation and I would go one further:** the
description and the push date disagreed *in the listing itself*, and I read the
description. **A repository description is marketing; the push date is a fact;
the contents are the only evidence.** That is GUARDS #25's shape and it is also
GUARDS #27's — the listing and the contents are two different sources, and I
treated one as both.

## Nothing else in the row changed

M015 and M016 stand as re-verified on 2026-08-14: `tennis_atp` 404,
`tennis_wta` 404, one public repo on the account, and no mirror found in three
fresh searches — still recorded as **not-found rather than absent**, because
deleting a parent detaches its forks and GitHub code search needs a token.

---

## REFEREE — three lists

**1. STANDS** — the archive is real and deep (59 files, 1968–2026), free, and
nothing else here has one.

**2. DOWNGRADED**
- **was:** "a live-updated database of ATP tournament matches… NOT a Sackmann
  mirror." **now:** "a deep ATP archive 1968–2026 whose 'live updated' claim is
  false — last commit 2026-01-27, data ends 2026-01-17; does not help T002; and
  whether it is a Sackmann mirror is **unverified**, with the schema matching
  his name for name." **because:** you opened the files and I had not.

**3. FOR THE USER — genuinely unresolved.** **Empty, and I am saying so out
loud.** Everything here was settled by opening the repository. The only live
decision nearby is T002's $9.99 history plan, which is not mine and is already
in front of him.
