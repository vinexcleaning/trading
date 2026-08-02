"""Phase 0: probe every data endpoint this project depends on.

Read-only. No auth, no orders. Writes docs/connectivity.json.
"""
import json
import time
import sys
from datetime import datetime, timezone

import requests

TIMEOUT = 20
UA = {"User-Agent": "research-readonly/0.1"}

# (name, method, url, params, what_to_check)
PROBES = [
    # --- Kalshi (public, unauthenticated market data) ---
    ("kalshi_exchange_status", "GET",
     "https://api.elections.kalshi.com/trade-api/v2/exchange/status", None),
    ("kalshi_series_list_crypto", "GET",
     "https://api.elections.kalshi.com/trade-api/v2/series",
     {"category": "Crypto"}),
    ("kalshi_markets_open", "GET",
     "https://api.elections.kalshi.com/trade-api/v2/markets",
     {"limit": 5, "status": "open"}),
    ("kalshi_legacy_host", "GET",
     "https://trading-api.kalshi.com/trade-api/v2/exchange/status", None),

    # --- Polymarket ---
    ("polymarket_gamma_markets", "GET",
     "https://gamma-api.polymarket.com/markets", {"limit": 3, "closed": "false"}),
    ("polymarket_clob_ok", "GET", "https://clob.polymarket.com/", None),
    ("polymarket_clob_markets", "GET", "https://clob.polymarket.com/markets", None),
    ("polymarket_data_api", "GET",
     "https://data-api.polymarket.com/trades", {"limit": 3}),

    # --- Deribit (options / DVOL) ---
    ("deribit_index", "GET",
     "https://www.deribit.com/api/v2/public/get_index_price",
     {"index_name": "btc_usd"}),
    ("deribit_instruments", "GET",
     "https://www.deribit.com/api/v2/public/get_instruments",
     {"currency": "BTC", "kind": "option", "expired": "false"}),

    # --- OKX ---
    ("okx_ticker", "GET",
     "https://www.okx.com/api/v5/market/ticker", {"instId": "BTC-USDT-SWAP"}),

    # --- Spot venues (CF Benchmarks constituents) ---
    ("coinbase_ticker", "GET",
     "https://api.exchange.coinbase.com/products/BTC-USD/ticker", None),
    ("kraken_ticker", "GET",
     "https://api.kraken.com/0/public/Ticker", {"pair": "XBTUSD"}),
    ("bitstamp_ticker", "GET",
     "https://www.bitstamp.net/api/v2/ticker/btcusd/", None),
    ("gemini_ticker", "GET", "https://api.gemini.com/v1/pubticker/btcusd", None),
    ("lmax_public", "GET", "https://public-data-api.london-digital.lmax.com/v1/", None),

    # --- Binance (expected geo-blocked; data.binance.vision may differ) ---
    ("binance_api", "GET",
     "https://api.binance.com/api/v3/ticker/price", {"symbol": "BTCUSDT"}),
    ("binance_vision_root", "GET",
     "https://data.binance.vision/?prefix=data/spot/daily/klines/BTCUSDT/1s/", None),
    ("binance_vision_file_head", "HEAD",
     "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/"
     "BTCUSDT-1m-2026-07-01.zip", None),

    # --- Bybit (expected geo-blocked) ---
    ("bybit_ticker", "GET",
     "https://api.bybit.com/v5/market/tickers",
     {"category": "linear", "symbol": "BTCUSDT"}),

    # --- CF Benchmarks (the Kalshi settlement source) ---
    ("cfbenchmarks_api", "GET",
     "https://www.cfbenchmarks.com/api/v1/indices", None),

    # --- Polygon on-chain indexers (Polymarket fills) ---
    ("polygon_rpc", "POST", "https://polygon-rpc.com", None),
    ("polymarket_subgraph_goldsky", "POST",
     "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/"
     "subgraphs/orderbook-subgraph/prod/gn", None),
]


def probe(name, method, url, params):
    rec = {"name": name, "url": url, "method": method}
    t0 = time.perf_counter()
    try:
        if method == "POST":
            body = {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber",
                    "params": []}
            if "goldsky" in url:
                body = {"query": "{ _meta { block { number } } }"}
            r = requests.post(url, json=body, timeout=TIMEOUT, headers=UA)
        elif method == "HEAD":
            r = requests.head(url, timeout=TIMEOUT, headers=UA,
                              allow_redirects=True)
        else:
            r = requests.get(url, params=params, timeout=TIMEOUT, headers=UA)
        rec["status"] = r.status_code
        rec["ms"] = round((time.perf_counter() - t0) * 1000)
        rec["content_length"] = len(r.content)
        body = r.text[:400]
        rec["snippet"] = body.replace("\n", " ")[:400]
        rec["ok"] = 200 <= r.status_code < 300
    except Exception as e:
        rec["status"] = None
        rec["ms"] = round((time.perf_counter() - t0) * 1000)
        rec["ok"] = False
        rec["error"] = f"{type(e).__name__}: {str(e)[:220]}"
    return rec


def main():
    out = {"probed_at_utc": datetime.now(timezone.utc).isoformat(),
           "results": []}
    for name, method, url, params in PROBES:
        rec = probe(name, method, url, params)
        out["results"].append(rec)
        flag = "OK " if rec["ok"] else "FAIL"
        print(f"{flag} {name:34s} {str(rec['status']):>5} {rec['ms']:>6}ms  "
              f"{rec.get('error', rec.get('snippet',''))[:110]}")
        sys.stdout.flush()
    with open(r"C:\Users\gianf\crypto\docs\connectivity.json", "w") as f:
        json.dump(out, f, indent=2)
    n_ok = sum(1 for r in out["results"] if r["ok"])
    print(f"\n{n_ok}/{len(out['results'])} endpoints reachable")


if __name__ == "__main__":
    main()
