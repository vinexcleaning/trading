"""The switch he can throw without touching code, at 3am, half asleep.

Copied in mechanism from `kalshi-inplay-bot/kalshi_client.py`, which is the
app he already uses and already trusts: a file in the project folder, checked
every time, no restart, no flag, no code change.

    create  livedesk/TRADING_DISABLED   -> the button is dead
    delete  it                          -> the button works again

Fail closed. If the file is there, the button is dead whatever anything else
in this window believes.

The difference from the tennis bot is worth writing down: THERE the switch
stopped a real order going to Kalshi. HERE nothing can send an order at all --
this window has no key and no order code, and `tests/test_paper_only.py`
fails the build if any appears. So the switch stops the window from telling
him to place one. That is a smaller thing, and it is still the right thing:
one file, and the tool stops recommending trades.
"""
from __future__ import annotations

from pathlib import Path

SWITCH = Path(__file__).resolve().parents[1] / "TRADING_DISABLED"


def disabled() -> bool:
    return SWITCH.exists()


def reason() -> str:
    if not SWITCH.exists():
        return ""
    try:
        head = SWITCH.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        head = ""
    first = head.splitlines()[0] if head else ""
    return (f"TURNED OFF — the file TRADING_DISABLED is in the livedesk "
            f"folder. Delete it to turn this back on."
            + (f"  ({first})" if first else ""))
