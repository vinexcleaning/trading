"""Every pick the strategy made, and why this tool did not place it.

    py -3 livedesk\\tools\\why_not_placed.py
    py -3 livedesk\\tools\\why_not_placed.py --all     # include before the desk existed

READ ONLY. Opens `mlb-paper/data/paper.db` read-only and never writes anything.

# WHY IT EXISTS

Mailbox 022: *"The desk captured 30% of the strategy's picks, and the 70% it
dropped were the profitable ones... That number decides what to fix next and
nobody has it."* That is the right question and it had never been measured.

# ⚠ AND THE FIRST ANSWER WAS INFLATED, WHICH MATTERS

Comparing the whole of `mlb-paper` against the whole of this ledger says 85
picks missed, worth $90. **But 46 of those are from 7-13 August, before this
tool placed its first bet on the 14th.** They were not skipped. There was
nothing to skip them with.

**By default this counts only picks from the day the desk first placed a real
bet.** That date is read off the ledger, not typed in, so it cannot go stale.
`--all` shows the wider figure and labels it.

The honest number is still large and still the biggest single term in his loss.
It just is not the first one.
"""
from __future__ import annotations

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

LIVEDESK = Path(__file__).resolve().parents[1]
PAPER_DB = LIVEDESK.parent / "mlb-paper" / "data" / "paper.db"
sys.path.insert(0, str(LIVEDESK / "src"))

PLACED = ("won", "lost", "open", "awaiting-settlement")

#: Note text -> the reason in his words. Ordered: the FIRST match wins, so the
#: more specific patterns come first.
REASONS = [
    ("THESE DO NOT AGREE",
     "the old balance check refused it (fixed 16 Aug)"),
    ("under your $40 floor",
     "your account was under the $40 floor"),
    ("35% below its best",
     "the 35% drop rule had paused it"),
    ("STOPPED",
     "the 35% drop rule had paused it"),
    ("insufficient balance",
     "Kalshi said there was not enough cash"),
    ("market not found",
     "Kalshi did not have that market"),
    ("already", "one bet per signal, already had one"),
]


def reason_for(entry) -> str:
    note = entry.note or ""
    for needle, said in REASONS:
        if needle in note:
            return said
    if entry.status == "expired":
        return "the game started before it got placed (reason not recorded)"
    if entry.status == "void":
        return "recorded as never placed (reason not recorded)"
    return f"status {entry.status} (reason not recorded)"


def main() -> None:
    show_all = "--all" in sys.argv
    if not PAPER_DB.exists():
        sys.exit(f"  no paper database at {PAPER_DB}")

    import ledger as L
    led = L.Ledger()
    led.load()
    real = [e for e in led.entries if e.status in PLACED]
    if not real:
        sys.exit("  this desk has never placed a bet, so there is nothing to "
                 "compare.")
    first_day = min(e.confirmed_utc[:10] for e in real)

    con = sqlite3.connect(f"file:{PAPER_DB}?mode=ro", uri=True)
    cur = con.cursor()
    cur.execute("select game_key, ticker, pnl_c, status from positions "
                "where bot = 'starter__hold'")
    picks = [(gk, tk, (p or 0) / 100.0, st) for gk, tk, p, st in cur.fetchall()]
    con.close()

    ours = defaultdict(list)
    for e in led.entries:
        ours[e.ticker].append(e)

    before = [r for r in picks if r[0].split(":")[0] < first_day]
    if not show_all:
        picks = [r for r in picks if r[0].split(":")[0] >= first_day]

    placed, missed = [], []
    for row in picks:
        rows = ours.get(row[1], [])
        (placed if any(e.status in PLACED for e in rows) else missed).append(row)

    print()
    print(f"  The strategy's picks, and what this desk did with them.")
    if show_all:
        print(f"  ALL OF THEM, including {len(before)} from before the desk "
              f"existed on {first_day}.")
    else:
        money = sum(r[2] for r in before)
        print(f"  From {first_day}, the day this desk placed its first real "
              f"bet.")
        print(f"  {len(before)} earlier picks are EXCLUDED (${money:+.2f}) -- "
              f"there was no tool yet to skip them.")
    print()
    print(f"    the strategy picked        {len(picks):4d} games")
    print(f"    this desk placed           {len(placed):4d}   "
          f"the strategy made ${sum(r[2] for r in placed):+8.2f} on those")
    print(f"    this desk did NOT place    {len(missed):4d}   "
          f"the strategy made ${sum(r[2] for r in missed):+8.2f} on those")
    print()

    if not missed:
        print("  It placed every one. Nothing to explain.")
        return

    groups = defaultdict(lambda: [0, 0.0])
    for gk, tk, pnl, _ in missed:
        rows = ours.get(tk, [])
        why = reason_for(rows[0]) if rows else \
            "it never reached the tool at all"
        groups[why][0] += 1
        groups[why][1] += pnl

    print("  WHY EACH ONE WAS NOT PLACED, worst first by money left behind:")
    print()
    width = max(len(k) for k in groups)
    for why, (n, money) in sorted(groups.items(), key=lambda x: -x[1][1]):
        print(f"    {n:3d}  {why:<{width}}   the strategy made ${money:+8.2f}")
    print()
    print("  A reason that says 'not recorded' is itself a defect: the tool")
    print("  refused a bet and did not write down why.")
    print()


if __name__ == "__main__":
    main()
