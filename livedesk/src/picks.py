"""Where the bets come from, and the plain-English reason for each one.

THE PICKS ARE NOT MADE HERE. They are made by `mlb-paper`, which owns the
starting-pitcher strategy. This module opens that project's `paper.db`
**read-only** and reads the decisions its runner has already written.

That is deliberate and it is the single most important design choice in this
folder: a second copy of the strategy that drifts from the first is worse than
no tool at all. Nothing here scores a game, adjusts a price, or decides
anything. If a pick is wrong, it is wrong in `mlb-paper` and that is where it
gets fixed.

WHICH BOT. `starter__hold` -- the one that takes at most ONE position per game
and never exits early. `starter__free` takes two entries on the same game,
which is the exact thing Guard 1 exists to prevent, and `starter__exit-once`
is the same bot as `hold` under another name (its exit rule has fired zero
times in 303 positions, measured by the mlb chat on 2026-08-08).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

TRADING_ROOT = Path(__file__).resolve().parents[2]
MLB_DB = TRADING_ROOT / "mlb-paper" / "data" / "paper.db"
MLB_SRC = TRADING_ROOT / "mlb-paper" / "src"

BOT = "starter__hold"

# The 30-club code map belongs to mlb-paper and is imported rather than
# retyped -- a second copy of it is how the Athletics broke a name join once.
try:
    sys.path.insert(0, str(MLB_SRC))
    from kalshi import CODE as CLUB          # noqa: E402
except Exception:                            # pragma: no cover - fallback only
    CLUB = {}


@dataclass
class Pick:
    game_key: str
    ticker: str
    event_ticker: str
    team: str                 # the club being backed, full name
    matchup: str              # "Pittsburgh Pirates at Miami Marlins"
    side: str
    quoted_price_c: int       # what the bot saw when it decided
    starts_utc: str
    decided_utc: str
    window: str
    fair_c: float             # what the bot thinks it is worth
    why: list                 # plain-English lines
    warning: str              # '' or a sentence he must read

    @property
    def starts_local(self) -> datetime:
        return _parse(self.starts_utc).astimezone()

    @property
    def hours_away(self) -> float:
        return (_parse(self.starts_utc) - datetime.now(timezone.utc)).total_seconds() / 3600.0


def _parse(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _club(code: str) -> str:
    return CLUB.get(code, code)


def _matchup(game_key: str) -> str:
    """'2026-08-12:PIT@MIA' -> 'Pittsburgh Pirates at Miami Marlins'."""
    try:
        away, home = game_key.split(":", 1)[1].split("@", 1)
        return f"{_club(away)} at {_club(home)}"
    except (ValueError, IndexError):
        return game_key


def _event_ticker(ticker: str) -> str:
    """'KXMLBGAME-26AUG121840PITMIA-MIA' -> 'KXMLBGAME-26AUG121840PITMIA'."""
    return ticker.rsplit("-", 1)[0] if ticker.count("-") >= 2 else ticker


# ------------------------------------------------------------------ the why
# No statistics words anywhere in this window. "Earned runs per 9 innings" is
# baseball, which he knows; "divergence", "adjustment" and "edge" are not, and
# do not appear on the card.

def _poss(club: str) -> str:
    """Baltimore Orioles -> Baltimore Orioles'. Boston Red Sox -> Red Sox'.
    Club names ending in s do not take another one, and he reads this at 3am."""
    return club + ("'" if club.endswith("s") else "'s")


def _side_sentence(club: str, f: dict) -> Optional[str]:
    flags = f.get("flags") or []
    if not flags:
        return None
    bits = []
    d = f.get("divergence_er9")
    if "form_divergence" in flags and d is not None:
        recent, season = f.get("recent_era"), f.get("season_era")
        better = d < 0
        bits.append(
            f"{_poss(club)} starting pitcher has been "
            f"{'much better' if better else 'much worse'} in his last few "
            f"outings than he has been all season — "
            f"{recent} earned runs per 9 innings lately against {season} "
            f"across the whole year.")
    if "debut_or_near" in flags:
        n = f.get("career_starts_prior") or 0
        bits.append(
            f"{_poss(club)} starting pitcher has started only {n} big-league "
            f"{'game' if n == 1 else 'games'} in his career, so there is very "
            f"little to go on.")
    if "short_rest" in flags:
        bits.append(
            f"{_poss(club)} starting pitcher is going on "
            f"{f.get('rest_days')} days' rest.")
    return " ".join(bits)


def _why(r: dict, backed: str, away_club: str, home_club: str) -> list:
    lines = []
    flags = r.get("flags") or {}
    for side, club in (("away", away_club), ("home", home_club)):
        s = _side_sentence(club, flags.get(side) or {})
        if s:
            lines.append(s)
    if not lines:
        lines.append("the bot flagged something about the pitchers.")
    # One short line, not a paragraph. It is the same on every card, so every
    # extra line it takes is a line stolen from the reason that differs.
    lines.append("Season records are ignored on purpose — the price already "
                 f"has those. So it backs {backed}.")
    return lines


# The bot is allowed to disagree with the market. It is not normally allowed
# to disagree with it by THIRTY cents. When it does, that is almost always one
# pitcher with a tiny record being treated as if his one bad outing were a
# whole season, and he should see that before clicking, not after.
BIG_DISAGREEMENT_C = 12.0


def _warning(r: dict) -> str:
    fair = r.get("fair_c")
    price = r.get("price_c")
    if fair is None or price is None:
        return ""
    gap = abs(float(fair) - float(price))
    if gap < BIG_DISAGREEMENT_C:
        return ""
    thin = []
    for side in ("away", "home"):
        f = (r.get("flags") or {}).get(side) or {}
        n = f.get("career_starts_prior")
        if n is not None and n <= 3:
            thin.append(int(n))
    extra = ""
    if thin:
        n = min(thin)
        extra = (f" It leans on a pitcher with only {n} career "
                 f"{'start' if n == 1 else 'starts'}, so his 'recent form' is "
                 f"one or two games.")
    return (f"UNUSUAL — the bot says this should be {float(fair):.0f} cents; "
            f"the market says {int(price)}. That is the bot calling the market "
            f"badly wrong, not making a small correction." + extra
            + " Be suspicious.")


# ---------------------------------------------------------------- the read

def _connect(db: Path = MLB_DB) -> sqlite3.Connection:
    """Read-only, and it says so in the connection string. mlb-paper's runner
    is writing to this file every 300 seconds while we read it."""
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True, timeout=20)
    con.row_factory = sqlite3.Row
    return con


def source_age_minutes(db: Path = MLB_DB) -> Optional[float]:
    """How long since mlb-paper last did anything. If this stops moving, the
    picks are stale and the window must say so rather than showing yesterday's
    game as if it were live."""
    try:
        with _connect(db) as con:
            row = con.execute("SELECT MAX(ts_utc) t FROM ticks").fetchone()
        if not row or not row["t"]:
            return None
        return (datetime.now(timezone.utc) - _parse(row["t"])).total_seconds() / 60.0
    except sqlite3.Error:
        return None


def pending_picks(db: Path = MLB_DB, min_hours_before: float = 0.25) -> list:
    """Every starting-pitcher bet for a game that has not started yet.

    `min_hours_before` keeps a game that is about to throw its first pitch off
    the card. This is a PRE-GAME tool; there is no speed requirement and no
    reason to be placing a bet ninety seconds before the anthem.
    """
    out = []
    with _connect(db) as con:
        rows = con.execute(
            "SELECT * FROM decisions WHERE bot=? AND kind='entry' "
            "ORDER BY ts_utc DESC LIMIT 400", (BOT,)).fetchall()

    seen = set()
    now = datetime.now(timezone.utc)
    for row in rows:
        gk = row["game_key"]
        if gk in seen:
            continue                      # keep only the newest per game
        seen.add(gk)
        hours = (_parse(row["starts_utc"]) - now).total_seconds() / 3600.0
        if hours < min_hours_before:
            continue
        try:
            j = json.loads(row["reasoning_json"])
        except json.JSONDecodeError:
            continue
        r = j.get("reasoning") or {}
        backed = r.get("backed") or ""
        try:
            away_code, home_code = gk.split(":", 1)[1].split("@", 1)
        except (ValueError, IndexError):
            away_code = home_code = ""
        out.append(Pick(
            game_key=gk,
            ticker=row["ticker"],
            event_ticker=_event_ticker(row["ticker"]),
            team=backed,
            matchup=_matchup(gk),
            side=row["side"] or "YES",
            quoted_price_c=int(row["quoted_price_c"] or 0),
            starts_utc=row["starts_utc"],
            decided_utc=row["ts_utc"],
            window=row["window"],
            fair_c=float(r.get("fair_c") or 0.0),
            why=_why(r, backed, _club(away_code), _club(home_code)),
            warning=_warning(r),
        ))

    # Soonest first pitch first. Deliberately NOT ranked by how good the bot
    # says each one is: ordering by the bot's own claimed number is picking
    # the best-looking of everything on offer, which is the habit this repo
    # has retracted forty-five results over.
    out.sort(key=lambda p: p.starts_utc)
    return out
