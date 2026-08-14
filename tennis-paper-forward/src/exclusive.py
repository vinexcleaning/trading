"""exclusive.py — does a bot make money on the matches ONLY it picked?

    .venv\\Scripts\\python.exe -m src.exclusive

THE QUESTION, AND WHERE IT CAME FROM
    `mlb-paper` took its own best bot apart with it: every cent it made came
    from games another bot also traded, and on the games only it picked it made
    nothing. A bot that only earns where it agrees with everyone else has not
    demonstrated a view of its own - it has demonstrated that the crowd of bots
    is occasionally right, which is a different and much weaker claim.

THIS IS A DECOMPOSITION, NOT A TEST
    Stated as plainly as they stated it. It splits money that has already been
    made; it does not establish that a difference between the two halves is
    real. The halves have different sizes, different prices and different
    matches, and nothing here corrects for that. A gap is a lead to follow, not
    a finding.

THE UNIT PROBLEM, WHICH IS SPECIFIC TO THIS TEST AND MUST BE SAID FIRST
    These bots come in FAMILIES OF THREE that share every entry and differ only
    in how they exit. `favourite__hold`, `favourite__exit-once` and
    `favourite__free` buy the same match at the same moment.

    So "a match only this BOT took" is nearly always empty by construction, and
    reporting it per bot would produce a table of zeros that looks like a
    finding and is an artefact of the design.

    Both are therefore reported, and the MENTALITY one is the one that answers
    the question. `pre-game` is the exception: it has no siblings, so its
    per-bot and per-mentality figures are the same number.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.plain_report import load  # noqa: E402


def mentality_of(bot: str) -> str:
    return bot.split("__")[0]


def decompose(state) -> dict:
    ledgers = state.get("engine", {}).get("ledgers") or {}

    # who traded each event, at both grains
    bots_on: dict[tuple, set] = defaultdict(set)
    ments_on: dict[tuple, set] = defaultdict(set)
    for bot, lg in ledgers.items():
        if bot.startswith("control"):
            continue
        for p in lg.get("positions", []):
            if p.get("pnl_cents") is None:
                continue
            # Keyed on the SIDE, not the match. Two bots on opposite sides of
            # one match DISAGREE; counting that as "shared" would call a
            # disagreement an agreement. Measured here: 177 of favourite's
            # overlaps are same-side and 19 are opposite, so the correction is
            # small but it points the wrong way when it bites.
            key = (p["event_ticker"], p["ticker"])
            bots_on[key].add(bot)
            ments_on[key].add(mentality_of(bot))

    out: dict[str, dict] = {}
    for bot, lg in sorted(ledgers.items()):
        if bot.startswith("control"):
            continue
        rows = {"sole_bot": [], "shared_bot": [], "sole_ment": [], "shared_ment": []}
        for p in lg.get("positions", []):
            if p.get("pnl_cents") is None:
                continue
            et = (p["event_ticker"], p["ticker"])
            staked = p["qty"] * p["entry_price"]
            rec = (p["pnl_cents"], staked)
            rows["sole_bot" if len(bots_on[et]) == 1 else "shared_bot"].append(rec)
            rows["sole_ment" if len(ments_on[et]) == 1 else "shared_ment"].append(rec)

        def agg(key):
            v = rows[key]
            if not v:
                return {"n": 0, "return_pct": None, "pnl_dollars": 0.0}
            pnl = sum(x[0] for x in v)
            stk = sum(x[1] for x in v)
            return {"n": len(v), "pnl_dollars": pnl / 100.0,
                    "return_pct": (100.0 * pnl / stk) if stk else None}

        out[bot] = {k: agg(k) for k in rows}
    return out


def main() -> int:
    state, _ = load()
    d = decompose(state)
    settled = len(state.get("settled_events") or {})

    print("=" * 78)
    print(" DOES A BOT MAKE MONEY ON THE MATCHES ONLY IT PICKED?")
    print(f" {settled} finished matches. Paper money throughout.")
    print("=" * 78)
    print("""
 THIS SPLITS MONEY ALREADY MADE. IT DOES NOT TEST ANYTHING.
 The two halves are different matches at different prices in different sizes,
 and nothing below corrects for that. A gap is a lead, not a finding.
""")

    print(" BY MENTALITY - this is the one that answers the question")
    print(" " + "-" * 76)
    print(f" {'bot':26s} {'only this style':>22s} {'shared with others':>24s}")
    print(f" {'':26s} {'bets':>6s} {'return':>8s} {'$':>6s} {'bets':>7s} {'return':>8s} {'$':>7s}")
    for bot in sorted(d, key=lambda b: -(d[b]["shared_ment"]["return_pct"] or -99)):
        s, sh = d[bot]["sole_ment"], d[bot]["shared_ment"]
        def fmt(x):
            r = x["return_pct"]
            return (f"{x['n']:6d} {'   -   ' if r is None else f'{r:+7.2f}%'} "
                    f"{x['pnl_dollars']:+6.0f}")
        print(f" {bot:26s} {fmt(s)} {fmt(sh)}")

    print("\n WHY THE PER-BOT VERSION IS NOT THE ANSWER HERE")
    print(" " + "-" * 76)
    zero = [b for b in d if d[b]["sole_bot"]["n"] == 0]
    print(f" {len(zero)} of {len(d)} bots have ZERO matches that only they took.")
    print(" That is the design, not a result: the three versions of each style buy the")
    print(" same match at the same moment and differ only in when they sell. Reporting")
    print(" it per bot would print a table of zeros that looks like a finding.")
    solo = [b for b in d if d[b]["sole_bot"]["n"] > 0]
    if solo:
        print(f"\n The exceptions, which have no siblings: {', '.join(solo)}")
        for b in solo:
            s = d[b]["sole_bot"]
            r = s["return_pct"]
            print(f"   {b:24s} {s['n']:4d} bets alone, "
                  f"{'no return computable' if r is None else f'{r:+.2f}%'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
