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
# ⚠ FROM is OPENING DAY, not the start of the tape. The first version began
# 2026-06-01, so `records_as_of` counted only June onward and handed `early` a
# team record built from a third of a season. The replayed `early` then backed
# the same club as the live bot on just 24 of 54 shared games -- a coin flip.
# `early`'s whole input is the season win rate, so a truncated season is not a
# smaller sample, it is a different bot.
FROM, TO = date(2026, 3, 15), date(2026, 9, 2)

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
    # ⚠ REGULAR SEASON ONLY. The cache reaches back to 15 March to get the
    # full season, which also swept in 133 spring-training and 7 exhibition
    # games. Counting those put every team about 10 games ahead of its real
    # record -- checked against the records the LIVE bot stored in its own
    # decision log, where 0 of 272 matched and every one was high by the same
    # amount. Standings count gameType 'R' and nothing else.
    for r in con.execute(
            "SELECT game_date, away_id, home_id, away_runs, home_runs, status "
            "FROM game WHERE json_extract(raw,'$.gameType')='R' "
            "ORDER BY game_date"):
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


# ===================================================================
# The replay itself.
#
# Both mentalities are re-implemented here against archive inputs rather than
# against a live brief. That is a real risk -- a re-implementation can drift
# from the thing it claims to replay -- so `--verify` re-runs this code over
# the FORWARD games and checks it reproduces what the live bots actually did.
# A replay that cannot reproduce the live decisions is not evidence.
#
# ⚠ Both use `season_era_asof`, never `season_era`. See the warning in
# statsapi.starter_profile: the unfiltered field would tell a June game how
# August turned out, and `starter`'s whole signal is recent-minus-season.
# ===================================================================
import math                                            # noqa: E402
from datetime import datetime, timezone                # noqa: E402

import mentalities as M                                # noqa: E402
from common.kalshi_fees import fee_order_cents         # noqa: E402

TRUTH = HERE.parent / "data" / "kalshi_truth.db"
_prof_cache = {}
_recs_cache = {}


def profile(pid, as_of):
    key = (pid, as_of.date())
    if key not in _prof_cache:
        try:
            _prof_cache[key] = S.starter_profile(pid, 2026, as_of)
        except Exception:                               # noqa: BLE001
            _prof_cache[key] = None
    return _prof_cache[key]


def quote(tcon, ticker, at_ts, tol=5400):
    """Real bid and ask at a moment. None if the tape does not cover it."""
    r = tcon.execute(
        "SELECT end_ts, yes_bid_close_c b, yes_ask_close_c a FROM candle "
        "WHERE ticker=? AND yes_bid_close_c IS NOT NULL AND "
        "yes_ask_close_c IS NOT NULL ORDER BY ABS(end_ts-?) LIMIT 1",
        (ticker, at_ts)).fetchone()
    if not r or abs(r["end_ts"] - at_ts) > tol:
        return None
    return {"bid": r["b"], "ask": r["a"], "spread": r["a"] - r["b"]}


def decide_early(recs, sa, sh, q_home, q_away):
    """m4_early, on archive inputs. Same constants, as-of ERA."""
    (aw, al), (hw, hl) = recs
    if aw + al == 0 or hw + hl == 0:
        return None
    g = M.M4_SHRINK_GAMES
    pa = (aw + g / 2.0) / (aw + al + g)
    ph = (hw + g / 2.0) / (hw + hl + g)
    diff = (math.log(ph / (1 - ph)) - math.log(pa / (1 - pa))
            + M.M4_HOME_FIELD_LOGIT)
    for prof_, sgn in ((sh, 1.0), (sa, -1.0)):
        era = (prof_ or {}).get("season_era_asof")
        if era is not None:
            diff += sgn * (4.20 - float(era)) * M.M4_LOGIT_PER_ERA_RUN
    fair_home = 100.0 / (1.0 + math.exp(-diff))
    best = None
    for side, fair, q in (("home", fair_home, q_home),
                          ("away", 100 - fair_home, q_away)):
        if q is None or q["spread"] > M.M4_MAX_SPREAD_C:
            continue
        price = q["ask"]                       # buying YES pays the ASK
        fee = float(fee_order_cents(price, 1))
        edge = fair - price - fee - M.SLIPPAGE_C
        if best is None or edge > best["edge"]:
            best = {"side": side, "edge": edge, "price": price,
                    "fair": round(fair, 2)}
    if best is None or best["edge"] < M.M4_BAR_C:
        return None
    return best


def decide_starter(sa, sh, q_home, q_away):
    """m1_starter, on archive inputs. Same constants, as-of ERA."""
    runs = 0.0
    for prof_, sgn in ((sh, +1.0), (sa, -1.0)):
        if not prof_:
            return None
        rec, sea = prof_.get("recent_era"), prof_.get("season_era_asof")
        if rec is None or sea is None:
            return None
        d = rec - sea
        prior = prof_.get("career_starts_prior") or 0
        rec_ip = prof_.get("recent_ip") or 0.0
        usable = (prior >= M.M1_MIN_PRIOR_STARTS_FOR_FORM
                  and rec_ip >= M.M1_MIN_RECENT_IP_FOR_FORM)
        if abs(d) >= M.M1_MIN_DIVERGENCE_ER9 and usable:
            runs += sgn * (-d) * (M.M1_C_PER_ER9 / M.CENTS_PER_RUN_MARGIN)
        if prof_.get("is_debut_or_near"):
            runs -= sgn * M.M1_DEBUT_RUNS
        rd = prof_.get("rest_days")
        if rd is not None and rd < 4:
            runs -= sgn * M.M1_SHORT_REST_RUNS
    adj = runs * M.CENTS_PER_RUN_MARGIN
    if adj == 0:
        return None
    side = "home" if adj > 0 else "away"
    q = q_home if side == "home" else q_away
    if q is None:
        return None
    price = q["ask"]
    fee = float(fee_order_cents(price, 1))
    edge = abs(adj) - fee - M.SLIPPAGE_C - q["spread"] / 2.0
    if edge < M.M1_BAR_C:
        return None
    return {"side": side, "edge": edge, "price": price,
            "fair": round(price + abs(adj), 2)}


def run_replay(limit=None):
    """Replay both mentalities over the archive and rebuild the buckets."""
    con = cache()
    tcon = sqlite3.connect(f"file:{TRUTH}?mode=ro", uri=True)
    tcon.row_factory = sqlite3.Row
    tape = collections.defaultdict(dict)
    for r in tcon.execute("SELECT ticker, game_date, away, home, suffix "
                          "FROM market WHERE series='KXMLBGAME'"):
        tape[(r["game_date"], r["away"], r["home"])][r["suffix"]] = r["ticker"]
    recs = records_as_of(con)
    games = con.execute(
        "SELECT * FROM game WHERE status='Final' AND away_runs IS NOT NULL "
        "AND away_prob_id IS NOT NULL AND home_prob_id IS NOT NULL "
        "ORDER BY game_date").fetchall()
    if limit:
        games = games[:limit]

    out = []
    for i, g in enumerate(games, 1):
        # ⚠ DATE-TOLERANT JOIN. The tape's `game_date` is the UTC date of
        # first pitch; MLB's is the LOCAL date. A 21:40 ET game is therefore
        # the NEXT day in the tape, and an exact join silently dropped 114 of
        # 788 in-window games -- disproportionately night games, which is a
        # biased sample, not just a smaller one.
        tk = None
        for off in (0, 1, -1):
            d2 = (date.fromisoformat(g["game_date"])
                  + timedelta(days=off)).isoformat()
            tk = tape.get((d2, g["away_code"], g["home_code"]))
            if tk:
                break
        if not tk:
            continue
        th = tk.get(g["home_code"])
        ta = tk.get(g["away_code"])
        if not th or not ta:
            continue
        st = datetime.fromisoformat(g["starts_utc"].replace("Z", "+00:00"))
        sts = int(st.timestamp())
        r = recs.get(g["game_date"], {})
        ra, rh = r.get(g["away_id"]), r.get(g["home_id"])
        if not ra or not rh:
            continue
        home_won = g["home_runs"] > g["away_runs"]

        # early decides at T-48h; starter at T-6h
        e_as = datetime.fromtimestamp(sts - 48 * 3600, timezone.utc)
        s_as = datetime.fromtimestamp(sts - 6 * 3600, timezone.utc)
        row = {"game": f"{g['game_date']}:{g['away_code']}@{g['home_code']}",
               "home_won": home_won}
        # ⚠ EVERY window the live bot uses, in order, taking the FIRST that
        # fires -- which is what the live engine does. The first version tested
        # one window each and reproduced the live bots on only 56-63% of shared
        # games. A bot given one chance a day to fire is a different bot from
        # one given three.
        WINDOWS = {"early": (48, 24), "starter": (24, 6, 3)}
        for tag in ("early", "starter"):
            d = None
            for hrs in WINDOWS[tag]:
                at = sts - hrs * 3600
                as_of = datetime.fromtimestamp(at, timezone.utc)
                qh, qa = quote(tcon, th, at), quote(tcon, ta, at)
                sa = profile(g["away_prob_id"], as_of)
                sh = profile(g["home_prob_id"], as_of)
                # ⚠ Records as of the DECISION, not the game. `early` decides
                # 48h out, so the table it sees is two days stale relative to
                # first pitch. Using the game-date table left every record 1-2
                # games high against the live bot's own log.
                # timestamp-precise, not date-precise -- see records_before.
                # Date granularity was wrong by exactly one game on 15 of the
                # games checked against the live bot's own log; this took
                # record fidelity from 0% exact to 97% (307 of 315).
                key = as_of.isoformat()
                if key not in _recs_cache:
                    _recs_cache[key] = records_before(con, key)
                r2 = _recs_cache[key]
                ra2, rh2 = r2.get(g["away_id"], ra), r2.get(g["home_id"], rh)
                d = (decide_early((ra2, rh2), sa, sh, qh, qa)
                     if tag == "early" else decide_starter(sa, sh, qh, qa))
                if d:
                    break
            row[tag] = d
        out.append(row)
        if i % 100 == 0:
            print(f"  {i}/{len(games)} games, {len(out)} replayed")
    tcon.close()
    con.close()
    return out


def pnl(d, home_won):
    """Money on one contract, real ask in, settle at 100 or 0, one fee."""
    if d is None:
        return None
    won = home_won if d["side"] == "home" else not home_won
    paid = d["price"] / 100.0 + float(fee_order_cents(d["price"], 1)) / 100.0
    return (1.0 if won else 0.0) - paid


def verify():
    """Does this re-implementation reproduce what the LIVE bots actually did?

    ⚠ THIS GATES EVERYTHING ELSE IN THIS FILE. The archive result contradicts
    mailbox 020, and a re-implementation that has quietly drifted would produce
    exactly that kind of contradiction. If the replay cannot reproduce the live
    decisions on the games where both exist, the archive numbers are a fact
    about this file and not about baseball.
    """
    import engine as E
    live = E.connect()
    real = {}
    for r in live.execute(
            "SELECT bot, game_key, ticker, side FROM positions "
            "WHERE bot IN ('starter__hold','early__hold')"):
        real.setdefault(r["game_key"], {})[r["bot"].split("__")[0]] = r["ticker"]
    out = run_replay()
    agree = {"starter": [0, 0], "early": [0, 0]}
    for o in out:
        gk = o["game"]
        if gk not in real:
            continue
        for m in ("starter", "early"):
            mine, theirs = o[m], real[gk].get(m)
            if theirs is None and mine is None:
                continue
            agree[m][1] += 1
            if theirs is not None and mine is not None:
                # same club backed?
                agree[m][0] += int(theirs.endswith(
                    gk.split("@")[1] if mine["side"] == "home"
                    else gk.split(":")[1].split("@")[0]))
    live.close()
    return agree, len(real)

def records_before(con, ts_utc, game_end_hours=3.25):
    """W-L for every team as of an exact MOMENT, not a date.

    ⚠ Date-granularity records were wrong by exactly one game on 15 of the
    games checked against the live bot's own log. A decision taken at 18:00
    sees games that finished that afternoon; a decision at 02:00 UTC is the
    previous evening locally and does not. `records_as_of` cuts on the date and
    cannot express either.

    A game counts once it has plausibly FINISHED -- first pitch plus
    `game_end_hours`. That is an approximation, and it is a much smaller one
    than a whole day.
    """
    from datetime import datetime as _dt
    cut = _dt.fromisoformat(ts_utc).timestamp() - game_end_hours * 3600
    rec = collections.defaultdict(lambda: [0, 0])
    for r in con.execute(
            "SELECT away_id, home_id, away_runs, home_runs, starts_utc "
            "FROM game WHERE status='Final' AND away_runs IS NOT NULL "
            "AND json_extract(raw,'$.gameType')='R'"):
        try:
            st = _dt.fromisoformat(r["starts_utc"].replace("Z", "+00:00"))
        except (TypeError, ValueError, AttributeError):
            continue
        if st.timestamp() > cut:
            continue
        aw = r["away_runs"] > r["home_runs"]
        rec[r["away_id"]][0 if aw else 1] += 1
        rec[r["home_id"]][1 if aw else 0] += 1
    return {t: tuple(v) for t, v in rec.items()}
