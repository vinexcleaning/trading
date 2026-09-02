"""Write PARTITIONS.md — which Kalshi families actually partition.

`coordinator` mailbox 010: *"put that table where it can be found by someone not
reading STRUCTURAL-01. It is a reference fact, not a result."*

Generated from the settlement data directly, never scraped from the report —
the report truncates its tables to the top rows and a reference file that
silently drops families would be worse than no file.

    py -3 strategy-factory/src/partitions_doc.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import structural as S  # noqa: E402


def main() -> None:
    c = S.con()
    parts, st = S.partitions(c)
    good = st["good"]
    bad = st["bad"]

    L = []
    A = L.append
    A("# WHICH KALSHI FAMILIES ACTUALLY PARTITION — a reference fact, not a result")
    A("")
    A("**Measured %s from settlement outcomes on recorded tape.** Rebuilt by "
      "`strategy-factory/src/partitions_doc.py`; do not hand-edit."
      % __import__("time").strftime("%Y-%m-%d", __import__("time").gmtime()))
    A("")
    A("## The question this answers in one lookup")
    A("")
    A("> **Can I buy every outcome of this event and be guaranteed exactly one "
      "payout?**")
    A("")
    A("If yes, sum-to-one arithmetic applies and a complete set costing under a "
      "dollar is real money. **If no, buying the whole set is a BET** — it can "
      "pay nothing, or pay several times over.")
    A("")
    A("⚠ **This is the exact distinction that retracted LEDGER C014** — 464 "
      "claimed bucket-sum arbitrages, every one withdrawn, because the ladder "
      "was not a partition. It also caught a fake finding of mine on "
      "2026-09-01: an *\"8 cent edge on 6 legs\"* of `KXEPLTOTAL`, which is a "
      "nested *Over 0.5 / Over 1.5 / Over 2.5* ladder where several legs are "
      "true at once.")
    A("")
    A("## How it was decided — by measurement, never by product name")
    A("")
    A("A family qualifies only if **every** settled event in it produced "
      "**exactly one** YES, over at least five events. **One lucky event "
      "cannot qualify a family:** a single 1-0 football match produces exactly "
      "one YES on a nested goals ladder and means nothing.")
    A("")
    A("| | count |")
    A("|---|---:|")
    A("| families measured | %d |" % (len(good) + len(bad)))
    A("| **partitions** | **%d** |" % len(good))
    A("| not partitions | %d |" % len(bad))
    A("")
    A("## PARTITIONS — buying the whole set pays exactly once")
    A("")
    A("| family | settled events measured |")
    A("|---|---:|")
    for s, n in sorted(good.items(), key=lambda x: -x[1]):
        A("| `%s` | %d |" % (s, n))
    A("")
    A("## NOT PARTITIONS — buying the whole set is a bet")
    A("")
    A("| family | settled events | YES per event |")
    A("|---|---:|---|")
    for s, (n, cts) in sorted(bad.items(), key=lambda x: -x[1][0]):
        A("| `%s` | %d | %s |" % (s, n, cts))
    A("")
    A("## What this does NOT say")
    A("")
    A("- **Not that the second list is untradeable** — only that *sum-to-one* "
      "arithmetic does not apply to it. A nested ladder has its own identity "
      "(a higher strike must be worth less than a lower one), tested "
      "separately and also empty.")
    A("- **Not permanent.** Measured from families that settled inside the "
      "recording window. A family absent here was **not measured**, which "
      "`GUARDS.md` #15 and #25 both insist is different from being absent from "
      "the exchange.")
    A("- **Not a claim about size.** A partition can be real and still offer "
      "nothing tradeable; on this tape the whole structure offered about a "
      "dollar across 14 days.")
    A("")

    out = ROOT / "PARTITIONS.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote %s — %d partitions, %d not" % (out, len(good), len(bad)))


if __name__ == "__main__":
    main()
