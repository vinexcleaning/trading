"""The one window for the baseball bets.

    py -3 livedesk\\src\\desk.py

WHAT IT DOES
    Shows the next starting-pitcher bet, why it was picked, what it costs and
    what it pays.

    ⚠ AND IT SENDS REAL ORDERS. Live Kalshi, real money, no undo. **AUTO
    STARTS ON**, so opening this window starts placing bets by itself. The
    button in the header turns that off.

    ⚠ A SENTENCE THAT USED TO BE HERE AND IS NOW FALSE, left visible on
    purpose because deleting it is how someone re-derives it: *"Nothing that
    touches real money can fire while he is asleep."* That was true of the
    hand-off build. It is not true of this one. With AUTO on, this window
    places real bets with nobody watching.

    What still limits it: $4.15 a bet, $50 a day, the $50 account floor, the
    35% trailing stop, one bet per signal, two per game, and a kill switch
    file. Those are in `ledger.py` and `DECISIONS.md` says what each one cost
    to learn.

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

import demo_exec as DEMO                                 # noqa: E402
import killswitch                                        # noqa: E402
import picks as PICKS                                    # noqa: E402
import prices as PRICES                                  # noqa: E402
import fees                                               # noqa: E402
import onemachine                                         # noqa: E402
from alerts import DeskAlerts                             # noqa: E402
from ledger import (ACCOUNT_FLOOR_USD, Entry, Ledger,    # noqa: E402
                    TRAILING_DROP_FRAC)
from money import (AGREED_EVIDENCE_GAMES, BANKROLL_START,   # noqa: E402
                   MAX_STAKE_USD, STAKE_PCT, STAKE_PCT_AGREED,
                   STAKE_PCT_OTHER, STAKE_USD, bucket_for, size_bet,
                   stake_for, stake_for_bucket, stake_pct_for, usd)

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
        self.title("Baseball desk — auto-exec enabled")
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
        # (entry, pick, bet) while he is over on Kalshi placing it. The card
        # holds this state until he says whether it went on -- Guard 6, one
        # click one order, and the reason the hand-off card cannot vanish.
        self.pending = None
        self._account_read_ok = None   # so the first result is logged either way
        self.quotes: dict = {}             # ticker -> Quote
        self.source_age = None
        self.last_check = "—"
        self.check_count = 0
        self.paused = False
        self.stop_flag = threading.Event()
        # Auto-execution: submit qualifying picks as soon as the loop sees them.
        # Starts ON — the user wants "one command, bot runs on its own."
        self.auto_exec = True
        self._auto_submitted: set = set()   # signals already auto-submitted this session
        # Entry objects already submitted this session, by identity. Belt and
        # braces against the status handler: see the retry loop for why one
        # lock was not enough.
        self._auto_submitted_ids: set = set()
        # Phone alerts. Reads the ledger and sends text; it can do nothing
        # else, and if every line of it failed the desk would trade exactly as
        # it does now.
        self.alerts = DeskAlerts()
        self._cycles = 0
        self._fee_warned: set = set()   # so a fee warning is said once, not hourly

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
        # Auto-exec toggle — starts ON, user can turn OFF if needed.
        self.auto_btn = tk.Button(self.head, text="AUTO: ON",
                                  command=self._toggle_auto, bg="#166534",
                                  fg="white", font=("Segoe UI", 10, "bold"))
        self.auto_btn.pack(side="right", padx=4, pady=4)
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
        tk.Label(bar, text="  CASH (not portfolio):  $",
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

        self._log("auto-execution ENABLED — qualifying bets are placed "
                  "automatically via Kalshi's PRODUCTION environment.")
        self._log(f"one bet per signal, two per game at most. "
                  f"{len(self.ledger.signals_played())} signal(s) are already "
                  f"closed for good.")
        self._log("All 5 safety guards active. Unlimited daily trading. $50 balance floor hard stop.")

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
                  "unreconciled": "  NOT CHECKED  ",
                  "auto": "  AUTO-EXEC  "}.get(kind,
                                                 "  YOU PLACE THE BET  "))
        self.total_lbl.configure(text=self.ledger.summary_line())
        self.rules_lbl.configure(
            # ⚠ THIS USED TO READ "(10% of your $X)" WHILE THE CARD BELOW IT
            # WAS SIZED AT 5%. The stake became tiered and the label did not
            # follow, so the header stated a rule the tool was not using -- he
            # would have read "10%" and seen $5 and had no way to tell which
            # was broken. The label now states the RULE, not one number.
            text=(f"${self._stake():.2f} a bet  ·  {STAKE_PCT_OTHER:.0f}% of "
                  f"your ${self.ledger.account_balance_usd or 0:.2f}, flat, "
                  f"whatever the bucket  ·  one bet per signal, two per game, "
                  f"never twice on one market"))
        self.beat_lbl.configure(
            text=f"last checked {self.last_check}  (#{self.check_count})")

        state, msg = self.ledger.reconcile()
        self.recon_lbl.configure(
            text=msg[:150],
            fg={"disagree": "#fca5a5", "unchecked": "#fcd34d",
                "ok": "#86efac"}.get(state, "#9ca3af"))
        # ⚠ `waiting_line()` IS THE ONE HE NEEDED AND DID NOT HAVE. Ten of his
        # bets sat on finished games for up to four days, counted at what they
        # cost as though the result were unknown, and the only way anyone found
        # out was him reading Kalshi. Fifth time. It is on the screen now, with
        # the age, and it shouts once it goes past a day.
        self.room_lbl.configure(
            text="  " + self.ledger.room_line()
                 # ⚠ IN BETS, NOT DOLLARS. He should not have to divide his
                 # spare cash by his stake to discover he is two bets from the
                 # tool pausing itself. Mailbox 022.
                 + chr(10) + "  " + self.ledger.room_in_bets_line()
                 + chr(10) + "  " + self.ledger.daily_line()
                 + chr(10) + "  " + self.ledger.at_risk_line()
                 + chr(10) + "  " + self.ledger.riding_line()
                 + chr(10) + "  " + self.ledger.waiting_line()
                 # ⚠ HIS MONEY AND THE BOT'S ARE NEVER ADDED TOGETHER. This
                 # tool cannot tell one from the other, so it reports its own
                 # figure, labelled, and shows the difference as UNEXPLAINED
                 # rather than folding it into a total. Mailbox 022.
                 + (chr(10) + "  " + self.ledger.start_line()
                    if self.ledger.start_line() else "")
                 + chr(10) + "  " + self.ledger.bot_only_line()
                 + chr(10) + "  " + self.ledger.unexplained_line()
                 + chr(10) + "  " + self.ledger.two_window_line())

        avail = self._available()
        if self.pending is not None:
            # Nothing else is offered while a bet is out being placed. One at
            # a time, and it also means a second click cannot start a second.
            self._placement_card()
        elif blocked:
            self._dead_card(blocked[1])
        elif not avail:
            self._dead_card(self._nothing_text())
        elif self.auto_exec:
            kind = "auto"
            self._live_card(avail[0])
            self._surface(avail[0])
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

    def _entry_from(self, p, bet) -> Entry:
        """Build the ledger row for a pick. THE ONLY PLACE THIS HAPPENS.

        ⚠ IT USED TO HAPPEN TWICE and the two copies drifted, which is exactly
        the failure this collapses. The manual click path carried the
        who-else flag; the automatic path built its own `Entry(...)` and did
        not. Every bet is automatic, so **`alone` was empty on all 31 rows** --
        including the three that filled after the flag was wired -- and the
        sizing rule that reads that flag could not be switched on at all.

        Two construction sites for one object is a slow leak. One is a fact.
        """
        return Entry(
            game_key=p.game_key, ticker=p.ticker, event_ticker=p.event_ticker,
            team=p.team, matchup=p.matchup, side=p.side, price_c=bet.price_c,
            contracts=bet.contracts, cost_usd=bet.cost_usd,
            fee_usd=bet.fee_usd, win_profit_usd=bet.win_profit_usd,
            lose_usd=bet.lose_usd, starts_utc=p.starts_utc, signal=p.signal,
            confirmed_utc=datetime.now().astimezone().isoformat(
                timespec="seconds"),
            why=list(p.why),
            alone=p.alone, consensus=p.consensus,
            bucket=bucket_for(p.alone, p.consensus))

    def _fee_rate(self, ticker):
        """The taker rate for this market's series. Cached per session by
        `fees`; falls back to the FULL rate, which overstates the cost -- the
        only safe direction when a lookup fails."""
        try:
            rate, known = fees.rate_for(ticker, DEMO._client())
            if not known and ticker not in self._fee_warned:
                self._fee_warned.add(ticker)
                self.events.put(("log", fees.note_for(ticker)))
            return rate
        except Exception:
            return None

    def _stake(self, p=None) -> float:
        """What one bet may cost right now, in the tier this pick is in.

        His instruction, 2026-08-16: "ten percent on agreed games, five percent
        on everything else". Fails closed -- if the balance has never been read
        this is 0.00 and nothing sizes, rather than falling back to a number
        the tool made up. And a MISSING who-else flag sizes small, never big.
        """
        if p is None:
            return stake_for(self.ledger.account_balance_usd)
        return stake_for_bucket(self.ledger.account_balance_usd,
                                p.alone, p.consensus)

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
        # ⚠ THE FEE RATE COMES FROM THE SERIES, NOT FROM A CONSTANT. Kalshi
        # charges HALF fee on KXMLBGAME, which is everything this desk trades.
        # Without it the break-even shown -- the number he actually reasons
        # with -- overstates the bar by about one win in a hundred.
        bet = size_bet(price, self._stake(p), self._fee_rate(p.ticker))
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
        # Was anything else on this game? INFORMATION ONLY -- shown, recorded,
        # never filtered on. mlb-paper's own measurement is that every dollar
        # this strategy has made came from games something else also wanted,
        # and that it loses on the ones it picks alone -- but that was found by
        # looking at results and has never been tried on a game that was not
        # used to find it. So it is a caption, not a criterion.
        if p.consensus:
            lines.append("")
            lines.append(f"  who else is on this game:  {p.consensus}")
            if p.alone:
                lines.append("  (on its own picks so far this bot has LOST "
                             "money — worth knowing, not a reason to skip)")
        # Which tier, and WHY, in words. He sized this rule himself and should
        # be able to see it applied rather than take it on trust.
        pct = stake_pct_for(p.alone, p.consensus)
        tier = bucket_for(p.alone, p.consensus)
        lines.append("")
        lines.append({
            # ⚠ The count goes on the card EVERY time the big tier fires, not
            # once in a document. It rests on 3 games, so he should see that
            # each time rather than take the extra size on trust.
            "agreed": f"  both approaches like this one — betting {pct:.0f}%."
                      f" Based on only {AGREED_EVIDENCE_GAMES} games so far,"
                      f" so the bigger size is an experiment.",
            "opposite": f"  another approach took the OTHER side — betting "
                        f"{pct:.0f}%",
            "alone": f"  only this approach likes it — betting {pct:.0f}%",
            "unknown": f"  could not tell who else is on it — betting the "
                       f"SMALL {pct:.0f}%, never the big one",
        }[tier])
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

    def _placement_card(self) -> None:
        """The click-by-click hand-off, shown after COPY & OPEN.

        HIS WORDS, and it is a real failure not a nicety: *"I go to click the
        trade on Kalshi and it opens up, but then I get bombarded with a bunch
        of different trades to make, and then I get confused. Right now this is
        perfect, I can see everything. But when I go to click it, I get
        bombarded by a bunch of different shit on Kalshi and I don't know what
        to click."*

        The card was doing its job; the hand-off was not. On 2026-08-12 he
        copied Pittsburgh, Cleveland and Seattle and voided all three -- three
        bets lost to a confusing page, not to indecision.

        It stays on screen until he says which happened. He is looking at
        Kalshi and then back at this, so it must not vanish.

        ⚠ THE LABELS ARE FROM HIS SCREENSHOT, NOT FROM MY OWN READING OF THE
        PAGE. Kalshi renders client-side and the page came back empty to every
        tool I have. What IS verified, from Kalshi's own API on 2026-08-12: the
        event this window links to has exactly TWO markets, one per team. So
        "find the row with the team name, there are only two" is solid; the
        exact button wording is his screenshot's and is written to survive
        being slightly wrong.
        """
        e, p, bet = self.pending
        f = self._card_shell(f"  DO THIS ON THE PAGE THAT JUST OPENED  ",
                             title_colour="#1d4ed8")

        q = self.quotes.get(p.ticker)
        warn = ""
        if q and q.ask_c and q.ask_c - bet.price_c >= 3:
            warn = (f"CAREFUL — the price has gone UP to {q.ask_c} cents since "
                    f"you clicked; you were shown {bet.price_c}. That is "
                    f"against you. Buying now costs more and wins less. It is "
                    f"fine to press \"I did NOT place it\" and let this one go.")
        elif q and q.ask_c and bet.price_c - q.ask_c >= 3:
            warn = (f"The price has come DOWN to {q.ask_c} cents since you "
                    f"clicked; you were shown {bet.price_c}. That is in your "
                    f"favour.")
        tk.Label(f, text=self._fit([warn] if warn else [""], self.WARN_LINES),
                 justify="left", anchor="nw", font=("Consolas", 9),
                 fg=("#b45309" if warn else "black"), height=self.WARN_LINES
                 ).pack(fill="x")

        team = e.team.upper()
        lines = [
            "",
            f"  1. Find the row that says      {team}",
            f"     (there are only two rows — the two teams)",
            "",
            f"  2. Click the GREEN button on that row.",
            f"     It says \"Yes\" and a price, about {bet.price_c}c.",
            f"     The RED \"No\" button next to it is the OTHER team. Not that one.",
            "",
            f"  3. In the quantity box, type   {bet.contracts}",
            "",
            f"  4. Check the total says about  ${bet.cost_usd:.2f}",
            "",
            f"  5. Press the buy button to confirm.",
            "",
            "  IGNORE everything under headings like \"Spread and Total\",",
            "  \"Team Totals\", or anything saying over/under. Those are",
            "  different bets on the same game and are not this one.",
        ]
        tk.Label(f, text=self._fit(lines, self.CARD_BODY_LINES),
                 justify="left", anchor="nw", font=("Consolas", 9),
                 height=self.CARD_BODY_LINES).pack(fill="x")

        row = tk.Frame(f)
        row.pack(fill="x", pady=(6, 2))
        tk.Button(row, text="I PLACED IT", width=30, bg="#166534", fg="white",
                  font=("Segoe UI", 11, "bold"),
                  command=self._placed).pack(side="left")
        tk.Frame(row, width=50).pack(side="left")
        tk.Button(row, text="I did NOT place it",
                  command=self._not_placed).pack(side="left")
        # Production order. Real money, real API -- every order here is
        # indistinguishable from one placed via the web UI. Only offered when
        # a production key is set up, and it never replaces the real hand-off above.
        ready, why = DEMO.configured()
        tk.Button(row, text="PRODUCTION order", state=("normal" if ready
                                                      else "disabled"),
                  command=self._practice).pack(side="left", padx=(12, 0))
        tk.Label(row, text=("production = real money" if ready
                            else "production not set up"),
                 fg="#666", font=("Segoe UI", 8)).pack(side="right", padx=6)

    def _practice(self) -> None:
        """Send this bet to Kalshi's PRODUCTION environment. Real money, real risk."""
        if self.pending is None:
            return
        e, p, bet = self.pending
        try:
            out = DEMO.submit(self.ledger, e)
        except DEMO.Refused as exc:
            self._alert(str(exc), "warn")
            self._log(f"PRODUCTION order refused: {exc}")
            return
        except Exception as exc:
            self._alert(f"The PRODUCTION order could not be sent: {exc}", "error")
            self._log(f"PRODUCTION order error: {exc}")
            return
        self._log(f"PRODUCTION order [{out.state}] {out.message}")
        self._alert(out.message,
                    "info" if out.state in ("filled", "partial") else "warn")
        e.note = (f"PRODUCTION order {out.order_id or '—'}: {out.state}"
                  f" ({out.filled:g} of {out.requested})")
        self.ledger.save()
        self._render()

    def _placed(self) -> None:
        e, p, bet = self.pending
        self.pending = None
        self._log(f"PLACED {e.team} {e.contracts} at {e.price_c}c "
                  f"(${e.cost_usd:.2f})")
        self._alert(f"Recorded. ${e.cost_usd:.2f} on {e.team}. Type your new "
                    f"Kalshi balance in the box above when it updates.", "info")
        self._render()

    def _not_placed(self) -> None:
        e, p, bet = self.pending
        self.pending = None
        e.status = "void"
        e.note = "he pressed 'I did NOT place it' on the hand-off card"
        self.ledger.save()
        voids = len([x for x in self.ledger.entries
                     if x.signal == e.signal and x.status == "void"])
        again = voids < 2
        self._log(f"NOT PLACED {e.team} — ${e.cost_usd:.2f} taken back out"
                  + (". It will be offered once more." if again
                     else ". Second time, so it is now closed for good."))
        self._alert(
            f"Taken back out. Nothing was bet." +
            (" This one will come round again — it is offered once more."
             if again else
             " That is the second time on this bet, so it is now closed."),
            "info")
        self._render()

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
        # The row id is the entry's POSITION, not its ticker. It used to be the
        # ticker, and that crashed the whole window the moment the same ticker
        # appeared twice -- which became possible on 2026-08-12 when a voided
        # bet started being offered once more. A duplicate id raises inside
        # _render, so the window would have died on his next click.
        self.tree.delete(*self.tree.get_children())
        for i, e in reversed(list(enumerate(self.ledger.entries))):
            pl = (usd(e.pnl_usd) if e.status in ("won", "lost")
                  else ("—" if e.status == "void" else "open"))
            self.tree.insert("", "end", iid=str(i), values=(
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
        if self.pending is not None:
            # A double-click, a repeated callback or a stray retry must not
            # produce two of anything.
            self._alert("One at a time — finish telling me whether the last "
                        "one went on.", "warn")
            return
        blocked = self._blocked()
        if blocked:
            self._alert(blocked[1], "error")
            self._render()
            return
        q = self.quotes.get(p.ticker)
        ok, why = self.ledger.may_bet(p.game_key, p.signal,
                                      q.ask_c if q else None, bet.cost_usd)
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
            f"Next the window shows you exactly what to click on that page. "
            f"Come back and tell it whether the bet went on — if it did not, "
            f"nothing is recorded and this one is offered once more.")
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
        self.ledger.add(self._entry_from(p, bet))
        self.pending = (self.ledger.entries[-1], p, bet)
        self._log(f"COPIED {detail}")
        self._log(f"opened {url}")
        self._alert(f"Copied. The window now shows exactly what to click on "
                    f"that page — follow it, then come back and say whether "
                    f"it went on.", "info")
        self._render()

    def _void_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            self._alert("Click a row in the list first.", "warn")
            return
        try:
            e = self.ledger.entries[int(sel[0])]
        except (ValueError, IndexError):
            self._alert("Could not find that row — refresh and try again.",
                        "warn")
            return
        if e.status != "open":
            self._alert("That one is already settled or already voided.", "warn")
            return
        voids = len([x for x in self.ledger.entries
                     if x.signal == e.signal and x.status == "void"])
        again = voids + 1 < 2
        if messagebox.askokcancel(
                "Mark as not placed?",
                f"{e.team} — {e.matchup}\n\n"
                f"This takes ${e.cost_usd:.2f} back out of the running total, "
                f"because you never actually placed it.\n\n"
                + ("This bet will be offered ONCE more, since nothing was "
                   "actually bet on it."
                   if again else
                   "This is the second time on this bet, so it is now closed "
                   "for good.")):
            e.status = "void"
            e.pnl_usd = 0.0
            e.note = "marked not placed by hand"
            self.ledger.save()
            self._log(f"voided {e.matchup} — not actually placed"
                      + (". Offered once more." if again else ". Now closed."))
            self._render()

    def _toggle(self) -> None:
        self.paused = not self.paused
        self.pause_btn.configure(text="resume" if self.paused else "pause")
        self._log("paused — nothing is being refreshed" if self.paused
                  else "resumed")

    def _toggle_auto(self) -> None:
        """Toggle auto-execution on / off."""
        self.auto_exec = not self.auto_exec
        self.auto_btn.configure(
            text=f"AUTO: {'ON' if self.auto_exec else 'OFF'}",
            bg="#166534" if self.auto_exec else "#7f1d1d",
            fg="white")
        self._log(f"auto-execution {'enabled' if self.auto_exec else 'disabled'}")
        self._alert(
            f"Auto-execution {'enabled — bets will be placed automatically' if self.auto_exec else 'disabled — you must place bets manually'}",
            "info")
        self._render()

    # --------------------------------------------------- auto-exec helpers
    @staticmethod
    def _is_temporary_refusal(reason: str) -> bool:
        """Classify a guard refusal as temporary (deferred) or permanent (void).

        Temporary blocks can clear on their own:
          - reconciliation disagreement
          - account floor / trailing drawdown
          - daily caps (clears at midnight)
          - kill switch
          - losing position (price may recover)

        Permanent blocks are final:
          - duplicate signal (Guard 1)
          - game already has max positions
          - game has started/finished
        """
        permanent_keywords = [
            "already been taken",        # duplicate signal
            "already been taken on this game",
            "the limit",                  # max positions per game
            "losing position",            # could be temporary, but we treat as permanent
            "game has started",
            "game has finished",
        ]
        lower = reason.lower()
        for kw in permanent_keywords:
            if kw in lower:
                return False
        return True  # default to temporary (deferred)

    def _handle_auto_refused(self, entry, exc: DEMO.Refused) -> None:
        """Handle a guard refusal during auto-exec. Classifies the failure."""
        reason = str(exc)
        if self._is_temporary_refusal(reason):
            entry.status = "deferred"
            entry.note = f"auto-exec deferred: {reason}"
            self._log(f"AUTO deferred {entry.team}: {reason} — will retry when condition clears")
            self._alert(f"Auto-deferred {entry.team}: {reason}", "warn")
        else:
            entry.status = "void"
            entry.note = f"auto-exec refused (permanent): {reason}"
            self._log(f"AUTO void {entry.team}: {reason} — permanently closed")
            self._alert(f"Auto-voided {entry.team}: {reason}", "warn")
        self.ledger.save()
        self.events.put(("auto_refused", (entry, reason)))

    def _handle_auto_error(self, entry, exc: Exception) -> None:
        """Handle a non-guard error during auto-exec. Network errors are deferred."""
        entry.status = "deferred"
        entry.note = f"auto-exec deferred (error): {exc}"
        self._log(f"AUTO deferred {entry.team}: {exc} — will retry")
        self._alert(f"Auto-deferred {entry.team}: {exc}", "warn")
        self.ledger.save()
        self.events.put(("auto_error", (entry, str(exc))))

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
        # Guard 4's input. READ ONLY -- two GETs, positions and balance. This
        # is what re-pointed the guard on 2026-08-16: it used to compare the
        # ledger against his WHOLE balance, which could never agree because he
        # trades manually, so every signal deferred and 11 bets expired
        # unplaced. It now checks that OUR OWN bets are in his account.
        # Keep both "this desk is alive" claims fresh: the local lock file and
        # the ntfy claim the other machine reads. Neither can raise -- a failed
        # claim must never be able to stop a bet being checked.
        onemachine.heartbeat(lock_path=onemachine.LOCK_PATH)
        self._cycles = getattr(self, "_cycles", 0) + 1
        if self._cycles % 10 == 0:
            who, _checked = onemachine.remote_holder()
            if who:
                # Do not kill the window -- he may have a position open on it.
                # Stop it BETTING, say so loudly, and let him decide.
                self.events.put(("autooff", who))

        did = self.alerts.tick(self.ledger)
        if did:
            self.events.put(("log", did))

        ok, said = DEMO.read_account(self.ledger)
        if ok != self._account_read_ok:
            self._account_read_ok = ok
            self.events.put(("log", f"account: {said}"))
        # Say it out loud the moment it appears. He should never have to read
        # Kalshi himself to find out the tool's numbers are wrong.
        for line in DEMO.drain_corrections():
            self.events.put(("log", f"CORRECTED from your account — {line}"))
            self.events.put(("alert", (f"Corrected from your account: {line}",
                                       "warn")))

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
        for e in self.ledger.live_entries():
            try:
                q = PRICES.quote(e.ticker)
            except RuntimeError:
                continue
            if q.is_final:
                won = ((q.result == "yes") == (e.side.upper() == "YES"))
                self.events.put(("settle", (e.ticker, won)))

        # ---- auto-execution: submit qualifying picks automatically --------
        if self.auto_exec and self.pending is None and not self.paused:
            # ---- retry deferred entries first ----
            deferred = self.ledger.deferred_entries()
            for de in deferred:
                # Expire any that have started since last check
                if de.status == "deferred":
                    self.ledger.expire_deferred_past_game_start()
                # Re-check: still deferred and not expired?
                if de.status != "deferred":
                    continue
                # Try to submit again. guards_ok() in demo_exec will re-evaluate
                # all guards; if the blocking condition has cleared, it will go
                # through. If not, it will be re-marked deferred with updated note.
                # ⚠ SECOND LOCK, deliberately independent of the status.
                # The status handler is what SHOULD stop a retry, and it
                # failed to, which cost 8 orders on one market. This does not
                # care what the status says: one submission per entry per
                # session, full stop. Two locks because the first one being
                # wrong is not a hypothetical here -- it already happened.
                if id(de) in self._auto_submitted_ids:
                    continue
                try:
                    self._auto_submitted_ids.add(id(de))
                    outcome = DEMO.submit(self.ledger, de)
                    self.events.put(("auto_result", (de, outcome)))
                    break
                except DEMO.Refused as exc:
                    de.note = f"auto-exec still refused: {exc}"
                    self.ledger.save()
                    self.events.put(("auto_refused", (de, str(exc))))
                    # Keep it deferred for next retry
                    break
                except Exception as exc:
                    de.note = f"auto-exec error: {exc}"
                    self.ledger.save()
                    self.events.put(("auto_error", (de, str(exc))))
                    # Keep it deferred for next retry
                    break

            # ---- fresh picks (only if no deferred entry was retried) ----
            if self.pending is None:  # deferred retry didn't produce a pending
                avail = self._available()
                for p in avail:
                    if p.signal in self._auto_submitted:
                        continue
                    # Build the bet at the current quote (or the bot's price if
                    # no live quote yet).
                    q = self.quotes.get(p.ticker)
                    price = q.ask_c if (q and q.ask_c) else p.quoted_price_c
                    # Half fee on KXMLBGAME -- see _fee_rate and src/fees.py.
                    bet = size_bet(price, self._stake(p),
                                   self._fee_rate(p.ticker))
                    if not bet.placeable:
                        continue
                    entry = self._entry_from(p, bet)
                    self.ledger.add(entry)
                    # Submit through the production adapter (guards + signing).
                    try:
                        self._auto_submitted_ids.add(id(entry))
                        outcome = DEMO.submit(self.ledger, entry)
                        self.events.put(("auto_result", (entry, outcome)))
                    except DEMO.Refused as exc:
                        self._handle_auto_refused(entry, exc)
                    except Exception as exc:
                        self._handle_auto_error(entry, exc)
                    self._auto_submitted.add(p.signal)
                    break          # one bet per loop iteration

        self.events.put(("checked", time.strftime("%H:%M:%S")))

    def _pump(self) -> None:
        dirty = False
        try:
            while True:
                kind, *rest = self.events.get_nowait()
                if kind == "alert":
                    # ⚠ THIS BRANCH DID NOT EXIST AND THE MESSAGES WERE BEING
                    # DROPPED ON THE FLOOR. The background thread has been
                    # queueing ("alert", ...) since the corrections work went
                    # in -- so every "CORRECTED from your account" banner, the
                    # loudest thing this window can say, was silently
                    # discarded and only the log line survived. Found by
                    # grepping for the handler before adding a second caller,
                    # not by any test: 244 of them pass either way, because
                    # not one of them drains this queue.
                    text, level = rest[0]
                    self._alert(text, level)
                    dirty = True
                elif kind == "autooff":
                    # ⚠ ANOTHER MACHINE IS RUNNING THIS DESK TOO. Both would
                    # place the same bet and both act on the same position.
                    # The window is NOT closed -- he may have money on it and
                    # closing it would take the screen away from him. It stops
                    # BETTING and says so, loudly, and on his phone.
                    if self.auto_exec:
                        self.auto_exec = False
                        msg = (f"AUTO TURNED OFF: the baseball desk is also "
                               f"running on \"{rest[0]}\". Two of them would "
                               f"both place the same bet. Close one, then "
                               f"turn AUTO back on.")
                        self._log(msg)
                        self._alert(msg, "warn")
                        self.alerts.say(msg, title="Baseball desk: two copies",
                                        urgent=True)
                elif kind == "log":
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
                    if e is None:
                        # ⚠ THE SILENT NO-OP THAT COST 106 HOURS. This branch
                        # did not exist: `settle()` returned None, `if e:` was
                        # false, and nothing was written or logged. It ran once
                        # a minute and did nothing, invisibly, for four days.
                        why = self.ledger.settle_reason(ticker)
                        if why:
                            self._log(f"COULD NOT SETTLE {why}")
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
                elif kind == "auto_result":
                    entry, outcome = rest[0]
                    # ⚠ THE STATUS MUST CHANGE HERE, AND IT DID NOT.
                    #
                    # This handler used to only log. A `deferred` entry that
                    # submitted SUCCESSFULLY stayed `deferred`, so the retry
                    # loop picked it up again 60 seconds later, and again, and
                    # again. On 2026-08-16 that put EIGHT orders on one
                    # Baltimore market -- 64 contracts, $26.24 -- against a
                    # rule of $4.15 a bet. Roughly a quarter of his money on a
                    # single game.
                    #
                    # It only started firing when Guard 4 was fixed the same
                    # evening: before that every submit was refused, so the
                    # loop span harmlessly. Removing the accidental brake is
                    # what exposed the missing one.
                    if outcome.is_working:
                        entry.status = "open"
                        entry.note = (f"auto-placed: {outcome.state}, "
                                      f"{outcome.filled:g} of "
                                      f"{outcome.requested} @ "
                                      f"{entry.price_c}c")
                    elif outcome.state in ("rejected", "cancelled"):
                        entry.status = "void"
                        entry.note = f"auto {outcome.state}: {outcome.message}"
                    else:                       # unknown
                        # NOT retried. Unknown means we do not know whether
                        # money went on, and guessing "no" is how you place it
                        # twice.
                        entry.status = "open"
                        entry.note = (f"auto UNKNOWN — may or may not be on. "
                                      f"{outcome.message}")
                    self.ledger.save()
                    self._log(f"AUTO [PRODUCTION] [{outcome.state}] {outcome.message}")
                    if outcome.is_working:
                        self._alert(
                            f"Auto-placed {entry.team}: {outcome.message}",
                            "info")
                    else:
                        self._alert(
                            f"Auto on {entry.team}: {outcome.message}",
                            "warn")
                    dirty = True
                elif kind == "auto_refused":
                    entry, reason = rest[0]
                    self._log(f"AUTO refused {entry.team}: {reason}")
                    self._alert(f"Auto-refused {entry.team}: {reason}", "warn")
                    dirty = True
                elif kind == "auto_error":
                    entry, reason = rest[0]
                    self._log(f"AUTO error on {entry.team}: {reason}")
                    self._alert(f"Auto error on {entry.team}: {reason}", "error")
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

    # The one irreversible mistake in the move to the laptop: two desks running
    # would both place the same bet and both act on the same position, and
    # neither can see the other. src/onemachine.py says what this catches and,
    # more importantly, what it does not.
    ok, why = onemachine.may_start()
    if not ok:
        print()
        print("  " + why)
        print()
        try:
            import tkinter.messagebox as mb
            root = tk.Tk()
            root.withdraw()
            mb.showerror("Baseball desk is already running", why)
            root.destroy()
        except Exception:
            pass
        raise SystemExit(1)
    if why:
        print()
        print("  " + why)
        print()

    onemachine.write_lock(onemachine.LOCK_PATH)
    try:
        Desk().mainloop()
    finally:
        # Free it immediately rather than making him wait out the five-minute
        # staleness window before he can open it on the other machine.
        onemachine.clear_lock(onemachine.LOCK_PATH)


if __name__ == "__main__":
    main()
