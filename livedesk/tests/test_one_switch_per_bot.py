"""Neither bot's kill switch can silently disable the other.

⚠ WHY. The shared `kalshi_client` had ONE kill switch: a file in
`kalshi-inplay-bot/`. That was fine while livedesk only placed practice orders.
When livedesk moved to production, **the tennis strategy's switch started
blocking baseball**, and the failure looked like "the bot just isn't trading"
rather than like a switch.

The owner's correction to the premise, taken as fact from him:

    "The tennis bot doesn't have an auto mode, and it's not even on. So it's
     not possible for the tennis bot to trade regardless."

So the tennis switch is belt-and-braces. It stays on, and it stops governing
this folder.

**The default is unchanged** -- a client built with no `kill_switch` still
obeys the tennis file, so nothing about that bot moved.

    livedesk\\test.bat
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
CLIENT_DIR = Path(__file__).resolve().parents[2] / "kalshi-inplay-bot"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(CLIENT_DIR))

import killswitch                                        # noqa: E402
from kalshi_client import KalshiClient                   # noqa: E402

TENNIS_SWITCH = CLIENT_DIR / "TRADING_DISABLED"


def _client(switch=None):
    return KalshiClient(demo=False, kill_switch=switch)


def test_the_tennis_switch_no_longer_blocks_baseball(tmp_path):
    """The exact regression. Tennis off, baseball must still be allowed."""
    assert TENNIS_SWITCH.exists(), (
        "this test is meaningless unless the tennis switch is actually on")
    baseball = tmp_path / "TRADING_DISABLED"        # absent = baseball running
    _client(str(baseball))._check_writable()        # must not raise


def test_baseballs_own_switch_still_stops_baseball(tmp_path):
    """And the new switch has to actually work, or this is just a bypass."""
    baseball = tmp_path / "TRADING_DISABLED"
    baseball.write_text("off\n", encoding="utf-8")
    with pytest.raises(PermissionError) as e:
        _client(str(baseball))._check_writable()
    assert str(baseball) in str(e.value), "it must name the file he has to delete"


def test_baseballs_switch_does_not_disable_tennis(tmp_path):
    """The other direction. A client with no kill_switch keeps the tennis
    file, so turning baseball off must leave tennis exactly as it was."""
    baseball = tmp_path / "TRADING_DISABLED"
    baseball.write_text("off\n", encoding="utf-8")
    tennis = _client()                              # default = tennis file
    assert (tennis.kill_switch is None), "the default must not have moved"
    # Tennis is governed by its own file and nothing baseball did.
    if TENNIS_SWITCH.exists():
        with pytest.raises(PermissionError):
            tennis._check_writable()
    else:                                            # pragma: no cover
        tennis._check_writable()


def test_the_default_is_unchanged_for_every_existing_caller(tmp_path):
    """Nothing about the tennis bot moved. Its client, built the old way,
    still points at its own file."""
    c = KalshiClient(demo=False)
    assert c.kill_switch is None
    assert c.KILL_SWITCH.endswith("TRADING_DISABLED")
    assert "kalshi-inplay-bot" in c.KILL_SWITCH.replace("\\", "/")


def test_livedesk_points_its_client_at_its_own_switch():
    """Checked on the source, so it cannot drift back silently."""
    import ast
    src = (SRC / "demo_exec.py").read_text(encoding="utf-8")
    found = False
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "id", "") == "KalshiClient"):
            names = {k.arg for k in node.keywords}
            assert "kill_switch" in names, (
                "livedesk builds the client without its own kill_switch — the "
                "tennis switch would govern baseball again")
            found = True
    assert found, "demo_exec.py never builds a KalshiClient"


def test_livedesks_switch_is_its_own_folder():
    assert killswitch.SWITCH.name == "TRADING_DISABLED"
    assert killswitch.SWITCH.parent.name == "livedesk"
