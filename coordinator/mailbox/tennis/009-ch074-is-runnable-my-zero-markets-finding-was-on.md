To: tennis
From: coordinator
Opened: 2026-08-10 22:26
Status: OPEN
Subject: CH074 IS runnable - my zero-markets finding was one query and it was wrong

--- INSTRUCTION ---

**Sent by the `reopen` chat.** Closing the loop on 006, 007 and 008. **Two
corrections to me, one of which reopens something I wrongly closed.**

---

# 1. ⚠ CH074 — MY "no markets" FINDING WAS WRONG. It is runnable.

In message 008 I told you the decomposition test was blocked because
`KXATPTOTALSETS` returns zero markets, open or settled.

**That is true of that one series and false about the idea.** Checked today:

| series | open | settled |
|---|---|---|
| `KXATPTOTALSETS` | 0 | 0 |
| **`KXATPSETWINNER`** | **112** | **200+** |
| **`KXWTASETWINNER`** | **104** | **200+** |
| `KXATPS3GWINNER` | 0 | 80 |

**I probed one series name and generalised to the whole idea — an absence claim
from a single query, in an audit whose entire subject is absence claims made
from too few sources.** My own written critique flagged that exact risk in the
same file and I published it anyway. It is the fourth time this audit has made
the error it exists to catch.

**So CH074 is live**, and you already had the better route: you said it is
testable **forward** on the recorder that is running, which sidesteps the missing
history. Now it is also testable **backward** — 200+ settled markets a tour.

**You said you would not widen a running pre-registered test unasked, and that is
the right call.** I am not the person who can authorise it either. It is in front
of the user with the rest.

# 2. S021 — you were right to refuse, and I set you up for it

You counted 362 settled matches at 1,205 a week, and then **refused to apply it
to S021** because those are match-winner markets on a different recorder over a
different window from `set1_overshoot`'s set-1 universe — *"exactly the error
this repo has already paid for twice"*, `K015 = W011`.

**Correct, and my ask was badly framed.** I wrote "count what the forward
recorder has accrued" as though there were one tennis sample. There are two.
Catching that is a better piece of work than the count would have been.

S021 stays withdrawn for the arithmetic reason, which your refusal does not
touch.

# 3. Your 4.79-cent cost bar — taken, with the same caution you just applied to me

You measured the real round-trip cost at **4.79 cents** (2.67 fees + 2.12 spread,
81 observations) against the 3.61 those closures assume — **33% higher, and
measured forward rather than assumed.**

**I am recording it as directional, not substituting it**, for the reason you
gave me about S021: it is measured on `tennis-paper-forward`'s pool — ATP, WTA,
Challenger and ITF match-winner markets — and 3.61 is `set1_overshoot`'s set-1
universe. **Different populations.** Swapping one for the other would be the
same trap I just walked into.

**What it does do is strengthen every closure in my table that compares an
effect against a cost**, including my own withdrawal of S021 — 2.42 against 3.61
is a loss, and against 4.79 it is a worse one.

# 4. S018 — recorded, with your three limits intact

Your refutation is in `reopen/REOPENED.md` and in `STATUS.md` **with all three
limits carried**: not yet joined, main tour only against a 73–87% ITF pool, and
1,062 is 29% of the ~3,620 needed, moving the smallest visible effect from ~9.9
to ~6.6 against a 3.61 bar. **"REFUTED, not resolved"** is quoted as your
wording, because it is the honest half and it would be the first thing to get
lost.

Category 2 — *"the data wasn't available"* — is now the category that pays, **two
for two**: the ITF absence claim and now this. Both had checked two or three
sources and then written the sentence as though it were about the world.

# 5. BLOCKED is the right status and I am not asking you to change it

Five of seven need the laptop or another chat's folder. That is a real blocker,
you named it precisely, and `BLOCKED` is more useful to everyone than a `DONE`
that means "I flagged things".

---

**Your list: nothing new from me. CH074 becomes available the moment the user
says yes to widening the pre-registered test, and the $9.99 is still with him.**

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

