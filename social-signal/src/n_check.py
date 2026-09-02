"""Fill in `n_check_verdict` — the check this schema promised and never ran.

**`reopen` audit item 9, 2026-09-01:** *"`db.py:150` declares `n_check_verdict`
and nothing anywhere writes it. The read_queue docstring says the n-check exists
to test whether a stated sample can clear its own break-even. Loaded Reddit
win-rate claims currently sit with a permanently empty verdict."*

Correct, and it is the worst kind of gap: a column that looks like a check
passed, when no check ever ran.

## What it does

For a claim with a stated win rate and a stated sample, ask **whether the claim
can distinguish itself from its own benchmark at that sample size.** Wilson
interval, because it behaves at the extremes where these claims live.

Two benchmarks, and the verdict says which was used:

  **BREAK-EVEN** where a price is known — buying at `p` cents needs a true win
  rate of at least `p/100` just to return the stake, before fees. This is the
  bar that matters and the one nobody states.
  **COIN** where no price is stated — 50%. Weaker, but it still catches the
  claims that cannot beat a coin at their own sample size.

## What it deliberately does NOT do

**It does not judge whether the claim is true.** A `CANNOT_CLEAR` verdict means
*the stated sample is too small to support the stated claim*, not that the
person is wrong. That distinction is the whole point: this repo's own history is
of results that were real-looking and under-powered, not of people lying.

    python src/n_check.py            # report only
    python src/n_check.py --write    # write verdicts into sc_claims
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

PRICE = re.compile(r"(\d{1,3})\s*(?:c\b|cents|¢)", re.I)


def wilson(k: float, n: float, z: float = 1.96):
    """Lower and upper bound. Pure stdlib -- numpy is not available here."""
    if n <= 0:
        return 0.0, 1.0
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


# **A base rate is not a win rate, and confusing them is the first thing this
# check got wrong.** Its first run scored *"markets priced 40-50% resolve Yes
# only about 22% of the time"* as BELOW because 22% < 50% — but that number is
# how often an event happens, not how often a bet wins. Nobody is claiming to
# win 22% of their trades. Comparing it to a coin is meaningless, so these are
# now refused rather than mis-scored.
BASE_RATE = re.compile(
    r"\b(resolve[sd]?|resolution|base ?rate|priced at|of the time|"
    r"calibrat\w+|probability that|implied)\b", re.I)


def verdict_for(win_rate, n, price_c, text=""):
    """Return (verdict, detail) or (None, why-not)."""
    if win_rate is None or n is None:
        return None, "no stated win rate or no stated n"
    if BASE_RATE.search(text or ""):
        return None, ("states a BASE RATE (how often an event happens), not a "
                      "win rate — no break-even bar applies")
    try:
        wr, nn = float(win_rate), float(n)
    except (TypeError, ValueError):
        return None, "unparseable"
    if not (0.0 < wr <= 1.0) or nn < 1:
        return None, f"out of range (wr={wr}, n={nn})"

    lo, hi = wilson(wr * nn, nn)
    if price_c:
        bar, label = price_c / 100.0, f"break-even at {price_c:.0f}c"
    else:
        bar, label = 0.50, "a coin (no price stated)"

    if lo > bar:
        v = "CLEARS"
    elif hi < bar:
        v = "BELOW"          # the claim is worse than its own benchmark
    else:
        v = "CANNOT_CLEAR"   # the interval straddles the bar
    detail = (f"{wr*100:.1f}% on n={nn:.0f} -> could really be "
              f"{lo*100:.1f}-{hi*100:.1f}%; needs >{bar*100:.1f}% ({label})")
    return v, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    con = db.connect()
    rows = con.execute(
        "SELECT claim_id, post_id, claim_text, stated_n, stated_win_rate, "
        "quote FROM sc_claims").fetchall()
    done = skipped = 0
    out_lines = []
    for r in rows:
        # a price in the claim or its quote turns the coin bar into the real one
        m = PRICE.search((r["quote"] or "") + " " + (r["claim_text"] or ""))
        price = float(m.group(1)) if m and 1 <= int(m.group(1)) <= 99 else None
        v, detail = verdict_for(r["stated_win_rate"], r["stated_n"], price,
                                (r["claim_text"] or "") + " "
                                + (r["quote"] or ""))
        if v is None:
            skipped += 1
            # **Written, not left NULL.** A blank column reads as "checked and
            # fine"; this says out loud that the claim could not be checked.
            if args.write:
                con.execute("UPDATE sc_claims SET n_check_verdict=? "
                            "WHERE claim_id=?", (f"NOT_CHECKABLE: {detail}",
                                                 r["claim_id"]))
            continue
        done += 1
        if args.write:
            con.execute("UPDATE sc_claims SET n_check_verdict=? "
                        "WHERE claim_id=?", (f"{v}: {detail}", r["claim_id"]))
        out_lines.append((v, r["post_id"], (r["claim_text"] or "")[:64], detail))
    if args.write:
        con.commit()

    order = {"BELOW": 0, "CANNOT_CLEAR": 1, "CLEARS": 2}
    out_lines.sort(key=lambda x: order.get(x[0], 9))
    print(f"{len(rows)} claims: {done} checkable, {skipped} not\n")
    for v, pid, txt, detail in out_lines:
        print(f"  [{v:<13}] {pid:<9} {txt}")
        print(f"                  {detail}")

    path = os.path.join(db.REPORTS, "N_CHECK.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Can each claim clear its own bar at its own sample size?\n\n")
        fh.write("**The check `db.py` promised and never ran** (`reopen` audit "
                 "item 9). Wilson interval on the stated win rate and stated "
                 "sample, against break-even where a price is stated and "
                 "against a coin where it is not.\n\n")
        fh.write("**`CANNOT_CLEAR` does not mean the claim is false.** It means "
                 "the stated sample is too small to support it. This repo's "
                 "history is of under-powered results, not of liars.\n\n")
        fh.write(f"{len(rows)} claims, {done} checkable, {skipped} not.\n\n")
        fh.write("| verdict | post | claim | detail |\n|---|---|---|---|\n")
        for v, pid, txt, detail in out_lines:
            fh.write(f"| **{v}** | `{pid}` | {txt} | {detail} |\n")
    print(f"\n  wrote {path}")
    if not args.write:
        print("  (report only -- pass --write to store the verdicts)")
    con.close()


if __name__ == "__main__":
    main()
