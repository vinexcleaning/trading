# briefs/

**Every version of [BRIEF.md](../BRIEF.md), each at its own permanent path.**

Do not edit anything in here. These files are written by
`coordinator/brief.py` and are **never rewritten once created**.

| File | What it is |
|---|---|
| `BRIEF-YYYY-MM-DD-NN.md` | One generation. Immutable. |
| `BRIEF-YYYY-MM-DD.md` | That day's final state. Rewritten during the day. |

## Why this folder exists

The coordinating chat reads this repo over the public web, and its fetcher
**caches by path and discards query strings** — a request for `?v=A` returns the
body cached under `?v=B`. Measured on 2026-08-07, not assumed. So no
cache-busting URL can work, and `BRIEF.md` freezes exactly the way `STATUS.md`
did.

The way round it is not to defeat the cache but to route around it. **Each page
names the path of the next page.** A reader starts anywhere — even at a copy
frozen weeks ago — and follows next-links until one returns 404. The last page
that loaded is the newest.

Entry point, which never changes:

```
https://raw.githubusercontent.com/vinexcleaning/trading/main/BRIEF.md
```

## The thing that breaks it

**A page here that is not pushed.** The previous page tells a reader to fetch
it, the fetch returns nothing, and the reader concludes it already has the
newest — reading stale content while believing it is current.

`coordinator\start.bat` reports any unpushed page as the first item in its
digest, and `brief.py check` fails on any gap in the numbering. If you see
either, push.
