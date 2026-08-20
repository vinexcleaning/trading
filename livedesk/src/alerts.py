"""Phone alerts for the baseball desk.

    py -3 livedesk\\src\\alerts.py             # print today's message, send nothing
    py -3 livedesk\\src\\alerts.py --test      # actually send it to his phone

WHAT THIS FILE CAN DO: read the ledger, and send text.
WHAT IT CANNOT DO: write the ledger, place a bet, cancel a bet, touch a guard.

**If every line of it failed, the desk would trade exactly as it does now.**
That is the only acceptable shape for something bolted onto a path that spends
real money, and `tests/test_alerts.py` holds it to that.

# IT REUSES THE NOTIFIER, IT DOES NOT REWRITE IT

`kalshi-inplay-bot/notify.py` already does ntfy and already does the
healthchecks.io ping, and CLAUDE.md §6 says use the existing one rather than
writing a second. This imports that class off `sys.path` exactly the way
`demo_exec.py` imports `kalshi_client` from the same folder. **Nothing here
re-implements sending.** What is added is baseball-shaped: the daily summary,
the once-a-day scheduling, and telling him on screen when it is not working.

# WHY THERE ARE TWO SERVICES AND NOT ONE

**ntfy cannot tell him the desk has died.** A crashed process and a laptop with
no power both send exactly nothing, which on his phone is indistinguishable
from a quiet day with no bets. That is the failure he asked to be protected
from -- *"tell me if the bot turns off"* -- and it is the one ntfy structurally
cannot cover, because the thing that would have to send the message is the
thing that stopped.

**healthchecks.io is the second service, and it is free.** The desk pings a URL
every refresh. If those pings stop for an hour, healthchecks.io emails him. It
watches from OUTSIDE the machine, which is the entire point: nothing running on
the laptop can report that the laptop is off.

Two consequences, and both are told to him rather than only written here:

  * **The summary is sent EVERY day, including days with no bets at all.** "No
    bets today" and silence are different messages, and only one of them also
    means the desk is alive.
  * **So silence means something is wrong**, and he can be told that plainly,
    because with a summary every day it is finally true.
"""
from __future__ import annotations

import json
import os
import socket
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVEDESK = HERE.parent
STATE_PATH = LIVEDESK / "data" / "alerts_state.json"
CLIENT_DIR = LIVEDESK.parent / "kalshi-inplay-bot"

#: Local hour to send the daily summary. 22:00 -- late enough that most night
#: games have settled, early enough that he is still awake to read it.
SUMMARY_HOUR = 22


def _notifier():
    """The Notifier from kalshi-inplay-bot. Returns None rather than raising --
    a missing notifier must degrade to a silent desk, never to a broken one."""
    try:
        if str(CLIENT_DIR) not in sys.path:
            sys.path.insert(0, str(CLIENT_DIR))
        from notify import Notifier
        return Notifier()
    except Exception:
        return None


def machine_name() -> str:
    """What this computer calls itself. Shown to him, never keyed on."""
    try:
        return socket.gethostname() or "unknown-computer"
    except Exception:
        return "unknown-computer"


# --------------------------------------------------------------- the message

def summary_text(ledger, day=None) -> str:
    """The four things he listed, in his order, money AND percent.

        Baseball desk - 19 Aug
        5 bets placed today
        up $12.40 for the day (3 won, 2 lost)
        that is $108 back for every $100 staked
        3 still running, $14.80 riding on them

    ⚠ THE PERCENT IS SPELLED OUT AS MONEY RATHER THAN WRITTEN AS A PERCENTAGE.
    "up 8%" is ambiguous between 8% of what he staked and 8% of his account,
    and those are wildly different numbers. This tool has already shown him one
    misleading percentage -- the stake label said "10% of your balance" while
    the card underneath was sized at 5%.
    """
    s = ledger.day_summary(day)
    d = s["day"]
    lines = [f"Baseball desk - {d.day} {d:%b}"]

    lines.append("no bets placed today" if not s["placed"] else
                 f"{s['placed']} bet{'' if s['placed'] == 1 else 's'} "
                 f"placed today")

    if not (s["won"] + s["lost"]):
        lines.append("nothing has finished yet, so no result for the day")
    else:
        m = s["money"]
        lines.append(f"{'up' if m >= 0 else 'down'} ${abs(m):.2f} for the day "
                     f"({s['won']} won, {s['lost']} lost)")
        lines.append(f"that is ${100.0 + s['pct']:.0f} back for every "
                     f"$100 staked")

    lines.append(f"{s['running']} still running, ${s['at_risk']:.2f} riding "
                 f"on them" if s["running"] else "nothing still running")

    if s["unreadable"]:
        lines.append(f"WARNING: {s['unreadable']} bet(s) had an unreadable "
                     f"date and are missing from these numbers")
    return "\n".join(lines)


# ------------------------------------------------------------- the scheduler

def _state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(d: dict) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")
    except Exception:
        pass


class DeskAlerts:
    """Call `tick(ledger)` once per refresh. It does the right thing or nothing.

    ⚠ IT NEVER RAISES INTO THE DESK. A notification failing must not be able to
    stop a bet being placed or a guard being checked. Every path is wrapped,
    and `last_error` keeps what went wrong so it can be shown rather than
    swallowed -- a notifier that has silently stopped working is worse than no
    notifier, because he reads silence as good news.
    """

    def __init__(self, notifier=None, hour: int = SUMMARY_HOUR,
                 state_path=None):
        self.n = notifier if notifier is not None else _notifier()
        self.hour = hour
        self.state_path = Path(state_path) if state_path else STATE_PATH
        self.last_error = ""
        self.sent_today = self._read().get("summary_sent_for", "")

    # state is read through these two so tests never touch his real file
    def _read(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, d: dict) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps(d, indent=2),
                                       encoding="utf-8")
        except Exception:
            pass

    @property
    def enabled(self) -> bool:
        return bool(self.n and getattr(self.n, "enabled", False))

    @property
    def watching(self) -> bool:
        """True only if something OUTSIDE this machine would notice it dying."""
        return bool(self.n and getattr(self.n, "healthcheck_url", ""))

    def tick(self, ledger, now=None) -> str:
        """Heartbeat every refresh; the summary once, after the hour."""
        did = []
        try:
            if self.n:
                self.n.heartbeat()
        except Exception as exc:
            self.last_error = f"heartbeat: {exc}"
        try:
            now = now or datetime.now().astimezone()
            today = now.date().isoformat()
            if now.hour >= self.hour and self.sent_today != today:
                if self.send_summary(ledger, now.date()):
                    self.sent_today = today
                    st = self._read()
                    st["summary_sent_for"] = today
                    self._save(st)
                    did.append("sent the daily summary to your phone")
        except Exception as exc:
            self.last_error = f"summary: {exc}"
        return "; ".join(did)

    def send_summary(self, ledger, day=None) -> bool:
        if not self.enabled:
            return False
        try:
            self.n.send(summary_text(ledger, day), title="Baseball desk",
                        kind="daily", tags="baseball")
            return True
        except Exception as exc:
            self.last_error = f"send: {exc}"
            return False

    def say(self, message: str, title: str = "Baseball desk",
            urgent: bool = False) -> bool:
        """One-off, for the things worth interrupting him for: the desk
        pausing at the floor, an order refused, the ledger disagreeing."""
        if not self.enabled:
            return False
        try:
            self.n.send(message, title=title, kind="order",
                        priority="urgent" if urgent else "default",
                        tags="warning" if urgent else "baseball")
            return True
        except Exception as exc:
            self.last_error = f"say: {exc}"
            return False

    def status_line(self) -> str:
        """On the window, because a notifier he THINKS is on and is not is
        worse than none -- he would read silence as good news."""
        if not self.enabled:
            return ("phone alerts OFF -- silence tells you nothing, and you "
                    "will NOT be told if this stops")
        if not self.watching:
            return ("phone alerts on, but NOTHING WATCHES FOR THIS DYING -- "
                    "set KALSHI_HEALTHCHECK_URL")
        return (f"phone alerts on | summary every day at {self.hour}:00 | "
                f"death-watch on")


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    from ledger import Ledger

    lg = Ledger()
    lg.load()
    a = DeskAlerts()
    print()
    print("  " + a.status_line())
    print()
    print("  ---- what would go to your phone tonight ----")
    for line in summary_text(lg).splitlines():
        print("    " + line)
    print("  ---------------------------------------------")
    print()
    if "--test" in sys.argv:
        print("  sent to your phone." if a.send_summary(lg) else
              f"  NOT sent: {a.last_error or 'no ntfy topic set'}")
    else:
        print("  Nothing was sent. Add --test to send it to your phone.")
    print()
