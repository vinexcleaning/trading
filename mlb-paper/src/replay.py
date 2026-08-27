"""Replay the mentalities over the rescued archive. Mailbox 022.

The forward test has 114 settled games and needs three more weeks for the next
handful. The rescued tape holds **798 distinct games** with real bid and ask
reaching ~72h before first pitch. No bot has ever seen any of them.

⚠ THE COUNT IN MAILBOX 022 IS WRONG AND THIS IS THE CORRECTION. It says 1,703
distinct games. The archive holds **1,753 who-wins MARKETS**, which is about two
per game -- counting markets as games roughly doubles the prize. Measured
distinct `away|home|date`: **798 for who-wins, 766 for totals, 798 combined.**
Still 7x the forward test, which is the point; just not 15x.

⚠ THE GATE, CHECKED FIRST AND IT PASSES. 022 asked whether `early` can be
replayed at all, since it bets before the professional bookmakers post a price.
**It can.** Its DECISION never used the sharp line -- reading `m4_early`, the
inputs are a shrunk season win rate, a fixed home-field term and a starter-ERA
term, all public. The sharp line is only its scoring YARDSTICK. And the
re-pulled tape reaches 48h back on **95% of archive markets** (286 of 300
sampled), covering both of its windows.

⚠ POINT-IN-TIME RECORDS. `statsapi.standings()` returns standings as of TODAY,
which would hand every replayed game the end-of-season answer. Records are
rebuilt here by counting completed games strictly BEFORE each date. That is the
single largest leak this file could have had.

    python src/replay.py --build      # cache schedule + results
    python src/replay.py              # report what is cached
"""
from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import statsapi as S                                  # noqa: E402

CACHE = HERE.parent / "data" / "replay_cache.db"
FROM, TO = date(2026, 6, 1), date(2026, 8, 15)

SCHEMA = """
CREATE TABLE IF NOT EXISTS game (
  game_pk INTEGER PRIMARY KEY, game_date TEXT, starts_utc TEXT,
  away_id INTEGER, home_id INTEGER, away_name TEXT, home_name TEXT,
  away_code TEXT, home_code TEXT, status TEXT,
  away_runs INTEGER, home_runs INTEGER,
  away_prob_id INTEGER, home_prob_id INTEGER, raw TEXT);
CREATE INDEX IF NOT EXISTS ix_g_date ON game(game_date);
"""


def cache():
    con = sqlite3.connect(CACHE, timeout=120)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def build(con):
    n = 0
    d = FROM
    while d <= TO:
        try:
            days = S.schedule(d)
        except Exception as e:                          # noqa: BLE001
            print(f"  ! {d}: {type(e).__name__} {e}")
            d += timedelta(days=1)
            continue
        for g in days:
            tm = g.get("teams") or {}
            a, h = tm.get("away") or {}, tm.get("home") or {}
            con.execute(
                "INSERT OR REPLACE INTO game VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (g.get("gamePk"), str(d), g.get("gameDate"),
                 (a.get("team") or {}).get("id"),
                 (h.get("team") or {}).get("id"),
                 (a.get("team") or {}).get("name"),
                 (h.get("team") or {}).get("name"),
                 (a.get("team") or {}).get("abbreviation"),
                 (h.get("team") or {}).get("abbreviation"),
                 (g.get("status") or {}).get("abstractGameState"),
                 a.get("score"), h.get("score"),
                 (a.get("probablePitcher") or {}).get("id"),
                 (h.get("probablePitcher") or {}).get("id"),
                 json.dumps(g)[:20000]))
            n += 1
        con.commit()
        d += timedelta(days=1)
    return n


def records_as_of(con):
    """W-L for every team as of the START of each date. NO look-ahead."""
    out = {}
    rec = collections.defaultdict(lambda: [0, 0])
    by_date = collections.defaultdict(list)
    for r in con.execute("SELECT game_date, away_id, home_id, away_runs, "
                         "home_runs, status FROM game ORDER BY game_date"):
        by_date[r["game_date"]].append(r)
    for d in sorted(by_date):
        out[d] = {t: tuple(v) for t, v in rec.items()}      # BEFORE today
        for r in by_date[d]:
            if r["status"] != "Final" or r["away_runs"] is None:
                continue
            aw = r["away_runs"] > r["home_runs"]
            rec[r["away_id"]][0 if aw else 1] += 1
            rec[r["home_id"]][1 if aw else 0] += 1
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    a = ap.parse_args()
    con = cache()
    if a.build:
        print(f"caching schedule + results {FROM} -> {TO}")
        print(f"  {build(con)} games cached")
    g = con.execute(
        "SELECT COUNT(*) n, COUNT(DISTINCT game_date) d, "
        "SUM(status='Final') f, SUM(away_prob_id IS NOT NULL AND "
        "home_prob_id IS NOT NULL) p FROM game").fetchone()
    print(f"\ncached: {g['n']} games over {g['d']} dates, {g['f']} final, "
          f"{g['p']} with BOTH probable pitchers")
    rec = records_as_of(con)
    if rec:
        ds = sorted(rec)
        d = ds[len(ds) // 2]
        n = len(rec[d])
        tot = sum(sum(v) for v in rec[d].values())
        print(f"point-in-time records: as of {d}, {n} teams, "
              f"{tot} team-games counted (end of season would be ~{30*162})")
    con.close()
