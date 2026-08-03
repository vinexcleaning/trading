"""Phase 3: tiered Kalshi recorder. Read-only. Runs until killed.

Budget: measured safe sustained rate is 15 req/s (0% 429). We run ~8 req/s.
  - exchange-wide trades feed      ~1.0 req/s
  - tier1 full order books         ~4.0 req/s (rotating)
  - tier2 top-of-book              ~2.0 req/s (rotating)
  - universe refresh               occasional
"""

from __future__ import annotations

import json
import signal
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kalshi_research.api import KalshiPublicClient  # noqa: E402
from kalshi_research.clock import CLOCK, mono_ns, now_ns, parse_iso_ns  # noqa: E402
from kalshi_research.writer import PartitionedWriter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw"
LOG = ROOT / "data" / "recorder_kalshi.log"

STOP = threading.Event()

# Series we most want deep books on. KXBTC15M markets are minted continuously.
TIER1_SERIES = [
    "KXBTC15M",
    "KXBTC",
    "KXETH",
    "KXBTCD",
    "KXETHD",
    "KXINXU",
    "KXNASDAQ100U",
    "KXINX",
    "KXNASDAQ100",
]
TIER1_WEATHER = [
    "KXTEMPDCH",
    "KXTEMPLAXH",
    "KXTEMPNYH",
    "KXTEMPCHIH",
    "KXTEMPMIAH",
    "KXTEMPAUSH",
    "KXTEMPDENH",
    "KXTEMPPHILH",
]


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _ob_rows(ticker: str, ob: dict, recv_ns: int, mono: int) -> list[dict]:
    """Flatten an orderbook snapshot into one row per (side, level)."""
    fp = ob.get("orderbook_fp") or ob.get("orderbook") or {}
    rows = []
    w = now_ns()
    for side_key, side in (("yes_dollars", "yes"), ("no_dollars", "no")):
        levels = fp.get(side_key) or []
        for depth_i, lvl in enumerate(levels):
            try:
                px, sz = float(lvl[0]), float(lvl[1])
            except (TypeError, ValueError, IndexError):
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "side": side,
                    "price": px,
                    "size": sz,
                    "depth_i": depth_i,
                    "n_levels": len(levels),
                    "event_ns": None,  # REST snapshot: exchange event time not exposed
                    "recv_ns": recv_ns,
                    "write_ns": w,
                    "mono_ns": mono,
                }
            )
    return rows


def trades_worker(c: KalshiPublicClient) -> None:
    """Exchange-wide trades feed. Dedup by trade_id, walk forward only."""
    w = PartitionedWriter(DATA, "kalshi_trades", flush_rows=1500, flush_seconds=45)
    seen: set[str] = set()
    seen_order: list[str] = []
    n = 0
    while not STOP.is_set():
        try:
            t_req = mono_ns()
            recv = now_ns()
            d = c.get("/markets/trades", {"limit": 200})
            lat_ns = mono_ns() - t_req
            rows = []
            for t in d.get("trades") or []:
                tid = t.get("trade_id")
                if not tid or tid in seen:
                    continue
                seen.add(tid)
                seen_order.append(tid)
                rows.append(
                    {
                        "trade_id": tid,
                        "ticker": t.get("ticker"),
                        "count": float(t.get("count_fp") or 0),
                        "yes_price": float(t.get("yes_price_dollars") or 0),
                        "no_price": float(t.get("no_price_dollars") or 0),
                        "taker_outcome_side": t.get("taker_outcome_side"),
                        "taker_book_side": t.get("taker_book_side"),
                        "is_block_trade": bool(t.get("is_block_trade")),
                        "event_ns": parse_iso_ns(t.get("created_time")),
                        "recv_ns": recv,
                        "write_ns": now_ns(),
                        "latency_ns": lat_ns,
                    }
                )
            if rows:
                w.add_many(rows)
                n += len(rows)
            if len(seen_order) > 60000:
                for old in seen_order[:20000]:
                    seen.discard(old)
                del seen_order[:20000]
            if n and n % 2000 < len(rows):
                log(f"[trades] {n} new trades recorded")
            w.maybe_flush()
        except Exception as e:  # noqa: BLE001
            log(f"[trades] ERROR {type(e).__name__}: {e}")
            STOP.wait(5)
        STOP.wait(1.0)
    w.flush()
    log(f"[trades] stopped, rows_written={w.rows_written}")


TIER1_CAP = 24
TIER2_CAP = 140


def _near_money(markets: list[dict], k: int) -> list[str]:
    """Pick the k markets whose mid price is closest to 50c (most informative book)."""

    def dist(m: dict) -> float:
        try:
            b = float(m.get("yes_bid_dollars") or 0)
            a = float(m.get("yes_ask_dollars") or 0)
        except (TypeError, ValueError):
            return 9.0
        if a <= 0 and b <= 0:
            return 9.0
        mid = (b + a) / 2 if (b > 0 and a > 0) else (b or a)
        return abs(mid - 0.5)

    return [m["ticker"] for m in sorted(markets, key=dist)[:k]]


def universe_worker(c: KalshiPublicClient, state: dict) -> None:
    """Refresh tier1 (near-money in priority series) and tier2 (top-volume singles).

    tier1 is capped so a full rotation stays fast enough for 15-minute markets.
    tier2 comes from a cached watchlist so we never re-walk all 551k markets.
    """
    wl_path = ROOT / "data" / "watchlist_tier2.json"
    while not STOP.is_set():
        try:
            t1: list[str] = []
            # every currently tradeable KXBTC15M market (there are only ~1-2)
            for s in ("KXBTC15M", "KXETH15M", "KXINX15M"):
                try:
                    d = c.get("/markets", {"series_ticker": s, "status": "open", "limit": 50})
                    t1 += [m["ticker"] for m in (d.get("markets") or [])]
                except Exception:  # noqa: BLE001,S112
                    continue
            # near-money strikes from the priority hourly/daily series
            per_series = max(1, (TIER1_CAP - len(t1)) // 6)
            for s in ("KXBTC", "KXETH", "KXINXU", "KXNASDAQ100U", "KXBTCD", "KXETHD"):
                try:
                    d = c.get("/markets", {"series_ticker": s, "status": "open", "limit": 200})
                except Exception:  # noqa: BLE001,S112
                    continue
                t1 += _near_money(d.get("markets") or [], per_series)
            t1 = list(dict.fromkeys(t1))[:TIER1_CAP]
            state["tier1"] = t1

            # tier2 from cached watchlist, refreshed by refresh_watchlist.py
            t2: list[str] = []
            if wl_path.exists():
                try:
                    t2 = json.loads(wl_path.read_text()).get("tickers") or []
                except Exception:  # noqa: BLE001,S110
                    pass
            state["tier2"] = [t for t in t2 if t not in set(t1)][:TIER2_CAP]
            log(f"[universe] tier1={len(state['tier1'])} tier2={len(state['tier2'])}")
        except Exception as e:  # noqa: BLE001
            log(f"[universe] ERROR {type(e).__name__}: {e}")
        STOP.wait(180)


def book_worker(c: KalshiPublicClient, state: dict, tier: str, rps: float) -> None:
    w = PartitionedWriter(
        DATA, f"kalshi_book_{tier}", flush_rows=4000, flush_seconds=60
    )
    interval = 1.0 / rps
    i = 0
    while not STOP.is_set():
        tks = state.get(tier) or []
        if not tks:
            STOP.wait(5)
            continue
        tk = tks[i % len(tks)]
        i += 1
        try:
            t_req = mono_ns()
            recv = now_ns()
            # `orderbook_fp` sits at the TOP level of the response. Unwrapping a
            # non-existent "orderbook" key here silently yielded {} on every call,
            # so every snapshot was written as an empty marker. _ob_rows handles
            # both shapes, so pass the raw response through.
            ob = c.get(f"/markets/{tk}/orderbook")
            mono = mono_ns()
            rows = _ob_rows(tk, ob, recv, mono)
            if rows:
                for r in rows:
                    r["latency_ns"] = mono - t_req
                w.add_many(rows)
            else:
                # empty book still informative: record a marker row
                w.add(
                    {
                        "ticker": tk,
                        "side": "empty",
                        "price": None,
                        "size": None,
                        "depth_i": -1,
                        "n_levels": 0,
                        "event_ns": None,
                        "recv_ns": recv,
                        "write_ns": now_ns(),
                        "mono_ns": mono,
                        "latency_ns": mono - t_req,
                    }
                )
        except Exception as e:  # noqa: BLE001
            log(f"[{tier}] {tk} ERROR {type(e).__name__}: {str(e)[:80]}")
            STOP.wait(2)
        w.maybe_flush()
        STOP.wait(interval)
    w.flush()
    log(f"[{tier}] stopped, rows_written={w.rows_written}")


def status_worker(c: KalshiPublicClient, state: dict) -> None:
    """Record exchange trading status. Kalshi halts trading daily (observed
    2026-07-30: trading_active=false 07:00-09:00 UTC), which explains empty
    trade feeds and absent active markets. Recording it makes gaps explicable.
    """
    w = PartitionedWriter(DATA, "kalshi_status", flush_rows=50, flush_seconds=120)
    prev = None
    while not STOP.is_set():
        try:
            recv = now_ns()
            d = c.get("/exchange/status")
            act = bool(d.get("trading_active"))
            state["trading_active"] = act
            w.add(
                {
                    "trading_active": act,
                    "exchange_active": bool(d.get("exchange_active")),
                    "raw": json.dumps(d),
                    "event_ns": None,
                    "recv_ns": recv,
                    "write_ns": now_ns(),
                }
            )
            if act != prev:
                log(f"[status] trading_active {prev} -> {act}")
                prev = act
        except Exception as e:  # noqa: BLE001
            log(f"[status] ERROR {type(e).__name__}: {e}")
        w.maybe_flush()
        STOP.wait(30)
    w.flush()


def clock_worker() -> None:
    while not STOP.is_set():
        CLOCK.refresh()
        log(f"[clock] ntp offset={CLOCK.ntp_offset_s} server={CLOCK.ntp_server}")
        STOP.wait(3600)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)

    def handler(signum, frame):  # noqa: ANN001, ARG001
        log(f"[main] signal {signum}, stopping")
        STOP.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handler)
        except Exception:  # noqa: BLE001,S110
            pass

    CLOCK.refresh()
    log(f"[main] START ntp_offset={CLOCK.ntp_offset_s}s server={CLOCK.ntp_server}")
    (ROOT / "data" / "recorder_start.json").write_text(
        json.dumps({"start_ns": now_ns(), "clock": CLOCK.as_dict()}, indent=1)
    )

    c = KalshiPublicClient(rps=8.0)
    state: dict = {"tier1": [], "tier2": []}

    threads = [
        threading.Thread(target=status_worker, args=(c, state), daemon=True),
        threading.Thread(target=universe_worker, args=(c, state), daemon=True),
        threading.Thread(target=trades_worker, args=(c,), daemon=True),
        threading.Thread(target=book_worker, args=(c, state, "tier1", 4.0), daemon=True),
        threading.Thread(target=book_worker, args=(c, state, "tier2", 2.0), daemon=True),
        threading.Thread(target=clock_worker, daemon=True),
    ]
    for t in threads:
        t.start()

    last = time.monotonic()
    while not STOP.is_set():
        STOP.wait(120)
        if time.monotonic() - last > 100:
            log(f"[main] alive req={c.n_req} 429={c.n_429}")
            last = time.monotonic()
    for t in threads:
        t.join(timeout=10)
    log("[main] STOPPED")


if __name__ == "__main__":
    main()
