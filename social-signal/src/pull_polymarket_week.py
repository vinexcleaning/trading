"""Copy one week of the Polymarket order-book archive before it is taken down.

**Authorised by the user on 2026-08-14: "take one week, about 68GB. Not all of
it."** He also corrected a real error of mine — I offered "all of it, 1.15 TB"
without ever checking his disk. There is ~781 GB free, so the full archive was
never actually an option and one of the three choices I gave him was fictional.

**Why the raw files are KEPT rather than filtered.** The Kalshi puller streams
each hour, keeps two tennis series and discards the rest, because the scope was
already decided there. **Nothing here has decided what Polymarket scope matters
yet**, and the host is under a shutdown request — so filtering now would throw
away irreplaceable data to answer a question nobody has asked. He sized and
approved ~68 GB; that is what this stores.

**Coverage, measured 2026-08-13 by one HEAD per day, not assumed:** the archive
runs 2026-04-14 to 2026-08-09, 118 consecutive days, zero gaps, ~9.7 GB/day.
This takes the most recent seven days.

    python src/pull_polymarket_week.py
    python src/pull_polymarket_week.py --since 2026-08-03 --until 2026-08-09
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

HOST = "https://r2v2.pmxt.dev"
NAME = "polymarket_orderbook_{d}T{h:02d}.parquet"
OUT = os.path.join(db.DATA, "polymarket_archive")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/127.0 Safari/537.36"}
PACE = 3.0          # somebody else's bandwidth, and he is already under pressure


def fetch(url: str, retries: int = 3) -> bytes:
    """Return the body, or raise. **Never returns empty on failure** — a refusal
    and a zero-byte file must not look the same (GUARDS #25)."""
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=900) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            if attempt >= retries:
                raise RuntimeError(f"{url} refused after {retries + 1} tries "
                                   f"({last})") from e
            wait = 15 * (attempt + 1)
            print(f"    {last}; retrying in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(last)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-08-03")
    ap.add_argument("--until", default="2026-08-09")   # inclusive
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    d0 = dt.date.fromisoformat(args.since)
    d1 = dt.date.fromisoformat(args.until)
    targets = []
    d = d0
    while d <= d1:
        for h in range(24):
            targets.append((d.isoformat(), h))
        d += dt.timedelta(days=1)

    print(f"{len(targets)} hourly files, {args.since} .. {args.until}")
    print(f"  -> {OUT}\n", flush=True)

    got = skipped = failed = 0
    total = 0
    missing = []
    t0 = time.time()
    for i, (ds, h) in enumerate(targets, 1):
        name = NAME.format(d=ds, h=h)
        path = os.path.join(OUT, name)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            skipped += 1
            total += os.path.getsize(path)
            continue
        try:
            blob = fetch(f"{HOST}/{name}")
        except RuntimeError as e:
            # Recorded by name. A missing hour is a hole in an irreplaceable
            # archive and must never be silent.
            print(f"  [{i}/{len(targets)}] {ds}T{h:02d} FAILED: {e}", flush=True)
            failed += 1
            missing.append(f"{ds}T{h:02d}")
            continue
        if blob[:4] != b"PAR1":
            print(f"  [{i}/{len(targets)}] {ds}T{h:02d} NOT PARQUET "
                  f"({len(blob)}b, starts {blob[:16]!r}) — not saved", flush=True)
            failed += 1
            missing.append(f"{ds}T{h:02d}")
            continue
        tmp = path + ".part"
        with open(tmp, "wb") as fh:
            fh.write(blob)
        os.replace(tmp, path)          # never leave a half file looking whole
        got += 1
        total += len(blob)
        if got % 10 == 0 or i == len(targets):
            mins = (time.time() - t0) / 60
            print(f"  [{i}/{len(targets)}] {ds}T{h:02d}  "
                  f"{total/1e9:.1f} GB on disk, {got} new, {mins:.0f} min",
                  flush=True)
        time.sleep(PACE)

    print(f"\nnew={got} skipped={skipped} failed={failed} "
          f"{total/1e9:.1f} GB  {(time.time()-t0)/60:.0f} min")
    if missing:
        print(f"  MISSING HOURS ({len(missing)}): {missing}")
        print("  These are holes in an archive that cannot be re-obtained. "
              "Re-run to retry them.")
    else:
        print("  no gaps")
    db.log(db.connect(), "pull_polymarket",
           f"new={got} skipped={skipped} failed={failed} gb={total/1e9:.1f}")


if __name__ == "__main__":
    main()
