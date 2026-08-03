"""Reputation verification: does anyone INDEPENDENT vouch for this tool?

verify_tools.py only proves a URL responds. That is necessary and nowhere near
sufficient. A live site with a referral link is not evidence of a scam, and a
polished landing page is not evidence of safety. This layer asks a different
question: what does the internet say about it that the vendor did not write?

Four verdicts, and the fourth is the one people collapse by mistake:

  POSITIVE      independent corroboration from a source that is not the vendor
  MIXED         real product, real criticism
  NEGATIVE      documented complaints, scam reports, dead product
  NO_FOOTPRINT  nothing found

NO_FOOTPRINT IS NOT POSITIVE. Absence of complaints about a small tool is absence
of evidence, not a clean bill of health. They are stored as different values and
must never be merged.

Promotional coverage does not count as corroboration. Medium posts by crypto
accounts, "review" sites that link affiliate codes, and the vendor's own blog are
all the vendor talking. Only sources with no incentive count as independent.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db as _db  # noqa: E402
import db_phase2  # noqa: E402

SCHEMA = """
ALTER TABLE tools ADD COLUMN reputation TEXT;
ALTER TABLE tools ADD COLUMN reputation_detail TEXT;
ALTER TABLE tools ADD COLUMN reputation_sources TEXT;
ALTER TABLE tools ADD COLUMN reputation_utc TEXT;
"""

# Researched by web search on 2026-08-03. Sources recorded so a later session can
# re-check rather than trust this.
FINDINGS = {
    "Kreo (Telegram copy-trading bot)": {
        "reputation": "MIXED",
        "detail": (
            "REAL PRODUCT, REAL RISK. Non-custodial smart-wallet architecture, which "
            "is genuinely better than the typical Telegram bot where the operator "
            "holds private keys — but it is still a hot wallet by design. Placed "
            "first in independent testing for execution speed and usability. "
            "AGAINST THAT: Polymarket reviewed its own Builders Program over "
            "concerns about copy-trading apps, naming Kreo among apps that market "
            "'following insider traders'; that cohort has suffered security "
            "breaches with losses reported up to $230,000. Its own selling point "
            "is finding 'insider traders before anyone else', which is the "
            "behaviour that triggered the platform review. Do not hold size in it."
        ),
        "sources": [
            "https://www.kucoin.com/news/flash/polymarket-reviews-developer-program-amid-concerns-over-copy-trading-apps-and-insider-like-behavior",
            "https://coincodecap.com/kreo-review-polymarket-kalshi-copy-trading-bot",
            "https://polymarktbots.com/tools/copy-trading-bots/kreo/",
        ],
        "rename_from": "Creo (Telegram copy-trading bot)",
        "note": (
            "NAME CORRECTION: the transcript said 'Creo'. The product is 'Kreo' "
            "(@KreoPolyBot). Auto-generated captions garble product names, and a "
            "tool-extraction pipeline that trusts them will verify the wrong thing "
            "or nothing at all. Always search variants before recording NO_FOOTPRINT."
        ),
    },
}


def main():
    con = db_phase2.connect()
    for stmt in SCHEMA.strip().split(";"):
        if stmt.strip():
            try:
                con.execute(stmt)
            except Exception:  # noqa: BLE001 - column already exists
                pass
    con.commit()

    for name, f in FINDINGS.items():
        old = f.get("rename_from")
        if old:
            con.execute("UPDATE tools SET name=? WHERE name=?", (name, old))
        con.execute(
            """UPDATE tools SET reputation=?, reputation_detail=?,
                   reputation_sources=?, reputation_utc=? WHERE name=?""",
            (f["reputation"], f["detail"], json.dumps(f["sources"]),
             _db.now(), name))
        print(f"  {f['reputation']:<13} {name}")
        if f.get("note"):
            print(f"      NOTE: {f['note'][:150]}...")
    con.commit()

    print("\n  tools with a reputation verdict:")
    for r in con.execute(
        "SELECT reputation, COUNT(*) n FROM tools WHERE reputation IS NOT NULL"
        " GROUP BY reputation"
    ):
        print(f"    {r['reputation']:<14}{r['n']}")
    unchecked = con.execute(
        "SELECT COUNT(*) c FROM tools WHERE reputation IS NULL").fetchone()["c"]
    print(f"    {'(unchecked)':<14}{unchecked}")
    print("\n  Reminder: NO_FOOTPRINT is never POSITIVE. Absence of complaints "
          "about\n  a small tool is absence of evidence.")
    con.close()


if __name__ == "__main__":
    main()
