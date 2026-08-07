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
  settled matches                 {h['settled_total']} of the 50 needed""")

    span = health[0], health[-1]
    try:
        t0 = datetime.fromisoformat(span[0]["ts"])
        t1 = datetime.fromisoformat(span[1]["ts"])
        hours = max(0.01, (t1 - t0).total_seconds() / 3600)
        rate = (span[1]["settled_total"] - span[0]["settled_total"]) / hours
        if rate > 0:
            need = 50 - h["settled_total"]
            print(f"  settling at about {rate:.1f} matches/hour over the logged window")
            print(f"  at that rate the remaining {need} take about "
                  f"{need/rate/24:.1f} more days")
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
