"""Answer mailbox 006: examine the `starter` bots against the other four.

Every number here is recomputed from `data/paper.db` rather than agreed with.
The coordinator read the database directly without seeing this code, so the
point of this file is to be a SECOND independent count -- if it disagrees, the
disagreement is the finding.

Questions, in the order asked:
  1. check the arithmetic, especially the staking base and how free's 60
     positions map to 30 games
  2. how many more games until 63-out-of-100 stops being luck; as games and a date
  3. what `starter` actually does, and what would make it wrong
  4. is it one edge or three -- has the exit rule EVER changed an outcome
  5. park-air: starvation, or correct abstention

    python src/examine_starter.py
"""
from __future__ import annotations

import math
import sqlite3
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as E                     # noqa: E402


def q(con, sql, args=()):
    return con.execute(sql, args).fetchall()


def binom_tail(k, n, p):
    """P(X >= k) for Binomial(n, p). Exact, no scipy."""
    return sum(math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))


def main():
    con = E.connect()
    print("=" * 78)
    print("MAILBOX 006 -- examining `starter`, recomputed from paper.db")
    print("=" * 78)

    # ---------------------------------------------------------------- 1. counts
    print("\n## 1. THE COUNTS, recomputed independently\n")
    print(f"{'bot':<22} {'pos':>4} {'games':>6} {'won':>4} {'staked$':>9} "
          f"{'profit$':>9} {'return':>8} {'c/contract':>10}")
    rows = {}
    for bot in sorted({r["bot"] for r in q(con,
                      "SELECT DISTINCT bot FROM positions")}):
        pos = q(con,
                "SELECT game_key, contracts, entry_price_c, entry_fee_c, "
                "       settle_value_c, pnl_c, status FROM positions "
                "WHERE bot=? AND status IN ('settled','closed')", (bot,))
        if not pos:
            continue
        games = {p["game_key"] for p in pos}
        # STAKED = what you actually laid out: contracts x entry price, plus
        # the entry fee, because the fee leaves the bankroll too.
        staked = sum(p["contracts"] * p["entry_price_c"] + p["entry_fee_c"]
                     for p in pos) / 100.0
        profit = sum(p["pnl_c"] or 0 for p in pos) / 100.0
        contracts = sum(p["contracts"] for p in pos)
        won = sum(1 for p in pos if (p["pnl_c"] or 0) > 0)
        rows[bot] = {"pos": len(pos), "games": len(games), "won": won,
                     "staked": staked, "profit": profit,
                     "contracts": contracts}
        print(f"{bot:<22} {len(pos):>4} {len(games):>6} {won:>4} "
              f"{staked:>9.2f} {profit:>9.2f} "
              f"{100*profit/staked if staked else 0:>7.1f}% "
              f"{100*profit/contracts if contracts else 0:>10.2f}")

    tot_s = sum(r["staked"] for r in rows.values())
    tot_p = sum(r["profit"] for r in rows.values())
    tot_n = sum(r["pos"] for r in rows.values())
    print(f"\n{'ALL BOTS':<22} {tot_n:>4} {'':>6} {'':>4} {tot_s:>9.2f} "
          f"{tot_p:>9.2f} {100*tot_p/tot_s if tot_s else 0:>7.1f}%")

    # ------------------------------------------- 2. does free map to hold's games
    print("\n## 2. DOES `free` TRADE THE SAME GAMES AS `hold`?\n")
    for fam in ("starter", "early", "bullpen", "park-air"):
        g = {}
        for mode in ("hold", "exit-once", "free"):
            g[mode] = {r["game_key"] for r in q(con,
                       "SELECT DISTINCT game_key FROM positions WHERE bot=?",
                       (f"{fam}__{mode}",))}
        if not any(g.values()):
            continue
        same = g["hold"] == g["exit-once"] == g["free"]
        print(f"  {fam:<10} hold={len(g['hold'])} exit-once={len(g['exit-once'])} "
              f"free={len(g['free'])} games; identical sets: {same}")
        if not same:
            print(f"      free-only games: "
                  f"{sorted(g['free'] - g['hold'])[:4]}")

    # ------------------------------- 3. has the exit rule EVER changed anything?
    print("\n## 3. HAS THE EXIT RULE EVER CHANGED AN OUTCOME?\n")
    n_closed = q(con, "SELECT COUNT(*) c FROM positions "
                      "WHERE status='closed'")[0]["c"]
    n_settled = q(con, "SELECT COUNT(*) c FROM positions "
                       "WHERE status='settled'")[0]["c"]
    n_exitfills = q(con, "SELECT COUNT(*) c FROM fills "
                         "WHERE action='close'")[0]["c"]
    print(f"  positions that SETTLED (held to the end)  : {n_settled}")
    print(f"  positions CLOSED EARLY by an exit rule    : {n_closed}")
    print(f"  actual closing fills                      : {n_exitfills}")
    # Compare WITHIN a family. The first version matched `bot LIKE '%__hold'`
    # against `bot LIKE '%__exit-once'`, which cross-joins starter__hold with
    # early__exit-once wherever they traded the same game, and reported 24
    # spurious differences. Caught because the aggregate rows above show
    # starter__hold and starter__exit-once with IDENTICAL staked AND profit --
    # two totals that cannot both match if 24 positions differ. The internal
    # contradiction was the tell, not a second opinion.
    diffs = pairs = 0
    for fam in ("starter", "early", "bullpen", "park-air"):
        for r in q(con,
                   "SELECT a.pnl_c pa, b.pnl_c pb FROM positions a "
                   "JOIN positions b ON a.game_key=b.game_key "
                   "  AND a.ticker=b.ticker "
                   "WHERE a.bot=? AND b.bot=? "
                   "  AND a.status IN ('settled','closed') "
                   "  AND b.status IN ('settled','closed')",
                   (f"{fam}__hold", f"{fam}__exit-once")):
            pairs += 1
            if abs((r["pa"] or 0) - (r["pb"] or 0)) > 1e-9:
                diffs += 1
    print(f"  hold/exit-once pairs compared within family : {pairs}")
    print(f"  ...of which DIFFER                          : {diffs}")
    if n_closed == 0:
        print("\n  => The exit rule has NEVER fired. `hold` and `exit-once` are")
        print("     the SAME BOT with two names, and `free` is the same bot")
        print("     entering twice. Three names, one idea.")

    # -------------------------------------------------- 4. the luck arithmetic
    print("\n## 4. IS `starter` EXPLAINABLE BY LUCK?\n")
    sp = q(con, "SELECT contracts, entry_price_c, entry_fee_c, pnl_c "
                "FROM positions WHERE bot='starter__hold' "
                "AND status IN ('settled','closed')")
    if sp:
        n = len(sp)
        won = sum(1 for p in sp if (p["pnl_c"] or 0) > 0)
        avg_price = sum(p["entry_price_c"] * p["contracts"] for p in sp) / \
            max(1, sum(p["contracts"] for p in sp))
        # break-even win rate = price + fee, as a fraction of $1
        fee_per_c = sum(p["entry_fee_c"] for p in sp) / \
            max(1, sum(p["contracts"] for p in sp))
        breakeven = (avg_price + fee_per_c) / 100.0
        p_luck = binom_tail(won, n, breakeven)
        print(f"  games (one position per game)     : {n}")
        print(f"  won                               : {won}  "
              f"({100*won/n:.0f} out of 100)")
        print(f"  average buy price                 : {avg_price:.1f}c")
        print(f"  fee per contract                  : {fee_per_c:.2f}c")
        print(f"  break-even win rate               : "
              f"{100*breakeven:.1f} out of 100")
        print(f"  chance of {won}+ wins from {n} with NO edge : "
              f"{100*p_luck:.1f} out of 100  (1 in {1/p_luck:.1f})")
        fam = 5
        any_one = 1 - (1 - p_luck) ** fam
        print(f"  chance the BEST of {fam} families looks this good by luck: "
              f"{100*any_one:.0f} out of 100")

        # how many more games to reach 1-in-20 AFTER the 5-family correction
        print("\n  HOW MANY GAMES UNTIL IT STOPS BEING LUCK")
        print("  (keeping the same 63-out-of-100 rate, and correcting for the")
        print("   fact that five families were searched -- so a single family")
        print("   must reach 1 in 100 for the SET to reach about 1 in 20)")
        rate = won / n
        for target, label in ((0.01, "1 in 100 (set-wide ~1 in 20)"),
                              (0.002, "1 in 500 (set-wide ~1 in 100)")):
            need = None
            for m in range(n, 4000):
                k = math.ceil(rate * m)
                if binom_tail(k, m, breakeven) <= target:
                    need = m
                    break
            if need:
                per_day = _games_per_day(con, "starter__hold")
                extra = need - n
                days = extra / per_day if per_day else float("inf")
                when = (datetime.now(timezone.utc)
                        + timedelta(days=days)).date().isoformat()
                print(f"    {label:<30} needs {need:>4} games "
                      f"({extra:>4} more, ~{days:.0f} days, about {when})")
            else:
                print(f"    {label:<30} not reached below 4,000 games")

    # ------------------------------------------------------- 5. park-air famine
    print("\n## 5. `park-air` -- STARVATION OR CORRECT ABSTENTION?\n")
    dec = q(con, "SELECT reasoning_json FROM decisions "
                 "WHERE mentality='park-air' AND kind IN ('decline','shadow')")
    import json
    reasons = defaultdict(int)
    adj = []
    for r in dec:
        try:
            d = json.loads(r["reasoning_json"])
        except json.JSONDecodeError:
            continue
        reasons[d.get("reason", "?")] += 1
        a = (d.get("detail") or {}).get("adjustment_c")
        if a is not None:
            adj.append(abs(a))
    print(f"  park-air decisions that were NOT entries: {len(dec)}")
    for k, v in sorted(reasons.items(), key=lambda x: -x[1])[:6]:
        print(f"    {v:>5}  {k}")
    if adj:
        adj.sort()
        print(f"  its stated adjustment, when it had one: "
              f"median {adj[len(adj)//2]:.2f}c, "
              f"p90 {adj[int(0.9*len(adj))]:.2f}c, max {adj[-1]:.2f}c")
        print(f"  it needs roughly 3.5c to clear its own cost bar.")
    con.close()


def _games_per_day(con, bot):
    rows = q(con, "SELECT MIN(opened_utc) a, MAX(opened_utc) b, "
                  "COUNT(DISTINCT game_key) n FROM positions WHERE bot=?",
             (bot,))[0]
    if not rows["a"]:
        return 0.0
    span = (datetime.fromisoformat(rows["b"])
            - datetime.fromisoformat(rows["a"])).total_seconds() / 86400
    return rows["n"] / span if span > 0.5 else rows["n"]


if __name__ == "__main__":
    main()
