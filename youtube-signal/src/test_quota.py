"""Prove the quota halt fires. Uses a scratch DB so the real ledger is untouched."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quota  # noqa: E402

db = Path(tempfile.mkdtemp()) / "scratch.db"
con = quota.connect(db)

# 94 searches = 9,400 units, just under the 9,500 halt.
for i in range(94):
    quota.charge(con, "search.list", phase="test", detail=f"query {i}")
print(f"after 94 search.list calls: {quota.spent(con)} units")

quota.charge(con, "videos.list", phase="test", detail="cheap call")
print(f"after 1 videos.list call  : {quota.spent(con)} units")

try:
    quota.charge(con, "search.list", phase="test", detail="the one that should halt")
    print("FAIL -- no halt raised")
except quota.QuotaExceeded as exc:
    print("\nHALT FIRED:")
    print(" ", exc)

print(f"\nspend after the refused call: {quota.spent(con)} units (must be unchanged)")

try:
    quota.charge(con, "captions.download")
    print("FAIL -- unknown endpoint accepted")
except ValueError as exc:
    print(f"unknown endpoint rejected: {exc}")

print()
print(quota.report(con))
con.close()
