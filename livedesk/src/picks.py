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

from ledger import signal_key                      # noqa: E402

TRADING_ROOT = Path(__file__).resolve().parents[2]
MLB_DB = TRADING_ROOT / "mlb-paper" / "data" / "paper.db"
MLB_SRC = TRADING_ROOT / "mlb-paper" / "src"

BOT = "starter__hold"
# The unconstrained view of the same mentality. Not capped by entries, re-run
# every tick, and the only thing that can retire a pick. See _changed_mind.
SHADOW_BOT = "starter__shadow"

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
    signal: str               # which rule fired on what state -- Guard 1

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

    # mlb amendment A3, 2026-08-12: a divergence computed on too little
    # pitching is recorded and NOT used. Say so out loud -- "the bot looked
    # and decided it could not tell" is a different thing from "the bot found
    # nothing", and only one of them is honest about a rookie.
    ignored = next((x for x in flags
                    if x.startswith("form_divergence_IGNORED")), None)
    if ignored:
        n = f.get("career_starts_prior")
        bits.append(
            f"{_poss(club)} starting pitcher looks very different lately from "
            f"his season line, but the bot IGNORED that — he has only "
            f"{n} career start(s) behind him, so there is not enough pitching "
            f"there to read anything into.")

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
# `mlb` asked for this second trigger on 2026-08-12 and it is theirs, not mine:
# "a pitcher with two starts is worth flagging even at a 6-cent gap, because
# that is where the bot is thinnest." After their amendment A3 the enormous
# gaps mostly stop appearing, so the gap alone would stop catching the thin
# cases -- which are the ones that were wrong in the first place.
THIN_PITCHER_STARTS = 3
THIN_GAP_C = 6.0


def _thin(r: dict):
    """The fewest career starts either flagged pitcher has, or None."""
    seen = []
    for side in ("away", "home"):
        f = (r.get("flags") or {}).get(side) or {}
        if not (f.get("flags") or []):
            continue
        n = f.get("career_starts_prior")
        if n is not None:
            seen.append(int(n))
    return min(seen) if seen else None


def _warning(r: dict) -> str:
    fair, price = r.get("fair_c"), r.get("price_c")
    if fair is None or price is None:
        return ""
    gap = abs(float(fair) - float(price))
    thin = _thin(r)
    thin_hit = thin is not None and thin <= THIN_PITCHER_STARTS and gap >= THIN_GAP_C
    if gap < BIG_DISAGREEMENT_C and not thin_hit:
        return ""
    extra = ""
    if thin is not None and thin <= THIN_PITCHER_STARTS:
        extra = (f" It rests on a pitcher with only {thin} career "
                 f"{'start' if thin == 1 else 'starts'} — the thinnest ground "
                 f"this bot ever stands on.")
    if gap >= BIG_DISAGREEMENT_C:
        head = (f"UNUSUAL — the bot says this should be {float(fair):.0f} "
                f"cents; the market says {int(price)}. That is the bot calling "
                f"the market badly wrong, not making a small correction.")
    else:
        head = (f"CAREFUL — the bot wants {float(fair):.0f} cents against the "
                f"market's {int(price)}.")
    return head + extra + " Be suspicious."


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


def _changed_mind(con) -> dict:
    """game_key -> when `mlb-paper` last looked at that game and decided NOT
    to trade it.

    WHY THIS EXISTS, and it is not a nicety. `starter__hold` takes at most one
    entry per game, so once it has entered, it never writes another row for
    that game -- and a stale entry would sit on the card for ever. On
    2026-08-12 that happened for real: `mlb` fixed a defect (their amendment
    A3) which cut one game's claimed value from 99 cents to 71 and dropped it
    below the cost bar, and the superseded entry was still on the card.

    The SHADOW bot is the unconstrained view. It is not capped by entries, it
    re-runs every tick, and every one of its 1,063 recorded rows says the same
    thing: the mentality looked, had a real view, and decided the trade does
    not clear its own cost bar. So a shadow row written AFTER our entry is
    `mlb-paper` saying it no longer wants that bet.

    This is still reading their published view, not recomputing it (D1).
    """
    out = {}
    for r in con.execute(
            "SELECT game_key, ts_utc, reasoning_json FROM decisions "
            "WHERE bot=? AND kind='shadow' ORDER BY ts_utc", (SHADOW_BOT,)):
        try:
            j = json.loads(r["reasoning_json"])
        except json.JSONDecodeError:
            continue
        # Only a row that actually says "no" retires anything. If a future
        # shadow row ever records a PASS, it must not be read as a refusal.
        if (j.get("detail") or {}).get("passes") is False:
            out[r["game_key"]] = (r["ts_utc"], j.get("reason") or "no longer worth it")
    return out


def pending_picks(db: Path = MLB_DB, min_hours_before: float = 0.25,
                  retired: Optional[list] = None) -> list:
    """Every starting-pitcher bet for a game that has not started yet, that
    `mlb-paper` has not since changed its mind about.

    `min_hours_before` keeps a game that is about to throw its first pitch off
    the card. This is a PRE-GAME tool; there is no speed requirement and no
    reason to be placing a bet ninety seconds before the anthem.

    `retired` collects (matchup, reason) for anything dropped, so the window
    can say "the bot has changed its mind about X" instead of a card silently
    vanishing.
    """
    out = []
    with _connect(db) as con:
        rows = con.execute(
            "SELECT * FROM decisions WHERE bot=? AND kind='entry' "
            "ORDER BY ts_utc DESC LIMIT 400", (BOT,)).fetchall()
        changed = _changed_mind(con)

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
        later = changed.get(gk)
        if later and later[0] > row["ts_utc"]:
            if retired is not None:
                retired.append((_matchup(gk), later[1]))
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
            signal=signal_key(gk, backed, r.get("flags") or {}),
        ))

    # Soonest first pitch first. Deliberately NOT ranked by how good the bot
    # says each one is: ordering by the bot's own claimed number is picking
    # the best-looking of everything on offer, which is the habit this repo
    # has retracted forty-five results over.
    out.sort(key=lambda p: p.starts_utc)
    return out
