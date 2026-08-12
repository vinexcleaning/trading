"""The one window for the baseball bets.

    py -3 livedesk\\src\\desk.py

WHAT IT DOES
    Shows the next starting-pitcher bet, why it was picked, what it costs and
    what it pays. One button. The button copies the bet to your clipboard and
    opens the right Kalshi page. **You place it.**

WHAT IT DOES NOT DO, AND CANNOT
    Send an order. There is no key in this folder, no signing code, and no
    write call anywhere in this package. `tests/test_paper_only.py` walks
    every file here and fails if any appears.

    The tennis app needed one-click because it was chasing live in-play
    events where seconds mattered. This is a PRE-GAME strategy: the bets go
    on hours before first pitch. The gap between "this window tells you
    exactly what to do" and "this window does it for you" is about twenty
    seconds of typing, on a bet with hours of runway. Nothing can fire while
    he is asleep.

THE BUTTON NEVER MOVES
    That is his one named complaint about the old app: "sometimes bars will
    get added on, and then it would end up moving the button, which would
    piss me off." So:
      * the alert strip is ALWAYS on screen and always exactly one line tall
      * the card is a fixed-height frame with pack_propagate off
      * the warning line is always there, blank when there is nothing to warn
      * the body is a fixed number of lines, and long text is wrapped and
        truncated to fit rather than being allowed to push anything
      * everything that changes length -- other games, the log, the bet list
        -- is below the button or in another pane, never above it
"""
from __future__ import annotations

import queue
import sys
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import killswitch                                        # noqa: E402
import picks as PICKS                                    # noqa: E402
import prices as PRICES                                  # noqa: E402
from ledger import (ACCOUNT_FLOOR_USD, Entry, Ledger,    # noqa: E402
                    TRAILING_DROP_FRAC)
from money import (BANKROLL_START, STAKE_PCT,            # noqa: E402
                   STAKE_USD, size_bet, usd)

REFRESH_SECONDS = 60
# Longer than this since mlb-paper last wrote a tick and the picks are stale.
# Its runner works on a 300-second loop, so 25 minutes is five missed loops --
# a blip is not an outage, and an outage is not a blip.
SOURCE_STALE_MINUTES = 25

BG_HEAD = "#14532d"
BG_HEAD_STOPPED = "#7f1d1d"
BG_HEAD_OFF = "#3f3f46"

# The permanent line at the bottom. It is not dismissible and it does not
# change. Numbers are the mlb chat's recomputed ones from 2026-08-08, NOT the
# first pass: the fee belongs in the staking base (7.6%, not 7.9%) and in the
# break-even (53.7 out of 100, not 52), which makes 19 wins from 30 less
# impressive, not more.
FOOTER = (
    "  What this is built on — 30 games, 7 to 12 August 2026: won 19, up 7.6 "
    "cents for every dollar laid out. Five approaches were watched at once, so "
    "66 times out of 100 one of five looks this good with nothing behind it.\n"
    "  On the 12 of those games with a professional line to check against, it "
    "was buying about 1.7 cents WORSE than where that line closed. He decided "
    "to run it knowing all of that.")


class Desk(tk.Tk):
    # Fixed geometry. These four numbers are the reason the button holds still.
    CARD_HEIGHT = 440
    CARD_BODY_LINES = 18
    # The six lines of numbers at the bottom of the body are a fixed block, so
    # the reason gets everything else. Sized off the real cards on 2026-08-12:
    # two flagged pitchers wrap to six lines at WRAP_COLS, plus the header and
    # the one-line note, which is ten -- so twelve leaves room and still fits.
    NUMBER_LINES = 6
    # Four, not two. The warning is the most important thing on the card and
    # it was being cut off mid-sentence at two -- which is worse than not
    # warning at all, because a half-read warning reads as a formality.
    WARN_LINES = 4
    WRAP_COLS = 84

    def __init__(self):
        super().__init__()
        self.title("Baseball desk — you place the bet, not this window")
        # Amendment 2 added two more fixed strips above the card (the balance
        # box and the room line), so the window needs the height back or the
        # waiting list is squeezed to nothing. Measured: 954 required.
        self.geometry("1180x900")
        self.minsize(1080, 800)

        self.ledger = Ledger()
        self.events: "queue.Queue[tuple]" = queue.Queue()
        self.picks: list = []
        self.skipped: set = set()          # this session only, not the ledger
        self._announced: set = set()       # signals already raised and chimed
        self._retired_said: set = set()    # games we have already said were dropped
        self.quotes: dict = {}             # ticker -> Quote
        self.source_age = None
        self.last_check = "—"
        self.check_count = 0
        self.paused = False
        self.stop_flag = threading.Event()

        self._build_ui()
        self._render()
        self.after(150, self._pump)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        threading.Thread(target=self._loop, daemon=True).start()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.head = tk.Frame(self, bg=BG_HEAD)
        self.head.pack(fill="x", side="top")
        self.mode_lbl = tk.Label(self.head, text="  YOU PLACE THE BET  ",
                                 bg=BG_HEAD, fg="white",
                                 font=("Segoe UI", 14, "bold"))
        self.mode_lbl.pack(side="left", pady=6)
        self.total_lbl = tk.Label(self.head, text="", bg=BG_HEAD, fg="white",
                                  font=("Segoe UI", 12, "bold"))
        self.total_lbl.pack(side="left", padx=16)
        self.rules_lbl = tk.Label(self.head, bg=BG_HEAD, fg="#d1fae5", text="")
        self.rules_lbl.pack(side="left", padx=10)
        self.pause_btn = tk.Button(self.head, text="pause", command=self._toggle)
        self.pause_btn.pack(side="right", padx=8, pady=4)
        self.beat_lbl = tk.Label(self.head, text="last checked —", bg=BG_HEAD,
                                 fg="#d1fae5")
        self.beat_lbl.pack(side="right", padx=10)

        # Always present, always one line. It used to be that a message
        # appearing shoved the whole window down by its own height, right as
        # you were about to click.
        self.alert_bar = tk.Frame(self, height=32, bg="#27272a")
        self.alert_bar.pack(fill="x", side="top")
        self.alert_bar.pack_propagate(False)
        self.alert_lbl = tk.Label(self.alert_bar, text="  —", anchor="w",
                                  bg="#27272a", fg="#71717a", padx=10,
                                  font=("Segoe UI", 10))
        self.alert_lbl.pack(fill="both", expand=True)
        self._alert_job = None

        # The balance strip. Fixed height like everything above the button.
        # This is the ONLY way an account number gets into this tool: he reads
        # it off Kalshi and types it. Nothing here can fetch it, and that is
        # what keeps "this window cannot send an order" a fact about the
        # folder rather than a promise about code.
        bar = tk.Frame(self, height=34, bg="#1f2937")
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)
        tk.Label(bar, text="  What Kalshi says your balance is:  $",
                 bg="#1f2937", fg="#e5e7eb",
                 font=("Segoe UI", 10)).pack(side="left")
        self.bal_var = tk.StringVar(value=(
            f"{self.ledger.account_balance_usd:.2f}"
            if self.ledger.account_balance_usd is not None else ""))
        e = tk.Entry(bar, textvariable=self.bal_var, width=10,
                     font=("Segoe UI", 11))
        e.pack(side="left", padx=4, pady=4)
        e.bind("<Return>", lambda _ev: self._set_balance())
        tk.Button(bar, text="check", command=self._set_balance).pack(
            side="left", padx=4, pady=3)
        self.recon_lbl = tk.Label(bar, text="", bg="#1f2937", fg="#9ca3af",
                                  anchor="w", font=("Segoe UI", 9))
        self.recon_lbl.pack(side="left", fill="x", expand=True, padx=10)
        self.room_lbl = tk.Label(self, text="", anchor="w", bg="#111827",
                                 fg="#9ca3af", font=("Segoe UI", 9), padx=10)
        self.room_lbl.pack(fill="x", side="top")

        # Packed from the BOTTOM before the body, so the body takes what is
        # left and the footer can never be pushed off or push anything up.
        foot = tk.Frame(self, height=52, bg="#18181b")
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)
        tk.Label(foot, text=FOOTER, anchor="w", justify="left", bg="#18181b",
                 fg="#a1a1aa", font=("Segoe UI", 8)).pack(fill="both", expand=True)

        body = tk.PanedWindow(self, orient="horizontal", sashwidth=6)
        body.pack(fill="both", expand=True, padx=6, pady=6)

        left = tk.Frame(body)
        body.add(left, minsize=600, width=690)
        tk.Label(left, text="The next bet", font=("Segoe UI", 11, "bold")
                 ).pack(anchor="w")
        self.card = tk.Frame(left, height=self.CARD_HEIGHT)
        self.card.pack(fill="x", pady=(0, 6))
        self.card.pack_propagate(False)

        tk.Label(left, text="Other games waiting", font=("Segoe UI", 9, "bold"),
                 fg="#666").pack(anchor="w")
        wrap = tk.Frame(left)
        wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(wrap, highlightthickness=0)
        sb = tk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        self.queue_frame = tk.Frame(canvas)
        self.queue_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.queue_frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        right = tk.Frame(body)
        body.add(right, minsize=380)
        posf = tk.LabelFrame(right, text="Bets you have placed")
        posf.pack(fill="both", pady=4)
        cols = ("game", "team", "size", "price", "state", "P/L")
        self.tree = ttk.Treeview(posf, columns=cols, show="headings", height=9)
        for c, w in zip(cols, (120, 100, 60, 45, 60, 60)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", padx=4, pady=4)
        tk.Button(posf, text="I did NOT actually place this one",
                  command=self._void_selected).pack(anchor="w", padx=4, pady=(0, 6))

        logf = tk.LabelFrame(right, text="Log")
        logf.pack(fill="both", expand=True, pady=4)
        self.log = tk.Text(logf, height=12, state="disabled", bg="#111",
                           fg="#ddd", wrap="word")
        self.log.pack(fill="both", expand=True, padx=4, pady=4)

        self._log("this window cannot send an order. it copies the bet and "
                  "opens the Kalshi page; you place it yourself.")
        self._log(f"one bet per signal, two per game at most. "
                  f"{len(self.ledger.signals_played())} signal(s) are already "
                  f"closed for good.")

    # --------------------------------------------------------------- pieces
    def _log(self, msg: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", f"{time.strftime('%H:%M:%S')}  {msg}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _alert(self, msg: str, level: str = "info") -> None:
        colours = {"info": ("#1e3a5f", "#cfe4ff"),
                   "warn": ("#5c4400", "#ffe9a8"),
                   "error": ("#5c1a1a", "#ffd2d2")}
        bg, fg = colours.get(level, colours["info"])
        if len(msg) > 160:
            msg = msg[:157] + "…"
        self.alert_bar.configure(bg=bg)
        self.alert_lbl.configure(text="  " + msg, bg=bg, fg=fg)
        if self._alert_job:
            self.after_cancel(self._alert_job)
            self._alert_job = None
        if level == "info":
            self._alert_job = self.after(45000, self._clear_alert)

    def _clear_alert(self) -> None:
        self._alert_job = None
        self.alert_bar.configure(bg="#27272a")
        self.alert_lbl.configure(text="  —", bg="#27272a", fg="#71717a")

    def _fit(self, lines, max_lines: int) -> str:
        """Wrap to a known width and cap the line count.

        Clipping is what a fixed-height label does on its own, and clipping
        loses information silently. Truncating on purpose says so with a '…'.
        Either way nothing below moves, which is the point.
        """
        import textwrap
        out = []
        for line in lines:
            if not line:
                out.append("")
                continue
            out.extend(textwrap.wrap(line, self.WRAP_COLS) or [""])
        if len(out) > max_lines:
            out = out[:max_lines - 1] + ["…  (full text in the log)"]
        return "\n".join(out + [""] * (max_lines - len(out)))

    # ---------------------------------------------------------------- state
    def _blocked(self):
        """Why the button is dead, or None. Checked in order of severity."""
        if killswitch.disabled():
            return ("off", killswitch.reason())
        stopped, why = self.ledger.stopped()
        if stopped:
            return ("stopped", why)
        # Guard 4. A number that might be $32 wrong is worse than no number.
        state, msg = self.ledger.reconcile()
        if state in ("disagree", "unchecked"):
            return ("unreconciled", msg)
        return None

    def _available(self) -> list:
        """Picks he could still act on. A pick whose signal has been taken, or
        whose game is full, or whose game holds a losing bet, is gone -- and
        `may_bet` says which so the card can explain itself."""
        out = []
        for p in self.picks:
            if p.game_key in self.skipped:
                continue
            q = self.quotes.get(p.ticker)
            ok, _ = self.ledger.may_bet(p.game_key, p.signal,
                                        q.ask_c if q else None)
            if ok:
                out.append(p)
        return out

    def _set_balance(self) -> None:
        raw = self.bal_var.get().strip().lstrip("$").replace(",", "")
        if not raw:
            self._alert("Type the number Kalshi shows, then press check.", "warn")
            return
        try:
            value = float(raw)
        except ValueError:
            self._alert(f"'{raw}' is not a number.", "warn")
            return
        if value < 0 or value > 100000:
            self._alert(f"${value:.2f} does not look like a Kalshi balance.",
                        "warn")
            return
        self.ledger.set_account_balance(value)
        state, msg = self.ledger.reconcile()
        self._log(f"balance set to ${value:.2f} — {state}: {msg}")
        self._alert(msg, "error" if state == "disagree" else "info")
        self._render()

    # --------------------------------------------------------------- render
    def _render(self) -> None:
        for w in self.card.winfo_children():
            w.destroy()
        for w in self.queue_frame.winfo_children():
            w.destroy()

        blocked = self._blocked()
        kind = blocked[0] if blocked else ""
        colour = {"off": BG_HEAD_OFF, "stopped": BG_HEAD_STOPPED,
                  "unreconciled": "#78350f"}.get(kind, BG_HEAD)
        for widget in (self.head, self.mode_lbl, self.total_lbl, self.rules_lbl,
                       self.beat_lbl):
            widget.configure(bg=colour)
        self.mode_lbl.configure(
            text={"off": "  TURNED OFF  ", "stopped": "  STOPPED  ",
                  "unreconciled": "  NOT CHECKED  "}.get(
                      kind, "  YOU PLACE THE BET  "))
        self.total_lbl.configure(text=self.ledger.summary_line())
        self.rules_lbl.configure(
            text=(f"${STAKE_USD:.2f} a bet ({STAKE_PCT:.0f}% of "
                  f"${BANKROLL_START:.0f})  ·  one bet per signal, two per "
                  f"game at most"))
        self.beat_lbl.configure(
            text=f"last checked {self.last_check}  (#{self.check_count})")

        state, msg = self.ledger.reconcile()
        self.recon_lbl.configure(
            text=msg[:150],
            fg={"disagree": "#fca5a5", "unchecked": "#fcd34d",
                "ok": "#86efac"}.get(state, "#9ca3af"))
        self.room_lbl.configure(text="  " + self.ledger.room_line())

        avail = self._available()
        if blocked:
            self._dead_card(blocked[1])
        elif not avail:
            self._dead_card(self._nothing_text())
        else:
            self._live_card(avail[0])
            self._surface(avail[0])

        self._render_queue(avail[1:])
        self._render_tree()

    def _nothing_text(self) -> str:
        bits = ["No bet right now."]
        if self.source_age is None:
            bits.append("Could not read the baseball bot's file at all — it "
                        "may be mid-write, which is normal, or it may not be "
                        "running.")
        elif self.source_age > SOURCE_STALE_MINUTES:
            bits.append(f"WARNING: the baseball bot has not written anything "
                        f"for {self.source_age:.0f} minutes. It should write "
                        f"every 5. Nothing here is fresh.")
        else:
            bits.append(f"The baseball bot is alive (it wrote "
                        f"{self.source_age:.0f} minutes ago). It just has not "
                        f"found a game where a starting pitcher has done "
                        f"something new enough to bet on.")
        bits.append("")
        bits.append("Most days it finds one or two. Leave this window open.")
        return "\n".join(bits)

    def _surface(self, p) -> None:
        """Come to the front and make a noise when a NEW bet qualifies.

        His reason, and it is a real risk control rather than a convenience:
        *"I don't really wanna be on Kalshi, because then I start looking at
        other games and I'm like oh maybe I'll bet this, and then I lose all
        my money."* So the window finds him; he does not go looking.

        Once per signal. A window that raises itself on every refresh is a
        window he minimises, and then it never reaches him at all.
        """
        if p.signal in self._announced:
            return
        self._announced.add(p.signal)
        try:
            self.deiconify()
            self.lift()
            # -topmost is set and released, not left on: a window that sits
            # permanently over everything gets moved off the screen.
            self.attributes("-topmost", True)
            self.after(1200, lambda: self.attributes("-topmost", False))
            self.bell()
        except tk.TclError:
            pass
        self._log(f"NEW BET on screen: {p.team} — {p.matchup}")

    def _card_shell(self, title: str, title_colour: str = "black"):
        f = tk.LabelFrame(self.card, text=title, font=("Segoe UI", 10, "bold"),
                          fg=title_colour, padx=8, pady=4)
        f.pack(fill="x", padx=4, pady=4)
        return f

    def _dead_card(self, text: str) -> None:
        f = self._card_shell("  nothing to do  ", "#666")
        tk.Label(f, text=" ", height=self.WARN_LINES, anchor="w",
                 font=("Consolas", 9)).pack(fill="x")
        tk.Label(f, text=self._fit(text.split("\n"), self.CARD_BODY_LINES),
                 justify="left", anchor="nw", font=("Consolas", 9), fg="#777",
                 height=self.CARD_BODY_LINES).pack(fill="x")
        row = tk.Frame(f)
        row.pack(fill="x", pady=(6, 2))
        tk.Button(row, text="COPY & OPEN KALSHI", width=30, state="disabled",
                  font=("Segoe UI", 11, "bold"), bg="#3a3a3a", fg="#777"
                  ).pack(side="left")
        tk.Frame(row, width=50).pack(side="left")
        tk.Button(row, text="skip this one", state="disabled").pack(side="left")

    def _live_card(self, p) -> None:
        q = self.quotes.get(p.ticker)
        price = q.ask_c if (q and q.ask_c) else p.quoted_price_c
        bet = size_bet(price)
        start = p.starts_local.strftime("%a %d %b, %H:%M")

        f = self._card_shell(f"  {p.team}   —   {p.matchup}  ")

        warn = p.warning
        if q is None:
            warn = warn or ("No live price read back yet — the "
                            f"{p.quoted_price_c} cents below is what the bot "
                            f"saw when it decided. Check the price on the page "
                            f"before you buy.")
        elif q.ask_c and abs(q.ask_c - p.quoted_price_c) >= 4:
            warn = warn or (f"The price has moved since the bot decided: it saw "
                            f"{p.quoted_price_c} cents, it is {q.ask_c} now.")
        tk.Label(f, text=self._fit([warn] if warn else [""], self.WARN_LINES),
                 justify="left", anchor="nw", font=("Consolas", 9),
                 fg=("#b45309" if warn else "black"), height=self.WARN_LINES
                 ).pack(fill="x")

        lines = ["why this bet:"]
        lines += [f"  · {w}" for w in p.why]
        lines.append("")
        body = self._fit(lines, self.CARD_BODY_LINES - self.NUMBER_LINES)
        numbers = (
            f"   first pitch    {start}   ({p.hours_away:.0f} hours away)\n"
            f"   price now      {price} cents to buy"
            f"{'' if q else '   (what the bot saw — no live price yet)'}\n"
            f"   you put in     ${bet.cost_usd:.2f}   "
            f"({bet.contracts} contracts at {price}c, fee ${bet.fee_usd:.2f})\n"
            f"   if it wins     you make ${bet.win_profit_usd:.2f}\n"
            f"   if it loses    you lose ${bet.lose_usd:.2f}\n"
            f"   to break even  it has to win "
            f"{bet.breakeven_out_of_100:.0f} times out of 100")
        tk.Label(f, text=body + numbers, justify="left", anchor="nw",
                 font=("Consolas", 9), height=self.CARD_BODY_LINES
                 ).pack(fill="x")

        row = tk.Frame(f)
        row.pack(fill="x", pady=(6, 2))
        if not bet.placeable:
            tk.Button(row, text="TOO EXPENSIVE TO SIZE", width=30,
                      state="disabled", font=("Segoe UI", 11, "bold"),
                      bg="#3a3a3a", fg="#777").pack(side="left")
        else:
            tk.Button(row, text=f"COPY & OPEN KALSHI  —  ${bet.cost_usd:.2f}",
                      width=30, bg="#166534", fg="white",
                      font=("Segoe UI", 11, "bold"),
                      command=lambda: self._confirm(p, bet)).pack(side="left")
        # A gap, so a stray second click after the main button lands on nothing.
        tk.Frame(row, width=50).pack(side="left")
        tk.Button(row, text="skip this one",
                  command=lambda: self._skip(p)).pack(side="left")
        tk.Label(row, text="one bet per game — this game closes when you click",
                 fg="#666", font=("Segoe UI", 8)).pack(side="right", padx=6)

    def _render_queue(self, rest) -> None:
        if not rest:
            tk.Label(self.queue_frame, fg="#888", anchor="w", justify="left",
                     text="  Nothing else queued.").pack(fill="x", padx=8, pady=6)
            return
        for p in rest:
            q = self.quotes.get(p.ticker)
            price = q.ask_c if (q and q.ask_c) else p.quoted_price_c
            tk.Label(self.queue_frame, justify="left", anchor="w",
                     font=("Consolas", 9),
                     text=(f"  {p.starts_local.strftime('%a %H:%M')}  "
                           f"{p.team[:22]:<22} {price:>3}c   {p.matchup}")
                     ).pack(fill="x", padx=8, pady=1)

    def _render_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for e in reversed(self.ledger.entries):
            pl = (usd(e.pnl_usd) if e.status in ("won", "lost")
                  else ("—" if e.status == "void" else "open"))
            self.tree.insert("", "end", iid=e.ticker, values=(
                e.game_key[5:], e.team[:16], f"${e.cost_usd:.2f}",
                f"{e.price_c}c", e.status, pl))

    # --------------------------------------------------------------- actions
    def _skip(self, p) -> None:
        """This session only. Skipping is not betting, so the game is NOT
        closed for good -- it comes back if you restart. Only a click on the
        real button closes a game permanently."""
        self.skipped.add(p.game_key)
        self._log(f"skipped {p.matchup} for this session")
        self._render()

    def _confirm(self, p, bet) -> None:
        blocked = self._blocked()
        if blocked:
            self._alert(blocked[1], "error")
            self._render()
            return
        q = self.quotes.get(p.ticker)
        ok, why = self.ledger.may_bet(p.game_key, p.signal, q.ask_c if q else None)
        if not ok:
            self._alert(f"{p.matchup}: {why}", "warn")
            self._render()
            return

        ok = messagebox.askokcancel(
            "Copy this bet and open Kalshi?",
            f"{p.team} to win — {p.matchup}\n\n"
            f"Buy {bet.contracts} contracts at {bet.price_c} cents.\n"
            f"That is ${bet.cost_usd:.2f} out, ${bet.win_profit_usd:.2f} back "
            f"if it wins, ${bet.lose_usd:.2f} gone if it loses.\n\n"
            f"This window does NOT place it. It copies the details and opens "
            f"the page — you place it there.\n\n"
            f"This exact bet is then closed for good. If the bot later finds a "
            f"genuinely different reason on the same game it may offer once "
            f"more — two per game is the hard limit, and never on top of a "
            f"bet that is losing.")
        if not ok:
            return

        detail = (f"{p.team} YES — {bet.contracts} contracts at "
                  f"{bet.price_c}c or better (${bet.cost_usd:.2f}) — "
                  f"{p.ticker}")
        try:
            self.clipboard_clear()
            self.clipboard_append(detail)
            self.update_idletasks()
        except tk.TclError as e:
            self._log(f"could not reach the clipboard ({e}) — the details are "
                      f"in the log line below, copy them by hand")

        url = PRICES.market_url(p.event_ticker)
        try:
            webbrowser.open(url)
        except Exception as e:
            self._log(f"could not open the browser ({e}) — the page is {url}")

        # Written the moment he clicks. If he then does not actually place it,
        # the "I did NOT actually place this one" button voids the money while
        # LEAVING THE GAME CLOSED. Closing on the click is the whole of Guard 1;
        # closing only on a confirmed fill would let a hesitated click come
        # back around and become a second bet on the same game.
        self.ledger.add(Entry(
            game_key=p.game_key, ticker=p.ticker, event_ticker=p.event_ticker,
            team=p.team, matchup=p.matchup, side=p.side, price_c=bet.price_c,
            contracts=bet.contracts, cost_usd=bet.cost_usd, fee_usd=bet.fee_usd,
            win_profit_usd=bet.win_profit_usd, lose_usd=bet.lose_usd,
            starts_utc=p.starts_utc, signal=p.signal,
            confirmed_utc=datetime.now().astimezone().isoformat(timespec="seconds"),
            why=list(p.why)))
        self._log(f"COPIED {detail}")
        self._log(f"opened {url}")
        self._alert(f"Copied. Paste it on the Kalshi page and buy "
                    f"{bet.contracts} at {bet.price_c}c. {p.matchup} is now "
                    f"closed for good.", "info")
        self._render()

    def _void_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            self._alert("Click a row in the list first.", "warn")
            return
        for e in self.ledger.entries:
            if e.ticker == sel[0] and e.status == "open":
                if messagebox.askokcancel(
                        "Mark as not placed?",
                        f"{e.team} — {e.matchup}\n\n"
                        f"This takes ${e.cost_usd:.2f} back out of the running "
                        f"total, because you never actually placed it.\n\n"
                        f"The game stays closed either way — it will not be "
                        f"offered again."):
                    e.status = "void"
                    e.pnl_usd = 0.0
                    e.note = "marked not placed by hand"
                    self.ledger.save()
                    self._log(f"voided {e.matchup} — not actually placed")
                    self._render()
                return
        self._alert("That one is already settled or already voided.", "warn")

    def _toggle(self) -> None:
        self.paused = not self.paused
        self.pause_btn.configure(text="resume" if self.paused else "pause")
        self._log("paused — nothing is being refreshed" if self.paused
                  else "resumed")

    # ------------------------------------------------------------ background
    def _loop(self) -> None:
        while not self.stop_flag.is_set():
            if not self.paused:
                try:
                    self._work()
                except Exception as e:                # never kill the thread
                    self.events.put(("log", f"refresh failed: {e}"))
            self.stop_flag.wait(REFRESH_SECONDS)

    def _work(self) -> None:
        age = PICKS.source_age_minutes()
        retired = []
        found = PICKS.pending_picks(retired=retired)
        self.events.put(("source", age))
        self.events.put(("picks", found))
        # A card that silently vanishes is indistinguishable from a bug. Say
        # it once per game, not on every refresh.
        for matchup, why in retired:
            if matchup not in self._retired_said:
                self._retired_said.add(matchup)
                self.events.put(("log", f"DROPPED {matchup} — the baseball bot "
                                        f"has changed its mind: {why}"))

        # Live prices for what is actually on offer. One read per game, not
        # per rung -- there is one market per club and we hold at most one.
        # Every game still on offer, not the first few: a card that says
        # "no live price" only because this loop stopped counting is a lie
        # about the market. MLB plays at most 15 a day and this is one small
        # GET each, once a minute.
        wanted = [p for p in found if p.game_key not in self.skipped][:16]
        got = {}
        for p in wanted:
            try:
                got[p.ticker] = PRICES.quote(p.ticker)
            except RuntimeError as e:
                self.events.put(("log", f"price read failed for {p.team}: {e}"))
        if got:
            self.events.put(("quotes", got))

        # Settle anything finished. Kalshi's own result for the exact ticker
        # bought is the authority -- not a score read from anywhere else.
        for e in self.ledger.open_entries():
            try:
                q = PRICES.quote(e.ticker)
            except RuntimeError:
                continue
            if q.is_final:
                won = ((q.result == "yes") == (e.side.upper() == "YES"))
                self.events.put(("settle", (e.ticker, won)))

        self.events.put(("checked", time.strftime("%H:%M:%S")))

    def _pump(self) -> None:
        dirty = False
        try:
            while True:
                kind, *rest = self.events.get_nowait()
                if kind == "log":
                    self._log(rest[0])
                elif kind == "source":
                    self.source_age = rest[0]
                    dirty = True
                elif kind == "picks":
                    self.picks = rest[0]
                    dirty = True
                elif kind == "quotes":
                    self.quotes.update(rest[0])
                    dirty = True
                elif kind == "settle":
                    ticker, won = rest[0]
                    e = self.ledger.settle(ticker, won)
                    if e:
                        self._log(f"{'WON' if won else 'LOST'} {e.matchup} — "
                                  f"{e.team} — {usd(e.pnl_usd)}")
                        self._alert(
                            f"{e.team} {'won' if won else 'lost'}. "
                            f"{usd(e.pnl_usd)}. Running total for baseball: "
                            f"{usd(self.ledger.realised_usd())}.",
                            "info" if won else "warn")
                        stopped, reason = self.ledger.stopped()
                        if stopped:
                            self._alert(reason, "error")
                            self._log(reason)
                    dirty = True
                elif kind == "checked":
                    self.last_check = rest[0]
                    self.check_count += 1
                    dirty = True
        except queue.Empty:
            pass
        if dirty:
            self._render()
        self.after(200, self._pump)

    def _on_close(self) -> None:
        self.stop_flag.set()
        self.destroy()


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    Desk().mainloop()


if __name__ == "__main__":
    main()
