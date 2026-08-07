"""The pre-match brief: one dict per game, built only from free permitted data.

Everything a mentality is allowed to see about a game lives here. The brief is
built at a stated instant, carries that instant, and every field is derived
strictly from information available AT that instant. A bot never sees the
brief for a game that has started.

    starting pitchers ... season line, last 3 STARTS, rest days, pitch count,
                          debut flag, and the recent-vs-season divergence
    bullpen ............. days of rest per reliever, 3-day pitch load, extra
                          innings in the last 4 games -- computed from prior
                          boxscores, never estimated
    lineup .............. battingOrder when posted (live-only, 2-4 h out) and
                          which of the club's top-5 OPS regulars are absent
    team form ........... W/L, run differential, last ten, home and road splits
    ballpark ............ run index and home/road ratio computed from this
                          season, plus elevation and the park's azimuth
    weather ............. NOAA TAF forecast wind/temp, resolved into a
                          blowing-out component using the park's azimuth
    market .............. Kalshi touch and the de-vigged Pinnacle reference

### The missing-data rule, borrowed and cited

`phatcobra/nrfi-predictor`'s feature builder states it best and this project
adopts it verbatim: *"Missing observations remain missing; they are never
converted into zero-valued outcomes or included in rate denominators."*

Every field below is `None` when unknown. A bot that cannot compute its rule
because an input is `None` must DECLINE the game -- it may not substitute a
default. `soccer/`'s feature builder defaulted missing features to 0.0 and that
is recorded in this repo as a defect.

### Fields deliberately NOT in the brief

The price pattern. No price bands, no drift, no staleness, no volume shape.
148 price-pattern strategies on 909 MLB games returned 0 positive
(`SCOREBOARD.md` p5), and rebuilding one is the most predictable waste
available. The Kalshi price appears once, at the end, as the thing a
conclusion is compared against.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(r"C:\Users\vinig\trading")))

import kalshi as K          # noqa: E402
import parkfactor as PF     # noqa: E402
import pinnacle as PIN      # noqa: E402
import statsapi as S        # noqa: E402
import wx as WX             # noqa: E402
from common.kalshi_fees import fee_order_cents   # noqa: E402

SEASON = None               # None -> the year of the game being briefed


def _season(dt):
    return SEASON or dt.year


def _iso(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00"))


# ------------------------------------------------------------------ pitching

def _starter_block(team_side, game, as_of):
    pp = (game["teams"][team_side].get("probablePitcher") or {})
    pid = pp.get("id")
    prof = None
    if pid:
        try:
            prof = S.starter_profile(pid, _season(as_of), as_of)
        except RuntimeError:
            prof = None
    if prof is None:
        return {"name": pp.get("fullName"), "person_id": pid,
                "announced": bool(pid), "profile": None}
    # the divergence M1 is about: last three starts against the season line
    div = None
    if prof["recent_era"] is not None and prof["season_era"] is not None:
        div = round(prof["recent_era"] - prof["season_era"], 2)
    return {
        "name": pp.get("fullName"), "person_id": pid, "announced": True,
        "profile": prof,
        "recent_minus_season_era": div,
        "short_rest": (prof["rest_days"] is not None and prof["rest_days"] < 4),
        "heavy_last_start": (prof["last_start_pitches"] is not None
                             and prof["last_start_pitches"] >= 105),
        "debut_or_near": prof["is_debut_or_near"],
    }


# -------------------------------------------------------------------- lineup

def _lineup_block(game, as_of):
    pk = game["gamePk"]
    try:
        lu = S.lineup(pk)
    except RuntimeError:
        return {"available": False, "reason": "boxscore unreachable"}
    out = {"available": True}
    for side in ("home", "away"):
        blk = lu[side]
        tid = blk["team_id"]
        posted = blk["posted"]
        missing = None
        if posted:
            try:
                top = S.team_roster_ops(tid, _season(as_of))
                in_order = {pid for pid, _ in blk["order"]}
                missing = [t for t in top if t["id"] not in in_order]
            except RuntimeError:
                missing = None
        out[side] = {
            "posted": posted,
            "order": blk["order"] if posted else None,
            "top5_missing": ([m["name"] for m in missing] if missing is not None
                             else None),
            "top5_missing_count": (len(missing) if missing is not None
                                   else None),
            "top5_missing_ops_sum": (round(sum(m["ops"] for m in missing), 3)
                                     if missing else (0.0 if missing == []
                                                      else None)),
        }
    return out


# ---------------------------------------------------------------- the market

def _market_block(game_key, kalshi_by_game, pin_games, pin_mkts, k_parts):
    """Kalshi's touch and the de-vigged Pinnacle reference, or None for each.

    The Pinnacle join requires club pair AND start time within 20 minutes. A
    club-pair-only join matches the wrong day of a three-game series and
    manufactures a 20-cent fake edge -- measured, see TARGET_CHOICE.md.
    """
    out = {"kalshi": {}, "pinnacle": None, "reference_available": False}
    for series, mkts in kalshi_by_game.items():
        rows = []
        for m in mkts:
            t = K.touch(m)
            if not t:
                continue
            bid, ask, bsz, asz = t
            rows.append({
                "ticker": m["ticker"], "suffix": m["ticker"].rsplit("-", 1)[-1],
                "yes_sub_title": m.get("yes_sub_title"),
                "floor_strike": m.get("floor_strike"),
                "bid": bid, "ask": ask, "mid": (bid + ask) / 2,
                "spread": ask - bid, "bid_size": bsz, "ask_size": asz,
                "entry_fee_c": round(float(fee_order_cents(ask, 1)), 3),
                "volume": float(m.get("volume_fp") or 0),
            })
        if rows:
            out["kalshi"][series] = rows

    g = None
    for pg in pin_games.values():
        if not pg["starts"]:
            continue
        a, h = K.CODE.get(k_parts["away"]), K.CODE.get(k_parts["home"])
        if not a or not h:
            break
        if a in (pg["away"] or "") and h in (pg["home"] or ""):
            dt = abs((pg["starts"] - k_parts["starts"]).total_seconds()) / 60
            if dt <= 20:
                g = pg
                break
    if g is None:
        return out

    mk = PIN.markets_for(g, pin_mkts)
    ref = {"start_utc": g["starts_raw"], "moneyline": None, "totals": []}
    ml = mk.get("moneyline")
    if ml:
        away = next((p for p in ml["prices"]
                     if str(p.get("designation", "")).lower() == "away"), None)
        home = next((p for p in ml["prices"]
                     if str(p.get("designation", "")).lower() == "home"), None)
        if away and home:
            pa = PIN.american_to_prob(away["price"])
            ph = PIN.american_to_prob(home["price"])
            fa, fh, vig = PIN.devig(pa, ph)
            ref["moneyline"] = {
                "away_fair_c": round(fa * 100, 2),
                "home_fair_c": round(fh * 100, 2),
                "overround_pp": round(vig * 100, 3),
                "limit_usd": ml["limit"],
            }
    for t in mk.get("totals", []):
        ou = PIN.over_under(t)
        if not ou:
            continue
        o, u, pts = ou
        po, pu = PIN.american_to_prob(o), PIN.american_to_prob(u)
        fo, fu, vig = PIN.devig(po, pu)
        ref["totals"].append({
            "points": pts, "over_fair_c": round(fo * 100, 2),
            "overround_pp": round(vig * 100, 3),
            "is_alternate": t["is_alternate"], "limit_usd": t["limit"],
        })
    ref["totals"].sort(key=lambda x: (x["is_alternate"], x["points"]))
    out["pinnacle"] = ref
    out["reference_available"] = bool(ref["moneyline"] or ref["totals"])
    return out


# ------------------------------------------------------------------- the API

def build_for_day(day=None, as_of=None, series=("KXMLBGAME", "KXMLBTOTAL"),
                  want_lineups=True, want_weather=True, want_bullpen=True):
    """One brief per scheduled game. `as_of` is the decision instant."""
    as_of = as_of or datetime.now(timezone.utc)
    day = day or as_of.date()
    games = S.schedule(day)
    pf = PF.load()
    stand = S.standings(_season(as_of))
    # The sharp reference is OPTIONAL. Pinnacle's guest API 401s under load
    # and its listing horizon is about one day, so a brief built at T-48 h
    # legitimately has no reference at all. Neither is an error; both are
    # recorded on the brief so a decision rule can decline for the right
    # reason instead of silently seeing None.
    try:
        pin_games = PIN.games()
        pin_mkts = PIN.straight_markets()
        pin_error = None
    except RuntimeError as e:
        pin_games, pin_mkts, pin_error = {}, {}, str(e)

    kalshi = {}
    for s in series:
        try:
            for m in K.markets(s):
                p = K.ticker_parts(m["ticker"])
                if not p:
                    continue
                kalshi.setdefault(p["game_key"], {}).setdefault(s, []).append(m)
        except RuntimeError:
            continue

    out = []
    for g in games:
        if (g.get("status") or {}).get("abstractGameState") == "Final":
            continue
        starts = _iso(g["gameDate"])
        home_id = g["teams"]["home"]["team"]["id"]
        away_id = g["teams"]["away"]["team"]["id"]
        v = S.venue(g["venue"]["id"])

        gk = None
        kp = None
        for cand, blocks in kalshi.items():
            for s, mkts in blocks.items():
                p = K.ticker_parts(mkts[0]["ticker"])
                if not p:
                    continue
                if abs((p["starts"] - starts).total_seconds()) <= 20 * 60 and \
                        K.CODE.get(p["home"]) == g["teams"]["home"]["team"]["name"] \
                        and K.CODE.get(p["away"]) == g["teams"]["away"]["team"]["name"]:
                    gk, kp = cand, p
                    break
            if gk:
                break

        b = {
            "built_at_utc": as_of.isoformat(timespec="seconds"),
            "game_pk": g["gamePk"],
            "game_date_utc": g["gameDate"],
            "starts_utc": starts.isoformat(),
            "hours_to_first_pitch": round(
                (starts - as_of).total_seconds() / 3600, 2),
            "away_team": g["teams"]["away"]["team"]["name"],
            "home_team": g["teams"]["home"]["team"]["name"],
            "away_team_id": away_id, "home_team_id": home_id,
            "game_type": g.get("gameType"),
            "double_header": g.get("doubleHeader"),
            "kalshi_game_key": gk,
            "pinnacle_error": pin_error,
            "venue": v,
            "park": {
                "index": (pf["venues"].get(str(v["id"])) or {}).get("park_index"),
                "index_n": (pf["venues"].get(str(v["id"])) or {}).get("n"),
                "index_usable": (pf["venues"].get(str(v["id"])) or {}).get("usable"),
                "home_road_ratio": (pf["clubs"].get(str(home_id)) or {}).get("home_road_ratio"),
                "home_road_usable": (pf["clubs"].get(str(home_id)) or {}).get("usable"),
                "league_runs_per_game": pf.get("league_runs_per_game"),
            },
            "form": {
                "away": stand.get(away_id), "home": stand.get(home_id),
            },
            "starters": {
                "away": _starter_block("away", g, as_of),
                "home": _starter_block("home", g, as_of),
            },
        }
        if want_bullpen:
            b["bullpen"] = {
                "away": S.bullpen_load(away_id, _season(as_of), as_of),
                "home": S.bullpen_load(home_id, _season(as_of), as_of),
            }
        if want_lineups:
            b["lineup"] = _lineup_block(g, as_of)
        if want_weather:
            try:
                b["weather"] = WX.forecast(v, starts)
            except RuntimeError as e:
                b["weather"] = {"available": False, "reason": str(e)}
        if gk and kp:
            b["market"] = _market_block(gk, kalshi.get(gk, {}), pin_games,
                                        pin_mkts, kp)
        else:
            b["market"] = {"kalshi": {}, "pinnacle": None,
                           "reference_available": False,
                           "note": "no Kalshi market matched this game"}
        out.append(b)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--out")
    ap.add_argument("--no-lineups", action="store_true")
    a = ap.parse_args()
    day = (datetime.fromisoformat(a.date).date() if a.date
           else datetime.now(timezone.utc).date())
    bs = build_for_day(day, want_lineups=not a.no_lineups)
    print(f"{len(bs)} briefs for {day}")
    for b in bs:
        w = b.get("weather") or {}
        st = b["starters"]
        print(f"\n{b['away_team']} @ {b['home_team']}  "
              f"T-{b['hours_to_first_pitch']}h  kalshi={bool(b['kalshi_game_key'])} "
              f"pin_ref={b['market']['reference_available']}")
        print(f"   park idx={b['park']['index']} (n={b['park']['index_n']}) "
              f"elev={b['venue']['elevation_ft']}ft roof={b['venue']['roof']}")
        print(f"   wx: {w.get('wind_used')} out={w.get('wind_out_kt')}kt "
              f"T={w.get('fcst_temp_c') or w.get('obs_temp_c')}C "
              f"taf_ok={w.get('taf_covers_game_time')}")
        for side in ("away", "home"):
            s = st[side]
            p = s.get("profile") or {}
            print(f"   SP {side}: {s['name']} era={p.get('season_era')} "
                  f"last3={p.get('recent_era')} rest={p.get('rest_days')} "
                  f"pitches={p.get('last_start_pitches')} "
                  f"debut={s.get('debut_or_near')}")
        if "bullpen" in b:
            for side in ("away", "home"):
                bp = b["bullpen"][side]
                print(f"   BP {side}: seen={bp.get('games_seen')} "
                      f"used_yday={bp.get('relievers_used_yesterday')} "
                      f"heavy3={bp.get('relievers_heavy_last3')} "
                      f"pitches3={bp.get('bullpen_pitches_last3')} "
                      f"xtra={bp.get('extra_inning_games_last4')}")
        if "lineup" in b and b["lineup"].get("available"):
            for side in ("away", "home"):
                lu = b["lineup"][side]
                print(f"   LU {side}: posted={lu['posted']} "
                      f"top5_missing={lu['top5_missing_count']}")
    if a.out:
        Path(a.out).write_text(json.dumps(bs, indent=2, default=str))
        print(f"\nwrote {a.out}")
