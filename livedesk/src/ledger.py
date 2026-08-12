"""The record of every bet this window proposed and he confirmed.

This file is the only thing that knows what the strategy has actually done
with his money, and it is what every guard reads.

  Guard 1  ONE BET PER SIGNAL. Not per game -- he corrected that himself and
           he was right: *"We should be allowed to reenter the same game if
           it's a different scenario… the criteria has been met again. It's a
           different bet but it's the same game."* What has to be blocked is
           the SAME rule firing again on the SAME state, which is leverage on
           one outcome dressed up as several trades. Plus a hard cap of two
           positions per game whatever the reasoning, and never adding to a
           position that is currently losing.

  Guard 2  STOP EVERYTHING, on two rules, either of which is enough:
             * the account below $50 -- absolute, never moves
             * the running total more than 35% below its highest point
           He corrected the fixed -$33 himself: *"It can't be cut off at
           thirty, because let's say the bot keeps going and makes three
           hundred, and then we lose thirty. That's only ten percent."*

  Guard 4  RECONCILE OR REFUSE, and this is the most important one, because
           it is the only guard that can catch the other guards being fed a
           wrong number. See `reconcile()`.

It is a plain JSON file so he can open it, read it, and correct it with
Notepad if this window ever gets something wrong. It lives under `data/`,
which is gitignored repo-wide -- his money records do not go on the internet.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from money import BANKROLL_START, usd

LEDGER_PATH = Path(__file__).resolve().parents[1] / "data" / "ledger.json"

# --- Guard 2, as he restated it -----------------------------------------
ACCOUNT_FLOOR_USD = 50.00      # absolute. never moves. his "cannot go under".
TRAILING_DROP_FRAC = 0.35      # 35% below the highest the running total reached
# From $83 that is a stop at $53.95 -- next to his floor at the start, and
# proportionate later: at $300 it allows a $105 drawdown, which is what he
# meant by "thirty out of three hundred is only ten percent".

# --- Guard 1 -------------------------------------------------------------
MAX_POSITIONS_PER_GAME = 2

# --- Guard 4 -------------------------------------------------------------
RECONCILE_TOLERANCE_USD = 1.00
# Kalshi pays a settled market out some minutes after the result is final, so
# a bet that settled seconds ago is legitimately in the ledger and not yet in
# the balance. Anything settled inside this window is held back from the
# expected figure and shown separately, rather than firing a false alarm that
# would train him to ignore the real one.
SETTLEMENT_LAG_HOURS = 3.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse(s):
    if not s:
        return None
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# A flag like "form_divergence_IGNORED_only_1_starts_5.1ip" carries numbers
# that drift between one decision window and the next. The SIGNAL is the rule
# that fired, not the innings count, so the tail is stripped before the key is
# built -- otherwise the identical rule on the identical pitcher would look
# like a fresh signal three times a day and Guard 1 would never fire.
_FLAG_TAIL = re.compile(r"^(form_divergence_IGNORED)_.*$")


def signal_key(game_key: str, backed: str, flags: dict) -> str:
    """Which rule fired, and on what state. Two decisions with the same key
    are the same bet and the second one is blocked forever."""
    parts = []
    for side in sorted(flags or {}):
        names = sorted(_FLAG_TAIL.sub(r"\1", f)
                       for f in (flags[side].get("flags") or []))
        if names:
            parts.append(f"{side}:{'+'.join(names)}")
    return f"{game_key}|{backed}|{';'.join(parts)}"


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
    signal: str = ""
    status: str = "open"            # 'open' | 'won' | 'lost' | 'void'
    settled_utc: Optional[str] = None
    pnl_usd: float = 0.0
    note: str = ""
    why: list = field(default_factory=list)

    @property
    def counts_as_money(self) -> bool:
        """A void entry was never actually placed, so no money left the
        account for it. It still closes its signal."""
        return self.status != "void"

    @property
    def payout_usd(self) -> float:
        """What the account received back. A winning contract pays $1."""
        return round(self.contracts * 1.00, 2) if self.status == "won" else 0.0


class Ledger:
    def __init__(self, path: Path = LEDGER_PATH):
        self.path = Path(path)
        self.entries: list[Entry] = []
        # The Kalshi balance when this ledger began, and the last balance he
        # typed in. Both are his numbers; nothing here can read an account.
        self.account_start_usd: float = BANKROLL_START
        self.account_balance_usd: Optional[float] = None
        self.account_checked_utc: Optional[str] = None
        self.peak_total_usd: float = BANKROLL_START
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
            # -- an empty ledger re-opens every signal Guard 1 has closed. Keep
            # the bad file and refuse to run instead.
            raise RuntimeError(
                f"{self.path} is not readable JSON. It is the record of what "
                f"has already been bet, so this window will not start without "
                f"it. Fix or move the file and restart.")
        self.entries = [Entry(**e) for e in raw.get("entries", [])]
        self.account_start_usd = float(
            raw.get("account_start_usd", BANKROLL_START))
        b = raw.get("account_balance_usd")
        self.account_balance_usd = None if b is None else float(b)
        self.account_checked_utc = raw.get("account_checked_utc")
        self.peak_total_usd = float(raw.get("peak_total_usd",
                                            self.account_start_usd))

    def save(self) -> None:
        """Write via a temp file in the same folder, then replace. A half
        written ledger is a ledger that has forgotten a bet, and a forgotten
        bet is a repeated bet."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._bump_peak()
        payload = {"account_start_usd": self.account_start_usd,
                   "account_balance_usd": self.account_balance_usd,
                   "account_checked_utc": self.account_checked_utc,
                   "peak_total_usd": self.peak_total_usd,
                   "account_floor_usd": ACCOUNT_FLOOR_USD,
                   "trailing_drop_frac": TRAILING_DROP_FRAC,
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
    def signals_played(self) -> set:
        """Every signal this tool has ever acted on. Permanent, and a void
        counts -- he saw that exact bet and dealt with it."""
        return {e.signal for e in self.entries if e.signal}

    def positions_on_game(self, game_key: str) -> int:
        return len([e for e in self.entries
                    if e.game_key == game_key and e.counts_as_money])

    def open_on_game(self, game_key: str) -> list:
        return [e for e in self.entries
                if e.game_key == game_key and e.status == "open"]

    def may_bet(self, game_key: str, signal: str, price_now_c=None):
        """(allowed, reason). The reason is shown on the button, so it is
        written for him, not for a log."""
        if signal and signal in self.signals_played():
            return False, ("this exact bet has already been taken on this "
                           "game — same rule, same reason. One per signal.")
        n = self.positions_on_game(game_key)
        if n >= MAX_POSITIONS_PER_GAME:
            return False, (f"you already have {n} bets on this game, which is "
                           f"the limit. Two is the most, whatever the reason.")
        if price_now_c is not None:
            for e in self.open_on_game(game_key):
                if price_now_c < e.price_c:
                    return False, (
                        f"your open bet on this game is losing "
                        f"({e.price_c}c paid, {int(price_now_c)}c now). This "
                        f"tool never adds to a losing position.")
        return True, ""

    def add(self, entry: Entry) -> None:
        ok, why = self.may_bet(entry.game_key, entry.signal)
        if not ok:
            raise ValueError(f"Guard 1: {why}")
        self.entries.append(entry)
        self.save()

    # ---- the money ------------------------------------------------------
    def realised_usd(self) -> float:
        return round(sum(e.pnl_usd for e in self.entries
                         if e.status in ("won", "lost")), 2)

    def at_risk_usd(self) -> float:
        return round(sum(e.cost_usd for e in self.entries
                         if e.status == "open"), 2)

    def running_total_usd(self) -> float:
        """The bot's own running total: what the account would be if it had
        only ever done what this tool proposed."""
        return round(self.account_start_usd + self.realised_usd(), 2)

    def worst_case_total_usd(self) -> float:
        """Where that lands if every open bet loses. Both are checked, so the
        cut-off cannot keep handing out bets while losers are in flight."""
        return round(self.running_total_usd() - self.at_risk_usd(), 2)

    def _bump_peak(self) -> None:
        self.peak_total_usd = max(self.peak_total_usd,
                                  self.running_total_usd())

    # ---- Guard 2 --------------------------------------------------------
    def trailing_stop_usd(self) -> float:
        return round(self.peak_total_usd * (1.0 - TRAILING_DROP_FRAC), 2)

    def account_for_floor_usd(self):
        """(value, is_real). His typed balance if he has given one, otherwise
        what the ledger implies -- and the caller is told which, because a
        floor checked against a number this tool made up is not his floor."""
        if self.account_balance_usd is not None:
            return self.account_balance_usd, True
        return self.worst_case_total_usd(), False

    def stopped(self):
        """(True, reason) if everything must stop. Both rules, either fires."""
        self._bump_peak()
        acct, real = self.account_for_floor_usd()
        if acct < ACCOUNT_FLOOR_USD:
            src = "your account" if real else "this tool's own count"
            return True, (f"STOPPED. {src} is at ${acct:.2f}, under the "
                          f"${ACCOUNT_FLOOR_USD:.0f} floor you set. That floor "
                          f"never moves. No more bets.")
        stop_at = self.trailing_stop_usd()
        worst = self.worst_case_total_usd()
        if worst < stop_at:
            return True, (
                f"STOPPED. Counting every open bet as a loss, this tool is at "
                f"${worst:.2f}. Its best was ${self.peak_total_usd:.2f}, and "
                f"35% below that is ${stop_at:.2f}. No more bets.")
        return False, ""

    def room_line(self) -> str:
        """Both cut-offs and how much room is left in each, always on screen."""
        acct, real = self.account_for_floor_usd()
        stop_at = self.trailing_stop_usd()
        worst = self.worst_case_total_usd()
        return (f"floor ${ACCOUNT_FLOOR_USD:.0f}: "
                f"${max(0.0, acct - ACCOUNT_FLOOR_USD):.2f} of room"
                f"{'' if real else ' (from this tool, not your account)'}"
                f"   ·   35% off its best ${self.peak_total_usd:.2f} = stop at "
                f"${stop_at:.2f}: ${max(0.0, worst - stop_at):.2f} of room")

    # ---- Guard 4: reconcile or refuse -----------------------------------
    def money_out_usd(self) -> float:
        return round(sum(e.cost_usd for e in self.entries
                         if e.counts_as_money), 2)

    def money_back_usd(self, exclude_recent=True) -> float:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=SETTLEMENT_LAG_HOURS)
        total = 0.0
        for e in self.entries:
            if e.status != "won":
                continue
            if exclude_recent:
                t = _parse(e.settled_utc)
                if t and t > cutoff:
                    continue
            total += e.payout_usd
        return round(total, 2)

    def pending_payout_usd(self) -> float:
        """Won, but settled too recently for the cash to have landed."""
        return round(self.money_back_usd(exclude_recent=False)
                     - self.money_back_usd(exclude_recent=True), 2)

    def expected_account_usd(self) -> float:
        return round(self.account_start_usd - self.money_out_usd()
                     + self.money_back_usd(), 2)

    def set_account_balance(self, value: float) -> None:
        self.account_balance_usd = round(float(value), 2)
        self.account_checked_utc = _now()
        self.save()

    def reconcile(self):
        """(state, message). One of:

        'nothing'   nothing has been placed, so the ledger cannot be wrong
        'unchecked' bets have settled and he has not told us the balance
        'ok'        the two agree inside a dollar
        'disagree'  they do not, and the window must refuse to show a profit
                    figure and refuse to propose trades

        THIS EXISTS BECAUSE IT HAS ALREADY HAPPENED. His account went from
        $130 to $160 while the tennis app said it was down $2, with no trades
        of his own in between -- about $32 of disagreement, reported, "fixed",
        and still wrong. The cut-off watches the ledger, so a ledger that can
        be $32 out is a cut-off that does not fire. A number that might be $32
        wrong is worse than no number, because he will act on it.
        """
        if not [e for e in self.entries if e.counts_as_money]:
            return "nothing", "nothing placed yet, so there is nothing to check"
        settled = [e for e in self.entries if e.status in ("won", "lost")]
        if self.account_balance_usd is None:
            if not settled:
                return "nothing", ("nothing has finished yet — type your Kalshi "
                                   "balance in when the first game settles")
            return "unchecked", (
                f"{len(settled)} bet(s) have finished and this tool has not "
                f"been checked against your real balance. Type what Kalshi "
                f"shows into the balance box. Until then it will not show a "
                f"profit figure and will not propose a bet.")
        exp = self.expected_account_usd()
        diff = round(self.account_balance_usd - exp, 2)
        if abs(diff) <= RECONCILE_TOLERANCE_USD:
            return "ok", (f"agrees: your balance ${self.account_balance_usd:.2f} "
                          f"against ${exp:.2f} expected")
        pend = self.pending_payout_usd()
        extra = (f" ${pend:.2f} of winnings settled in the last "
                 f"{SETTLEMENT_LAG_HOURS:.0f} hours and is not counted yet, "
                 f"which may be the whole difference." if pend else "")
        return "disagree", (
            f"THESE DO NOT AGREE by {usd(diff)}. Your balance says "
            f"${self.account_balance_usd:.2f}; this tool expects "
            f"${exp:.2f} (started ${self.account_start_usd:.2f}, "
            f"${self.money_out_usd():.2f} out, ${self.money_back_usd():.2f} "
            f"back).{extra} No profit figure and no bets until this is sorted "
            f"— a number that might be wrong is worse than no number.")

    def profit_shown(self) -> bool:
        return self.reconcile()[0] in ("nothing", "ok")

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
        money = (usd(self.realised_usd()) if self.profit_shown()
                 else "— (not checked)")
        return (f"baseball: {money} on {n_done} finished ({won} won)  ·  "
                f"${self.at_risk_usd():.2f} riding on {n_open}  ·  "
                f"account {self._account_str()}")

    def _account_str(self) -> str:
        if self.account_balance_usd is None:
            return "not typed in"
        when = _parse(self.account_checked_utc)
        age = ""
        if when:
            hrs = (datetime.now(timezone.utc) - when).total_seconds() / 3600.0
            age = f" ({hrs:.0f}h ago)" if hrs >= 1 else " (just now)"
        return f"${self.account_balance_usd:.2f}{age}"
