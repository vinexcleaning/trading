"""Reconstruct a Kalshi order book from the pmxt L2 archive.

THE ARCHIVE IS A WIRE CAPTURE, NOT A BOOK SERIES. 99.73% of rows are
`orderbook_delta` (one price level, one signed size change, one side) and
0.27% are `orderbook_snapshot` (the full ladder, both sides). Nothing in the
file is a point-in-time book. You get one by replaying snapshot + deltas in
order, per ticker. Reading `yes_bids` directly returns an empty list on
99.98% of rows -- which is how a naive pass concludes there is no depth.

TWO PARSING TRAPS, both hit before:
  * the struct children are literally named "1" (price) and "2" (size).
    Iterating the converted dict yields its KEYS, producing a perfectly
    plausible ladder of (1.0, 2.0) at every level on every market.
  * BOTH sides are quoted as BIDS. `yes_bids` are bids to buy YES; `no_bids`
    are bids to buy NO. A YES ask is therefore 100 - (best NO bid). There is
    no "ask" column and treating `no_bids` as asks inverts the book.

Prices arrive in dollars (0.001-0.999) and are held here in CENTS.
"""
import os
from collections import defaultdict

import pyarrow.compute as pc
import pyarrow.parquet as pq

ARCHIVE = r"C:\Users\gianf\trading\market-selection\data\pmxt"


def hour_path(stamp):
    return os.path.join(ARCHIVE, f"kalshi_orderbook_{stamp}.parquet")


def load_hour(stamp, tickers=None, columns=None):
    """Read one hourly file, optionally filtered to a set of tickers."""
    cols = columns or ["timestamp_received", "timestamp", "market_ticker",
                       "event_type", "yes_bids", "no_bids", "price", "delta",
                       "side"]
    t = pq.read_table(hour_path(stamp), columns=cols)
    if tickers:
        mask = pc.is_in(t["market_ticker"],
                        value_set=pa_array(sorted(tickers)))
        t = t.filter(mask)
    return t


def pa_array(vals):
    import pyarrow as pa
    return pa.array(vals)


def levels(arr):
    """struct list -> [(price_cents, size)]. Read the children BY KEY."""
    out = []
    for d in (arr or []):
        try:
            out.append((float(d["1"]) * 100.0, float(d["2"])))
        except (KeyError, TypeError, ValueError):
            continue
    return out


class Book:
    """One market's two bid ladders, replayed from the wire."""

    __slots__ = ("yes", "no", "ts", "n_snap", "n_delta")

    def __init__(self):
        self.yes = defaultdict(float)      # price_cents -> size, bids to buy YES
        self.no = defaultdict(float)       # price_cents -> size, bids to buy NO
        self.ts = None
        self.n_snap = self.n_delta = 0

    def apply_snapshot(self, yes_arr, no_arr, ts):
        self.yes.clear()
        self.no.clear()
        for p, s in levels(yes_arr):
            if s:
                self.yes[round(p, 1)] = s
        for p, s in levels(no_arr):
            if s:
                self.no[round(p, 1)] = s
        self.ts = ts
        self.n_snap += 1

    def apply_delta(self, price_dollars, delta, side, ts):
        if price_dollars is None or delta is None:
            return
        p = round(float(price_dollars) * 100.0, 1)
        book = self.yes if side == "yes" else self.no
        book[p] = book.get(p, 0.0) + float(delta)
        if book[p] <= 0:
            book.pop(p, None)
        self.ts = ts
        self.n_delta += 1

    # ---- reads
    def best_yes_bid(self):
        return max(self.yes) if self.yes else None

    def best_no_bid(self):
        return max(self.no) if self.no else None

    def yes_ask(self):
        """Buying YES lifts the ask, and the ask is 100 - best NO bid."""
        nb = self.best_no_bid()
        return None if nb is None else round(100.0 - nb, 1)

    def touch(self):
        return self.best_yes_bid(), self.yes_ask()

    def spread(self):
        b, a = self.touch()
        return None if (b is None or a is None) else round(a - b, 1)

    def size_at(self, price_c, side="yes"):
        return (self.yes if side == "yes" else self.no).get(round(price_c, 1), 0.0)

    def depth_within(self, cents):
        """Contracts resting within `cents` of the touch, both sides."""
        b, a = self.touch()
        d = 0.0
        if b is not None:
            d += sum(s for p, s in self.yes.items() if p >= b - cents)
        nb = self.best_no_bid()
        if nb is not None:
            d += sum(s for p, s in self.no.items() if p >= nb - cents)
        return d

    def is_valid(self):
        """Content check: prices in range, sizes positive, book not crossed."""
        for bk in (self.yes, self.no):
            for p, s in bk.items():
                if not (0.0 < p < 100.0) or s <= 0:
                    return False, f"bad level {p}@{s}"
        b, a = self.touch()
        if b is not None and a is not None and a < b:
            return False, f"crossed book: bid {b} > ask {a}"
        return True, "ok"


def for_ticker(table, ticker):
    """Filter in ARROW before converting to Python.

    The first version converted all nine columns of an 11.8M-row table to
    Python lists inside `replay()`, then skipped the 99.9% of rows belonging
    to other tickers -- and did that once per ticker. Forty tickers made it
    effectively non-terminating. Filter first; convert what is left.
    """
    return table.filter(pc.equal(table["market_ticker"], ticker))


def replay(table, ticker=None):
    """Yield (ts, Book) after each message, in order.

    Pass a table already filtered to one ticker, or give `ticker` and it will
    be filtered here.
    """
    if ticker is not None:
        table = for_ticker(table, ticker)
    if table.num_rows == 0:
        return
    et = table.column("event_type").to_pylist()
    tr = table.column("timestamp_received").to_pylist()
    px = table.column("price").to_pylist()
    dl = table.column("delta").to_pylist()
    sd = table.column("side").to_pylist()
    yb = table.column("yes_bids").to_pylist()
    nb = table.column("no_bids").to_pylist()
    b = Book()
    started = False
    for i in range(len(et)):
        if et[i] == "orderbook_snapshot":
            b.apply_snapshot(yb[i], nb[i], tr[i])
            started = True
        elif started:
            b.apply_delta(px[i], dl[i], sd[i], tr[i])
        else:
            continue          # deltas before the first snapshot are unusable
        yield tr[i], b
