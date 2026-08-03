"""
paper_bot.py — runs many strategies side by side on live markets, with no money.

Every strategy sees the SAME market at the SAME moment, so the comparison is
like-for-like. Decisions are written to a log the instant they are made —
before the outcome is known — which is the whole point: it makes hindsight
bias impossible. A strategy cannot look good in this log because someone
went back and reinterpreted it afterwards.

    python paper_bot.py                    # start paper trading
    python paper_bot.py --summary          # league table of every strategy
    python paper_bot.py --summary --detail # every closed trade

Nothing here can place an order. It holds a read-only Kalshi client.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional

from kalshi_client import KalshiClient, Market, _fp
from sofascore_feed import SofaScoreClient
from autoscan import subject_player, _name_matches, other_side

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_trades.jsonl")
STAKE = 9                      # contracts per paper trade, fixed for comparability


# ----------------------------------------------------------------------
# what a strategy sees
# ----------------------------------------------------------------------

@dataclass
class View:
    """Everything known about one player in one live match, right now."""
    ticker: str
    player: str
    match: str
    bid: int
    ask: int
    spread: int
    sets_won: int
    sets_lost: int
    games_won: int
    games_lost: int
    set_scores: list          # completed sets, [(mine, theirs), ...]
    serving: Optional[bool]
    open_price: Optional[int]
    rank: Optional[int]
    opp_rank: Optional[int]
    category: Optional[str]
    status: str

    @property
    def was_favorite(self) -> Optional[bool]:
        return None if self.open_price is None else self.open_price > 50

    @property
    def ahead(self) -> bool:
        return self.sets_won > self.sets_lost

    @property
    def level(self) -> bool:
        return self.sets_won == self.sets_lost and self.sets_won > 0

    @property
    def best_set_margin(self) -> int:
        won = [m - t for m, t in self.set_scores if m > t]
        return max(won) if won else 0

    def just_won_a_set(self) -> bool:
        """Most recently completed set went their way."""
        return bool(self.set_scores) and self.set_scores[-1][0] > self.set_scores[-1][1]


_COMMON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from kalshi_fees import fee_order_dollars as _fee_order_dollars  # noqa: E402


def fee(n: int, price_cents: int) -> float:
    """Kalshi taker fee in dollars. Exact Decimal — see common/kalshi_fees.py."""
    return _fee_order_dollars(price_cents, n)


# ----------------------------------------------------------------------
# strategies
# ----------------------------------------------------------------------

@dataclass
class Strategy:
    name: str
    why: str                              # the reasoning being tested
    enter: Callable[[View], bool]
    stop_drop: Optional[int] = 38         # cents below entry; None = no stop
    target: Optional[int] = 95            # absolute cents; None = no target
    max_positions: int = 8


def _liquid(v: View) -> bool:
    return v.spread <= 3 and 1 <= v.ask <= 99


STRATEGIES: list[Strategy] = [
    # --- what the live bot does now, as the benchmark -------------------
    Strategy(
        "live_current",
        "the rules the real bot runs today: favourite, ahead on sets, <=75c",
        lambda v: _liquid(v) and v.was_favorite is True and v.ahead
                  and v.ask <= 75 and v.best_set_margin >= 2,
    ),
    # --- the only entry band that has actually made money ---------------
    Strategy(
        "band_60_75",
        "entry price 60-75c only; the one bucket carrying live P&L (+$83)",
        lambda v: _liquid(v) and 60 <= v.ask <= 75 and v.ahead,
    ),
    Strategy(
        "band_60_75_strict",
        "same band, but demands a decisive set (6-3 or better), not 7-5",
        lambda v: _liquid(v) and 60 <= v.ask <= 75 and v.ahead
                  and v.best_set_margin >= 3,
    ),
    # --- the momentum finding: at one set all, back who won set 2 -------
    Strategy(
        "momentum_set2",
        "at 1-1, buy whoever just won set 2 (measured 62% win vs 54c price)",
        lambda v: _liquid(v) and v.level and v.sets_won == 1
                  and v.just_won_a_set() and 35 <= v.ask <= 70,
    ),
    # --- the mirror: the market clings to the set-1 winner ---------------
    Strategy(
        "fade_set1_winner",
        "at 1-1, AVOID whoever won set 1 (measured 38% win vs 48c price) — "
        "so buy their opponent instead",
        lambda v: _liquid(v) and v.level and v.sets_won == 1
                  and not v.just_won_a_set() and 35 <= v.ask <= 70,
    ),
    # --- exit-rule experiments on the same entry ------------------------
    Strategy(
        "band_no_stop",
        "control: same 60-75c entry, NO stop, hold to settlement",
        lambda v: _liquid(v) and 60 <= v.ask <= 75 and v.ahead,
        stop_drop=None, target=None,
    ),
    Strategy(
        "band_wide_stop",
        "same entry, 50c stop — is even wider better than 38c?",
        lambda v: _liquid(v) and 60 <= v.ask <= 75 and v.ahead,
        stop_drop=50,
    ),
    Strategy(
        "band_quick_target",
        "same entry, take profit at +15c instead of riding to 95c",
        lambda v: _liquid(v) and 60 <= v.ask <= 75 and v.ahead,
        stop_drop=38, target=None,            # target set per-trade below
    ),
    # --- known losers, kept as controls so the log proves it ------------
    Strategy(
        "high_prob_90plus",
        "CONTROL, expected to lose: buy 90c+ favourites for small sure gains",
        lambda v: _liquid(v) and 90 <= v.ask <= 97,
        stop_drop=None, target=None,
    ),
    Strategy(
        "cheap_longshot",
        "CONTROL, expected to lose: sub-25c underdogs hoping for a spike",
        lambda v: _liquid(v) and 5 <= v.ask <= 25,
        stop_drop=None, target=60,
    ),
    # --- fee-aware: fees peak at 50c, so demand more edge there ---------
    Strategy(
        "fee_cheap_zone",
        "only trade where fees are cheap (<=30c or >=75c) and player is ahead",
        lambda v: _liquid(v) and v.ahead and (v.ask <= 30 or 75 <= v.ask <= 88),
    ),
    # --- ranking edge, newly recordable ---------------------------------
    Strategy(
        "big_rank_gap",
        "player ranked 100+ places better AND ahead on sets",
        lambda v: _liquid(v) and v.ahead and v.rank is not None
                  and v.opp_rank is not None and (v.opp_rank - v.rank) >= 100
                  and v.ask <= 80,
    ),
]


# ----------------------------------------------------------------------
# the book
# ----------------------------------------------------------------------

@dataclass
class PaperPos:
    strategy: str
    ticker: str
    player: str
    match: str
    entry: int
    contracts: int
    stop: Optional[int]
    target: Optional[int]
    opened_ts: float
    open_price: Optional[int] = None
    rank: Optional[int] = None
    opp_rank: Optional[int] = None
    category: Optional[str] = None
    sets_at_entry: str = ""


class PaperBook:
    def __init__(self, log_path: str = LOG):
        self.log_path = log_path
        self.open: dict[tuple[str, str], PaperPos] = {}    # (strategy, ticker)
        self.closed_tickers: dict[str, set] = defaultdict(set)
        self._load()

    def _write(self, rec: dict) -> None:
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _load(self) -> None:
        """Rebuild open positions from the log so a restart doesn't lose them."""
        if not os.path.exists(self.log_path):
            return
        with open(self.log_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                key = (r.get("strategy"), r.get("ticker"))
                if r.get("event") == "OPEN":
                    self.open[key] = PaperPos(**r["pos"])
                elif r.get("event") == "CLOSE":
                    self.open.pop(key, None)
                    self.closed_tickers[r.get("strategy")].add(r.get("ticker"))

    def enter(self, s: Strategy, v: View) -> None:
        key = (s.name, v.ticker)
        if key in self.open or v.ticker in self.closed_tickers[s.name]:
            return                                   # one paper trade per market
        if sum(1 for k in self.open if k[0] == s.name) >= s.max_positions:
            return
        target = s.target
        if s.name == "band_quick_target":
            target = min(99, v.ask + 15)             # relative target
        pos = PaperPos(
            strategy=s.name, ticker=v.ticker, player=v.player, match=v.match,
            entry=v.ask, contracts=STAKE,
            stop=(max(1, v.ask - s.stop_drop) if s.stop_drop else None),
            target=target, opened_ts=time.time(),
            open_price=v.open_price, rank=v.rank, opp_rank=v.opp_rank,
            category=v.category, sets_at_entry=f"{v.sets_won}-{v.sets_lost}",
        )
        self.open[key] = pos
        self._write({"event": "OPEN", "ts": round(time.time(), 1),
                     "strategy": s.name, "ticker": v.ticker,
                     "why": s.why, "pos": asdict(pos)})

    def mark(self, markets: dict[str, Market]) -> list[str]:
        """Close any paper position whose stop or target the book has reached."""
        msgs = []
        for key, p in list(self.open.items()):
            m = markets.get(p.ticker)
            if not m or m.yes_bid <= 0:
                continue
            hit = None
            if p.stop is not None and m.yes_bid <= p.stop:
                hit = ("stop", m.yes_bid)
            elif p.target is not None and m.yes_bid >= p.target:
                hit = ("target", p.target)
            if hit:
                self._close(key, p, hit[0], hit[1])
                msgs.append(f"{p.strategy}: {hit[0]} {p.player[:18]} @ {hit[1]}c")
        return msgs

    def settle(self, kc: KalshiClient) -> list[str]:
        """Close anything whose market has finished, using the real result."""
        msgs = []
        for key, p in list(self.open.items()):
            m = markets_cache.get(p.ticker)
            if m is not None:
                continue                    # still trading; leave it open
            try:
                mk = kc._get(f"/markets/{p.ticker}").get("market", {})
            except Exception:
                continue
            res = mk.get("result")
            if res not in ("yes", "no"):
                continue
            self._close(key, p, "settled", 100 if res == "yes" else 0)
            msgs.append(f"{p.strategy}: settled {p.player[:18]} {res}")
        return msgs

    def _close(self, key, p: PaperPos, how: str, exit_px: int) -> None:
        cost = p.contracts * p.entry / 100 + fee(p.contracts, p.entry)
        proceeds = p.contracts * exit_px / 100
        if 0 < exit_px < 100:
            proceeds -= fee(p.contracts, exit_px)
        pnl = proceeds - cost
        self.open.pop(key, None)
        self.closed_tickers[p.strategy].add(p.ticker)
        self._write({"event": "CLOSE", "ts": round(time.time(), 1),
                     "strategy": p.strategy, "ticker": p.ticker,
                     "player": p.player, "how": how,
                     "entry": p.entry, "exit": exit_px,
                     "contracts": p.contracts, "pnl": round(pnl, 4),
                     "held_sec": int(time.time() - p.opened_ts),
                     "open_price": p.open_price, "rank": p.rank,
                     "opp_rank": p.opp_rank, "category": p.category,
                     "sets_at_entry": p.sets_at_entry})


markets_cache: dict[str, Market] = {}


# ----------------------------------------------------------------------

def build_views(kc: KalshiClient, feed: SofaScoreClient,
                opens: dict) -> list[View]:
    try:
        live = [f for f in feed.raw(force=True) if f.get("matchType") == "singles"]
    except Exception:
        return []
    if not live:
        return []
    try:
        markets = [m for m in kc.tennis_markets() if m.is_trading]
    except Exception:
        return []
    markets_cache.clear()
    markets_cache.update({m.ticker: m for m in markets})

    views = []
    for m in markets:
        subj = subject_player(m.title)
        if not subj:
            continue
        pair = side = None
        for f in live:
            if _name_matches(subj, f.get("homePlayerName", "")):
                pair, side = f, "home"; break
            if _name_matches(subj, f.get("awayPlayerName", "")):
                pair, side = f, "away"; break
        if pair is None:
            continue
        oth = other_side(side)
        sc = pair.get("score") or {}
        games = pair.get("games") or {}
        last = str(pair.get("lastPeriod") or "")
        cur = games.get(last.replace("period", "set"), {}) if last else {}

        sets_done = []
        for i in range(1, 6):
            g = games.get(f"set{i}")
            if not g:
                continue
            if f"period{i}" == last and pair.get("statusType") == "inprogress":
                continue
            sets_done.append((int(g.get(side) or 0), int(g.get(oth) or 0)))

        if m.ticker not in opens:
            try:
                opens[m.ticker] = kc.opening_price(m.ticker)
            except Exception:
                opens[m.ticker] = None

        views.append(View(
            ticker=m.ticker, player=subj,
            match=f"{pair.get('homePlayerName')} vs {pair.get('awayPlayerName')}",
            bid=m.yes_bid, ask=m.yes_ask, spread=m.yes_ask - m.yes_bid,
            sets_won=int(sc.get(side) or 0), sets_lost=int(sc.get(oth) or 0),
            games_won=int(cur.get(side) or 0), games_lost=int(cur.get(oth) or 0),
            set_scores=sets_done,
            serving=(None if pair.get("serving") is None
                     else pair["serving"] == side),
            open_price=opens[m.ticker],
            rank=pair.get("homeRank") if side == "home" else pair.get("awayRank"),
            opp_rank=pair.get("awayRank") if side == "home" else pair.get("homeRank"),
            category=pair.get("category"),
            status=pair.get("status", ""),
        ))
    return views


def summarize(path: str, detail: bool = False) -> None:
    if not os.path.exists(path):
        print("no paper trades yet"); return
    closed = defaultdict(list); opened = defaultdict(int); why = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("event") == "OPEN":
                opened[r["strategy"]] += 1
                why[r["strategy"]] = r.get("why", "")
            elif r.get("event") == "CLOSE":
                closed[r["strategy"]].append(r)
    if not closed:
        print(f"{sum(opened.values())} positions opened, none closed yet")
        return
    rows = []
    for name, v in closed.items():
        n = len(v); w = [x for x in v if x["pnl"] > 0]
        pnl = sum(x["pnl"] for x in v)
        rows.append((pnl / n, name, n, 100 * len(w) / n, pnl,
                     sum(x["pnl"] for x in w) / len(w) if w else 0,
                     (sum(x["pnl"] for x in v if x["pnl"] <= 0) / (n - len(w)))
                     if n - len(w) else 0,
                     opened[name] - n))
    rows.sort(reverse=True)
    print(f"\n{'strategy':<22} {'closed':>6} {'open':>5} {'win%':>6} "
          f"{'net $':>9} {'per trade':>10} {'avg win':>9} {'avg loss':>9}")
    print("-" * 82)
    for per, name, n, wr, pnl, aw, al, still in rows:
        print(f"{name:<22} {n:>6} {still:>5} {wr:>5.0f}% {pnl:>+9.2f} "
              f"{per:>+10.3f} {aw:>+9.2f} {al:>+9.2f}")
    print()
    for _, name, *_ in rows:
        print(f"  {name:<22} {why.get(name,'')}")
    if detail:
        print()
        for name, v in closed.items():
            print(f"\n--- {name} ---")
            for x in sorted(v, key=lambda r: r["ts"]):
                print(f"  {x['player'][:22]:<22} {x['entry']:>3}c -> "
                      f"{x['exit']:>3}c  {x['how']:<8} {x['pnl']:>+7.2f}  "
                      f"sets {x.get('sets_at_entry','')}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Paper-trade many strategies. No money.")
    ap.add_argument("--interval", type=int, default=45)
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--detail", action="store_true")
    ap.add_argument("--log", default=LOG)
    a = ap.parse_args()

    if a.summary:
        summarize(a.log, a.detail); return

    kc = KalshiClient(demo=False, read_only=True)     # cannot place orders
    feed = SofaScoreClient(cache_sec=10)
    book = PaperBook(a.log)
    opens: dict = {}

    print(f"paper trading {len(STRATEGIES)} strategies every {a.interval}s")
    print(f"log: {a.log}")
    print("NO REAL ORDERS. ctrl-c to stop.\n")
    try:
        while True:
            t0 = time.time()
            views = build_views(kc, feed, opens)
            for msg in book.mark(markets_cache):
                print(f"    {msg}")
            for msg in book.settle(kc):
                print(f"    {msg}")
            for s in STRATEGIES:
                for v in views:
                    try:
                        if s.enter(v):
                            book.enter(s, v)
                    except Exception:
                        continue
            per = defaultdict(int)
            for (sname, _) in book.open:
                per[sname] += 1
            print(f"  {time.strftime('%H:%M:%S')}  {len(views):3d} markets  "
                  f"open: " + " ".join(f"{k}={v}" for k, v in sorted(per.items()))
                  or "none", flush=True)
            time.sleep(max(1.0, a.interval - (time.time() - t0)))
    except KeyboardInterrupt:
        print("\nstopped. run --summary to compare strategies")


if __name__ == "__main__":
    main()
