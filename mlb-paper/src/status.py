"""One command that answers "is this alive and what has it done".

    python src/status.py            # the whole picture
    python src/status.py --brief    # four lines, for a phone

Designed to be the ONLY thing anyone has to run. `bot-hunt`'s recorder died for
2.5 hours with zero bytes in its error log and nothing noticed, because nothing
was watching. This is what watches.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as E                              # noqa: E402

ROOT = HERE.parent
STALE_MIN = 20


def _age_min(iso):
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).total_seconds() / 60.0


def health(con):
    hb = {r["k"]: r["v"] for r in
          con.execute("SELECT k, v FROM heartbeat").fetchall()}
    last = hb.get("last_tick_utc")
    age = _age_min(last)
    lock = ROOT / "data" / "runner.lock"
    lock_pid = None
    if lock.exists():
        try:
            lock_pid = json.loads(lock.read_text()).get("pid")
        except (json.JSONDecodeError, OSError):
            pass
    alive = age is not None and age < STALE_MIN
    return {"last_tick_utc": last, "age_min": None if age is None else round(age, 1),
            "alive": alive, "lock_pid": lock_pid,
            "last_error_utc": hb.get("last_error_utc"),
            "last_tick_elapsed_s": hb.get("last_tick_elapsed_s")}


def report(con, brief_only=False):
    h = health(con)
    flag = "ALIVE " if h["alive"] else "*** STALE ***"
    print(f"{flag} last tick {h['last_tick_utc']} "
          f"({h['age_min']} min ago)  pid={h['lock_pid']}  "
          f"tick took {h['last_tick_elapsed_s']}s")
    if h["last_error_utc"]:
        print(f"  last error: {h['last_error_utc']}  "
              f"(see logs/run.log)")

    t = con.execute(
        "SELECT COUNT(*) n, MIN(ts_utc) a, MAX(ts_utc) b FROM ticks"
    ).fetchone()
    dec = con.execute(
        "SELECT kind, COUNT(*) n FROM decisions GROUP BY kind").fetchall()
    pos = con.execute(
        "SELECT status, COUNT(*) n, SUM(contracts) c FROM positions "
        "GROUP BY status").fetchall()
    settled = con.execute(
        "SELECT COUNT(*) n FROM positions WHERE status='settled'").fetchone()["n"]
    print(f"ticks {t['n']}  ({t['a']} -> {t['b']})   "
          f"decisions: " + " ".join(f"{r['kind']}={r['n']}" for r in dec)
          + "   positions: "
          + " ".join(f"{r['status']}={r['n']}" for r in pos))

    if brief_only:
        pnl = con.execute(
            "SELECT COALESCE(SUM(pnl_c),0)/100.0 p FROM positions "
            "WHERE status IN ('closed','settled')").fetchone()["p"]
        print(f"settled positions {settled}   paper P&L ${pnl:.2f}   "
              f"(PAPER ONLY - no money exists in this system)")
        return

    print("\n-- per bot --")
    print(f"{'bot':<22} {'entries':>7} {'open':>5} {'settled':>7} "
          f"{'contracts':>9} {'pnl_$':>8} {'c/contract':>10} {'bankroll_$':>10}")
    rows = con.execute(
        "SELECT bot, "
        "  SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) o, "
        "  SUM(CASE WHEN status='settled' THEN 1 ELSE 0 END) s, "
        "  SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) c, "
        "  COUNT(*) n, SUM(contracts) k, "
        "  COALESCE(SUM(pnl_c),0) p "
        "FROM positions GROUP BY bot ORDER BY bot").fetchall()
    seen = set()
    for r in rows:
        seen.add(r["bot"])
        done = (r["s"] or 0) + (r["c"] or 0)
        per = (r["p"] / r["k"]) if r["k"] else 0.0
        print(f"{r['bot']:<22} {r['n']:>7} {r['o'] or 0:>5} {done:>7} "
              f"{r['k'] or 0:>9} {r['p']/100.0:>8.2f} {per:>10.2f} "
              f"{E.bankroll(con, r['bot']):>10.2f}")
    import mentalities as MEN
    for b in MEN.BOT_IDS:
        if b not in seen:
            print(f"{b:<22} {'0':>7} {'0':>5} {'0':>7} {'0':>9} "
                  f"{'0.00':>8} {'-':>10} {E.bankroll(con, b):>10.2f}")

    print("\n-- decisions by mentality and outcome --")
    for r in con.execute(
            "SELECT mentality, kind, COUNT(*) n FROM decisions "
            "GROUP BY mentality, kind ORDER BY mentality, kind").fetchall():
        print(f"  {r['mentality']:<12} {r['kind']:<9} {r['n']}")

    print("\n-- why bots declined (top reasons) --")
    import collections
    c = collections.Counter()
    for r in con.execute(
            "SELECT reasoning_json FROM decisions WHERE kind IN "
            "('decline','shadow') ORDER BY ts_utc DESC LIMIT 4000").fetchall():
        try:
            d = json.loads(r["reasoning_json"])
        except json.JSONDecodeError:
            continue
        if "reason" in d:
            c[f"{d.get('mentality')}: {d['reason']}"] += 1
    for k, v in c.most_common(12):
        print(f"  {v:>5}  {k}")

    print("\n-- market health, last 12 ticks --")
    for r in con.execute(
            "SELECT * FROM ticks ORDER BY ts_utc DESC LIMIT 12").fetchall():
        n = json.loads(r["notes"] or "{}")
        print(f"  {r['ts_utc']}  pool={r['games_in_pool']:<3} "
              f"mkts={r['markets_seen']:<4} ask={r['markets_with_ask']:<4} "
              f"leak={r['leaked_filtered']:<3} ent={r['entries']:<3} "
              f"shd={r['shadows']:<3} fill={n.get('filled', 0):<3} "
              f"cls={r['closes']:<3} set={n.get('settled', 0):<3} "
              f"alert={r['errors']:<2} {n.get('elapsed_s')}s"
              + ("  PIN_ERR" if n.get("pin_error") else ""))

    print("\n-- closing-line value so far (PRIMARY endpoint) --")
    clv = clv_table(con)
    if not clv:
        print("  no settled reference yet")
    for row in clv:
        print(f"  {row['bot']:<22} n={row['n']:<4} mean CLV "
              f"{row['mean_clv_c']:>7.2f}c   [{row['lo']:>6.2f}, "
              f"{row['hi']:>6.2f}]")

    print("\nPAPER ONLY. No credential is read, no order endpoint exists, "
          "and no money is at risk.")


def clv_table(con):
    """Mean closing-line value per bot, game-clustered bootstrap interval.

    CLV = (de-vigged sharp fair at the LAST mark before first pitch)
          - (the executable price the bot actually paid).
    Positive means the bot bought below where the sharp line ended.
    """
    import random
    import statistics
    rows = con.execute(
        "SELECT f.bot, f.game_key, f.ticker, f.price_c, f.side "
        "FROM fills f WHERE f.action='open'").fetchall()
    by_bot = {}
    for r in rows:
        close = con.execute(
            "SELECT sharp_fair_yes_c FROM marks WHERE ticker=? AND "
            "sharp_fair_yes_c IS NOT NULL ORDER BY ts_utc DESC LIMIT 1",
            (r["ticker"],)).fetchone()
        if not close or close["sharp_fair_yes_c"] is None:
            continue
        fair = close["sharp_fair_yes_c"]
        if r["side"] == "NO":
            fair = 100 - fair
        by_bot.setdefault(r["bot"], []).append((r["game_key"],
                                                fair - r["price_c"]))
    out = []
    rnd = random.Random(11)
    for bot, pts in sorted(by_bot.items()):
        games = {}
        for gk, v in pts:
            games.setdefault(gk, []).append(v)
        keys = list(games)
        vals = [statistics.mean(games[k]) for k in keys]
        if not vals:
            continue
        boots = []
        for _ in range(2000):
            s = [vals[rnd.randrange(len(vals))] for _ in vals]
            boots.append(statistics.mean(s))
        boots.sort()
        out.append({"bot": bot, "n": len(keys),
                    "mean_clv_c": statistics.mean(vals),
                    "lo": boots[int(0.025 * len(boots))],
                    "hi": boots[int(0.975 * len(boots))]})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    con = E.connect()
    if a.json:
        print(json.dumps({"health": health(con), "clv": clv_table(con)},
                         indent=2, default=str))
    else:
        report(con, brief_only=a.brief)
    con.close()
    sys.exit(0 if health(E.connect())["alive"] else 2)
