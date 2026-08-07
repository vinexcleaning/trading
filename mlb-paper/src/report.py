"""The pre-registered endpoint tables, produced by one command.

    python src/report.py                 # everything
    python src/report.py --endpoint P1   # just closing-line value
    python src/report.py --json out.json

Every table here corresponds to a numbered endpoint in PREREGISTRATION.md, and
the pre-registered PREDICTION is printed next to the measurement so that a
failed prediction is visible rather than quietly forgotten.

### Three things this file will not do

1. **It will not call a P&L result significant.** The P&L endpoint is
   pre-registered UNTESTABLE (~4,004 settled games per bot to resolve the 3.0c
   cost bar under the joint correction). Its MDE is printed beside every row.
2. **It corrects across 32, not 16.** One Benjamini-Hochberg family spanning
   this test and the tennis one -- see ../JOINT_MULTIPLICITY.md. Bots that never
   fired stay in the denominator as NO-ENTRY rows so it cannot quietly shrink.
3. **It clusters on the GAME.** Never on a fill, a tick or a ladder rung.
   KXMLBTOTAL lists a median of 11 strikes per game and eleven rungs are eleven
   views of one run total.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import engine as E                 # noqa: E402
import mentalities as MEN          # noqa: E402

JOINT_DENOMINATOR = 32             # ../JOINT_MULTIPLICITY.md
Q = 0.10
Z_BETA = 0.8416                    # 80% power
COST_BAR_C = 3.0                   # measured: spread/2 + taker fee at ~50c
BOOTS = 4000


def _z(p):
    """Inverse normal CDF (Acklam). No scipy in this package."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]
    pl = 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q
                + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > 1 - pl:
        q = math.sqrt(-2 * math.log(1 - p))
        return -((((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q
                  + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1))
    q = p - 0.5
    r = q * q
    return ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r
             + a[5]) * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1))


K_JOINT = _z(1 - (Q / JOINT_DENOMINATOR) / 2) + Z_BETA


def mde(sd, n):
    return None if not n else round(K_JOINT * sd / math.sqrt(n), 2)


def cluster_boot(by_game, seed=11):
    """Mean and a 95% interval, resampling GAMES not observations."""
    keys = list(by_game)
    if not keys:
        return None
    vals = [statistics.mean(by_game[k]) for k in keys]
    m = statistics.mean(vals)
    rnd = random.Random(seed)
    boots = sorted(statistics.mean(
        [vals[rnd.randrange(len(vals))] for _ in vals]) for _ in range(BOOTS))
    return {"n_games": len(keys), "mean": round(m, 3),
            "lo": round(boots[int(0.025 * BOOTS)], 3),
            "hi": round(boots[int(0.975 * BOOTS)], 3),
            "sd_between_games": round(statistics.pstdev(vals), 3)
            if len(vals) > 1 else None}


def _hdr(t, pred=None):
    print()
    print("=" * 92)
    print(t)
    if pred:
        print(f"PRE-REGISTERED PREDICTION: {pred}")
    print("=" * 92)


# ------------------------------------------------------------------- P1 CLV

def p1_clv(con):
    _hdr("P1 -- CLOSING-LINE VALUE vs the de-vigged sharp line  [PRIMARY]",
         "every bot between -3.0c and +0.5c; only 'early' has a mechanism for "
         "a positive number")
    rows = con.execute(
        "SELECT bot, game_key, ticker, price_c, side FROM fills "
        "WHERE action='open'").fetchall()
    by_bot = {}
    missing_ref = 0
    for r in rows:
        close = con.execute(
            "SELECT sharp_fair_yes_c FROM marks WHERE ticker=? AND "
            "sharp_fair_yes_c IS NOT NULL ORDER BY ts_utc DESC LIMIT 1",
            (r["ticker"],)).fetchone()
        if not close:
            missing_ref += 1
            continue
        fair = close["sharp_fair_yes_c"]
        if r["side"] == "NO":
            fair = 100 - fair
        by_bot.setdefault(r["bot"], {}).setdefault(
            r["game_key"], []).append(fair - r["price_c"])
    out = []
    print(f"{'bot':<22} {'games':>6} {'mean CLV':>9} {'[95% CI]':>20} "
          f"{'MDE@n':>8}  verdict")
    for bot in MEN.BOT_IDS:
        g = by_bot.get(bot)
        if not g:
            print(f"{bot:<22} {'0':>6} {'-':>9} {'NO-ENTRY':>20} {'-':>8}  "
                  f"NO-ENTRY (stays in the denominator of 32)")
            out.append({"bot": bot, "n_games": 0, "verdict": "NO-ENTRY"})
            continue
        s = cluster_boot(g)
        m = mde(s["sd_between_games"] or 3.0, s["n_games"])
        v = ("SURVIVES" if s["lo"] > 0 else
             "COLLAPSES" if s["hi"] < 0 else "UNDERPOWERED")
        print(f"{bot:<22} {s['n_games']:>6} {s['mean']:>9.2f} "
              f"[{s['lo']:>8.2f},{s['hi']:>8.2f}] {str(m):>8}  {v}")
        out.append(dict(s, bot=bot, mde_c=m, verdict=v))
    if missing_ref:
        print(f"\n  {missing_ref} fills have no sharp reference on any mark -- "
              f"Pinnacle's listing horizon is about one day, so an entry at "
              f"T-48h legitimately has none. Reported, not dropped silently.")
    print("\n  CLV is the primary endpoint because its variance is roughly an "
          "order of magnitude\n  smaller than settlement P&L. A bot with no "
          "fills is NOT excluded -- it is a NO-ENTRY row.")
    return out


# ---------------------------------------------------------------- P2 early

def p2_early_window(con):
    _hdr("P2 -- is the early window real? Kalshi mid vs the sharp line by lead",
         "mean indistinguishable from zero at every lead; DISPERSION falls "
         "monotonically toward first pitch")
    buckets = [(36, 60, "T-48h"), (18, 30, "T-24h"), (4.5, 7.5, "T-6h"),
               (2, 4, "T-3h"), (1, 2, "T-90m"), (0.25, 0.75, "T-30m")]
    print(f"{'lead':<8} {'marks':>7} {'games':>6} {'mean gap':>9} "
          f"{'[95% CI]':>20} {'sd':>7}")
    out = []
    for lo, hi, name in buckets:
        rows = con.execute(
            "SELECT game_key, ticker, bid, ask, sharp_fair_yes_c "
            "FROM marks WHERE sharp_fair_yes_c IS NOT NULL "
            "AND hours_to_start >= ? AND hours_to_start < ?", (lo, hi)
        ).fetchall()
        by_game = {}
        for r in rows:
            mid = (r["bid"] + r["ask"]) / 2.0
            by_game.setdefault(r["game_key"], []).append(
                r["sharp_fair_yes_c"] - mid)
        s = cluster_boot(by_game)
        if not s:
            print(f"{name:<8} {'0':>7} {'0':>6} {'-':>9} {'no data':>20}")
            continue
        print(f"{name:<8} {len(rows):>7} {s['n_games']:>6} {s['mean']:>9.2f} "
              f"[{s['lo']:>8.2f},{s['hi']:>8.2f}] "
              f"{str(s['sd_between_games']):>7}")
        out.append(dict(s, lead=name, marks=len(rows)))
    print("\n  A non-zero mean at T-48h that vanishes by T-6h is the ONLY shape "
          "that supports M4.\n  A flat mean with falling dispersion is the "
          "market simply getting more certain.")
    return out


# --------------------------------------------------------------- P3 lineup

def p3_lineup_lag(con):
    _hdr("P3 -- does Kalshi lag the lineup drop?",
         "no detectable move at +1 or +5 min; less than the 2.0c spread by +60")
    print("  Needs the lineup-posting instant, which the runner records as the "
          "first brief\n  where lineup.posted flips true. Reported once at "
          "least one card has been seen live.")
    rows = con.execute(
        "SELECT COUNT(*) c FROM decisions WHERE mentality='lineup' "
        "AND kind IN ('entry','shadow')").fetchone()["c"]
    print(f"  lineup decisions so far: {rows}")
    return {"lineup_decisions": rows}


# ----------------------------------------------------------------- P4 cost

def p4_cost(con):
    _hdr("P4 -- what does it actually cost to trade this market?",
         "2.5-3.5c hold-to-settle, 5.5-7.0c round trip. BELOW 2.0c IS A BUG.")
    opens = con.execute(
        "SELECT f.bot, f.game_key, f.ticker, f.ts_utc, f.price_c, "
        "       f.contracts, f.fee_c, d.quoted_price_c "
        "FROM fills f JOIN decisions d ON d.id = f.decision_id "
        "WHERE f.action='open'").fetchall()
    if not opens:
        print("  no fills yet")
        return {}
    slip, feec, spread_paid, no_mark = {}, {}, {}, 0
    for r in opens:
        g = r["game_key"]
        if r["quoted_price_c"] is not None:
            slip.setdefault(g, []).append(r["price_c"] - r["quoted_price_c"])
        feec.setdefault(g, []).append(r["fee_c"] / max(1, r["contracts"]))
        # THE SPREAD PAID. The first version of this function omitted it and
        # reported 1.68c against a pre-registered 2.5-3.5c, tripping its own
        # "below 2.0c is a bug" alarm. The alarm was right and the bug was
        # here, not in the fill model: `_exec_price` pays the ask, which is
        # correct, but half the spread is a real cost and was simply not being
        # counted. PREREGISTRATION section 5/P4 defines the cost as
        # "entry fee + exit fee + spread paid + measured slippage".
        mk = con.execute(
            "SELECT bid, ask FROM marks WHERE ticker=? AND ts_utc <= ? "
            "ORDER BY ts_utc DESC LIMIT 1", (r["ticker"], r["ts_utc"])
        ).fetchone()
        if not mk:
            no_mark += 1
            continue
        spread_paid.setdefault(g, []).append(abs(r["price_c"]
                                                 - (mk["bid"] + mk["ask"]) / 2.0))
    s_slip = cluster_boot(slip)
    s_fee = cluster_boot(feec)
    s_spr = cluster_boot(spread_paid)
    print(f"  spread paid (fill price vs the mid at fill)      : "
          f"{s_spr['mean']:>6.2f}c  [{s_spr['lo']:.2f},{s_spr['hi']:.2f}]  "
          f"n={s_spr['n_games']} games")
    print(f"  realised slippage, decision price -> fill price  : "
          f"{s_slip['mean']:>6.2f}c  [{s_slip['lo']:.2f},{s_slip['hi']:.2f}]  "
          f"n={s_slip['n_games']} games")
    print(f"  realised entry fee per contract                  : "
          f"{s_fee['mean']:>6.2f}c  [{s_fee['lo']:.2f},{s_fee['hi']:.2f}]")
    if no_mark:
        print(f"  ({no_mark} fills had no earlier mark for their ticker and "
              f"are excluded from the spread figure)")
    closes = con.execute(
        "SELECT game_key, fee_c, contracts FROM fills "
        "WHERE action='close'").fetchall()
    if closes:
        c = {}
        for r in closes:
            c.setdefault(r["game_key"], []).append(
                r["fee_c"] / max(1, r["contracts"]))
        s_c = cluster_boot(c)
        print(f"  realised exit fee per contract (traded exits)   : "
              f"{s_c['mean']:>6.2f}c")
    tot = s_spr["mean"] + s_slip["mean"] + s_fee["mean"]
    print(f"\n  HOLD-TO-SETTLE cost so far ~ {tot:.2f}c per contract "
          f"(spread paid + slippage + ONE fee)")
    print(f"  A position held to settlement pays ONE fee, because Kalshi "
          f"charges on the trade.\n  That is why the 'hold' arm has a lower "
          f"cost bar than the other two, and it must\n  not be quietly "
          f"reversed by counting a second fee here.")
    if tot < 2.0:
        print("\n  *** BELOW 2.0c. Per PREREGISTRATION section 5/P4 this is a "
              "BUG until proven\n  *** otherwise -- it is how a +14.4% tennis "
              "result became -24.3%. Do not report\n  *** any P&L number until "
              "this is explained.")
    # The population median spread on KXMLBGAME/KXMLBTOTAL is 2.0c (measured,
    # reports/market_census.json), which is where the 2.5-3.5c prediction came
    # from. If the realised spread paid is materially tighter, the bots are
    # SELECTING into the tightest markets -- a wider quote makes the net edge
    # fail their own cost bar, so they decline it. That is a real selection
    # effect and it runs OPPOSITE to the esports finding, where a strategy that
    # had to trade every qualifying event paid the mean rather than the median.
    if s_spr["mean"] * 2 < 1.5:
        print(f"\n  NOTE: realised spread {s_spr['mean']*2:.1f}c against a "
              f"population median of 2.0c.\n  The bots are declining the wider "
              f"quotes, because a wider quote fails their own\n  cost bar. "
              f"Report the realised number AND the population number; the "
              f"realised one\n  is only available to a strategy allowed to "
              f"decline, which these are.")
    return {"spread_paid": s_spr, "slippage": s_slip, "entry_fee": s_fee,
            "hold_to_settle_c": round(tot, 3)}


# ------------------------------------------------------------- P5 coverage

def p5_coverage(con):
    _hdr("P5 -- does the brief exist for the games Kalshi lists?",
         "probables >=90% at T-24h and BELOW 60% at T-48h; TAF ~100% inside "
         "T-24h and ~0% beyond T-30h; lineups 0% at T-12h")
    briefs = sorted((HERE.parent / "data" / "briefs").glob("*.json"))
    if not briefs:
        print("  no briefs on disk yet")
        return {}
    buckets = {}
    for f in briefs:
        try:
            b = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        h = b.get("hours_to_first_pitch")
        if h is None:
            continue
        lead = ("T-48h" if h >= 30 else "T-24h" if h >= 12 else
                "T-6h" if h >= 4 else "T-3h" if h >= 2 else "T-90m")
        d = buckets.setdefault(lead, {"n": 0, "probables": 0, "taf": 0,
                                      "lineup": 0, "park": 0, "pin": 0})
        d["n"] += 1
        st = b.get("starters") or {}
        if all((st.get(s) or {}).get("announced") for s in ("away", "home")):
            d["probables"] += 1
        w = b.get("weather") or {}
        if w.get("taf_covers_game_time"):
            d["taf"] += 1
        lu = b.get("lineup") or {}
        if lu.get("available") and all(
                (lu.get(s) or {}).get("posted") for s in ("away", "home")):
            d["lineup"] += 1
        if (b.get("park") or {}).get("index_usable"):
            d["park"] += 1
        if (b.get("market") or {}).get("reference_available"):
            d["pin"] += 1
    print(f"{'lead':<8} {'briefs':>7} {'probables':>10} {'TAF':>7} "
          f"{'lineup':>8} {'park idx':>9} {'sharp ref':>10}")
    for lead in ("T-48h", "T-24h", "T-6h", "T-3h", "T-90m"):
        d = buckets.get(lead)
        if not d:
            continue
        n = d["n"]
        print(f"{lead:<8} {n:>7} {100*d['probables']/n:>9.0f}% "
              f"{100*d['taf']/n:>6.0f}% {100*d['lineup']/n:>7.0f}% "
              f"{100*d['park']/n:>8.0f}% {100*d['pin']/n:>9.0f}%")
    print("\n  If probables come back ABOVE 90% at T-48h, suspect the schedule "
          "hydrate of\n  back-filling rather than celebrate.")
    return buckets


# ------------------------------------------------------------ P6 overlap

def p6_overlap(con):
    _hdr("P6 -- five instruments, or one bot in five hats?",
         "park-air and bullpen overlap most; early and lineup near-disjoint "
         "BY CONSTRUCTION")
    ent = {}
    for r in con.execute(
            "SELECT mentality, game_key FROM decisions WHERE kind='entry'"
    ).fetchall():
        ent.setdefault(r["mentality"], set()).add(r["game_key"])
    names = [m for m in MEN.MENTALITIES if m in ent]
    if len(names) < 2:
        print(f"  only {len(names)} mentality has entered a game so far")
        return {}
    print("        " + "".join(f"{n[:9]:>10}" for n in names))
    js = []
    for a in names:
        line = f"{a[:7]:<8}"
        for b in names:
            u = len(ent[a] | ent[b])
            j = len(ent[a] & ent[b]) / u if u else 0.0
            line += f"{j:>10.2f}"
            if a < b:
                js.append(j)
        print(line)
    if js:
        med = statistics.median(js)
        print(f"\n  median pairwise Jaccard = {med:.2f}  "
              + ("-> five genuinely different instruments"
                 if med < 0.5 else
                 "-> WARNING: the labels may be decoration and the 32-way "
                 "correction is measuring one thing many times"
                 if med > 0.8 else "-> partially overlapping"))
    return {"jaccard_median": statistics.median(js) if js else None}


# --------------------------------------------------------------- P7 health

def p7_health(con):
    _hdr("P7 -- did the machinery survive?",
         ">=95% of expected ticks, zero double-runner incidents, clean resume")
    t = con.execute(
        "SELECT COUNT(*) n, MIN(ts_utc) a, MAX(ts_utc) b FROM ticks"
    ).fetchone()
    if not t["n"]:
        print("  no ticks")
        return {}
    span = (datetime.fromisoformat(t["b"])
            - datetime.fromisoformat(t["a"])).total_seconds()
    expected = max(1, int(span / 300) + 1)
    pct = 100.0 * t["n"] / expected
    print(f"  ticks {t['n']} over {span/3600:.1f} h; expected ~{expected} "
          f"at 300 s  ->  {pct:.1f}%   "
          + ("PASS" if pct >= 95 else "*** BELOW THE 95% GATE ***"))
    leaked = con.execute(
        "SELECT SUM(leaked_filtered) s FROM ticks").fetchone()["s"] or 0
    alerts = con.execute("SELECT SUM(errors) s FROM ticks").fetchone()["s"] or 0
    print(f"  markets filtered as started-or-settled BEFORE any bot saw them: "
          f"{leaked}")
    print(f"  structural alerts (impossible quotes): {alerts}")
    traded = con.execute(
        "SELECT COUNT(*) c FROM positions p JOIN decisions d "
        "ON d.id = p.decision_id WHERE d.outcome_known = 1 "
        "AND p.opened_utc > d.ts_utc AND d.kind='entry' "
        "AND d.outcome_known = 1 AND p.status='open'").fetchone()["c"]
    print(f"  VOID CHECK -- positions opened on a game whose outcome was "
          f"already known: {traded}"
          + ("  (run is void if non-zero)" if traded else "  OK"))
    return {"ticks": t["n"], "expected": expected, "pct": round(pct, 1),
            "leaked_filtered": leaked, "structural_alerts": alerts,
            "void_check": traded}


# ------------------------------------------------------------- P&L, unbelieved

def pnl(con):
    _hdr("SECONDARY -- P&L, reported and NOT believed",
         "every bot between -10c and +2c; NO bot survives the joint BH; "
         "modal verdict UNDERPOWERED. hold > exit-once > free.")
    print(f"  Joint BH denominator {JOINT_DENOMINATOR} at q={Q}; "
          f"power constant k={K_JOINT:.3f}; cost bar {COST_BAR_C}c")
    print(f"  To resolve the cost bar needs ~"
          f"{int((K_JOINT * 50.0 / COST_BAR_C) ** 2):,} settled games PER BOT.")
    print()
    print(f"{'bot':<22} {'games':>6} {'c/contract':>11} {'[95% CI]':>22} "
          f"{'MDE@n':>8}  verdict")
    out = []
    for bot in MEN.BOT_IDS:
        rows = con.execute(
            "SELECT game_key, pnl_c, contracts FROM positions "
            "WHERE bot=? AND status IN ('settled','closed')", (bot,)).fetchall()
        by_game = {}
        for r in rows:
            by_game.setdefault(r["game_key"], []).append(
                r["pnl_c"] / max(1, r["contracts"]))
        s = cluster_boot(by_game)
        if not s:
            print(f"{bot:<22} {'0':>6} {'-':>11} {'NO-ENTRY':>22} {'-':>8}  "
                  f"NO-ENTRY (stays in the denominator)")
            out.append({"bot": bot, "n_games": 0, "verdict": "NO-ENTRY"})
            continue
        m = mde(s["sd_between_games"] or 50.0, s["n_games"])
        v = ("SURVIVES" if (s["lo"] > 0 and s["mean"] > COST_BAR_C) else
             "COLLAPSES" if s["hi"] < 0 else "UNDERPOWERED")
        print(f"{bot:<22} {s['n_games']:>6} {s['mean']:>11.2f} "
              f"[{s['lo']:>9.2f},{s['hi']:>9.2f}] {str(m):>8}  {v}")
        out.append(dict(s, bot=bot, mde_c=m, verdict=v))
    print("\n  UNTESTABLE at any n this run will reach. The word 'works' does "
          "not appear here.")
    return out


def shadows(con):
    _hdr("SHADOW decisions -- views that were NOT taken")
    rows = con.execute(
        "SELECT mentality, COUNT(*) n FROM decisions WHERE kind='shadow' "
        "GROUP BY mentality").fetchall()
    if not rows:
        print("  none")
        return []
    for r in rows:
        print(f"  {r['mentality']:<12} {r['n']}")
    print("\n  A shadow is a real view that did not survive the cost bar. It "
          "has NO position,\n  NO stake and NO P&L, and it is never counted as "
          "a trade. It exists so that the\n  CLV endpoint has usable n while "
          "the traded arms stay honest.")
    return [dict(r) for r in rows]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint")
    ap.add_argument("--json")
    a = ap.parse_args()
    con = E.connect()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"mlb-paper report  ·  {stamp}  ·  PAPER ONLY, no money exists here")
    print(f"joint BH denominator {JOINT_DENOMINATOR} across BOTH forward tests "
          f"(../JOINT_MULTIPLICITY.md)")
    fns = {"P1": p1_clv, "P2": p2_early_window, "P3": p3_lineup_lag,
           "P4": p4_cost, "P5": p5_coverage, "P6": p6_overlap,
           "P7": p7_health, "PNL": pnl, "SHADOW": shadows}
    res = {}
    for k, fn in fns.items():
        if a.endpoint and a.endpoint.upper() != k:
            continue
        try:
            res[k] = fn(con)
        except Exception as e:                       # noqa: BLE001
            print(f"\n  !! {k} failed: {e}")
    if a.json:
        Path(a.json).write_text(json.dumps(
            {"generated_utc": stamp, "results": res}, indent=2, default=str))
        print(f"\nwrote {a.json}")
    con.close()
