"""v2 — record 15-minute crypto OPENS for EVERY asset, not just BTC.

v1 covered KXBTC15M only, so every non-BTC asset would have been a week behind.
Marginal cost of adding the rest is ~zero: one extra /markets call per series
per poll, and only inside the 60-second post-open window.

Same schema as v1 plus `series`, so v1 and v2 files concatenate cleanly.

Supervised: never exits on error, exponential backoff on 429, append-only,
per-row content validation (rejects unparseable / crossed / empty).
Single-threaded and paced — two other Claude sessions share this API.
"""
import argparse
import datetime as dt
import json
import os
import time

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}
OUT = r"C:\Users\gianf\crypto\data\btc15m_opens"

WINDOW_S = 60
POLL_S = 2.0
IDLE_POLL_S = 15.0


def now_ns():
    return time.time_ns()


def discover_15m_series(sess):
    """Every crypto series on a fifteen-minute (or shorter) cadence."""
    out = []
    try:
        r = sess.get(f"{BASE}/series", params={"category": "Crypto"},
                     headers=UA, timeout=40)
        if r.status_code != 200:
            return out
        for s in r.json().get("series", []) or []:
            freq = str(s.get("frequency") or "")
            tk = s.get("ticker") or ""
            if freq in ("fifteen_min", "five_min", "one_min"):
                out.append({"ticker": tk, "freq": freq,
                            "fee_type": s.get("fee_type"),
                            "fee_multiplier": s.get("fee_multiplier")})
    except Exception:
        pass
    return out


def valid(row):
    try:
        yb, ya = float(row["yes_bid"]), float(row["yes_ask"])
        nb, na = float(row["no_bid"]), float(row["no_ask"])
    except (TypeError, ValueError, KeyError):
        return False, "unparseable"
    for v in (yb, ya, nb, na):
        if not (0.0 <= v <= 1.0):
            return False, "out of range"
    if ya < yb or na < nb:
        return False, "crossed"
    if ya <= 0 and na <= 0:
        return False, "both sides empty"
    if not row.get("ticker") or not row.get("open_ts_ns"):
        return False, "missing key field"
    return True, ""


class Writer:
    def __init__(self, root=OUT):
        self.root = root
        os.makedirs(root, exist_ok=True)
        self.fh = None
        self.day = None
        self.n = 0
        self.rejected = 0

    def write(self, row):
        ok, why = valid(row)
        if not ok:
            self.rejected += 1
            return False
        d = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
        if d != self.day:
            if self.fh:
                self.fh.close()
            self.fh = open(os.path.join(self.root, f"opens_all_{d}.jsonl"),
                           "a", encoding="utf-8")
            self.day = d
        self.fh.write(json.dumps(row, separators=(",", ":")) + "\n")
        self.n += 1
        return True

    def flush(self):
        if self.fh:
            self.fh.flush()


def iso_ns(s):
    if not s:
        return None
    try:
        return int(dt.datetime.fromisoformat(
            s.replace("Z", "+00:00")).timestamp() * 10**9)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=168.0)
    args = ap.parse_args()

    sess = requests.Session()
    sess.headers.update(UA)
    w = Writer()

    series = discover_15m_series(sess)
    print(f"v2 open recorder start "
          f"{dt.datetime.now(dt.timezone.utc).isoformat()}", flush=True)
    print(f"discovered {len(series)} short-cadence crypto series:", flush=True)
    for s in series:
        print(f"    {s['ticker']:<22} {s['freq']:<14} "
              f"fee_type={s['fee_type']} mult={s['fee_multiplier']}",
              flush=True)
    tickers = [s["ticker"] for s in series]
    if not tickers:
        print("no series discovered, exiting", flush=True)
        return

    t_end = time.monotonic() + args.hours * 3600
    backoff = 0.0
    errors = 0
    seen = {}

    while time.monotonic() < t_end:
        try:
            if backoff > 0:
                time.sleep(backoff)
            in_window = False
            for st in tickers:
                r = sess.get(f"{BASE}/markets",
                             params={"series_ticker": st, "status": "open",
                                     "limit": 50},
                             headers=UA, timeout=30)
                if r.status_code == 429:
                    backoff = min(60.0, max(5.0, backoff * 2 or 5.0))
                    print(f"[429] backoff {backoff:.0f}s", flush=True)
                    break
                if r.status_code != 200:
                    continue
                backoff = 0.0
                t_ns = now_ns()
                for m in r.json().get("markets", []) or []:
                    open_ns = iso_ns(m.get("open_time"))
                    if open_ns is None:
                        continue
                    age = (t_ns - open_ns) / 1e9
                    if not (0 <= age <= WINDOW_S):
                        continue
                    in_window = True
                    seen[m.get("ticker")] = 1
                    w.write({
                        "series": st,
                        "ticker": m.get("ticker"),
                        "event_ticker": m.get("event_ticker"),
                        "floor_strike": m.get("floor_strike"),
                        "open_ts_ns": open_ns,
                        "close_ts_ns": iso_ns(m.get("close_time")),
                        "age_since_open_s": round(age, 3),
                        "yes_bid": m.get("yes_bid_dollars"),
                        "yes_ask": m.get("yes_ask_dollars"),
                        "yes_bid_size": m.get("yes_bid_size_fp"),
                        "yes_ask_size": m.get("yes_ask_size_fp"),
                        "no_bid": m.get("no_bid_dollars"),
                        "no_ask": m.get("no_ask_dollars"),
                        "no_bid_size": m.get("no_bid_size_fp"),
                        "no_ask_size": m.get("no_ask_size_fp"),
                        "last_price": m.get("last_price_dollars"),
                        "volume": m.get("volume_fp"),
                        "open_interest": m.get("open_interest_fp"),
                        "liquidity": m.get("liquidity_dollars"),
                        "tick_structure": m.get("price_level_structure"),
                        "status": m.get("status"),
                        "ts_recv_ns": t_ns,
                        "ts_write_ns": now_ns(),
                    })
                time.sleep(0.12)          # pace between series
            if w.n and w.n % 100 < len(tickers):
                w.flush()
                print(f"[{dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S')}]"
                      f" rows={w.n} rejected={w.rejected} "
                      f"windows={len(seen)} errors={errors}", flush=True)
            time.sleep(POLL_S if in_window else IDLE_POLL_S)
        except Exception as e:
            errors += 1
            backoff = min(60.0, max(5.0, backoff * 2 or 5.0))
            print(f"[err {errors}] {type(e).__name__}: {str(e)[:110]}",
                  flush=True)

    w.flush()
    print(f"done rows={w.n} rejected={w.rejected} windows={len(seen)}",
          flush=True)


if __name__ == "__main__":
    main()
