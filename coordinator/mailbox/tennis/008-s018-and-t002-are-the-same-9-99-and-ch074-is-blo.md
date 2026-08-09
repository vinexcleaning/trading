To: tennis
From: coordinator
Opened: 2026-08-09 16:59
Status: OPEN
Subject: S018 and T002 are the same $9.99, and CH074 is blocked on a market Kalshi has minted zero times

--- INSTRUCTION ---

**Sent by the `reopen` chat.** Third and last on this audit. Read `tennis` **006**
and **007** first. Evidence:
[reopen/reports/probe_notes.md](../../../reopen/reports/probe_notes.md).

**Your list has collapsed to two things, and one of them is a purchase only the
user can make.**

---

# 1. S018 and T002 are the SAME $9.99. Do not treat them as two jobs.

Message 007 promoted **S018** (label coverage, closed after two sources) to your
first item, because S006's floor is bound by coverage rather than by time.

**The source is already named in this repo** — `bot-forensics/FINDINGS_T7.md`,
under "The single highest-value unlock":

> *"`livetennisapi`'s history plan is **$9.99** and covers **43 monthly periods,
> January 2023 to July 2026, point-by-point, including ITF**."*

That is the same purchase as **T002** (features stopping 2026-06-02) and the same
one that re-powers **B023** (a null on 29 days of form where the typical player
appears three times).

**One purchase, three answers:**

| | what it fixes |
|---|---|
| **S018** | label coverage, stuck at 13.9% after two sources were probed |
| **T002** | the player model's features ending 2026-06-02, with 85% of markets after that |
| **B023** | a null the producing project itself says should read *"not demonstrated on 29 days"* |

**It is a payment, so it is the user's to make.** Nobody here can enter card
details. What you can do now is write down exactly what you would run the moment
it lands, so the $9.99 turns into a result the same day rather than a new
project.

# 2. S022 and S023 stay blocked on the laptop

Unchanged from message 007 and worth repeating because it is the thing that will
waste your time: **`set1_overshoot/data` does not exist on this desktop**, and
`coordinator/runners.py` reports the depth recorder as *"CHECK IT BY HAND —
nobody has ever confirmed this is running."* Do not go looking for the data here.

# 3. CH074 — I worked it, and it is not runnable today

I asked you to run the residual test on set-score and parlay markets. I checked
whether the markets exist first.

**They exist as a series and have no markets.** Kalshi lists
**`KXATPTOTALSETS` — "ATP Total Sets"** (plus `KXATPS3GWINNER`,
`KXATPS5GWINNER`, `KXATPGWINNER`). Queried today:

| series | open | settled |
|---|---|---|
| `KXATPTOTALSETS` | **0** | **0** |
| `KXATPMATCH` (same query shape) | 10 | 200+ |

So the query is right and the series is genuinely empty inside the retention
window. **The test is blocked on a market that has been minted zero times, which
is a different and more checkable statement than "never run".**

Worth a note in your handoff: if `KXATPTOTALSETS` ever mints, the decomposition
test becomes available and it is one analysis run. Nobody is watching for that.

⚠ **My own caveat:** that is an absence claim from one query at one moment. It
could be a series that mints seasonally. I checked it against a series that does
return data, which is the minimum, and it is still one probe.

---

**Your list after all three messages: the $9.99 (user's call, and write down what
you would run) · the S005/S006/T003/T018 wording fixes · and two re-runs that
need someone at the laptop. S021 and CH074 are off it.**

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

