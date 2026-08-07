"""sackmann.py — the free history layer.

SOURCES, all free, all fetch-verified 2026-08-06 (GUARDS #13/#15):

  JeffSackmann/tennis_MatchChartingProject   200, 399 stars, pushed 2026-05-25
      charting-{m,w}-points-*.csv   real point-by-point, ~13k charted matches
      charting-{m,w}-matches.csv    the index

  Aneeshers/tennis-sackmann-archive          200, mirror, pushed 2026-06-25
      atp/atp_matches_YYYY.csv             main tour 1968-2026
      atp/atp_matches_qual_chall_YYYY.csv  qualifying + Challenger
      atp/atp_matches_futures_YYYY.csv     ITF futures
      wta/wta_matches_YYYY.csv             main tour
      wta/wta_matches_qual_itf_YYYY.csv    qualifying + ITF
      {atp,wta}/*_rankings_current.csv     live-ish rankings
      slam_pointbypoint/                   slam point-by-point 2011-

  JeffSackmann/tennis_atp, tennis_wta, tennis_slam_pointbypoint   404
      Confirmed dead upstream. The mirror above is what replaces them.

RECENCY IS THE BINDING CONSTRAINT AND IT MUST BE STATED EVERY TIME
    The mirror's last ATP main-tour row is tourney_date 20260525. As of
    2026-08-06 that makes "recent form" about ten weeks stale, and it gets one
    day staler per day of the forward test. Anything the brief calls "form" is
    form as of late May, not as of yesterday. `Brief.staleness_days` carries
    the number so a bot can reason about it and the analysis can condition on
    it. This is a limitation of free data, not a bug, and pretending otherwise
    is how a study reports a null it never had the power to find.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from . import safety

DATA = Path(__file__).resolve().parent.parent / "data" / "sackmann"
MIRROR = "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main"
MCP = "https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master"

# How far back to load. Ten years is enough for a career record that means
# something and small enough to load in seconds.
DEFAULT_FROM_YEAR = 2015


# --------------------------------------------------------------------------
# Name normalisation — the accent problem, already solved once in this repo
# --------------------------------------------------------------------------

_LETTER_FOLD = str.maketrans({
    "đ": "dj", "ð": "d", "ł": "l", "ø": "o", "ß": "ss",
    "æ": "ae", "œ": "oe", "þ": "th", "ħ": "h", "ı": "i",
})


def norm_name(s: str) -> str:
    """Lowercase, fold accents, drop punctuation. 'Aleksandar Vukić' == 'Vukic'.

    NFKD cannot decompose stroked letters, hence the explicit table. Tennis is
    full of them and without this the player is simply invisible.
    """
    folded = unicodedata.normalize("NFKD", str(s).lower().translate(_LETTER_FOLD))
    return " ".join(
        "".join(ch for ch in tok if ch.isalnum() and not unicodedata.combining(ch))
        for tok in folded.split()
    ).strip()


def surname_of(full: str) -> str:
    toks = norm_name(full).split()
    return toks[-1] if toks else ""


# --------------------------------------------------------------------------
# Fetch + cache
# --------------------------------------------------------------------------

def _cache_path(rel: str) -> Path:
    return DATA / rel.replace("/", "__")


def fetch_csv(base: str, rel: str, *, refresh: bool = False) -> list[dict] | None:
    """Download and cache one CSV. Returns None if the file does not exist.

    GUARDS #13 — the caller must assert on CONTENT. `load_matches` below
    asserts the header carries the columns it is about to read, so a 200
    serving the wrong file (football-data.co.uk's COL.csv == POL.csv) cannot
    pass silently.
    """
    p = _cache_path(rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    if refresh or not p.exists() or p.stat().st_size == 0:
        text = safety.get(f"{base}/{rel}", expect_json=False, timeout=120)
        if text is None:
            return None
        p.write_text(text, encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"))))
    return rows


MATCH_COLUMNS = {
    "tourney_date", "surface", "winner_name", "loser_name", "score",
    "round", "tourney_level", "tourney_name",
}


def load_matches(tour: str, from_year: int = DEFAULT_FROM_YEAR,
                 to_year: int | None = None, *, refresh: bool = False,
                 verbose: bool = False) -> list[dict]:
    """Every singles match for one tour across the year range, all tiers."""
    to_year = to_year or date.today().year
    if tour == "atp":
        patterns = ["atp/atp_matches_{y}.csv",
                    "atp/atp_matches_qual_chall_{y}.csv",
                    "atp/atp_matches_futures_{y}.csv"]
    else:
        patterns = ["wta/wta_matches_{y}.csv",
                    "wta/wta_matches_qual_itf_{y}.csv"]
    out: list[dict] = []
    for y in range(from_year, to_year + 1):
        for pat in patterns:
            rel = pat.format(y=y)
            rows = fetch_csv(MIRROR, rel, refresh=refresh)
            if not rows:
                continue
            missing = MATCH_COLUMNS - set(rows[0].keys())
            if missing:
                raise ValueError(
                    f"{rel} returned 200 but is not a Sackmann match file "
                    f"(missing {sorted(missing)}). GUARDS #13."
                )
            for r in rows:
                r["_src"] = rel
            out.extend(rows)
            if verbose:
                print(f"  {rel:44s} {len(rows):6d} rows")
    return out


# --------------------------------------------------------------------------
# Score parsing — where the deciding-set and tiebreak facts come from
# --------------------------------------------------------------------------

_SET = re.compile(r"^(\d+)-(\d+)(?:\((\d+)\))?$")


@dataclass
class ParsedScore:
    sets: list[tuple[int, int]]          # (winner games, loser games)
    tiebreaks: int
    completed: bool
    retired: bool
    walkover: bool
    went_deciding: bool                  # 3rd set in bo3, 5th in bo5
    best_of: int

    @property
    def straight(self) -> bool:
        return self.completed and not self.went_deciding


def parse_score(score: str, best_of: int = 3) -> ParsedScore:
    s = (score or "").strip()
    retired = bool(re.search(r"\bRET\b", s, re.I))
    walkover = bool(re.search(r"\bW/?O\b|walkover|DEF", s, re.I))
    sets: list[tuple[int, int]] = []
    tb = 0
    for tok in re.sub(r"\bRET\b|\bW/?O\b|\bDEF\b", "", s, flags=re.I).split():
        m = _SET.match(tok)
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        sets.append((a, b))
        if m.group(3) is not None or {a, b} == {7, 6}:
            tb += 1
    need = 3 if best_of == 5 else 2
    completed = (not retired and not walkover
                 and sum(1 for a, b in sets if a > b) >= need)
    went = completed and len(sets) == (2 * need - 1)
    return ParsedScore(sets, tb, completed, retired, walkover, went, best_of)


# --------------------------------------------------------------------------
# The player index
# --------------------------------------------------------------------------

@dataclass
class PlayerRecord:
    """Everything the archive knows about one player, already aggregated.

    Every counter is a plain integer so the brief can print the denominator
    next to the rate. A rate without its n is not a fact — CLAUDE.md §6.
    """
    name: str
    matches: int = 0
    wins: int = 0
    by_surface: dict[str, list[int]] = field(default_factory=lambda: defaultdict(lambda: [0, 0]))
    by_level: dict[str, list[int]] = field(default_factory=lambda: defaultdict(lambda: [0, 0]))
    by_round: dict[str, list[int]] = field(default_factory=lambda: defaultdict(lambda: [0, 0]))
    deciding_played: int = 0
    deciding_won: int = 0
    straight_wins: int = 0
    tiebreaks_played: int = 0
    tiebreaks_in_wins: int = 0
    retired_own: int = 0            # this player retired mid-match
    opp_retired: int = 0
    # serve/return aggregates
    svpt: int = 0
    first_in: int = 0
    first_won: int = 0
    second_won: int = 0
    sv_gms: int = 0
    bp_saved: int = 0
    bp_faced: int = 0
    aces: int = 0
    dfs: int = 0
    ret_bp_won: int = 0             # break points converted (opponent's bp_faced - bp_saved)
    ret_bp_chances: int = 0
    stat_matches: int = 0           # matches where serve stats were present
    minutes: int = 0
    minutes_matches: int = 0
    results: list[tuple[int, int, str, str]] = field(default_factory=list)
    # (tourney_date, won, surface, level) newest last
    elo: float = 1500.0
    elo_surface: dict[str, float] = field(default_factory=dict)
    elo_matches: int = 0
    rank: int | None = None
    rank_points: int | None = None
    hand: str | None = None
    height: int | None = None
    ioc: str | None = None
    age: float | None = None

    def rate(self, w: int, n: int) -> float | None:
        return (w / n) if n else None


def _i(v: Any) -> int | None:
    try:
        f = float(v)
        return int(f) if not math.isnan(f) else None
    except (TypeError, ValueError):
        return None


_ELO_K_BASE = 250.0
_ELO_K_OFF = 5.0
_ELO_K_SHAPE = 0.4


def _elo_k(n: int) -> float:
    """FiveThirtyEight-style decaying K. Not tuned, not fitted to anything."""
    return _ELO_K_BASE / ((n + _ELO_K_OFF) ** _ELO_K_SHAPE)


class Archive:
    """The whole free history, indexed by normalised player name."""

    def __init__(self, tour: str, from_year: int = DEFAULT_FROM_YEAR,
                 *, refresh: bool = False, verbose: bool = False):
        self.tour = tour
        self.players: dict[str, PlayerRecord] = {}
        self.h2h: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
        self.h2h_detail: dict[tuple[str, str], list[dict]] = defaultdict(list)
        self.by_surname: dict[str, set[str]] = defaultdict(set)
        self.last_date: int = 0
        self._build(load_matches(tour, from_year, refresh=refresh, verbose=verbose))
        self._load_rankings(refresh=refresh)

    # -- construction ------------------------------------------------------

    def _rec(self, name: str) -> PlayerRecord:
        k = norm_name(name)
        r = self.players.get(k)
        if r is None:
            r = PlayerRecord(name=name)
            self.players[k] = r
            self.by_surname[surname_of(name)].add(k)
        return r

    def _build(self, rows: list[dict]) -> None:
        rows.sort(key=lambda r: (_i(r.get("tourney_date")) or 0,
                                _i(r.get("match_num")) or 0))
        for r in rows:
            wn, ln = (r.get("winner_name") or "").strip(), (r.get("loser_name") or "").strip()
            if not wn or not ln:
                continue
            d = _i(r.get("tourney_date")) or 0
            self.last_date = max(self.last_date, d)
            surf = (r.get("surface") or "").strip() or "Unknown"
            lvl = (r.get("tourney_level") or "").strip() or "?"
            rnd = (r.get("round") or "").strip() or "?"
            bo = _i(r.get("best_of")) or 3
            ps = parse_score(r.get("score", ""), bo)

            W, L = self._rec(wn), self._rec(ln)
            for rec, won in ((W, 1), (L, 0)):
                rec.matches += 1
                rec.wins += won
                rec.by_surface[surf][0] += won
                rec.by_surface[surf][1] += 1
                rec.by_level[lvl][0] += won
                rec.by_level[lvl][1] += 1
                rec.by_round[rnd][0] += won
                rec.by_round[rnd][1] += 1
                rec.results.append((d, won, surf, lvl))
                if ps.went_deciding:
                    rec.deciding_played += 1
                    rec.deciding_won += won
                rec.tiebreaks_played += ps.tiebreaks
            if ps.straight:
                W.straight_wins += 1
            if ps.tiebreaks and ps.completed:
                W.tiebreaks_in_wins += ps.tiebreaks
            if ps.retired:
                L.retired_own += 1
                W.opp_retired += 1

            # serve/return stats, present on a minority of lower-tier rows
            w_svpt, l_svpt = _i(r.get("w_svpt")), _i(r.get("l_svpt"))
            if w_svpt and l_svpt:
                for rec, pre, opp in ((W, "w", "l"), (L, "l", "w")):
                    rec.stat_matches += 1
                    rec.svpt += _i(r.get(f"{pre}_svpt")) or 0
                    rec.first_in += _i(r.get(f"{pre}_1stIn")) or 0
                    rec.first_won += _i(r.get(f"{pre}_1stWon")) or 0
                    rec.second_won += _i(r.get(f"{pre}_2ndWon")) or 0
                    rec.sv_gms += _i(r.get(f"{pre}_SvGms")) or 0
                    rec.bp_saved += _i(r.get(f"{pre}_bpSaved")) or 0
                    rec.bp_faced += _i(r.get(f"{pre}_bpFaced")) or 0
                    rec.aces += _i(r.get(f"{pre}_ace")) or 0
                    rec.dfs += _i(r.get(f"{pre}_df")) or 0
                    ofaced = _i(r.get(f"{opp}_bpFaced")) or 0
                    osaved = _i(r.get(f"{opp}_bpSaved")) or 0
                    rec.ret_bp_chances += ofaced
                    rec.ret_bp_won += max(0, ofaced - osaved)
            mins = _i(r.get("minutes"))
            if mins:
                for rec in (W, L):
                    rec.minutes += mins
                    rec.minutes_matches += 1

            kw, kl = norm_name(wn), norm_name(ln)
            key = (kw, kl) if kw < kl else (kl, kw)
            self.h2h[key][0 if key[0] == kw else 1] += 1
            self.h2h_detail[key].append(
                {"date": d, "winner": kw, "surface": surf, "level": lvl,
                 "round": rnd, "score": r.get("score", "")}
            )

            self._update_elo(W, L, surf)

    def _update_elo(self, W: PlayerRecord, L: PlayerRecord, surf: str) -> None:
        ew = 1.0 / (1.0 + 10 ** ((L.elo - W.elo) / 400.0))
        kw, kl = _elo_k(W.elo_matches), _elo_k(L.elo_matches)
        W.elo += kw * (1.0 - ew)
        L.elo -= kl * (1.0 - ew)
        W.elo_matches += 1
        L.elo_matches += 1
        if surf and surf != "Unknown":
            sw = W.elo_surface.get(surf, 1500.0)
            sl = L.elo_surface.get(surf, 1500.0)
            e = 1.0 / (1.0 + 10 ** ((sl - sw) / 400.0))
            W.elo_surface[surf] = sw + 40.0 * (1.0 - e)
            L.elo_surface[surf] = sl - 40.0 * (1.0 - e)

    def _load_rankings(self, *, refresh: bool = False) -> None:
        rel = f"{self.tour}/{self.tour}_rankings_current.csv"
        rows = fetch_csv(MIRROR, rel, refresh=refresh)
        prel = f"{self.tour}/{self.tour}_players.csv"
        prows = fetch_csv(MIRROR, prel, refresh=refresh) or []
        if not rows:
            return
        by_id = {}
        for p in prows:
            pid = (p.get("player_id") or "").strip()
            first = (p.get("name_first") or "").strip()
            last = (p.get("name_last") or "").strip()
            if pid and (first or last):
                by_id[pid] = (f"{first} {last}".strip(),
                              (p.get("hand") or "").strip() or None,
                              _i(p.get("height")),
                              (p.get("ioc") or "").strip() or None)
        for r in rows:
            pid = (r.get("player") or "").strip()
            info = by_id.get(pid)
            if not info:
                continue
            k = norm_name(info[0])
            rec = self.players.get(k)
            if rec is None:
                continue
            rec.rank = _i(r.get("rank"))
            rec.rank_points = _i(r.get("points"))
            rec.hand, rec.height, rec.ioc = info[1], info[2], info[3]

    def absorb(self, rows: list[dict]) -> None:
        """Fold additional matches into an already-built archive.

        Used by tennisdata.py to bring main-tour form up to date. It runs the
        SAME `_build` path, so elo, form, deciding-set and H2H all update by the
        one code path rather than a parallel one that could drift from it.
        """
        if not rows:
            return
        self._build(rows)

    # -- lookup ------------------------------------------------------------

    def find(self, full_name: str, surname_hint: str | None = None) -> PlayerRecord | None:
        """Resolve a Kalshi player string to an archive record.

        GUARDS #22 in miniature. Exact normalised match first. Then surname,
        but only when the surname is long enough to mean something and resolves
        to exactly one player. A surname that maps to several people returns
        None rather than a coin flip: an ambiguous join is a missing join.
        """
        k = norm_name(full_name)
        if k in self.players:
            return self.players[k]
        sn = surname_of(full_name) or norm_name(surname_hint or "")
        if len(sn) < 4:
            return None
        cands = self.by_surname.get(sn) or set()
        if len(cands) == 1:
            return self.players[next(iter(cands))]
        if len(cands) > 1:
            first = k.split()[0] if k.split() else ""
            hits = [c for c in cands if c.split() and c.split()[0] == first]
            if len(hits) == 1:
                return self.players[hits[0]]
            initial = first[:1]
            hits = [c for c in cands if c.split() and c.split()[0][:1] == initial]
            if len(hits) == 1:
                return self.players[hits[0]]
        return None

    def head_to_head(self, a: str, b: str) -> dict[str, Any]:
        ka, kb = norm_name(a), norm_name(b)
        key = (ka, kb) if ka < kb else (kb, ka)
        w = self.h2h.get(key)
        if not w:
            return {"n": 0, "a_wins": 0, "b_wins": 0, "meetings": []}
        a_w = w[0] if key[0] == ka else w[1]
        b_w = w[1] if key[0] == ka else w[0]
        det = sorted(self.h2h_detail.get(key, []), key=lambda d: d["date"])[-6:]
        return {"n": a_w + b_w, "a_wins": a_w, "b_wins": b_w, "meetings": det}


# --------------------------------------------------------------------------
# Surface, derived from the archive rather than from a hand-written table
# --------------------------------------------------------------------------

_LEVEL_PREFIX = re.compile(r"^\s*[MW]\d{2,3}\s+", re.I)
_TRAILING_STATE = re.compile(r"\s+[A-Z]{2}$")


def venue_key(tourney_name: str) -> str:
    """'M25 Kursumlijska Banja' and 'M15 Kursumlijska Banja' -> the same venue.

    The prize-money prefix says how big the event is, not what it is played on.
    The venue does. A US state suffix ('Southaven MS') is also dropped, because
    Kalshi writes it and Sackmann usually does not.
    """
    s = _LEVEL_PREFIX.sub("", str(tourney_name or "").strip())
    s = _TRAILING_STATE.sub("", s)
    return norm_name(s)


# A venue that has genuinely hosted two surfaces must resolve to None, not to
# the more common one. Guessing a surface is worse than admitting it is unknown:
# the brief is read by bots that can reason about a null and cannot reason about
# a plausible wrong answer.
SURFACE_MIN_AGREEMENT = 0.80
SURFACE_MIN_N = 2


class SurfaceIndex:
    """venue -> (surface, agreement, n), built from every match in the archive."""

    def __init__(self, archives: list["Archive"], rows_by_tour: dict[str, list[dict]]):
        counts: dict[str, Counter] = defaultdict(Counter)
        for rows in rows_by_tour.values():
            for r in rows:
                surf = (r.get("surface") or "").strip()
                if not surf or surf == "Unknown":
                    continue
                k = venue_key(r.get("tourney_name", ""))
                if k:
                    counts[k][surf] += 1
        self.index: dict[str, tuple[str, float, int]] = {}
        for k, c in counts.items():
            n = sum(c.values())
            surf, top = c.most_common(1)[0]
            agree = top / n
            self.index[k] = (surf, agree, n)

    def lookup(self, tournament: str | None) -> tuple[str | None, dict]:
        if not tournament:
            return None, {"reason": "no tournament name in the rules text"}
        k = venue_key(tournament)
        hit = self.index.get(k)
        if hit is None:
            return None, {"reason": "venue not in the archive", "venue_key": k}
        surf, agree, n = hit
        meta = {"venue_key": k, "agreement": round(agree, 3), "n_past_events": n,
                "source": "derived from the free archive's own tourney_name -> surface"}
        if n < SURFACE_MIN_N:
            return None, {**meta, "reason": f"only {n} past event(s) at this venue"}
        if agree < SURFACE_MIN_AGREEMENT:
            return None, {**meta,
                          "reason": f"this venue has hosted more than one surface "
                                    f"({agree:.0%} agreement) - NOT guessed"}
        return surf, meta


_SURFACE_INDEX: SurfaceIndex | None = None


def get_surface_index(from_year: int = DEFAULT_FROM_YEAR) -> SurfaceIndex:
    global _SURFACE_INDEX
    if _SURFACE_INDEX is None:
        rows = {t: load_matches(t, from_year) for t in ("atp", "wta")}
        _SURFACE_INDEX = SurfaceIndex([], rows)
    return _SURFACE_INDEX


_CACHE: dict[str, Archive] = {}


def get_archive(tour: str, **kw) -> Archive:
    if tour not in _CACHE:
        _CACHE[tour] = Archive(tour, **kw)
    return _CACHE[tour]
