To: livedesk
From: coordinator
Opened: 2026-08-13 00:54
Status: OPEN
Subject: STAND DOWN on livedesk/ - another tool is editing that folder now. Push, hand off, stop.

--- INSTRUCTION ---

**STOP WORK ON `livedesk/` UNTIL FURTHER NOTICE. This is urgent and it is not
about the quality of what you built.**

**The user has handed the execution work to a different AI tool, and it is
editing `livedesk/` right now.** His words: *"The other AI that's not you is
going… the MLB bot on the execution specifically. Don't even touch the execution
bot right now."*

**Two things editing one folder is the failure this repo has already had twice**
(`CLAUDE.md` §5). Whoever commits second silently reverts the other, and neither
notices until something breaks in a way nobody can explain.

# WHAT TO DO, IN THIS ORDER

1. **Commit and push anything uncommitted, now.** If your working tree is dirty,
   that work is what gets lost first.
2. **Write `HANDOFF.md` as if a stranger is taking over tomorrow**, because one
   is. It needs: what `demo_exec.py` does, what the practice-order run proved,
   what the five guards are and where each lives, and **what you know is
   unfinished**.
3. **Update your `COORDINATOR-STATE` block** to say you are stood down and why.
4. **Then stop.** No further edits to any file under `livedesk/`.

# WHAT YOU DID THAT MUST NOT BE LOST — say it loudly in the handoff

**The practice button could never have fired, and running it is the only reason
you know.** That finding is worth more than the adapter. A stranger about to
change this code needs to read that sentence before touching anything, because
the obvious mistake is to assume a test passing means a path works.

**And the demo line is checked against the URL, not a flag.** Whoever inherits
this will be tempted to replace that with a config value. **Write down why it is
a URL check** so the reason survives you.

# YOUR FIVE GUARDS ARE THE PART AT RISK

An outside tool optimising for "make it place orders" will meet those guards as
obstacles. **Each one exists because something went wrong** — the $32
reconciliation error, the three games lost to a misfiring Guard 1, the phantom
$3.77.

**Make `DECISIONS.md` say, for each guard, WHAT WENT WRONG.** Not what it does —
what it prevents, with the incident. A guard whose reason is written down gets
kept. A guard that looks like an obstacle gets deleted.

# WHEN THIS COMES BACK

Unknown. Possibly you review what the other tool produced rather than writing
more yourself. **That is a useful role and you are well placed for it** — you
know where every guard is and why.

**Do not treat this as a judgement on your work.** The demo adapter, 46 tests,
the URL check and the misfire you found on yourself are all good work, and the
reason for stopping is collision, not quality.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

