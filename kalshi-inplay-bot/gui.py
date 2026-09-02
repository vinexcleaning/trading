"""
gui.py — desktop window for the Kalshi tennis bot.

Finds its own trades. It cross-references every open Kalshi tennis market
against every live match on the Apify feed, scores each one with
tennis_engine, and shows you the best ones ranked. You click PLACE TRADE
and it sends the buy, rests a take-profit sell on the exchange, and starts
watching a synthetic stop loss.

    python gui.py                            # demo account
    python gui.py --watch                    # real prices, orders blocked
    python gui.py --live --bankroll 115 --stake-pct 5   # real money

Read this before using --live:

  * One click places the trade. There is no second confirm. Check the mode
    banner at the top before you click.
  * The take-profit sell is a real resting order on Kalshi. It fills whether
    or not this app is running.
  * The stop loss is NOT on the exchange. Kalshi has no stop orders. This
    app watches the price and sells when your line breaks — so the stop
    only exists while this window is open, and only fires as fast as the
    scan interval. A fast drop can fill you well below your stop.

Moving to another machine: copy the folder, `pip install requests
cryptography curl_cffi`, set KALSHI_KEY_ID / KALSHI_KEY_PATH.
Live scores come from Sofascore now — free, no token needed.
"""

from __future__ import annotations

import argparse
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from autoscan import Candidate, find_candidates
from notify import Notifier
from kalshi_client import KalshiClient, _fp
from sofascore_feed import SofaScoreClient as LiveScoreClient
from position_manager import PositionManager
from tennis_engine import Config


MODE_COLORS = {"DEMO": "#2d6a4f", "WATCH": "#495057", "LIVE": "#9d0208"}


class App(tk.Tk):
    def __init__(self, cfg: Config, client: KalshiClient, live: LiveScoreClient,
                 mode: str, interval: int):
        super().__init__()
        self.title("Kalshi Tennis Bot")
        self.geometry("1080x720")

        self.cfg = cfg
        self.client = client
        self.live = live
        self.mode = mode
        self.interval = interval

        self.events: "queue.Queue[tuple]" = queue.Queue()
        self.candidates: list[Candidate] = []
        self.rejected: list = []
        self.dismissed: set[str] = set()
        # tickers with an order in flight, and ones with a bid already resting.
        # Without these, an impatient double-click stacks duplicate buys that
        # all fill together if the price ever comes back to them.
        self.placing: set[str] = set()
        self.resting_buys: set[str] = set()
        # What the EXCHANGE says you own. Kept separate from pm.positions
        # because a position can be held without being tracked — see
        # adopt_orphans. Cards are filtered against this too, so you can never
        # be offered a player you already hold even if adoption hasn't run.
        self.held_tickers: set[str] = set()
        # order_id -> when we first saw it resting, for the 60s cancel rule
        self._buy_seen: dict[str, float] = {}
        # orphan sell orders already reported, so the warning fires once
        self._orphan_warned: set[str] = set()
        # consecutive failed scans, for deciding when to push an alert
        self._scan_errors = 0
        # last $ milestone we pushed, so crossing +$10 alerts once, not
        # every scan while it hovers there
        self._pnl_milestone = 0
        self._pnl_notified_at = 0.0        # P&L when we last sent a ping
        self._pnl_ping_times: list[float] = []   # for the 2-per-hour cap
        self.notifier = Notifier()
        self.pm = PositionManager(client, on_event=self._pm_event,
                                  max_hold_minutes=cfg.max_hold_minutes)

        self.scan_stop = threading.Event()
        self.scan_thread: Optional[threading.Thread] = None
        self.last_scan = "—"
        self.scan_count = 0
        self._last_source = ""
        self.state_restored = False
        self.pnl_baseline: Optional[float] = None   # realized P&L when this session opened
        self.session_realized = 0.0
        self.session_unrealized = 0.0
        # Realised session P&L as a % of bankroll — drives the daily-loss
        # circuit breaker in tennis_engine.evaluate().
        self.session_pnl_pct = 0.0

        self._build_ui()
        # draw the empty card straight away — the first scan takes ~30-60s and
        # the panel used to sit blank until it finished
        self._render_cards()
        self._refresh_balance()
        self._restore_state()
        self.after(150, self._poll_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start_scan()

    def _restore_state(self, held: Optional[dict] = None) -> None:
        """Pick stops back up after a restart, but only for positions the
        exchange agrees you still hold. If the read fails we leave
        state_restored False so a later scan retries — a transient blip at
        startup must not mean your stops go unwatched all session."""
        if held is None and self.client.authenticated:
            try:
                held = {p["ticker"]: float(p.get("position_fp", 0) or 0)
                        for p in self.client.positions()}
            except Exception as e:
                self._log(f"couldn't read positions to restore stops ({e}) — "
                          f"will retry on the next scan")
                return
        n = self.pm.load(held=held)
        self.state_restored = True
        if n:
            self._log(f"restored {n} stop(s) from your last session")
            self._refresh_positions()

    # ---- background helper ------------------------------------------------
    def _bg(self, fn: Callable, *args, on_done: Optional[Callable] = None, **kwargs) -> None:
        def run():
            try:
                self.events.put(("done", on_done, fn(*args, **kwargs), None))
            except Exception as e:
                self.events.put(("done", on_done, None, e))
        threading.Thread(target=run, daemon=True).start()

    # idle appearance of the always-present alert strip
    ALERT_IDLE_BG = "#2b2b2b"
    ALERT_IDLE_TEXT = "  —"

    # --- P&L notification gate -------------------------------------------
    # Three separate brakes, because one alone was not enough:
    #   1. levels      — only whole $10 steps are worth a message at all
    #   2. hysteresis  — after pinging at $10 it must reach ~$13 or fall to
    #                    ~$7 before pinging again, so P&L hovering on the
    #                    boundary cannot buzz on every scan
    #   3. rate limit  — at most 2 messages an hour no matter what
    PNL_HYSTERESIS = 3.0        # dollars of movement required before re-ping
    PNL_MAX_PER_HOUR = 2

    def _maybe_ping_pnl(self, pnl: float) -> None:
        step = self.cfg.notify_pnl_every or 10
        level = int(pnl / step) * step          # truncates toward zero
        if level == 0:
            return
        if level == self._pnl_milestone:
            return                               # same level, already said
        if abs(pnl - self._pnl_notified_at) < self.PNL_HYSTERESIS:
            return                               # jitter around a boundary
        now = time.time()
        self._pnl_ping_times = [t for t in self._pnl_ping_times
                                if now - t < 3600]
        if len(self._pnl_ping_times) >= self.PNL_MAX_PER_HOUR:
            self._pnl_milestone = level          # remember it, stay silent
            return
        self._pnl_ping_times.append(now)
        self._pnl_milestone = level
        self._pnl_notified_at = pnl
        self.notifier.milestone(level, pnl, 0.0)

    def _alert(self, msg: str, level: str = "info") -> None:
        """Show a message in the alert strip instead of a modal dialog.

        Non-blocking and never steals focus, so it cannot cause a misclick on
        the trade button underneath. Warnings stay until something replaces
        them; informational ones clear themselves after 30 seconds.
        """
        colours = {"info": ("#1e3a5f", "#cfe4ff"),
                   "warn": ("#5c4400", "#ffe9a8"),
                   "error": ("#5c1a1a", "#ffd2d2")}
        bg, fg = colours.get(level, colours["info"])
        # one line only — the strip's height is fixed, so anything longer
        # would be clipped rather than wrapped. Full text is always in the log.
        if len(msg) > 150:
            msg = msg[:147] + "…"
        self.alert_bar.configure(bg=bg)
        self.alert_lbl.configure(text=msg, bg=bg, fg=fg)
        if self._alert_job:
            self.after_cancel(self._alert_job)
            self._alert_job = None
        if level == "info":
            self._alert_job = self.after(30000, self._clear_alert)

    def _clear_alert(self) -> None:
        """Back to the idle strip. Never unpacks it — the space stays
        reserved so nothing below ever moves."""
        self._alert_job = None
        self.alert_bar.configure(bg=self.ALERT_IDLE_BG)
        self.alert_lbl.configure(text=self.ALERT_IDLE_TEXT,
                                 bg=self.ALERT_IDLE_BG, fg="#777")

    def _pm_event(self, msg: str) -> None:
        """Everything the position manager says goes to the log; the ones that
        moved real money or left something unprotected also go to your phone."""
        self.events.put(("log", msg))
        # Routine wins and stops are LOG ONLY. They used to text on every one,
        # which on a 20-stop day is 20 messages saying nothing you can act on.
        # The phone is now reserved for the P&L pings and for things that mean
        # something is actually wrong and money may be unprotected.
        if msg.startswith(("STOP FAILED", "ADOPTED UNWATCHED")):
            self.notifier.stop_fired(msg)

    def _log(self, msg: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", f"{time.strftime('%H:%M:%S')}  {msg}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ---- UI -----------------------------------------------------------------
    def _build_ui(self) -> None:
        colour = MODE_COLORS.get(self.mode, "#333")
        top = tk.Frame(self, bg=colour)
        top.pack(fill="x")
        tk.Label(top, text=f"  {self.mode}  ", bg=colour, fg="white",
                 font=("Segoe UI", 15, "bold")).pack(side="left", pady=6)
        self.balance_lbl = tk.Label(top, text="balance: —", bg=colour, fg="white",
                                    font=("Segoe UI", 11))
        self.balance_lbl.pack(side="left", padx=16)
        tk.Label(top, text=f"bankroll ${self.cfg.bankroll:.2f} | {self.cfg.stake_pct}% per trade",
                 bg=colour, fg="white").pack(side="left", padx=16)
        self.status_lbl = tk.Label(top, text="starting…", bg=colour, fg="#ddd")
        self.status_lbl.pack(side="left", padx=16)
        self.scan_btn = tk.Button(top, text="pause", command=self._toggle_scan)
        self.scan_btn.pack(side="right", padx=8, pady=4)
        # heartbeat: a quiet app and a hung app look identical without this
        self.heartbeat_lbl = tk.Label(top, text="last scan —", bg=colour, fg="#ddd")
        self.heartbeat_lbl.pack(side="right", padx=10)
        self.pnl_lbl = tk.Label(top, text="session P&L  —", bg=colour, fg="white",
                                font=("Segoe UI", 12, "bold"))
        self.pnl_lbl.pack(side="right", padx=14)

        # Alert strip. Replaces the pop-up dialogs that used to appear in the
        # middle of the screen and demand a click: those steal focus while you
        # are mid-click on a trade, which is a good way to misclick something
        # you didn't mean to. This says the same thing, in place, without
        # blocking anything. Every alert is also written to the log.
        # The strip is ALWAYS on screen and always exactly one line tall. It
        # used to be packed only when there was something to say, so every
        # message shoved the whole window down by its height — right as you
        # were about to click the trade button. Reserving the space means the
        # layout never moves; only the text and colour change. The fixed-height
        # frame also stops a long message from wrapping to two lines and
        # shifting things that way instead.
        self.alert_bar = tk.Frame(self, height=32, bg=self.ALERT_IDLE_BG)
        self.alert_bar.pack(fill="x", side="top")
        self.alert_bar.pack_propagate(False)
        self.alert_lbl = tk.Label(self.alert_bar, text=self.ALERT_IDLE_TEXT,
                                  anchor="w", justify="left",
                                  bg=self.ALERT_IDLE_BG, fg="#777", padx=10,
                                  font=("Segoe UI", 10))
        self.alert_lbl.pack(fill="both", expand=True)
        self._alert_job = None

        body = tk.PanedWindow(self, orient="horizontal", sashwidth=6)
        body.pack(fill="both", expand=True, padx=6, pady=6)
        self.alert_anchor = body

        # left: the trades it found
        left = tk.Frame(body)
        body.add(left, minsize=560, width=640)

        # Trades live in a FIXED pane at the top so the button never moves.
        # The rejected-match list scrolls separately underneath — it used to
        # push the button around as its length changed.
        tk.Label(left, text="Best trades right now",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.cards = tk.Frame(left, height=300)
        self.cards.pack(fill="x", pady=(0, 6))
        self.cards.pack_propagate(False)

        tk.Label(left, text="Not qualifying", font=("Segoe UI", 9, "bold"),
                 fg="#666").pack(anchor="w")
        wrap = tk.Frame(left)
        wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(wrap, highlightthickness=0)
        sb = tk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        self.rejects = tk.Frame(canvas)
        self.rejects.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.rejects, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # right: positions + log
        right = tk.Frame(body)
        body.add(right, minsize=380)

        posf = tk.LabelFrame(right, text="Open positions (stop watched by this app)")
        posf.pack(fill="both", pady=4)
        cols = ("player", "qty", "entry", "stop", "target", "state")
        self.pos_tree = ttk.Treeview(posf, columns=cols, show="headings", height=7)
        for c, w in zip(cols, (110, 40, 50, 50, 55, 80)):
            self.pos_tree.heading(c, text=c)
            self.pos_tree.column(c, width=w, anchor="center")
        self.pos_tree.pack(fill="both", padx=4, pady=4)

        logf = tk.LabelFrame(right, text="Log")
        logf.pack(fill="both", expand=True, pady=4)
        self.log = tk.Text(logf, height=14, state="disabled", bg="#111", fg="#ddd", wrap="word")
        self.log.pack(fill="both", expand=True, padx=4, pady=4)

        if self.mode == "LIVE":
            self._log("LIVE — one click places a real order, no second confirm.")
        self._log("stop losses are app-side: they stop working if you close this window.")

    # ---- balance --------------------------------------------------------
    def _refresh_balance(self) -> None:
        if not self.client.authenticated:
            self.balance_lbl.configure(text="balance: no API key")
            return
        self._bg(self.client.balance, on_done=self._on_balance)

    def _on_balance(self, bal, err) -> None:
        self.balance_lbl.configure(
            text=f"balance: ${bal:.2f}" if not err else "balance: error")

    # ---- the scan loop -----------------------------------------------------
    def _start_scan(self) -> None:
        self.scan_stop.clear()
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()
        self.scan_btn.configure(text="pause")

    def _toggle_scan(self) -> None:
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_stop.set()
            self.scan_btn.configure(text="resume")
            self.events.put(("status", "paused"))
        else:
            self._start_scan()

    def _scan_loop(self) -> None:
        while not self.scan_stop.is_set():
            try:
                markets = self.client.tennis_markets()
                by_ticker = {m.ticker: m for m in markets}

                # what we actually own, straight from the exchange — the stop
                # logic must never act on a position that has already closed
                held: dict[str, float] = {}
                pos_rows: list = []
                if self.client.authenticated:
                    try:
                        pos_rows = self.client.positions()
                        held = {p["ticker"]: float(p.get("position_fp", 0) or 0)
                                for p in pos_rows}
                    except Exception:
                        held = None   # unknown: fall back to price-only stops

                # a failed startup restore gets another go once positions read
                if not self.state_restored and held is not None:
                    self.events.put(("restore", held))

                # Never offer a player the exchange says you already hold,
                # tracked or not.
                if held is not None:
                    self.events.put(("held_tickers",
                                     {t for t, q in held.items() if q > 0}))

                # Adopt anything you HOLD that nothing is protecting. A limit
                # buy that misses the await_fill window is abandoned by the
                # placing code but keeps resting on Kalshi, so it can fill
                # minutes later leaving you with contracts, no stop and no
                # take-profit — and the scanner will offer you that player
                # again because the ticker isn't tracked. Runs before check()
                # so a newly adopted stop is evaluated on this very pass.
                if held and self.state_restored:
                    self.pm.adopt_orphans(
                        by_ticker, held,
                        stop_drop=self.cfg.favorite_exit_drop,
                        target_price=self.cfg.favorite_target_price,
                        rows=pos_rows)

                # stops first — protecting money beats finding new trades
                self.pm.check(by_ticker, held=held)

                # Backstop: any resting SELL on a market you hold nothing in is
                # an order to open a short. Catches orphans this app didn't
                # create — e.g. left over from a previous session that crashed.
                if held is not None and self.client.authenticated:
                    try:
                        orders = self.client.resting_orders()
                        buys: dict[str, int] = {}
                        for o in orders:
                            tk = o.get("ticker", "")
                            if o.get("action") == "sell":
                                if held.get(tk, 0.0) <= 0:
                                    # Say it once per order, not once per scan.
                                    # This used to repeat every 20 seconds and
                                    # buried every message that mattered.
                                    oid_s = o.get("order_id", tk)
                                    if oid_s not in self._orphan_warned:
                                        self._orphan_warned.add(oid_s)
                                        self.events.put((
                                            "log",
                                            f"WARNING orphan sell order on {tk} "
                                            f"({o.get('remaining_count_fp')} @ "
                                            f"${o.get('yes_price_dollars')}) but you hold "
                                            f"none — cancel it on Kalshi or it can open "
                                            f"a short."))
                            elif o.get("action") == "buy":
                                buys[tk] = buys.get(tk, 0) + 1
                                # v3 spec section 4: cancel/re-price an unfilled
                                # entry after 60s. A buy that rests indefinitely
                                # can fill twenty minutes later on a thesis that
                                # has expired — the set score that justified it
                                # is long gone. This is the CAUSE of the orphan
                                # problem; adopt_orphans only cleans up after it.
                                oid = o.get("order_id", "")
                                first = self._buy_seen.setdefault(oid, time.time())
                                age = time.time() - first
                                if (self.cfg.cancel_unfilled_after_sec
                                        and age >= self.cfg.cancel_unfilled_after_sec):
                                    try:
                                        self.client.cancel(oid)
                                        self._buy_seen.pop(oid, None)
                                        self.events.put((
                                            "log",
                                            f"CANCELLED unfilled buy on {tk} after "
                                            f"{int(age)}s — the price never came back "
                                            f"and a late fill would be on a stale score."))
                                    except Exception as e:
                                        self.events.put((
                                            "log", f"could not cancel stale buy on "
                                                   f"{tk}: {e}"))
                        # forget orders that are no longer resting
                        live_ids = {o.get("order_id", "") for o in orders}
                        for gone in [k for k in self._buy_seen if k not in live_ids]:
                            self._buy_seen.pop(gone, None)
                        # keep the button's warning state honest with reality
                        self.events.put(("resting_buys", set(buys)))
                        for tk, n in buys.items():
                            if n > 1:
                                self.events.put((
                                    "log",
                                    f"WARNING {n} duplicate buy orders resting on {tk} — "
                                    f"they can ALL fill together. Cancel the extras on Kalshi."))
                    except Exception:
                        pass
                for pos in self.pm.rearm_candidates(by_ticker):
                    self.events.put(("log", f"{pos.player} recovered to "
                                            f"{by_ticker[pos.ticker].yes_ask}c after stopping out "
                                            f"— it may re-appear below if it still qualifies"))
                    self.dismissed.discard(pos.ticker)

                open_n = 0
                if self.client.authenticated:
                    try:
                        open_n = len(self.client.positions())
                    except Exception:
                        pass

                # session P&L: realized straight from Kalshi's own numbers,
                # plus mark-to-market on whatever is still open
                if self.client.authenticated:
                    try:
                        # Portfolio value = cash + every open position marked to
                        # the bid. Session P&L is just how much that has moved.
                        #
                        # The old version summed realized_pnl_dollars and diffed
                        # a baseline. Two things broke it: a settled market DROPS
                        # OFF the positions list, so the total fell and P&L went
                        # negative on winning days; and unrealised only counted
                        # positions this app happened to be tracking, so anything
                        # opened in an earlier session was invisible. This matches
                        # the number Kalshi shows you.
                        cash = self.client.balance()
                        held = self.client.positions()
                        pos_val = 0.0
                        for p in held:
                            mk = by_ticker.get(p.get("ticker", ""))
                            if mk and mk.yes_bid > 0:
                                pos_val += _fp(p.get("position_fp")) * mk.yes_bid / 100
                        portfolio = cash + pos_val
                        if self.pnl_baseline is None:
                            self.pnl_baseline = portfolio
                        realized = portfolio - self.pnl_baseline
                        unreal = pos_val
                        self.events.put(("portfolio", (cash, pos_val, portfolio)))
                        self.events.put(("pnl", (realized, 0.0)))
                        # ⚠ THIS COMMENT WAS WRONG AND IS CORRECTED (audit
                        # 2026-09-01, `tennis` mailbox 022). It said the
                        # daily-loss circuit breaker "no longer halts trading".
                        # IT DOES. Config re-enabled max_daily_loss_pct=15.0 on
                        # 3 Aug; this value is passed to evaluate() at line ~541
                        # as `daily_pnl_pct`, and tennis_engine.py:350 calls
                        # bad() on it, which blocks. Behaviour is safe; only the
                        # comment was misleading.
                        #
                        # ⚠ AND IT IS PER-SESSION, NOT PER-DAY. `pnl_baseline`
                        # is set when the app opens (just above), so restarting
                        # resets the "daily" limit. Moot while trading is off,
                        # and a real gap the day it comes back on.
                        if self.cfg.bankroll > 0:
                            self.session_pnl_pct = realized / self.cfg.bankroll * 100.0

                        # P&L pings. `realized` is already the full session
                        # move (portfolio now minus portfolio at open), so it
                        # must NOT have position value added to it — doing that
                        # made every scan look like a new milestone and is why
                        # the phone was buzzing every minute.
                        self._maybe_ping_pnl(realized)
                    except Exception:
                        pass
                    # keep the balance live: it used to be fetched once, so a
                    # single hiccup left "error" on screen for the whole session
                    try:
                        self.events.put(("balance", self.client.balance()))
                    except Exception:
                        pass

                self.events.put(("status", "fetching live scores…"))
                # Names we were stopped out of that have since recovered may
                # use the reserved re-entry slots.
                # A market we were stopped out of stays flagged as a re-entry
                # even after check() retires the position record, so the
                # re-entry guards keep applying instead of the market quietly
                # reverting to "fresh entry" a minute after it stopped us out.
                reentry = ({p.ticker for p in self.pm.positions.values()
                            if p.stopped_out and p.rearm_above is not None}
                           | set(self.pm.stop_history))
                # How long ago each market stopped us out, and how many times
                # we have already bought it back. Drives the cooldown and the
                # per-event re-entry cap added 3 Aug — without this the guards
                # would sit at their defaults and never fire. Read from the
                # manager's own ledger, not from the positions dict, because
                # a stopped-out position is retired within about a minute.
                reentry_info = self.pm.reentry_state()
                cands, notes, rejected = find_candidates(
                    self.cfg, markets, self.live, open_positions=open_n,
                    client=self.client, reentry_tickers=reentry,
                    daily_pnl_pct=self.session_pnl_pct,
                    reentry_info=reentry_info)
                self.events.put(("scanned", time.strftime("%H:%M:%S")))
                if self.live.source and self.live.source != self._last_source:
                    self._last_source = self.live.source
                    self.events.put(("log", f"live scores now coming from "
                                            f"{self.live.source}"
                                            + (f" — {self.live.last_error}"
                                               if self.live.last_error else "")))
                if open_n >= self.cfg.max_open_positions:
                    self.events.put(("log", f"you hold {open_n} positions (limit "
                                            f"{self.cfg.max_open_positions}) — everything is "
                                            f"blocked until you close some"))
                self.events.put(("rejected", rejected))
                self.events.put(("candidates", cands))
                self.events.put(("status", notes[-1] if notes else ""))
                for n in notes[:-1]:
                    self.events.put(("log", n))
                # The scan completed. Tell the dead-man switch we're alive —
                # if these stop arriving, healthchecks.io alerts you, which is
                # the only way to learn the laptop lost power (a dead process
                # cannot send its own alert).
                self.notifier.heartbeat()
                self._scan_errors = 0
            except Exception as e:
                self.events.put(("log", f"scan error: {e}"))
                # One failed scan is a blip — Wi-Fi hiccups happen and the
                # client already retries reads. Several in a row means it is
                # not recovering, and nobody is sitting in front of it.
                self._scan_errors += 1
                if self._scan_errors in (3, 12):
                    self.notifier.crashed(
                        f"{self._scan_errors} consecutive scan failures.\n"
                        f"Last error: {e}")
            self.scan_stop.wait(self.interval)

    # ---- cards -------------------------------------------------------------
    def _render_cards(self) -> None:
        for w in self.cards.winfo_children():
            w.destroy()
        for w in self.rejects.winfo_children():
            w.destroy()

        shown = [c for c in self.candidates if c.ticker not in self.dismissed
                 and c.ticker not in self.pm.positions
                 and c.ticker not in self.held_tickers]
        if shown:
            # only the top trade gets the button, so it is always in one place
            self._build_card(0, shown[0])
            if len(shown) > 1:
                tk.Label(self.cards, fg="#666", anchor="w",
                         text=f"  +{len(shown) - 1} more qualifying "
                              f"(shown after you act on this one)").pack(fill="x", padx=8)
        else:
            # Same frame, same rows, same button geometry as a real card — just
            # inert. Keeps the panel from jumping around as trades come and go,
            # and shows exactly where to look.
            checked = (f"{len(self.rejected)} live match(es) checked at {self.last_scan}"
                       if self.last_scan != "—" else
                       "first scan running… (can take up to a minute)")
            f = self._card_frame(" waiting for a trade ")
            self._card_body(f, f"no match currently passes the rules\n"
                               f"{checked}\n\n"
                               f"the button below lights up when one does",
                            fg="#888")
            row = self._card_button_row(f)
            tk.Button(row, text="PLACE TRADE", bg="#3a3a3a", fg="#777",
                      font=("Segoe UI", 10, "bold"), width=26,
                      state="disabled").pack(side="left")
            tk.Frame(row, width=60).pack(side="left")
            tk.Button(row, text="buy again", font=("Segoe UI", 9),
                      state="disabled").pack(side="left")
            tk.Button(row, text="dismiss",
                      state="disabled").pack(side="right", padx=6)

        self._render_rejects()

    def _render_rejects(self) -> None:
        """Why each live match was turned down. Lives in its own scroll pane
        so its length can never move the PLACE TRADE button."""
        if not self.rejected:
            tk.Label(self.rejects, fg="#888", justify="left", anchor="w",
                     text="  Nothing lined up. A trade needs a match BOTH listed on\n"
                          "  Kalshi AND live on the score feed. If 'matched up' is 0,\n"
                          "  no live match has a Kalshi market open.").pack(fill="x", padx=8, pady=6)
            return
        tk.Label(self.rejects, fg="#666", anchor="w", font=("Segoe UI", 8),
                 text="closest to qualifying first — your rules in tennis_engine.py"
                 ).pack(fill="x", padx=8)
        for r in self.rejected[:14]:
            why = "\n".join(f"       x  {t}" for t in r.reasons)
            tk.Label(self.rejects, justify="left", anchor="w", font=("Consolas", 9),
                     text=f"  {r.player[:26]:<26} {r.ask:>3}c  sets {r.sets}\n{why}"
                     ).pack(fill="x", padx=8, pady=2)

    # The PLACE TRADE button must land on the exact same pixel whether a trade
    # is showing or not, and whatever a card's text length happens to be — you
    # park the mouse there and click. So every card is built from these three
    # helpers, and the body is a FIXED number of text lines.
    CARD_BODY_LINES = 15

    def _card_frame(self, title: str) -> tk.LabelFrame:
        f = tk.LabelFrame(self.cards, text=title,
                          font=("Segoe UI", 10, "bold"), padx=6, pady=4)
        f.pack(fill="x", padx=4, pady=5)
        return f

    def _card_body(self, parent: tk.Widget, text: str, fg: str = "black") -> None:
        tk.Label(parent, justify="left", anchor="nw", font=("Consolas", 9),
                 height=self.CARD_BODY_LINES, fg=fg, text=text).pack(fill="x")

    def _card_button_row(self, parent: tk.Widget) -> tk.Frame:
        row = tk.Frame(parent)
        row.pack(fill="x", pady=(6, 2))
        return row

    def _build_card(self, rank: int, c: Candidate) -> None:
        d, s = c.decision, c.score
        f = self._card_frame(f"#{rank + 1}   {c.player}   —   {s.match_title}")

        why = "\n".join(f"   {'+' if k == 'ok' else '!' if k == 'warn' else 'x'} {t}"
                        for k, t in d.reasons)
        self._card_body(f, (f"why this trade:\n{why}\n\n"
                       f"   live score   {s.sets_won}-{s.sets_lost}  ({s.status}, {s.age_sec}s old)\n"
                       f"   pre-match    {'favorite' if s.was_favorite else 'underdog'}"
                       f"   ·   setup: {d.setup.value}\n"
                       f"   market       {c.market.yes_bid}/{c.market.yes_ask}c"
                       f"   spread {c.market.spread}c\n"
                       f"\n"
                       f"   BUY          {d.contracts} @ {d.entry_price}c   (${d.cost:.2f})\n"
                       f"   take profit  {d.target_price}c   (rests on Kalshi)\n"
                       f"   stop loss    {d.exit_price}c   (watched by this app only)\n"
                       f"   risk         ${d.loss_if_exit:.2f} if stopped ·"
                       f" ${d.loss_if_held:.2f} if it goes to zero\n"
                       f"   need to win  {d.breakeven_with_exit:.0f}% with stop ·"
                       f" {d.breakeven_holding:.0f}% holding"))

        row = self._card_button_row(f)

        # Two SEPARATE buttons, never one that changes meaning under the cursor.
        # The main button always sits in the same place and can only ever open a
        # first position. Deliberately doubling up is a different button, set
        # apart, so spam-clicking the main one can't reach it.
        in_flight = c.ticker in self.placing
        has_resting = c.ticker in self.resting_buys

        if in_flight:
            tk.Button(row, text="PLACING… please wait", bg="#555", fg="white",
                      font=("Segoe UI", 10, "bold"), state="disabled",
                      width=26).pack(side="left")
        elif has_resting:
            tk.Button(row, text="bid already resting", bg="#3a3a3a", fg="#aaa",
                      font=("Segoe UI", 10, "bold"), state="disabled",
                      width=26).pack(side="left")
        else:
            tk.Button(row, text=f"PLACE TRADE  —  ${d.cost:.2f}", bg="#9d0208",
                      fg="white", font=("Segoe UI", 10, "bold"), width=26,
                      command=lambda: self._place(c)).pack(side="left")

        # gap, so a stray click after the main button lands on nothing
        tk.Frame(row, width=60).pack(side="left")

        tk.Button(row, text="buy again", font=("Segoe UI", 9),
                  state=("normal" if (has_resting and not in_flight) else "disabled"),
                  command=lambda: self._place(c, again=True)).pack(side="left")
        tk.Button(row, text="dismiss",
                  command=lambda: self._dismiss(c.ticker)).pack(side="right", padx=6)

    def _dismiss(self, ticker: str) -> None:
        self.dismissed.add(ticker)
        self._render_cards()

    # ---- trading ------------------------------------------------------------
    def _place(self, c: Candidate, again: bool = False) -> None:
        """Buy, then rest the take-profit. These are two separate orders and
        the second one can fail on its own — if that happens you are HOLDING
        the position with no exit resting, so we start the stop watch anyway
        and say so loudly rather than reporting a clean failure."""
        d = c.decision

        # Guard 1: one order at a time per market. Extra clicks do nothing.
        if c.ticker in self.placing:
            self._log(f"already placing {c.player} — ignoring the extra click")
            return
        # Guard 2: the main button can NEVER stack a second bid, even if the
        # UI is mid-redraw when the click lands. Doubling up requires the
        # separate "buy again" button, which sets again=True.
        if c.ticker in self.resting_buys and not again:
            self._log(f"{c.player} already has a bid resting — use 'buy again' "
                      f"if you really want a second one")
            return
        # Guard 3: never buy a player the EXCHANGE says you already hold.
        # pm.positions is not enough — a late fill leaves you holding contracts
        # the bot never tracked, which is how Zink and Maria were offered twice.
        if c.ticker in self.held_tickers and not again:
            self._log(f"{c.player}: you already hold this position on Kalshi. "
                      f"Use 'buy again' if you genuinely want to add to it.")
            return
        if again:
            if not messagebox.askokcancel(
                    "Place a SECOND order?",
                    f"You already have a buy for {c.player} at {d.entry_price}c "
                    f"RESTING and unfilled.\n\n"
                    f"This adds ANOTHER {d.contracts} contracts (${d.cost:.2f}). "
                    f"If the price comes back down, BOTH fill — double the "
                    f"position you planned.\n\n"
                    f"Place a second order anyway?"):
                return
        self.placing.add(c.ticker)
        self._render_cards()          # button redraws disabled

        def work():
            resp = self.client.limit_buy(c.ticker, d.contracts, d.entry_price)
            order_id = (resp.get("order") or resp).get("order_id", "")

            # Nothing may be sold until the buy really fills. A take-profit
            # sell on contracts you don't own is not an exit — it opens a
            # SHORT, and it would trigger exactly when the match turns your way.
            filled, status = self.client.await_fill(order_id) if order_id else (0.0, "unknown")
            if filled <= 0:
                return ("not_filled", status, order_id, 0.0)

            qty = int(filled)
            try:
                sresp = self.client.limit_sell(c.ticker, qty, d.target_price)
                tp_id = (sresp.get("order") or sresp).get("order_id", "")
            except Exception as sell_err:
                return ("bought_only", sell_err, order_id, filled)
            return ("ok", tp_id, order_id, filled)

        def done(result, err):
            self.placing.discard(c.ticker)   # always, on every path
            if err:
                # buy itself failed — nothing was opened, nothing to protect
                self._log(f"ORDER FAILED {c.player}: {err} — nothing was bought")
                self._alert(f"ORDER FAILED — {c.player}: {err}. Nothing was bought.",
                            "error")
                self.notifier.order_problem(
                    f"Buy failed for {c.player}: {err}. Nothing was bought.")
                self._render_cards()
                return

            state, detail, order_id, filled = result

            if state == "not_filled":
                # The price moved away before the order landed. Nothing is
                # owned, so no take-profit and no stop — just a live bid.
                self.resting_buys.add(c.ticker)
                self._render_cards()
                self._log(f"NOT FILLED {c.player}: your bid of {d.entry_price}c is resting "
                          f"(status {detail}). The market moved away. No take-profit and no "
                          f"stop were set, because you don't own anything yet.")
                self._alert(
                    f"NOT FILLED — {c.player}: your {d.contracts} @ {d.entry_price}c "
                    f"is resting on Kalshi, the price moved away. Nothing is owned yet, "
                    f"so no stop and no take-profit. It auto-cancels in "
                    f"{self.cfg.cancel_unfilled_after_sec}s if it doesn't fill.", "info")
                self._refresh_balance()
                return

            qty = int(filled)
            self.pm.track(c.ticker, c.player, qty, d.entry_price,
                          d.exit_price, d.target_price,
                          take_profit_order_id=(detail if state == "ok" else None))

            if state == "bought_only":
                self._log(f"PARTIAL {c.player}: BOUGHT {qty} @ {d.entry_price}c but the "
                          f"take-profit sell FAILED ({detail}). Holding with no resting exit "
                          f"— set {d.target_price}c on Kalshi yourself.")
                # Stays on screen until something replaces it — you are holding
                # a position with no exit resting on the exchange, which is the
                # one state you should not scroll past.
                self.notifier.order_problem(
                    f"HOLDING WITH NO EXIT: bought {qty} of {c.player} @ "
                    f"{d.entry_price}c but the take-profit failed. Place a sell "
                    f"at {d.target_price}c on Kalshi yourself.")
                self._alert(
                    f"HOLDING WITH NO EXIT — {c.player}: bought {qty} @ "
                    f"{d.entry_price}c but the take-profit FAILED ({detail}). "
                    f"Place a sell at {d.target_price}c on Kalshi yourself. "
                    f"The app-side stop at {d.exit_price}c is watching, but it "
                    f"dies if this window closes.", "warn")
            else:
                self._log(f"FILLED {c.player}: {qty} @ {d.entry_price}c, "
                          f"take-profit resting at {d.target_price}c, stop watching {d.exit_price}c")

            self._refresh_positions()
            self._render_cards()
            self._refresh_balance()

        self._bg(work, on_done=done)

    def _refresh_positions(self) -> None:
        self.pos_tree.delete(*self.pos_tree.get_children())
        for t, p in self.pm.positions.items():
            state = p.outcome or ("open" if not p.stopped_out else "closed")
            self.pos_tree.insert("", "end", iid=t, values=(
                p.player[:16], p.contracts, f"{p.entry_price}c",
                f"{p.stop_price}c", f"{p.target_price}c", state))

    # ---- event pump ---------------------------------------------------------
    def _poll_events(self) -> None:
        try:
            while True:
                kind, *rest = self.events.get_nowait()
                if kind == "done":
                    on_done, result, err = rest
                    if on_done:
                        on_done(result, err)
                elif kind == "log":
                    self._log(rest[0])
                elif kind == "status":
                    self.status_lbl.configure(text=rest[0])
                elif kind == "scanned":
                    self.last_scan = rest[0]
                    self.scan_count += 1
                    self.heartbeat_lbl.configure(
                        text=f"last scan {self.last_scan}  (#{self.scan_count})")
                elif kind == "portfolio":
                    cash, pos_val, total = rest[0]
                    # show the same number Kalshi shows: cash AND positions
                    self.balance_lbl.configure(
                        text=f"portfolio: ${total:.2f}   (cash ${cash:.2f} + "
                             f"positions ${pos_val:.2f})")
                elif kind == "balance":
                    self.balance_lbl.configure(text=f"cash: ${rest[0]:.2f}")
                elif kind == "restore":
                    self._restore_state(held=rest[0])
                elif kind == "pnl":
                    self.session_realized, self.session_unrealized = rest[0]
                    tot = self.session_realized + self.session_unrealized
                    colour = "#4ade80" if tot > 0.005 else ("#f87171" if tot < -0.005 else "white")
                    open_bit = (f"   (open {self.session_unrealized:+.2f})"
                                if abs(self.session_unrealized) > 0.005 else "")
                    self.pnl_lbl.configure(
                        text=f"session P&L  {tot:+.2f}{open_bit}", fg=colour)
                elif kind == "resting_buys":
                    self.resting_buys = rest[0]
                elif kind == "held_tickers":
                    self.held_tickers = rest[0]
                elif kind == "rejected":
                    self.rejected = rest[0]
                elif kind == "candidates":
                    self.candidates = rest[0]
                    self._render_cards()
                    self._refresh_positions()
        except queue.Empty:
            pass
        self.after(150, self._poll_events)

    def _on_close(self) -> None:
        live_stops = [p for p in self.pm.positions.values() if not p.stopped_out]
        if live_stops:
            names = ", ".join(p.player for p in live_stops)
            if not messagebox.askokcancel(
                    "Stops will stop working",
                    f"{len(live_stops)} position(s) still have an app-side stop loss:\n\n"
                    f"{names}\n\n"
                    f"Closing this window means nothing is watching them. The "
                    f"take-profit sells stay resting on Kalshi, but the stops do not.\n\n"
                    f"Close anyway?"):
                return
        self.scan_stop.set()
        self.destroy()


def main() -> None:
    # Windows consoles default to cp1252, which cannot encode a player name
    # like "Aleksandar Vukić" — printing one raises UnicodeEncodeError and
    # kills the scan thread mid-loop. Force UTF-8 before anything prints.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true", help="real prices, read-only")
    ap.add_argument("--live", action="store_true", help="real money")
    ap.add_argument("--bankroll", type=float, default=110.0)
    ap.add_argument("--stake-pct", type=float, default=5.0)
    # Scores are free now (Sofascore), so scan as often as you like. 20s keeps
    # score age inside the 30s staleness gate; the old 60s default existed
    # only because every miss of the cache cost an Apify actor run.
    ap.add_argument("--interval", type=int, default=20,
                    help="seconds between scans")
    args = ap.parse_args()

    if args.live:
        print("\n  *** LIVE MODE — REAL MONEY, ONE-CLICK ORDERS ***")
        if input("  type LIVE to continue > ").strip() != "LIVE":
            print("  cancelled")
            return

    client = KalshiClient(demo=not (args.live or args.watch), read_only=args.watch)
    cfg = Config(bankroll=args.bankroll, stake_pct=args.stake_pct)
    live = LiveScoreClient()
    mode = "LIVE" if args.live else ("WATCH" if args.watch else "DEMO")

    App(cfg, client, live, mode, args.interval).mainloop()


if __name__ == "__main__":
    main()
