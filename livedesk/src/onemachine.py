"""Stop the desk running in two places at once.

    py -3 livedesk\\src\\onemachine.py       # who currently claims the desk

# WHY THIS EXISTS

He is moving the desk to the laptop so it stops stealing focus mid-game. The
laptop stays on; the desktop is where he works. **The one move that can cost him
real money is leaving it running on both**, because the two machines cannot see
each other and would both act on the same signal and the same position. Nothing
in the betting code can notice.

`kalshi-inplay-bot/MOVING_TO_LAPTOP.md` warns about this in a red box. A warning
in a document is not a guard, and he will not have the document open at the
moment it matters.

# ⚠ WHAT I WAS ASKED TO BUILD, AND WHY I BUILT SOMETHING ELSE

Mailbox 017 suggested: *"have the desk refuse to start if the account already
holds a position it has no local entry for and cannot explain."*

**That would recreate the defect that cost eleven bets.** He trades manually and
always will -- he has said so twice, and the old Guard 4 assumed otherwise,
compared the ledger against his whole account, could never agree, and ate every
signal for days. A rule keyed on "a position we cannot explain" refuses to start
every single time he has a bet of his own open, which is most days. **It would
be off within a week and he would be unprotected and think he was not.**

So the claim is carried explicitly instead of inferred from his money.

# THE TWO MECHANISMS, AND WHAT EACH ONE MISSES

**1. A LOCK FILE, on this machine.** `data/desk.lock` carries a machine name, a
process id and a timestamp, rewritten every refresh. A second window on the SAME
computer sees a fresh lock and refuses.

    catches:  two windows open on one machine -- which has happened, and is the
              more likely of the two mistakes because it needs no travel
    misses:   the other machine entirely. A file on the desktop is invisible to
              the laptop.

**2. A CLAIM POSTED TO NTFY**, on a topic he does not subscribe to
(`<his topic>-deskclaim`, priority `min`, so it never reaches his phone). Both
machines can already reach ntfy -- it is how his alerts work -- which makes it
the only channel the two computers genuinely share. Each desk posts its name
every refresh and reads the last five minutes before starting.

    catches:  the real thing. Desktop running, laptop started -> laptop refuses
              and names the machine holding it
    misses:   both started inside the same few seconds, before either has
              posted; and anything at all if his internet is down

# ⚠ IT BLOCKS ON EVIDENCE, NOT ON THE ABSENCE OF EVIDENCE

If ntfy cannot be reached, this **allows** the desk to start. That is deliberate
and it is the one place a guard should be lenient: a bad connection is common
and a second machine is rare, so failing shut would mean no internet equals no
desk, and he would work around it -- which leaves him with no guard at all
rather than a partial one.

**A guard he turns off protects nothing.** So it blocks only when it has
positive evidence of another desk, and says out loud when it could not check.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVEDESK = HERE.parent
LOCK_PATH = LIVEDESK / "data" / "desk.lock"
CLIENT_DIR = LIVEDESK.parent / "kalshi-inplay-bot"

#: How stale a claim may be before we stop believing that desk is alive. The
#: window refreshes every 60 seconds, so five minutes is four missed beats --
#: long enough to survive a slow network, short enough that closing the window
#: on one machine frees the other within a few minutes rather than an hour.
STALE_SEC = 300.0

_HOST = "https://ntfy.sh"

#: Every claim carries this. ⚠ FOUND BY RUNNING IT, not by a test: a stray
#: message on that topic was read as a machine name, and the desk refused to
#: start because a debug probe reading "probe-from-livedesk" looked like a
#: computer holding the lock. The topic is PUBLIC to anyone who knows it, so
#: anything not in this exact shape is now ignored.
_TAG = "livedesk-claim-v1:"


def _me() -> str:
    try:
        import socket
        return socket.gethostname() or "unknown-computer"
    except Exception:
        return "unknown-computer"


def _topic() -> str:
    """The claim topic. Deliberately NOT the one his phone is subscribed to --
    a startup claim every 60 seconds would train him to ignore the app."""
    base = os.environ.get("KALSHI_NTFY_TOPIC", "").strip()
    return f"{base}-deskclaim" if base else ""


# ------------------------------------------------------------- the lock file

def read_lock(path=None) -> dict:
    try:
        return json.loads(Path(path or LOCK_PATH).read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_lock(path=None, now=None) -> None:
    """Rewritten every refresh. The timestamp is what makes it a heartbeat
    rather than a file somebody has to remember to delete -- a crashed desk
    leaves a stale lock, and a stale lock must not block him for ever."""
    p = Path(path or LOCK_PATH)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"machine": _me(), "pid": os.getpid(),
                                 "at": now if now is not None else time.time()},
                                indent=2), encoding="utf-8")
    except Exception:
        pass


def clear_lock(path=None) -> None:
    try:
        Path(path or LOCK_PATH).unlink()
    except Exception:
        pass


def local_holder(path=None, now=None) -> dict:
    """The OTHER live window on this machine, or {}. Our own pid never counts
    -- otherwise the desk would refuse to start because of itself, which is
    exactly the shape of bug that made the practice button unclickable."""
    d = read_lock(path)
    if not d:
        return {}
    if d.get("pid") == os.getpid():
        return {}
    age = (now if now is not None else time.time()) - float(d.get("at") or 0)
    return d if age < STALE_SEC else {}


# ------------------------------------------------------ the cross-machine claim

def post_claim(topic=None, timeout=6.0) -> bool:
    """Say we are alive. Never raises; a failed claim is not worth a crash.

    ⚠ IT SENDS THROUGH `kalshi-inplay-bot/notify.py` AND DOES NOT POST DIRECTLY,
    and that is not tidiness. `tests/test_paper_only.py` fails the build on any
    non-GET HTTP verb outside `demo_exec.py`, and it fired on the first version
    of this function. **The canary was right and I was wrong to want an
    exception to it.** A POST to ntfy is harmless today; a filename-shaped hole
    in that check would be there the next time somebody adds a POST to this
    file, and the whole value of the rule is that it has no exceptions.

    A FRESH `Notifier` EACH TIME, deliberately. Its throttle is per-instance and
    the default gap is five minutes -- reusing one would silently drop four of
    every five claims, and `STALE_SEC` is five minutes, so the other machine
    would flicker in and out of existence.
    """
    t = topic if topic is not None else _topic()
    if not t:
        return False
    try:
        if str(CLIENT_DIR) not in sys.path:
            sys.path.insert(0, str(CLIENT_DIR))
        from notify import Notifier
        Notifier(topic=t).send(_TAG + _me(), title="desk", kind="info",
                               priority="min", tags="lock")
        return True
    except Exception:
        return False


def read_claims(topic=None, timeout=8.0):
    """(claims, could_check). `could_check` is False when ntfy was unreachable,
    and the caller MUST distinguish that from an empty list -- 'nobody else is
    running' and 'I could not find out' are different answers, and treating
    them the same is how a live position got voided on 2026-08-16."""
    t = topic if topic is not None else _topic()
    if not t:
        return [], False
    try:
        import requests
        # ⚠ TWO ATTEMPTS. The very first live run polled twice a second apart
        # and got a failure then a success -- so a single poll spuriously
        # reporting "could not check" is real, and that answer weakens the
        # guard to nothing. One retry, then believe it.
        r = None
        for _ in range(2):
            try:
                r = requests.get(f"{_HOST}/{t}/json?poll=1&since=10m",
                                 timeout=timeout)
                break
            except Exception:
                r = None
        if r is None:
            return [], False
        out = []
        for line in r.text.strip().splitlines():
            if not line.strip():
                continue
            m = json.loads(line)
            if m.get("event") != "message":
                continue
            body = (m.get("message") or "").strip()
            if not body.startswith(_TAG):
                continue
            out.append({"machine": body[len(_TAG):].strip(),
                        "at": float(m.get("time") or 0)})
        return out, True
    except Exception:
        return [], False


def remote_holder(topic=None, now=None):
    """(machine_name_or_None, could_check)."""
    claims, ok = read_claims(topic)
    if not ok:
        return None, False
    now = now if now is not None else time.time()
    mine = _me()
    fresh = [c for c in claims
             if c["machine"] and c["machine"] != mine
             and now - c["at"] < STALE_SEC]
    if not fresh:
        return None, True
    return max(fresh, key=lambda c: c["at"])["machine"], True


# ------------------------------------------------------------------ the answer

def may_start(lock_path=None, topic=None, now=None):
    """(ok, message). Call once before the window opens.

    Blocks only on positive evidence. `ok=True` with a message means it ran but
    could not check the other machine, and the message says so -- because a
    guard that quietly did nothing reads on screen exactly like a guard that
    passed.
    """
    other = local_holder(lock_path, now)
    if other:
        return False, (
            f"The baseball desk is ALREADY OPEN on this computer "
            f"(started as process {other.get('pid')}). Close that window "
            f"first. Two of them would both place the same bet.")

    who, checked = remote_holder(topic, now)
    if who:
        return False, (
            f"The baseball desk is ALREADY RUNNING on \"{who}\". Close it "
            f"there before opening it here. If both run, both place the same "
            f"bet and both act on the same position, and neither can see the "
            f"other.")
    if not checked:
        return True, (
            "COULD NOT CHECK the other computer (no internet, or no alert "
            "topic set). Starting anyway -- but make sure the desk is CLOSED "
            "on the other machine yourself.")
    return True, ""


def heartbeat(lock_path=None, topic=None) -> None:
    """Call every refresh. Keeps both claims fresh."""
    write_lock(lock_path)
    post_claim(topic)


def real_paths():
    """Everything on disk this module can write, for the canary that checks a
    test run left his real files alone."""
    return (LOCK_PATH,)


if __name__ == "__main__":
    print()
    print(f"  this computer : {_me()}")
    t = _topic()
    print(f"  claim channel : {'set' if t else 'NOT SET (no cross-machine check)'}")
    d = read_lock()
    if d:
        age = time.time() - float(d.get("at") or 0)
        print(f"  lock file     : {d.get('machine')} pid {d.get('pid')}, "
              f"{age / 60:.1f} min old"
              + ("  (stale, ignored)" if age >= STALE_SEC else "  (LIVE)"))
    else:
        print("  lock file     : none")
    who, checked = remote_holder()
    print(f"  other machine : "
          + (f"{who} IS RUNNING IT" if who
             else "none running it" if checked else "could not check"))
    ok, msg = may_start()
    print()
    print(f"  may this machine start?  {'YES' if ok else 'NO'}")
    if msg:
        print(f"  {msg}")
    print()
