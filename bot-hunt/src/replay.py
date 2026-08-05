"""Order-book REPLAY from the Kalshi L2 archive: snapshot + deltas -> a
point-in-time book. `market-selection` called this "the single biggest piece of
unbuilt machinery" and it was still unbuilt.

WHAT THE DATA ACTUALLY IS, measured in src/peek_l2.py rather than assumed:

  event_type   `orderbook_delta` (~99.9%) and `orderbook_snapshot` (~0.1%)
  snapshot     carries `yes_bids` / `no_bids` as [(price_dollars, size)] and
               **a NULL timestamp on 46 of 46 sampled**
  delta        carries (price, delta, side); delta is signed, ~50/50 +/-
  side         'yes' or 'no' — BOTH are bid ladders. A YES ask is 1 - best NO bid.
  prices       dollars, 0.01 .. 0.98

TWO PROBLEMS AND HOW EACH IS HANDLED, because both could silently fabricate a book:

1. **Snapshots have no timestamp**, so they cannot be ordered against deltas.
   ASSUMPTION: a snapshot is the book at the START of its hourly file. That is
   an assumption, so it is TESTED, not trusted — see `conservation` below.

2. **Only ~37 of ~99 tickers per hour carry a snapshot.** The rest must inherit
   the closing book of the previous hour. Hours are therefore replayed in
   chronological order and state is carried forward.

THE CONSERVATION CANARY. If the seed or the ordering is wrong, applying deltas
will drive some price level NEGATIVE — you cannot remove size that was never
there. Every negative level is counted and reported as a fraction. A book with
a high violation rate is not a book, and the caller must refuse to trade it.
This is the same idea as GUARDS #12: check content, not row counts.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pyarrow.parquet as pq

DATA = Path(__file__).resolve().parent.parent / "data" / "l2"


@dataclass
class Book:
    """Two bid ladders, price_cents -> size. Kalshi quotes both sides as bids."""
    yes: dict = field(default_factory=dict)
    no: dict = field(default_factory=dict)
    neg_events: int = 0
    applied: int = 0

    def apply(self, side: str, price_c: int, delta: float) -> None:
        book = self.yes if side == "yes" else self.no
        cur = book.get(price_c, 0.0)
        new = cur + delta
        self.applied += 1
        if new < -1e-9:
            # Cannot remove size that was never there -> the seed or the
            # ordering is wrong. Counted, then clamped so one bad level does
            # not poison the rest of the replay.
            self.neg_events += 1
            new = 0.0
        if new <= 1e-9:
            book.pop(price_c, None)
        else:
            book[price_c] = new

    def best_yes_bid(self):
        return max(self.yes) if self.yes else None

    def best_no_bid(self):
        return max(self.no) if self.no else None

    def yes_ask(self):
        nb = self.best_no_bid()
        return None if nb is None else 100 - nb

    def spread(self):
        b, a = self.best_yes_bid(), self.yes_ask()
        return None if (b is None or a is None) else a - b

    def size_at(self, side: str, price_c: int) -> float:
        return (self.yes if side == "yes" else self.no).get(price_c, 0.0)

    def depth(self, side: str, within_c: int):
        book = self.yes if side == "yes" else self.no
        if not book:
            return 0.0
        best = max(book)
        return sum(s for p, s in book.items() if p >= best - within_c)

    def copy_state(self):
        return dict(self.yes), dict(self.no)


def to_cents(x) -> int:
    """Archive prices are decimal dollars. Kalshi's tick is 1c, so integer
    cents is the exact representation and avoids float keys entirely."""
    return int(round(float(x) * 100))


def hours_on_disk():
    return sorted(DATA.glob("es_*.parquet"))


def replay(files=None, tickers=None, on_event=None, verbose=True):
    """Replay hourly files in order, carrying book state across hours.

    `on_event(ts, ticker, book, row)` is called after each delta is applied, so
    a strategy sees exactly the book a participant would have seen and can
    never read a later row. There is no look-ahead available by construction.

    Returns {ticker: Book} final state plus a stats dict.
    """
    files = files or hours_on_disk()
    books: dict[str, Book] = {}
    stats = {"files": 0, "rows": 0, "deltas": 0, "snapshots": 0,
             "snap_seeded": 0, "snap_resynced": 0,
             "neg_events": 0, "applied": 0, "tickers": set(),
             "crossed_obs": 0, "obs": 0}

    for fp in files:
        t = pq.read_table(fp)
        d = t.to_pydict()
        n = t.num_rows
        stats["files"] += 1
        stats["rows"] += n

        # 1. A SNAPSHOT REPLACES THE BOOK. It does not merely seed an empty one.
        #
        # BUG FOUND AND FIXED HERE. v1 skipped a snapshot whenever the ticker
        # already had carried-forward state, to protect continuity for the
        # ~62-of-99 tickers that have no snapshot in a given hour. The effect
        # was that a seeded book NEVER RE-SYNCED, so levels that the feed
        # expects a snapshot to clear accumulated all day. The replay ended
        # with books like bid=99 / ask=16 — crossed by 83c, which is impossible
        # in a real order book and would have made every fill simulation
        # nonsense.
        #
        # The conservation canary PASSED throughout (0.047%), because stale
        # levels are not negative levels. It took looking at the output. That is
        # the third time in this project that reading beat scoring.
        for i in range(n):
            if d["event_type"][i] != "orderbook_snapshot":
                continue
            stats["snapshots"] += 1
            tk = d["market_ticker"][i]
            if tickers and tk not in tickers:
                continue
            yb = {to_cents(x["1"]): float(x["2"])
                  for x in (d["yes_bids"][i] or [])}
            nb = {to_cents(x["1"]): float(x["2"])
                  for x in (d["no_bids"][i] or [])}
            if yb or nb:
                prev = books.get(tk)
                bk = Book(yes=yb, no=nb)
                if prev is not None:
                    bk.neg_events = prev.neg_events
                    bk.applied = prev.applied
                    stats["snap_resynced"] += 1
                books[tk] = bk
                stats["snap_seeded"] += 1

        # 2. apply deltas in timestamp order
        order = sorted((i for i in range(n)
                        if d["event_type"][i] == "orderbook_delta"
                        and d["timestamp"][i] is not None),
                       key=lambda i: d["timestamp"][i])
        for i in order:
            tk = d["market_ticker"][i]
            if tickers and tk not in tickers:
                continue
            bk = books.get(tk)
            if bk is None:
                # No snapshot ever seen for this ticker. Starting from an empty
                # book makes every removal a violation, so such tickers are
                # tracked but flagged; the caller filters on `seeded`.
                bk = books[tk] = Book()
                bk.unseeded = True  # type: ignore[attr-defined]
            stats["tickers"].add(tk)
            stats["deltas"] += 1
            bk.apply(d["side"][i], to_cents(d["price"][i]),
                     float(d["delta"][i]))
            # THE CROSSED-BOOK CANARY. best_yes_bid + best_no_bid > 100 is a
            # free arbitrage and cannot persist in a real book, so any material
            # rate of it means the replay is wrong. This is the check that
            # would have caught the stale-level bug immediately; conservation
            # alone did not, because stale levels are not negative levels.
            yb_, nb_ = bk.best_yes_bid(), bk.best_no_bid()
            if yb_ is not None and nb_ is not None:
                stats["obs"] += 1
                if yb_ + nb_ > 100:
                    stats["crossed_obs"] += 1
            if on_event is not None:
                on_event(d["timestamp"][i], tk, bk, i, d)
        if verbose:
            print(f"  {fp.name}: {n:,} rows, {len(books)} books, "
                  f"neg so far {sum(b.neg_events for b in books.values()):,}",
                  flush=True)

    stats["neg_events"] = sum(b.neg_events for b in books.values())
    stats["applied"] = sum(b.applied for b in books.values())
    stats["tickers"] = len(stats["tickers"])
    return books, stats


def conservation_report(books, stats):
    """THE CANARY. A replay whose deltas drive levels negative is not a book."""
    seeded = {k: b for k, b in books.items() if not getattr(b, "unseeded", False)}
    unseeded = {k: b for k, b in books.items() if getattr(b, "unseeded", False)}
    s_neg = sum(b.neg_events for b in seeded.values())
    s_app = sum(b.applied for b in seeded.values())
    u_neg = sum(b.neg_events for b in unseeded.values())
    u_app = sum(b.applied for b in unseeded.values())
    print("\n== CONSERVATION CANARY (negative levels mean a bad seed/order)")
    print(f"   SEEDED tickers    {len(seeded):>5}   "
          f"violations {s_neg:>8,} / {s_app:>9,} applied = "
          f"{100*s_neg/max(s_app,1):.3f}%")
    print(f"   UNSEEDED tickers  {len(unseeded):>5}   "
          f"violations {u_neg:>8,} / {u_app:>9,} applied = "
          f"{100*u_neg/max(u_app,1):.3f}%")
    print("   (unseeded books start empty, so a high rate there is EXPECTED "
          "and is the control:")
    print("    if seeded and unseeded rates were similar, the snapshot seed "
          "would be doing nothing.)")
    ok = (s_neg / max(s_app, 1)) < 0.02
    print(f"   -> seeded replay {'PASSES' if ok else 'FAILS'} "
          f"at a 2% violation threshold")

    cx = stats.get("crossed_obs", 0)
    obs = max(stats.get("obs", 0), 1)
    rate = cx / obs
    print("\n== CROSSED-BOOK CANARY (yes_bid + no_bid > 100 is free money)")
    print(f"   crossed observations: {cx:,} / {obs:,} = {100*rate:.3f}%")
    cross_ok = rate < 0.01
    print(f"   -> {'PASSES' if cross_ok else 'FAILS'} at a 1% threshold. "
          f"A real book is essentially never crossed;")
    print("      a high rate means stale levels are accumulating and no fill "
          "simulation on it is meaningful.")
    return {"seeded": len(seeded), "unseeded": len(unseeded),
            "seeded_violation_rate": s_neg / max(s_app, 1),
            "unseeded_violation_rate": u_neg / max(u_app, 1),
            "crossed_rate": rate, "pass": ok and cross_ok,
            "conservation_pass": ok, "crossed_pass": cross_ok}


if __name__ == "__main__":
    fs = hours_on_disk()
    print(f"replaying {len(fs)} hours from {DATA}")
    books, stats = replay(fs)
    print(f"\nrows={stats['rows']:,} deltas={stats['deltas']:,} "
          f"snapshots={stats['snapshots']} seeded={stats['snap_seeded']} "
          f"tickers={stats['tickers']}")
    rep = conservation_report(books, stats)
    two = [k for k, b in books.items()
           if not getattr(b, "unseeded", False) and b.spread() is not None]
    print(f"\n   books ending two-sided: {len(two)}")
    for k in two[:6]:
        b = books[k]
        print(f"     {k[:46]:46} bid={b.best_yes_bid()} ask={b.yes_ask()} "
              f"spread={b.spread()}c depth5={b.depth('yes',5):.0f}")
    (Path(__file__).resolve().parent.parent / "reports"
     / "replay_conservation.json").write_text(
        json.dumps({**rep, "files": stats["files"], "rows": stats["rows"]},
                   indent=1), encoding="utf-8")
