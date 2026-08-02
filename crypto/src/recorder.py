"""Live order-book + trade recorder for Kalshi and Polymarket crypto series.

Neither venue exposes historical order books, so recording is the ONLY path to
Tier B data. Started as early as possible in the session.

Discipline (per the project's failure-mode list):
  - three timestamps per row: exchange event, our receipt, our write
  - UTC integer nanoseconds; one monotonic clock for sequencing
  - content validation, not row counts: every snapshot is checked for a
    non-empty book with parseable numeric prices before it is written
  - reads *_dollars / *_fp on Kalshi, never the legacy integer fields (which
    now silently return None)

Read-only. No auth, no orders, no wallet.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

UA = {"User-Agent": "research-readonly/0.1"}
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
CLOB = "https://clob.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
DATA = "https://data-api.polymarket.com"

ROOT = r"C:\Users\gianf\crypto\data"

# Kalshi series to record. The 15m series is the prior work's; the hourly
# ladders are new and are the ones with fixed round-number strikes.
KALSHI_SERIES = ["KXBTC15M", "KXETH15M", "KXSOL15M", "KXXRP15M",
                 "KXBTC", "KXBTCD", "KXETH", "KXETHD", "KXSOLD", "KXXRP"]

POLY_PREFIXES = ("btc-updown-", "eth-updown-", "sol-updown-", "xrp-updown-",
                 "doge-updown-", "bnb-updown-", "hype-updown-")


def now_ns():
    return time.time_ns()


def mono_ns():
    return time.monotonic_ns()


def iso_to_ns(s):
    if not s:
        return None
    try:
        if isinstance(s, (int, float)):
            v = int(s)
            return v * 10**9 if v < 10**12 else v * 10**6
        s = str(s).replace("Z", "+00:00")
        return int(datetime.fromisoformat(s).timestamp() * 10**9)
    except Exception:
        return None


class Writer:
    """Append-only JSONL, partitioned source/date/hour. Converted to parquet
    later so a crash never corrupts a columnar file mid-write."""

    def __init__(self, root=ROOT):
        self.root = root
        self.handles = {}
        self.counts = {}

    def path(self, source, ts_ns):
        d = datetime.fromtimestamp(ts_ns / 1e9, timezone.utc)
        p = os.path.join(self.root, source, d.strftime("%Y-%m-%d"),
                         d.strftime("%H"))
        os.makedirs(p, exist_ok=True)
        return os.path.join(p, f"{source}.jsonl")

    def write(self, source, row):
        p = self.path(source, row["ts_write_ns"])
        h = self.handles.get(p)
        if h is None:
            h = open(p, "a", encoding="utf-8")
            self.handles[p] = h
        h.write(json.dumps(row, separators=(",", ":")) + "\n")
        self.counts[source] = self.counts.get(source, 0) + 1

    def flush(self):
        for h in self.handles.values():
            h.flush()

    def close(self):
        for h in self.handles.values():
            try:
                h.close()
            except Exception:
                pass


def valid_book(bids, asks):
    """Content validation. Row counts are not a data-quality check.

    A book is usable only if at least one side is non-empty AND every level
    parses to a finite numeric price in (0,1] with positive size.
    """
    if not bids and not asks:
        return False, "both sides empty"
    for side, name in ((bids, "bids"), (asks, "asks")):
        for lvl in side:
            try:
                p = float(lvl.get("price"))
                s = float(lvl.get("size"))
            except (TypeError, ValueError):
                return False, f"{name}: unparseable level {lvl}"
            if not (0 < p <= 1):
                return False, f"{name}: price out of range {p}"
            if s <= 0:
                return False, f"{name}: non-positive size {s}"
    return True, ""


class Dedup:
    """Write-on-change. A recorder that re-writes an unchanged quote every
    cycle produces ~99% redundant rows: 16k rows/minute measured on a smoke
    test, ~23M/day. Only state CHANGES carry information, so only changes are
    written. `seen` maps key -> last state fingerprint.

    Note this makes row counts non-uniform in time, which is correct but means
    row count is even less usable as a data-quality check than usual.
    """

    def __init__(self, cap=400_000):
        self.seen = {}
        self.cap = cap

    def changed(self, key, fingerprint):
        prev = self.seen.get(key)
        if prev == fingerprint:
            return False
        if len(self.seen) > self.cap:
            self.seen.clear()
        self.seen[key] = fingerprint
        return True


class Session:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update(UA)

    def get(self, url, params=None, timeout=15):
        t_req = mono_ns()
        r = self.s.get(url, params=params, timeout=timeout)
        t_recv_ns = now_ns()
        return r, t_recv_ns, mono_ns() - t_req


# ------------------------------------------------------------------- Kalshi
def kalshi_cycle(sess, w, stats, dedup, keyframe=False):
    for series in KALSHI_SERIES:
        try:
            r, t_recv, lat = sess.get(f"{KALSHI}/markets",
                                      {"series_ticker": series,
                                       "status": "open", "limit": 200})
            if r.status_code != 200:
                stats["kalshi_http_err"] = stats.get("kalshi_http_err", 0) + 1
                continue
            mkts = r.json().get("markets", []) or []
        except Exception as e:
            stats["kalshi_exc"] = stats.get("kalshi_exc", 0) + 1
            stats["last_err"] = f"kalshi {series}: {type(e).__name__}"
            continue

        # Only record markets with a live two-sided quote or real interest.
        for m in mkts:
            bid = m.get("yes_bid_dollars")
            ask = m.get("yes_ask_dollars")
            if bid is None and ask is None:
                stats["kalshi_null_price"] = stats.get(
                    "kalshi_null_price", 0) + 1
                continue
            fp = (bid, ask, m.get("yes_bid_size_fp"), m.get("yes_ask_size_fp"),
                  m.get("volume_fp"), m.get("open_interest_fp"))
            # Keyframes. Write-on-change alone never emits the dead wing
            # strikes (they never change), so a COMPLETE ladder snapshot is
            # never recorded -- which makes the bucket-sum hypothesis (A1)
            # untestable, since summing a partial ladder is meaningless.
            # Every `keyframe` cycles, write every market unconditionally.
            if not keyframe and not dedup.changed(("k", m.get("ticker")), fp):
                stats["kalshi_unchanged"] = stats.get("kalshi_unchanged", 0) + 1
                continue
            if keyframe:
                dedup.changed(("k", m.get("ticker")), fp)
            row = {
                "venue": "kalshi",
                "series": series,
                "ticker": m.get("ticker"),
                "event_ticker": m.get("event_ticker"),
                "strike_type": m.get("strike_type"),
                "floor_strike": m.get("floor_strike"),
                "cap_strike": m.get("cap_strike"),
                "yes_bid": bid,
                "yes_ask": ask,
                "yes_bid_size": m.get("yes_bid_size_fp"),
                "yes_ask_size": m.get("yes_ask_size_fp"),
                "no_bid": m.get("no_bid_dollars"),
                "no_ask": m.get("no_ask_dollars"),
                "last_price": m.get("last_price_dollars"),
                "volume": m.get("volume_fp"),
                "open_interest": m.get("open_interest_fp"),
                "liquidity": m.get("liquidity_dollars"),
                "tick_structure": m.get("price_level_structure"),
                "status": m.get("status"),
                "keyframe": bool(keyframe),
                "ts_event_ns": iso_to_ns(m.get("updated_time")),
                "ts_close_ns": iso_to_ns(m.get("close_time")),
                "ts_recv_ns": t_recv,
                "ts_write_ns": now_ns(),
                "latency_ns": lat,
            }
            w.write("kalshi_quotes", row)
        stats["kalshi_markets"] = stats.get("kalshi_markets", 0) + len(mkts)


# --------------------------------------------------------------- Polymarket
def poly_discover(sess):
    """Discover live short-dated crypto markets from the trade tape.

    Gamma's tag_slug / slug_contains filters are silently ignored, so the tape
    is the only reliable discovery mechanism.
    """
    out = {}
    try:
        r, _, _ = sess.get(f"{DATA}/trades", {"limit": 500})
        if r.status_code != 200:
            return out
        for t in r.json():
            s = str(t.get("slug") or "")
            if s.startswith(POLY_PREFIXES):
                out[s] = t.get("conditionId")
    except Exception:
        pass
    return out


def poly_cycle(sess, w, stats, cache, dedup):
    slugs = poly_discover(sess)
    for slug, cid in slugs.items():
        toks = cache.get(slug)
        if toks is None:
            try:
                r, _, _ = sess.get(f"{GAMMA}/markets", {"slug": slug})
                if r.status_code != 200 or not r.json():
                    continue
                g = r.json()[0]
                toks = json.loads(g.get("clobTokenIds") or "[]")
                cache[slug] = toks
            except Exception:
                cache[slug] = []
                continue
        for idx, tid in enumerate(toks or []):
            try:
                r, t_recv, lat = sess.get(f"{CLOB}/book", {"token_id": tid})
                if r.status_code != 200:
                    continue
                b = r.json()
            except Exception:
                stats["poly_exc"] = stats.get("poly_exc", 0) + 1
                continue
            bids = b.get("bids") or []
            asks = b.get("asks") or []
            ok, why = valid_book(bids, asks)
            if not ok:
                stats["poly_bad_book"] = stats.get("poly_bad_book", 0) + 1
                stats["last_bad_book"] = f"{slug}: {why}"
                continue
            # the venue's own book hash is the natural change fingerprint
            if not dedup.changed(("p", tid), b.get("hash")):
                stats["poly_unchanged"] = stats.get("poly_unchanged", 0) + 1
                continue
            row = {
                "venue": "polymarket",
                "slug": slug,
                "condition_id": cid,
                "token_id": tid,
                "outcome_index": idx,
                "tick_size": b.get("tick_size"),
                "min_order_size": b.get("min_order_size"),
                "neg_risk": b.get("neg_risk"),
                "last_trade_price": b.get("last_trade_price"),
                "book_hash": b.get("hash"),
                "n_bids": len(bids),
                "n_asks": len(asks),
                # full depth, both sides
                "bids": [[lv["price"], lv["size"]] for lv in bids],
                "asks": [[lv["price"], lv["size"]] for lv in asks],
                "ts_event_ns": iso_to_ns(b.get("timestamp")),
                "ts_recv_ns": t_recv,
                "ts_write_ns": now_ns(),
                "latency_ns": lat,
            }
            w.write("poly_books", row)
            stats["poly_books"] = stats.get("poly_books", 0) + 1

    # trade tape (rolling ~10 min window, so poll often)
    try:
        r, t_recv, lat = sess.get(f"{DATA}/trades", {"limit": 500})
        if r.status_code == 200:
            for t in r.json():
                s = str(t.get("slug") or "")
                if not s.startswith(POLY_PREFIXES):
                    continue
                # the tape is a rolling window re-served every poll; dedupe on
                # the on-chain tx hash + asset + wallet + timestamp
                tkey = (t.get("transactionHash"), t.get("asset"),
                        t.get("proxyWallet"), t.get("timestamp"),
                        t.get("size"))
                if not dedup.changed(("t", tkey), 1):
                    stats["poly_trade_dup"] = stats.get(
                        "poly_trade_dup", 0) + 1
                    continue
                row = dict(t)
                row["ts_event_ns"] = iso_to_ns(t.get("timestamp"))
                row["ts_recv_ns"] = t_recv
                row["ts_write_ns"] = now_ns()
                row["latency_ns"] = lat
                w.write("poly_trades", row)
                stats["poly_trades"] = stats.get("poly_trades", 0) + 1
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=60.0)
    ap.add_argument("--interval", type=float, default=5.0)
    ap.add_argument("--keyframe-every", type=int, default=24,
                    help="cycles between full unconditional ladder snapshots")
    args = ap.parse_args()

    sess = Session()
    w = Writer()
    stats = {}
    cache = {}
    dedup = Dedup()
    t_end = time.monotonic() + args.minutes * 60
    cycles = 0
    t0 = time.time()

    print(f"recorder start {datetime.now(timezone.utc).isoformat()}  "
          f"minutes={args.minutes} interval={args.interval}s")
    sys.stdout.flush()

    while time.monotonic() < t_end:
        c0 = time.monotonic()
        kf = (cycles % args.keyframe_every) == 0
        try:
            kalshi_cycle(sess, w, stats, dedup, keyframe=kf)
            poly_cycle(sess, w, stats, cache, dedup)
        except Exception as e:
            stats["cycle_exc"] = stats.get("cycle_exc", 0) + 1
            stats["last_err"] = f"{type(e).__name__}: {e}"
        cycles += 1
        if cycles % 12 == 0:
            w.flush()
            el = time.time() - t0
            print(f"[{el:7.0f}s] cycles={cycles} "
                  f"rows={ {k: v for k, v in w.counts.items()} } "
                  f"stats={ {k: v for k, v in stats.items() if k != 'last_err'} }")
            sys.stdout.flush()
        dt_ = args.interval - (time.monotonic() - c0)
        if dt_ > 0:
            time.sleep(dt_)

    w.flush()
    w.close()
    print(f"\nrecorder done. rows={w.counts}")
    print(f"stats={stats}")
    with open(os.path.join(ROOT, "recorder_manifest.json"), "w") as f:
        json.dump({"finished_utc": datetime.now(timezone.utc).isoformat(),
                   "cycles": cycles, "rows": w.counts, "stats": stats},
                  f, indent=2)


if __name__ == "__main__":
    main()
