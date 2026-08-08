"""Is each background test still alive, or has it quietly died?

This answers one question and refuses to pretend it answers a bigger one.

WHAT "ALIVE" MEANS HERE
-----------------------
A heartbeat file changed recently. That is all. A runner ticking every minute
while writing nonsense reads ALIVE; a healthy runner having a long quiet spell
reads STALE. It is a heartbeat, not a health check, and it is not dressed up as
one. See COORDINATOR.md section 3b.

Four states for a runner this machine can see, because two would lie:

  ALIVE      the heartbeat changed inside its own threshold
  STALE      a continuous job that has gone quiet -- go and look at it
  FINISHED   a one-shot job whose log says it completed. NOT a problem
  NEVER RUN  no heartbeat file has ever appeared

FINISHED exists because of a real near-miss: crypto's tape pull completed
cleanly and a two-state check would have shouted STALE at it forever. A check
that cries wolf gets ignored -- already recorded here as decision D8.

AND TWO STATES THAT ARE NOT LIVENESS AT ALL
-------------------------------------------
The two Kalshi recorders run on the LAPTOP. There is no shared drive, no sync
folder, no heartbeat that reaches this machine, and this module makes no
network call by design. **There is no signal to read, and no registry entry can
invent one.**

  CONFIRMED (by hand)   a human said it was running, at the time shown
  CHECK IT BY HAND      nobody has said so recently enough

Those describe **the freshness of a human check-in, not the recorder.** It can
die one minute after a confirmation and this will read CONFIRMED for the rest
of the window. That is a real weakness and it is printed next to the state
every time, because a reader who mistakes it for monitoring is worse off than
one who was told nothing. See COORDINATOR.md section 3b.

TWO REGISTRIES, COMPARED NOT MERGED
-----------------------------------
runners/runners.json (the shared watchdog) owns WHAT RUNS on this machine.
This module owns WHETHER IT IS PRODUCING ANYTHING. Different questions, so
they stay separate -- but two lists of the same runners drift, so every run
reports any runner present in one and missing from the other.

No network. No credentials. Reads files and asks Windows whether a process id
still exists. Never starts, stops or restarts anything.

Usage
-----
  py -3 coordinator\\runners.py            # the table
  py -3 coordinator\\runners.py --json     # same, machine-readable
  py -3 coordinator\\runners.py confirm <id> --note "what you saw"
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
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

# Confirmation-monitored runners -- see COORDINATOR.md section 3b. These two
# states describe A HUMAN CHECK-IN, not a process. They are named so that
# nobody can read them as liveness.
CONFIRMED = "CONFIRMED (by hand)"
CHECK_IT = "CHECK IT BY HAND"

CONFIRMS = HERE / "confirmations"

# The watchdog's own registry. It owns WHAT RUNS; this module owns WHETHER IT
# IS PRODUCING ANYTHING. Two lists of the same runners drift, so they are
# compared rather than merged.
WATCHDOG_REGISTRY = REPO / "runners" / "runners.json"

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


def rel_to_repo(p: Path) -> str:
    """Path relative to the repo, or the whole path if it lies outside it.

    Path.relative_to RAISES on a path outside the repo. It was used inside an
    error message about a missing file, so the failure path had a second
    failure hiding in it -- the report about the broken thing was itself the
    crash. Found by a test that pointed the registry at a temp folder.
    """
    try:
        return str(p.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(p)


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
# confirmation monitoring -- for runners no signal reaches
# --------------------------------------------------------------------------
def confirmation_path(runner_id: str) -> Path:
    return CONFIRMS / f"{runner_id}.json"


def last_confirmation(runner_id: str) -> dict | None:
    p = confirmation_path(runner_id)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def record_confirmation(runner_id: str, note: str, when: str) -> Path:
    """Write down that a human looked and it was alive. Nothing more.

    This is the whole of what 'monitored-only' can mean for the laptop
    recorders: there is no shared drive, no sync folder, no heartbeat that
    reaches this machine and no network call allowed. So what is stored is the
    check-in, and the coordinator nags when the check-in goes stale.
    """
    CONFIRMS.mkdir(exist_ok=True)
    path = confirmation_path(runner_id)
    path.write_text(
        json.dumps({"runner": runner_id, "confirmed_alive_at": when,
                    "note": note}, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return path


def check_confirmation(entry: dict, out: dict) -> dict:
    """State the age of the last human check-in. NOT the state of the runner.

    A recorder can die one minute after a confirmation and this reads
    CONFIRMED for the rest of the window. That is stated everywhere it is
    printed, because a reader who mistakes it for liveness is worse off than
    one who was told nothing.
    """
    hours = float(entry.get("confirm_every_hours", 24))
    rec = last_confirmation(entry["id"])
    where = f"on the {out['machine']}"

    if not rec:
        out["state"] = CHECK_IT
        out["why"] = (
            f"Nobody has ever confirmed this is running. It is {where}, and "
            f"nothing on this machine can see it -- no shared drive, no "
            f"heartbeat, and the coordinator makes no network calls. This is "
            f"not monitoring; it is a reminder to go and look."
        )
        out["needs_a_human"] = True
        return out

    try:
        t = datetime.strptime(rec["confirmed_alive_at"][:16], "%Y-%m-%d %H:%M")
    except Exception:
        t = None
    mins = minutes_since(t.timestamp()) if t else 1e9
    out["last_write"] = rec.get("confirmed_alive_at", "?")
    out["age_minutes"] = round(mins, 1)
    note = f" Note: {rec['note']}" if rec.get("note") else ""

    if mins <= hours * 60:
        out["state"] = CONFIRMED
        out["why"] = (
            f"A human confirmed it was running {english_age(mins)}.{note} "
            f"**That is a statement about the past, not monitoring** -- it "
            f"could have stopped since and nothing here would know."
        )
        return out

    out["state"] = CHECK_IT
    out["why"] = (
        f"The last time anyone confirmed this was running was "
        f"{english_age(mins)}, and a check is expected every {int(hours)} "
        f"hours.{note} Nothing on this machine can see it, so this is the only "
        f"signal there is."
    )
    out["needs_a_human"] = True
    return out


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

    if entry.get("monitor") == "confirmation":
        return check_confirmation(entry, out)

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


def watchdog_drift(entries: list[dict]) -> list[str]:
    """Runners the watchdog starts that nothing watches, and vice versa.

    runners/runners.json says WHAT RUNS. This file says HOW TO TELL IT IS
    PRODUCING ANYTHING. They are separate on purpose -- different questions --
    but two lists of the same runners drift, and the record in this repo on
    that is the fee formula reaching 17 copies while its rule was a convention.
    """
    try:
        wd = json.loads(WATCHDOG_REGISTRY.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{rel_to_repo(WATCHDOG_REGISTRY)} is missing. Either the "
                f"shared watchdog was removed, or this is not the machine that "
                f"runs the tests. Nothing below is cross-checked."]
    except Exception as exc:
        return [f"{rel_to_repo(WATCHDOG_REGISTRY)} could not be read "
                f"({exc}). The two registries were NOT cross-checked."]

    enabled = {r["name"] for r in wd.get("runners", []) if r.get("enabled")}
    disabled = {r["name"] for r in wd.get("runners", []) if not r.get("enabled")}
    watched = {e["watchdog_name"] for e in entries if e.get("watchdog_name")}

    out = []
    for name in sorted(enabled - watched):
        out.append(
            f"The watchdog starts '{name}' but nothing in coordinator/"
            f"runners.json checks whether it is producing anything. It would "
            f"be restarted forever while writing nothing, and this page would "
            f"never mention it."
        )
    for name in sorted(watched - enabled):
        why = ("it is present but disabled" if name in disabled
               else "it is not in that file at all")
        out.append(
            f"coordinator/runners.json watches '{name}', but the watchdog will "
            f"not start it -- {why}. After a reboot it stays down, and the row "
            f"here will read STALE with no explanation."
        )
    return out


def check_all() -> dict:
    entries = load()
    rows = [check(e) for e in entries]
    known = set()
    for e in entries:
        known.update(e.get("heartbeat") or [])
        if e.get("lock"):
            known.add(e["lock"])
    return {
        "runners": rows,
        "unregistered": unregistered(known),
        "drift": watchdog_drift(entries),
    }


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
        for chunk in textwrap.wrap(r["why"].replace("**", ""), 68,
                                   initial_indent="      ",
                                   subsequent_indent="      "):
            L.append(chunk)
        if r["state"] in (STALE, CHECK_IT) and r["restart"]:
            for chunk in textwrap.wrap("What to do:  " + r["restart"], 68,
                                       initial_indent="      ",
                                       subsequent_indent="        "):
                L.append(chunk)
        L.append("")
    L.append("  ALIVE means it wrote to its log recently. It does NOT mean the")
    L.append("  numbers coming out of it are right -- nothing here checks that.")
    L.append("")
    L.append("  CONFIRMED means A HUMAN SAID SO, at the time shown. Nothing on")
    L.append("  this machine can see the laptop recorders -- no shared drive,")
    L.append("  no heartbeat, no network call. They can stop one minute after a")
    L.append("  confirmation and this page will not know. See COORDINATOR.md")
    L.append("  section 3b for why that cannot be fixed by editing a config.")

    if result.get("drift"):
        L.append("")
        L.append("  THE TWO RUNNER LISTS DISAGREE:")
        for d in result["drift"]:
            for chunk in textwrap.wrap(d, 68, initial_indent="    - ",
                                       subsequent_indent="      "):
                L.append(chunk)
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


def cmd_confirm(runner_id: str, note: str, when: str | None) -> int:
    entry = next((e for e in load() if e["id"] == runner_id), None)
    if entry is None:
        ids = ", ".join(e["id"] for e in load())
        sys.exit(f"No runner called '{runner_id}'. Known: {ids}")
    if entry.get("monitor") != "confirmation":
        sys.exit(
            f"'{runner_id}' is watched by its log file, not by hand. Confirming "
            f"it would replace a measurement with an opinion. Nothing written."
        )
    stamp = when or f"{datetime.now():%Y-%m-%d %H:%M}"
    path = record_confirmation(runner_id, note, stamp)
    print(f"Recorded: {entry['title']} was confirmed running at {stamp}.")
    if note:
        print(f"Note: {note}")
    print(f"Written to {rel_to_repo(path)}")
    print()
    print("This records that SOMEBODY LOOKED. It does not monitor anything.")
    print(f"The next reminder is in {int(entry.get('confirm_every_hours', 24))} "
          f"hours.")
    return 0


def main() -> int:
    _ascii_safe_console()
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd")
    ap.add_argument("--json", action="store_true")

    c = sub.add_parser("confirm", help="record that a human saw it running")
    c.add_argument("runner_id")
    c.add_argument("--note", default="", help="what you actually saw")
    c.add_argument("--at", default=None, help="YYYY-MM-DD HH:MM, if not now")

    a = ap.parse_args()
    if a.cmd == "confirm":
        return cmd_confirm(a.runner_id, a.note, a.at)
    result = check_all()
    print(json.dumps(result, indent=2) if a.json else render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
