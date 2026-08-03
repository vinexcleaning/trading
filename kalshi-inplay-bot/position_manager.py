"""
position_manager.py — the stop-loss / take-profit engine.

Kalshi has no native stop orders for event contracts: a sell limit placed
below the current price fills instantly instead of waiting. So a stop loss
has to be synthetic — something watches the price and sends a sell only
once the line is breached. That's this module.

    entry   -> a resting limit sell goes out immediately (take profit).
               That one is real and rests on the exchange; it fills whether
               or not this program is running.
    stop    -> tracked HERE, in memory. Checked every poll. When the bid
               drops to or below the stop, this fires a sell.

What that means in practice, and it matters:
  * Close the app and the stop is GONE. The take-profit sell survives on
    Kalshi; the stop does not. Nothing is watching.
  * A stop only fires as fast as the poll interval. Between polls the price
    can gap straight through your line, and you get filled lower than the
    stop price, or not at all if the book empties.
  * This sells at the best available bid, so a thin book means a worse fill.
It is a real risk-reduction tool, not a guarantee. Position sizing is still
what actually limits a loss.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

from kalshi_client import KalshiClient, Market

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_state.json")


@dataclass
class ManagedPosition:
    ticker: str
    player: str
    contracts: int
    entry_price: int
    stop_price: int
    target_price: int
    opened_at: float = field(default_factory=time.time)

    stopped_out: bool = False
    stop_fill_price: Optional[int] = None
    note: str = ""
    # how it ended: "" while open, else "target hit" / "stopped" /
    # "closed elsewhere" / "stop failed". Keeps the UI honest — a take-profit
    # that filled is a WIN and must never be labelled a failure.
    outcome: str = ""

    # the resting take-profit on the exchange. Must be cancelled the moment
    # the position goes away, or it becomes an order to open a SHORT.
    take_profit_order_id: Optional[str] = None

    # so the app can re-offer this trade if the price recovers after a stop
    rearm_above: Optional[int] = None
    rearm_notified: bool = False
    # 3 Aug: feed the re-entry cooldown and per-event re-entry cap in
    # tennis_engine.Config. `stopped_out_at` is a unix timestamp; `reentries`
    # counts how many times this event has already been bought back.
    stopped_out_at: Optional[float] = None
    reentries: int = 0

    @property
    def age_sec(self) -> int:
        return int(time.time() - self.opened_at)


class PositionManager:
    """Watches open positions and fires synthetic stop-loss sells.

    Call `check(markets)` on every scan tick with fresh market data. It
    returns a list of human-readable events describing anything it did.
    """

    def __init__(self, client: KalshiClient,
                 on_event: Optional[Callable[[str], None]] = None,
                 max_hold_minutes: int = 0):
        self.client = client
        self.positions: dict[str, ManagedPosition] = {}
        self.on_event = on_event or (lambda msg: None)
        # 0 disables it. Anything else closes a position that has gone
        # nowhere for that long — see check().
        self.max_hold_minutes = max_hold_minutes
        # ticker -> {"at": unix_ts_of_last_stop, "reentries": int}
        #
        # Added 3 Aug. This deliberately does NOT live on ManagedPosition:
        # check() retires a stopped-out position two passes after it closes,
        # so anything stored on the position is gone within about a minute —
        # far short of the 15-minute re-entry cooldown it is supposed to
        # enforce. The ledger has to outlive the position it describes.
        self.stop_history: dict[str, dict] = {}

    def reentry_state(self, now: Optional[float] = None) -> dict:
        """ticker -> {"ago_sec", "reentries"} for every market that has
        stopped us out. Feeds the re-entry cooldown and the per-event
        re-entry cap in tennis_engine.evaluate()."""
        now = now or time.time()
        return {tk: {"ago_sec": int(now - h["at"]), "reentries": h["reentries"]}
                for tk, h in self.stop_history.items()}

    def track(self, ticker: str, player: str, contracts: int,
              entry_price: int, stop_price: int, target_price: int,
              take_profit_order_id: Optional[str] = None) -> ManagedPosition:
        # Buying back a market that previously stopped us out is a re-entry;
        # count it so max_reentries_per_event can bite on the next one.
        if ticker in self.stop_history:
            self.stop_history[ticker]["reentries"] += 1
        pos = ManagedPosition(ticker=ticker, player=player, contracts=contracts,
                              entry_price=entry_price, stop_price=stop_price,
                              target_price=target_price,
                              take_profit_order_id=take_profit_order_id)
        self.positions[ticker] = pos
        self.save()
        self.on_event(f"tracking {player}: stop {stop_price}c, target {target_price}c "
                      f"(stop resumes if you reopen the app, but nothing watches "
                      f"it while the app is closed)")
        return pos

    def untrack(self, ticker: str) -> None:
        self.positions.pop(ticker, None)
        self.save()

    # ---- persistence -------------------------------------------------
    # Stops live in this process, so closing the app used to silently
    # abandon them. Writing them down means a restart (or a crash) can
    # pick the watch back up instead of leaving a position unguarded.
    def save(self) -> None:
        try:
            with open(STATE_FILE, "w") as f:
                json.dump({"positions": [asdict(p) for p in self.positions.values()],
                           # Persisted so a restart cannot reset the cooldown.
                           # Closing and reopening the app was otherwise a way
                           # to buy straight back into a market that had just
                           # stopped you out.
                           "stop_history": self.stop_history},
                          f, indent=1)
        except OSError as e:
            self.on_event(f"couldn't save state: {e}")

    def load(self, held: Optional[dict[str, float]] = None) -> int:
        """Restore tracked stops. If `held` is given (what the exchange says
        you own), anything you no longer hold is dropped rather than revived."""
        if not os.path.exists(STATE_FILE):
            return 0
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            self.on_event(f"couldn't read saved state: {e}")
            return 0

        hist = data.get("stop_history")
        if isinstance(hist, dict):
            self.stop_history = hist

        restored = 0
        for raw in data.get("positions", []):
            try:
                pos = ManagedPosition(**raw)
            except TypeError:
                continue
            if pos.stopped_out:
                continue
            if held is not None:
                owned = held.get(pos.ticker, 0.0)
                if owned <= 0:
                    self.on_event(f"{pos.player}: saved stop dropped — you no "
                                  f"longer hold this position")
                    continue
                pos.contracts = min(pos.contracts, int(owned))
            self.positions[pos.ticker] = pos
            restored += 1
            self.on_event(f"resumed watching {pos.player}: stop {pos.stop_price}c, "
                          f"target {pos.target_price}c")
        return restored

    def check(self, markets: dict[str, Market],
              held: Optional[dict[str, float]] = None) -> list[str]:
        """One pass over tracked positions. Fires stops that have breached.

        `held` maps ticker -> contracts actually owned right now. It is the
        safety interlock: the take-profit sell rests on the exchange and can
        fill while this app knows nothing about it, and a stop fired against
        contracts you no longer hold does not close anything — it opens a
        SHORT. So we never sell more than the exchange says we own."""
        events: list[str] = []
        for ticker, pos in list(self.positions.items()):
            if pos.stopped_out:
                continue
            m = markets.get(ticker)
            if m is None:
                continue

            if held is not None:
                owned = held.get(ticker, 0.0)
                if owned <= 0:
                    pos.stopped_out = True
                    # gone while at/above target = the take-profit filled: a win
                    hit_target = m.yes_bid >= pos.target_price - 2
                    pos.outcome = "target hit" if hit_target else "closed elsewhere"
                    pos.note = pos.outcome
                    msg = (f"{pos.player}: {'TARGET HIT — take-profit filled' if hit_target else 'position closed'}"
                           f". Stop retired — nothing left to protect.")
                    self.on_event(msg)
                    events.append(msg)
                    # A take-profit still resting with no position behind it is
                    # an order to go SHORT. Pull it.
                    cancel_msg = self._cancel_take_profit(pos)
                    if cancel_msg:
                        events.append(cancel_msg)
                    continue
                if owned < pos.contracts:
                    pos.contracts = int(owned)   # partial exit happened elsewhere

            # sell into the bid — that's what we'd actually receive
            if m.yes_bid > 0 and m.yes_bid <= pos.stop_price:
                events.append(self._fire_stop(pos, m))
                continue

            # Time stop. A position that has reached neither target nor stop
            # after this long is not working, and it is holding a slot that a
            # live signal cannot use. Krivoshchekov sat open 4h45m on 27 Jul
            # and cost $2.67 while blocking every re-entry behind it.
            #
            # Losers only. A position trading ABOVE entry is working — it is
            # climbing toward the 95c target, and the data says 94% of markets
            # that reach 92c settle at 100. Timing that out would sell exactly
            # the trades worth keeping.
            if (self.max_hold_minutes
                    and pos.age_sec >= self.max_hold_minutes * 60
                    and 0 < m.yes_bid < pos.entry_price):
                msg = self._fire_stop(pos, m, reason="time")
                pos.note = f"held {pos.age_sec // 60}min with no result"
                events.append(msg)

        # Retire anything that has finished. A closed position sitting in the
        # table under a heading that says "Open positions" is actively
        # misleading — it read as three live positions while Kalshi correctly
        # showed none. Keep them one pass so the outcome is visible, then drop.
        for ticker, pos in list(self.positions.items()):
            if pos.stopped_out and pos.outcome:
                if getattr(pos, "_shown_closed", False):
                    del self.positions[ticker]
                else:
                    pos._shown_closed = True

        if events:
            self.save()
        return events

    def _cancel_take_profit(self, pos: ManagedPosition) -> str:
        """Pull the resting take-profit. Safe to call more than once."""
        if not pos.take_profit_order_id:
            return ""
        oid, pos.take_profit_order_id = pos.take_profit_order_id, None
        try:
            self.client.cancel(oid)
            msg = f"cancelled the {pos.target_price}c take-profit on {pos.player}"
        except Exception as e:
            # 404 means the order is already gone — it filled, or was cancelled
            # earlier. That is the normal path when the take-profit is what
            # closed the position, so it must not read like an emergency.
            if "404" in str(e) or "not found" in str(e).lower():
                msg = (f"{pos.player}: {pos.target_price}c take-profit was already "
                       f"gone (it filled or was cancelled) — nothing to clean up")
            else:
                msg = (f"COULD NOT CANCEL the {pos.target_price}c take-profit on "
                       f"{pos.player}: {e} — CANCEL IT ON KALSHI YOURSELF, otherwise it "
                       f"can fill and open a short.")
        self.on_event(msg)
        return msg

    def _fire_stop(self, pos: ManagedPosition, m: Market,
                   reason: str = "stop") -> str:
        """Sell out at whatever the book will take. Marks the position
        stopped either way so we never loop on a failing order.

        The resting take-profit is cancelled FIRST: on Kalshi it reserves the
        very contracts we're trying to sell, so leaving it there can make the
        stop fail — and if the stop does work, the leftover sell becomes a
        short waiting to happen."""
        pos.stopped_out = True
        # 3 Aug: this was `stop_price + 2`. Two cents above your own stop is
        # ordinary bid/ask jitter, not a recovery, so in a falling market it
        # re-armed within seconds and the bot bought the same collapsing
        # contract again — three times on SAGLEV on 28 Jul, at 49c, 31c and
        # 19c. Re-arm only if the price gets back to where we ENTERED, which
        # is the only level at which the original thesis is intact again.
        pos.rearm_above = max(pos.entry_price, pos.stop_price + 2)
        pos.stopped_out_at = time.time()
        prev = self.stop_history.get(pos.ticker, {})
        self.stop_history[pos.ticker] = {
            "at": pos.stopped_out_at,
            "reentries": prev.get("reentries", 0),
        }
        self._cancel_take_profit(pos)
        try:
            # price at the bid so it crosses and fills now, rather than resting
            self.client.limit_sell(pos.ticker, pos.contracts, max(1, m.yes_bid))
            pos.stop_fill_price = m.yes_bid
            if reason == "time":
                pos.outcome = "time stop"
                msg = (f"TIME STOP {pos.player}: sold {pos.contracts} at "
                       f"~{m.yes_bid}c after {pos.age_sec // 60}min going "
                       f"nowhere (entry {pos.entry_price}c). The {pos.stop_price}c "
                       f"stop was NOT hit — this closed on time, not on price.")
            else:
                pos.outcome = "stopped"
                msg = (f"STOP FIRED {pos.player}: sold {pos.contracts} at "
                       f"~{m.yes_bid}c (stop was {pos.stop_price}c, entry "
                       f"{pos.entry_price}c)")
        except Exception as e:
            pos.note = str(e)
            pos.outcome = "stop failed"
            msg = (f"STOP FAILED {pos.player} at {m.yes_bid}c: {e} — "
                   f"CHECK KALSHI YOURSELF, you may still be holding this")
        self.on_event(msg)
        return msg

    def adopt_orphans(self, markets: dict[str, Market], held: dict[str, float],
                      stop_drop: int, target_price: int,
                      rows: Optional[list[dict]] = None) -> list[str]:
        """Start watching any position you HOLD but nothing is protecting.

        This closes a real hole. A limit buy that doesn't fill inside the
        await_fill window is abandoned by the placing code — but the order is
        good-till-cancelled, so it stays resting on Kalshi and can fill minutes
        later. You then own contracts with no stop and no take-profit, and
        because the ticker isn't tracked the scanner will happily offer you the
        same player again. That is exactly how Tyler Zink ended up unmanaged.

        Entry price is taken from the exchange's cost basis when it is
        available; otherwise we anchor the stop to the current bid, which
        protects the position from here even if it can't reconstruct history.
        """
        events: list[str] = []
        by_ticker = {r.get("ticker"): r for r in (rows or [])}

        # Sells already resting on the exchange, so we adopt them instead of
        # placing a competing second one.
        existing_sells: dict[str, dict] = {}
        try:
            for o in self.client.resting_orders():
                if o.get("action") == "sell" and o.get("ticker"):
                    existing_sells.setdefault(o["ticker"], o)
        except Exception:
            pass

        for ticker, qty in held.items():
            if qty <= 0 or ticker in self.positions:
                continue
            m = markets.get(ticker)
            if m is None or m.yes_bid <= 0:
                continue

            entry = None
            row = by_ticker.get(ticker) or {}
            for key in ("market_exposure_dollars", "total_traded_dollars",
                        "market_exposure", "total_traded"):
                raw = row.get(key)
                if raw in (None, ""):
                    continue
                try:
                    dollars = float(raw)
                except (TypeError, ValueError):
                    continue
                if dollars > 0:
                    cents = dollars / float(qty) * 100.0
                    if key.endswith(("_exposure", "_traded")):   # already cents
                        cents = float(raw) / float(qty)
                    if 1 <= cents <= 99:
                        entry = int(round(cents))
                        break

            anchored = entry is None
            if anchored:
                entry = m.yes_bid          # can't know the fill; protect from here

            tgt = min(99, max(target_price, m.yes_bid + 1))
            pos = self.track(
                ticker=ticker, player=(m.title.split(" win the ")[0]
                                       .replace("Will ", "")[:28] or ticker),
                contracts=int(qty), entry_price=entry,
                stop_price=max(1, entry - stop_drop),
                target_price=tgt,
            )

            # Rest the take-profit too — an EXIT on contracts you already own,
            # not a new position, and it survives the app closing unlike the
            # stop.
            #
            # But ONLY if there isn't already a sell resting on this market.
            # Adopting a position that still had an old take-profit from a
            # previous session used to stack a second one; the first to fill
            # closed the position and left the other live with nothing behind
            # it — a naked short waiting to happen, and a log full of orphan
            # warnings. Adopt the existing order instead of competing with it.
            tp_note = ""
            existing = existing_sells.get(ticker)
            if existing:
                pos.take_profit_order_id = existing.get("order_id", "")
                px = existing.get("yes_price_dollars")
                tp_note = (f" A sell was already resting"
                           + (f" at {round(float(px)*100)}c" if px else "")
                           + " — adopted that rather than stacking another.")
            elif not self.client.read_only:
                try:
                    resp = self.client.limit_sell(ticker, int(qty), tgt)
                    pos.take_profit_order_id = (
                        (resp.get("order") or resp).get("order_id", ""))
                    tp_note = f" Take-profit now resting at {tgt}c."
                except Exception as e:
                    tp_note = (f" COULD NOT rest a take-profit ({e}) — set one "
                               f"on Kalshi yourself.")

            msg = (f"ADOPTED UNWATCHED POSITION {pos.player}: you hold "
                   f"{int(qty)} contracts that nothing was protecting. "
                   f"Stop set at {pos.stop_price}c"
                   + (f" (anchored to the current {m.yes_bid}c bid — the real "
                      f"entry price was not recoverable)" if anchored
                      else f" from a {entry}c entry")
                   + "." + tp_note)
            self.on_event(msg)
            events.append(msg)

        if events:
            self.save()
        return events

    def rearm_candidates(self, markets: dict[str, Market]) -> list[ManagedPosition]:
        """Positions that stopped out but whose price has recovered — the
        'he's going back up, want back in?' case. Returns them for the app
        to re-offer; does NOT re-enter on its own.

        Reports each recovery ONCE. It used to return the same position on
        every scan, which buried the log in hundreds of identical lines and
        hid the messages that actually mattered. The flag clears if the price
        falls back below the trigger, so a genuine second recovery still
        gets announced."""
        out = []
        for pos in self.positions.values():
            if not pos.stopped_out or pos.rearm_above is None:
                continue
            m = markets.get(pos.ticker)
            if not m:
                continue
            if m.yes_ask >= pos.rearm_above:
                if not pos.rearm_notified:
                    pos.rearm_notified = True
                    out.append(pos)
            elif pos.rearm_notified:
                pos.rearm_notified = False   # dropped back; arm it again
        return out
