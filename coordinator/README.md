# coordinator/

**Read [COORDINATOR.md](COORDINATOR.md) first** — the design, and explicitly
what this cannot do.

**One command:**

```
coordinator\start.bat
```

It only reads. No network call, no credential, no ability to place a trade —
`tests/test_no_money_no_network.py` fails the moment that stops being true.

| I want to… | Command |
|---|---|
| See the state of everything | `coordinator\start.bat` |
| Write my section of the brief | `py -3 coordinator\brief.py write <slug> --file mysection.md` |
| Send an instruction to a session | `py -3 coordinator\mail.py send <slug> --subject "…" --file body.md` |
| See unanswered instructions | `py -3 coordinator\mail.py open` |
| Read my mail | `py -3 coordinator\mail.py show <slug>` |
| Get the address to paste into the coordinating chat | `py -3 coordinator\brief.py url` |

**After writing your section, commit `BRIEF.md` *and* `briefs/`, then end your
message with the address `brief.py url` prints.** A page that is not pushed
gives the user an address that returns nothing, and the coordinating chat
silently keeps reading whatever it last had. `start.bat` shouts about this
first if it happens.

**Never hand out the repo-root `BRIEF.md` address** — it is cached frozen for
that reader and serves an old page that looks current. Tested, not assumed.

Slugs: `tennis` · `mlb` · `devig` · `signal` · `coordinator`.

To reply to a message, **edit the message file**: change `Status: OPEN` to
`Status: DONE` or `BLOCKED` and type under the reply line. No script.
