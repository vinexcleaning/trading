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
| Get the URL for the coordinating chat | `py -3 coordinator\brief.py chain` |

**After writing your section, commit `BRIEF.md` *and* `briefs/`.** A brief page
that is not pushed makes the next link 404, and a reader then believes a stale
page is the newest. `start.bat` shouts about this first if it happens.

Slugs: `tennis` · `mlb` · `devig` · `signal` · `coordinator`.

To reply to a message, **edit the message file**: change `Status: OPEN` to
`Status: DONE` or `BLOCKED` and type under the reply line. No script.
