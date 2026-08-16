"""One-off repair of `data/ledger.json`, mailbox 006 Job 1.

Kept in the repo rather than run from a shell, because it edits the record of
his money and that edit should be reviewable afterwards.

WHAT WENT WRONG
    Guard 4 compared this tool's ledger against his WHOLE Kalshi balance. He
    trades manually, so the two can never agree -- every entry's note says the
    same thing:

        auto-exec deferred: THESE DO NOT AGREE by +$29.53. Your balance says
        $100.00; this tool expects $70.47 (started $83.00, ...)

    So every signal deferred, waited, and died at first pitch. 11 expired
    unplaced before this ran.

WHAT THIS DOES
    1. account_start_usd and peak_total_usd 83.00 -> 106.00. Both were left at
       the figure from the day the tool was built.
    2. Deferred entries whose game has NOT started: DELETED.
    3. Deferred entries whose game HAS started: marked expired, because they
       can no longer be placed.

WHY DELETE RATHER THAN VOID, WHICH LOOKS GENTLER
    No money was ever placed against them, so there is nothing to record. And
    **8 of these signals appear more than once**, while two voids on one signal
    closes it for good (`MAX_VOIDS_BEFORE_CLOSED`). Voiding would therefore
    have destroyed exactly the bets this is meant to give back. Deleting
    reopens the signal so it re-prices and re-qualifies normally.

    A backup is written next to the ledger before anything is changed.

    py -3 livedesk\\tools\\repair_006.py
"""
from __future__ import annotations

import collections
import datetime
import json
import shutil
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[1] / "data" / "ledger.json"
NEW_START_USD = 106.00


def main() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    data = json.loads(LEDGER.read_text(encoding="utf-8"))

    backup = LEDGER.with_suffix(".before-repair-006.json")
    shutil.copy2(LEDGER, backup)
    print(f"backup written: {backup.name}")

    before = collections.Counter(e["status"] for e in data["entries"])
    old_start = data.get("account_start_usd")
    data["account_start_usd"] = NEW_START_USD
    data["peak_total_usd"] = NEW_START_USD

    kept, deleted, expired_now = [], 0, 0
    for e in data["entries"]:
        if e["status"] != "deferred":
            kept.append(e)
            continue
        starts = datetime.datetime.fromisoformat(
            e["starts_utc"].replace("Z", "+00:00"))
        if starts > now:
            deleted += 1                      # signal reopens
        else:
            e["status"] = "expired"
            e["note"] = (e.get("note", "")
                         + " | first pitch passed while deferred").strip(" |")
            kept.append(e)
            expired_now += 1
    data["entries"] = kept
    LEDGER.write_text(json.dumps(data, indent=1), encoding="utf-8")

    after = collections.Counter(e["status"] for e in data["entries"])
    print(f"account_start_usd {old_start} -> {NEW_START_USD}")
    print(f"peak_total_usd    -> {NEW_START_USD}")
    print(f"deferred deleted (game not started, no money, signal reopened): "
          f"{deleted}")
    print(f"deferred -> expired (first pitch already passed): {expired_now}")
    print(f"before: {dict(before)}")
    print(f"after : {dict(after)}")


if __name__ == "__main__":
    main()
