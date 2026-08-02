"""Record KXMLBRFI and the first-5-innings families across the whole day.

WHY THIS IS URGENT. KXMLBRFI was shortlisted as "the deepest book on the list"
on the strength of ONE measurement: 301,578 contracts at the touch, 1c spread,
taken at ~08:00 UTC. Re-measured at ~20:00 UTC the same market shows 19
contracts and an 8c spread -- a cost bar of 5.75c instead of 2.24c.

That is LEDGER S012/S013 exactly: "ATP is the thinnest book, 30 lots, 3c
spread" was retracted because it was a single 68-minute window and the full
day read 1.0c / 312 lots. Here the error runs the other way -- the flattering
number was the snapshot.

Depth cannot be backfilled, so the only way to know which figure describes the
market is to record across the full daily cycle, especially the hours around
first pitch.

Content-validated per row, not by row count. Paced, read-only, public.
"""
import datetime as dt
import json
import pathlib
import sys
import time
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]
                       / "market-selection" / "src"))
import kalshi_api as K  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "depth"
SERIES = ["KXMLBRFI", "KXMLBF5", "KXMLBF5TOTAL", "KXMLBF5SPREAD",
          "KXMLBGAME", "KXMLBTOTAL", "KXMLBSPREAD", "KXMLBEXTRAS"]
CYCLE = 240          # 4 minutes
REFRESH = 20         # re-list markets every N cycles
DEPTH = 20


def now():
    return dt.datetime.now(dt.timezone.utc)


def log(m):
    print(f"[{now():%Y-%m-%d %H:%M:%S}] {m}", flush=True)


def pick():
    """Every open market in these series, re-listed live."""
    out = []
    for s in SERIES:
        r = K.get("/markets", {"series_ticker": s, "status": "open",
                               "limit": 1000})
        if r is None or r.status_code != 200:
            continue
        for m in r.json().get("markets", []):
            out.append((s, m["ticker"], m.get("close_time"),
                        m.get("title"), m.get("yes_sub_title")))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mkts, cycle, tot = [], 0, Counter()
    log(f"MLB depth recorder starting -- {len(SERIES)} series, "
        f"{CYCLE}s cycle, {DEPTH} levels/side, read-only")
    while True:
        if cycle % REFRESH == 0:
            try:
                mkts = pick()
            except Exception as e:  # noqa: BLE001
                log(f"re-list failed: {type(e).__name__}: {e}")
                time.sleep(60)
                continue
            log(f"tracking {len(mkts)} markets across "
                f"{len({s for s, *_ in mkts})} series")
        cycle += 1
        t = now()
        d = OUT / f"{t:%Y-%m-%d}" / f"{t:%H}"
        d.mkdir(parents=True, exist_ok=True)
        path = d / "depth.jsonl"
        cyc = Counter()
        t0 = time.time()
        with open(path, "a", encoding="utf-8", buffering=1) as fh:
            for s, tk, close, title, sub in mkts:
                yes, no = K.orderbook(tk, DEPTH)
                ts = now()
                if yes is None and no is None:
                    cyc["http_fail"] += 1
                    continue
                yes, no = yes or [], no or []
                bad = False
                for p, sz in yes + no:
                    if not (0.0 < p < 100.0) or sz < 0:
                        bad = True
                        break
                if bad:
                    cyc["invalid"] += 1
                    continue
                yb, ya, bs, a_s = K.touch(yes, no)
                cyc["rows"] += 1
                if yes or no:
                    cyc["nonempty"] += 1
                if yb is not None and ya is not None:
                    cyc["two_sided"] += 1
                fh.write(json.dumps({
                    "ts": ts.isoformat(), "series": s, "ticker": tk,
                    "close_time": close, "title": title, "yes_sub": sub,
                    "yes": yes, "no": no,
                    "yes_bid_c": yb, "yes_ask_c": ya,
                    "bid_sz": bs, "ask_sz": a_s,
                }) + "\n")
        for k, v in cyc.items():
            tot[k] += v
        r_ = cyc["rows"] or 1
        log(f"cycle {cycle}: {cyc['rows']} rows in {time.time()-t0:.0f}s | "
            f"nonempty {100*cyc['nonempty']/r_:.0f}% "
            f"two-sided {100*cyc['two_sided']/r_:.0f}% | "
            f"invalid {cyc['invalid']} fail {cyc['http_fail']}")
        if cycle % 15 == 0:
            g = tot["nonempty"] / max(tot["rows"], 1)
            log(f"HEALTH {cycle} cycles: rows={tot['rows']} "
                f"nonempty={100*g:.1f}% "
                f"two_sided={100*tot['two_sided']/max(tot['rows'],1):.1f}% "
                f"invalid={tot['invalid']}")
            if tot["rows"] > 300 and g < 0.05:
                log("WARNING: <5% of snapshots carry depth. Writing "
                    "well-formed nothing. CHECK orderbook_fp KEY NAMES.")
        time.sleep(max(20, CYCLE - (time.time() - t0)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
