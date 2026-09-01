"""
record_data.py — the data collector. Trades nothing, ever.

Joins Kalshi prices to Sofascore scores for EVERY live tennis match, once
every interval, and appends one row per market to a JSONL file. This is the
dataset that does not exist anywhere: price and score, aligned, timestamped,
including the matches the trading bot would never enter.

WHY IT EXISTS
    Kalshi's candlestick history has prices but no scores. Sofascore has
    historical scores but only set DURATIONS, so reconstructing when a set
    ended is accurate to maybe ±10 minutes — fine for coarse questions, far
    too loose to test an entry rule. Recording it live solves that exactly:
    every row is stamped when we saw it.

    Three nights of this is a few hundred matches, which is enough to ask
    the questions the 4-week price-only backtest could not answer:
      * does a set won 6-3 behave differently from one won 7-6?
      * is a wide-margin pre-match favourite losing set 1 a real edge?
      * does entering at the start of a service game beat entering mid-game?

SAFETY
    This script imports no order-placing code path and holds a read-only
    Kalshi client. It cannot buy or sell.

USE
    python record_data.py                       # 60s interval -> tennis_data.jsonl
    python record_data.py --interval 120 --out mynight.jsonl
    python record_data.py --summary tennis_data.jsonl    # what did I collect?
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Optional

from autoscan import _name_matches, subject_player
from kalshi_client import KalshiClient
from sofascore_feed import SofaScoreClient

# 10s floor, lowered from 30 on 28 Jul. A break of serve can move these
# markets 20c, and at 30s the reaction was already over before the next
# snapshot. The floor exists because SofaScore is a free endpoint that has
# blocked scrapers before — going much below 10s risks losing the feed
# entirely, which costs more than the extra resolution is worth.
#
# ⚠ THIS DELIBERATELY CONTRADICTS `sofascore_feed.POLL_MIN_SEC = 60`, which
# says "floor; do not lower". Noted 2026-09-01 during the assumption audit;
# BOTH numbers are intentional and neither was changed:
#   * the RECORDER (this file) needs fine resolution, because measuring how
#     fast the market reacts is the entire question it exists to answer, and
#     a 60s sample cannot see a reaction that finishes in 20s;
#   * the LIVE FEED module is polled by the trading bot, which needs the feed
#     to keep working far more than it needs another data point.
# If the feed ever gets blocked, this is the first thing to look at — but do
# not "fix" one of these to match the other without knowing which caller you
# are looking at. They answer different questions.
MIN_INTERVAL = 10


LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         ".recorder.lock")


def _utf8() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _pid_alive(pid: int) -> bool:
    """Is that process still running? Windows-safe, no extra dependencies."""
    try:
        out = os.popen(f'tasklist /FI "PID eq {pid}" /NH').read()
        return str(pid) in out
    except Exception:
        return False


def claim_lock() -> bool:
    """Refuse to start if another recorder is already running.

    Launching the bat file twice used to start a second, third, fourth
    recorder all appending to the same file — duplicate rows, and no way to
    tell from the console which one you were looking at. A stale lock from a
    crashed run is detected and cleared rather than blocking forever.
    """
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                old = int((f.read() or "0").strip())
        except (OSError, ValueError):
            old = 0
        if old and old != os.getpid() and _pid_alive(old):
            print(f"A recorder is ALREADY RUNNING (pid {old}).")
            print("Only one may run at a time or you get duplicate rows.")
            print(f"Stop that one first, or delete {LOCK_FILE} if it crashed.")
            return False
        print("(clearing a stale lock from a recorder that didn't shut down)")
    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
    except OSError:
        pass          # a lock we can't write is not worth refusing to run over
    return True


def release_lock() -> None:
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE) as f:
                if (f.read() or "").strip() == str(os.getpid()):
                    os.remove(LOCK_FILE)
    except OSError:
        pass


def collect_set_markets(kc: KalshiClient) -> list[dict]:
    """Per-set markets ('will X win set 2'). Recorded only — never traded.
    Match-winner being efficiently priced tells us nothing about these."""
    now = time.time()
    try:
        ms = kc.set_markets()
    except Exception:
        return []
    return [{
        "ts": round(now, 1), "row_type": "set_market",
        "ticker": m.ticker, "title": m.title,
        "bid": m.yes_bid, "ask": m.yes_ask, "spread": m.yes_ask - m.yes_bid,
        "last_price": m.last_price, "volume": m.volume,
        "open_interest": m.open_interest,
        "series": m.ticker.split("-")[0],
    } for m in ms if m.is_trading]


def collect_once(kc: KalshiClient, live: SofaScoreClient,
                 opens: dict, prev_price: Optional[dict] = None) -> list[dict]:
    """One snapshot: every Kalshi tennis market that maps to a live match."""
    now = time.time()
    prev_price = prev_price if prev_price is not None else {}
    try:
        feed = live.raw(force=True)
    except Exception:
        return []
    singles = [f for f in feed if f.get("matchType") == "singles"]
    if not singles:
        return []

    try:
        markets = kc.tennis_markets()
    except Exception:
        return []

    rows = []
    for m in markets:
        if not m.is_trading:
            continue
        subject = subject_player(m.title)
        if not subject:
            continue

        pair = side = None
        for f in singles:
            if _name_matches(subject, f["homePlayerName"]):
                pair, side = f, "home"
                break
            if _name_matches(subject, f["awayPlayerName"]):
                pair, side = f, "away"
                break
        if pair is None:
            continue

        other = "away" if side == "home" else "home"
        sc = pair.get("score") or {}
        pts = pair.get("points") or {}
        games = pair.get("games") or {}
        last = str(pair.get("lastPeriod") or "")
        cur = games.get(last.replace("period", "set"), {}) if last else {}

        # Opening price = the pre-match favourite, cached per ticker.
        if m.ticker not in opens:
            try:
                opens[m.ticker] = kc.opening_price(m.ticker)
            except Exception:
                opens[m.ticker] = None
        op = opens[m.ticker]

        rows.append({
            "ts": round(now, 1),
            "ticker": m.ticker,
            "player": subject,
            "match": f"{pair['homePlayerName']} vs {pair['awayPlayerName']}",
            "tournament": pair.get("tournament", ""),
            # --- market ---
            "bid": m.yes_bid, "ask": m.yes_ask, "spread": m.yes_ask - m.yes_bid,
            "last_price": m.last_price, "volume": m.volume,
            "open_interest": m.open_interest,
            "open_price": op,
            "was_favorite": (None if op is None else op > 50),
            # --- score ---
            "sets_won": sc.get(side), "sets_lost": sc.get(other),
            "games_won": cur.get(side), "games_lost": cur.get(other),
            "point": pts.get(side), "opp_point": pts.get(other),
            "serving": (None if pair.get("serving") is None
                        else pair["serving"] == side),
            "set_number": (int(last.replace("period", ""))
                           if last.startswith("period") else None),
            "all_sets": games,          # full per-set games, for set-quality work
            "status": pair.get("status", ""),
            "status_type": pair.get("statusType", ""),
            "score_change_ts": pair.get("changeTimestamp"),
            "event_id": pair.get("eventId"),
            # --- strength of field / league tier ---
            "rank": pair.get("homeRank") if side == "home" else pair.get("awayRank"),
            "opp_rank": pair.get("awayRank") if side == "home" else pair.get("homeRank"),
            "rank_gap": (
                None if (pair.get("homeRank") is None or pair.get("awayRank") is None)
                else (pair["awayRank"] - pair["homeRank"]) * (1 if side == "home" else -1)
            ),                                   # positive = this player ranked better
            "category": pair.get("category"),    # ATP / WTA / Challenger / ITF...
            "gender": pair.get("gender"),
            "unique_tournament": pair.get("uniqueTournament"),
            "series": m.ticker.split("-")[0],    # Kalshi's own tier label
            # --- price reaction to the last score change ---
            # The mispricing question is "how far does price move AFTER a
            # point/game/set lands, and does it overshoot". That needs the
            # price now, the price just before the change, and how long ago
            # the change was. Without these you can only see the level, never
            # the reaction.
            "secs_since_score_change": (
                None if not pair.get("changeTimestamp")
                else round(now - float(pair["changeTimestamp"]), 1)
            ),
            "bid_before_change": prev_price.get(m.ticker, (None, None))[0],
            "ask_before_change": prev_price.get(m.ticker, (None, None))[1],
        })
    return rows


def dedupe(path: str) -> None:
    """Drop duplicate rows left by more than one recorder running at once.

    Two recorders a few seconds apart produce near-identical rows, so the key
    is (ticker, score state, price) rather than the exact timestamp — that
    collapses the copies while keeping every real change.
    """
    if not os.path.exists(path):
        print(f"{path} not found")
        return
    seen, kept, dropped = set(), [], 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            key = (r.get("ticker"), r.get("sets_won"), r.get("sets_lost"),
                   r.get("games_won"), r.get("games_lost"), r.get("point"),
                   r.get("opp_point"), r.get("bid"), r.get("ask"))
            if key in seen:
                dropped += 1
                continue
            seen.add(key)
            kept.append(r)
    backup = path + ".bak"
    os.replace(path, backup)
    with open(path, "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"kept {len(kept):,} rows, dropped {dropped:,} duplicates")
    print(f"original saved as {backup}")


def summarize(path: str) -> None:
    if not os.path.exists(path):
        print(f"{path} not found")
        return
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    if not rows:
        print("file is empty")
        return
    tickers = {r["ticker"] for r in rows}
    matches = {r["match"] for r in rows}
    tours = {}
    for r in rows:
        tours[r.get("tournament", "?")] = tours.get(r.get("tournament", "?"), 0) + 1
    span = (max(r["ts"] for r in rows) - min(r["ts"] for r in rows)) / 3600
    served = sum(1 for r in rows if r.get("serving") is not None)
    withset = sum(1 for r in rows if (r.get("sets_won") or 0) + (r.get("sets_lost") or 0) > 0)
    print(f"{len(rows):,} rows | {len(tickers)} markets | {len(matches)} matches "
          f"| {span:.1f} h")
    print(f"  rows with a resolved set : {withset:,} ({withset/len(rows)*100:.0f}%)")
    print(f"  rows with server known   : {served:,} ({served/len(rows)*100:.0f}%)")
    print("  tournaments:")
    for t, n in sorted(tours.items(), key=lambda x: -x[1])[:15]:
        print(f"    {n:7,}  {t[:50]}")


def resolve_finished(kc: KalshiClient, pending: dict, last_row: dict) -> list[dict]:
    """Emit one terminal row per market that has left the live feed and has
    since settled on Kalshi.

    Without this the dataset cannot score itself: every row was written while
    `status_type == 'inprogress'`, so nothing recorded WHO WON, and no strategy
    could be backtested without re-fetching 300+ outcomes by hand afterwards.

    Settlement is not instant, so a market that just vanished is kept in
    `pending` and retried each cycle until Kalshi reports a result.
    """
    done = []
    for ticker in list(pending):
        try:
            m = kc._get(f"/markets/{ticker}").get("market", {})
        except Exception:
            continue                     # try again next cycle
        result = m.get("result")
        if result not in ("yes", "no"):
            # give up after an hour of asking; the match may be postponed
            if time.time() - pending[ticker] > 3600:
                pending.pop(ticker, None)
            continue
        prev = last_row.get(ticker, {})
        done.append({
            "ts": round(time.time(), 1),
            "ticker": ticker,
            "player": prev.get("player"),
            "match": prev.get("match"),
            "tournament": prev.get("tournament"),
            "row_type": "final",                  # <- the terminal row
            "result": result,                     # 'yes' = this player won
            "player_won": result == "yes",
            "settle_status": m.get("status"),
            # last live state seen, so the outcome sits next to the final score
            "last_bid": prev.get("bid"), "last_ask": prev.get("ask"),
            "final_sets_won": prev.get("sets_won"),
            "final_sets_lost": prev.get("sets_lost"),
            "final_all_sets": prev.get("all_sets"),
            "open_price": prev.get("open_price"),
            "was_favorite": prev.get("was_favorite"),
            "event_id": prev.get("event_id"),
        })
        pending.pop(ticker, None)
    return done


def main() -> None:
    _utf8()
    ap = argparse.ArgumentParser(description="Record price+score. Trades nothing.")
    ap.add_argument("--interval", type=int, default=20,
                    help=f"seconds between snapshots (min {MIN_INTERVAL})")
    ap.add_argument("--out", default="tennis_data.jsonl")
    ap.add_argument("--summary", metavar="FILE", help="summarise a file and exit")
    ap.add_argument("--dedupe", metavar="FILE",
                    help="remove duplicate rows left by overlapping recorders")
    ap.add_argument("--set-markets-every", type=int, default=4, metavar="N",
                    help="also record per-set markets every Nth cycle "
                         "(0 = off). These are recorded, never traded.")
    a = ap.parse_args()

    if a.summary:
        summarize(a.summary)
        return
    if a.dedupe:
        dedupe(a.dedupe)
        return

    if not claim_lock():
        sys.exit(1)

    interval = max(a.interval, MIN_INTERVAL)
    kc = KalshiClient(demo=False, read_only=True)   # cannot place orders
    live = SofaScoreClient(cache_sec=5)
    opens: dict[str, Optional[int]] = {}

    print(f"recording every {interval}s -> {a.out}")
    print("read-only: this process cannot place an order.  ctrl-c to stop\n")
    total = 0
    finals = 0
    loop_n = 0
    set_every = a.set_markets_every      # 0 disables set-market capture
    prev_price: dict[str, tuple] = {}
    live_now: set[str] = set()          # tickers seen in the previous cycle
    pending: dict[str, float] = {}      # left the feed, awaiting settlement
    last_row: dict[str, dict] = {}      # last live row per ticker
    try:
        while True:
            t0 = time.time()
            rows = collect_once(kc, live, opens, prev_price)
            # remember this tick's quotes so the NEXT tick can report what the
            # price was immediately before a score change landed
            for r in rows:
                prev_price[r["ticker"]] = (r.get("bid"), r.get("ask"))

            set_rows = collect_set_markets(kc) if set_every and \
                (loop_n % set_every == 0) else []
            loop_n += 1

            seen = {r["ticker"] for r in rows}
            for r in rows:
                last_row[r["ticker"]] = r
            # anything that was live last cycle and isn't now has ended
            for gone in live_now - seen:
                pending.setdefault(gone, time.time())
            live_now = seen

            done = resolve_finished(kc, pending, last_row) if pending else []
            finals += len(done)

            if rows or done or set_rows:
                with open(a.out, "a", encoding="utf-8") as f:
                    for r in rows + done + set_rows:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                total += len(rows) + len(done) + len(set_rows)
            matches = len({r["match"] for r in rows})
            extra = f"  +{len(done)} final" if done else ""
            sx = f"  +{len(set_rows)} set-mkt" if set_rows else ""
            print(f"  {time.strftime('%H:%M:%S')}  {len(rows):3d} rows "
                  f"({matches} matches){extra}{sx}  total {total:,} "
                  f"[{finals} outcomes, {len(pending)} awaiting]", flush=True)
            time.sleep(max(1.0, interval - (time.time() - t0)))
    except KeyboardInterrupt:
        print(f"\nstopped. {total:,} rows in {a.out}")
        print("run with --summary to see what you collected")
    finally:
        release_lock()


if __name__ == "__main__":
    main()
