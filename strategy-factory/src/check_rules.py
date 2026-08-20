"""THE FOUR UNCHECKED ASSUMPTIONS — answered from rules text already on tape.

`reports/COMPLETENESS-01.md` named four assumptions that were never checked, and
mailbox 005 says to check them BEFORE screening, not after: *"a spec killed by a
settlement rule costs nothing to kill now and wastes a screening slot later."*

Two of them can void a spec outright:

  SF009  Does Kalshi's NFL spread market have a PUSH outcome? The spec rests on
         "a team cannot cover a 7-point handicap more often than it simply
         wins". If an exact-number tie can resolve the spread NO while the win
         market resolves YES, that implication is false and SF009 is VOID, not
         weak.
  SF012  Can more than one person be pardoned? The spec sells a set of named
         candidates on the argument that they are mutually exclusive and must
         sum to under a dollar. If two can happen, nothing is bounded and there
         is no arbitrage - only a bet.
  SF015  Is a company KPI ladder one observation per earnings report, or twenty
         markets? If it is one report, the sample is ~4 per company per year and
         the spec is underpowered by two orders of magnitude.
  SF013  Is the Pyth price feed free and public? (Not answerable from rules
         text; recorded as still-open with what WOULD answer it.)

**The answers come from `w_names.rules_primary`, which the recorder has been
storing since 2026-08-18.** No new HTTP request is needed for three of the four.

⚠ READING BEATS SCORING (`CLAUDE.md` §6). This script prints the actual rules
text for a human to read rather than pattern-matching a verdict out of it. The
keyword counts are a way of FINDING the text, never a way of deciding what it
says.

    py -3 strategy-factory/src/check_rules.py
"""
from __future__ import annotations

import re
import sqlite3
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def con():
    c = sqlite3.connect("file:%s?mode=ro" % (ROOT / "data" / "wide_top.db"),
                        uri=True)
    c.execute("attach database ? as d",
              (str(ROOT / "data" / "wide_depth.db"),))
    return c


def rules_for(c, series, limit=3):
    """Rules text for a family, from whichever database has it."""
    out = []
    for tbl in ("w_names", "d.w_names"):
        try:
            rows = c.execute(
                "select ticker, title, yes_sub_title, rules_primary from %s "
                "where series=? and rules_primary is not null "
                "and length(rules_primary)>40 limit ?" % tbl,
                (series, limit)).fetchall()
        except sqlite3.Error:
            rows = []
        out.extend(rows)
        if out:
            break
    return out[:limit]


def show(title, series_list, patterns, question, kills):
    print("=" * 78)
    print(title)
    print("=" * 78)
    print("QUESTION : %s" % question)
    print("KILLS    : %s" % kills)
    print()
    c = con()
    found_any = False
    for ser in series_list:
        rows = rules_for(c, ser)
        if not rows:
            print("  %-20s no rules text on tape yet" % ser)
            continue
        found_any = True
        tk, ttl, sub, txt = rows[0]
        print("  %s  (%s)" % (ser, tk))
        print("  market: %s / %s" % ((ttl or "")[:60], sub or ""))
        for line in textwrap.wrap(re.sub(r"\s+", " ", txt)[:900], 74):
            print("      %s" % line)
        hits = [p for p in patterns
                if re.search(p, txt, re.I)]
        print("      >> keyword hits: %s" % (hits or "none"))
        print()
    if not found_any:
        print("  NOTHING ON TAPE FOR ANY OF THESE FAMILIES.")
        print("  That is itself the finding: the spec cannot be checked, and")
        print("  GUARDS #15 says an absent reading is not a verdict.")
    c.close()
    print()


def main() -> None:
    show("SF009 — does the NFL spread have a PUSH?",
         ["KXNFLSPREAD", "KXNCAAFSPREAD", "KXEPLSPREAD", "KXUCLSPREAD"],
         [r"\bpush\b", r"\btie\b", r"\bexactly\b", r"\bhalf[- ]point\b",
          r"\bvoid\b", r"\brefund"],
         "Can an exact-number result resolve the spread NO while the win "
         "market resolves YES?",
         "SF009 is VOID if yes - the inequality it trades does not hold.")

    show("SF012 — can more than one candidate happen?",
         ["KXTRUMPPARDONS", "KXFEDERALCHARGE"],
         [r"\bmutually exclusive\b", r"\bonly one\b", r"\bany (of|other)\b",
          r"\beach\b", r"\bseparate\b", r"\bindependent"],
         "Are the named candidates mutually exclusive, or can several resolve "
         "YES at once?",
         "SF012 is VOID if several can - nothing is bounded by a dollar and "
         "there is no arbitrage, only a bet.")

    show("SF015 — is a company KPI ladder ONE report or twenty markets?",
         ["KXHOODA", "KXTSLAA", "KXSPOTA", "KXSBUXA"],
         [r"\bquarter", r"\bannual\b", r"\bfiscal\b", r"\breport",
          r"\bearnings\b"],
         "Do all the strikes in a family settle off ONE published number on "
         "one date?",
         "Not a void, but it makes the unit the EARNINGS REPORT and the "
         "sample ~4 per company per year - underpowered by two orders of "
         "magnitude, which SF015 itself names as its likeliest kill.")

    show("SF011 / SF016 — is a candidate set EXHAUSTIVE?",
         ["KXROLEATEVENTCOACHELLA", "KXPERFORMVS", "KXNOBELPHYSICS"],
         [r"\bany other\b", r"\bnone of\b", r"\bsomeone else\b",
          r"\bnot listed\b", r"\bexhaustive\b"],
         "Can the outcome be somebody the market never listed?",
         "Both specs' BUY branch dies if the set is not exhaustive - that is "
         "LEDGER C014, where 464 claimed arbitrages vanished on requiring a "
         "complete tiling.")

    # SF013 cannot be answered from rules text. Say so rather than skip it.
    print("=" * 78)
    print("SF013 — is the Pyth price feed free and public?")
    print("=" * 78)
    print("NOT ANSWERABLE FROM RULES TEXT, and not guessed at here.")
    print()
    c = con()
    rows = rules_for(c, "KXGOLDH", 1) or rules_for(c, "KXSILVERH", 1)
    if rows:
        print("  What the rules DO say about the settlement source:")
        for line in textwrap.wrap(re.sub(r"\s+", " ", rows[0][3])[:600], 74):
            print("      %s" % line)
    c.close()
    print()
    print("  WHAT WOULD ANSWER IT: an unauthenticated GET against Pyth's")
    print("  public price endpoint returning a gold price. That is one")
    print("  request and it is a NETWORK check, not a tape check, so it is")
    print("  deliberately not bundled into this script.")
    print("  Until then SF013 is SCREENABLE (the Kalshi side is on tape) but")
    print("  its settlement source is UNVERIFIED, and that is recorded rather")
    print("  than assumed.")


if __name__ == "__main__":
    main()
