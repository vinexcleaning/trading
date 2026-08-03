"""
autoscan.py — finds tradeable matches by itself.

Cross-references every open Kalshi tennis market against every live match
on the Apify feed, matching them up by player name. Whatever lines up gets
scored by tennis_engine and ranked, so the app can show "here are the best
trades right now" without you picking anything from a list.

Kalshi titles look like:
    "Will Alan Magadan win the Hernandez vs Magadan: Qualification match?"
Apify gives us homePlayerName / awayPlayerName. We pull the subject player
out of the Kalshi title and match on surname.

This module only reads and ranks. It never places an order.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from kalshi_client import Market
from sofascore_feed import SofaScoreClient as LiveScoreClient, LiveScore
from tennis_engine import Config, Decision, Snapshot, evaluate


# Letters NFKD cannot decompose because they are distinct letters rather than
# an accented base: stroked d/l/o, and the ligatures. Without these, "Đoković"
# never matches Kalshi's "Djokovic".
_LETTER_FOLD = str.maketrans({
    "đ": "dj", "ð": "d", "ł": "l", "ø": "o", "ß": "ss",
    "æ": "ae", "œ": "oe", "þ": "th", "ħ": "h", "ı": "i",
})


def other_side(side: str) -> str:
    return "away" if side == "home" else "home"


def _norm(s: str) -> str:
    """Lowercase, strip punctuation AND strip accents.

    Stripping accents is not cosmetic — it is the difference between seeing a
    market and not seeing it. Sofascore writes "Aleksandar Vukić"; Kalshi
    writes "Aleksandar Vukic". Without this fold those are different strings,
    the market never matches, and the player is invisible to the bot.
    Tennis is full of them: Čilić, Świątek, Đoković, Muñar, Tsitsipás.
    """
    folded = unicodedata.normalize("NFKD", str(s).lower().translate(_LETTER_FOLD))
    return "".join(ch for ch in folded
                   if ch.isalnum() and not unicodedata.combining(ch))


def subject_player(title: str) -> str:
    """The player a Kalshi market is asking about — the name between
    'Will' and 'win'. Returns '' if the title isn't that shape."""
    m = re.match(r"\s*will\s+(.+?)\s+win\b", title, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _name_matches(kalshi_name: str, feed_name: str) -> bool:
    """True if these are plausibly the same person. Compares surnames
    (last token) and requires the rest to not contradict — 'Alan Magadan'
    matches 'Magadan' and 'A. Magadan' but not 'Luis Magadan-Reyes'."""
    k_parts = [_norm(p) for p in kalshi_name.split() if _norm(p)]
    f_parts = [_norm(p) for p in feed_name.split() if _norm(p)]
    if not k_parts or not f_parts:
        return False
    if k_parts[-1] != f_parts[-1]:
        return False
    # surname agrees; if both have a first name, it must agree too (allowing initials)
    if len(k_parts) > 1 and len(f_parts) > 1:
        k_first, f_first = k_parts[0], f_parts[0]
        if not (k_first == f_first or k_first.startswith(f_first) or f_first.startswith(k_first)):
            return False
    return True


@dataclass
class Rejected:
    """A match that lined up but didn't pass the rules — kept so the app can
    tell you WHY nothing qualified instead of leaving you guessing."""
    player: str
    ask: int
    sets: str
    reasons: list[str]


@dataclass
class Candidate:
    market: Market
    score: LiveScore
    decision: Decision
    player: str

    @property
    def ticker(self) -> str:
        return self.market.ticker

    @property
    def edge(self) -> float:
        """How much better than a coin flip this trade needs to be, inverted
        into a rough 'how much room' number for ranking. Lower breakeven =
        better trade, so we rank by (100 - breakeven)."""
        return 100.0 - self.decision.breakeven_with_exit


def find_candidates(cfg: Config, markets: list[Market], live: LiveScoreClient,
                    open_positions: int = 0,
                    max_matches: int = 60,
                    client=None,
                    reentry_tickers: Optional[set] = None,
                    daily_pnl_pct: float = 0.0,
                    reentry_info: Optional[dict] = None
                    ) -> tuple[list[Candidate], list[str], list[Rejected]]:
    """Match live Kalshi markets to live feed matches, evaluate each, and
    return (qualifying candidates ranked best-first, status notes, rejected
    matches with their reasons). Never places anything.

    `client` is an optional KalshiClient used only to look up each market's
    opening price, which is how we now decide who the pre-match favourite
    was. Without it every market is treated as a divergence setup."""
    notes: list[str] = []
    rejected: list[Rejected] = []
    if not live.enabled:
        return [], ["live feed unavailable"], []

    try:
        feed = live.raw(max_matches=max_matches, force=False)
    except Exception as e:
        return [], [f"couldn't reach live feed: {e}"], []

    if not feed:
        return [], ["no matches are live on the feed right now"], []

    singles = [f for f in feed if f.get("matchType", "singles") == "singles"]
    out: list[Candidate] = []
    matched_tickers = 0

    for m in markets:
        if not m.is_trading:
            continue
        subject = subject_player(m.title)
        if not subject:
            continue

        pair = None
        for f in singles:
            home, away = f.get("homePlayerName", ""), f.get("awayPlayerName", "")
            if _name_matches(subject, home):
                pair, side = f, "home"
                break
            if _name_matches(subject, away):
                pair, side = f, "away"
                break
        if pair is None:
            continue
        matched_tickers += 1

        score = live.score_from_item(pair, side)
        if score is None:
            continue

        # Who was the pre-match favourite? The old Apify feed answered this
        # from bookmaker odds. Sofascore's live endpoint has none, so ask
        # Kalshi: a market that opened above 50c opened this player favourite.
        # If the lookup fails we fall back to False, which routes the trade
        # down the divergence path — the stricter of the two, so a failed
        # lookup can never loosen a gate.
        was_fav = False
        op = None
        if client is not None:
            op = client.opening_price(m.ticker)
            if op is not None:
                # Between the two thresholds there was no clear favourite, so
                # leave was_fav False and let it take the stricter path.
                was_fav = op >= cfg.favorite_threshold

        # Completed sets only, from this player's point of view. The set in
        # progress is excluded — its games say nothing about a set won.
        set_scores = []
        allg = pair.get("games") or {}
        last = str(pair.get("lastPeriod") or "")
        for i in range(1, 6):
            g = allg.get(f"set{i}")
            if not g:
                continue
            if f"period{i}" == last and (pair.get("statusType") == "inprogress"):
                continue                       # still being played
            mine, theirs = g.get(side, 0), g.get(other_side(side), 0)
            set_scores.append((int(mine or 0), int(theirs or 0)))

        # Feeds the re-entry cooldown and per-event re-entry cap added 3 Aug.
        # `reentry_info` maps ticker -> {"ago_sec": int, "reentries": int}.
        # A ticker that isn't in it has never stopped us out, which is the
        # old behaviour exactly.
        info = (reentry_info or {}).get(m.ticker) or {}

        snap = Snapshot(
            player=subject, match=score.match_title,
            ask=m.yes_ask, bid=m.yes_bid,
            sets_won=score.sets_won, sets_lost=score.sets_lost,
            was_prematch_favorite=was_fav,
            set_scores=set_scores, open_price=op,
            score_age_sec=score.age_sec,
            market_open=m.is_open,
            open_positions=open_positions,
            is_reentry=bool(reentry_tickers and m.ticker in reentry_tickers),
            daily_pnl_pct=daily_pnl_pct,
            stopped_out_ago_sec=info.get("ago_sec"),
            reentries_so_far=info.get("reentries", 0),
        )
        d = evaluate(cfg, snap)
        if d.take:
            out.append(Candidate(market=m, score=score, decision=d, player=subject))
        else:
            rejected.append(Rejected(
                player=subject, ask=m.yes_ask,
                sets=f"{score.sets_won}-{score.sets_lost}",
                reasons=[t for k, t in d.reasons if k == "bad"]))

    notes.append(f"{len(markets)} Kalshi markets, {len(singles)} live on feed, "
                 f"{matched_tickers} matched up, {len(out)} qualify")
    out.sort(key=lambda c: c.edge, reverse=True)
    rejected.sort(key=lambda r: len(r.reasons))
    return out, notes, rejected
