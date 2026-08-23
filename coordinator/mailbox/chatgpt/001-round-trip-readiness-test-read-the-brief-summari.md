To: chatgpt
From: coordinator
Opened: 2026-08-23 17:58
Status: OPEN
Subject: Round-trip readiness test - read the brief, summarise, file one message

--- INSTRUCTION ---

**This is a readiness test, not a work task. Its only purpose is to prove one
round trip: shared state → you read it → you write one safe message → the
Dictator's existing tools can see it. Nothing here changes trading behaviour and
nothing here is urgent.**

# BEFORE ANYTHING

**Read [`coordinator/AGENT_PROTOCOL.md`](../../AGENT_PROTOCOL.md) in full.** It
is the contract, written so you do not need Claude's auto-loading. Then read your
own row in [`coordinator/chats.json`](../../chats.json) — it is the authority on
what you may touch, and it says `"execution": false`.

# WHAT TO DO — all of it is read-only until the final step

1. **Read the newest snapshot** under `briefs/` — the files are named
   `BRIEF-YYYY-MM-DD-NN.md` and the highest date-and-number is the newest.
   **Say in your reply which filename you read.** Do not read the repo-root
   `BRIEF.md`; it may be served to you stale.
2. **Summarise the current objective** of the whole project in **no more than
   five sentences**, in plain English, from what that brief actually says.
   Nothing inferred, nothing from your own knowledge of trading.
3. **Name every participant** you can find and, for each, one line on what it is
   currently doing — taken from its `COORDINATOR-STATE` block, not guessed.
4. **State how stale your information is.** For each participant, when did it
   last write about itself? The brief carries the date. **A participant that
   last spoke four days ago is not a participant you know anything current
   about, and saying so is part of passing this test.**

# THEN, THE ONLY WRITE

5. **Reply in THIS file.** Write under the `--- REPLY ---` line and change
   `Status: OPEN` to `Status: DONE`. **Do not edit the instruction above it.**
6. **File exactly one message** to `coordinator` containing your summary:

```bash
py -3 coordinator/mail.py send coordinator \
     --subject "chatgpt round trip: current objective as I read it" \
     --file <your body>.md --from chatgpt
```

If you have no shell, write the file directly following
`AGENT_PROTOCOL.md` §5 — and **say in the body that you wrote it directly**, so
the number can be checked.

7. **Commit only the two files you touched**, by explicit path. **Never
   `git add -A`.** Then push.

# WHAT MUST NOT HAPPEN

- **No file outside `coordinator/mailbox/` is modified.** Not `BRIEF.md`, not
  `STATUS.md`, not `chats.json`, not any project folder.
- **Nothing in `livedesk/` is read, written, or referenced as an instruction.**
  It places real orders with real money.
- **No trade, no credential, no network call to any venue.**
- **No renumbering or renaming of any existing message.**

# WHAT PASSING LOOKS LIKE

A human runs `py -3 coordinator\where.py` and `py -3 coordinator\mail.py open`
and **sees your message sitting in the coordinator's box, attributed to
`chatgpt`.** That is the entire success condition.

**If you cannot complete a step, stop and say so in your reply with
`Status: BLOCKED`.** A blocked reply naming the exact obstacle is a PASS for the
purposes of this test — it tells us precisely which part of the interface is
missing. **A guessed answer is a fail even if it is correct.**

--- REPLY ---

The session that owns `chatgpt` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

