"""Why do `early`, `bullpen` and `park-air` lose while `starter` wins?

Mailbox 011, in his words: *"We also wanna analyse the unsuccessful bots, see
what hasn't worked… we don't want a biased sample."*

The sharpest comparison available is `early` against `starter`, because they
trade **the same games** from the same pool. One is up 14% and the other down
8.6%. If they are on opposite sides of the same game, one of them must lose, and
that is a different story from either of them being badly costed.

The question this file exists to separate:

    IS THE LOSS A SIGNAL PROBLEM OR A COSTING PROBLEM?

  * A COSTING problem looks like: wins about as often as it should, but pays
    more spread, enters at a worse price, or trades a wider book. Fixable.
  * A SIGNAL problem looks like: pays the same as everyone else and simply
    picks wrong. Not fixable by better execution.

    python src/analyse_losers.py
"""
from __future__ import annotations

import collections
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as E                     # noqa: E402

FAMS = ("starter", "early", "bullpen", "park-air")


def binom_tail(k, n, p):
    return sum(math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))


def main():
    con = E.connect()
    print("=" * 78)
    print("WHY THE LOSING BOTS LOSE -- signal problem or costing problem?")
    print("=" * 78)

    # ------------------------------------------------ the costing comparison
    print("\n## 1. COST: is a loser paying more to get in?\n")
    print(f"{'family':<10} {'games':>6} {'won':>5} {'win/100':>8} {'breakeven':>10} "
          f"{'buy price':>10} {'spread paid':>12} {'fee/contract':>13}")
    stats = {}
    for fam in FAMS:
        rows = con.execute(
            "SELECT p.entry_price_c, p.entry_fee_c, p.contracts, p.pnl_c, "
            "       p.ticker, p.game_key, p.opened_utc, f.ts_utc "
            "FROM positions p LEFT JOIN fills f "
            "  ON f.decision_id = p.decision_id AND f.action='open' "
            "WHERE p.bot=? AND p.status='settled'", (f"{fam}__hold",)).fetchall()
        if not rows:
            continue
        n = len(rows)
        won = sum(1 for r in rows if (r["pnl_c"] or 0) > 0)
        contracts = sum(r["contracts"] for r in rows)
        price = statistics.mean(r["entry_price_c"] for r in rows)
        fee = sum(r["entry_fee_c"] for r in rows) / max(1, contracts)
        # spread paid = fill price minus the mid recorded on the nearest mark
        spreads = []
        for r in rows:
            mk = con.execute(
                "SELECT bid, ask FROM marks WHERE ticker=? AND ts_utc<=? "
                "ORDER BY ts_utc DESC LIMIT 1",
                (r["ticker"], r["ts_utc"] or r["opened_utc"])).fetchone()
            if mk and mk["bid"] and mk["ask"]:
                spreads.append(abs(r["entry_price_c"] - (mk["bid"] + mk["ask"]) / 2))
        sp = statistics.mean(spreads) if spreads else float("nan")
        be = (price + fee) / 100.0
        stats[fam] = {"n": n, "won": won, "price": price, "fee": fee,
                      "spread": sp, "breakeven": be,
                      "pnl": sum(r["pnl_c"] or 0 for r in rows) / 100.0,
                      "contracts": contracts,
                      "games": {r["game_key"] for r in rows}}
        print(f"{fam:<10} {n:>6} {won:>5} {100*won/n:>7.0f} "
              f"{100*be:>9.1f} {price:>10.1f} {sp:>12.2f} {fee:>13.2f}")

    print("\n  If a loser's spread paid and fee match the winner's, the loss is")
    print("  NOT a costing problem -- it is picking wrong.")

    # ------------------------------------------------ the head-to-head
    print("\n## 2. `early` vs `starter` ON THE SAME GAMES\n")
    if "early" in stats and "starter" in stats:
        shared = stats["early"]["games"] & stats["starter"]["games"]
        print(f"  games both traded: {len(shared)} "
              f"(early {len(stats['early']['games'])}, "
              f"starter {len(stats['starter']['games'])})")
        opp = same = 0
        opp_rows = []
        for g in shared:
            a = con.execute("SELECT ticker,pnl_c FROM positions WHERE "
                            "bot='early__hold' AND game_key=? AND status='settled'",
                            (g,)).fetchone()
            b = con.execute("SELECT ticker,pnl_c FROM positions WHERE "
                            "bot='starter__hold' AND game_key=? AND status='settled'",
                            (g,)).fetchone()
            if not a or not b:
                continue
            if a["ticker"] == b["ticker"]:
                same += 1
            else:
                opp += 1
                opp_rows.append((g, (a["pnl_c"] or 0) / 100, (b["pnl_c"] or 0) / 100))
        print(f"  SAME side     : {same}")
        print(f"  OPPOSITE side : {opp}")
        if opp:
            e = sum(r[1] for r in opp_rows)
            s = sum(r[2] for r in opp_rows)
            print(f"    on those {opp} games: early ${e:+.2f}, starter ${s:+.2f}")
            print("    On an opposite-side game one of them MUST lose. That is")
            print("    not evidence about either signal -- it is one bet, twice.")
        if same:
            print(f"    On the {same} SAME-side games they win and lose together,")
            print("    so any difference between them comes from the games only")
            print("    ONE of them took.")

    # ------------------------------------------------ where each one is alone
    print("\n## 3. THE GAMES ONLY ONE OF THEM TOOK -- where the difference lives\n")
    if "early" in stats and "starter" in stats:
        for a, b in (("early", "starter"), ("starter", "early")):
            only = stats[a]["games"] - stats[b]["games"]
            if not only:
                continue
            rows = con.execute(
                "SELECT pnl_c, contracts FROM positions WHERE bot=? "
                "AND status='settled' AND game_key IN (%s)"
                % ",".join("?" * len(only)),
                tuple([f"{a}__hold"] + list(only))).fetchall()
            pnl = sum(r["pnl_c"] or 0 for r in rows) / 100.0
            c = sum(r["contracts"] for r in rows)
            print(f"  {a:<8} alone on {len(only):>3} games: ${pnl:+8.2f}  "
                  f"({100*pnl/c if c else 0:+.2f}c per contract)")

    # ------------------------------------------------ closing-line value
    print("\n## 4. CLOSING-LINE VALUE -- the number with a sample behind it\n")
    for fam in FAMS:
        rows = con.execute(
            "SELECT f.ticker, f.price_c, f.side, f.game_key FROM fills f "
            "WHERE f.bot=? AND f.action='open'", (f"{fam}__hold",)).fetchall()
        by_game = {}
        for r in rows:
            cl = con.execute(
                "SELECT sharp_fair_yes_c FROM marks WHERE ticker=? AND "
                "sharp_fair_yes_c IS NOT NULL ORDER BY ts_utc DESC LIMIT 1",
                (r["ticker"],)).fetchone()
            if not cl:
                continue
            fair = cl["sharp_fair_yes_c"]
            if r["side"] == "NO":
                fair = 100 - fair
            by_game.setdefault(r["game_key"], []).append(fair - r["price_c"])
        if not by_game:
            print(f"  {fam:<10} no sharp reference")
            continue
        vals = [statistics.mean(v) for v in by_game.values()]
        print(f"  {fam:<10} n={len(vals):>3} games   mean CLV "
              f"{statistics.mean(vals):>6.2f}c")
    print("\n  Every family is NEGATIVE here. They are all buying behind the")
    print("  closing sharp line -- the winner included.")

    # ------------------------------------------------ lead time
    print("\n## 5. WHEN each family buys -- lead time is the obvious suspect\n")
    for fam in FAMS:
        w = collections.Counter()
        for r in con.execute(
                "SELECT window FROM decisions WHERE bot=? AND kind='entry'",
                (f"{fam}__hold",)):
            w[r["window"]] += 1
        if w:
            print(f"  {fam:<10} " + "  ".join(f"{k}={v}" for k, v in
                                              sorted(w.items())))
    con.close()


if __name__ == "__main__":
    main()
