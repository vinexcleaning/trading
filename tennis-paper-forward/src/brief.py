"""brief.py — the pre-match brief the bots read.

One brief per match, built from free sources only, written to disk BEFORE any
bot is asked for a decision and before the result is known. The brief is the
evidence; the bots' reasoning logs reference it by hash so the two cannot drift.

WHAT IS IN IT
    The four things the specification named - player history, surface record,
    recent form, third-set record, response after losing serve - plus every
    other field the free sources actually carry, because leaving a free field
    out is a choice that has to be justified and none of these needed
    justifying: rank and rank points, elo and surface elo, hand, height,
    nationality, age, workload and rest days, retirement rate, tiebreak
    record, straight-sets share, serve and return splits with their own
    denominators, head-to-head with the individual meetings, and the market's
    own quote.

EVERY RATE CARRIES ITS DENOMINATOR
    `{"value": 0.61, "n": 23}`, never a bare 0.61. A player with a 100% third-set
    record over two matches and one with 62% over 180 are not the same fact and
    a bot that cannot see the difference will treat them as if they were.

MISSING IS A VALUE
    Unresolvable player, absent surface, no charting coverage - all None, and
    `coverage` counts them. A brief that invents a number to avoid a null is
    the failure this repo has recorded most often.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from typing import Any

from . import charting
from .kalshi_read import MatchView
from .sackmann import Archive, PlayerRecord, get_archive, norm_name


def _r(w: int, n: int) -> dict[str, Any]:
    """A rate that always carries its denominator."""
    return {"value": (w / n) if n else None, "w": w, "n": n}


def _ratio(num: int, den: int) -> dict[str, Any]:
    return {"value": (num / den) if den else None, "num": num, "n": den}


def _to_date(yyyymmdd: int) -> date | None:
    s = str(yyyymmdd)
    if len(s) != 8:
        return None
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:]))
    except ValueError:
        return None


def _elo_prob(a: float, b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((b - a) / 400.0))


def player_block(rec: PlayerRecord | None, *, surface: str | None,
                 level: str | None, rnd: str | None,
                 today: date, archive_last: int) -> dict[str, Any]:
    if rec is None:
        return {"resolved": False}

    b: dict[str, Any] = {"resolved": True, "name": rec.name}
    b["career"] = _r(rec.wins, rec.matches)

    # -- surface -----------------------------------------------------------
    if surface and surface in rec.by_surface:
        w, n = rec.by_surface[surface]
        b["surface"] = {"which": surface, **_r(w, n)}
    else:
        b["surface"] = {"which": surface, "value": None, "w": 0, "n": 0}
    b["surface_all"] = {k: _r(v[0], v[1]) for k, v in rec.by_surface.items()}

    # -- tier and round ----------------------------------------------------
    if level and level in rec.by_level:
        w, n = rec.by_level[level]
        b["level"] = {"which": level, **_r(w, n)}
    else:
        b["level"] = {"which": level, "value": None, "w": 0, "n": 0}
    if rnd and rnd in rec.by_round:
        w, n = rec.by_round[rnd]
        b["round"] = {"which": rnd, **_r(w, n)}
    else:
        b["round"] = {"which": rnd, "value": None, "w": 0, "n": 0}

    # -- recent form -------------------------------------------------------
    res = sorted(rec.results)
    last10 = res[-10:]
    last20 = res[-20:]
    b["form_last10"] = _r(sum(x[1] for x in last10), len(last10))
    b["form_last20"] = _r(sum(x[1] for x in last20), len(last20))
    if surface:
        surf_res = [x for x in res if x[2] == surface][-10:]
        b["form_last10_surface"] = _r(sum(x[1] for x in surf_res), len(surf_res))
    else:
        b["form_last10_surface"] = _r(0, 0)

    last_played = _to_date(res[-1][0]) if res else None
    b["last_match_date"] = last_played.isoformat() if last_played else None
    b["days_since_last_match"] = (today - last_played).days if last_played else None
    if last_played:
        cut28 = (today - last_played).days
        recent = [x for x in res if (_to_date(x[0]) and (today - _to_date(x[0])).days <= 28)]
        b["matches_last_28d"] = len(recent)
        recent90 = [x for x in res if (_to_date(x[0]) and (today - _to_date(x[0])).days <= 90)]
        b["form_last90d"] = _r(sum(x[1] for x in recent90), len(recent90))
        b["_cut28"] = cut28
    else:
        b["matches_last_28d"] = None
        b["form_last90d"] = _r(0, 0)

    # -- deciding set, tiebreaks, attrition --------------------------------
    b["deciding_set"] = _r(rec.deciding_won, rec.deciding_played)
    b["straight_set_share"] = _ratio(rec.straight_wins, rec.wins)
    b["tiebreaks_played"] = rec.tiebreaks_played
    b["retired_rate"] = _ratio(rec.retired_own, rec.matches)
    b["opp_retired"] = rec.opp_retired
    b["avg_minutes"] = (rec.minutes / rec.minutes_matches) if rec.minutes_matches else None
    b["avg_minutes_n"] = rec.minutes_matches

    # -- serve / return, from the match files ------------------------------
    b["serve"] = {
        "stat_matches": rec.stat_matches,
        "first_in": _ratio(rec.first_in, rec.svpt),
        "first_won": _ratio(rec.first_won, rec.first_in),
        "second_won": _ratio(rec.second_won, max(0, rec.svpt - rec.first_in)),
        "ace_rate": _ratio(rec.aces, rec.svpt),
        "df_rate": _ratio(rec.dfs, rec.svpt),
        "bp_saved": _ratio(rec.bp_saved, rec.bp_faced),
        "bp_faced_per_svgm": (rec.bp_faced / rec.sv_gms) if rec.sv_gms else None,
    }
    b["ret_bp_conversion"] = _ratio(rec.ret_bp_won, rec.ret_bp_chances)

    # -- rating and identity ----------------------------------------------
    b["elo"] = round(rec.elo, 1)
    b["elo_matches"] = rec.elo_matches
    b["elo_surface"] = ({surface: round(rec.elo_surface[surface], 1)}
                        if surface and surface in rec.elo_surface else {})
    b["rank"] = rec.rank
    b["rank_points"] = rec.rank_points
    b["hand"] = rec.hand
    b["height_cm"] = rec.height
    b["country"] = rec.ioc
    b["archive_matches"] = rec.matches

    # -- the one field the match files cannot answer -----------------------
    ch = charting.lookup(rec.name)
    if ch and ch.get("serve_games"):
        b["response_after_losing_serve"] = {
            "source": "MatchChartingProject point-by-point",
            "charted_matches": ch["matches"],
            "hold_rate": {"value": ch["hold_rate"], "n": ch["serve_games"]},
            "break_rate": {"value": ch["break_rate"], "n": ch["return_games"]},
            "times_broken": ch["broken"],
            "break_back_immediately": {"value": ch["breakback_rate"],
                                       "n": ch["breakback_chances"]},
            "hold_next_service_game": {"value": ch["hold_after_broken"],
                                       "n": ch["held_after_broken_chances"]},
            # the deltas ARE the claim; the raw rates alone are not
            "break_back_vs_own_baseline": ch["breakback_delta"],
            "hold_after_broken_vs_own_baseline": ch["hold_after_broken_delta"],
            # ...and THESE are the controlled claim - the same two quantities
            # measured after a HOLD instead, same match and same opponent, so
            # only what just happened differs. GUARDS #20.
            "control_break_after_hold": {"value": ch.get("break_after_hold"),
                                         "n": ch.get("breakback_after_hold_chances", 0)},
            "control_hold_after_hold": {"value": ch.get("hold_after_hold"),
                                        "n": ch.get("held_after_hold_chances", 0)},
            "break_back_vs_control": ch.get("breakback_vs_control"),
            "hold_after_broken_vs_control": ch.get("hold_after_broken_vs_control"),
            "population_prior": (
                "Across 185 charted players with >=50 occasions of each, being "
                "broken is followed by a 3.33pp LOWER chance of breaking back on "
                "the very next return game (CI95 [-4.14,-2.52]) and a 5.55pp lower "
                "chance of holding the next service game (CI95 [-6.39,-4.72]), "
                "against the matched after-a-hold control. Player-clustered, "
                "computed 2026-08-06. A player at the population mean has no edge; "
                "only a player who departs from it is saying anything."
            ),
        }
    else:
        b["response_after_losing_serve"] = {
            "source": "MatchChartingProject point-by-point",
            "charted_matches": 0,
            "note": "no point-by-point coverage for this player - not zero, absent",
        }
    return b


@dataclass
class Brief:
    event_ticker: str
    built_at: str
    tour: str
    tier: str
    series: str
    tournament: str | None
    round: str | None
    surface: str | None
    surface_source: str
    surface_meta: dict[str, Any]
    player_a: str
    player_b: str
    a: dict[str, Any]
    b: dict[str, Any]
    h2h: dict[str, Any]
    market: dict[str, Any]
    model: dict[str, Any]
    staleness_days: int | None
    archive_last_date: int | None
    coverage: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


def build_brief(mv: MatchView, *, today: date | None = None) -> Brief:
    today = today or datetime.now(timezone.utc).date()
    arch: Archive = get_archive(mv.tour)
    warnings: list[str] = []

    name_a = mv.primary.player
    name_b = mv.mirror.player if mv.mirror else (mv.primary.rules.get("surname_b") or "")
    if not mv.mirror:
        warnings.append("only one side of the event is listed; opponent taken from the rules text")

    rec_a = arch.find(name_a, mv.primary.rules.get("surname_a"))
    rec_b = arch.find(name_b, mv.primary.rules.get("surname_b"))
    if rec_a is None:
        warnings.append(f"player not resolved in the archive: {name_a!r}")
    if rec_b is None:
        warnings.append(f"player not resolved in the archive: {name_b!r}")

    # Surface: the archive's own tourney_name -> surface record first, because
    # it covers the ITF and Challenger venues that are 73% of what Kalshi lists
    # and that no hand-written table was ever going to enumerate. The regex
    # table in kalshi_read is the fallback for main-tour names.
    from .sackmann import get_surface_index
    surface, surf_meta = get_surface_index().lookup(mv.tournament)
    surface_source = surf_meta.get("source", "archive venue index")
    if surface is None and mv.surface:
        surface, surface_source = mv.surface, "main-tour name table"
        surf_meta = {**surf_meta, "fell_back_to": "main-tour name table"}
    if surface is None:
        warnings.append(
            f"surface unknown ({surf_meta.get('reason')}) - NOT guessed. Every "
            f"surface figure below is the all-surface figure.")

    level = {"ATP": "A", "WTA": "A", "CH": "C", "ITF": "S"}.get(mv.tier)
    rnd = mv.round

    a = player_block(rec_a, surface=surface, level=level, rnd=rnd,
                     today=today, archive_last=arch.last_date)
    b = player_block(rec_b, surface=surface, level=level, rnd=rnd,
                     today=today, archive_last=arch.last_date)

    h2h = arch.head_to_head(name_a, name_b) if (rec_a and rec_b) else {
        "n": 0, "a_wins": 0, "b_wins": 0, "meetings": [],
        "note": "at least one player unresolved - H2H not computable",
    }

    q = mv.primary
    market = {
        "ticker": q.ticker,
        "pays_on": q.player,
        "yes_bid": q.yes_bid,
        "yes_ask": q.yes_ask,
        "spread": q.spread,
        "yes_bid_size": q.yes_bid_size,
        "yes_ask_size": q.yes_ask_size,
        "mid_DIAGNOSTIC_ONLY": q.mid,
        "last": q.last,
        "volume": q.volume,
        "open_interest": q.open_interest,
        "mirror_yes_ask": mv.mirror.yes_ask if mv.mirror else None,
        "pair_ask_sum": (
            (q.yes_ask + mv.mirror.yes_ask)
            if (mv.mirror and q.yes_ask is not None and mv.mirror.yes_ask is not None)
            else None
        ),
        "stale_book": mv.crossed(),
        "gross_arb_cents": mv.gross_arb_cents(),
        "status": q.status,
        "expected_expiration": q.expected_expiration,
    }
    if market["stale_book"]:
        warnings.append("the two BIDS sum to over 100c, which cannot happen in a live book - one side is stale")

    # -- the brief's own estimate, and it is explicitly not a good one ------
    model: dict[str, Any] = {"elo_prob_a": None, "elo_prob_a_surface": None,
                             "rank_prob_a": None, "note": ""}
    if rec_a and rec_b:
        model["elo_prob_a"] = round(_elo_prob(rec_a.elo, rec_b.elo), 4)
        sa = rec_a.elo_surface.get(surface) if surface else None
        sb = rec_b.elo_surface.get(surface) if surface else None
        if sa is not None and sb is not None:
            model["elo_prob_a_surface"] = round(_elo_prob(sa, sb), 4)
        if rec_a.rank and rec_b.rank:
            # crude, deliberately: log-rank difference, no fitting
            import math
            d = math.log(rec_b.rank) - math.log(rec_a.rank)
            model["rank_prob_a"] = round(1.0 / (1.0 + math.exp(-0.55 * d)), 4)
    model["note"] = (
        "elo is computed forward-only from the free archive and is NOT fitted "
        "to prices. This repo has already measured that a far better tennis "
        "model loses the accuracy contest to the bookmakers (+0.01922 Brier, "
        "n=2,645). Treat this as a reference point, not as fair value."
    )

    last_dt = _to_date(arch.last_date)
    staleness = (today - last_dt).days if last_dt else None
    if staleness is not None and staleness > 21:
        warnings.append(
            f"the free archive's last match is {staleness} days old - anything "
            f"called 'recent form' is form as of {last_dt}, not as of yesterday"
        )

    coverage = {
        "player_a_resolved": bool(rec_a),
        "player_b_resolved": bool(rec_b),
        "surface_known": surface is not None,
        "round_known": rnd is not None,
        "h2h_n": h2h.get("n", 0),
        "charting_a": a.get("response_after_losing_serve", {}).get("charted_matches", 0) if rec_a else 0,
        "charting_b": b.get("response_after_losing_serve", {}).get("charted_matches", 0) if rec_b else 0,
        "quotable": q.is_quotable(),
    }

    return Brief(
        event_ticker=mv.event_ticker,
        built_at=datetime.now(timezone.utc).isoformat(),
        tour=mv.tour, tier=mv.tier, series=mv.series,
        tournament=mv.tournament, round=rnd,
        surface=surface, surface_source=surface_source,
        surface_meta=surf_meta,
        player_a=name_a, player_b=name_b or "?",
        a=a, b=b, h2h=h2h, market=market, model=model,
        staleness_days=staleness, archive_last_date=arch.last_date or None,
        coverage=coverage, warnings=warnings,
    )
