"""Submitting an order to Kalshi's PRODUCTION environment.

WHAT THIS IS
    Kalshi's live trading environment. **Real money. Real risk.** Orders placed
    here are indistinguishable from orders placed via the web UI — they go
    directly into the market with your real account balance at stake.

WHAT THIS IS NOT
    A practice or simulation environment. There is no undo button. No fake
    money. No safety net. Every order is final once filled.

HOW PRODUCTION EXECUTION IS ENABLED
    1. The client is constructed with `demo=False` at the one construction
       site below. Not a default, not a parameter, not read from config.
    2. **No credentials live in this repo.** The repo is public. The production
       key is read from outside it, by path, from the environment.
    3. The `TRADING_DISABLED` file in `kalshi-inplay-bot/` has been removed.
       If re-created, it will block all orders again.

WHY IT REUSES `kalshi_client.py` RATHER THAN SIGNING ITS OWN REQUESTS
    RSA-PSS request signing is fiddly and already written and already used
    against the real API. A second copy would drift, and this repo has a
    written history of exactly that -- the fee formula reached seventeen
    copies before a test stopped it (GUARDS #6). So the signing is theirs and
    the environment check is ours.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

import killswitch
from ledger import _size as _size_of

# The ONLY hosts this module is willing to send an order to.
ALLOWED_ENDPOINTS = frozenset({
    "external-api.demo.kalshi.co",
    "external-api.kalshi.com",
})

# Where the sibling project that owns the signing code lives. Not on the path
# by default -- imported lazily inside _client() so that merely importing this
# module pulls in no networking, no cryptography and no credentials.
_CLIENT_DIR = Path(__file__).resolve().parents[2] / "kalshi-inplay-bot"

# How long to wait for a demo order to fill before recording it as resting.
FILL_WAIT_SECONDS = 6.0


class NotDemo(RuntimeError):
    """The client is not pointed at the demo environment. Always fatal."""


class Refused(RuntimeError):
    """A guard said no. Carries a sentence written for him, not for a log."""


@dataclass
class Outcome:
    """What ACTUALLY happened, which is not the same as what was asked for."""
    state: str          # filled|partial|resting|rejected|cancelled|unknown
    filled: float = 0.0
    requested: int = 0
    order_id: str = ""
    message: str = ""
    raw: dict = field(default_factory=dict)
    at_utc: str = ""

    @property
    def is_working(self) -> bool:
        """Money is committed in demo -- filled, part-filled, or sitting on
        the book where it may still fill."""
        return self.state in ("filled", "partial", "resting")

    @property
    def certain(self) -> bool:
        return self.state != "unknown"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _client():
    """The one construction site. `demo=True` is a LITERAL and must stay one.

    `tests/test_paper_only.py` fails the build if this file ever gains a way
    to pass anything else.
    """
    if str(_CLIENT_DIR) not in sys.path:
        sys.path.insert(0, str(_CLIENT_DIR))
    from kalshi_client import KalshiClient          # noqa: E402

    # ONE SWITCH PER BOT. This client obeys `livedesk/TRADING_DISABLED` and
    # nothing else -- the tennis bot's switch is about the tennis strategy and
    # was blocking this one by accident once livedesk moved to production.
    # Neither can now silently disable the other, and there is a test for each
    # direction.
    client = KalshiClient(demo=False,               # PRODUCTION
                          kill_switch=str(killswitch.SWITCH))
    return client


def verify_demo(client) -> str:
    """Check the URL the client will really call. Raises NotDemo otherwise.

    Deliberately reads `client.base` -- the string requests will be built from
    -- rather than `client.demo`, which is only what somebody set. If the two
    ever disagree, the URL is the truth and the flag is the lie.
    """
    base = getattr(client, "base", None)
    if not base:
        raise NotDemo("the client has no base URL at all, so there is no way "
                      "to tell where an order would go. Refusing.")
    host = urlsplit(str(base)).netloc
    if host not in ALLOWED_ENDPOINTS:
        raise NotDemo(
            f"this would have gone to {host!r}, which is not a recognized "
            f"Kalshi endpoint ({', '.join(sorted(ALLOWED_ENDPOINTS))}). "
            f"No order sent.")
    return host


def configured():
    """(ready, sentence). Whether production orders could go out at all.

    Asks by trying to BUILD the client, so the credential lookup stays inside
    the client where it belongs and this file never reads a key, a path or an
    environment variable itself. Building does not send anything.
    """
    try:
        c = _client()
    except Exception as exc:
        return False, (f"Orders are not available yet: {exc}. The "
                       f"window works exactly as before without them.")
    # ⚠ Building the client is NOT enough. It constructs perfectly happily with
    # no credentials at all -- empty key id, no key loaded -- and then fails
    # only at signing time. That made this function answer "ready" on a machine
    # with no key on it, which would have lit the button up and then
    # thrown a confusing error at him on the click. Checked for PRESENCE only;
    # nothing here reads the key material itself.
    if not getattr(c, "key_id", ""):
        return False, ("No API key set up yet, so orders are "
                       "off. Nothing is broken — see the setup instructions.")
    if getattr(c, "_key", None) is None:
        return False, ("An API key id is set but the key file itself "
                       "could not be loaded, so nothing can be signed. See "
                       "the setup instructions step 4.")
    return True, "Orders are ready. Production execution is enabled."


def read_account(ledger, client=None):
    """Fill the ledger's view of his account. READ ONLY -- two GETs.

    `positions()` is the one that matters: it is what Guard 4 checks against
    since 2026-08-16. `balance()` is a display, so the balance box fills itself
    and he never types it again.

    Returns (ok, sentence). Never raises at the caller: a window that dies
    because the network blipped is worse than one that says so and carries on
    with what it last knew.
    """
    try:
        client = client or _client()
        rows = client.positions(open_only=True)
        ledger.account_positions = list(rows or [])
        try:
            ledger.set_account_balance(float(client.balance()))
        except Exception:
            pass                       # the balance is a display, not the check
        return True, (f"read {len(ledger.account_positions)} open position(s) "
                      f"from your account")
    except Exception as exc:
        return False, (f"could not read your account ({exc}). Guard 4 is using "
                       f"the last reading it got, and will not approve a bet on "
                       f"stale information.")


def guards_ok(ledger, entry) -> None:
    """Every existing guard, called rather than restated.

    Two copies of a guard is how guards drift, so nothing here re-implements
    a rule -- it asks the code that already owns it. Raises Refused with a
    sentence he can act on.
    """
    # The kill switch is checked HERE, immediately before submitting, not at
    # startup. A file dropped while the window is open must stop the next one.
    if killswitch.disabled():
        raise Refused(f"Turned off. {killswitch.reason()}")

    stopped, why = ledger.stopped()
    if stopped:
        raise Refused(why)

    # Guard 4 gates SUBMISSION, not only the display. It is the guard that
    # caught his $32 problem, and a wrong running total makes every other
    # guard read a wrong number.
    # ignore=entry: this bet has already been written to the ledger and has
    # NOT been placed yet, so without this it counts as one of our own open
    # bets missing from his account and refuses itself. See _ours_open.
    state, msg = ledger.reconcile(ignore=entry)
    if state in ("disagree", "unchecked"):
        raise Refused(msg)

    # `ignore=entry` throughout: this entry is normally ALREADY in the ledger
    # by the time a practice order is asked for, and its own row must not be
    # read as somebody else having taken the bet or spent the day's money.
    capped = ledger.daily_block(entry.cost_usd, ignore=entry)
    if capped:
        raise Refused(capped)

    ok, why = ledger.may_bet(entry.game_key, entry.signal,
                             next_cost_usd=entry.cost_usd, ignore=entry)
    if not ok:
        raise Refused(why)

    # ⚠ THIRD LOCK, AND THE ONLY ONE THAT CANNOT BE FOOLED BY OUR OWN STATE.
    #
    # "Make sure that type of mistake doesn't happen again." -- him, after the
    # desk put EIGHT orders on one Baltimore market because an entry's status
    # never got updated and the retry loop kept picking it up.
    #
    # The other two locks are the entry's status and a session identity set.
    # Both live inside this tool, and both were wrong or absent at some point
    # tonight. This one asks HIS ACCOUNT: am I already holding this market? An
    # account answer survives a restart, a status bug, a lost set, and a second
    # copy of the window running. It is the only one of the three that could
    # have stopped what actually happened.
    held = 0.0
    for r in (ledger.account_positions or []):
        if str(r.get("ticker") or "") == entry.ticker:
            held += abs(_size_of(r.get("position_fp")))
    if held > 0:
        raise Refused(
            f"you are ALREADY holding {held:g} contracts of "
            f"{entry.team} ({entry.ticker}). This tool will not add to a "
            f"market it is already in. If that position is not from this bot, "
            f"it still will not touch it.")



def submit(ledger, entry, client=None) -> Outcome:
    """Place ONE practice order for an entry the guards have cleared.

    Never invents a fill. A successful HTTP response is not a fill -- that is
    the exact mistake that put a phantom $3.77 in his ledger. The order is
    read back and only what actually happened is recorded. **Unknown is a real
    state and is recorded as unknown**, never quietly as filled.
    """
    guards_ok(ledger, entry)

    own = client is None
    if own:
        client = _client()
    else:
        # An injected client still has to prove where it points. A test double
        # that forgets to look like a recognized Kalshi endpoint must fail.
        verify_demo(client)

    try:
        resp = client.limit_buy(entry.ticker, entry.contracts, entry.price_c)
    except PermissionError as exc:
        # kalshi_client refuses ALL writes while `kalshi-inplay-bot/
        # TRADING_DISABLED` exists -- and it does exist, from 2026-08-03.
        # Reported as itself rather than swallowed. NOT worked around: that
        # file is the tennis strategy's production kill switch and deleting it
        # to make a practice order go through would re-arm real tennis orders.
        raise Refused(
            f"The shared Kalshi client is switched off, so nothing was sent. "
            f"It says: {exc}. That switch belongs to the tennis bot and turning "
            f"it off here would turn real tennis orders back on, so this tool "
            f"will not touch it.") from exc
    except Exception as exc:
        return Outcome(state="rejected", requested=entry.contracts,
                       message=f"Kalshi refused the practice order: {exc}",
                       at_utc=_now())

    order = (resp or {}).get("order") or resp or {}
    order_id = str(order.get("order_id") or "")
    if not order_id:
        return Outcome(state="rejected", requested=entry.contracts,
                       raw=resp or {}, at_utc=_now(),
                       message="Kalshi accepted the request but gave back no "
                               "order number, so there is nothing to check. "
                               "Treat it as not placed and look at the demo "
                               "site before trying again.")

    # ---- read it back. this is the whole point. -----------------------
    try:
        filled, status = client.await_fill(order_id, FILL_WAIT_SECONDS)
    except Exception as exc:
        return Outcome(state="unknown", requested=entry.contracts,
                       order_id=order_id, raw=resp or {}, at_utc=_now(),
                       message=f"The practice order went in as {order_id} but "
                               f"this tool could not read back what happened "
                               f"to it ({exc}). It is NOT recorded as placed. "
                               f"Check the demo site.")

    return _classify(filled, status, order_id, entry.contracts, resp or {})


def _classify(filled, status, order_id, requested, raw) -> Outcome:
    status = str(status or "unknown").lower()
    filled = float(filled or 0.0)
    common = dict(filled=filled, requested=requested, order_id=order_id,
                  raw=raw, at_utc=_now())
    if filled >= requested > 0:
        return Outcome(state="filled",
                       message=f"Practice order filled: all {requested} "
                               f"contracts.", **common)
    if filled > 0:
        return Outcome(state="partial",
                       message=f"Practice order only PART filled: {filled:g} "
                               f"of {requested}. The rest is still sitting on "
                               f"the book.", **common)
    if status in ("canceled", "cancelled"):
        return Outcome(state="cancelled",
                       message="The practice order was cancelled before it "
                               "filled. Nothing is on.", **common)
    if status in ("resting", "open", "pending", "executed"):
        # 'executed' with zero fill is contradictory, so it is not called
        # filled. Resting is the honest reading and the UI says to check.
        return Outcome(state="resting",
                       message=f"Practice order {order_id} is sitting on the "
                               f"book unfilled at {requested} contracts. It "
                               f"may fill later or not at all.", **common)
    return Outcome(state="unknown",
                   message=f"Kalshi came back with a state this tool does not "
                           f"recognise ({status!r}), so nothing is being "
                           f"assumed. Check the demo site for order "
                           f"{order_id}.", **common)
