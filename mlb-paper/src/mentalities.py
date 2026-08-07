"""The five mentalities as decision functions. One file, no price patterns.

Rationale for each is in MENTALITIES.md; the parameters are fixed in
PREREGISTRATION.md section 10 and DECISIONS.md, and are not tuned once an
outcome exists.

## The shape every mentality has, and why it is this shape

Each mentality states a **signed adjustment in cents** to the market's current
price, derived from baseball inputs alone, and enters only when that adjustment
survives the cost of trading:

    fair      = kalshi_mid_for_my_side + my_adjustment_c
    net_edge  = fair - executable_price - kalshi_taker_fee - slippage
    enter     if net_edge >= this mentality's bar

Two design decisions here matter and both were made deliberately.

**First: the anchor is the market price, not an invented probability.** The
production MLB bot in the corpus (`mmoore07129/mlb-kalshi-bot`) reached the same
conclusion and states it in its own README as "Pinnacle-primary,
model-fallback-only". This repo's own far better tennis model lost to the
bookmakers by +0.019 Brier on 2,645 matches. Building a rival win-probability
model is a known-dead path; stating "this specific factor is worth k cents and
the price has not moved for it" is the claim actually being tested.

Using the current price as an anchor is **not** the banned thing. What is banned
is the price *pattern* -- bands, drift, staleness, volume shape -- because 148
price-pattern strategies on 909 MLB games returned 0 positive. No function below
reads price history.

**Second: the sharp line is a YARDSTICK, not a gate.** An earlier version of
this file required the de-vigged Pinnacle price to already agree that Kalshi was
behind. That turns every mentality into a de-vig arbitrage bot -- a strategy
this project measured at **0 of 58 markets qualifying** (TARGET_CHOICE.md) -- and
in a dry run it silenced three of the five permanently. Pinnacle's proper role
is the closing-line-value reference in PREREGISTRATION.md section 5/P1, which is
the primary endpoint, and CLV cannot be measured on a trade that never happens.
The de-vigged edge is computed and recorded on every intent; nothing branches
on it.

## Three rules enforced by the shapes below

1. **Free entry, none forced.** Returning a Decline is always legal, and a bot
   that declines every game for a week is a valid reported outcome.
2. **Missing means decline, never default.** No league average, no zero, no
   prior substituted for an absent input. `soccer/` defaulting missing features
   to 0.0 is a recorded defect in this repo.
3. **Every magnitude is stated, with the assumption it rests on**, so that a
   wrong coefficient is visible as a wrong coefficient rather than as a null.

## The run-to-cents conversions, stated once

A full-game total sits near 8.5-9 runs with a standard deviation of about 4.3.
The density at the median is therefore roughly 0.09 per run, so **one run of
expected total is worth about 9 cents on an at-the-money Over**. One run of
expected MARGIN is worth about **11 cents** on an at-the-money moneyline. Both
numbers are approximations used openly as approximations; they are the
sensitivity, not the edge.
"""
from __future__ import annotations

import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# The repo root, derived from this file. NEVER a hardcoded home
# directory: this package is meant to run on the laptop, whose paths
# live under a different user, and a hardcoded desktop path would
# import nothing and fail at the first shared-fee call.
TRADING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRADING_ROOT))
from common.kalshi_fees import fee_order_cents        # noqa: E402

SLIPPAGE_C = 1.0
CENTS_PER_RUN_TOTAL = 9.0      # d(Over price)/d(expected total runs)
CENTS_PER_RUN_MARGIN = 11.0    # d(moneyline price)/d(expected run margin)


@dataclass
class Intent:
    mentality: str
    ticker: str
    side: str                    # "YES" or "NO"
    entry_price_c: int           # executable: the ask for YES, 100-bid for NO
    conviction: float            # the net edge in cents; comparable across bots
    stated_prob_c: float         # this mentality's own fair value
    edge_c: float
    window: str
    top_of_book_size: float = 0.0
    reasoning: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class Decline:
    mentality: str
    reason: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


# ------------------------------------------------------------------ helpers

def _executable(row, side):
    """The price you actually pay. There is no mid in this path. GUARDS #7."""
    if side == "YES":
        return row["ask"], row["ask_size"]
    return 100 - row["bid"], row["bid_size"]


def _mid_for(row, side):
    """The market's own estimate for a side. Reporting anchor only -- never a
    fill price; `tests/test_no_mid_fill.py` asserts no fill path reads it."""
    return row["mid"] if side == "YES" else 100 - row["mid"]


def _decide(row, side, adjustment_c, bar_c):
    """Turn a stated adjustment into an entry or a reason not to."""
    fair = _mid_for(row, side) + adjustment_c
    fair = max(1.0, min(99.0, fair))
    price, size = _executable(row, side)
    fee = float(fee_order_cents(price, 1))
    edge = round(fair - price - fee - SLIPPAGE_C, 3)
    return {"fair_c": round(fair, 2), "price_c": price, "size": size,
            "fee_c": round(fee, 3), "slippage_c": SLIPPAGE_C,
            "net_edge_c": edge, "bar_c": bar_c, "passes": edge >= bar_c}


def _ml_rows(brief):
    return (brief.get("market", {}).get("kalshi", {}) or {}).get("KXMLBGAME", [])


def _total_rows(brief):
    return (brief.get("market", {}).get("kalshi", {}) or {}).get("KXMLBTOTAL", [])


def _pin(brief):
    return (brief.get("market") or {}).get("pinnacle")


def _sharp_yardstick(brief, kind, side, price_c, points=None):
    """The de-vigged sharp view of this exact bet, RECORDED and never gated on.

    PREREGISTRATION section 5/P1 makes closing-line value the primary endpoint;
    this is the same quantity computed at decision time, so the two are
    directly comparable and any drift between them is visible.
    """
    pin = _pin(brief)
    if not pin:
        return {"available": False}
    if kind == "moneyline":
        ml = pin.get("moneyline")
        if not ml:
            return {"available": False}
        fair = ml[f"{side}_fair_c"]
        return {"available": True, "sharp_fair_c": fair,
                "overround_pp": ml["overround_pp"],
                "sharp_net_edge_c": round(
                    fair - price_c - float(fee_order_cents(price_c, 1))
                    - SLIPPAGE_C, 3)}
    tot = None
    for t in pin.get("totals", []):
        if points is not None and abs(float(t["points"]) - float(points)) < 1e-6:
            tot = t
            break
    if tot is None:
        return {"available": False}
    fair = tot["over_fair_c"] if side == "YES" else 100 - tot["over_fair_c"]
    return {"available": True, "sharp_fair_c": fair,
            "sharp_points": tot["points"], "overround_pp": tot["overround_pp"],
            "sharp_net_edge_c": round(
                fair - price_c - float(fee_order_cents(price_c, 1))
                - SLIPPAGE_C, 3)}


def _club_row(brief, rows, team_side):
    import kalshi as K
    want = next((c for c, n in K.CODE.items()
                 if n == brief[f"{team_side}_team"]), None)
    for r in rows:
        if r["suffix"] == want:
            return r
    for r in rows:                     # the subtitle names the club
        st = (r.get("yes_sub_title") or "").strip()
        if st and st.split()[0] and st.split()[0] in brief[f"{team_side}_team"]:
            return r
    return None


def _rung_nearest(rows, points, tol=0.51):
    best = None
    for r in rows:
        fs = r.get("floor_strike")
        if fs is None:
            continue
        d = abs(float(fs) - float(points))
        if best is None or d < best[0]:
            best = (d, r)
    return best[1] if best and best[0] <= tol else None


def _main_total_points(brief, rows):
    """Which rung to trade. Pinnacle's main line if present, else the rung
    whose Kalshi mid is closest to 50c -- the at-the-money rung, which is what
    'the total' means. This uses the CURRENT price to pick a strike, not to
    form a view, and it is the only place any mentality touches price for
    selection."""
    pin = _pin(brief)
    if pin:
        main = next((t for t in pin.get("totals", [])
                     if not t["is_alternate"]), None)
        if main:
            return float(main["points"]), "pinnacle main line"
    atm = min(rows, key=lambda r: abs(r["mid"] - 50.0), default=None)
    if atm is None or atm.get("floor_strike") is None:
        return None, "no rung"
    return float(atm["floor_strike"]), "at-the-money rung"


# ============================================================= M1  starter
# BAR and coefficients: PREREGISTRATION section 10, DECISIONS.md D2.
M1_WINDOWS = {"T-24h", "T-6h", "T-3h"}
M1_MIN_DIVERGENCE_ER9 = 1.50
M1_BAR_C = 1.0
# Assumption, stated: three starts is ~18 innings, so a divergence of 1.0 ER/9
# over that span is worth roughly 0.25 runs of true expected margin once
# regressed. 0.25 runs x 11c/run = 2.75c per unit of divergence.
M1_C_PER_ER9 = 2.75
M1_DEBUT_RUNS = 0.35       # a first-or-second career start, against his side
M1_SHORT_REST_RUNS = 0.20


def m1_starter(brief, window):
    """Only NEW starting-pitcher information. Never the season ERA alone.

    The season line is the most public number in the sport and is exactly what
    the price is already built on. What is claimed here is narrower: that the
    market anchors on a 25-start average while the last three starts, a debut,
    or short rest are the parts it absorbs slowly.
    """
    if window not in M1_WINDOWS:
        return Decline("starter", "outside this mentality's windows",
                       {"window": window})
    rows = _ml_rows(brief)
    if not rows:
        return Decline("starter", "no KXMLBGAME market for this game")

    runs, flags = 0.0, {}
    for side, sgn in (("home", +1.0), ("away", -1.0)):
        s = brief["starters"][side]
        if not s.get("announced") or not s.get("profile"):
            return Decline("starter", f"{side} starter not announced")
        d = s.get("recent_minus_season_era")
        if d is None:
            return Decline("starter",
                           f"{side} has no recent-vs-season divergence "
                           f"(missing stays missing)")
        f = []
        # d < 0 means pitching BETTER lately, which helps his own side
        if abs(d) >= M1_MIN_DIVERGENCE_ER9:
            f.append("form_divergence")
            runs += sgn * (-d) * (M1_C_PER_ER9 / CENTS_PER_RUN_MARGIN)
        if s.get("debut_or_near"):
            f.append("debut_or_near")
            runs -= sgn * M1_DEBUT_RUNS
        if s.get("short_rest"):
            f.append("short_rest")
            runs -= sgn * M1_SHORT_REST_RUNS
        flags[side] = {"flags": f, "divergence_er9": d,
                       "rest_days": s["profile"].get("rest_days"),
                       "career_starts_prior":
                           s["profile"].get("career_starts_prior"),
                       "season_era": s["profile"].get("season_era"),
                       "recent_era": s["profile"].get("recent_era")}

    if not any(flags[s]["flags"] for s in flags):
        return Decline("starter", "no new pitcher information", flags)
    adj_c = runs * CENTS_PER_RUN_MARGIN
    if abs(adj_c) < 0.5:
        return Decline("starter", "flags fired but the net direction is flat",
                       dict(flags, adjustment_c=round(adj_c, 3)))

    team_side = "home" if adj_c > 0 else "away"
    row = _club_row(brief, rows, team_side)
    if row is None:
        return Decline("starter", "could not locate the club's market row",
                       {"team_side": team_side})
    d = _decide(row, "YES", abs(adj_c), M1_BAR_C)
    yard = _sharp_yardstick(brief, "moneyline", team_side, d["price_c"])
    detail = {"rule": "new starting-pitcher information only",
              "backed": brief[f"{team_side}_team"],
              "expected_margin_runs": round(runs, 4),
              "adjustment_c": round(adj_c, 3),
              "cents_per_run_margin": CENTS_PER_RUN_MARGIN,
              "flags": flags, "market_mid_c": _mid_for(row, "YES"),
              **d, "sharp_yardstick": yard}
    if not d["passes"]:
        return Decline("starter", "adjustment does not survive the cost bar",
                       detail)
    return Intent("starter", row["ticker"], "YES", d["price_c"],
                  d["net_edge_c"], d["fair_c"], d["net_edge_c"], window,
                  d["size"], detail)


# ============================================================ M2  park+air
M2_WINDOWS = {"T-6h", "T-3h", "T-90m"}
M2_MIN_PARK_N = 30
M2_BAR_C = 1.0
# Assumptions, stated. The PARK ITSELF IS NOT AN ADJUSTMENT -- elevation and
# dimensions are the most public facts about a game and are fully in the line.
# What can move is the deviation of tonight's AIR from a normal night there:
M2_RUNS_PER_KT_OUT = 0.030     # 10 kt blowing out ~ +0.30 runs
M2_RUNS_PER_DEG_C = 0.020      # +10 C over a 22 C reference ~ +0.20 runs
M2_REF_TEMP_C = 22.0
M2_PARK_AMPLIFIER = True       # a hitter's park amplifies both terms


def m2_park_air(brief, window):
    """Runs, not winners. Tonight's AIR against a normal night at this park."""
    if window not in M2_WINDOWS:
        return Decline("park-air", "outside this mentality's windows",
                       {"window": window})
    rows = _total_rows(brief)
    if not rows:
        return Decline("park-air", "no KXMLBTOTAL market for this game")
    park = brief.get("park") or {}
    if not park.get("index_usable") or park.get("index") is None:
        return Decline("park-air", "park index below the n>=30 floor",
                       {"n": park.get("index_n"), "floor": M2_MIN_PARK_N})
    w = brief.get("weather") or {}
    if not w.get("available"):
        return Decline("park-air", "no weather", {"reason": w.get("reason")})
    roof = (brief["venue"].get("roof") or "").lower()
    indoors = roof in ("dome", "retractable", "closed", "indoor", "fixed")
    if indoors:
        return Decline("park-air", "roof; there is no air to read",
                       {"roof": brief["venue"].get("roof")})
    if not w.get("taf_covers_game_time"):
        return Decline("park-air",
                       "TAF does not cover first pitch; an observed METAR "
                       "hours early is not a forecast",
                       {"wind_used": w.get("wind_used")})
    wind_out = w.get("wind_out_kt")
    if wind_out is None:
        return Decline("park-air", "wind direction unresolvable (variable)",
                       {"wind_variable": w.get("wind_variable")})
    temp = w.get("fcst_temp_c", None)
    if temp is None:
        temp = w.get("obs_temp_c")
    if temp is None:
        return Decline("park-air", "no temperature")

    runs = (M2_RUNS_PER_KT_OUT * float(wind_out)
            + M2_RUNS_PER_DEG_C * (float(temp) - M2_REF_TEMP_C))
    amp = float(park["index"]) if M2_PARK_AMPLIFIER else 1.0
    runs *= amp
    adj_c = runs * CENTS_PER_RUN_TOTAL

    points, how = _main_total_points(brief, rows)
    if points is None:
        return Decline("park-air", "no tradeable rung", {"how": how})
    row = _rung_nearest(rows, points)
    if row is None:
        return Decline("park-air", "Kalshi lists no rung at that total",
                       {"points": points, "how": how})
    side = "YES" if adj_c > 0 else "NO"      # YES = Over
    d = _decide(row, side, abs(adj_c), M2_BAR_C)
    yard = _sharp_yardstick(brief, "totals", side, d["price_c"], points)
    detail = {"rule": "tonight's air against a normal night at this park",
              "direction": "more runs" if adj_c > 0 else "fewer runs",
              "wind_out_kt": wind_out, "temp_c": temp,
              "park_index": park["index"], "park_index_n": park["index_n"],
              "park_amplifier": round(amp, 4),
              "expected_total_runs_delta": round(runs, 4),
              "adjustment_c": round(adj_c, 3),
              "cents_per_run_total": CENTS_PER_RUN_TOTAL,
              "rung": row.get("yes_sub_title"), "rung_chosen_by": how,
              "elevation_ft": brief["venue"].get("elevation_ft"),
              "azimuth_deg": brief["venue"].get("azimuth_deg"),
              "wx_station": w.get("station"),
              "market_mid_c": _mid_for(row, side),
              **d, "sharp_yardstick": yard}
    if not d["passes"]:
        return Decline("park-air", "adjustment does not survive the cost bar",
                       detail)
    return Intent("park-air", row["ticker"], side, d["price_c"],
                  d["net_edge_c"], d["fair_c"], d["net_edge_c"], window,
                  d["size"], detail)


# ============================================================= M3  bullpen
M3_WINDOWS = {"T-6h", "T-3h", "T-90m"}
M3_MIN_GAMES_SEEN = 5
M3_BAR_C = 1.0
# Assumptions, stated. A depleted bullpen means worse arms for more innings.
M3_RUNS_PER_RELIEVER_USED_YDAY = 0.045
M3_RUNS_PER_HEAVY_RELIEVER = 0.055
M3_RUNS_PER_100_PITCHES_3D = 0.060
M3_RUNS_PER_EXTRA_INNING_GAME = 0.070


def m3_bullpen(brief, window):
    """The third of the game nobody reprices. Both sides add to the total."""
    if window not in M3_WINDOWS:
        return Decline("bullpen", "outside this mentality's windows",
                       {"window": window})
    bp = brief.get("bullpen")
    if not bp:
        return Decline("bullpen", "no bullpen block on the brief")
    rows = _total_rows(brief)
    if not rows:
        return Decline("bullpen", "no KXMLBTOTAL market for this game")

    runs, parts = 0.0, {}
    for side in ("away", "home"):
        b = bp[side] or {}
        if (b.get("games_seen") or 0) < M3_MIN_GAMES_SEEN:
            return Decline("bullpen", f"{side} has too few prior games",
                           {"games_seen": b.get("games_seen"),
                            "floor": M3_MIN_GAMES_SEEN})
        used, heavy = b.get("relievers_used_yesterday"), b.get("relievers_heavy_last3")
        p3, xtra = b.get("bullpen_pitches_last3"), b.get("extra_inning_games_last4")
        if used is None or heavy is None or p3 is None:
            return Decline("bullpen",
                           f"{side} bullpen load missing (missing stays "
                           f"missing)", b)
        r = (M3_RUNS_PER_RELIEVER_USED_YDAY * used
             + M3_RUNS_PER_HEAVY_RELIEVER * heavy
             + M3_RUNS_PER_100_PITCHES_3D * (p3 / 100.0)
             + M3_RUNS_PER_EXTRA_INNING_GAME * (xtra or 0))
        runs += r
        parts[side] = {"used_yesterday": used, "heavy_last3": heavy,
                       "pitches_last3": p3, "extra_innings_last4": xtra,
                       "runs_added": round(r, 4)}

    # A LEAGUE-TYPICAL bullpen is not news. The claim is the DEVIATION from a
    # normal night, and a normal night is roughly 2 relievers used yesterday,
    # 2 carrying a heavy load and ~150 pitches over three days, per side.
    baseline_runs = 2 * (M3_RUNS_PER_RELIEVER_USED_YDAY * 2
                         + M3_RUNS_PER_HEAVY_RELIEVER * 2
                         + M3_RUNS_PER_100_PITCHES_3D * 1.5)
    delta_runs = runs - baseline_runs
    adj_c = delta_runs * CENTS_PER_RUN_TOTAL

    points, how = _main_total_points(brief, rows)
    if points is None:
        return Decline("bullpen", "no tradeable rung", {"how": how})
    row = _rung_nearest(rows, points)
    if row is None:
        return Decline("bullpen", "Kalshi lists no rung at that total",
                       {"points": points})
    side = "YES" if adj_c > 0 else "NO"
    d = _decide(row, side, abs(adj_c), M3_BAR_C)
    yard = _sharp_yardstick(brief, "totals", side, d["price_c"], points)
    detail = {"rule": "bullpen depletion against a league-typical night",
              "direction": "more runs" if adj_c > 0 else "fewer runs",
              "components": parts, "total_runs_added": round(runs, 4),
              "baseline_runs": round(baseline_runs, 4),
              "delta_runs": round(delta_runs, 4),
              "adjustment_c": round(adj_c, 3),
              "rung": row.get("yes_sub_title"), "rung_chosen_by": how,
              "market_mid_c": _mid_for(row, side),
              **d, "sharp_yardstick": yard}
    if not d["passes"]:
        return Decline("bullpen", "adjustment does not survive the cost bar",
                       detail)
    return Intent("bullpen", row["ticker"], side, d["price_c"],
                  d["net_edge_c"], d["fair_c"], d["net_edge_c"], window,
                  d["size"], detail)


# =============================================================== M4  early
M4_WINDOWS = {"T-48h", "T-24h"}
M4_MAX_SPREAD_C = 6
M4_BAR_C = 2.0            # higher bar: this one has no sharp line to check
M4_HOME_FIELD_LOGIT = 0.16
M4_SHRINK_GAMES = 50
M4_LOGIT_PER_ERA_RUN = 0.10


def m4_early(brief, window):
    """The window BEFORE the sharp line exists.

    The only mentality that forms an absolute probability rather than an
    adjustment, because its thesis is that Kalshi's price is unanchored at
    T-48 h and so there is nothing sensible to adjust. The prior is
    deliberately crude and entirely public -- shrunk season win rate, a fixed
    home-field term, a starter-ERA term. Crude is the point: the archive's far
    better tennis model lost to the bookmakers, so a good model is not the
    claim. The claim is that nobody is quoting this game carefully yet.

    Scored primarily on CLOSING-LINE VALUE, not P&L.
    """
    if window not in M4_WINDOWS:
        return Decline("early", "outside this mentality's windows",
                       {"window": window})
    rows = _ml_rows(brief)
    if not rows:
        return Decline("early", "no KXMLBGAME market for this game")
    form = brief.get("form") or {}
    fa, fh = form.get("away"), form.get("home")
    if not fa or not fh:
        return Decline("early", "no team records (missing stays missing)")

    def shrunk(rec):
        w, l = rec.get("wins") or 0, rec.get("losses") or 0
        n = w + l
        if n == 0:
            return None
        return (w + M4_SHRINK_GAMES / 2.0) / (n + M4_SHRINK_GAMES)

    pa, ph = shrunk(fa), shrunk(fh)
    if pa is None or ph is None:
        return Decline("early", "no games played")
    diff = (math.log(ph / (1 - ph)) - math.log(pa / (1 - pa))
            + M4_HOME_FIELD_LOGIT)
    sp_term, prof = 0.0, {}
    for side, sgn in (("home", 1.0), ("away", -1.0)):
        s = brief["starters"][side] or {}
        p = s.get("profile") or {}
        era = p.get("season_era")
        prof[side] = {"name": s.get("name"), "season_era": era,
                      "announced": s.get("announced")}
        if era is not None:
            sp_term += sgn * (4.20 - float(era)) * M4_LOGIT_PER_ERA_RUN
    diff += sp_term
    fair_home_c = 100.0 / (1.0 + math.exp(-diff))

    best = None
    for team_side, fair in (("home", fair_home_c), ("away", 100 - fair_home_c)):
        row = _club_row(brief, rows, team_side)
        if row is None or row["spread"] > M4_MAX_SPREAD_C:
            continue
        price, size = _executable(row, "YES")
        fee = float(fee_order_cents(price, 1))
        edge = round(fair - price - fee - SLIPPAGE_C, 3)
        if best is None or edge > best["net_edge_c"]:
            best = {"team_side": team_side, "row": row, "fair_c": round(fair, 2),
                    "price_c": price, "size": size, "fee_c": round(fee, 3),
                    "net_edge_c": edge}
    if best is None:
        return Decline("early", "no club row inside the spread cap",
                       {"max_spread_c": M4_MAX_SPREAD_C})
    yard = _sharp_yardstick(brief, "moneyline", best["team_side"],
                            best["price_c"])
    detail = {"rule": "crude public prior, before the sharp line exists",
              "backed": brief[f"{best['team_side']}_team"],
              "away_record": [fa.get("wins"), fa.get("losses")],
              "home_record": [fh.get("wins"), fh.get("losses")],
              "shrunk_win_pct": {"away": round(pa, 4), "home": round(ph, 4)},
              "home_field_logit": M4_HOME_FIELD_LOGIT,
              "starter_term_logit": round(sp_term, 4), "starters": prof,
              "fair_home_c": round(fair_home_c, 2),
              "sharp_reference_present": bool(_pin(brief)),
              "bar_c": M4_BAR_C, **{k: v for k, v in best.items()
                                    if k not in ("row",)},
              "sharp_yardstick": yard,
              "caveat": "scored on CLV, not P&L; the prior is deliberately crude"}
    detail.pop("team_side", None)
    if best["net_edge_c"] < M4_BAR_C:
        return Decline("early", "crude public prior does not disagree enough",
                       detail)
    return Intent("early", best["row"]["ticker"], "YES", best["price_c"],
                  best["net_edge_c"], best["fair_c"], best["net_edge_c"],
                  window, best["size"], detail)


# ============================================================== M5  lineup
M5_WINDOWS = {"T-90m", "T-30m"}
M5_MIN_MISSING = 2
M5_BAR_C = 1.0
# Assumption, stated: one top-five regular out of the card costs roughly 0.15
# runs of expected margin against his own side.
M5_RUNS_PER_MISSING_REGULAR = 0.15


def m5_lineup(brief, window):
    """The last free information of the day, treated as a LATENCY question.

    The claim is not that this knows something Pinnacle does not. It is that
    Kalshi has not moved yet. So the reasoning records the de-vigged sharp
    price at decision time as the yardstick, and P3 in PREREGISTRATION measures
    the market's own reaction to the same event independently of any bot.
    """
    if window not in M5_WINDOWS:
        return Decline("lineup", "outside this mentality's windows",
                       {"window": window})
    lu = brief.get("lineup") or {}
    if not lu.get("available"):
        return Decline("lineup", "no lineup block", {"reason": lu.get("reason")})
    rows = _ml_rows(brief)
    if not rows:
        return Decline("lineup", "no KXMLBGAME market for this game")
    posted = {s: (lu.get(s) or {}).get("posted") for s in ("away", "home")}
    if not all(posted.values()):
        return Decline("lineup", "card not posted for both sides", posted)

    missing = {}
    for s in ("away", "home"):
        c = (lu[s] or {}).get("top5_missing_count")
        if c is None:
            return Decline("lineup", f"{s} top-5 comparison unavailable")
        missing[s] = c
    if max(missing.values()) < M5_MIN_MISSING:
        return Decline("lineup", "no material absence", {"missing": missing})
    delta = missing["away"] - missing["home"]      # >0 => away is weakened
    if delta == 0:
        return Decline("lineup", "both sides equally short", {"missing": missing})

    runs = delta * M5_RUNS_PER_MISSING_REGULAR     # signed toward home
    adj_c = runs * CENTS_PER_RUN_MARGIN
    team_side = "home" if adj_c > 0 else "away"
    row = _club_row(brief, rows, team_side)
    if row is None:
        return Decline("lineup", "could not locate the club's market row",
                       {"team_side": team_side})
    d = _decide(row, "YES", abs(adj_c), M5_BAR_C)
    yard = _sharp_yardstick(brief, "moneyline", team_side, d["price_c"])
    detail = {"rule": "lineup-drop latency, not lineup information",
              "backed": brief[f"{team_side}_team"],
              "top5_missing_count": missing,
              "top5_missing": {s: (lu[s] or {}).get("top5_missing")
                               for s in ("away", "home")},
              "expected_margin_runs": round(runs, 4),
              "adjustment_c": round(adj_c, 3),
              "market_mid_c": _mid_for(row, "YES"),
              **d, "sharp_yardstick": yard}
    if not d["passes"]:
        return Decline("lineup",
                       "Kalshi has already repriced -- no lag left to trade",
                       detail)
    return Intent("lineup", row["ticker"], "YES", d["price_c"],
                  d["net_edge_c"], d["fair_c"], d["net_edge_c"], window,
                  d["size"], detail)


MENTALITIES = {
    "starter": m1_starter, "park-air": m2_park_air, "bullpen": m3_bullpen,
    "early": m4_early, "lineup": m5_lineup,
}
TARGET = {"starter": "KXMLBGAME", "park-air": "KXMLBTOTAL",
          "bullpen": "KXMLBTOTAL", "early": "KXMLBGAME",
          "lineup": "KXMLBGAME"}
WINDOWS_FOR = {"starter": M1_WINDOWS, "park-air": M2_WINDOWS,
               "bullpen": M3_WINDOWS, "early": M4_WINDOWS,
               "lineup": M5_WINDOWS}
EXIT_MODES = ("hold", "exit-once", "free")
BOT_IDS = [f"{m}__{e}" for m in MENTALITIES for e in EXIT_MODES] + \
          ["control__no-trade"]
assert len(BOT_IDS) == 16, "PREREGISTRATION declares 16 MLB bots"

ALL_WINDOWS = ("T-48h", "T-24h", "T-6h", "T-3h", "T-90m", "T-30m")
WINDOW_HOURS = {"T-48h": 48.0, "T-24h": 24.0, "T-6h": 6.0, "T-3h": 3.0,
                "T-90m": 1.5, "T-30m": 0.5}
WINDOW_TOL_H = {"T-48h": 12.0, "T-24h": 6.0, "T-6h": 1.5, "T-3h": 1.0,
                "T-90m": 0.5, "T-30m": 0.25}


def window_for(hours_to_first_pitch):
    """Which decision window a brief falls in, or None."""
    for w in ALL_WINDOWS:
        if abs(hours_to_first_pitch - WINDOW_HOURS[w]) <= WINDOW_TOL_H[w]:
            return w
    return None
