"""Is each background test still alive, or has it quietly died?

This answers one question and refuses to pretend it answers a bigger one.

WHAT "ALIVE" MEANS HERE
-----------------------
A heartbeat file changed recently. That is all. A runner ticking every minute
while writing nonsense reads ALIVE; a healthy runner having a long quiet spell
reads STALE. It is a heartbeat, not a health check, and it is not dressed up as
one. See COORDINATOR.md section 3b.

Four states, because two would lie:

  ALIVE      the heartbeat changed inside its own threshold
  STALE      a continuous job that has gone quiet -- go and look at it
  FINISHED   a one-shot job whose log says it completed. NOT a problem
  NEVER RUN  no heartbeat file has ever appeared

FINISHED exists because of a real near-miss: crypto's tape pull completed
cleanly and a two-state check would have shouted STALE at it forever. A check
that cries wolf gets ignored -- already recorded here as decision D8.

Runners on the laptop are reported "can't see from this machine", never dead.
Claiming to know the state of something you cannot observe is worse than saying
nothing.

No network. No credentials. Reads files and asks Windows whether a process id
still exists. Never starts, stops or restarts anything.

Usage
-----
  py -3 coordinator\\runners.py            # the table
  py -3 coordinator\\runners.py --json     # same, machine-readable
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
REGISTRY = HERE / "runners.json"

ALIVE = "ALIVE"
STALE = "STALE"
FINISHED = "FINISHED"
NEVER = "NEVER RUN"
UNSEEN = "can't see from this machine"

# How far back a one-shot log tail is read looking for its done marker.
TAIL_BYTES = 4096

# A wall of 30 unwatched log files is the same as no warning at all.
UNREGISTERED_SHOWN = 8

# Folders that never hold a background test's log.
HEAVY = {".venv", "venv", "__pycache__", ".git", "node_modules", ".pytest_cache",
         ".mypy_cache", "_archive", "briefs"}


# --------------------------------------------------------------------------
# process liveness, without shelling out
# --------------------------------------------------------------------------
def pid_alive(pid: int) -> bool | None:
    """True / False / None where None means 'could not tell'.

    os.kill is deliberately NOT used. On Windows os.kill(pid, 0) does not probe
    a process -- it calls TerminateProcess and would kill the very runner this
    is supposed to be reporting on. This opens a query-only handle instead.
    """
    if sys.platform != "win32":
        try:
            import os
            os.kill(pid, 0)          # POSIX: signal 0 really is a probe
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True              # exists, not ours
        except Exception:
            return None
    try:
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            err = ctypes.get_last_error()
            # 87 = invalid parameter, which is how Windows says "no such pid".
            # 5 = access denied, which means it exists but is not ours to see.
            if err == 87:
                return False
            if err == 5:
                return True
            return None
        try:
            code = ctypes.c_ulong()
            if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return None
            return code.value == STILL_ACTIVE
        finally:
            k32.CloseHandle(handle)
    except Exception:
        return None


# --------------------------------------------------------------------------
# files
# --------------------------------------------------------------------------
def newest_mtime(paths: list[str]):
    """(epoch, relative path) of the most recently touched heartbeat file."""
    best_t, best_p = 0.0, ""
    for rel in paths:
        p = REPO / rel
        try:
            t = p.stat().st_mtime
        except OSError:
            continue
        if t > best_t:
            best_t, best_p = t, rel
    return best_t, best_p


def tail(path: Path, n: int = TAIL_BYTES) -> str:
    try:
        with path.open("rb") as fh:
            try:
                fh.seek(-n, 2)
            except OSError:
                fh.seek(0)
            return fh.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def lock_pid(rel):
    """The process id a runner recorded for itself, if it kept one."""
    if not rel:
        return None
    p = REPO / rel
    try:
        raw = p.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    try:
        return int(json.loads(raw).get("pid"))
    except Exception:
        return None


def minutes_since(epoch: float) -> float:
    return (datetime.now().timestamp() - epoch) / 60.0


def english_age(mins: float) -> str:
    if mins < 1:
        return "less than a minute ago"
    if mins < 60:
        n = int(mins)
        return f"{n} minute{'s' if n != 1 else ''} ago"
    if mins < 48 * 60:
        n = int(mins // 60)
        return f"{n} hour{'s' if n != 1 else ''} ago"
    n = int(mins // 1440)
    return f"{n} day{'s' if n != 1 else ''} ago"


# --------------------------------------------------------------------------
# the check
# --------------------------------------------------------------------------
def check(entry: dict) -> dict:
    out = {
        "id": entry["id"],
        "workstream": entry.get("workstream", ""),
        "title": entry.get("title", entry["id"]),
        "plain_english": entry.get("plain_english", ""),
        "kind": entry.get("kind", "continuous"),
        "machine": entry.get("machine", "desktop"),
        "restart": entry.get("restart", ""),
        "state": NEVER,
        "why": "",
        "last_write": "",
        "age_minutes": None,
        "heartbeat_file": "",
        "process": "",
        "needs_a_human": False,
    }

    if out["machine"] != "desktop":
        out["state"] = UNSEEN
        out["why"] = (
            f"It runs on the {out['machine']}. Nothing on this machine can see "
            f"it, so no claim is made either way."
        )
        return out

    t, rel = newest_mtime(entry.get("heartbeat") or [])
    if not t:
        out["why"] = (
            "No log file has ever appeared where this one is supposed to write. "
            "Either it has never been started here, or it is writing somewhere "
            "else than the registry says."
        )
        out["needs_a_human"] = entry.get("kind") == "continuous"
        return out

    mins = minutes_since(t)
    out["age_minutes"] = round(mins, 1)
    out["last_write"] = datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")
    out["heartbeat_file"] = rel

    pid = lock_pid(entry.get("lock"))
    running = pid_alive(pid) if pid else None
    if pid:
        out["process"] = (
            f"process {pid} is running" if running is True else
            f"process {pid} is gone" if running is False else
            f"process {pid}, could not tell"
        )

    # A one-shot job that says it finished is finished. Do not shout at it.
    if entry.get("kind") == "one-shot" and entry.get("done_marker"):
        if entry["done_marker"] in tail(REPO / rel):
            out["state"] = FINISHED
            out["why"] = (
                f"Its log ends with '{entry['done_marker']}', so it completed. "
                f"It last wrote {english_age(mins)}. This is normal and needs "
                f"nothing."
            )
            return out

    limit = float(entry.get("stale_after_minutes", 30))
    every = entry.get("writes_every_minutes")
    if mins <= limit:
        out["state"] = ALIVE
        out["why"] = f"It wrote to its log {english_age(mins)}."
        if running is False:
            # Fresh log but no process: it stopped in the last few minutes.
            out["state"] = STALE
            out["why"] = (
                f"It wrote {english_age(mins)}, but the process it recorded "
                f"({pid}) is gone. It has stopped very recently."
            )
            out["needs_a_human"] = True
        return out

    out["state"] = STALE
    expect = f" It is supposed to write every {every} minute(s)." if every else ""
    if running is True:
        out["why"] = (
            f"Its process ({pid}) is still running, but it has written nothing "
            f"for {english_age(mins)}.{expect} Running but silent is worse than "
            f"stopped -- it looks fine in the task list."
        )
    elif running is False:
        out["why"] = (
            f"Stopped. Last wrote {english_age(mins)} and process {pid} no "
            f"longer exists.{expect}"
        )
    else:
        out["why"] = f"Last wrote {english_age(mins)}.{expect}"
    out["needs_a_human"] = True
    return out


# --------------------------------------------------------------------------
# what is NOT in the registry
# --------------------------------------------------------------------------
def unregistered(known: set[str]) -> list[dict]:
    """Log-shaped and lock-shaped files nobody registered, newest first.

    This does not turn them into watched tests. It makes the omission visible,
    which is the most an unmaintained list can honestly offer. Newest first,
    because a file touched an hour ago is far more likely to be a live thing
    nobody added than one touched last week.

    Empty files are skipped -- an untouched `.err` is the *absence* of a
    problem, and listing it as something to look at is exactly the crying-wolf
    failure this module exists to avoid.
    """
    found = []
    for project in sorted(p for p in REPO.iterdir() if p.is_dir()):
        if project.name in HEAVY or project.name.startswith("."):
            continue
        for sub in ("logs", "data"):
            d = project / sub
            if not d.is_dir():
                continue
            for f in sorted(d.iterdir()):
                if not f.is_file():
                    continue
                if f.suffix.lower() not in {".log", ".out", ".err", ".lock"} and \
                        f.name != "health.jsonl":
                    continue
                rel = str(f.relative_to(REPO)).replace("\\", "/")
                if rel in known:
                    continue
                try:
                    st = f.stat()
                except OSError:
                    continue
                if st.st_size == 0:
                    continue
                found.append({
                    "path": rel,
                    "age_minutes": round(minutes_since(st.st_mtime), 1),
                    "age": english_age(minutes_since(st.st_mtime)),
                })
    found.sort(key=lambda r: r["age_minutes"])
    return found


def load() -> list[dict]:
    if not REGISTRY.exists():
        return []
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return data.get("runners", [])


def check_all() -> dict:
    entries = load()
    rows = [check(e) for e in entries]
    known = set()
    for e in entries:
        known.update(e.get("heartbeat") or [])
        if e.get("lock"):
            known.add(e["lock"])
    return {"runners": rows, "unregistered": unregistered(known)}


def by_workstream(result: dict) -> dict:
    out: dict[str, list[dict]] = {}
    for r in result["runners"]:
        out.setdefault(r["workstream"], []).append(r)
    return out


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
def render(result: dict) -> str:
    L = ["BACKGROUND TESTS", ""]
    width = max((len(r["title"]) for r in result["runners"]), default=10)
    for r in result["runners"]:
        L.append(f"  {r['state']:<28} {r['title']:<{width}}")
        L.append(f"      {r['why']}")
        if r["state"] == STALE and r["restart"]:
            L.append(f"      To restart it:  {r['restart']}")
        L.append("")
    L.append("  ALIVE means it wrote to its log recently. It does NOT mean the")
    L.append("  numbers coming out of it are right -- nothing here checks that.")
    un = result["unregistered"]
    if un:
        L.append("")
        L.append(f"  {len(un)} log file(s) found on disk that are NOT in the watch")
        L.append("  list, so nothing above covers them. Newest first:")
        for u in un[:UNREGISTERED_SHOWN]:
            L.append(f"    - {u['path']}  (last touched {u['age']})")
        if len(un) > UNREGISTERED_SHOWN:
            L.append(f"    ...and {len(un) - UNREGISTERED_SHOWN} older ones, "
                     f"the oldest last touched {un[-1]['age']}. Full list: "
                     f"py -3 coordinator\\runners.py --json")
    return "\n".join(L)


def _ascii_safe_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    _ascii_safe_console()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    result = check_all()
    print(json.dumps(result, indent=2) if a.json else render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
