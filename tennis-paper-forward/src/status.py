"""status.py — the one command that answers "is it still working?".

    .venv\\Scripts\\python.exe -m src.status

Prints a page in plain English. Reads only; starts nothing, stops nothing,
touches no other process on the machine.

It is deliberately blunt about the two things that go wrong silently:
a recorder that is alive but writing nulls, and a runner that died three days
ago while its last log line still looks fine.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOGS = ROOT / "logs"


def _jsonl_tail(path: Path, n: int = 200) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    out = []
    for line in lines:
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


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


def _ago(iso: str | None) -> str:
    if not iso:
        return "never"
    try:
        t = datetime.fromisoformat(iso)
    except Exception:
        return iso
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    d = datetime.now(timezone.utc) - t
    s = int(d.total_seconds())
    if s < 90:
        return f"{s}s ago"
    if s < 5400:
        return f"{s//60}m ago"
    return f"{s//3600}h {(s%3600)//60}m ago"


def main() -> int:
    print("=" * 74)
    print(" TENNIS PAPER FORWARD TEST — status")
    print(" PAPER ONLY. No credentials, no order endpoint, no money anywhere.")
    print("=" * 74)

    lock = DATA / ".runner.lock"
    running = False
    if lock.exists():
        try:
            info = json.loads(lock.read_text(encoding="utf-8"))
            pid = int(info.get("pid", 0))
            running = _pid_alive(pid)
            print(f"\nRUNNER   pid {pid}  started {info.get('started','?')}  "
                  f"{'ALIVE' if running else 'DEAD (stale lock)'}")
        except Exception:
            print("\nRUNNER   lock file unreadable")
    else:
        print("\nRUNNER   not running (no lock file)")

    health = _jsonl_tail(LOGS / "health.jsonl", 400)
    if not health:
        print("\nNo health log yet. If the runner just started, wait one tick.")
        return 1
    h = health[-1]
    age = _ago(h["ts"])
    print(f"LAST TICK  #{h['tick']}  {age}  took {h['secs']}s")

    stale = False
    try:
        t = datetime.fromisoformat(h["ts"])
        stale = (datetime.now(timezone.utc) - t) > timedelta(minutes=10)
    except Exception:
        pass
    if stale:
        print("  *** THE LAST TICK IS OVER TEN MINUTES OLD. The runner is not "
              "working, whatever the lock file says. ***")

    # The target is whatever the runner was actually started with, read from its
    # own record. It was hardcoded to 50 until 2026-08-08, so once the target was
    # raised to 2,500 this printed "139 of the 50 needed" and "-4.3 more days".
    # Not merely wrong -- visibly absurd, and it had been for half a day, because
    # nobody reads a progress line looking for arithmetic errors.
    target = h.get("target")
    if target is None:
        try:
            target = int(json.loads((DATA / "state.json").read_text(
                encoding="utf-8")).get("target") or 50)
        except Exception:
            target = 50

    print(f"""
WHAT IT IS SEEING
  tennis markets on Kalshi      {h['markets']}
  distinct matches              {h['matches']}
  carrying a live two-sided quote {h['pct_quotable']}%
  markets with no ask at all      {100 - h['pct_with_ask']:.1f}%   (should be near 0)

WHAT THE BOTS ARE DOING
  decisions considered this tick  {h['deliberations']}
  written to the reasoning log    {h.get('reasoning_lines_written', 0)}
  entries queued                  {h['entries_queued']}
  exits queued                    {h['exits_queued']}
  orders filled this tick         {h['filled']}
  open paper positions            {h['open_positions']}
  closed paper positions          {h['closed_positions']}

PROGRESS
  settled matches                 {h['settled_total']} of the {target} wanted""")

    # Rate over time the runner was actually RUNNING, not wall-clock.
    #
    # The first version divided by (last tick - first tick), which silently
    # includes any period the runner was DEAD. On 2026-08-08 it had been dead
    # for 12h44m, and the resulting estimate was 1.5 matches/hour against a true
    # 3.9 -- so it reported 66 days remaining when the honest figure was 25.
    # An outage made the job look two and a half times longer than it is, which
    # is exactly the wrong direction: the number gets worse the more of it you
    # miss, so it punishes you twice for the same fault.
    #
    # Gaps longer than five poll intervals are treated as downtime and excluded.
    try:
        stamps = [datetime.fromisoformat(x["ts"]) for x in health]
        poll = max(1.0, float(health[-1].get("secs", 13)))
        max_gap = max(300.0, poll * 5)
        running = 0.0
        for a, b in zip(stamps, stamps[1:]):
            gap = (b - a).total_seconds()
            if gap <= max_gap:
                running += gap
        hours = max(0.01, running / 3600)
        rate = (health[-1]["settled_total"] - health[0]["settled_total"]) / hours
        if rate > 0:
            need = target - h["settled_total"]
            print(f"  settling at about {rate:.1f} matches/hour "
                  f"({hours:.0f}h of actual running time in the log)")
            print(f"  at that rate the remaining {need} take about "
                  f"{need/rate/24:.0f} more days of UPTIME")
            print(f"  note: a bot enters roughly 40% of matches, so {target} "
                  f"settled gives each bot about {int(0.4*target)} trades")
        else:
            print("  no matches have settled in the logged window yet — normal "
                  "early on, since a match must finish AND Kalshi must resolve it")
    except Exception:
        pass

    alerts = h.get("alerts") or []
    print("\nALERTS")
    if not alerts:
        print("  none")
    for a in alerts:
        print(f"  ! {a}")

    if h.get("gross_arb_pairs"):
        print(f"\n  (for information, not a fault: {h['gross_arb_pairs']} matches have "
              f"both asks summing under a dollar, median {h.get('gross_arb_median_cents',0)}c. "
              f"{h.get('tradeable_arb_pairs',0)} of them beat the two-leg fee. "
              f"The archive has never found one with size behind it.)")

    print("""
DISK
""", end="")
    for p in (LOGS / "reasoning.jsonl", LOGS / "tape.jsonl", LOGS / "health.jsonl",
              DATA / "state.json"):
        if p.exists():
            print(f"  {p.name:22s} {p.stat().st_size/1e6:8.1f} MB   "
                  f"modified {_ago(datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat())}")
    bd = DATA / "briefs"
    if bd.exists():
        print(f"  briefs/                {len(list(bd.glob('*.json'))):8d} files")

    # The logs are the asset. Rotation stops them filling the disk, but
    # rotation also DELETES the oldest generation - so the ceiling has to be
    # visible before it is reached, not discovered afterwards.
    total = sum(p.stat().st_size for p in LOGS.glob("*.jsonl*") if p.is_file())
    print(f"  {'ALL LOGS':22s} {total/1e9:8.2f} GB of a 2.00 GB ceiling")
    if total > 1_500_000_000:
        print("  *** The logs are near the 2 GB ceiling. Past it, the OLDEST")
        print("      reasoning records start being deleted. Copy logs/ somewhere")
        print("      else, or raise MAX_LOG_GENERATIONS in src/forward.py. ***")

    print("""
NEXT
  full pre-registered analysis:  .venv\\Scripts\\python.exe -m src.analyse
  the gates it computes:         PREREGISTRATION.md
""")
    return 0 if (running and not stale) else 1


if __name__ == "__main__":
    sys.exit(main())
