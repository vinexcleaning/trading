"""The record of every bet this window proposed and he confirmed.

This file is the only thing that knows what the strategy has actually done
with his money, and it is what both surviving guards read:

  Guard 1  ONE BET PER GAME, EVER. Once a game_key is in here, that game is
           never offered again -- not this session, not after a restart.
           His own words about the tennis app: "it would keep repeating bets,
           so it would make me bet a lot on the same games, which actually
           worked out in our favour with the wins, but then it would also work
           against us in the losses."

  Guard 2  STOP EVERYTHING at -$33 on THIS LEDGER, not on the account
           balance. He spotted the hole himself: "there might be a chance it
           dips to fifty because I'm the reason it dipped to fifty, and it had
           nothing to do with baseball."

It is a plain JSON file so he can open it, read it, and correct it with
Notepad if this window ever gets something wrong. It lives under `data/`,
which is gitignored repo-wide -- his money records do not go on the internet.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from money import BANKROLL_START, CUTOFF_LOSS_USD, usd

LEDGER_PATH = Path(__file__).resolve().parents[1] / "data" / "ledger.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Entry:
    game_key: str
    ticker: str
    event_ticker: str
    team: str
    matchup: str
    side: str
    price_c: int
    contracts: int
    cost_usd: float
    fee_usd: float
    win_profit_usd: float
    lose_usd: float
    starts_utc: str
    confirmed_utc: str
    status: str = "open"            # 'open' | 'won' | 'lost' | 'void'
    settled_utc: Optional[str] = None
    pnl_usd: float = 0.0
    note: str = ""
    why: list = field(default_factory=list)


class Ledger:
    def __init__(self, path: Path = LEDGER_PATH):
        self.path = Path(path)
        self.entries: list[Entry] = []
        self.load()

    # ---- disk -----------------------------------------------------------
    def load(self) -> None:
        if not self.path.exists():
            self.entries = []
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # A corrupt ledger must never be silently treated as an empty one
            # -- an empty ledger re-opens every game Guard 1 has closed. Keep
            # the bad file and refuse to run instead.
            raise RuntimeError(
                f"{self.path} is not readable JSON. It is the record of what "
                f"has already been bet, so this window will not start without "
                f"it. Fix or move the file and restart.")
        self.entries = [Entry(**e) for e in raw.get("entries", [])]

    def save(self) -> None:
        """Write via a temp file in the same folder, then replace. A half
        written ledger is a ledger that has forgotten a bet, and a forgotten
        bet is a repeated bet."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"bankroll_start_usd": BANKROLL_START,
                   "cutoff_loss_usd": CUTOFF_LOSS_USD,
                   "written_utc": _now(),
                   "entries": [asdict(e) for e in self.entries]}
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=1)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # ---- Guard 1 --------------------------------------------------------
    def played_games(self) -> set:
        """Every game this tool has ever put money on. Permanent."""
        return {e.game_key for e in self.entries}

    def has_played(self, game_key: str) -> bool:
        return game_key in self.played_games()

    def add(self, entry: Entry) -> None:
        if self.has_played(entry.game_key):
            raise ValueError(
                f"Guard 1: {entry.game_key} already has a bet. One per game.")
        self.entries.append(entry)
        self.save()

    # ---- Guard 2 --------------------------------------------------------
    def realised_usd(self) -> float:
        """Money this strategy has actually won or lost on settled games."""
        return round(sum(e.pnl_usd for e in self.entries
                         if e.status in ("won", "lost")), 2)

    def at_risk_usd(self) -> float:
        """Money currently sitting in games that have not finished."""
        return round(sum(e.cost_usd for e in self.entries
                         if e.status == "open"), 2)

    def worst_case_usd(self) -> float:
        """Where the running total lands if every open bet loses. The cut-off
        is checked against THIS, not against settled money alone -- otherwise
        it would keep handing out bets while $40 of losers were still in
        flight, and only notice after they all settled."""
        return round(self.realised_usd() - self.at_risk_usd(), 2)

    def running_total_usd(self) -> float:
        return self.realised_usd()

    def bankroll_usd(self) -> float:
        return round(BANKROLL_START + self.realised_usd(), 2)

    def cutoff_hit(self) -> bool:
        return self.worst_case_usd() <= -CUTOFF_LOSS_USD

    def cutoff_reason(self) -> str:
        return (f"STOPPED. This tool is down ${abs(self.worst_case_usd()):.2f} "
                f"counting every open bet as a loss, and the line you set was "
                f"${CUTOFF_LOSS_USD:.2f}. No more bets. "
                f"Settled so far: {usd(self.realised_usd())} on "
                f"{len([e for e in self.entries if e.status in ('won','lost')])} "
                f"finished games.")

    # ---- settlement -----------------------------------------------------
    def open_entries(self) -> list:
        return [e for e in self.entries if e.status == "open"]

    def settle(self, ticker: str, won: bool) -> Optional[Entry]:
        for e in self.entries:
            if e.ticker == ticker and e.status == "open":
                e.status = "won" if won else "lost"
                e.pnl_usd = (e.win_profit_usd if won else -e.lose_usd)
                e.settled_utc = _now()
                self.save()
                return e
        return None

    def summary_line(self) -> str:
        n_done = len([e for e in self.entries if e.status in ("won", "lost")])
        n_open = len(self.open_entries())
        won = len([e for e in self.entries if e.status == "won"])
        return (f"baseball: {usd(self.realised_usd())} on {n_done} finished "
                f"({won} won)  ·  ${self.at_risk_usd():.2f} still riding on "
                f"{n_open} game(s)  ·  bankroll ${self.bankroll_usd():.2f}")
