"""What has actually happened to his money, against what the strategy did.

    py -3 livedesk\tools\whats_happened.py

⚠ WHY THIS EXISTS, and it is the most useful number nobody had given him.

Over the window this desk has been live, the STRATEGY made money and HE lost
money. Same picks, same games, opposite outcome. The gap is not the strategy and
not luck about which games came up -- it is **which bets this tool managed to
place, and at what size.**

On 2026-08-16 the strategy won 8 of 13 and made +$34.93. This tool placed
NOTHING that day: one void, five expired, a guard refusing everything. Two days
later the guard was fixed, the strategy had a bad day, and it placed all of
them.

**That is a measurement of what our defects cost him, not an excuse**, and the
count of what the tool REFUSED on a winning day is the most expensive line in
this whole project. Nothing displayed it until now.
"""
from __future__ import annotations

import collections
import sqlite3
import sys
from pathlib import Path

LIVEDESK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVEDESK / "src"))

import ledger as L                                        # noqa: E402
from money import usd                                     # noqa: E402

PAPER_DB = LIVEDESK.parent / "mlb-paper" / "data" / "paper.db"


def paper_by_day():
    """What `starter__hold` did, by the day the bet settled."""
    try:
        con = sqlite3.connect(f"file:{PAPER_DB}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
    except Exception:
        return {}
    out = collections.defaultdict(lambda: [0, 0, 0.0])
    try:
        # pnl_c, in CENTS -- not pnl_usd, which does not exist. Reading a
        # column that is not there returned nothing and printed an empty
        # column rather than an error, which is the quiet kind of wrong.
        rows = con.execute(
            "SELECT game_key, status, pnl_c FROM positions "
            "WHERE bot='starter__hold' AND status='settled'")
    except sqlite3.Error:
        return {}
    for r in rows:
        day = str(r["game_key"])[:10]
        out[day][0] += 1
        pnl = (r["pnl_c"] or 0) / 100.0
        if pnl > 0:
            out[day][1] += 1
        out[day][2] += pnl
    return out


def main() -> None:
    led = L.Ledger()
    settled = [e for e in led.entries if e.status in ("won", "lost")]
    riding = led.at_risk_usd()
    now = led.account_start_usd + led.realised_usd()

    print()
    print("  WHAT HAS HAPPENED TO YOUR MONEY")
    print("  " + "=" * 68)
    print(f"    started with     ${led.account_start_usd:.2f}")
    print(f"    now              ${now:.2f}   "
          f"(${now - riding:.2f} cash + ${riding:.2f} riding)")
    down = led.realised_usd()
    word = "up" if down >= 0 else "down"
    print(f"    so you are       {word} ${abs(down):.2f}")
    print(f"    on               {len(settled)} finished bets")
    print()

    # --- day by day, ours against the strategy's ------------------------
    paper = paper_by_day()
    ours = collections.defaultdict(lambda: collections.Counter())
    for e in led.entries:
        day = str(e.game_key)[:10]
        ours[day][e.status] += 1
        if e.status in ("won", "lost"):
            ours[day]["pnl"] += 0     # keep the key present
    money = collections.defaultdict(float)
    for e in settled:
        money[str(e.game_key)[:10]] += e.pnl_usd

    days = sorted(set(list(paper.keys()) + list(ours.keys())))
    if days:
        print("  DAY BY DAY — the strategy against what this tool actually did")
        print("  " + "-" * 68)
        print(f"    {'day':<12} {'the strategy':<26} {'this tool':<28}")
        print("  " + "-" * 68)
        for d in days:
            n, w, p = paper.get(d, [0, 0, 0.0])
            left = (f"{n} bets, won {w}, {usd(p)}" if n else "-")
            c = ours.get(d, collections.Counter())
            placed = c.get("won", 0) + c.get("lost", 0)
            refused = c.get("void", 0) + c.get("expired", 0)
            bits = []
            if placed:
                bits.append(f"{placed} placed, {usd(money[d])}")
            if refused:
                bits.append(f"REFUSED {refused}")
            right = ", ".join(bits) or "-"
            flag = ""
            if refused and p > 0 and not placed:
                flag = "  <-- it won and we placed nothing"
            print(f"    {d:<12} {left:<26} {right:<28}{flag}")
        print()

    print("  READ THIS WITH IT:")
    print("  - the difference between those two columns is not the strategy.")
    print("    It is which bets this tool managed to place, and at what size.")
    print("  - a REFUSED count on a day the strategy won is the most")
    print("    expensive line here.")
    print()


if __name__ == "__main__":
    main()
