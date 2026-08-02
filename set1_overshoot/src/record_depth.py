"""Overnight order-book depth recorder for live tennis markets.

WHY THIS RUNS FIRST. Kalshi publishes no historical order-book endpoint --
depth exists only in what is recorded live, and every hour not recorded is
gone permanently. Candles are re-pullable any time; this is not.

It matters specifically for Task 1b. The maker model currently assumes one
contract, all-or-nothing, because the candlesticks carry no size. That makes
the reported fill rates an upper bound. With depth-at-touch and queue size,
tomorrow's session can model partial fills at real size instead of assuming
them away.

API COURTESY: single-threaded, one request at a time, paced, with exponential
backoff on 429. Two other Claude Code sessions are hitting the same API.
Read-only public endpoints; no orders, no credentials.
"""
import datetime as dt
import json
import pathlib
import sys
import time

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "depth"
BASE = "https://api.elections.kalshi.com/trade-api/v2"
SERIES = ["KXATPMATCH", "KXWTAMATCH", "KXATPCHALLENGERMATCH",
          "KXITFMATCH", "KXITFWMATCH"]

PACE = 0.55          # seconds between requests -- deliberately gentle
REFRESH_MIN = 20     # re-list open markets this often
DEPTH = 20


def now():
    return dt.datetime.now(dt.timezone.utc)


def log(msg):
    print(f"[{now():%H:%M:%S}] {msg}", flush=True)


def get(sess, url, params, tries=5):
    delay = 1.0
    for i in range(tries):
        try:
            r = sess.get(url, params=params, timeout=30)
            if r.status_code == 429:
                log(f"429 -- backing off {delay:.0f}s")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            if r.status_code >= 500:
                time.sleep(delay)
                delay = min(delay * 2, 30)
                continue
            if r.ok:
                return r.json()
            return None
        except Exception:  # noqa: BLE001
            time.sleep(delay)
            delay = min(delay * 2, 30)
    return None


def open_markets(sess):
    """One market per event, chosen by the SAME outcome-independent rule as the
    universe: lexicographically first ticker. Halves the request load and does
    not read anything post-settlement."""
    by_event = {}
    for s in SERIES:
        body = get(sess, f"{BASE}/markets",
                   {"series_ticker": s, "status": "open", "limit": 1000})
        time.sleep(PACE)
        for m in (body or {}).get("markets", []):
            ev = m.get("event_ticker")
            tk = m.get("ticker")
            if not ev or not tk:
                continue
            if ev not in by_event or tk < by_event[ev][0]:
                by_event[ev] = (tk, s)
    return sorted(by_event.values())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sess = requests.Session()
    mkts, last_refresh = [], None
    n_snap = n_empty = 0

    log("depth recorder starting (single-threaded, read-only)")
    while True:
        if last_refresh is None or (now() - last_refresh).total_seconds() > REFRESH_MIN * 60:
            mkts = open_markets(sess)
            last_refresh = now()
            log(f"tracking {len(mkts)} markets (one per event)")
            if not mkts:
                time.sleep(300)
                continue

        t = now()
        d = OUT / f"{t:%Y-%m-%d}" / f"{t:%H}"
        d.mkdir(parents=True, exist_ok=True)
        path = d / "depth.jsonl"

        cycle_start = time.time()
        with open(path, "a", encoding="utf-8") as fh:
            for tk, series in mkts:
                body = get(sess, f"{BASE}/markets/{tk}/orderbook",
                           {"depth": DEPTH})
                ts = now()
                ob = (body or {}).get("orderbook_fp") or {}
                yes = ob.get("yes_dollars") or []
                no = ob.get("no_dollars") or []
                if not yes and not no:
                    n_empty += 1
                else:
                    n_snap += 1
                fh.write(json.dumps({
                    "ts": ts.isoformat(),
                    "ticker": tk, "series": series,
                    "yes": yes, "no": no,
                }) + "\n")
                time.sleep(PACE)

        el = time.time() - cycle_start
        log(f"cycle {len(mkts)} mkts in {el:.0f}s | snapshots with depth "
            f"{n_snap:,} | empty {n_empty:,} | -> {path.parent.name}")
        # health: if everything is coming back empty, say so loudly
        if n_snap + n_empty > 200 and n_snap == 0:
            log("WARNING: every snapshot is empty -- recorder is writing "
                "nothing useful. Check the endpoint.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
