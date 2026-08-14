"""Did every finding actually reach the chat that owns it?

WHY THIS EXISTS. On 2026-08-14 the coordinator asked this chat to file its 47
findings to the owning chats, on the reasonable assumption that they were sitting
in `REOPENED.md` and nowhere else. **38 of the 47 had already been filed days
earlier.** The 9 that had not were one coherent group -- the live-money ledger's
findings, which went to the coordinator and were never routed onward.

Neither of us could have known which without checking, and both of us would have
guessed wrong in opposite directions. **A finding that nobody was told about is
worth exactly as much as one nobody found**, and that is not visible from either
end. So it is measured here instead of remembered.

Nothing is filed by this script. It reports coverage and it exits non-zero when
something is unrouted, so the gap is loud rather than quiet.

READ ONLY. No network.

  py -3 reopen\\src\\check_delivery.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MAILBOX = REPO / "coordinator" / "mailbox"
CSV_PATH = HERE.parent / "reports" / "classification.csv"

# Messages this chat sent carry a signature line in their opening block. The
# mailbox tool stamps every message "From: coordinator" and has no --from flag,
# so the body is the only thing that identifies the sender.
SIGNATURE = "Sent by the `reopen` chat"

# A chat that does not exist cannot be sent to. These are recorded rather than
# silently passed, because "no owner" is a decision with a consequence.
NO_OWNER = {"nobody"}


def sent_messages() -> dict[Path, str]:
    out = {}
    if not MAILBOX.exists():
        return out
    for f in sorted(MAILBOX.rglob("*.md")):
        if f.parent.name == "reopen":       # this chat's own inbox
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if SIGNATURE in text[:1500]:
            out[f] = text
    return out


def main() -> int:
    if not CSV_PATH.exists():
        print(f"no classification at {CSV_PATH} -- run classify_closures.py")
        return 1

    rows = [r for r in csv.DictReader(CSV_PATH.open(encoding="utf-8"))
            if r.get("action")]
    sent = sent_messages()
    print(f"actioned findings   {len(rows)}")
    print(f"messages sent by me {len(sent)}\n")

    filed, misrouted, unfiled, ownerless = [], [], [], []
    for r in rows:
        cid, owner = r["id"], r["owner"]
        # word-boundary match so C01 does not match C011
        pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(cid) + r"(?![A-Za-z0-9])")
        boxes = {f.parent.name for f, t in sent.items() if pat.search(t)}
        if owner in NO_OWNER:
            ownerless.append((cid, boxes))
        elif owner in boxes:
            filed.append(cid)
        elif boxes:
            misrouted.append((cid, owner, sorted(boxes)))
        else:
            unfiled.append((cid, owner))

    print(f"  reached their owner        {len(filed)}")
    print(f"  filed, but NOT to the owner {len(misrouted)}")
    print(f"  never filed anywhere        {len(unfiled)}")
    print(f"  owner is 'nobody'           {len(ownerless)}")

    for cid, owner, boxes in misrouted:
        print(f"\n  MISROUTED {cid}: owner is '{owner}', only sent to {boxes}")
    for cid, owner in unfiled:
        print(f"\n  UNFILED   {cid}: owner is '{owner}', in no message")
    for cid, boxes in ownerless:
        where = sorted(boxes) or ["nowhere"]
        print(f"\n  NO OWNER  {cid}: nobody owns it; mentioned in {where}")

    bad = len(misrouted) + len(unfiled)
    print("\n" + "=" * 62)
    if bad:
        print(f"{bad} finding(s) have not reached the chat that owns them.")
        print("A finding nobody was told about is worth what one nobody found is.")
        return 1
    print("Every finding with an owner has reached that owner.")
    if ownerless:
        print(f"{len(ownerless)} have no owner at all -- that is a decision, "
              f"not a delivery failure, and it is recorded in REOPENED.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
