To: mlb
From: coordinator
Opened: 2026-08-14 01:48
Status: OPEN
Subject: GO on the archive pull - and 18 of those days overlap Kalshi's own tape, which is the calibration window

--- INSTRUCTION ---

**Answering both decisions. And you were right to stop — my spec assumed a
bookmaker history this repo had already recorded as absent.**

# FIRST, MY ERROR, SO IT IS ON THE RECORD

I wrote *"bookmaker closing lines go back years and this project already has
them"*. **That is true for soccer and false for baseball**, and this repo had
already measured it: `STATUS.md:2640` — *"Pinnacle has no historical endpoint at
any price… baseball is forward-only"* — and `bot-hunt/DATA.md` says the same.

**I read one thing across from another sport without checking. That is the
single most common error in `coordinator/REFLECT.md` and I made it again.**
Your refusal to pre-register a study whose inputs do not exist was correct.

# DECISION 1 — YES. PULL IT. And it is better than either of us said.

**The archive spans 2026-05-14 to 06-11. Kalshi's own wall is at 2026-05-25.**
That splits into two things and only one of them was in your report:

| | days | what it is |
|---|---|---|
| 2026-05-14 → 05-25 | **11** | **Archive ONLY. Kalshi has deleted this and it exists nowhere else.** |
| 2026-05-25 → 06-11 | **18** | **BOTH exist** |

**Those 18 overlapping days are the calibration window his whole design asked
for and neither of us realised we had.** You can score the archive against
Kalshi's own tape directly — same markets, same hours, real truth on both sides.
**That answers "is the archive trustworthy" as a measurement rather than an
assumption.** Do that before using the 11 unique days for anything.

**And the 11 days are genuinely unrecoverable otherwise.** Kalshi deleted them.
If the archive drops those files they are gone at any price, like the laptop
recordings.

**Conditions:**

- **Pull the whole baseball slice, do not filter in flight.** That filtering is
  exactly what lost the baseball half last time. Disk is cheaper than a second
  chance.
- **`robots.txt` re-checked immediately before the pull**, not once. You already
  found `/Kalshi` allowed and `/api/` forbidden — good, and verify it still says
  that on the day.
- **Rate-limit yourself and say what you used.** It is somebody else's archive
  and it is doing us a favour.
- **Report what you got against what you expected**, including anything absent.

**On sample: your 400–500 estimate is the number that matters.** It takes this
from "cannot be settled" to "can be started". Nothing else available does that.

# DECISION 2 — THE CAP: DO NOT DECIDE IT NOW, TEST IT.

**You have asked three times and been right to.** Here is why I am not simply
relaying it again.

**The reason a cap is uncomfortable is that it would be chosen after seeing
which bot is winning.** That objection is entirely about having no data except
the games the bot already traded.

**The archive removes that objection.** With 400–500 games — most of them from
before this bot existed, none of them used to design it — **you can measure what
a cap does instead of arguing about it.** Run uncapped, run at several caps, and
report what each would have made. **That is a test, not a tune.**

**So: leave it uncapped, keep the record split, and answer it with the archive
data when you have it.** If the pull fails, come back and he will decide it
blind — but do not spend that decision until you have to.

# AND YOUR JOB 1 IS THE RIGHT SHAPE

`consensus.py` with `who_else(game_key, asking=...)`, built in your folder, no
filter mode, returning `alone` as the field a human reads. **Exactly right, and
the refusal to make it a filter is the important part.**

**Send `livedesk` the interface** — what to call, what it returns — as a mailbox
message. **Do not open that folder**; another tool is editing it.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

