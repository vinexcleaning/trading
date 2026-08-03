"""Phase 3: external free data recorders.

Sources (all free, public, no auth):
  - BTC/ETH spot trades+book from Coinbase, Kraken, Bitstamp (3 venues)
  - Binance perps: mark price / funding / open interest (public REST)
  - Deribit: DVOL index + BTC option chain summary (public REST)
  - NWS: observations for weather settlement stations
"""

from __future__ import annotations

import signal
import sys
import threading
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.clock import CLOCK, mono_ns, now_ns  # noqa: E402
from kalshi_research.writer import PartitionedWriter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw"
LOG = ROOT / "data" / "recorder_external.log"
STOP = threading.Event()

# Kalshi weather settlement stations (NWS station ids for the KXTEMP*/KXHIGH* cities)
NWS_STATIONS = {
    "DCA": "KDCA", "LAX": "KLAX", "NYC": "KNYC", "CHI": "KMDW",
    "MIA": "KMIA", "AUS": "KAUS", "DEN": "KDEN", "PHIL": "KPHL",
}


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _loop(name: str, fn, interval: float, writer: PartitionedWriter) -> None:
    fails = 0
    while not STOP.is_set():
        try:
            t0 = mono_ns()
            recv = now_ns()
            rows = fn(recv, mono_ns() - t0)
            if rows:
                writer.add_many(rows)
            fails = 0
        except Exception as e:  # noqa: BLE001
            fails += 1
            if fails <= 3 or fails % 20 == 0:
                log(f"[{name}] ERROR({fails}) {type(e).__name__}: {str(e)[:100]}")
        STOP.wait(interval)
    writer.flush()
    log(f"[{name}] stopped rows={writer.rows_written}")


S = requests.Session()
S.headers.update({"User-Agent": "kalshi-research-readonly/0.1 (research)"})


def spot_rows(recv: int, lat: int) -> list[dict]:
    """Best bid/ask + last from three independent venues."""
    out = []
    w = now_ns()
    for venue, url, parse in (
        (
            "coinbase",
            "https://api.exchange.coinbase.com/products/BTC-USD/ticker",
            lambda d: (float(d["bid"]), float(d["ask"]), float(d["price"]), float(d["volume"])),
        ),
        (
            "kraken",
            "https://api.kraken.com/0/public/Ticker?pair=XBTUSD",
            lambda d: (
                float(next(iter(d["result"].values()))["b"][0]),
                float(next(iter(d["result"].values()))["a"][0]),
                float(next(iter(d["result"].values()))["c"][0]),
                float(next(iter(d["result"].values()))["v"][1]),
            ),
        ),
        (
            "bitstamp",
            "https://www.bitstamp.net/api/v2/ticker/btcusd/",
            lambda d: (float(d["bid"]), float(d["ask"]), float(d["last"]), float(d["volume"])),
        ),
    ):
        try:
            t0 = mono_ns()
            d = S.get(url, timeout=10).json()
            bid, ask, last, vol = parse(d)
            out.append(
                {
                    "venue": venue, "symbol": "BTCUSD", "bid": bid, "ask": ask,
                    "last": last, "volume": vol, "event_ns": None,
                    "recv_ns": recv, "write_ns": w, "latency_ns": mono_ns() - t0,
                }
            )
        except Exception:  # noqa: BLE001,S112
            continue
    # ETH from coinbase for the lead-lag test
    try:
        t0 = mono_ns()
        d = S.get("https://api.exchange.coinbase.com/products/ETH-USD/ticker", timeout=10).json()
        out.append(
            {
                "venue": "coinbase", "symbol": "ETHUSD", "bid": float(d["bid"]),
                "ask": float(d["ask"]), "last": float(d["price"]),
                "volume": float(d["volume"]), "event_ns": None,
                "recv_ns": recv, "write_ns": w, "latency_ns": mono_ns() - t0,
            }
        )
    except Exception:  # noqa: BLE001,S110
        pass
    return out


def perp_rows(recv: int, lat: int) -> list[dict]:
    """Perp funding / mark / basis / open interest — vol and regime inputs.

    Binance (451) and Bybit (403) are geo-blocked from this host, so we use
    OKX swaps plus Deribit perpetuals. Both are free and unauthenticated.
    """
    out = []
    w = now_ns()
    for inst in ("BTC-USD-SWAP", "ETH-USD-SWAP"):
        rec: dict = {"venue": "okx", "symbol": inst, "event_ns": None,
                     "recv_ns": recv, "write_ns": w}
        got = False
        try:
            d = S.get("https://www.okx.com/api/v5/public/funding-rate",
                      params={"instId": inst}, timeout=10).json()["data"][0]
            rec.update(
                funding_rate=float(d["fundingRate"]),
                next_funding_ns=int(d["fundingTime"]) * 1_000_000,
            )
            got = True
        except Exception:  # noqa: BLE001,S110
            pass
        try:
            d = S.get("https://www.okx.com/api/v5/market/ticker",
                      params={"instId": inst}, timeout=10).json()["data"][0]
            rec.update(
                last=float(d["last"]), bid=float(d["bidPx"]), ask=float(d["askPx"]),
                vol24h=float(d.get("vol24h") or 0),
                event_ns=int(d["ts"]) * 1_000_000,
            )
            got = True
        except Exception:  # noqa: BLE001,S110
            pass
        try:
            d = S.get("https://www.okx.com/api/v5/public/open-interest",
                      params={"instType": "SWAP", "instId": inst}, timeout=10).json()["data"][0]
            rec["open_interest_usd"] = float(d["oiUsd"])
            rec["open_interest_ccy"] = float(d["oiCcy"])
            got = True
        except Exception:  # noqa: BLE001,S110
            pass
        if got:
            out.append(rec)

    for inst in ("BTC-PERPETUAL", "ETH-PERPETUAL"):
        try:
            r = S.get("https://www.deribit.com/api/v2/public/ticker",
                      params={"instrument_name": inst}, timeout=10).json()["result"]
            out.append(
                {
                    "venue": "deribit", "symbol": inst,
                    "last": r.get("last_price"), "bid": r.get("best_bid_price"),
                    "ask": r.get("best_ask_price"),
                    "index_price": r.get("index_price"),
                    "mark_price": r.get("mark_price"),
                    "funding_rate": r.get("current_funding"),
                    "funding_8h": r.get("funding_8h"),
                    "open_interest_usd": r.get("open_interest"),
                    "event_ns": int(r["timestamp"]) * 1_000_000,
                    "recv_ns": recv, "write_ns": w,
                }
            )
        except Exception:  # noqa: BLE001,S112
            continue
    return out


def deribit_rows(recv: int, lat: int) -> list[dict]:
    """DVOL implied-vol index + BTC index price. Free public endpoint."""
    out = []
    w = now_ns()
    try:
        d = S.get(
            "https://www.deribit.com/api/v2/public/get_index_price",
            params={"index_name": "btc_usd"}, timeout=10,
        ).json()
        out.append(
            {
                "metric": "btc_index_price",
                "value": float(d["result"]["index_price"]),
                "event_ns": None, "recv_ns": recv, "write_ns": w,
            }
        )
    except Exception:  # noqa: BLE001,S110
        pass
    for idx, name in (("btc_usd", "BTC_DVOL"), ("eth_usd", "ETH_DVOL")):
        try:
            d = S.get(
                "https://www.deribit.com/api/v2/public/get_volatility_index_data",
                params={
                    "currency": idx.split("_")[0].upper(),
                    "start_timestamp": int(time.time() * 1000) - 3_600_000,
                    "end_timestamp": int(time.time() * 1000),
                    "resolution": "60",
                },
                timeout=12,
            ).json()
            rows = d.get("result", {}).get("data") or []
            if rows:
                last = rows[-1]
                out.append(
                    {
                        "metric": name, "value": float(last[4]),
                        "event_ns": int(last[0]) * 1_000_000,
                        "recv_ns": recv, "write_ns": w,
                    }
                )
        except Exception:  # noqa: BLE001,S112
            continue
    return out


def deribit_chain_rows(recv: int, lat: int) -> list[dict]:
    """BTC option chain summary -> risk-neutral distribution input."""
    out = []
    w = now_ns()
    try:
        d = S.get(
            "https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
            params={"currency": "BTC", "kind": "option"}, timeout=20,
        ).json()
        for r in d.get("result") or []:
            out.append(
                {
                    "instrument": r.get("instrument_name"),
                    "mark_price": r.get("mark_price"),
                    "mark_iv": r.get("mark_iv"),
                    "bid": r.get("bid_price"), "ask": r.get("ask_price"),
                    "underlying_price": r.get("underlying_price"),
                    "open_interest": r.get("open_interest"),
                    "volume": r.get("volume"),
                    "event_ns": (int(r["creation_timestamp"]) * 1_000_000)
                    if r.get("creation_timestamp") else None,
                    "recv_ns": recv, "write_ns": w,
                }
            )
    except Exception:  # noqa: BLE001,S110
        pass
    return out


def nws_rows(recv: int, lat: int) -> list[dict]:
    """Latest observation per Kalshi weather settlement station."""
    out = []
    w = now_ns()
    for city, stn in NWS_STATIONS.items():
        try:
            d = S.get(
                f"https://api.weather.gov/stations/{stn}/observations/latest",
                timeout=12,
            ).json()
            p = d.get("properties") or {}
            tc = (p.get("temperature") or {}).get("value")
            out.append(
                {
                    "city": city, "station": stn,
                    "temp_c": tc,
                    "temp_f": (tc * 9 / 5 + 32) if tc is not None else None,
                    "dewpoint_c": (p.get("dewpoint") or {}).get("value"),
                    "wind_kph": (p.get("windSpeed") or {}).get("value"),
                    "text": p.get("textDescription"),
                    "event_ns": _iso_ns(p.get("timestamp")),
                    "recv_ns": recv, "write_ns": w,
                }
            )
        except Exception:  # noqa: BLE001,S112
            continue
    return out


def _iso_ns(ts: str | None) -> int | None:
    if not ts:
        return None
    from datetime import datetime

    try:
        return int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1e9)
    except Exception:  # noqa: BLE001
        return None


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)

    def handler(signum, frame):  # noqa: ANN001, ARG001
        STOP.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handler)
        except Exception:  # noqa: BLE001,S110
            pass

    CLOCK.refresh()
    log(f"[main] START external recorders ntp={CLOCK.ntp_offset_s}")

    jobs = [
        ("spot", spot_rows, 2.0, "ext_spot", 3000, 60),
        ("perp", perp_rows, 10.0, "ext_perp", 500, 120),
        ("deribit", deribit_rows, 30.0, "ext_deribit", 300, 180),
        ("deribit_chain", deribit_chain_rows, 300.0, "ext_deribit_chain", 5000, 600),
        ("nws", nws_rows, 300.0, "ext_nws", 200, 600),
    ]
    threads = []
    for name, fn, interval, src, frows, fsecs in jobs:
        wr = PartitionedWriter(DATA, src, flush_rows=frows, flush_seconds=fsecs)
        t = threading.Thread(target=_loop, args=(name, fn, interval, wr), daemon=True)
        t.start()
        threads.append(t)

    while not STOP.is_set():
        STOP.wait(300)
        log("[main] external alive")
    for t in threads:
        t.join(timeout=10)


if __name__ == "__main__":
    main()
