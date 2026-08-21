"""Audit factory strategy specs on arrival.

The `factory` chat generates specs at volume across families this repo has never
worked in. **Volume is exactly when a bad premise slips through**, and this chat
is the only one whose job is catching that.

Three mechanical screens. None of them decides anything -- they order the
reading, the same way `screen_closures.py` does for ledger claims:

  NO-ID      the spec engages no recorded claim BY ID. Prose references are
             good practice and invisible to every tool here -- `idea.py` and
             this script both key on ids, so a spec that says "the archive is
             against this" in words cannot be cross-checked by anything.

  DUD        the spec's families or thesis overlap a claim on the dud list in
             STRATEGY_SPECS.md -- wrongly closed AND dead anyway. Landing on
             one of those is the signal to stop, not to screen.

  GUARD-24   the entry band reaches into near-certainty (>=90c) or its mirror
             (<=10c). GUARDS #24 measured across SEVEN sports that the market
             does not quote a near-certainty: buyable at 95c+ ran 29 to 67 in
             100, while a 40-70c control was 100 in 100 on all 33,802 minutes.
             **A spec in that band must report the availability rate, not
             assume it.**

READ ONLY. No network.

  py -3 reopen\\src\\audit_specs.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SPECS = REPO / "strategy-factory" / "specs"

CLAIM_ID = re.compile(
    r"(?<![A-Za-z0-9])((?:S|C|W|T|K|B|M|BH|CH|SO)\d{2,3}[a-z]?)(?![A-Za-z0-9])")

# From STRATEGY_SPECS.md -- wrongly closed AND dead anyway, with the later
# result that killed each one. A spec landing here is not a fresh idea.
DUDS: dict[str, str] = {
    "S021": "effect 2.42 out of 100 against a 3.61 cost; the bucket version "
            "needs ~61 weeks of recording",
    "K001": "family dead on structure -- K013, minted at the money on 99.86% "
            "of 6,261 markets",
    "K012": "22-48 settlements ever against the 481 needed. UNMEASURABLE, "
            "which is not the same as no-edge and is just as final",
    "M011": "settled properly since -- 1,460 paired observations, largest "
            "venue disagreement 2.77c against a 2.75c cost",
    "C088": "C079 measured it: informed flow dies inside 15 seconds against a "
            "~66-second public visibility delay (C089)",
    "C011": "a broken parameter in a dormant bot, not a strategy",
    "C012": "a broken parameter in a dormant bot, not a strategy",
    "C082": "a defect in a pipeline C077 killed at 42,652 wallets",
    "C083": "a defect in a pipeline C077 killed at 42,652 wallets",
    "SO006": "the data fell out of Kalshi's ~69-day window and cannot be "
             "rebuilt",
    "C001": "a 75-leg ladder carries a ~1.9c fee floor; K007 found 52 "
            "violations and 0 with tradeable size",
    "C002": "same fee-floor arithmetic as C001",
    "M027": "the DATA claim was false and is corrected; the TRADE is not "
            "unlocked -- B009 measures ITF at -9.13c a trade on 6,135 trades",
}

# Specs this chat already wrote from ledger claims. The factory agreed not to
# re-derive them.
#
# ⚠ SHARPENED 2026-08-20, the same lesson as GUARD-24 below. This screen was
# labelled "duplicate". It is not one: SF111 carries `claims: ["S005","S006"]`
# because it CITES them as prior work, which is exactly what mail 007 asked
# for -- and the screen then flagged the good behaviour as a collision. A
# script cannot tell "cites the claim" from "re-tests the claim". So this now
# reports SHARES-CLAIM and says out loud that it needs reading.
MINE = {
    "C023": "RS-01", "C061": "RS-02", "CH074": "RS-03", "S023": "RS-04",
    "M025": "RS-05", "B023": "RS-06", "S005": "RS-07", "S006": "RS-07",
    "C106c": "RS-08", "C016": "RS-09",
}

NEAR_CERTAIN_HIGH = 90
NEAR_CERTAIN_LOW = 10
NARROW = 25


def main() -> int:
    if not SPECS.exists():
        print(f"no specs at {SPECS} -- the factory has written none yet.")
        return 0

    files = sorted(SPECS.glob("*.json"))
    print(f"specs found: {len(files)}\n")

    no_id, dud_hits, guard24, mine_hits = [], [], [], []

    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except ValueError as e:
            print(f"  UNPARSEABLE {f.name}: {e}")
            continue
        sid = d.get("id", f.stem)
        # The factory added a structured `claims` list after mail 007. Prefer
        # it when present -- a regex over the whole blob also catches ids that
        # merely appear in prose, which is how this screen over-reported.
        declared = d.get("claims")
        if isinstance(declared, list) and declared:
            ids = {str(c).strip() for c in declared}
        else:
            ids = set(CLAIM_ID.findall(json.dumps(d)))

        if not ids:
            no_id.append(sid)
        for cid in sorted(ids & set(DUDS)):
            dud_hits.append((sid, cid, DUDS[cid]))
        for cid in sorted(ids & set(MINE)):
            mine_hits.append((sid, cid, MINE[cid]))

        # SHARPENED 2026-08-20. The first version flagged any band reaching
        # 90c and caught 28 of 31 -- useless, because most specs carry a wide
        # "any price" band like 3-97c. What GUARDS #24 kills is a band that
        # TARGETS near-certainty, so the test is narrow AND extreme.
        entry = d.get("entry") or {}
        lo, hi = entry.get("min_price_c"), entry.get("max_price_c")
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
            width = hi - lo
            if hi >= NEAR_CERTAIN_HIGH and width <= NARROW:
                guard24.append((sid, f"targets {lo}-{hi}c -- near-certainty"))
            elif lo <= NEAR_CERTAIN_LOW and width <= NARROW:
                guard24.append((sid, f"targets {lo}-{hi}c -- the long-shot "
                                     f"mirror of the same absence"))

    print(f"NO-ID    {len(no_id):3d}  engage no recorded claim by id")
    if no_id:
        print(f"           {', '.join(no_id)}")
    print(f"DUD      {len(dud_hits):3d}  cite a claim that is dead anyway")
    for sid, cid, why in dud_hits:
        print(f"           {sid} cites {cid}: {why}")
    print(f"GUARD-24 {len(guard24):3d}  entry band reaches near-certainty")
    for sid, why in guard24:
        print(f"           {sid} {why}")
    print(f"SHARES-CLAIM {len(mine_hits):3d}  cites a claim a reopen RS- spec "
          f"also works")
    for sid, cid, rs in mine_hits:
        print(f"           {sid} shares {cid} with {rs} "
              f"-- READ IT: citing is not duplicating")

    print("\n" + "=" * 66)
    print("None of these is a verdict.")
    print("NO-ID is not the same as ignoring the archive -- several specs")
    print("engage prior work in prose, which is good practice and invisible")
    print("to every tool here.")
    print("DUD and GUARD-24 are worth reading by hand.")
    print("SHARES-CLAIM is a prompt to read, not a finding.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
