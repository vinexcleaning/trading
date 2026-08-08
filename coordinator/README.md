# coordinator/

**Read [COORDINATOR.md](COORDINATOR.md) first** — the design, and explicitly
what this cannot do. Sections 3 and 3b are the honest half.

**One command:**

```
coordinator\start.bat
```

It prints, in this order: **where is everything at** (one table — which chat,
what it is doing now, what is left, is its background test alive, does it need
you), then what needs you and exactly what to do, then every background test,
then anything git and the filesystem flag, then the brief and the address to
paste out, then unanswered instructions.

It only reads. No network call, no credential, no ability to place a trade, and
it never starts or stops anything — `tests/test_no_money_no_network.py` fails
the moment that stops being true.

## You do not type any of this

Open a Claude Code session in the repo and say what you want in plain English.

| Say | You get |
|---|---|
| *"where is everything at"* or *"run the coordinator"* | The table, and what needs you |
| *"is the baseball test still running"* | ALIVE / STALE / FINISHED, plus the restart command if it died |
| *"tell the tennis chat to stop dating the briefs"* | A filed message that chat reads when it next starts |
| *"new idea: test de-vig against a retail book"* | A ready-to-paste prompt for a fresh window |

## The commands underneath, for a session that needs them

| I want to… | Command |
|---|---|
| See the state of everything | `coordinator\start.bat` |
| Just the where-is-everything table | `py -3 coordinator\where.py` |
| Just the background tests | `py -3 coordinator\runners.py` |
| Turn an idea into a prompt for a new session | `py -3 coordinator\newprompt.py --idea "…"` |
| Write my section of the brief | `py -3 coordinator\brief.py write <slug> --file mysection.md` |
| Send an instruction to a session | `py -3 coordinator\mail.py send <slug> --subject "…" --file body.md` |
| See unanswered instructions | `py -3 coordinator\mail.py open` |
| Read my mail | `py -3 coordinator\mail.py show <slug>` |
| Get the address to paste into the coordinating chat | `py -3 coordinator\brief.py url` |

## If you are a session being reported on: declare your state

Put this anywhere in your own `HANDOFF.md`, or in your `BRIEF.md` section. It is
an HTML comment, so it is invisible in rendered Markdown and costs the page
nothing.

```
<!-- COORDINATOR-STATE
doing: one line, present tense, what you are working on
left: one line, what still has to happen
needs: no
-->
```

`needs:` is `no`, or `yes - <the question, in one line>` — that line is printed
to the user verbatim under "what needs you".

**Without it, the two middle columns are guessed** out of your `HANDOFF.md` and
marked with a `~`. The guesses are mediocre by design, and the table says how
many of them there are.

## Two things that are easy to get wrong

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

## ALIVE does not mean working

`runners.py` reports **ALIVE** when a job's log file changed recently. That is
all it means. A runner ticking every minute while writing nonsense reads ALIVE;
nothing here checks that any number coming out of it is correct.

A background test that is not listed in `runners.json` is **not watched**. Every
run also prints log files it found on disk that nobody registered, so an
omission is visible — but visible is not the same as covered.
