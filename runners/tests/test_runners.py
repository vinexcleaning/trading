"""Guards on the shared runner layer.

The watchdog runs unattended on a laptop whose most valuable asset is two
recorders collecting data that cannot be re-pulled at any price. The single
most important property of this code is therefore NEGATIVE: it must not be
able to stop anything.

Run:  py -3 -m pytest runners/tests -q
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
RUNNERS = HERE.parent
ROOT = RUNNERS.parent
REGISTRY = RUNNERS / "runners.json"


def _ps(name: str) -> str:
    """Read a PowerShell file with COMMENTS STRIPPED.

    The first version of this scanned the raw text and failed on watchdog.ps1 --
    because that file's header comment *names* Stop-Process and taskkill while
    explaining that it does neither. A detector that cannot tell code from the
    prose describing it will either be defeated by an allowlist or delete the
    documentation, and both are worse than parsing properly.
    """
    src = (RUNNERS / name).read_text(encoding="utf-8", errors="replace")
    src = re.sub(r"<#.*?#>", "", src, flags=re.S)          # block comments
    src = re.sub(r"(?m)^\s*#.*$", "", src)                 # whole-line comments
    src = re.sub(r"(?m)(?<!`)#[^\"']*$", "", src)          # trailing comments
    return src


# --------------------------------------------------------------------------
# THE ONE THAT MATTERS: the watchdog cannot stop anything
# --------------------------------------------------------------------------

STOPPING = [
    (r"Stop-Process", "PowerShell process kill"),
    (r"\btaskkill\b", "the Windows kill command"),
    (r"\.Kill\(", "a .NET process kill"),
    (r"Stop-ScheduledTask", "stopping a scheduled task"),
    (r"Stop-Service", "stopping a service"),
    (r"Remove-Item\s+.*recorder", "deleting recorder state"),
]


def test_the_watchdog_contains_no_way_to_stop_a_process():
    """A script with no stopping code cannot stop a recorder by mistake.

    This is the whole safety argument for letting it run every ten minutes,
    unattended, on the machine holding the irreplaceable data.
    """
    src = _ps("watchdog.ps1")
    hits = [what for pat, what in STOPPING if re.search(pat, src, re.I)]
    assert not hits, (
        "watchdog.ps1 gained the ability to stop things: " + ", ".join(hits) +
        ". It runs unattended beside two recorders whose data cannot be "
        "re-pulled at any price. Starting is safe because each runner has its "
        "own lock; stopping is not safe and is not needed."
    )


def test_the_status_page_contains_no_way_to_stop_a_process():
    hits = [what for pat, what in STOPPING if re.search(pat, _ps("status.ps1"), re.I)]
    assert not hits, f"status.ps1 must be read-only, found: {hits}"


def test_the_installer_stops_nothing_either():
    """It may create a task. It may not stop a process."""
    src = _ps("install.ps1")
    hits = [what for pat, what in STOPPING if re.search(pat, src, re.I)]
    assert not hits, f"install.ps1 gained stopping code: {hits}"


def test_the_detector_bites(tmp_path):
    """GUARDS #9 - a guard that cannot fail is not a guard."""
    planted = "Get-Process python | Stop-Process -Force\n"
    hits = [what for pat, what in STOPPING if re.search(pat, planted, re.I)]
    assert hits, "the stopping-code detector failed to fire on a literal kill"


def test_uninstall_may_remove_the_task_but_not_kill_runners():
    src = _ps("uninstall.ps1")
    assert "Unregister-ScheduledTask" in src
    hits = [what for pat, what in STOPPING if re.search(pat, src, re.I)]
    assert not hits, (
        "uninstall.ps1 kills processes. Removing the watchdog must not stop the "
        f"tests it was watching, and must never risk a recorder: {hits}")


# --------------------------------------------------------------------------
# The registry has to be usable by a human at 1am
# --------------------------------------------------------------------------

def _cfg() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_registry_parses():
    assert _cfg()["runners"], "no runners registered"


@pytest.mark.parametrize("field", ["name", "enabled", "dir", "exe", "args", "match", "log"])
def test_every_entry_has_the_required_fields(field):
    for r in _cfg()["runners"]:
        assert field in r, f"runner {r.get('name','?')} is missing {field!r}"


def test_match_strings_are_unique_among_enabled_entries():
    """Two entries sharing a match string makes liveness ambiguous: the
    watchdog would see one running, believe both are, and never start the
    second. install.ps1 refuses it; this catches it earlier."""
    ms = [r["match"] for r in _cfg()["runners"] if r["enabled"]]
    assert len(ms) == len(set(ms)), f"duplicate match strings: {ms}"


def test_every_named_folder_exists():
    for r in _cfg()["runners"]:
        assert (ROOT / r["dir"]).is_dir(), f"{r['name']}: no folder {r['dir']}"


def test_a_disabled_entry_says_why():
    for r in _cfg()["runners"]:
        if not r["enabled"]:
            assert r.get("_why_disabled"), (
                f"{r['name']} is disabled with no reason recorded. A silently "
                f"disabled test looks identical to one nobody noticed was off.")


def test_no_credentials_anywhere_in_the_registry():
    raw = REGISTRY.read_text(encoding="utf-8")
    for bad in ("KALSHI_KEY", "API_KEY", "SECRET", "TOKEN", "PRIVATE_KEY", ".pem"):
        assert bad not in raw.upper().replace(".PEM", ".pem"), \
            f"registry mentions {bad}; it must carry no credential of any kind"


def test_the_watchdog_clears_exchange_credentials_before_starting_anything():
    src = _ps("watchdog.ps1")
    assert "KALSHI_KEY_ID" in src and "Remove-Item" in src, (
        "the watchdog no longer clears exchange credentials from the "
        "environment it hands to a paper process")


def test_one_scheduled_task_not_one_per_runner():
    """The whole point of this layer: adding a test is a config line, not a
    new scheduled task."""
    src = _ps("install.ps1")
    assert len(re.findall(r"Register-ScheduledTask", src)) == 1, (
        "install.ps1 registers more than one task. Adding a runner must not "
        "add a task, or the pattern has stopped being reusable.")
