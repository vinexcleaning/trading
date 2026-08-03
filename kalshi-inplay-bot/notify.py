"""
notify.py — push alerts to your phone when the bot needs you.

An unattended bot that dies quietly is worse than no bot: you believe stops
are being watched when nothing is watching them. This sends a push to your
phone for the events you'd actually want woken up for.

SETUP (2 minutes, free, no account)
    1. Install "ntfy" from the App Store / Play Store.
    2. In the app: Subscribe to a topic. Make up a name nobody could guess,
       e.g.  kalshi-vinnie-7fj29xk
       Topics are PUBLIC to anyone who knows the name, so treat it like a
       password. Never put account details in a message.
    3. On the laptop, tell the bot that name:
           setx KALSHI_NTFY_TOPIC kalshi-vinnie-7fj29xk
       Reopen Command Prompt afterwards.
    4. Test it:
           python notify.py --test

OPTIONAL — a dead-man switch that catches the whole laptop dying
    ntfy tells you when the bot has a problem. It cannot tell you when the bot
    stops existing, because a dead process sends nothing. For that, sign up
    free at healthchecks.io, create a check with a 1-hour period, and:
           setx KALSHI_HEALTHCHECK_URL https://hc-ping.com/your-uuid-here
    The bot pings it every scan. If pings stop for an hour, healthchecks.io
    emails you. That is what catches a power cut, a crash, or dead Wi-Fi.

If neither variable is set, every call here does nothing at all — the bot runs
exactly as before.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Optional

import requests

NTFY_HOST = "https://ntfy.sh"

# Don't send the same alert over and over. Key -> when we last sent it.
_MIN_GAP_SEC = {
    "crash": 300,
    "feed": 900,
    "order": 60,
    "stop": 0,          # every stop is worth knowing about
    "won": 0,           # so is every win
    "milestone": 0,     # already de-duplicated by the caller
    "daily": 3600,
    "info": 300,
}


class Notifier:
    def __init__(self, topic: Optional[str] = None,
                 healthcheck_url: Optional[str] = None):
        self.topic = topic or os.environ.get("KALSHI_NTFY_TOPIC", "")
        self.healthcheck_url = (healthcheck_url
                                or os.environ.get("KALSHI_HEALTHCHECK_URL", ""))
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return bool(self.topic)

    def send(self, message: str, title: str = "Kalshi bot",
             kind: str = "info", priority: str = "default",
             tags: str = "tennis") -> None:
        """Fire and forget. Never raises, never blocks the caller for long —
        a notification failing must not be able to take the bot down."""
        if not self.topic:
            return
        with self._lock:
            gap = _MIN_GAP_SEC.get(kind, 300)
            now = time.time()
            if gap and now - self._last.get(kind, 0.0) < gap:
                return
            self._last[kind] = now

        def worker():
            try:
                requests.post(
                    f"{NTFY_HOST}/{self.topic}",
                    data=message.encode("utf-8"),
                    headers={"Title": title, "Priority": priority, "Tags": tags},
                    timeout=10)
            except Exception:
                pass          # a failed alert is not worth an exception
        threading.Thread(target=worker, daemon=True).start()

    # ---- the events worth waking up for ---------------------------------
    def crashed(self, err: str) -> None:
        self.send(f"The bot hit an error and may have stopped:\n\n{err}\n\n"
                  f"Your positions and resting take-profits are safe on Kalshi, "
                  f"but STOP LOSSES are not being watched until it restarts.",
                  title="Kalshi bot CRASHED", kind="crash",
                  priority="urgent", tags="rotating_light")

    def feed_down(self, detail: str) -> None:
        self.send(f"Live scores have been unavailable: {detail}\n\n"
                  f"No new trades will be entered while the feed is down. "
                  f"Existing stops are still being watched.",
                  title="Score feed down", kind="feed",
                  priority="high", tags="warning")

    def order_problem(self, detail: str) -> None:
        self.send(detail, title="Order problem", kind="order",
                  priority="high", tags="warning")

    def stop_fired(self, detail: str) -> None:
        self.send(detail, title="Stop fired", kind="stop",
                  priority="default", tags="chart_with_downwards_trend")

    def won(self, detail: str) -> None:
        """A take-profit filled. Deliberately NOT sent on entries — those fire
        several times an hour and you'd learn to ignore the app."""
        self.send(detail, title="Target hit", kind="won",
                  priority="default", tags="moneybag")

    def milestone(self, pnl: float, realized: float, unrealized: float) -> None:
        up = pnl >= 0
        self.send(
            f"Session P&L has crossed {'+' if up else '-'}${abs(pnl):.0f}.\n\n"
            f"Realised: ${realized:+.2f}\n"
            f"Open positions: ${unrealized:+.2f}",
            title=f"{'Up' if up else 'Down'} ${abs(pnl):.0f} this session",
            kind="milestone", priority="default",
            tags="chart_with_upwards_trend" if up else "chart_with_downwards_trend")

    def daily_limit(self, pct: float) -> None:
        self.send(f"Down {abs(pct):.1f}% today — the daily loss limit has been "
                  f"hit. No new entries will be taken. Open positions are still "
                  f"managed.",
                  title="Daily loss limit hit", kind="daily",
                  priority="urgent", tags="octagonal_sign")

    # ---- dead-man switch -------------------------------------------------
    def heartbeat(self) -> None:
        """Ping healthchecks.io. If these stop arriving, it alerts you — which
        is the only way to catch the laptop losing power, since a dead process
        cannot send its own alert."""
        if not self.healthcheck_url:
            return

        def worker():
            try:
                requests.get(self.healthcheck_url, timeout=10)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="send a test push")
    a = ap.parse_args()

    n = Notifier()
    print(f"ntfy topic       : {n.topic or '(not set — KALSHI_NTFY_TOPIC)'}")
    print(f"healthcheck url  : {n.healthcheck_url or '(not set — optional)'}")
    if not n.enabled:
        print("\nNothing is configured, so the bot will run silently.")
        print("Set KALSHI_NTFY_TOPIC to get phone alerts. See the top of this file.")
        raise SystemExit(1)
    if a.test:
        n.send("If you can read this on your phone, alerts are working.",
               title="Kalshi bot test", tags="white_check_mark")
        n.heartbeat()
        print("\nSent. Check your phone (allow a few seconds).")
