"""Remove the duplicate deferred entries that stacked up per signal.

    py -3 livedesk\\tools\\clean_duplicate_deferred.py

WHY THEY EXIST. `signals_played()` had been changed so a DEFERRED entry did
not close its signal, on the reasoning that a deferred pick "will be retried".
It is retried -- by the retry loop. But the FRESH-PICK path also runs every
refresh and creates a new entry for any signal not yet played. So both ran, and
the ledger collected three entries each for Miami, San Diego and Atlanta, at
two different stake sizes from different rounds.

Fixed in `ledger.py`; this clears up what the bug already wrote.

**Keeps the NEWEST of each signal**, because that one was sized at the current
stake and the current price. Nothing here was ever placed -- deferred means no
money moved -- so removing the older copies loses nothing.

⚠ CLOSE THE DESK WINDOW FIRST. Its background loop writes this file every
minute and will simply put the duplicates back. The tool checks and tells you.
"""
from __future__ import annotations

import collections
import shutil
import sys
from pathlib import Path

LIVEDESK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVEDESK / "src"))

import ledger as L                                       # noqa: E402


def main() -> None:
    led = L.Ledger()
    backup = led.path.with_suffix(".before-dedupe.json")
    shutil.copy2(led.path, backup)
    print(f"  backup: {backup.name}")
    print()

    by_signal = collections.defaultdict(list)
    for e in led.entries:
        if e.status == "deferred":
            by_signal[e.signal].append(e)

    drop = []
    for signal, group in by_signal.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda x: x.confirmed_utc)
        keep = group[-1]                      # newest: current stake and price
        for e in group[:-1]:
            drop.append(e)
        print(f"  {keep.team[:22]:<22} {len(group)} copies -> keeping the "
              f"newest ({keep.contracts} at {keep.price_c}c, "
              f"${keep.cost_usd:.2f})")

    if not drop:
        print("  no duplicates.")
        return

    before = len(led.entries)
    led.entries = [e for e in led.entries if e not in drop]
    led.save()

    fresh = L.Ledger()
    if len(fresh.entries) != len(led.entries):
        print()
        print("  !! THE CHANGE DID NOT STICK.")
        print("     The desk window is almost certainly still open and writing")
        print("     this file. Close it completely and run this again.")
        sys.exit(1)

    print()
    print(f"  removed {len(drop)} duplicate(s): {before} entries -> "
          f"{len(led.entries)}")
    print("  none of them had any money on it — deferred means never placed.")
    print()


if __name__ == "__main__":
    main()
