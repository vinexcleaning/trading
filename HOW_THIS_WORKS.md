# HOW_THIS_WORKS.md

The operating manual. Short on purpose.

## Four repos, four separate things

| Repo | Visibility | What lives there |
|---|---|---|
| **trading** | **public** | All prediction-market and signal-extraction work. |
| **nexus** | private | The life/organisation system. ChatGPT-led. |
| **Vinex-OS** | private | The cleaning business. |
| **weather-market-bot** | private | Older trading work. |

**Never mix them.** Not files, not commits, not context. If something belongs in
another repo, it goes in that repo — do not park it here "for now".

## New ideas go in INBOX.md first

Always. Before deciding where an idea belongs, before judging it, before
starting on it. See [INBOX.md](INBOX.md). Routing is a separate pass.

## STATUS.md is the shared brain

Every session:

1. **Starts** with `git pull` and reading [STATUS.md](STATUS.md).
2. **Ends** by merging its own changes into STATUS.md — merging, not
   overwriting — and pushing.

STATUS.md is additive. You add a dated section and update the thread rows your
work actually touched. You do not rewrite someone else's section.

## One session per folder

Sessions never edit each other's directories. If your work needs a change in
another session's folder, write it down and hand it over — do not reach in.

Stage explicit paths when committing. Never `git add -A`: two sessions have
already cross-contaminated commits that way.

## Every session ends with a HANDOFF

Write `HANDOFF.md` in your own folder, then push. The handoff is the detail;
STATUS.md is the summary that points at it.

## Push or it did not happen

The coordinating chat reads this repo **directly, over the public web**. It
cannot see your disk. Work that is committed but not pushed is invisible to it,
and so is work that is only in a chat log.

Because the repo is public: `data/`, `reports/`, `KNOWLEDGE.md`, `.env`, keys
and anything naming real people stay gitignored. Check before you stage.

## Machines

- **Desktop `C:\Users\vinig` — primary.** All real work happens here.
- **Laptop — recording box only.** It runs the recorders and nothing else.
