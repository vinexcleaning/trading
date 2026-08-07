"""tennisdata.py — the fix for stale form data. Main tour only.

THE PROBLEM THIS SOLVES
    The Sackmann mirror is FROZEN. `Aneeshers/tennis-sackmann-archive` was last
    pushed 2026-06-25 and its 2026 files stop at tourney_date 20260525 (main
    tour) / 20260602 (ITF). Re-downloading is a no-op: verified 2026-08-07 by
    hashing all four 2026 files against the local cache - byte identical. The
    three upstream Sackmann repos are still 404. So "refresh from the mirror"
    cannot work, and saying so is the honest answer.

THE ONLY FREE SOURCE FOUND THAT IS ACTUALLY CURRENT
    tennis-data.co.uk publishes one spreadsheet per tour per year, updated
    weekly, with results, surface, round, rankings AND closing bookmaker odds.
    Checked 2026-08-07: ATP runs to **2026-08-03**, four days stale, against
    the mirror's seventy-four.

    robots.txt: **explicitly permitted.** "All robots will spider the domain",
    with `Disallow:` only on `/stuff/` and the 2000-2005 directories. The whole
    file was read before concluding that - GUARDS #14, the lesson being that
    `i.ytimg.com` cost a day by stopping at the first Disallow line.

WHAT IT DOES NOT FIX, AND THIS IS THE BIG CAVEAT
    **Main tour only. No Challenger, no ITF.** Those are 73% and 15% of what
    Kalshi actually lists, so this refreshes form for roughly the **13%** of the
    pool that is ATP/WTA main tour. The other 87% stays as stale as it was.
    Reporting the refresh without that number would be the more useful-sounding
    and less true thing to say.

TWO CONTENT TRAPS, BOTH REAL, BOTH GUARDED
    1. **The WTA file contains a date in 2029.** Max date reads 2029-07-20 - a
       typo in the source. Anything after today is dropped, and the count is
       reported. A naive `max(dates)` would have set "now" five years out and
       made every form window empty.
    2. **Same operator family as football-data.co.uk**, where `COL.csv` was
       byte-identical to `POL.csv` while returning HTTP 200. So the two
       workbooks are hashed and must differ, and each must carry its own tour's
       identifying column.
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from . import safety
from .sackmann import norm_name

DATA = Path(__file__).resolve().parent.parent / "data" / "tennisdata"
BASE = "http://www.tennis-data.co.uk"

# "Sinner J." -> ("Sinner", "J"). Non-greedy so multi-word surnames survive:
# "Bittoun Kouzmine C." -> ("Bittoun Kouzmine", "C").
# The trailing group allows compound initials - "Cerundolo J.M." -> ("Cerundolo",
# "J.M.") - because 111 rows were unparseable without it.
_SURNAME_FIRST = re.compile(r"^(.+?)\s+((?:[A-Z]\.?){1,3})$")


def _surname_keys(full_name: str) -> set[str]:
    """Every plausible surname spelling for one archive player.

    Three format mismatches cost 273 of 984 rows on the first run, and every one
    of them was a naming difference rather than a missing player:

      hyphens      tennis-data "Auger-Aliassime F."  vs Sackmann "Felix Auger Aliassime"
      multi-word   tennis-data "De Minaur A."        vs a last-token index holding "minaur"
      compound     tennis-data "Cerundolo J.M."      did not parse at all

    The misses were concentrated in exactly the players Kalshi lists most -
    De Minaur, Auger-Aliassime, Davidovich Fokina - so the refresh was failing
    hardest where it mattered most. Indexing every suffix of the name fixes all
    three at once.
    """
    toks = norm_name(full_name).split()
    keys: set[str] = set()
    if not toks:
        return keys
    for i in range(1, len(toks)):          # every suffix after the first token
        keys.add(" ".join(toks[i:]))
        keys.add("".join(toks[i:]))        # the de-hyphenated joined form
    keys.add(toks[-1])
    return keys

REQUIRED_COLS = {"Date", "Surface", "Round", "Winner", "Loser", "Best of",
                 "Wsets", "Lsets", "Comment", "Tournament"}


@dataclass
class RefreshResult:
    tour: str
    rows_in_file: int
    rows_after_archive: int
    rows_merged: int
    unmatched_players: int
    dropped_future_dated: int
    max_date: int | None
    file_hash: str
    notes: list[str]


def _fetch_workbook(rel: str) -> bytes | None:
    DATA.mkdir(parents=True, exist_ok=True)
    p = DATA / rel.replace("/", "__")
    text = safety.get(f"{BASE}/{rel}", expect_json=False, timeout=180,
                      as_bytes=True)
    if text is None:
        return None
    p.write_bytes(text)
    return text


def _rows(raw: bytes) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    hdr = [str(c).strip() if c is not None else "" for c in next(it)]
    out = []
    for r in it:
        if r is None or all(v is None for v in r):
            continue
        out.append(dict(zip(hdr, r)))
    return out


def _to_yyyymmdd(v: Any) -> int | None:
    if isinstance(v, datetime):
        return int(v.strftime("%Y%m%d"))
    if isinstance(v, date):
        return int(v.strftime("%Y%m%d"))
    return None


def _score_string(r: dict) -> tuple[str, int]:
    """Rebuild '6-4 3-6 7-5' from the per-set columns, winner's perspective."""
    parts = []
    for i in range(1, 6):
        w, l = r.get(f"W{i}"), r.get(f"L{i}")
        if w is None or l is None:
            continue
        try:
            parts.append(f"{int(w)}-{int(l)}")
        except (TypeError, ValueError):
            continue
    comment = str(r.get("Comment") or "").strip().lower()
    if comment.startswith("retired"):
        parts.append("RET")
    elif comment.startswith("walkover"):
        parts.append("W/O")
    try:
        bo = int(r.get("Best of") or 3)
    except (TypeError, ValueError):
        bo = 3
    return " ".join(parts), bo


_LEVEL = {"grand slam": "G", "masters 1000": "M", "masters cup": "F",
          "international gold": "A", "international": "A"}


def _level(r: dict) -> str:
    s = str(r.get("Series") or r.get("Tier") or "").strip().lower()
    return _LEVEL.get(s, "M" if "master" in s else ("G" if "grand" in s else "A"))


_SURNAME_INDEX: dict[int, dict[str, set[str]]] = {}


def _index(archive) -> dict[str, set[str]]:
    """surname-key -> {archive player keys}. Built once per archive."""
    got = _SURNAME_INDEX.get(id(archive))
    if got is not None:
        return got
    idx: dict[str, set[str]] = {}
    for k, rec in archive.players.items():
        for sk in _surname_keys(rec.name):
            idx.setdefault(sk, set()).add(k)
    _SURNAME_INDEX[id(archive)] = idx
    return idx


def resolve(name: str, archive) -> str | None:
    """'Sinner J.' -> the archive's normalised key, or None.

    Requires a UNIQUE (surname, first initial) match. An ambiguous surname
    returns None rather than a coin flip - GUARDS #22, an ambiguous join is a
    missing join. Merging the wrong player's result into a form record is
    exactly the kind of silent corruption that has no symptom.
    """
    s = str(name or "").strip()
    m = _SURNAME_FIRST.match(s)
    if not m:
        k = norm_name(s)
        return k if k in archive.players else None
    surname = norm_name(m.group(1))
    initial = m.group(2).replace(".", "").lower()[:1]
    idx = _index(archive)
    cands = idx.get(surname) or idx.get(surname.replace(" ", "")) or set()
    hits = [c for c in cands if c.split() and c.split()[0][:1] == initial]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        # Same surname AND same initial. "Nakashima B." is Brandon (450 matches,
        # main tour) and also Bryce (43, futures only).
        #
        # ONE principled tie-break, not a guess: this source publishes MAIN TOUR
        # ONLY, by construction. A candidate who has never played a main-tour
        # match cannot be the player in a main-tour row. If exactly one survives
        # that filter, it is the one. If two do, refuse - GUARDS #22, an
        # ambiguous join is a missing join.
        MAIN = {"G", "M", "A", "F"}
        on_tour = [c for c in hits
                   if any(lv in MAIN and n[1] > 0
                          for lv, n in archive.players[c].by_level.items())]
        if len(on_tour) == 1:
            return on_tour[0]
        return None
    return None


def refresh(archive, *, year: int | None = None,
            today: date | None = None) -> RefreshResult:
    """Pull the current year's results and merge anything the archive lacks.

    Only rows STRICTLY AFTER the archive's last date are merged, so this can
    never double-count a match the mirror already has.
    """
    today = today or date.today()
    year = year or today.year
    tour = archive.tour
    rel = f"{year}/{year}.xlsx" if tour == "atp" else f"{year}w/{year}.xlsx"
    notes: list[str] = []

    raw = _fetch_workbook(rel)
    if raw is None:
        return RefreshResult(tour, 0, 0, 0, 0, 0, None, "",
                             [f"{rel} did not download - archive left untouched"])
    h = hashlib.sha256(raw).hexdigest()[:12]
    rows = _rows(raw)
    if not rows:
        return RefreshResult(tour, 0, 0, 0, 0, 0, None, h,
                             [f"{rel} returned 200 but parsed to zero rows. GUARDS #13."])

    missing = REQUIRED_COLS - set(rows[0].keys())
    if missing:
        raise ValueError(f"{rel} is not a tennis-data workbook (missing {sorted(missing)}). "
                         f"GUARDS #13 - a 200 is not a correct file.")
    tour_col = "ATP" if tour == "atp" else "WTA"
    if tour_col not in rows[0]:
        raise ValueError(f"{rel} does not carry its own '{tour_col}' column - "
                         f"this may be the other tour's file. GUARDS #13.")

    cutoff = archive.last_date or 0
    today_i = int(today.strftime("%Y%m%d"))
    merged = unmatched = future = 0
    after = 0
    max_date = 0
    new_rows: list[dict] = []

    for r in rows:
        d = _to_yyyymmdd(r.get("Date"))
        if d is None:
            continue
        if d > today_i:
            future += 1          # the 2029 typo, and anything like it
            continue
        max_date = max(max_date, d)
        if d <= cutoff:
            continue
        after += 1
        wk = resolve(r.get("Winner"), archive)
        lk = resolve(r.get("Loser"), archive)
        if wk is None or lk is None:
            unmatched += 1
            continue
        score, bo = _score_string(r)
        new_rows.append({
            "tourney_date": str(d),
            "tourney_name": str(r.get("Tournament") or "").strip(),
            "surface": str(r.get("Surface") or "").strip() or "Unknown",
            "tourney_level": _level(r),
            "round": str(r.get("Round") or "").strip(),
            "winner_name": archive.players[wk].name,
            "loser_name": archive.players[lk].name,
            "score": score,
            "best_of": str(bo),
            "match_num": "0",
            "_src": f"tennis-data.co.uk/{rel}",
        })
        merged += 1

    if future:
        notes.append(f"dropped {future} row(s) dated in the future - the WTA "
                     f"workbook contains a 2029 typo and a naive max(date) would "
                     f"have emptied every form window")
    if unmatched:
        notes.append(f"{unmatched} of {after} new rows had a player this archive "
                     f"could not resolve UNIQUELY, and were skipped rather than "
                     f"guessed")
    notes.append("MAIN TOUR ONLY - no Challenger, no ITF, which are ~88% of the "
                 "Kalshi pool. Their form is unchanged and still stale.")

    if new_rows:
        archive.absorb(new_rows)

    return RefreshResult(tour, len(rows), after, merged, unmatched, future,
                         max_date or None, h, notes)
