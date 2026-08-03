# AUDIT DECISIONS LOG

Ambiguities resolved conservatively during the read-only audit. Newest last.

---

**AD-001 — Audit outputs are written to a new folder, not into the audited repos.**
The prompt says "commit after each output file" and "update PROGRESS.md". Two of the
audited projects already own files named `PROGRESS.md` and `DECISIONS.md`
(`C:\Users\vinig\kalshi markets\`). Overwriting or appending to them would violate the
read-only rule and would corrupt the very artifacts being audited. All audit output
therefore goes to `C:\Users\vinig\kalshi\audit\`. The audit's own `PROGRESS.md` and
`DECISIONS.md` live there and are distinct files from the project ones.

**AD-002 — No git commits made.**
`C:\Users\vinig\kalshi` (the audit output's parent) is not a git repo. Running `git init`
would create state in a live bot directory. The write-as-you-go requirement is satisfied
by writing each output file to disk as it is completed, so an interrupted run still
leaves usable output. No repository was created or modified.

**AD-003 — Chat exports are absent; all chat-only claims marked PENDING.**
`audit/pro_chats.json` and `audit/max_chats.json` do not exist anywhere on this machine.
Per the invoking override, Outputs 1–5 are built from project files, results files, logs
and git history alone. Claims that could only be sourced from a chat are labelled
`PENDING (chat export)` rather than `UNVERIFIED`, to distinguish "no artifact found" from
"no source consulted yet".

**AD-004 — Status assignment is strict and pessimistic.**
Where a claim has an artifact but the audit could not re-execute it (read-only rule: no
project code was run), the claim caps at `SUGGESTIVE` unless the artifact itself carries
the validation evidence (clustered CI, out-of-sample split, control results) in a form
that can be read directly from the output file. No claim is promoted on the strength of
prose in a report.

**AD-005 — `C:\Users\vinig\Vinex-OS`, `Documents\Codex\2026-07-*` session dirs and all
game/media folders treated as out of scope without being read.**
Directory names and top-level listings were used to classify them; no file contents were
opened. Two exceptions were opened and confirmed in scope:
`Documents\Codex\weather-market-bot` (Kalshi weather) and
`Downloads\DiscordChatExporter.win-x64` (the tool that produced the trading-server export).

**AD-006 — The Discord export on the Desktop is treated as in-scope evidence but is not
summarised as conversation.**
`OneDrive\Desktop\kalshi\RICH0FFTENN1S - TRADES - ...json` is a 1.5 MB export of a
trading server's calls channel. It is inventoried and counted, and its role as the
signal source is recorded, but its contents are not reproduced.

**AD-007 — Where two artifacts disagree, the later-dated artifact wins and the earlier
one is recorded as RETRACTED rather than deleted from the ledger.**
Several results in this project were corrected mid-session (see `LEDGER.md` retractions).
Both versions are kept in the ledger so that a future reader who remembers the earlier
number can find it and see that it was withdrawn.

**AD-008 — "No artifact found" is reported as such, not inferred to mean "never done".**
Several projects have no git history (`kalshi`, `tennis copy trade`,
`OneDrive\Desktop\kalshi`) and several referenced databases (`tape_scan.db`, `best.db`)
are not present on this machine. Claims resting on them are `UNVERIFIED` with the missing
artifact named, so the gap is closable by producing the file rather than by re-running the
analysis.
