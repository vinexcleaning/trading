"""STANDING BACKLOG #4 — verify every recorder is writing REAL CONTENT.

One line per check, suitable for a Monitor. Emits OK only when content
assertions pass, and emits a loud line when they do not. Row counts alone are
never accepted: both prior incidents in this project had correct row counts.
"""
import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")
NOW = datetime.now(timezone.utc)


def tail_rows(path, n=400):
    out = []
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 900_000))
            chunk = fh.read().decode("utf-8", "replace")
    except OSError as e:
        return None, f"unreadable: {e}"
    for line in chunk.split("\n")[1:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out[-n:], None


def check_depth():
    files = sorted(glob.glob(os.path.join(DATA, "depth_broad", "*", "*",
                                          "depth.jsonl")))
    if not files:
        return "DEPTH FAIL: no files at all"
    latest = files[-1]
    age_min = (NOW.timestamp() - os.path.getmtime(latest)) / 60
    rows, err = tail_rows(latest)
    if err:
        return f"DEPTH FAIL: {err}"
    if not rows:
        return f"DEPTH FAIL: {latest} has no parseable rows"
    n = len(rows)
    nonempty = sum(1 for d in rows if (d.get("yes") or d.get("no")))
    two = sum(1 for d in rows if d.get("yes_bid_c") is not None
              and d.get("yes_ask_c") is not None)
    bad_price = 0
    for d in rows:
        for p, _s in (d.get("yes") or []) + (d.get("no") or []):
            if not (0.0 < p < 100.0):
                bad_price += 1
    stale = 0
    for d in rows:
        try:
            ts = datetime.fromisoformat(d["ts"])
            if (NOW - ts) > timedelta(minutes=30):
                stale += 1
        except (KeyError, ValueError):
            stale += 1
    series = len({d.get("series") for d in rows})
    ok = (nonempty / n > 0.5 and bad_price == 0 and age_min < 15
          and stale / n < 0.5)
    return (f"DEPTH {'OK ' if ok else 'FAIL'} last={os.path.basename(os.path.dirname(latest))} "
            f"age={age_min:.1f}min rows={n} nonempty={100*nonempty/n:.1f}% "
            f"two_sided={100*two/n:.1f}% badprice={bad_price} "
            f"stale={100*stale/n:.0f}% series={series}")


def check_backfill():
    d = os.path.join(DATA, "tape_pmxt_window")
    done = sorted(glob.glob(os.path.join(d, "trades_*.jsonl")))
    part = glob.glob(os.path.join(d, "*.part"))
    gb = sum(os.path.getsize(f) for f in done + part) / 1e9
    detail = ""
    if part:
        p = part[0]
        rows, _ = tail_rows(p, 50)
        if rows:
            oldest = min(r.get("created_time", "") for r in rows)
            detail = f" working={os.path.basename(p)[:26]} at={oldest[:19]}"
    return (f"BACKFILL days_complete={len(done)} in_flight={len(part)} "
            f"{gb:.1f}GB{detail}")


def check_mirror():
    d = os.path.join(DATA, "pmxt")
    pq = glob.glob(os.path.join(d, "*.parquet"))
    bad = glob.glob(os.path.join(d, "*.BAD*"))
    gb = sum(os.path.getsize(f) for f in pq) / 1e9
    return f"MIRROR files={len(pq)}/662 {gb:.1f}GB bad={len(bad)}"


if __name__ == "__main__":
    print(f"[{NOW:%H:%M:%S}] " + check_depth(), flush=True)
    print(f"[{NOW:%H:%M:%S}] " + check_backfill(), flush=True)
    print(f"[{NOW:%H:%M:%S}] " + check_mirror(), flush=True)
