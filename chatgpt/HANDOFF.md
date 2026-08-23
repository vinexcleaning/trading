# HANDOFF — chatgpt

<!-- COORDINATOR-STATE
doing: registered but not yet exercised - waiting on the round-trip readiness test in mailbox 001
left: read the newest brief, summarise the objective, file one message back to coordinator
needs: no
state: BLOCKED
updated: 2026-08-22T21:40
-->

**Registered 2026-08-22.** Nothing has run yet.

`state: BLOCKED` is honest rather than pessimistic: this participant cannot act
until a human runs it, because there is no automated ChatGPT client wired in.
**That is the current state of the bridge, and it is what mailbox 001 exists to
change.**

## Where the protocol is

[`coordinator/AGENT_PROTOCOL.md`](../coordinator/AGENT_PROTOCOL.md). Read it in
full before writing anything.

## What has been built for this participant

- a registry row in `coordinator/chats.json`, carrying `may_write`,
  `read_only`, `never_touch` and `"execution": false`
- a mailbox at `coordinator/mailbox/chatgpt/`
- `mail.py --from chatgpt`, so a message is attributable in the file itself
- a workstream entry in `coordinator/scan.py`, so it appears in the
  where-is-everything table
