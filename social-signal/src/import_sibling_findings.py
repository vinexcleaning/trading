"""Fold in the hand-researched verdicts a sibling wrote but never loaded.

`youtube-signal/src/tool_reputation.py` carries eight tool verdicts researched by
hand, each with its sources: that Polymarket archived both V1 CLOB clients, that
a Telegram copy-trading bot named in a video is spelled differently from the
transcript and has a documented security history, that a widely-recommended
agent runtime ships with a 20-30% failure rate its promoters do not mention.

**None of it is in any database on this machine.** The `tools` table in
`signal.db` has no `reputation` column at all, so that module has never been
run here. The findings exist only as a Python dict inside a file nobody imports.
That is a real failure mode for a multi-project programme and it is the same
shape as the one `LEDGER.md` records under K015/W011: *a claim that travels
between projects gets a fresh status each time, and the weakest status is the
one a reader happens to find.*

This module reads that dict — it does not modify the sibling's database, which
belongs to another session — and records each verdict as an observation here,
attributed to its author.

Note the rename: the sibling's own `rename_from` field records that the
transcript said "Creo" and the product is "Kreo". This project's entity table
still says Creo, because it was built from the raw tool rows. The rename is
applied here rather than left as two entities for one product.
"""
from __future__ import annotations

import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import norm  # noqa: E402

TRADING = os.path.dirname(db.ROOT)
SIBLING = os.path.join(TRADING, "youtube-signal", "src", "tool_reputation.py")

# The sibling's four verdicts map onto this project's stance vocabulary. The
# mapping is deliberately lossy in one direction only: NO_FOOTPRINT stays
# NO_FOOTPRINT and never becomes anything positive.
STANCE = {
    "NEGATIVE": "CRITICISED",
    "MIXED": "MIXED_REPUTATION",
    "POSITIVE": "CORROBORATED",
    "NO_FOOTPRINT": "NO_FOOTPRINT",
}


def load_findings():
    """Import the sibling module without executing its `main()`.

    It imports `db` and `db_phase2` from its own package at module scope, so
    the sibling's `src` directory goes on the path first and this project's
    `db` is shadowed for the duration. Restored immediately after.
    """
    if not os.path.exists(SIBLING):
        return {}
    sib_dir = os.path.dirname(SIBLING)
    saved_path = list(sys.path)
    saved_db = sys.modules.pop("db", None)
    sys.path.insert(0, sib_dir)
    try:
        spec = importlib.util.spec_from_file_location("_sibling_toolrep", SIBLING)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return dict(getattr(mod, "FINDINGS", {}))
    except Exception as e:  # noqa: BLE001 — a sibling that will not import is a finding
        print(f"  could not import sibling module: {type(e).__name__}: {e}")
        return {}
    finally:
        sys.path[:] = saved_path
        sys.modules.pop("_sibling_toolrep", None)
        if saved_db is not None:
            sys.modules["db"] = saved_db


def main():
    con = db.connect()
    con.execute("DELETE FROM observations WHERE platform='sibling_research'")
    con.commit()

    findings = load_findings()
    print(f"  {len(findings)} hand-researched verdicts in the sibling module")
    if not findings:
        con.close()
        return

    renamed = 0
    for name, f in findings.items():
        old = f.get("rename_from")
        if old:
            # One product, one entity. The transcript's spelling and the
            # product's spelling are the same thing and must not both hold a row.
            row = con.execute("SELECT entity_id FROM entities WHERE key=?",
                              (norm.key(old),)).fetchone()
            if row:
                con.execute("UPDATE entities SET display=?, key=?, compact_key=? "
                            "WHERE entity_id=?",
                            (name, norm.key(name), norm.compact(name),
                             row["entity_id"]))
                renamed += 1
                print(f"  renamed: {old!r} -> {name!r} "
                      "(auto-captions garble product names)")

        eid = db.upsert_entity(con, norm.key(name), norm.compact(name), name)
        stance = STANCE.get(f["reputation"], "UNKNOWN")
        db.add_observation(
            con, eid, "sibling_research", "youtube-signal/tool_reputation.py",
            f["reputation"], stance, strength=float(len(f.get("sources") or [])),
            detail=(f["detail"][:600] +
                    (f"  NOTE: {f['note'][:200]}" if f.get("note") else "")),
            evidence="; ".join(f.get("sources") or [])[:400])
        print(f"  {f['reputation']:<13} {name[:60]}")
    con.commit()

    out = os.path.join(db.REPORTS, "T1c_sibling_findings.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Hand-researched verdicts imported from youtube-signal\n\n")
        fh.write(f"{len(findings)} verdicts from "
                 "`youtube-signal/src/tool_reputation.py`, which **has never "
                 "been run on this machine** — `signal.db`'s `tools` table has "
                 "no `reputation` column, so the research existed only as a "
                 "Python dict in a file nobody imports.\n\n")
        fh.write("`NO_FOOTPRINT` is never `POSITIVE`. The two are stored as "
                 "different values so an aggregation cannot merge them.\n\n")
        fh.write("| tool | verdict | sources | note |\n|---|---|---|---|\n")
        for name, f in findings.items():
            fh.write(f"| {name} | **{f['reputation']}** | "
                     f"{len(f.get('sources') or [])} | "
                     f"{(f.get('note') or f['detail'])[:200]} |\n")
        fh.write(f"\n{renamed} entity renamed from a garbled transcript "
                 "spelling.\n")
    print(f"  wrote {out}")
    db.log(con, "import_sibling_findings",
           f"verdicts={len(findings)} renamed={renamed}")
    con.close()


if __name__ == "__main__":
    main()
