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
import fees as F                                      # noqa: E402

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
    # ⚠ TWO FEE ERRORS FIXED 2026-09-02, and they stacked.
    #
    # (a) `fee_order_cents(price, 1)` applied Kalshi's per-ORDER round-up to a
    #     single contract. `common/kalshi_fees.py` says in its own docstring
    #     that `fee_rate_cents` is the one for expectancy, "where the per-order
    #     round-up is an artefact of order size rather than an economic cost".
    # (b) It used the FULL taker rate. Kalshi charges HALF on KXMLBGAME and
    #     KXMLBTOTAL (fee_multiplier 0.5), verified live against the API.
    #
    # Together the gate demanded ~3c of edge where the real one-way cost is
    # closer to 1c -- 2.3x at 50c, 6x at 95c. The error was in the SAFE
    # direction (it suppressed bets, it did not manufacture them), so every
    # result recorded before this date is understated, not inflated.
    fee = F.edge_fee_c(price, row["ticker"])
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


def _series_for_kind(kind):
    """Which Kalshi series a yardstick `kind` refers to.

    ⚠ The SERIES is determined by the kind; the RATE is then looked up live by
    `fees.rate_for`. Never hardcode the rate here -- both of these happen to be
    half-fee today and that is exactly the kind of coincidence that becomes a
    wrong constant later.
    """
    return "KXMLBGAME" if kind == "moneyline" else "KXMLBTOTAL"


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
                    fair - price_c - F.edge_fee_c(price_c, _series_for_kind(kind))
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
                fair - price_c - F.edge_fee_c(price_c, _series_for_kind(kind))
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
# ⚠ AMENDMENT A3, 2026-08-12. A DEFECT FIX, not a parameter tune.
#
# MENTALITIES.md and PREREGISTRATION describe this trigger as "a starter whose
# LAST THREE OUTINGS differ from his season line". The code did not implement
# that: `starter_profile` computes `recent_era` from however many prior starts
# exist, guarded only by `rec_ip > 0` -- one third of an inning qualified. So a
# pitcher with ONE career start and one bad outing produced
# recent_minus_season_era = 13.75, which times 2.75c gives a 41.7-cent
# adjustment and declared a 67-cent market worth 99.
#
# Worse, the same pitcher was ALSO charged M1_DEBUT_RUNS. The debut flag exists
# because there is no reliable recent form; the code then trusted recent form
# computed from that same single game. Double-counted, in opposite directions.
#
# Found by the `livedesk` session (mailbox 008) while writing the reason onto a
# card it could not say with a straight face. 9 of 43 entries leaned on a
# pitcher with <=3 career starts.
M1_MIN_PRIOR_STARTS_FOR_FORM = 3   # "last three outings" means three
M1_MIN_RECENT_IP_FOR_FORM = 12.0   # ~3 starts of real work, not one relief inning
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
        prof = s["profile"]
        prior = prof.get("career_starts_prior") or 0
        rec_ip = prof.get("recent_ip") or 0.0
        form_usable = (prior >= M1_MIN_PRIOR_STARTS_FOR_FORM
                       and rec_ip >= M1_MIN_RECENT_IP_FOR_FORM)
        # d < 0 means pitching BETTER lately, which helps his own side
        if abs(d) >= M1_MIN_DIVERGENCE_ER9 and form_usable:
            f.append("form_divergence")
            runs += sgn * (-d) * (M1_C_PER_ER9 / CENTS_PER_RUN_MARGIN)
        elif abs(d) >= M1_MIN_DIVERGENCE_ER9:
            # The divergence is large but rests on too little pitching to mean
            # anything. Recorded so the decline is legible, never used.
            #
            # ⚠ The flag NAME carries no numbers, deliberately. A3's first
            # version emitted `form_divergence_IGNORED_only_1_starts_5.1ip`,
            # and `livedesk` (mailbox 009) is keying a duplicate-signal guard on
            # these strings: the innings count moves between decision windows,
            # so the identical bet produced a fresh key three times a day and
            # their guard would silently never have fired. The counts belong in
            # FIELDS, which are right below, not in an identifier.
            f.append("form_divergence_IGNORED_insufficient_sample")
        if s.get("debut_or_near"):
            f.append("debut_or_near")
            runs -= sgn * M1_DEBUT_RUNS
        if s.get("short_rest"):
            f.append("short_rest")
            runs -= sgn * M1_SHORT_REST_RUNS
        flags[side] = {"flags": f, "divergence_er9": d,
                       "career_starts_prior": prior, "recent_ip": rec_ip,
                       "form_usable": form_usable,
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
        fee = F.edge_fee_c(price, row["ticker"])       # see _decide
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
# NOTE: HOLD_ONLY is defined further down, with the five strategies added
# 2026-09-03. BOT_IDS is rebuilt there once it exists.
BOT_IDS = [f"{m}__{e}" for m in MENTALITIES for e in EXIT_MODES] + \
          ["control__no-trade"]

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

# ============================================ the inverse bot (mailbox 020)
INVERSE_OF = "bullpen"
INVERSE_NAME = "bullpen-inverse"


def invert_intent(brief, intent):
    """Buy the OTHER club in the same game. His idea, mailbox 020.

    His distinction, and it is computable: a bot that loses about what it costs
    to trade is leaking fees, and flipping it gains nothing. A bot that loses
    far MORE than it costs to trade is picking the wrong team, and flipping it
    should win. `bullpen` is the second kind; `early` is the first, and is the
    control that shows the distinction is real.

    ⚠ This takes the opposite side by BUYING THE OTHER CLUB'S CONTRACT at that
    club's real ask -- not by selling the one we hold. Those are not the same
    trade. Selling would cross our own spread; buying the other side pays the
    other book's ask, which is what a real opposite position costs.

    ⚠ IN-SAMPLE UNTIL 60 GAMES. `bullpen` was chosen as the WORST of 16 bots,
    and inverting the worst of sixteen is the same selection effect as promoting
    the best of sixteen, mirrored. `PREREGISTRATION_INVERSE.md` fixes the count
    and what drops it, and was committed before this ran.
    """
    rows = _ml_rows(brief)
    if not rows:
        return None
    other = [r for r in rows if r["ticker"] != intent.ticker]
    if len(other) != 1:
        return None                       # never guess which side is opposite
    row = other[0]
    price, size = _executable(row, "YES")
    if not price:
        return None
    fee = F.edge_fee_c(price, row["ticker"])           # see _decide
    # The inverse has no fair value of its own. Its claim is only that the
    # original is wrong, so its stated edge is the original's edge carried
    # across, minus the cost of getting in on this side. Recorded as such
    # rather than dressed up as a model.
    edge = round((intent.edge_c or 0.0) - fee - SLIPPAGE_C, 3)
    detail = {"rule": "the opposite side of a bot that loses more than it costs",
              "inverts": intent.mentality,
              "original_ticker": intent.ticker,
              "original_price_c": intent.entry_price_c,
              "original_edge_c": intent.edge_c,
              "price_c": price, "fee_c": round(fee, 3),
              "net_edge_c": edge,
              "caveat": "IN-SAMPLE until 60 games settle after 2026-08-26. "
                        "bullpen was chosen as the worst of 16 bots; "
                        "inverting the worst of N is the same selection as "
                        "promoting the best of N. See PREREGISTRATION_INVERSE.md"}
    return Intent(INVERSE_NAME, row["ticker"], "YES", price, edge, None,
                  edge, intent.window, size, detail)

# ===================================================================
# The five added 2026-09-03 for the freed slots. PREREGISTRATION_FLEET2.md
# was committed before any of them ran.
#
# FIVE, NOT TEN. Eleven candidates were screened offline against the archive
# and five survived. Filling the rest with near-copies would re-create the
# duplicate problem that freed the slots -- an empty slot costs nothing extra,
# a fake strategy costs the denominator and lies about breadth.
#
# M6/M7 are new INSTRUMENTS: nothing else in this fleet reads the schedule.
# M8/M9/M10 are deliberate PAIRED refinements of `starter`. They share most of
# their games with it, so the game outcome cancels and the comparison is about
# 4x cheaper -- difference-spread 24.7c against 49.6c unpaired, measured here.
# They are NOT independent tests of the pitcher idea and must never be reported
# as if they were.
# ===================================================================
M6_WINDOWS = {"T-24h", "T-6h"}
M6_BAR_C = 1.0
M6_MIN_REST_GAP = 1          # days
M6_C_PER_REST_DAY = 2.0      # ASSUMED, not measured. See m6_rested.

M7_WINDOWS = {"T-24h", "T-6h"}
M7_BAR_C = 1.0
M7_MIN_MILES = 1200.0
M7_MIN_MILE_GAP = 600.0
M7_C_PER_1000_MILES = 1.5    # ASSUMED, not measured.

M9_MIN_EDGE_C = 3.0
M10_MAX_PRICE_C = 50


def _sched(brief, side):
    """Schedule context for a side, or {} -- missing stays missing."""
    return ((brief.get("schedule") or {}).get(side) or {})


def m6_rested(brief, window):
    """Back the better-rested side. Nothing else in this fleet reads rest.

    M6_C_PER_REST_DAY = 2.0 is ASSUMED, not measured -- the same shape of guess
    that left `lineup` unable to fire for three weeks. It is named here so the
    next reader cannot mistake it for a finding.

    The registered benchmark is "always back the home team", which returned
    -5.5% on 664 archive games, because rest correlates with home advantage and
    this could be home-field wearing a new name.
    """
    if window not in M6_WINDOWS:
        return Decline("rested", "outside this mentality's windows",
                       {"window": window})
    rows = _ml_rows(brief)
    if not rows:
        return Decline("rested", "no KXMLBGAME market for this game")
    a = _sched(brief, "away").get("rest_days")
    h = _sched(brief, "home").get("rest_days")
    if a is None or h is None:
        return Decline("rested", "no rest information (missing stays missing)")
    gap = h - a
    if abs(gap) < M6_MIN_REST_GAP:
        return Decline("rested", "both sides equally rested",
                       {"rest_days": {"away": a, "home": h}})
    side = "home" if gap > 0 else "away"
    adj_c = abs(gap) * M6_C_PER_REST_DAY
    row = _club_row(brief, rows, side)
    if row is None:
        return Decline("rested", "could not locate the club's market row")
    d = _decide(row, "YES", adj_c, M6_BAR_C)
    detail = {"rule": "back the better-rested side",
              "backed": brief[side + "_team"],
              "rest_days": {"away": a, "home": h},
              "adjustment_c": round(adj_c, 3),
              "cents_per_rest_day_ASSUMED": M6_C_PER_REST_DAY, **d,
              "sharp_yardstick": _sharp_yardstick(brief, "moneyline", side,
                                                  d["price_c"])}
    if not d["passes"]:
        return Decline("rested", "rest gap does not survive the cost bar",
                       detail)
    return Intent("rested", row["ticker"], "YES", d["price_c"], d["net_edge_c"],
                  d["fair_c"], d["net_edge_c"], window, d["size"], detail)


def m7_travel(brief, window):
    """Fade the side that has just flown furthest. Assumption flagged as such."""
    if window not in M7_WINDOWS:
        return Decline("travel", "outside this mentality's windows",
                       {"window": window})
    rows = _ml_rows(brief)
    if not rows:
        return Decline("travel", "no KXMLBGAME market for this game")
    a = _sched(brief, "away").get("travel_miles")
    h = _sched(brief, "home").get("travel_miles")
    if a is None or h is None:
        return Decline("travel", "no travel information (missing stays missing)")
    if max(a, h) < M7_MIN_MILES or abs(a - h) < M7_MIN_MILE_GAP:
        return Decline("travel", "no material travel difference",
                       {"travel_miles": {"away": a, "home": h}})
    side = "home" if a > h else "away"
    adj_c = (abs(a - h) / 1000.0) * M7_C_PER_1000_MILES
    row = _club_row(brief, rows, side)
    if row is None:
        return Decline("travel", "could not locate the club's market row")
    d = _decide(row, "YES", adj_c, M7_BAR_C)
    detail = {"rule": "fade the side that has just flown furthest",
              "backed": brief[side + "_team"],
              "travel_miles": {"away": a, "home": h},
              "adjustment_c": round(adj_c, 3),
              "cents_per_1000_miles_ASSUMED": M7_C_PER_1000_MILES, **d,
              "sharp_yardstick": _sharp_yardstick(brief, "moneyline", side,
                                                  d["price_c"])}
    if not d["passes"]:
        return Decline("travel", "travel gap does not survive the cost bar",
                       detail)
    return Intent("travel", row["ticker"], "YES", d["price_c"], d["net_edge_c"],
                  d["fair_c"], d["net_edge_c"], window, d["size"], detail)


def _starter_refinement(brief, window, name, accept, why):
    """`starter`'s own signal, taken only when `accept(intent)` is true."""
    res = m1_starter(brief, window)
    if isinstance(res, Decline):
        return Decline(name, "starter declined: " + res.reason, res.detail)
    if not accept(res):
        return Decline(name, why, {"starter_price_c": res.entry_price_c,
                                   "starter_edge_c": res.edge_c})
    d = dict(res.reasoning or {})
    d["rule"] = "starter's signal, restricted: " + why
    d["paired_with"] = "starter"
    return Intent(name, res.ticker, res.side, res.entry_price_c,
                  res.conviction, res.stated_prob_c, res.edge_c, window,
                  res.top_of_book_size, d)


def m8_consensus(brief, window):
    """`starter`, only where another strategy is also in this game.

    This pattern has been LOOKED AT repeatedly and never traded. Making it a
    pre-registered forward bot is how a looked-at pattern becomes evidence
    rather than a story. Its archive figure (+6.7% on 242 games) is IN-SAMPLE
    and is not a prediction.
    """
    others = 0
    for nm in ("early", "bullpen", "park-air", "lineup", "travel"):
        fn = MENTALITIES.get(nm)
        if not fn or window not in WINDOWS_FOR.get(nm, set()):
            continue
        try:
            if isinstance(fn(brief, window), Intent):
                others += 1
        except Exception:                               # noqa: BLE001
            continue
    return _starter_refinement(brief, window, "consensus",
                               lambda i: others > 0,
                               "no other strategy is in this game")


def m9_conviction(brief, window):
    return _starter_refinement(
        brief, window, "conviction",
        lambda i: (i.edge_c or 0) >= M9_MIN_EDGE_C,
        "does not clear " + str(M9_MIN_EDGE_C) + "c of edge")


def m10_underdog(brief, window):
    return _starter_refinement(
        brief, window, "underdog",
        lambda i: i.entry_price_c < M10_MAX_PRICE_C,
        "is not priced below " + str(M10_MAX_PRICE_C) + "c")


# ⚠ `rested` (m6) IS DELIBERATELY NOT REGISTERED. It is kept below as dead
# code with its evidence, because deleting it is how the same idea gets
# re-proposed in a month.
#
# It requires a rest-day GAP of 2 or more between the two sides to clear the
# cost bar. Measured over 2,125 games: gap 0 is 92 in 100, gap 1 is 8 in 100,
# and **gap 2 or more has never once occurred.** Baseball teams play daily.
#
# So it could never fire -- the exact `lineup` failure, an untested hypothesis
# wearing the costume of a null. Caught in a dry run before it took a slot
# rather than three weeks later.
#
# NOT FIXED BY TUNING `M6_C_PER_REST_DAY` UPWARD. That is choosing the dial to
# get the answer, and it is the same thing I refused to do for `lineup`.
MENTALITIES.update({"travel": m7_travel,
                    "consensus": m8_consensus, "conviction": m9_conviction,
                    "underdog": m10_underdog})
TARGET.update({"travel": "KXMLBGAME",
                   "consensus": "KXMLBGAME", "conviction": "KXMLBGAME",
                   "underdog": "KXMLBGAME"})
WINDOWS_FOR.update({"travel": M7_WINDOWS,
                    "consensus": M1_WINDOWS, "conviction": M1_WINDOWS,
                    "underdog": M1_WINDOWS})

#: Only these three take the hold/exit-once/free triple. The five added in
#: 2026-09 are HOLD-ONLY: the exit dimension fired 3 times in 1,516 positions
#: and adding it to five more strategies would buy ten more duplicates.
HOLD_ONLY = {"travel", "consensus", "conviction", "underdog"}

# ------------------------------------------------------------------ the fleet
# Rebuilt now that HOLD_ONLY exists.
#
# The five strategies added 2026-09-03 are HOLD-ONLY. The exit dimension fired
# 3 times in 1,516 positions and produced ten bit-identical duplicates; giving
# it to five more strategies would simply buy ten more.
BOT_IDS = ([f"{m}__{e}" for m in MENTALITIES if m not in HOLD_ONLY
            for e in EXIT_MODES]
           + [f"{m}__hold" for m in sorted(HOLD_ONLY)]
           + ["control__no-trade"])

# THE DENOMINATOR RISES AND DOES NOT FALL. This assert was 16 and is now 20.
# JOINT_MULTIPLICITY.md counts ONE denominator across this fleet and tennis's,
# so the repo goes 16 + 16 = 32 -> 20 + 16 = 36, and every previously reported
# number is recomputed against 37. That cost lands on the tennis chat too,
# which did not ask for it; it is flagged in PREREGISTRATION_FLEET2.md rather
# than absorbed silently.
assert len(BOT_IDS) == 20, "PREREGISTRATION_FLEET2 declares 20 MLB bots"

# ============================================ M11  bullpen-f5: the NEGATIVE CONTROL
#
# The factory's SF201, and it is the best idea anyone has sent this project.
#
# `bullpen` claims to read RELIEVER fatigue and trades the full-game run total.
# This runs THE SAME TRIGGER against the FIRST FIVE INNINGS total.
#
# **Relief pitchers do not pitch the first five innings. So this must find
# nothing.**
#
# If it makes money, `bullpen` is not measuring bullpens -- it is picking up
# something else (the starter, the park, the teams) and every number that bot
# has ever produced means something other than what it says.
#
# That is a negative control on a LIVE bot, which this repo has never run, and
# it costs one slot. GUARDS #3 and #4 are exactly this shape.
#
# ⚠ HOW TO READ IT, registered before it runs:
#   - it loses money or finds nothing  -> `bullpen` is measuring what it claims
#   - it makes money                   -> `bullpen` is MISLABELLED, and that is
#                                         a finding about the fleet, not a
#                                         strategy to trade
# **A profit here is bad news, not good news.** Nobody should be tempted to
# promote it.
M11_WINDOWS = M3_WINDOWS
M11_BAR_C = 1.0


def _f5_total_rows(brief):
    return (brief.get("market", {}).get("kalshi", {}) or {}).get(
        "KXMLBF5TOTAL", [])


def m11_bullpen_f5(brief, window):
    """`bullpen`'s trigger, pointed at a market relievers cannot affect."""
    if window not in M11_WINDOWS:
        return Decline("bullpen-f5", "outside this mentality's windows",
                       {"window": window})
    rows = _f5_total_rows(brief)
    if not rows:
        return Decline("bullpen-f5", "no KXMLBF5TOTAL market for this game")

    inner = m3_bullpen(brief, window)
    if isinstance(inner, Decline):
        return Decline("bullpen-f5", "bullpen declined: " + inner.reason,
                       inner.detail)

    det = dict(inner.reasoning or {})
    adj_c = det.get("adjustment_c")
    if adj_c is None:
        return Decline("bullpen-f5", "bullpen gave no adjustment", det)

    # The same signed view, on the first-five total. The rung is chosen the
    # same way; only the instrument changes.
    points, how = _main_total_points(brief, rows)
    if points is None:
        return Decline("bullpen-f5", "no tradeable first-five rung",
                       {"how": how})
    row = _rung_nearest(rows, points)
    if row is None:
        return Decline("bullpen-f5", "Kalshi lists no first-five rung there",
                       {"points": points})
    side = "YES" if adj_c > 0 else "NO"
    d = _decide(row, side, abs(adj_c), M11_BAR_C)
    detail = {"rule": "NEGATIVE CONTROL: bullpen's trigger on a market "
                      "relievers cannot affect",
              "controls": "bullpen",
              "expected": "nothing -- relievers do not pitch innings 1-5",
              "a_profit_here_means": "bullpen is mislabelled, NOT that this "
                                     "is tradeable",
              "adjustment_c": adj_c,
              "rung": row.get("yes_sub_title"), "rung_chosen_by": how,
              "full_game_ticker": inner.ticker, **d}
    if not d["passes"]:
        return Decline("bullpen-f5",
                       "adjustment does not survive the cost bar", detail)
    return Intent("bullpen-f5", row["ticker"], side, d["price_c"],
                  d["net_edge_c"], d["fair_c"], d["net_edge_c"], window,
                  d["size"], detail)


MENTALITIES.update({"bullpen-f5": m11_bullpen_f5})
TARGET.update({"bullpen-f5": "KXMLBF5TOTAL"})
WINDOWS_FOR.update({"bullpen-f5": M11_WINDOWS})
HOLD_ONLY.add("bullpen-f5")

BOT_IDS = ([f"{m}__{e}" for m in MENTALITIES if m not in HOLD_ONLY
            for e in EXIT_MODES]
           + [f"{m}__hold" for m in sorted(HOLD_ONLY)]
           + ["control__no-trade"])
# 20 -> 21. Joint denominator 16+16=32 -> 21+16=37 before tennis's own five.
assert len(BOT_IDS) == 21, "PREREGISTRATION_CONTROL declares 21 MLB bots"
