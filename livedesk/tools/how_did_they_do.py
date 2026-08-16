"""How the bets that never got placed would have settled.

    py -3 livedesk\\tools\\how_did_they_do.py

WHY THIS IS WORTH ANYTHING
    Every one of these picks was written into the ledger **before** its game
    started -- team, side, price, size -- and then never placed, because a
    guard was refusing everything. So the outcomes were unknown at the moment
    the pick was recorded.

    That is the honest shape of a forward test, and it is rare. Most of what
    this repo has thrown away was measured over the same window it was chosen
    on. This was not.

WHAT IT IS STILL NOT
    - **It is not what he would have made.** These are recorded prices, not
      fills. A real order at that price might not have filled, and the fee is
      the one recorded at the time.
    - **It is a small number of games**, so a good result here is not evidence
      the strategy works. Read the count before the profit.
    - **The "alone" column is RE-DERIVED**, not recorded before the outcome,
      for any bet taken before that flag was wired in on 2026-08-16. Re-derived
      is weaker and is marked with a `~`.

Settlement comes from Kalshi's own result for the exact ticker bought, which
is the authority -- not a score read from anywhere else.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import prices as PRICES                                   # noqa: E402
from ledger import Ledger                                 # noqa: E402
from money import usd                                     # noqa: E402

NEVER_PLACED = ("expired", "void", "deferred")


def main() -> None:
    led = Ledger()
    rows, unknown = [], []

    # ⚠ ONE ROW PER GAME, AND THIS IS NOT A DETAIL.
    #
    # The deferred-retry loop rewrote the same pick every few minutes, so the
    # ledger holds BOS@PIT three times, MIL@LAD three times, BAL@TB three
    # times. Counting those as separate bets triples the apparent sample and
    # triples the apparent profit, while every copy is the same game settling
    # once. `CLAUDE.md` §6: a market settles once; 490,464 fills from 762
    # matches are 762 observations.
    #
    # And it is not merely a statistical nicety here -- **Guard 1 would have
    # placed exactly one of them.** So one per game is also what would really
    # have happened. The earliest recorded is the one that would have gone on.
    first_per_game = {}
    for e in sorted(led.entries, key=lambda x: x.confirmed_utc):
        if e.status in NEVER_PLACED:
            first_per_game.setdefault(e.game_key, e)
    dropped = len([e for e in led.entries if e.status in NEVER_PLACED]) \
        - len(first_per_game)

    for e in first_per_game.values():
        if e.status not in NEVER_PLACED:
            continue
        try:
            q = PRICES.quote(e.ticker)
        except Exception as exc:
            unknown.append((e, f"could not read the market ({exc})"))
            continue
        if not q.is_final:
            unknown.append((e, f"not settled yet ({q.status})"))
            continue
        won = ((q.result == "yes") == (e.side.upper() == "YES"))
        pnl = e.win_profit_usd if won else -e.lose_usd
        rows.append((e, won, pnl))

    print()
    print("  BETS THE BOT PICKED AND NEVER PLACED")
    print("  " + "=" * 74)
    print(f"  {'game':<22} {'backed':<22} {'price':>5} {'size':>5} "
          f"{'result':>7} {'would be':>9}")
    print("  " + "-" * 74)
    for e, won, pnl in sorted(rows, key=lambda r: r[0].starts_utc):
        print(f"  {e.game_key[5:]:<22} {e.team[:22]:<22} "
              f"{str(e.price_c) + 'c':>5} {e.contracts:>5} "
              f"{('WON' if won else 'lost'):>7} {usd(pnl):>9}")

    if not rows:
        print("  nothing settled yet.")
    else:
        n = len(rows)
        wins = sum(1 for _, w, _ in rows if w)
        if dropped:
            print("  " + "-" * 74)
            print(f"  ({dropped} duplicate rows left out -- the retry loop "
                  f"rewrote the same pick repeatedly.")
            print(f"   Each game settles ONCE, and Guard 1 would have placed "
                  f"one of them.)")
        total = round(sum(p for _, _, p in rows), 2)
        staked = round(sum(e.cost_usd for e, _, _ in rows), 2)
        print("  " + "-" * 74)
        print(f"  {n} GAMES · won {wins} · lost {n - wins}")
        print(f"  laid out ${staked:.2f} · would have come to {usd(total)}")
        if staked:
            per100 = 100.0 * total / staked
            print(f"  that is {usd(per100)} for every $100 put in")
        print()
        print(f"  Out of 100 bets like these, it won about "
              f"{round(100.0 * wins / n)}.")

    if unknown:
        print()
        print("  NOT COUNTED (not settled, or the market could not be read):")
        for e, why in unknown:
            print(f"    {e.game_key[5:]:<22} {e.team[:22]:<22} {why}")

    # 008 asked for the causes, one line each, off the ledger not from memory.
    import collections
    why = collections.Counter()
    for e in led.entries:
        if e.status not in NEVER_PLACED:
            continue
        n = (e.note or "").lower()
        if "do not agree" in n or "not match your account" in n:
            why["Guard 4 balance/position mismatch (the defect fixed at 18:00)"] += 1
        elif "already holding" in n:
            why["the already-holding lock"] += 1
        elif "already been taken" in n or "one per signal" in n:
            why["duplicate of a bet already taken"] += 1
        elif "floor" in n or "35%" in n or "stopped" in n:
            why["the drawdown stop or the $50 floor"] += 1
        elif "first pitch passed" in n:
            why["game started while it was held back"] += 1
        elif not n:
            why["no reason recorded"] += 1
        else:
            why["something else"] += 1
    print()
    print("  WHY EACH ONE NEVER GOT PLACED")
    print("  " + "-" * 74)
    for reason, n in why.most_common():
        print(f"    {n:>3}  {reason}")

    print()
    print("  READ THIS BEFORE THE NUMBER ABOVE:")
    print("  - these are recorded prices, not fills. A real order might not")
    print("    have filled at that price.")
    print(f"  - it is {len(rows)} games. That is too few to conclude anything,")
    print("    whichever way it came out.")
    print("  - the picks were recorded before the games, which is the honest")
    print("    shape. That is what makes it worth printing at all.")
    print()


if __name__ == "__main__":
    main()
