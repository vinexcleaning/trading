# chatgpt/

**The working folder for the `chatgpt` participant.** Registered in
[`coordinator/chats.json`](../coordinator/chats.json) on 2026-08-22.

**Read [`coordinator/AGENT_PROTOCOL.md`](../coordinator/AGENT_PROTOCOL.md)
before writing anything.** It is the contract, written so an agent that cannot
rely on Claude Code's `CLAUDE.md` auto-loading can follow it from a standing
start.

## What this participant is for

Architecture · strategy · plan review · reading shared state · reading briefs
and handoffs · filing architecture and review messages · proposing changes ·
receiving execution reports.

## What it is NOT for

**`"execution": false` in its registry row, and that is the whole point.** It
does not run the trading system, place or modify any order, hold a credential,
or write into another participant's folder. **Claude's dictator chat remains the
execution dispatcher.**

`livedesk/` is off limits entirely — it sends real orders with real money.

## Mailbox

`coordinator/mailbox/chatgpt/`. Reply inside the message you were given; set
`Status:` to `DONE` or `BLOCKED`.
