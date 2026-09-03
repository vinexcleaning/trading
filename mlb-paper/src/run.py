"""The unattended runner. One tick every 300 s, resumes across a reboot.

    python src/run.py                 # run forever
    python src/run.py --once          # one tick, for a smoke test
    python src/run.py --dry-run       # decide and log, queue nothing

Each tick, in this order and for a reason:

  1. **Refresh the market** -- one paginated Kalshi read per series. Cheap, and
     it is what every later step is measured against.
  2. **Fill yesterday's intentions against TODAY'S book.** This happens BEFORE
     any new decision, so a decision can never fill at the price that triggered
     it. That single ordering is the latency model.
  3. **Mark every market**, with the de-vigged sharp price alongside, so
     closing-line value has a series to close against. CLV is the primary
     endpoint and it cannot be reconstructed later -- Kalshi's window is ~69
     days and closed markets 404 for good.
  4. **Manage exits** for the two modes that have them.
  5. **Decide**, but only for games inside a decision window, and only for
     games that have not started.
  6. **Settle** anything final, and stamp `outcome_known` on its decisions.
  7. **Heartbeat**, so `status.py` can answer "is this alive" in one command.

### The single-runner lock

`bot-hunt`'s recorder died for 2.5 hours with zero bytes in its error log and
nothing noticed. Two defences: a PID lock file that a second process refuses to
run past, and a heartbeat row that `status.py` reads. Neither is clever; both
were absent when it mattered.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# The repo root, derived from this file. NEVER a hardcoded home
# directory: this package is meant to run on the laptop, whose paths
# live under a different user, and a hardcoded desktop path would
# import nothing and fail at the first shared-fee call.
TRADING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRADING_ROOT))

import brief as BRIEF                 # noqa: E402
import engine as E                    # noqa: E402
import kalshi as K                    # noqa: E402
import mentalities as MEN             # noqa: E402
import pinnacle as PIN                # noqa: E402
import robots_check as ROBOTS         # noqa: E402
import statsapi as S                  # noqa: E402

ROOT = HERE.parent
LOCK = ROOT / "data" / "runner.lock"
LOGDIR = ROOT / "logs"
SERIES = ("KXMLBGAME", "KXMLBTOTAL")
TICK_S = 300
BRIEF_MAX_AGE_S = 1800


def log(msg):
    line = f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}"
    print(line, flush=True)
    LOGDIR.mkdir(parents=True, exist_ok=True)
    with open(LOGDIR / "run.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ------------------------------------------------------------------- the lock

def acquire_lock():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        try:
            d = json.loads(LOCK.read_text())
            pid = int(d.get("pid", -1))
        except (json.JSONDecodeError, ValueError, TypeError):
            pid = -1
        if pid > 0 and _alive(pid):
            raise SystemExit(
                f"another runner is alive (pid {pid}, started "
                f"{d.get('started_utc')}). Refusing to start a second. "
                f"Two runners would double every decision and silently halve "
                f"every per-game denominator.")
        log(f"stale lock from pid {pid}; taking it over")
    LOCK.write_text(json.dumps({"pid": os.getpid(),
                                "started_utc": E.now()}))


def _alive(pid):
    try:
        import subprocess
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=20).stdout
        return str(pid) in out
    except Exception:                       # noqa: BLE001
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def release_lock():
    try:
        LOCK.unlink(missing_ok=True)
    except OSError:
        pass


# ------------------------------------------------------------------- market

def read_market():
    """Every open MLB market, keyed by ticker, plus per-game grouping."""
    by_ticker, by_game, health = {}, {}, {
        "markets_seen": 0, "markets_with_ask": 0, "zero_ask": 0,
        "leaked_filtered": 0}
    now_utc = datetime.now(timezone.utc)
    for s in SERIES:
        try:
            mkts = K.markets(s)
        except RuntimeError as e:
            log(f"  ! kalshi {s}: {e}")
            continue
        for m in mkts:
            health["markets_seen"] += 1
            # GUARD #2: a market carrying a settlement result, or a game that
            # has already started, is removed BEFORE any bot can see it.
            if (m.get("result") or "").strip():
                health["leaked_filtered"] += 1
                continue
            p = K.ticker_parts(m["ticker"])
            if not p:
                continue
            if p["starts"] <= now_utc:
                health["leaked_filtered"] += 1
                continue
            t = K.touch(m)
            if not t:
                health["zero_ask"] += 1
                continue
            bid, ask, bsz, asz = t
            health["markets_with_ask"] += 1
            row = {"ticker": m["ticker"], "series": p["series"],
                   "suffix": p["suffix"], "yes_sub_title": m.get("yes_sub_title"),
                   "floor_strike": m.get("floor_strike"),
                   "bid": bid, "ask": ask, "mid": (bid + ask) / 2,
                   "spread": ask - bid, "bid_size": bsz, "ask_size": asz,
                   "game_key": p["game_key"], "starts": p["starts"],
                   "hours_to_start": round(
                       (p["starts"] - now_utc).total_seconds() / 3600, 3)}
            by_ticker[m["ticker"]] = row
            by_game.setdefault(p["game_key"], {}).setdefault(s, []).append(row)
    return by_ticker, by_game, health


def structural_alerts(by_game):
    """GUARD #18. Two impossibilities, alerted rather than silently absorbed."""
    alerts = []
    for gk, blocks in by_game.items():
        ml = blocks.get("KXMLBGAME") or []
        if len(ml) == 2 and (ml[0]["bid"] + ml[1]["bid"]) > 100:
            alerts.append(f"{gk}: complementary YES bids sum to "
                          f"{ml[0]['bid'] + ml[1]['bid']}c (>100 is impossible)")
        tot = sorted((r for r in (blocks.get("KXMLBTOTAL") or [])
                      if r.get("floor_strike") is not None),
                     key=lambda r: float(r["floor_strike"]))
        for a, b in zip(tot, tot[1:]):
            if a["mid"] < b["mid"] - 1e-9:
                alerts.append(
                    f"{gk}: Over {a['floor_strike']} ({a['mid']}c) is cheaper "
                    f"than Over {b['floor_strike']} ({b['mid']}c) -- a higher "
                    f"bar cannot be more likely")
    return alerts


def sharp_index():
    try:
        return PIN.games(), PIN.straight_markets(), None
    except RuntimeError as e:
        return {}, {}, str(e)


def sharp_fair_for(row, pin_games, pin_mkts):
    """The de-vigged sharp YES price for one Kalshi market row, or None.

    Recorded on every mark so that closing-line value has a reference series.
    Join requires club pair AND start time within 20 minutes -- a club-pair
    join matches the wrong day of a three-game series (measured: it produced a
    44-82% fake qualifying rate).
    """
    p = K.ticker_parts(row["ticker"])
    if not p:
        return None
    a, h = K.CODE.get(p["away"]), K.CODE.get(p["home"])
    if not a or not h:
        return None
    g = None
    for pg in pin_games.values():
        if not pg["starts"]:
            continue
        if a in (pg["away"] or "") and h in (pg["home"] or ""):
            if abs((pg["starts"] - p["starts"]).total_seconds()) <= 20 * 60:
                g = pg
                break
    if g is None:
        return None
    mk = PIN.markets_for(g, pin_mkts)
    if p["series"] == "KXMLBGAME":
        ml = mk.get("moneyline")
        if not ml:
            return None
        want = "home" if (p["suffix"] or "").upper() == p["home"] else "away"
        tgt = next((x for x in ml["prices"]
                    if str(x.get("designation", "")).lower() == want), None)
        oth = next((x for x in ml["prices"]
                    if str(x.get("designation", "")).lower()
                    == ("away" if want == "home" else "home")), None)
        if not tgt or not oth:
            return None
        fa, _, _ = PIN.devig(PIN.american_to_prob(tgt["price"]),
                             PIN.american_to_prob(oth["price"]))
        return round(fa * 100, 3)
    if p["series"] == "KXMLBTOTAL" and row.get("floor_strike") is not None:
        for t in mk.get("totals", []):
            ou = PIN.over_under(t)
            if not ou:
                continue
            o, u, pts = ou
            if pts is None or abs(float(pts) - float(row["floor_strike"])) > 1e-6:
                continue
            fo, _, _ = PIN.devig(PIN.american_to_prob(o),
                                 PIN.american_to_prob(u))
            return round(fo * 100, 3)
    return None


# ------------------------------------------------------------------- briefs

_BRIEF_CACHE: dict[str, tuple[float, dict]] = {}
MAX_BRIEFS_PER_TICK = 4
BRIEF_DIR = ROOT / "data" / "briefs"


def _cache_load(gk):
    """The brief cache lives on disk, not only in memory.

    Two reasons. It has to survive a reboot -- the whole package is supposed to
    run unattended on a laptop that may restart. And a brief is the exact
    evidence a bot saw when it decided, so it is a record, not a performance
    trick: `decisions.reasoning_json` refers to it and it must still exist when
    someone asks months later what the bot was looking at.
    """
    if gk in _BRIEF_CACHE:
        return _BRIEF_CACHE[gk]
    f = BRIEF_DIR / (gk.replace(":", "_").replace("@", "_at_") + ".json")
    if not f.exists():
        return None
    try:
        d = json.loads(f.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    rec = (f.stat().st_mtime, d)
    _BRIEF_CACHE[gk] = rec
    return rec


def _cache_store(gk, b):
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    f = BRIEF_DIR / (gk.replace(":", "_").replace("@", "_at_") + ".json")
    f.write_text(json.dumps(b, indent=1, default=str))
    _BRIEF_CACHE[gk] = (time.time(), b)


def _needs_for(window):
    """Which expensive blocks this window's mentalities actually read.

    The bullpen block is ~20 boxscore reads per team and nothing reads it
    before T-6 h; the lineup block is a live boxscore and nothing reads it
    before T-90 m. Building them anyway is what made the first tick take
    618.9 s against a 300 s interval.
    """
    n = set()
    if window in ("T-6h", "T-3h", "T-90m"):
        n |= {"bullpen", "weather"}
    if window in ("T-90m", "T-30m"):
        n.add("lineup")
    if window in ("T-48h", "T-24h"):
        n.add("weather")          # cheap, and P5 measures TAF coverage by lead
    return n


def briefs_for(needed_windows, as_of):
    """Briefs for games in a decision window, rebuilt at most every 30 min.

    `needed_windows` is {game_key: window}. At most MAX_BRIEFS_PER_TICK games
    are (re)built per tick so a tick can never overrun its own interval; the
    rest are picked up on a later tick, which loses nothing because a starter's
    game log and a bullpen's rest do not change inside half an hour.

    Freshness is prioritised by how close the game is: a T-30m game is rebuilt
    before a T-48h one, because that is where a stale brief would matter.
    """
    stale = []
    for gk in needed_windows:
        rec = _cache_load(gk)
        if rec is None or (time.time() - rec[0]) > BRIEF_MAX_AGE_S:
            stale.append(gk)
    order = {"T-30m": 0, "T-90m": 1, "T-3h": 2, "T-6h": 3, "T-24h": 4,
             "T-48h": 5}
    stale.sort(key=lambda gk: order.get(needed_windows[gk], 9))
    stale = stale[:MAX_BRIEFS_PER_TICK]

    by_day = {}
    for gk in stale:
        by_day.setdefault(gk.split(":")[0], []).append(gk)
    for d, keys in sorted(by_day.items()):
        needs = set()
        for gk in keys:
            needs |= _needs_for(needed_windows[gk])
        try:
            built = BRIEF.build_for_day(
                datetime.fromisoformat(d).date(), as_of=as_of,
                only_keys=set(keys), needs=needs)
        except Exception as e:                          # noqa: BLE001
            log(f"  ! brief build for {d}: {e}")
            continue
        got = {b.get("kalshi_game_key") for b in built}
        for miss in set(keys) - got:
            log(f"  . brief unavailable for {miss} (no schedule match)")
        for b in built:
            gk = b.get("kalshi_game_key")
            if gk:
                _cache_store(gk, b)

    fresh = {}
    for gk in needed_windows:
        rec = _cache_load(gk)
        if rec:
            b = dict(rec[1])
            # the cached brief was built at an earlier instant; the hours-to-
            # first-pitch must be recomputed or a bot would act in the wrong
            # window on stale arithmetic
            try:
                starts = datetime.fromisoformat(b["starts_utc"])
                b["hours_to_first_pitch"] = round(
                    (starts - as_of).total_seconds() / 3600, 3)
                b["brief_age_s"] = round(time.time() - rec[0])
            except (KeyError, ValueError):
                pass
            fresh[gk] = b
    return fresh


# --------------------------------------------------------------- the decisions

def decide(con, briefs, by_game, dry_run=False):
    entries = shadows = 0
    for gk, b in briefs.items():
        b = dict(b)
        b["market"] = dict(b.get("market") or {})
        b["market"]["kalshi"] = by_game.get(gk, {})
        hours = b.get("hours_to_first_pitch")
        if hours is None or hours <= 0:
            continue
        window = MEN.window_for(hours)
        if window is None:
            continue
        for mentality, fn in MEN.MENTALITIES.items():
            if window not in MEN.WINDOWS_FOR[mentality]:
                continue
            try:
                res = fn(b, window)
            except Exception as e:                      # noqa: BLE001
                log(f"  ! {mentality} on {gk}: {e}")
                continue

            if isinstance(res, MEN.Decline):
                # a view that exists but does not clear the cost bar becomes a
                # SHADOW: reasoning and price recorded, no position, no stake.
                adj = abs((res.detail or {}).get("adjustment_c") or 0.0)
                if (res.reason.startswith("adjustment does not survive")
                        or res.reason.startswith("crude public prior does not")) \
                        and adj >= E.SHADOW_MIN_ADJUSTMENT_C:
                    for mode in MEN.EXIT_MODES:
                        pass    # a shadow is mode-independent; record once
                    E.record_decision(
                        con, bot=f"{mentality}__shadow", mentality=mentality,
                        exit_mode="shadow", brief=b, window=window,
                        kind="shadow", decline=res)
                    shadows += 1
                else:
                    E.record_decision(
                        con, bot=f"{mentality}__decline", mentality=mentality,
                        exit_mode="decline", brief=b, window=window,
                        kind="decline", decline=res)
                continue

            intent = res

            # the 17th bot: the opposite side of `bullpen` (mailbox 020).
            # Paper, hold-only, and deliberately NOT given the three exit modes
            # -- one new bot, not three, so the multiplicity does not grow.
            if mentality == MEN.INVERSE_OF:
                inv = MEN.invert_intent(b, intent)
                if inv is not None:
                    ibot = f"{MEN.INVERSE_NAME}__hold"
                    iok, iwhy = E.may_enter(con, ibot, gk, "hold")
                    if iok:
                        ibank = E.bankroll(con, ibot)
                        istake = E.stake_for(ibank, inv.edge_c or 0.0,
                                             inv.entry_price_c)
                        inn = E.contracts_for(istake, inv.entry_price_c,
                                              inv.top_of_book_size)
                        if inn >= 1:
                            idid = E.record_decision(
                                con, bot=ibot, mentality=MEN.INVERSE_NAME,
                                exit_mode="hold", brief=b, window=window,
                                kind="entry", intent=inv, stake_usd=istake)
                            if not dry_run:
                                E.queue_open(con, decision_id=idid, bot=ibot,
                                             brief=b, intent=inv, contracts=inn)
                            entries += 1

            # the control sees the identical intent and takes nothing
            E.record_decision(con, bot="control__no-trade", mentality=mentality,
                              exit_mode="no-trade", brief=b, window=window,
                              kind="control", intent=intent)
            for mode in MEN.EXIT_MODES:
                bot = f"{mentality}__{mode}"
                ok, why = E.may_enter(con, bot, gk, mode)
                if not ok:
                    E.record_decision(
                        con, bot=bot, mentality=mentality, exit_mode=mode,
                        brief=b, window=window, kind="decline",
                        decline=MEN.Decline(mentality, why or "not permitted",
                                            {"ticker": intent.ticker}))
                    continue
                bank = E.bankroll(con, bot)
                stake = E.stake_for(bank, intent.edge_c or 0.0,
                                    intent.entry_price_c)
                n = E.contracts_for(stake, intent.entry_price_c,
                                    intent.top_of_book_size)
                cap = E.reentry_size_cap(con, bot, gk)
                if cap is not None:
                    n = min(n, cap)     # a re-entry is never larger than the first
                if n < 1:
                    E.record_decision(
                        con, bot=bot, mentality=mentality, exit_mode=mode,
                        brief=b, window=window, kind="decline",
                        decline=MEN.Decline(
                            mentality, "sizing produced zero contracts",
                            {"bankroll": round(bank, 2), "stake_usd": stake,
                             "book_size": intent.top_of_book_size,
                             "depth_cap_frac": E.DEPTH_CAP_FRAC}))
                    continue
                did = E.record_decision(
                    con, bot=bot, mentality=mentality, exit_mode=mode, brief=b,
                    window=window, kind="entry", intent=intent,
                    stake_usd=stake)
                if not dry_run:
                    E.queue_open(con, decision_id=did, bot=bot, brief=b,
                                 intent=intent, contracts=n)
                entries += 1
    con.commit()
    return entries, shadows


# ------------------------------------------------------------------ settling

def settle(con):
    pks = [r["game_pk"] for r in con.execute(
        "SELECT DISTINCT game_pk FROM positions WHERE status='open' "
        "AND game_pk IS NOT NULL").fetchall()]
    got = {}
    for pk in pks:
        try:
            f = S.final_score(pk)
        except RuntimeError:
            continue
        if f and f["is_final"]:
            got[pk] = f
            con.execute(
                "INSERT OR REPLACE INTO settlements (game_pk, game_key, "
                "settled_utc, away_runs, home_runs, total_runs, "
                "first_inning_runs, raw_json) VALUES (?,?,?,?,?,?,?,?)",
                (pk, "", E.now(), f["away_runs"], f["home_runs"],
                 f["total_runs"], f["first_inning_runs"], json.dumps(f)))
    n = E.settle_open_positions(con, got) if got else 0
    if got:
        con.execute(
            "UPDATE decisions SET outcome_known=1 WHERE game_pk IN "
            "(%s)" % ",".join("?" * len(got)), tuple(got))
    con.commit()
    return n, len(got)


# ---------------------------------------------------------------- one tick

def tick(con, dry_run=False):
    t0 = time.time()
    as_of = datetime.now(timezone.utc)
    by_ticker, by_game, health = read_market()
    E.load_strikes(list(by_ticker.values()))

    filled, expired = (0, 0) if dry_run else E.fill_pending(con, by_ticker)
    pin_games, pin_mkts, pin_err = sharp_index()

    for row in by_ticker.values():
        con.execute(
            "INSERT OR REPLACE INTO marks (ts_utc, game_key, ticker, bid, ask, "
            "bid_size, ask_size, hours_to_start, sharp_fair_yes_c) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (as_of.isoformat(timespec="seconds"), row["game_key"],
             row["ticker"], row["bid"], row["ask"], row["bid_size"],
             row["ask_size"], row["hours_to_start"],
             sharp_fair_for(row, pin_games, pin_mkts)))
    con.commit()

    alerts = structural_alerts(by_game)
    for a in alerts:
        log(f"  !! STRUCTURAL: {a}")

    # ⚠ THE EXIT ARMS ARE BLIND AFTER FIRST PITCH, AND THIS LINE IS WHY.
    #
    # `by_ticker` comes from `read_market()`, which drops every market whose
    # game has already started (GUARD #2). That is correct and must stay -- it
    # is what stops a bot betting on a game in progress or seeing a settled
    # result. But handing the SAME filtered book to the exit path means the
    # instant a game starts its ticker vanishes, `manage_exits` looks it up,
    # gets None, and skips.
    #
    # So the exit rule can only ever fire in the pre-match window, where the
    # price barely moves -- measured at a median of 1 cent over waits of 1 to
    # 11 hours (the sell-out study, mailbox 017).
    #
    # Measured 2026-09-02:
    #   the live +/-12c rule over the minute tape INCLUDING in-game: 72 of 156
    #   what actually happened:                                       3 of 1,516
    # A 230x gap. Ten of the fifteen bots are consequently bit-identical
    # duplicates and the fleet is 5 strategies wearing 15 names.
    #
    # NOT FIXED ON PURPOSE. Fixing it means the bots start selling DURING
    # games, and the offline 81-cell sweep (PREREGISTRATION_EXITGRID.md) has
    # already answered that question against selling: every one of the 72
    # cells containing a stop-loss was worse than holding. Turning on in-play
    # selling to run an experiment whose answer we already have is the wrong
    # trade. See DECISIONS.md 2026-09-02.
    closes = 0 if dry_run else E.manage_exits(con, by_ticker)

    needed = {}
    for gk, blocks in by_game.items():
        for rows in blocks.values():
            for r in rows:
                w = MEN.window_for(r["hours_to_start"])
                if w:
                    needed[gk] = w
                    break
            if gk in needed:
                break
    briefs = briefs_for(needed, as_of) if needed else {}
    entries, shadows = decide(con, briefs, by_game, dry_run=dry_run)
    settled, finals = settle(con)

    con.execute(
        "INSERT OR REPLACE INTO ticks (ts_utc, games_in_pool, markets_seen, "
        "markets_with_ask, zero_ask, leaked_filtered, entries, shadows, "
        "closes, errors, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (as_of.isoformat(timespec="seconds"), len(by_game),
         health["markets_seen"], health["markets_with_ask"],
         health["zero_ask"], health["leaked_filtered"], entries, shadows,
         closes, len(alerts),
         json.dumps({"filled": filled, "expired": expired,
                     "settled": settled, "finals": finals,
                     "briefs": len(briefs), "windows": len(needed),
                     "pin_error": pin_err,
                     "elapsed_s": round(time.time() - t0, 1)})))
    for k, v in (("last_tick_utc", as_of.isoformat(timespec="seconds")),
                 ("pid", str(os.getpid())),
                 ("last_tick_elapsed_s", str(round(time.time() - t0, 1)))):
        con.execute("INSERT OR REPLACE INTO heartbeat (k, v) VALUES (?,?)",
                    (k, v))
    con.commit()
    log(f"tick: pool={len(by_game)} mkts={health['markets_seen']} "
        f"ask={health['markets_with_ask']} leak_filtered={health['leaked_filtered']} "
        f"briefs={len(briefs)} entries={entries} shadows={shadows} "
        f"filled={filled} closes={closes} settled={settled} "
        f"alerts={len(alerts)} {round(time.time() - t0, 1)}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--interval", type=int, default=TICK_S)
    a = ap.parse_args()

    ROBOTS.load_policy()          # refuses to start if the gate has not been run
    acquire_lock()
    con = E.connect()
    log(f"runner up: pid={os.getpid()} interval={a.interval}s "
        f"dry_run={a.dry_run} db={E.DB}")
    try:
        while True:
            try:
                tick(con, dry_run=a.dry_run)
            except Exception:                          # noqa: BLE001
                log("TICK FAILED:\n" + traceback.format_exc())
                con.execute(
                    "INSERT OR REPLACE INTO heartbeat (k, v) VALUES "
                    "('last_error_utc', ?)", (E.now(),))
                con.commit()
            if a.once:
                break
            time.sleep(a.interval)
    finally:
        release_lock()
        con.close()


if __name__ == "__main__":
    main()
