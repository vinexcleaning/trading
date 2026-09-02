"""
scanner.py — the bot.

Watches live Kalshi tennis markets, runs your rules on every one, and
shows you the trades that qualify. You press [c]. It places the buy AND
the resting sell together, then goes back to watching.

    python scanner.py              # demo account, safe to experiment
    python scanner.py --live       # real money, asks you to confirm first

Press Ctrl-C any time to stop.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Optional

from kalshi_client import TENNIS_SERIES, KalshiClient, Market
from sofascore_feed import SofaScoreClient as LiveScoreClient
from tennis_engine import Config, Snapshot, Setup, evaluate, render


# ----------------------------------------------------------------------

@dataclass
class MatchState:
    """What you tell the scanner about a match it's watching."""
    ticker: str
    player: str
    match: str
    was_prematch_favorite: bool
    sets_won: int
    sets_lost: int
    live_score_name: str = ""     # name to look up on the live feed; blank = manual only
    score_age_sec: int = 0        # how stale sets_won/sets_lost is; 0 for hand-typed


WATCHLIST_HELP = """
The scanner needs to know two things it can't read off the price:
who was the pre-match favorite, and the current set score.

Add matches with [a]. It remembers them until you remove them.
"""


class Scanner:
    def __init__(self, cfg: Config, client: KalshiClient, live: Optional[LiveScoreClient] = None):
        self.cfg = cfg
        self.client = client
        self.live = live
        self.watching: dict[str, MatchState] = {}
        self.placed: set[str] = set()

    # ---- live score refresh --------------------------------------------
    def _refresh_live_scores(self) -> None:
        """Pull fresh set scores for anyone with a live_score_name set.
        Never places anything — just updates the numbers evaluate() sees.
        Falls back silently to whatever's already stored if the lookup
        fails; the confirm card always shows how stale the score is."""
        if not self.live or not self.live.enabled:
            return
        for st in list(self.watching.values()):
            if not st.live_score_name:
                continue
            score = self.live.find(st.live_score_name)
            if score is None:
                continue
            if (score.sets_won, score.sets_lost) != (st.sets_won, st.sets_lost):
                print(f"  live: {st.player} now {score.sets_won}-{score.sets_lost} "
                      f"(was {st.sets_won}-{st.sets_lost})")
                self.placed.discard(st.ticker)
            st.sets_won, st.sets_lost = score.sets_won, score.sets_lost
            st.score_age_sec = score.age_sec

    # ---- the loop ----------------------------------------------------
    def scan(self) -> list[tuple[MatchState, Market, object]]:
        """Check every watched match, return the ones that qualify."""
        self._refresh_live_scores()
        try:
            markets = {m.ticker: m for m in self.client.tennis_markets()}
        except Exception as e:
            print(f"  couldn't reach Kalshi: {e}")
            return []

        hits = []
        open_count = 0
        if self.client.authenticated:
            try:
                open_count = len(self.client.positions())
            except Exception as e:
                print(f"  couldn't check open positions: {e}")

        for ticker, st in list(self.watching.items()):
            m = markets.get(ticker)
            if not m or not m.is_open:
                continue
            snap = Snapshot(
                player=st.player, match=st.match,
                ask=m.yes_ask, bid=m.yes_bid,
                sets_won=st.sets_won, sets_lost=st.sets_lost,
                was_prematch_favorite=st.was_prematch_favorite,
                score_age_sec=st.score_age_sec,
                market_open=m.is_open,
                open_positions=open_count,
            )
            d = evaluate(self.cfg, snap)
            if d.take and ticker not in self.placed:
                hits.append((st, m, d))
        return hits

    # ---- the one manual step -----------------------------------------
    def offer(self, st: MatchState, m: Market, d) -> None:
        print(render(d, Snapshot(player=st.player, match=st.match,
                                 ask=m.yes_ask, bid=m.yes_bid)))
        if st.live_score_name:
            print(f"  score source: live feed, {st.score_age_sec}s old — "
                  f"verify {st.sets_won}-{st.sets_lost} matches what you see on Kalshi/SofaScore")
        else:
            print(f"  score source: typed in by hand ({st.sets_won}-{st.sets_lost})")
        print(f"  [c] place both orders   [s] skip   [r] remove {st.player}")
        choice = input("  > ").strip().lower()

        if choice == "r":
            self.watching.pop(st.ticker, None)
            print(f"  removed {st.player}")
            return
        if choice != "c":
            print("  skipped")
            return

        try:
            resp = self.client.limit_buy(st.ticker, d.contracts, d.entry_price)
            order_id = (resp.get("order") or resp).get("order_id", "")
            print(f"  BUY placed: {d.contracts} @ {d.entry_price}c")

            # Nothing may be sold until the buy really fills. A take-profit
            # sell on contracts you do not own is not an exit -- it opens a
            # SHORT, and it would trigger exactly when the match turns your
            # way. `gui.py` was fixed for this on the same reasoning; this
            # file was missed, and a limit buy at a stale price simply RESTS,
            # so the unfilled case is the normal one rather than the rare one.
            filled, status = (self.client.await_fill(order_id)
                              if order_id else (0.0, "unknown"))
            if filled <= 0:
                print(f"  BUY DID NOT FILL ({status}) — no sell placed.")
                print("  nothing is owned, so there is nothing to protect.")
                print(f"  the buy may still be resting: check Kalshi and "
                      f"cancel it if you do not want it.")
                return

            qty = int(filled)
            if qty < d.contracts:
                print(f"  PARTIAL FILL: {qty} of {d.contracts} — selling "
                      f"only what was bought.")
            try:
                self.client.limit_sell(st.ticker, qty, d.target_price)
                print(f"  SELL resting at {d.target_price}c — fills without you")
            except Exception as sell_err:
                print(f"  BOUGHT {qty} BUT THE SELL FAILED: {sell_err}")
                print("  you are LONG with no take-profit. Set one on Kalshi.")
                self.placed.add(st.ticker)
                return
            print(f"  your manual exit is {d.exit_price}c. Kalshi has no stops.")
            self.placed.add(st.ticker)
        except Exception as e:
            print(f"  ORDER FAILED: {e}")
            print("  check Kalshi directly before retrying.")

    # ---- board: no setup, auto-scans everything -----------------------
    def board(self, interval: int = 15) -> None:
        """Scan every live market with no per-match setup. Flags candidates
        by price and spread alone; score is only needed for those."""
        print(f"  scanning all markets every {interval}s — Ctrl-C to stop\n")
        try:
            while True:
                try:
                    markets = [m for m in self.client.tennis_markets() if m.is_trading]
                except Exception as e:
                    print(f"  {time.strftime('%H:%M:%S')} — couldn't reach Kalshi: {e}")
                    time.sleep(interval)
                    continue

                candidates = []
                for m in markets:
                    if m.spread > 4:
                        continue
                    in_div = 15 <= m.yes_ask <= self.cfg.max_divergence_price
                    in_fav = m.yes_ask <= self.cfg.max_favorite_price
                    if in_div or in_fav:
                        candidates.append(m)
                shown = sorted(candidates, key=lambda m: m.spread)[:12]

                print(f"  {time.strftime('%H:%M:%S')} — {len(markets)} trading, "
                      f"{len(shown)} worth a look\n")
                for i, m in enumerate(shown):
                    zone = "div" if m.yes_ask <= self.cfg.max_divergence_price else "fav"
                    print(f"   {i:2d}. [{zone}] {m.title[:42]:<42} "
                          f"{m.yes_bid:>2}/{m.yes_ask:<2}c  spread {m.spread}c  vol {m.volume}")
                print()

                if shown:
                    raw = input("  [number] to check one   [Enter] to keep scanning   > ").strip()
                    if raw.isdigit() and int(raw) < len(shown):
                        self._quick_check(shown[int(raw)])
                    continue
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n  stopped\n")

    def _quick_check(self, m: Market) -> None:
        resolved = self._resolve_match_state()
        if resolved is None:
            return
        fav, won, lost, live_name = resolved
        snap = Snapshot(player=m.title[:30], match=m.title,
                        ask=m.yes_ask, bid=m.yes_bid,
                        sets_won=won, sets_lost=lost, was_prematch_favorite=fav)
        d = evaluate(self.cfg, snap)
        print(render(d, snap))
        if d.take:
            self.watching[m.ticker] = MatchState(
                ticker=m.ticker, player=m.title[:30], match=m.title,
                was_prematch_favorite=fav, sets_won=won, sets_lost=lost,
                live_score_name=live_name)
            print("  added to watch list — press [s] to get the confirm card\n")

    # ---- adding matches -----------------------------------------------
    def debug(self) -> None:
        """Dump the raw API response for one market — shows real field names."""
        for series in TENNIS_SERIES:
            try:
                data = self.client._get("/markets", {"series_ticker": series,
                                                     "status": "open", "limit": 2})
            except Exception as e:
                print(f"  {series}: request failed — {e}")
                continue
            markets = data.get("markets", [])
            print(f"\n  {series}: {len(markets)} returned, "
                  f"top-level keys {list(data.keys())}")
            if markets:
                m = markets[0]
                print(f"  raw fields for {m.get('ticker', '?')}:")
                for k, v in sorted(m.items()):
                    print(f"    {k:<26} {v!r}")
                return
        print("  nothing came back from any series\n")

    def add(self) -> None:
        try:
            allm = self.client.tennis_markets()
        except Exception as e:
            print(f"  couldn't load markets: {e}")
            return

        live = [m for m in allm if m.is_trading]
        if not live:
            print(f"\n  {len(allm)} tennis markets found, none trading yet.")
            print("  (no volume, no quotes — these matches haven't started)")
            print("  Check Kalshi's LIVE tab; if something IS live there,")
            print("  paste me its title and we'll find why it's missing.\n")
            return

        markets = live[:25]
        print(f"\n  {len(live)} trading now (of {len(allm)} listed)")
        for i, m in enumerate(markets):
            print(f"  {i:2d}. {m.title[:46]:<46} "
                  f"bid {m.yes_bid:>2} ask {m.yes_ask:>2} "
                  f"last {m.last_price:>2} vol {m.volume}")
        raw = input("  number (blank to cancel) > ").strip()
        if not raw.isdigit() or int(raw) >= len(markets):
            return
        m = markets[int(raw)]

        resolved = self._resolve_match_state()
        if resolved is None:
            return
        fav, won, lost, live_name = resolved

        self.watching[m.ticker] = MatchState(
            ticker=m.ticker, player=m.title[:30], match=m.title,
            was_prematch_favorite=fav, sets_won=won, sets_lost=lost,
            live_score_name=live_name)
        print(f"  watching {m.title[:40]}")

    def _resolve_match_state(self) -> Optional[tuple[bool, int, int, str]]:
        """Figure out pre-match-favorite + current set score, preferring the
        live feed so you don't have to go look it up yourself. Falls back to
        asking only when the live feed can't answer. Returns
        (was_favorite, sets_won, sets_lost, live_score_name) or None if
        the user bailed out."""
        if not self.live or not self.live.enabled:
            fav = input("  pre-match favorite? [y/n] > ").lower().startswith("y")
            try:
                won = int(input("  sets won > ") or 0)
                lost = int(input("  sets lost > ") or 0)
            except ValueError:
                print("  numbers only")
                return None
            return fav, won, lost, ""

        name = input("  player's name, spelled as it shows up live (e.g. SofaScore) > ").strip()
        score = self.live.find(name) if name else None

        if score is None:
            reason = self.live.last_error or "not showing as live right now"
            print(f"  couldn't auto-read this one ({reason}) — type it in for now, "
                  f"it'll switch to auto once the match shows up live")
            fav = input("  pre-match favorite? [y/n] > ").lower().startswith("y")
            try:
                won = int(input("  sets won > ") or 0)
                lost = int(input("  sets lost > ") or 0)
            except ValueError:
                print("  numbers only")
                return None
            return fav, won, lost, name

        print(f"  live: {score.match_title} — {score.sets_won}-{score.sets_lost} ({score.status})")
        if score.was_favorite is None:
            print("  couldn't tell who opened as favorite from the odds data")
            fav = input("  pre-match favorite? [y/n] > ").lower().startswith("y")
        else:
            fav = score.was_favorite
            print(f"  pre-match favorite: {'yes' if fav else 'no'} (from opening odds)")
        return fav, score.sets_won, score.sets_lost, name

    def update_score(self) -> None:
        if not self.watching:
            print("  nothing being watched")
            return
        items = list(self.watching.items())
        for i, (_, st) in enumerate(items):
            print(f"  {i}. {st.player} — {st.sets_won}-{st.sets_lost}")
        raw = input("  number > ").strip()
        if not raw.isdigit() or int(raw) >= len(items):
            return
        _, st = items[int(raw)]
        try:
            st.sets_won = int(input("  sets won > ") or st.sets_won)
            st.sets_lost = int(input("  sets lost > ") or st.sets_lost)
        except ValueError:
            return
        if st.live_score_name:
            print(f"  this was tracking live scores as '{st.live_score_name}' — "
                  f"[k] keep auto-updating   [x] switch to manual only")
            if input("  > ").strip().lower() == "x":
                st.live_score_name = ""
        st.score_age_sec = 0
        self.placed.discard(st.ticker)
        print("  updated")


# ----------------------------------------------------------------------

def main() -> None:
    # Windows consoles default to cp1252 and cannot encode a name like
    # "Aleksandar Vukić" — printing one raises UnicodeEncodeError and kills
    # the scan. Force UTF-8 first.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true",
                    help="real live prices, read-only — cannot place orders")
    ap.add_argument("--live", action="store_true", help="real money")
    ap.add_argument("--bankroll", type=float, default=110.0)
    ap.add_argument("--stake-pct", type=float, default=5.0)
    ap.add_argument("--interval", type=int, default=20, help="seconds between scans")
    args = ap.parse_args()

    if args.live:
        print("\n  *** LIVE MODE — REAL MONEY ***")
        if input("  type LIVE to continue > ").strip() != "LIVE":
            print("  cancelled")
            return

    client = KalshiClient(demo=not (args.live or args.watch),
                          read_only=args.watch)
    cfg = Config(bankroll=args.bankroll, stake_pct=args.stake_pct)
    live = LiveScoreClient()

    mode = "LIVE" if args.live else ("WATCH — real prices, no orders" if args.watch else "DEMO")
    print(f"\n  {mode} | bankroll ${cfg.bankroll:.2f} | {cfg.stake_pct}% per trade")
    print(f"  live score feed: {'on (sofascore, free)' if live.enabled else 'off'}")

    if args.watch:
        print("  read-only: it will show you trades but cannot place them")
        print(f"  api key: {'loaded' if client.authenticated else 'NOT loaded'}\n")
    elif not client.authenticated:
        print("  no API key found — set KALSHI_KEY_ID and KALSHI_KEY_PATH")
        print("  running read-only; orders will fail\n")
    else:
        try:
            print(f"  balance ${client.balance():.2f}\n")
        except Exception as e:
            print(f"  auth problem: {e}\n")

    print(WATCHLIST_HELP)
    s = Scanner(cfg, client, live=live)

    while True:
        try:
            n = len(s.watching)
            cmd = input(f"  [{n} watched] [b]oard [a]dd [u]pdate [s]can [d]ebug [q]uit > ").strip().lower()

            if cmd == "q":
                print("  done\n")
                return
            if cmd == "b":
                s.board(interval=args.interval)
            elif cmd == "d":
                s.debug()
            elif cmd == "a":
                s.add()
            elif cmd == "u":
                s.update_score()
            elif cmd == "s":
                if not s.watching:
                    print("  add a match first")
                    continue
                print(f"  scanning every {args.interval}s — Ctrl-C to stop")
                try:
                    while True:
                        hits = s.scan()
                        if hits:
                            for st, m, d in hits:
                                s.offer(st, m, d)
                        else:
                            print(f"  {time.strftime('%H:%M:%S')} — nothing qualifies")
                        time.sleep(args.interval)
                except KeyboardInterrupt:
                    print("\n  stopped scanning")
        except (KeyboardInterrupt, EOFError):
            print("\n  done\n")
            return


if __name__ == "__main__":
    main()
