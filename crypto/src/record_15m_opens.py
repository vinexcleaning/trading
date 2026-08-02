"""Record KXBTC15M quotes in the first 60 s after each window opens.

WHY THIS EXISTS: the fade-the-streak cell (after k consecutive downs, buy the
DOWN side) is the only cell in this project pointing the right way. Costing it
needs the price you could ACTUALLY pay at window open. Settled records carry
degenerate quotes (100% at 0/1), so this input exists only if recorded live.
It accrues in wall-clock time and cannot be recovered later.

Captures BOTH sides explicitly: yes_bid/yes_ask AND no_bid/no_ask with sizes.
The fade trade buys NO, so `no_ask` is the number that decides it.

Supervision: reconnects on any exception, backs off on 429, never exits on
error. Append-only JSONL, one file per UTC date. Content-validated on write --
a row is only written if it parses to a plausible two-sided quote.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}
OUT = r"C:\Users\gianf\crypto\data\btc15m_opens"
SERIES = "KXBTC15M"

WINDOW_S = 60          # capture the first 60 s after open
POLL_S = 2.0           # dense sampling inside the window
IDLE_POLL_S = 20.0     # between windows


def now_ns():
    return time.time_ns()


def valid(row):
    """Content-level validation. Row counts have hidden empty writes twice in
    this project, so nothing is written unless it is a usable quote."""
    try:
        yb, ya = float(row["yes_bid"]), float(row["yes_ask"])
        nb, na = float(row["no_bid"]), float(row["no_ask"])
    except (TypeError, ValueError, KeyError):
        return False, "unparseable"
    for v in (yb, ya, nb, na):
        if not (0.0 <= v <= 1.0):
            return False, f"out of range {v}"
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
            self.fh = open(os.path.join(self.root, f"opens_{d}.jsonl"), "a",
                           encoding="utf-8")
            self.day = d
        self.fh.write(json.dumps(row, separators=(",", ":")) + "\n")
        self.n += 1
        return True

    def flush(self):
        if self.fh:
            self.fh.flush()


def fetch_open_markets(sess):
    r = sess.get(f"{BASE}/markets",
                 params={"series_ticker": SERIES, "status": "open",
                         "limit": 50},
                 headers=UA, timeout=30)
    if r.status_code == 429:
        return None, 429
    if r.status_code != 200:
        return None, r.status_code
    return r.json().get("markets", []) or [], 200


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
    ap.add_argument("--hours", type=float, default=168.0)   # 1 week
    args = ap.parse_args()

    w = Writer()
    sess = requests.Session()
    sess.headers.update(UA)
    t_end = time.monotonic() + args.hours * 3600
    seen_windows = {}
    errors = 0
    backoff = 0.0

    print(f"btc15m open recorder start "
          f"{dt.datetime.now(dt.timezone.utc).isoformat()} "
          f"hours={args.hours}", flush=True)

    while time.monotonic() < t_end:
        try:
            if backoff > 0:
                time.sleep(backoff)
            mkts, code = fetch_open_markets(sess)
            if code == 429:
                backoff = min(60.0, max(5.0, backoff * 2 or 5.0))
                print(f"[429] backing off {backoff:.0f}s", flush=True)
                continue
            backoff = 0.0
            if not mkts:
                time.sleep(IDLE_POLL_S)
                continue

            t_ns = now_ns()
            in_window = False
            for m in mkts:
                open_ns = iso_ns(m.get("open_time"))
                close_ns = iso_ns(m.get("close_time"))
                if open_ns is None:
                    continue
                age_s = (t_ns - open_ns) / 1e9
                if not (0 <= age_s <= WINDOW_S):
                    continue
                in_window = True
                key = m.get("ticker")
                seen_windows.setdefault(key, 0)
                seen_windows[key] += 1
                row = {
                    "series": SERIES,
                    "ticker": key,
                    "event_ticker": m.get("event_ticker"),
                    "floor_strike": m.get("floor_strike"),
                    "open_ts_ns": open_ns,
                    "close_ts_ns": close_ns,
                    "age_since_open_s": round(age_s, 3),
                    "yes_bid": m.get("yes_bid_dollars"),
                    "yes_ask": m.get("yes_ask_dollars"),
                    "yes_bid_size": m.get("yes_bid_size_fp"),
                    "yes_ask_size": m.get("yes_ask_size_fp"),
                    "no_bid": m.get("no_bid_dollars"),
                    "no_ask": m.get("no_ask_dollars"),
                    "last_price": m.get("last_price_dollars"),
                    "volume": m.get("volume_fp"),
                    "open_interest": m.get("open_interest_fp"),
                    "tick_structure": m.get("price_level_structure"),
                    "ts_recv_ns": t_ns,
                    "ts_write_ns": now_ns(),
                }
                w.write(row)

            if w.n and w.n % 50 == 0:
                w.flush()
                print(f"[{dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S')}] "
                      f"rows={w.n} rejected={w.rejected} "
                      f"windows={len(seen_windows)} errors={errors}",
                      flush=True)
            time.sleep(POLL_S if in_window else IDLE_POLL_S)
        except Exception as e:                       # never exit on error
            errors += 1
            backoff = min(60.0, max(5.0, backoff * 2 or 5.0))
            print(f"[err {errors}] {type(e).__name__}: {str(e)[:120]} "
                  f"-> backoff {backoff:.0f}s", flush=True)

    w.flush()
    print(f"done rows={w.n} rejected={w.rejected} "
          f"windows={len(seen_windows)} errors={errors}", flush=True)


if __name__ == "__main__":
    main()
