"""Dump every claim row in every ledger to one flat file, so the closures can be
read in one pass.

This chat audits closures. It cannot audit what it cannot see, and the claims
live in three files with different table shapes. `coordinator/ledger.py` already
solves the parsing, so this imports it rather than writing a second parser --
the fee formula reached 17 copies while its rule was a convention, and a second
ledger parser would drift the same way.

READ ONLY. Writes nothing outside reopen/.

  py -3 reopen\\src\\dump_claims.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "coordinator"))

import ledger  # noqa: E402

OUT_DIR = HERE.parent / "reports"

# The retraction summary at the top of LEDGER.md repeats rows that also appear
# in their project's own table. Both copies are real text a reader can land on,
# so both are dumped -- but the dedupe key is printed so the audit counts
# CLAIMS, not table rows.
FIELDS = ["id", "status", "project", "section", "source_file", "claim", "why",
          "n_unit", "date_range", "effect_ci", "fdr", "holdout", "artifact"]


def main() -> int:
    rows, files, missing = ledger.all_rows()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    seen: dict[str, int] = {}
    out = []
    for r in rows:
        rid = (r.get("_id") or "").strip()
        seen[rid] = seen.get(rid, 0) + 1
        out.append({
            "id": rid,
            "status": ledger.status_of(r),
            "project": ledger.project_of(r),
            "section": r.get("_section", ""),
            "source_file": r.get("_file", ""),
            "claim": ledger.claim_of(r),
            "why": ledger.why_of(r),
            "n_unit": ledger.plain(r.get("n_unit", "")),
            "date_range": ledger.plain(r.get("date_range", "")),
            "effect_ci": ledger.plain(r.get("effect_ci", "")),
            "fdr": ledger.plain(r.get("fdr", "")),
            "holdout": ledger.plain(r.get("holdout", "")),
            "artifact": ledger.plain(r.get("artifact", "")),
        })

    csv_path = OUT_DIR / "all_claims.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)

    txt_path = OUT_DIR / "all_claims.txt"
    with txt_path.open("w", encoding="utf-8") as fh:
        fh.write("FILES READ\n")
        for f in files:
            fh.write(f"  {f}\n")
        if missing:
            fh.write(f"MISSING: {missing}\n")
        fh.write(f"\nTABLE ROWS: {len(out)}\n")
        dupes = {k: v for k, v in seen.items() if v > 1}
        fh.write(f"DISTINCT IDS: {len(seen)}\n")
        fh.write(f"IDS APPEARING MORE THAN ONCE: {sorted(dupes)}\n\n")
        for r in out:
            fh.write("=" * 78 + "\n")
            for k in FIELDS:
                v = (r.get(k) or "").strip()
                if v:
                    fh.write(f"{k:12s}: {v}\n")
            fh.write("\n")

    print(f"wrote {csv_path}")
    print(f"wrote {txt_path}")
    print(f"table rows {len(out)}  distinct ids {len(seen)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
