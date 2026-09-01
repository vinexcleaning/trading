"""Measure the real fill-vs-quote slip. Mailbox 024.

`SLIPPAGE_C = 1.0` in `mentalities.py` is subtracted from EVERY bot's edge, in
both the live path and the replay. It has never been measured. It was a guess.

⚠ WHERE THE DATA IS, AND WHY IT IS AWKWARD. The live desk records fills in the
free-text `note` of its ledger, not in a field -- there is no `fill_price_c`
anywhere in any of its nine ledger files. The two prices are:

    "auto-placed: filled, 27 of 27 @ 36c"                  <- what was PLACED
    "corrected from your account: ... really 27 at 33c"    <- what it REALLY
                                                              filled at

so the slip is (really - placed), and negative means we did BETTER than the
card said.

This reads `livedesk/data/ledger.json` READ-ONLY and writes nothing there.

    python src/measure_slip.py
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LEDGER = Path(__file__).resolve().parent.parent.parent / "livedesk" / "data" / "ledger.json"

PLACED = re.compile(r"filled,\s*(\d+)\s*of\s*\d+\s*@\s*(\d+)c")
REALLY = re.compile(r"really\s+(\d+)\s+at\s+(\d+)c")


def pairs():
    d = json.loads(LEDGER.read_text(encoding="utf-8"))
    out = []
    for e in d.get("entries") or []:
        note = e.get("note") or ""
        p, r = PLACED.search(note), REALLY.search(note)
        if not p or not r:
            continue
        out.append({"game": e.get("game_key"), "card_c": e.get("price_c"),
                    "placed_c": int(p.group(2)), "really_c": int(r.group(2)),
                    "contracts": int(r.group(1))})
    return out


if __name__ == "__main__":
    ps = pairs()
    print(f"orders with BOTH a placed price and an account-confirmed fill: "
          f"{len(ps)}")
    if not ps:
        print("  -> cannot measure. Report that, do not guess.")
        raise SystemExit
    slips = [p["really_c"] - p["placed_c"] for p in ps]
    worse = [s for s in slips if s > 0]
    better = [s for s in slips if s < 0]
    same = [s for s in slips if s == 0]
    print()
    print(f"  filled WORSE than placed : {len(worse)}  "
          f"{'(' + ', '.join(f'+{s}c' for s in worse) + ')' if worse else ''}")
    print(f"  filled at the same price : {len(same)}")
    print(f"  filled BETTER than placed: {len(better)}  "
          f"{'(' + ', '.join(f'{s}c' for s in better) + ')' if better else ''}")
    print()
    print(f"  mean slip   : {statistics.mean(slips):+.2f}c")
    print(f"  median slip : {statistics.median(slips):+.2f}c")
    print(f"  worst       : {max(slips):+d}c")
    print()
    print(f"  the constant currently assumed: +1.00c against us")
    print()
    for p in ps:
        s = p["really_c"] - p["placed_c"]
        print(f"    {p['game'][:22]:<24} placed {p['placed_c']:>2}c  "
              f"really {p['really_c']:>2}c   {s:+d}c")
