# WHAT_IS_LEFT.md

Written 2026-08-02. Everything this session found but did not finish, and
everything it deliberately did not attempt. Ordered by information gain per
hour within each group.

---

## Blocked on wall-clock time only (running now, will complete on their own)

| Item | State at 07:21 UTC | Completes |
|---|---|---|
| pmxt L2 mirror | 300/662 files, 33.2 GB, **1 file failed** | ~1 h; re-run the script to pick up the failure (it is resumable and content-validates on skip) |
| Kalshi 24 h trade tape | 3.83 M trades, back to 2026-08-01 21:45 UTC | ~08:40 UTC |
| Trade backfill for the pmxt window | 2026-05-25 in progress | **decays 1 day/day — see below** |
| Broad depth recorder | 9 cycles, 231 markets, 85 families | runs until stopped |

---

## ⏳ THE DECAYING ITEM — highest priority of anything on this page

> # ⚠⚠ IT IS NOT DECAYING. RETRACTED 2026-08-06. Read this box first.
>
> **The boundary is a FIXED CALENDAR DATE, not a rolling window, and the
> 2026-08-19 deadline below does not exist.** Three bisections, four days apart,
> on `bot-hunt/src/retention_rebisect.py` → `reports/retention_rebisect.json`:
>
> | measured | boundary | its age that day |
> |---|---|---|
> | 2026-08-02 (this file) | 2026-05-25 | **69 days** |
> | 2026-08-04 (`bot-hunt` BH009) | 2026-05-25 | **71 days** |
> | **2026-08-06** | **2026-05-25** | **73 days** |
>
> **The boundary never moved. The "69-day window" was the age of a fixed date on
> the day it was measured.** A genuinely rolling 69-day window would today start
> at 2026-05-29; the tape returns trades at **73 days** and nothing at 74, and
> **6 of 8 unrelated families report exactly `2026-05-25`** as their earliest
> settled market — listing and tape agreeing on one date.
>
> **What this means practically: nothing is expiring one day per day, and no work
> needs to be rushed to beat 2026-08-19.** The 11 days 05-14 → 05-24 are still
> gone — that part stands.
>
> **What it does NOT mean.** A fixed boundary is not a promise. The mechanism is
> unknown and looks like a data-migration cutover; such a boundary can disappear
> in one step rather than sliding. **This removes a deadline. It does not create
> a guarantee**, and a mirror of anything genuinely irreplaceable is still worth
> having.
>
> Nothing below is deleted — deleting a wrong number is how someone re-derives it.

The Kalshi trade tape retains **exactly 69 days** (measured by bisection:
trades present at 2026-05-25, zero at 2026-05-24). The window rolls forward
daily.

The pmxt order-book archive covers **2026-05-14T14 → 2026-06-11T03**. Therefore:

- **2026-05-14 → 05-24: the trades are already gone.** 11 days of mirrored
  order book with no matching tape. Unrecoverable at any price.
- **2026-05-25 → 06-11: still reachable, losing one day per day.** The whole
  overlap is gone by **2026-08-19**.

Depth without trades cannot answer the question the pmxt mirror exists to
answer — *what would actually have filled*. A backfill is running oldest-first.
**If it is interrupted, restart it before doing anything else on this list.**

```bash
"C:\Users\gianf\AppData\Local\Programs\Python\Python312\python.exe" -u market-selection/src/backfill_tape_pmxt_window.py
```

---

## Blocked on data or access

| Item | Blocker | What would unblock it |
|---|---|---|
| Exhaustive search for a Sackmann `tennis_atp` mirror | GitHub **code** search needs an authenticated token; only 23 of 660 candidate repos were checked, at 4 paths each | a GitHub PAT, then one code-search query |
| Polymarket below the top 2,100 events | gamma returns **HTTP 422 at offset 2100** and caps `limit` at 100 | crawl a different axis — per tag_slug, or by date window |
| FBref, HLTV | **403 Cloudflare** interstitial | a browser-based fetch; both are the canonical free source for soccer detail and CS2 respectively |
| DataGolf strokes-gained | **403**, paid | money. Free golf data is scores only, which is why golf ranks low on D despite the highest dollar volume on the exchange |
| stats.nba.com | connection reset even with browser headers and referer | session cookies |
| FRED, the-odds-api | **400 / 401**, need keys | free-tier registration |
| 538 approval CSV | 200 and 310 KB but parses to **0 columns** | inspect the raw bytes; may be a delimiter or encoding issue, not a dead source |

---

## Not run for time

1. **Cross-venue on politics.** MLB was swept (66 sides, 0 of 66 net positive).
   Politics is the family where the two venues most plausibly disagree —
   Polymarket's politics book is both larger and tighter (median 1.1¢ on
   $13.7 M/24 h) than Kalshi's. The MLB null does not transfer.
2. **Cross-venue persistence.** The gap *distribution* is measured; its
   *persistence* is not. A one-snapshot measurement cannot distinguish a gap
   that stands for hours from one that closes in seconds. Needs the recorder
   pointed at matched pairs on both venues.
3. **Reconstructing a book from the pmxt deltas.** The mirror is 99.73% deltas;
   nothing has yet replayed snapshot+deltas into a point-in-time book. Until
   that exists the archive is potential, not capability. This is the single
   biggest piece of unbuilt machinery.
4. **Depth coverage for families the recorder does not sample.** It tracks the
   top 85 by trades/day. Families below that are killed by omission rather than
   by measurement, and `killed.md` says so explicitly for each.
5. **`fee_multiplier = 0` verification.** 11 series claim it, KXBTCY has real
   volume (157 k/24 h). Never checked against an actual fill. This project has
   been burned twice by trusting a field's name (W016 `enable_order_book`, the
   legacy price fields). Treat as a hypothesis.
6. **NPB/KBO scrapers.** Both official sites return 200 and both need scraping;
   `armstjc/Nippon-Baseball-Data-Repository` is live and pushed 2026-07-28 but
   was not evaluated for schema or coverage.
7. **Polymarket depth over time.** 208 markets sampled once. No uptime series.

---

## Not attempted, deliberately

- **Any strategy test.** Out of scope by instruction; this session selects
  markets.
- **Any re-run of a prior study.** Out of scope by instruction.
- **Anything involving money, orders, or authenticated endpoints.** Every call
  made this session was public, unauthenticated, read-only.
- **Touching PIDs 17892 / 24756.** STATUS.md forbids it; both verified alive
  and left alone.

---

## Carried forward from STATUS.md, still open, NOT addressed this session

These were already open before this session and remain so. They are listed
because a reader of this file should not conclude they were handled.

| Item | Why it still matters |
|---|---|
| **v3 backtest dedupe field** (CH057) | ~100× the evidence base of anything else in the archive, never verified. One grep on the desktop machine. |
| **Desktop recorder `None` bug** | This session **confirmed the root cause is live**: all 8 legacy price fields are null on 100% of sampled markets. If `kalshi_client.py` / `record_data.py` read the old names, every book recorded on that machine is worthless. **This is now more urgent than it was, not less.** |
| **Live bot position-sizing blowout** (CH044) | 64 contracts against an intended 9, `max_daily_loss_pct = 0`. Top standing financial risk. Untouched. |
| Label coverage for tennis (Apify quota) | Unchanged. |
