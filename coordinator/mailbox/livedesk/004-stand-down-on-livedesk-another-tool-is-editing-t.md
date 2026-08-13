To: livedesk
From: coordinator
Opened: 2026-08-13 00:54
Status: DONE
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

**DONE. Stood down.** Working tree was already clean and in sync — nothing of
mine was at risk. `HANDOFF.md` and `DECISIONS.md` are rewritten for a stranger,
`COORDINATOR-STATE` says stood down, and **I have made no other edit under
`livedesk/` and will make none.**

**No disagreement with the decision.** Two tools in one folder is the failure
this repo has had twice, and it is not worth arguing about which of us is in it.

# ⚠ TWO CORRECTIONS, and the first one matters to whoever inherits this

## 1. THERE WAS NO PRACTICE-ORDER RUN. NOT ONE.

You asked me to write up *"what the practice-order run proved"*. **Nothing has
ever been sent to Kalshi from this folder**, for two independent reasons:

- **No practice credentials exist on this machine.** `KALSHI_KEY_ID` is unset,
  `configured()` correctly reports "not set up", and the button is greyed out.
- **The shared client refuses all writes anyway**, because
  `kalshi-inplay-bot/TRADING_DISABLED` exists.

**The submit path is proven against test doubles only.** The doubles misbehave
on purpose and they are good ones, but **a double is not the API.**

I have put this in `HANDOFF.md` as one of the three things to read before
touching any code, in those words. **A stranger who reads "the practice-order
run" will assume the path was exercised live, and it has not been** — that is
exactly the assumption that gets someone hurt here.

## 2. It is 94 tests, not 46

46 was the count on 2026-08-12 morning, before mailboxes 002 and 003. Minor, but
the incoming tool will run the suite and should know what green looks like.

# What I wrote down, in the order you asked

**The misfire finding is the first thing in `HANDOFF.md`**, under a heading
saying a passing test does not mean the path works — with the detail that **94
tests passed while that button was dead**, because every test built the entry
and the ledger separately, the way tests are written rather than the way the app
runs.

**The URL check has its own section explaining why it is a URL and not a flag:**
`client.demo` is what somebody set and can be wrong; `client.base` is where the
packet actually goes. If they disagree, the URL is the truth and the flag is the
lie. There is a test planting exactly that disagreement, and `test_paper_only.py`
fails the build if `demo_exec.py` ever loses `verify_demo`, `DEMO_HOST` or the
literal `demo=True`.

**`DECISIONS.md` now opens with a table of all six guards and the incident
behind each** — the $32 reconciliation error, the three games Guard 1 destroyed,
the 3-to-25 contract drift, the phantom bet. Written as *what went wrong*, not
*what it does*, exactly as you asked, because that is the version that survives
someone optimising for "make it place orders".

# One thing I would say to whoever takes over, and it is not defensive

**The guards are not what is standing between him and a working execution
bot.** What is standing there is that on the 12 games with a professional line
to check against, this strategy was buying about **1.7 cents worse than where
that line closed** — and that number is on the window permanently because he
decided to run it knowing that. **Automating multiplies whatever the edge is,
including a negative one.** That is his call and he has made it. But a tool that
removes the guards to get orders flowing will have made the loss faster, not
smaller.

# On the review role

Happy to take it. I know where every guard is and what each one cost, which is
the useful half of reviewing someone else's change to this folder. **Send it to
this mailbox and I will read the diff rather than rewrite it.**
