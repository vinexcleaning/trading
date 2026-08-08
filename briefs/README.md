# briefs/

**Every version of the brief, each at its own permanent address.**

Do not edit anything in here. These files are written by
`coordinator/brief.py` and are **never rewritten once created**.

| File | What it is |
|---|---|
| `BRIEF-YYYY-MM-DD-NN.md` | One version. Immutable. |
| `BRIEF-YYYY-MM-DD.md` | That day's final state. Rewritten during the day. |

## Why this folder exists

The coordinating chat reads this repo over the public web, and three things
about it were **measured, not assumed**:

1. **It caches by path and discards query strings.** A request for `?v=A`
   returned the body cached under `?v=B`. No cache-busting address can work.
2. **The repo-root `BRIEF.md` is frozen for it forever.** A connection test put
   a marker word in the page; the chat found it here and **not** there.
   **`BRIEF.md` is never the address you hand out.**
3. **It will not follow an address printed inside a page.** It can only open one
   the user pastes.

So the answer is not a clever address — it is an address that **cannot go
stale**. Each page here is written once and never touched again, so what it says
is exactly what was true at the timestamp on it.

## How the address reaches the chat

**One paste per page. That is the floor, and it is accepted.**

Every session ends every message with a `BRIEF —` line carrying the current
address, so the user copies the last line rather than going to look for it.
To print it yourself:

```
py -3 coordinator\brief.py url
```

## The thing that breaks it

**A page here that is not pushed.** The user pastes its address, the fetch
returns nothing, and the chat silently keeps reading whatever it last had.

`coordinator\start.bat` reports any unpushed page as the first item in its
digest, and `brief.py check` fails on any gap in the numbering. If you see
either, push.
