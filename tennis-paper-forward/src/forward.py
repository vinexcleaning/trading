"""forward.py — the unattended runner.

WHAT IT DOES, ONCE A MINUTE, FOREVER
    1. fill everything the bots decided on the PREVIOUS tick, against THIS
       tick's book (this is the latency model - see engine.py)
    2. pull every open Kalshi singles tennis market
    3. drop anything already carrying a result
    4. fold mirrored markets into matches on ticker order (GUARDS #1)
    5. build the brief for any match seen for the first time, and write it to
       disk BEFORE any bot is asked anything
    6. let all thirteen dispositions deliberate over the same pool
    7. append every deliberation to the reasoning log, fsynced
    8. look for settlements and mark positions at the real outcome
    9. save state atomically, so a reboot resumes rather than restarts

WHAT IT NEVER DOES
    Place an order. It cannot: `safety.get` is GET-only against an allowlist
    that has no order path on it, and `assert_no_credentials()` refuses to
    start on a process that carries a Kalshi key.

SURVIVING THE LAPTOP
    - single-instance lock file with a liveness check, so a Task Scheduler
      restart cannot produce two runners
    - state written to a temp file and os.replace'd, so a power cut cannot
      leave a half-written state file
    - every log line fsynced, so the reasoning log is on the platter before
      the result exists. That is the whole point of a pre-registered log.
    - the two recorders already running on that machine are never touched:
      this process starts nothing, stops nothing, and writes only inside its
      own directory
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import safety
from .bots import BOT_NAMES, BotRunner, Deliberation, LiveState
from .brief import Brief, build_brief
from .engine import PaperEngine
from .kalshi_read import (MatchView, build_match_pool, fetch_event, fetch_tennis,
                          TENNIS_SERIES)
from .sackmann import get_archive
from .tennisdata import refresh as refresh_form

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOGS = ROOT / "logs"
STATE = DATA / "state.json"
LOCK = DATA / ".runner.lock"

REASONING_LOG = LOGS / "reasoning.jsonl"
BRIEF_DIR = DATA / "briefs"
TAPE = LOGS / "tape.jsonl"
HEALTH = LOGS / "health.jsonl"
RUN_LOG = LOGS / "runner.log"

DEFAULT_POLL_SEC = 60
DEFAULT_TARGET_MATCHES = 50

# Settlements are read one event at a time. This caps how many are looked up
# per tick so a backlog cannot make a tick overrun its own poll interval.
SETTLEMENT_BATCH = 25

# A decision that has not filled within this long is dropped rather than filled
# against a book that has moved on. It matters across a restart: resuming eight
# hours later and filling yesterday's intention would be the worst kind of
# fictional fill.
PENDING_MAX_AGE_SEC = 300

# How often to pull fresh main-tour results. The Sackmann mirror is frozen at
# 2026-06-01; tennis-data.co.uk is updated weekly. Daily is generous.
FORM_REFRESH_SEC = 24 * 3600

# How much a PASS verdict must move before it is worth another line. Anything
# that acts is always written in full; this governs repetition only.
PASS_RELOG_CONVICTION_MOVE = 2.0     # a real change of mind, not price wobble
# The periodic heartbeat. Measured: at 0.5-cent conviction granularity the log
# ran 141 lines/tick and 780 MB/day, which would have rotated the earliest
# decisions off the disk before the run reached fifty matches. Coarsening the
# change threshold took it to 40 lines/tick and 143 MB/day - and at that point
# THIS was the dominant term, because 16 bots x ~136 matches is 2,176 heartbeats
# an hour on its own. Six hours puts a full week at roughly a third of the
# rotation budget. Nothing is lost by widening it: `repeated_unchanged` already
# counts every skipped tick and attaches the count to the next record written,
# so how long a view was held is recorded either way.
PASS_RELOG_MAX_GAP_SEC = 6 * 3600
MENTALITY_BARS = {"favourite": 2.0, "underdog": 2.0, "brief-led": 2.5,
                  "momentum": 2.5, "unconstrained": 3.5}

_STOP = False


def _sig(_s, _f):
    global _STOP
    _STOP = True


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def say(msg: str) -> None:
    line = f"{now()} {msg}"
    print(line, flush=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    with RUN_LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _append_fsync(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())


MAX_LOG_BYTES = 250_000_000      # roll at 250 MB
# Eight generations = a 2 GB ceiling. Measured after the D15 fix, the reasoning
# log runs about 170 MB/day, so a week is ~1.2 GB and a fortnight ~2.4 GB. Four
# generations would have quietly discarded the first 18% of a one-week run;
# eight covers a week with headroom, and `src/status.py` warns at 1.5 GB so the
# ceiling is seen coming rather than hit silently.
MAX_LOG_GENERATIONS = 8


def _rotate(path: Path) -> None:
    """Roll a log before it can fill the laptop.

    Nothing is deleted until there are four generations, and the analysis reads
    every generation, so rotating does not lose a single deliberation until the
    total exceeds about a gigabyte. A runner that fills the disk stops
    recording, and the recording is the whole asset.
    """
    try:
        if not path.exists() or path.stat().st_size < MAX_LOG_BYTES:
            return
        oldest = path.with_suffix(path.suffix + f".{MAX_LOG_GENERATIONS}")
        if oldest.exists():
            oldest.unlink()
        for i in range(MAX_LOG_GENERATIONS - 1, 0, -1):
            src = path.with_suffix(path.suffix + f".{i}")
            if src.exists():
                src.replace(path.with_suffix(path.suffix + f".{i+1}"))
        path.replace(path.with_suffix(path.suffix + ".1"))
        say(f"rotated {path.name} at {MAX_LOG_BYTES/1e6:.0f} MB")
    except Exception as exc:  # rotation must never take the runner down
        say(f"log rotation failed for {path.name}: {exc}")


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Single instance
# --------------------------------------------------------------------------

def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            import ctypes
            h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if not h:
                return False
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def acquire_lock() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        try:
            old = json.loads(LOCK.read_text(encoding="utf-8"))
        except Exception:
            old = {}
        pid = int(old.get("pid", 0))
        if _pid_alive(pid):
            raise SystemExit(
                f"a runner is ALREADY RUNNING (pid {pid}, started {old.get('started')}). "
                f"That is the guard working. Stop it first, or delete {LOCK} if you are "
                f"certain it is dead."
            )
        say(f"stale lock from dead pid {pid} - reclaiming")
    _atomic_write(LOCK, json.dumps({"pid": os.getpid(), "started": now()}))


def release_lock() -> None:
    try:
        if LOCK.exists():
            owner = json.loads(LOCK.read_text(encoding="utf-8")).get("pid")
            if owner != os.getpid():
                return          # not ours to remove
        LOCK.unlink(missing_ok=True)
    except Exception:
        pass


class LockLost(RuntimeError):
    """Another process took the lock while we were running."""


def assert_still_own_lock() -> None:
    """Re-check ownership EVERY TICK, not just at startup.

    Checking a lock once at startup is not a lock, it is a greeting. Two ways
    a second writer gets in afterwards, and both are realistic on the laptop:

      * somebody deletes a lock they believe is stale while the owner is alive
        (the setup guide even tells them how, for the case where it IS stale)
      * the Task Scheduler watchdog fires during a window where the lock file
        is briefly absent

    Two runners then share one `state.json` and one reasoning log, and because
    the state write is atomic the file is never malformed - it is simply
    whichever process wrote last, silently discarding the other's positions.
    That is the worst kind of corruption: it looks completely fine.

    This is not hypothetical. Six runners were alive at once on this machine
    during development, because the developer deleted the lock before each
    restart. The guard worked and was bypassed; the fix is to make bypassing it
    survive only until the next tick.
    """
    try:
        if not LOCK.exists():
            _atomic_write(LOCK, json.dumps({"pid": os.getpid(), "started": now(),
                                            "note": "re-created; it had been removed"}))
            return
        owner = json.loads(LOCK.read_text(encoding="utf-8")).get("pid")
    except Exception:
        return                  # an unreadable lock is not evidence of a rival
    if owner != os.getpid():
        raise LockLost(
            f"the lock is now held by pid {owner}, not by this process "
            f"({os.getpid()}). Another runner started. Exiting so that two "
            f"processes cannot write one state file - the last writer would "
            f"silently discard the other's positions."
        )


# --------------------------------------------------------------------------
# The runner
# --------------------------------------------------------------------------

class Forward:
    def __init__(self, poll_sec: int = DEFAULT_POLL_SEC,
                 target: int = DEFAULT_TARGET_MATCHES,
                 size: int = 10, once: bool = False, no_lock: bool = False):
        self.poll_sec = poll_sec
        self.target = target
        self.once = once
        self.no_lock = no_lock
        self.engine = PaperEngine(BOT_NAMES, size=size)
        self.runner = BotRunner(self.engine, self._log_reasoning)
        self.live: dict[str, LiveState] = {}
        self.briefs: dict[str, Brief] = {}
        self.seen_events: set[str] = set()
        self.settled_events: dict[str, str | None] = {}
        self.tick_no = 0
        self.started = now()
        self.deliberations = 0
        self._pending_lines: list[str] = []
        self._last_view: dict[tuple[str, str], tuple] = {}
        self._repeat_count: dict[tuple[str, str], int] = {}
        self._logged_lines = 0
        self._last_form_refresh = 0.0
        self._load()

    # -- persistence -------------------------------------------------------

    def _load(self) -> None:
        if not STATE.exists():
            return
        try:
            s = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            say("state.json unreadable - starting fresh (the logs are the record)")
            return
        self.engine.load(s.get("engine", {}))
        self.seen_events = set(s.get("seen_events", []))
        self.settled_events = dict(s.get("settled_events", {}))
        self.tick_no = int(s.get("tick_no", 0))
        self.started = s.get("started", self.started)
        self.deliberations = int(s.get("deliberations", 0))
        self.runner.control_intents = list(s.get("control_intents", []))
        from .engine import PendingOrder
        self.engine.pending = [PendingOrder(**o) for o in s.get("pending", [])]
        # Deliberately NOT restored. On resume the first pass on every match
        # is written in full again, which costs one extra record per bot per
        # match and guarantees the log after a restart is readable on its own.
        self._last_view = {}
        for et, d in (s.get("live") or {}).items():
            ls = LiveState(event_ticker=et, ticker=d.get("ticker", ""))
            ls.first_seen = d.get("first_seen", "")
            from .bots import Tick
            ls.ticks = [Tick(**t) for t in d.get("ticks", [])[-400:]]
            self.live[et] = ls
        for et in self.seen_events:
            p = BRIEF_DIR / f"{et}.json"
            if p.exists():
                try:
                    self.briefs[et] = Brief(**json.loads(p.read_text(encoding="utf-8")))
                except Exception:
                    pass
        say(f"resumed: tick {self.tick_no}, {len(self.seen_events)} events seen, "
            f"{len(self.settled_events)} settled, {self.deliberations} deliberations")

    def _save(self) -> None:
        payload = {
            "started": self.started,
            "saved_at": now(),
            "tick_no": self.tick_no,
            "deliberations": self.deliberations,
            "seen_events": sorted(self.seen_events),
            "settled_events": self.settled_events,
            "control_intents": self.runner.control_intents,
            "engine": self.engine.snapshot(),
            "pending": [asdict(o) for o in self.engine.pending],
            "live": {
                et: {"ticker": ls.ticker, "first_seen": ls.first_seen,
                     "ticks": [asdict(t) for t in ls.ticks[-120:]]}
                for et, ls in self.live.items()
            },
        }
        _atomic_write(STATE, json.dumps(payload, default=str))

    # -- logging -----------------------------------------------------------

    def _log_reasoning(self, d: Deliberation) -> None:
        """Buffer one deliberation; the tick flushes and fsyncs once.

        WHAT IS WRITTEN, AND WHY NOT ALL OF IT
            Every entry, re-entry and exit is written in full, always. A PASS is
            written in full the first time a bot sees a match and thereafter
            only when its verdict materially changes - a different action, or
            conviction moving by at least 0.5. An unchanged pass repeated once a
            minute for six hours is 360 identical records; at 16 bots x ~120
            matches that is 3.3 MB per tick and about 4.6 GB a day, which fills
            the laptop inside a week and buries the decisions that matter.

            The pre-registration guarantee is untouched: every action, and every
            first look, is on the platter with an fsync before the match
            finishes. What is dropped is literal repetition, and the repeat
            count is kept so the record still says how long a view was held.
        """
        assert d.outcome_known is False, "a deliberation must be written before the result"
        self.deliberations += 1
        key = (d.bot, d.event_ticker)
        now_ts = datetime.now(timezone.utc).timestamp()

        # Anything that ACTS is always written in full, always.
        if d.action != "pass":
            if self._repeat_count.get(key):
                d.repeated_unchanged = self._repeat_count.pop(key)
            self._last_view[key] = (d.action, d.conviction, now_ts)
            self._pending_lines.append(d.to_json())
            return

        prev = self._last_view.get(key)
        if prev is None:
            # FIRST LOOK at this match by this bot - full record, with prose.
            self._last_view[key] = ("pass", d.conviction, now_ts)
            self._pending_lines.append(d.to_json())
            return

        # A repeated pass. Three things make it worth another line, and small
        # conviction wobble as prices tick is not one of them: at 0.5-cent
        # granularity it produced 141 records a tick, 780 MB a day, and would
        # have rotated the earliest decisions off the disk before the run
        # reached fifty matches.
        _prev_act, prev_conv, prev_ts = prev
        bar = MENTALITY_BARS.get(d.mentality, 2.5)
        crossed_the_bar = (prev_conv < bar) != (d.conviction < bar)
        moved_a_lot = abs(d.conviction - prev_conv) >= PASS_RELOG_CONVICTION_MOVE
        too_long = (now_ts - prev_ts) >= PASS_RELOG_MAX_GAP_SEC
        if not (crossed_the_bar or moved_a_lot or too_long):
            self._repeat_count[key] = self._repeat_count.get(key, 0) + 1
            return
        d.repeated_unchanged = self._repeat_count.pop(key, 0)
        self._last_view[key] = ("pass", d.conviction, now_ts)
        self._pending_lines.append(d.to_json_compact())

    def _flush_reasoning(self) -> int:
        if not self._pending_lines:
            return 0
        REASONING_LOG.parent.mkdir(parents=True, exist_ok=True)
        _rotate(REASONING_LOG)
        _rotate(TAPE)
        n = len(self._pending_lines)
        with REASONING_LOG.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(self._pending_lines) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._pending_lines.clear()
        return n

    def _write_brief(self, br: Brief) -> None:
        BRIEF_DIR.mkdir(parents=True, exist_ok=True)
        _atomic_write(BRIEF_DIR / f"{br.event_ticker}.json",
                      json.dumps(br.to_dict(), default=str, indent=1))

    # -- one tick ----------------------------------------------------------

    def refresh_form(self) -> None:
        """Top up main-tour form from tennis-data.co.uk.

        The Sackmann mirror is FROZEN (last push 2026-06-25, data to
        2026-06-01, verified byte-identical on re-download). This is the only
        free source found that is current. MAIN TOUR ONLY - Challenger and ITF,
        which are ~88% of the Kalshi pool, are not covered and stay stale.

        Failure here must never take the runner down: stale form is a weaker
        brief, a dead runner is no brief at all.
        """
        now_t = time.time()
        if now_t - self._last_form_refresh < FORM_REFRESH_SEC:
            return
        self._last_form_refresh = now_t
        for tour in ("atp", "wta"):
            try:
                arch = get_archive(tour)
                before = arch.last_date
                r = refresh_form(arch)
                say(f"form refresh {tour}: {before} -> {arch.last_date}  "
                    f"merged {r.rows_merged}/{r.rows_after_archive} new rows, "
                    f"{r.unmatched_players} unresolved, "
                    f"{r.dropped_future_dated} future-dated dropped")
            except Exception as exc:  # noqa: BLE001
                say(f"form refresh failed for {tour} ({exc}) - continuing on the "
                    f"frozen mirror, which is stale but correct")

    def tick(self) -> dict[str, Any]:
        self.tick_no += 1
        t0 = time.time()
        self.refresh_form()

        quotes = fetch_tennis(status="open")
        # An open market carrying a result is a settled market that has not
        # been reclassified yet. Letting one into the pool would hand every bot
        # the answer. GUARDS #2.
        leaked = sum(1 for q in quotes if q.result)
        quotes = [q for q in quotes if not q.result]

        pool = build_match_pool(quotes)
        pool = [m for m in pool if m.primary.is_quotable()]
        pool_by_event = {m.event_ticker: m for m in pool}

        # 1. fills first, against this tick's book
        filled = self.engine.execute_pending(pool_by_event)

        # 2. tape + briefs
        new_briefs = 0
        for mv in pool:
            ls = self.live.get(mv.event_ticker)
            if ls is None:
                ls = LiveState(event_ticker=mv.event_ticker, ticker=mv.primary.ticker)
                self.live[mv.event_ticker] = ls
            ls.push(mv)
            if mv.event_ticker not in self.briefs:
                try:
                    br = build_brief(mv)
                except Exception as exc:
                    say(f"brief failed for {mv.event_ticker}: {exc}")
                    continue
                self.briefs[mv.event_ticker] = br
                self._write_brief(br)
                self.seen_events.add(mv.event_ticker)
                new_briefs += 1

        # 3. deliberate
        counts = self.runner.tick(pool, self.briefs, self.live)

        # 4. settlements, and expire anything that never filled
        self._expire_pending()
        settled_now = self._check_settlements(set(pool_by_event))

        # 5. flush the reasoning log, then tape + health, content-asserted
        self._logged_lines = self._flush_reasoning()
        health = self._health(quotes, pool, leaked, filled, counts,
                              new_briefs, settled_now, time.time() - t0)
        _append_fsync(HEALTH, json.dumps(health))
        _append_fsync(TAPE, json.dumps({
            "ts": now(), "tick": self.tick_no,
            "quotes": [{"t": q.ticker, "e": q.event_ticker, "a": q.yes_ask,
                        "b": q.yes_bid, "as": q.yes_ask_size, "bs": q.yes_bid_size,
                        "v": q.volume, "l": q.last} for q in quotes],
        }))
        self._save()
        return health

    def _expire_pending(self) -> int:
        """Drop decisions older than PENDING_MAX_AGE_SEC, and say so."""
        from datetime import datetime as _dt
        cut = datetime.now(timezone.utc).timestamp() - PENDING_MAX_AGE_SEC
        keep, dropped = [], 0
        for o in self.engine.pending:
            try:
                age_ok = _dt.fromisoformat(o.decided_at).timestamp() >= cut
            except Exception:
                age_ok = False
            if age_ok:
                keep.append(o)
            else:
                self.engine.ledgers[o.bot].rejected.append({
                    "ts": now(), "decision_id": o.decision_id, "side": o.side,
                    "ticker": o.ticker,
                    "reason": f"never filled within {PENDING_MAX_AGE_SEC}s "
                              f"(usually a restart) - dropped rather than filled "
                              f"against a book that has moved on",
                    "decided_price": o.decided_price,
                })
                dropped += 1
        self.engine.pending = keep
        return dropped

    def _check_settlements(self, live_events: set[str]) -> int:
        """Read the outcome for every event we care about, one event at a time.

        "Care about" is any event a bot holds, any event the control recorded
        an intent on, and any event that has left the open pool. That last one
        is what makes the denominator honest: a match nobody traded still
        counts toward the fifty, so the sample is matches-that-settled and not
        matches-somebody-liked.
        """
        interesting: set[str] = set(self.seen_events)
        want = {e for e in interesting
                if e not in self.settled_events and e not in live_events}
        for lg in self.engine.ledgers.values():
            for p in lg.positions:
                if p.open and p.event_ticker not in self.settled_events:
                    want.add(p.event_ticker)
        if not want:
            return 0

        n = 0
        for et in sorted(want)[:SETTLEMENT_BATCH]:
            try:
                qs = fetch_event(et)
            except RuntimeError:
                continue
            if not qs:
                continue
            if any(q.status in ("active", "initialized") for q in qs):
                continue          # still trading; not settled, not missing
            winner = next((q.ticker for q in qs if q.result == "yes"), None)
            results = {q.result for q in qs}
            if winner is None and not (results & {"no", "yes"}):
                continue          # closed but unresolved; look again next pass
            if winner is None:
                # every side reads "no" - a void or no-contest. Its own state.
                # Folding it into a loss would be a silent selection effect.
                self.engine.settle(et, None, voided=True)
                self.settled_events[et] = None
            else:
                self.engine.settle(et, winner)
                self.settled_events[et] = winner
            n += 1
        return n

    def _health(self, quotes, pool, leaked, filled, counts, new_briefs,
                settled_now, secs) -> dict[str, Any]:
        """GUARDS #12 - assert CONTENT, not that the call returned."""
        n = len(quotes)
        with_ask = sum(1 for q in quotes if q.yes_ask is not None)
        zero_ask = sum(1 for q in quotes if q.yes_ask == 0)
        quotable = sum(1 for q in quotes if q.is_quotable())
        crossed = sum(1 for m in pool if m.crossed())
        gross_arb = [m.gross_arb_cents() for m in pool if m.gross_arb_cents() > 0]
        # Net-of-fee tradeable arbitrage: both legs pay a taker fee.
        from common.kalshi_fees import fee_rate_cents as _frc
        tradeable_arb = 0
        for m in pool:
            g = m.gross_arb_cents()
            if not g or m.mirror is None:
                continue
            cost = float(_frc(m.primary.yes_ask)) + float(_frc(m.mirror.yes_ask))
            if g > cost:
                tradeable_arb += 1
        open_pos = sum(1 for lg in self.engine.ledgers.values()
                       for p in lg.positions if p.open)
        closed = sum(len(lg.closed()) for lg in self.engine.ledgers.values())
        h = {
            "ts": now(), "tick": self.tick_no, "secs": round(secs, 2),
            "markets": n, "matches": len(pool),
            "pct_with_ask": round(100 * with_ask / n, 1) if n else 0.0,
            "zero_ask": zero_ask,
            "pct_quotable": round(100 * quotable / n, 1) if n else 0.0,
            "stale_book_pairs": crossed,
            "gross_arb_pairs": len(gross_arb),
            "gross_arb_median_cents": (sorted(gross_arb)[len(gross_arb) // 2]
                                       if gross_arb else 0),
            "tradeable_arb_pairs": tradeable_arb,
            "result_leak_filtered": leaked,
            "new_briefs": new_briefs,
            "deliberations": counts["deliberations"],
            "reasoning_lines_written": self._logged_lines,
            "pending_orders": len(self.engine.pending),
            "entries_queued": counts["entries_queued"],
            "exits_queued": counts["exits_queued"],
            "filled": filled,
            "settled_this_tick": settled_now,
            "settled_total": len(self.settled_events),
            "open_positions": open_pos,
            "closed_positions": closed,
            "alerts": [],
        }
        # The alerts are the thing a human reads. Each is a content assertion
        # that has actually failed somewhere in this repo before.
        if n == 0:
            h["alerts"].append("ZERO markets returned - the feed or the series list is wrong")
        elif h["pct_with_ask"] < 50:
            h["alerts"].append(
                f"only {h['pct_with_ask']}% of markets carry an ask - the *_dollars "
                f"field rename may have happened again (GUARDS #12)")
        if zero_ask > 0.2 * max(1, n):
            h["alerts"].append(f"{zero_ask} markets show a 0c ask - a parse returning 0 on error")
        if crossed > 0:
            h["alerts"].append(
                f"{crossed} matches have BIDS summing over 100c - impossible in a live "
                f"book, one side is stale (GUARDS #18)")
        if tradeable_arb > 0:
            h["alerts"].append(
                f"{tradeable_arb} matches show an ask sum below 100c by MORE than the "
                f"two-leg fee. Worth a look; the archive has never found one with size.")
        if secs > self.poll_sec:
            h["alerts"].append(f"the tick took {secs:.0f}s against a {self.poll_sec}s poll")
        return h

    # -- loop --------------------------------------------------------------

    def run(self) -> None:
        say(safety.banner())
        say(f"target {self.target} settled matches, poll {self.poll_sec}s, "
            f"{len(BOT_NAMES)} bots, size {self.engine.size} contracts")
        while not _STOP:
            try:
                if not self.no_lock:
                    assert_still_own_lock()
                h = self.tick()
                say(f"tick {h['tick']:5d}  markets {h['markets']:4d}  matches {h['matches']:3d}  "
                    f"delib {h['deliberations']:5d}  open {h['open_positions']:3d}  "
                    f"closed {h['closed_positions']:4d}  settled {h['settled_total']:3d}/"
                    f"{self.target}  {h['secs']:.1f}s"
                    + ("  ALERTS: " + "; ".join(h["alerts"]) if h["alerts"] else ""))
                if len(self.settled_events) >= self.target:
                    say(f"TARGET REACHED: {len(self.settled_events)} settled matches. "
                        f"Run `python -m src.analyse` for the pre-registered gates.")
                    break
            except KeyboardInterrupt:
                break
            except LockLost as exc:
                say(f"LOCK LOST - {exc}")
                say("stopping. This is the guard working, not a failure.")
                return
            except Exception:
                say("tick failed:\n" + traceback.format_exc())
            if self.once:
                break
            for _ in range(self.poll_sec):
                if _STOP:
                    break
                time.sleep(1)
        self._save()
        say("stopped cleanly; state saved")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Tennis paper-only forward test. No money anywhere.")
    ap.add_argument("--poll", type=int, default=DEFAULT_POLL_SEC)
    ap.add_argument("--target", type=int, default=DEFAULT_TARGET_MATCHES)
    ap.add_argument("--size", type=int, default=10, help="contracts per entry (FIXED, not dollars)")
    ap.add_argument("--once", action="store_true", help="one tick then exit")
    ap.add_argument("--no-lock", action="store_true")
    a = ap.parse_args(argv)

    safety.assert_no_credentials()
    signal.signal(signal.SIGINT, _sig)
    try:
        signal.signal(signal.SIGTERM, _sig)
    except Exception:
        pass
    if not a.no_lock:
        acquire_lock()
    try:
        Forward(poll_sec=a.poll, target=a.target, size=a.size, once=a.once,
                no_lock=a.no_lock).run()
    finally:
        if not a.no_lock:
            release_lock()
    return 0


if __name__ == "__main__":
    sys.exit(main())
