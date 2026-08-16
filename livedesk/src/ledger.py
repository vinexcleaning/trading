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

from money import BANKROLL_START, STAKE_USD, usd

LEDGER_PATH = Path(__file__).resolve().parents[1] / "data" / "ledger.json"

# --- Guard 2, as he restated it -----------------------------------------
ACCOUNT_FLOOR_USD = 50.00      # absolute. never moves. his "cannot go under".
TRAILING_DROP_FRAC = 0.35      # 35% below the highest the running total reached
# From $83 that is a stop at $53.95 -- next to his floor at the start, and
# proportionate later: at $300 it allows a $105 drawdown, which is what he
# meant by "thirty out of three hundred is only ten percent".

# --- Guard 1 -------------------------------------------------------------
MAX_POSITIONS_PER_GAME = 2
# A bet he copied and then said he never placed is offered ONCE more. The
# second void closes it for good. See signals_played() for why.
MAX_VOIDS_BEFORE_CLOSED = 2

# --- Guard 5: the daily caps, his numbers --------------------------------
# Guard 5: the daily caps
MAX_ORDERS_PER_DAY = 9999
MAX_STAKE_PER_DAY_USD = 50.00

# --- Guard 4 -------------------------------------------------------------
RECONCILE_TOLERANCE_USD = 1.00
# Kalshi pays a settled market out some minutes after the result is final, so
# a bet that settled seconds ago is legitimately in the ledger and not yet in
# the balance. Anything settled inside this window is held back from the
# expected figure and shown separately, rather than firing a false alarm that
# would train him to ignore the real one.
SETTLEMENT_LAG_HOURS = 3.0
# How long after first pitch a bet should still be visible as an open position.
# Beyond this it has probably settled and disappeared legitimately, so its
# absence means nothing and is not reported as a disagreement.
POSITION_LIVE_HOURS = 6.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _size(v) -> float:
    """Kalshi returns position size as a decimal STRING (`position_fp`), not a
    number, and the plain `position` field is the one that is wrong. Trap C024
    in this repo is exactly this family of mistake."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


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
    status: str = "open"            # 'open' | 'won' | 'lost' | 'void' | 'deferred' | 'expired'
    settled_utc: Optional[str] = None
    pnl_usd: float = 0.0
    note: str = ""
    why: list = field(default_factory=list)
    # Was anything else on this game when the bet was taken? Recorded so that
    # in 50 bets the question "did the solo picks lose again?" can be answered
    # FROM THE RECORD rather than re-derived from results afterwards, which is
    # how the pattern was found in the first place and why it is not yet
    # evidence. INFORMATION ONLY -- nothing reads these to make a decision.
    alone: Optional[bool] = None
    consensus: str = ""

    @property
    def counts_as_money(self) -> bool:
        """A void, deferred, or expired entry was never actually placed,
        so no money left the account for it.

        * `void` — user clicked "I did NOT place it" or genuine duplicate;
          permanently closed for good.
        * `deferred` — temporary block (reconciliation mismatch, network
          error, etc.); the signal is preserved and will be retried.
        * `expired` — the game has started; the signal is gone.
        """
        return self.status not in ("void", "deferred", "expired")

    @property
    def payout_usd(self) -> float:
        """What the account received back. A winning contract pays $1."""
        return round(self.contracts * 1.00, 2) if self.status == "won" else 0.0


class Ledger:
    def __init__(self, path=None):
        # ⚠ RESOLVED AT CALL TIME, NOT AS A DEFAULT ARGUMENT. It used to be
        # `path: Path = LEDGER_PATH`, and a default argument is bound once when
        # the function is defined -- so the GUI test's
        # `ledger.LEDGER_PATH = <temp file>` did nothing, `Desk()` opened the
        # REAL ledger, and the per-test fixture's `entries.clear()` + `save()`
        # DELETED EVERY ENTRY OF HIS on 2026-08-16.
        #
        # 150 tests passed while that was happening, because nothing asserted
        # where the tests were writing. There is now a test that does.
        self.path = Path(path if path is not None else LEDGER_PATH)
        self.entries: list[Entry] = []
        # The Kalshi balance when this ledger began, and the last balance he
        # typed in. Both are his numbers; nothing here can read an account.
        self.account_start_usd: float = BANKROLL_START
        self.account_balance_usd: Optional[float] = None
        self.account_checked_utc: Optional[str] = None
        self.peak_total_usd: float = BANKROLL_START
        # Last read of his OPEN POSITIONS, set by whoever fetched them. Never
        # fetched here -- this module has no network and a test enforces that.
        self.account_positions: list = []
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
    def signals_played(self, ignore=None) -> set:
        """Every signal that is closed for good.

        ⚠ CHANGED 2026-08-12, and it is a real change to Guard 1. It used to be
        "any entry at all, including a void". That cost him three bets in one
        evening: Pittsburgh, Cleveland and Seattle were all copied, he got lost
        on the Kalshi page, came back and pressed "I did NOT place this" --
        and all three games were then closed for ever having never been bet.

        **A void means no money was placed.** Guard 1 exists to stop the same
        bet going on twice, which is leverage on one outcome dressed up as
        several trades. Re-offering something he never placed is not that, so
        blocking it was the guard misfiring, not the guard working.

        So: a signal is closed if any entry on it was really placed, or if it
        has been voided TWICE. The second void closes it -- which stops a loop
        where he copies, voids, copies, voids and eventually buys at a price
        the bot never saw.

        **Deferred and expired entries do NOT close the signal.** A deferred
        pick was blocked by a temporary condition and will be retried; an
        expired pick's game has started so the bet is gone. Neither should
        count as "played" for Guard 1.
        """
        played = set()
        voids = {}
        for e in self.entries:
            # `ignore` is the entry being asked ABOUT -- when the caller is
            # re-checking a bet already written to the ledger, its own row must
            # not be read as somebody else having taken it. Without this the
            # practice-order button could never fire even once.
            if not e.signal or e is ignore:
                continue
            if e.status == "void":
                voids[e.signal] = voids.get(e.signal, 0) + 1
            elif e.status not in ("void", "deferred", "expired"):
                played.add(e.signal)
        return played | {s for s, n in voids.items()
                         if n >= MAX_VOIDS_BEFORE_CLOSED}

    def positions_on_game(self, game_key: str, ignore=None) -> int:
        return len([e for e in self.entries
                    if e.game_key == game_key and e.counts_as_money
                    and e is not ignore])

    def open_on_game(self, game_key: str) -> list:
        return [e for e in self.entries
                if e.game_key == game_key and e.status == "open"]

    def may_bet(self, game_key: str, signal: str, price_now_c=None,
                next_cost_usd: float = 0.0, ignore=None):
        """(allowed, reason). The reason is shown on the button, so it is
        written for him, not for a log."""
        if signal and signal in self.signals_played(ignore=ignore):
            return False, ("this exact bet has already been taken on this "
                           "game — same rule, same reason. One per signal.")
        n = self.positions_on_game(game_key, ignore=ignore)
        if n >= MAX_POSITIONS_PER_GAME:
            return False, (f"you already have {n} bets on this game, which is "
                           f"the limit. Two is the most, whatever the reason.")
        if price_now_c is not None:
            for e in self.open_on_game(game_key):
                if e is ignore:
                    continue
                if price_now_c < e.price_c:
                    return False, (
                        f"your open bet on this game is losing "
                        f"({e.price_c}c paid, {int(price_now_c)}c now). This "
                        f"tool never adds to a losing position.")
        capped = self.daily_block(next_cost_usd or 0.0, ignore=ignore)
        if capped:
            return False, capped
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

    # ---- Guard 5: the daily caps ----------------------------------------
    def _today_entries(self):
        """Everything really placed today, in HIS day, not UTC's.

        Raises if a date cannot be read. That is deliberate: an unreadable
        ledger must mean NO order, never an unlimited one.
        """
        today = datetime.now().astimezone().date()
        out = []
        for e in self.entries:
            if not e.counts_as_money:
                continue
            t = _parse(e.confirmed_utc)
            if t is None:
                raise ValueError(
                    f"entry {e.ticker} has no readable date "
                    f"({e.confirmed_utc!r}), so today's total cannot be "
                    f"counted and no order can be allowed")
            if t.astimezone().date() == today:
                out.append(e)
        return out

    def daily_used(self, ignore=None):
        """(orders today, dollars today). Raises rather than guess."""
        rows = [e for e in self._today_entries() if e is not ignore]
        return len(rows), round(sum(e.cost_usd for e in rows), 2)

    def daily_block(self, next_cost_usd: float = 0.0, ignore=None):
        """Why today's caps forbid another bet, or None. Fails closed."""
        try:
            n, spent = self.daily_used(ignore=ignore)
        except ValueError as exc:
            return f"cannot count today's bets, so no bet: {exc}"
        if n >= MAX_ORDERS_PER_DAY:
            return (f"you have made {n} bets today, which is the limit of "
                    f"{MAX_ORDERS_PER_DAY}. Nothing more until tomorrow.")
        if spent + next_cost_usd > MAX_STAKE_PER_DAY_USD + 1e-9:
            return (f"you have put ${spent:.2f} in today and this one would "
                    f"take it to ${spent + next_cost_usd:.2f}, over the "
                    f"${MAX_STAKE_PER_DAY_USD:.2f} daily limit. Nothing more "
                    f"until tomorrow.")
        return None

    def daily_line(self) -> str:
        """Both counters and WHICH ONE will actually stop him.

        At $4.15 a bet the money runs out at 6, so the limit of 10 orders can
        never be reached. That is fine as a belt and braces, but he must not
        think he raised his ceiling from 6 to 10 when he did not. Computed, so
        it stays true if any of the three numbers change.
        """
        try:
            n, spent = self.daily_used()
        except ValueError as exc:
            return f"today: cannot be counted, so no bets — {exc}"
        left_money = MAX_STAKE_PER_DAY_USD - spent
        stake = STAKE_USD if STAKE_USD > 0 else 0.01
        bets_money_allows = int((left_money + 1e-9) / stake)
        bets_count_allows = MAX_ORDERS_PER_DAY - n
        if bets_money_allows < bets_count_allows:
            which = (f"money runs out first, after {bets_money_allows} more"
                     if bets_money_allows else "the money is gone for today")
        elif bets_count_allows < bets_money_allows:
            which = (f"the order count runs out first, after "
                     f"{bets_count_allows} more")
        else:
            which = f"both run out together, after {bets_count_allows} more"
        return (f"today: {n} of {MAX_ORDERS_PER_DAY} bets  ·  "
                f"${spent:.2f} of ${MAX_STAKE_PER_DAY_USD:.2f}  ·  {which}")

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

    # ---- Guard 4, RE-POINTED 2026-08-16 ---------------------------------
    def _ours_open(self, ignore=None):
        """Our open bets that the account should currently be showing.

        Only bets on games inside the live window. Once a game has been over
        for a while the position settles and legitimately disappears, and
        "missing" would then mean nothing at all.

        ⚠ `ignore` is the entry being asked ABOUT, and leaving it out is not
        an optimisation -- it is the difference between the tool working and
        not. The entry is written to the ledger BEFORE it is submitted, so
        without this the bet about to be placed counts as one of our open bets
        that is missing from his account, Guard 4 says "does not match", and
        the bet refuses itself. Every auto bet, for ever.

        This is the SECOND time this exact shape has appeared here: Guard 1 had
        it in August and it made the practice button permanently dead. I fixed
        that one and then reintroduced it in Guard 4 the day I re-pointed it.
        """
        now = datetime.now(timezone.utc)
        out = {}
        for e in self.entries:
            if e.status != "open" or e is ignore:
                continue
            starts = _parse(e.starts_utc)
            if starts and now > starts + timedelta(hours=POSITION_LIVE_HOURS):
                continue
            out[e.ticker] = out.get(e.ticker, 0) + e.contracts
        return out

    def reconcile_positions(self, rows, ignore=None):
        """(state, message) from the account's OPEN POSITIONS, not its balance.

        ⚠ THIS REPLACED A CHECK THAT COULD NEVER PASS, and the failure was
        expensive. The old version compared this tool's ledger against his
        whole Kalshi balance, which silently assumed every trade in the account
        came from this tool. **He trades manually and always will** -- he has
        said so twice. So the two sums could never agree, and every entry's
        note recorded the same thing:

            auto-exec deferred: THESE DO NOT AGREE by +$29.53...

        **11 bets expired unplaced before anyone noticed.** The guard was not
        protecting him from anything; it was eating every signal the tool
        produced.

        The question it asks now is narrower and actually answerable: **is each
        bet I placed sitting in his account at the size I placed it?** Anything
        on a ticker this tool never touched is his own business and is not
        looked at.

        This is a STRONGER guard, not a weaker one. Before, the worst it could
        say was "something does not add up somewhere". Now it can say "the
        Cleveland bet I placed is not in your account", which is a real problem
        worth stopping for.
        """
        ours = self._ours_open(ignore=ignore)
        if not ours:
            return "nothing", "no open bets of its own to check"
        held = {}
        for r in (rows or []):
            t = str(r.get("ticker") or "")
            if t in ours:
                held[t] = held.get(t, 0.0) + abs(_size(r.get("position_fp")))
        problems = []
        for ticker, want in sorted(ours.items()):
            got = held.get(ticker, 0.0)
            e = next((x for x in self.entries
                      if x.ticker == ticker and x.status == "open"
                      and x is not ignore), None)
            who = f"{e.team} ({e.matchup})" if e else ticker
            if got <= 0:
                problems.append(f"the {who} bet is NOT in your account at all")
            elif abs(got - want) > 0.001:
                problems.append(f"the {who} bet shows {got:g} contracts, "
                                f"not the {want} it placed")
        if problems:
            return "disagree", (
                "THIS TOOL'S OWN BETS DO NOT MATCH YOUR ACCOUNT: "
                + "; ".join(problems)
                + ". Nothing else in your account is being looked at. No more "
                  "bets until this is sorted.")
        n = len(ours)
        return "ok", (f"all {n} of its own open bet{'s' if n != 1 else ''} are "
                      f"in your account at the right size")

    def balance_note(self) -> str:
        """The old balance comparison, kept as a DISPLAY only.

        It is genuinely informative -- it is how the $32 error would show up --
        but it must never gate anything again, because his own trading moves it
        and that is not a fault.
        """
        if self.account_balance_usd is None:
            return "account balance not read yet"
        exp = self.expected_account_usd()
        diff = round(self.account_balance_usd - exp, 2)
        if abs(diff) <= RECONCILE_TOLERANCE_USD:
            return (f"account ${self.account_balance_usd:.2f}, and this tool's "
                    f"own bets account for all of it")
        return (f"account ${self.account_balance_usd:.2f}; {usd(diff)} of that "
                f"is not from this tool — your own trades, which is expected")

    def reconcile(self, rows=None, ignore=None):
        """Guard 4. Delegates to the positions check -- see
        reconcile_positions for why it is no longer the balance."""
        if rows is None:
            rows = self.account_positions
        return self.reconcile_positions(rows, ignore=ignore)

    def _reconcile_balance_old(self):
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

    def deferred_entries(self) -> list:
        """Entries that were blocked by a temporary condition and can be
        retried when the condition clears. They are NOT closed signals."""
        return [e for e in self.entries if e.status == "deferred"]

    def expire_deferred_past_game_start(self) -> int:
        """Mark deferred entries whose game has already started as 'expired'.

        Returns the number of entries expired.  Expired entries are kept in
        the ledger for audit but are never retried.
        """
        now = datetime.now(timezone.utc)
        count = 0
        for e in self.entries:
            if e.status != "deferred":
                continue
            start = _parse(e.starts_utc)
            if start and start < now:
                e.status = "expired"
                e.note = (e.note or "") + "; game has started (expired)"
                count += 1
        if count:
            self.save()
        return count

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
