"""Put `data/ledger.json` back after the test suite wiped it, then re-repair.

⚠ WHAT HAPPENED, 2026-08-16 17:28 UTC. Running the test suite DELETED every
entry from his real ledger.

`tests/test_button_never_moves.py` sets `ledger.LEDGER_PATH` to a temp file
before constructing the window. That never worked:

    class Ledger:
        def __init__(self, path: Path = LEDGER_PATH):

**A default argument is bound once, when the function is defined.** Reassigning
the module global afterwards does nothing, so `Desk()` opened the REAL ledger,
and the per-test fixture then did `entries.clear()` and `save()` on it.

The bug is mine -- I wrote that fixture -- and it survived 150 passing tests
because nothing ever asserted where the tests were writing.

Fixed in `ledger.py` by resolving the path at CALL time, with a test that the
real ledger file is never touched during a run.

    py -3 livedesk\\tools\\restore_006.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
LEDGER = DATA / "ledger.json"
BACKUP = DATA / "ledger.before-repair-006.json"


def main() -> None:
    if not BACKUP.exists():
        raise SystemExit(f"no backup at {BACKUP}")
    now = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}
    if now.get("entries"):
        raise SystemExit(
            f"{LEDGER.name} already holds {len(now['entries'])} entries — "
            f"refusing to overwrite a ledger that is not empty.")
    shutil.copy2(BACKUP, LEDGER)
    back = json.loads(LEDGER.read_text(encoding="utf-8"))
    print(f"restored {len(back['entries'])} entries from {BACKUP.name}")
    print("now re-run: py -3 livedesk\\tools\\repair_006.py")


if __name__ == "__main__":
    main()
