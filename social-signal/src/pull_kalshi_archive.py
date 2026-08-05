"""Rescue the Kalshi order-book window that Kalshi itself has already dropped.

`archive.pmxt.dev` holds Kalshi order-book data for **15 May – 11 June 2026**.
Kalshi's own API is a ~69-day window and closed markets 404, so as of 4 Aug 2026
everything before roughly **27 May** is already unobtainable from the venue.
**That slice shrinks by one day per day** and the archive's Kalshi feed is dead
at 11 June, so it never grows back.

**What it actually is** — measured by downloading one file and opening it, after
this project first got this wrong by reading the directory listing and inferring
"hourly snapshots" from the filename cadence:

    kalshi_orderbook_2026-05-17T02.parquet
      128,739,737 bytes · 20,723,041 rows · ONE hour
      18,937,521 orderbook_delta + 1,785,520 orderbook_snapshot
      microsecond timestamps, full yes_bids/no_bids price-size ladders
      642,054 distinct tickers — incl. 97 KXATPMATCH/KXWTAMATCH and
      126,704 tennis rows in that single hour

Hourly is the **batching**, not the resolution. This is finer than this repo's
own 0.55 s depth recorder.

**Why it filters rather than hoarding.** The full window is ~288 files ≈ 37 GB
pulled from a volunteer-run archive. Tennis is ~0.6% of rows, so streaming each
hour, keeping only the tickers asked for and discarding the raw turns 37 GB of
transfer into a few hundred MB on disk. The transfer still costs them, so it is
paced and it is resumable — a re-run never re-downloads a file it already has.

    python src/pull_kalshi_archive.py --list
    python src/pull_kalshi_archive.py --since 2026-05-15 --until 2026-05-27
    python src/pull_kalshi_archive.py --prefixes KXATPMATCH,KXWTAMATCH,KXBTC
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

INDEX = "https://archive.pmxt.dev/Kalshi"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/127.0 Safari/537.36")
OUT = os.path.join(db.DATA, "kalshi_archive")
os.makedirs(OUT, exist_ok=True)

# The series this repo actually trades, per STATUS.md. Everything else in the
# hour is dropped unread.
DEFAULT_PREFIXES = ("KXATPMATCH", "KXWTAMATCH")

PACE = 3.0          # seconds between file downloads; somebody else's bandwidth
FILE_RE = re.compile(r"(kalshi_orderbook_(\d{4}-\d{2}-\d{2})T(\d{2})\.parquet)")
HREF_RE = re.compile(r'href="(https?://[^"]*kalshi_orderbook_[^"]*\.parquet)"')


def fetch(url: str, timeout: int = 300, retries: int = 3) -> bytes:
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if attempt >= retries:
                raise
            wait = 10 * (attempt + 1)
            print(f"    {type(e).__name__}; retrying in {wait}s", flush=True)
            time.sleep(wait)
    return b""


def index_pages(max_pages: int = 40):
    """Walk the paginated listing and yield (date, hour, url).

    The file URLs are on a SEPARATE host (`r2kalshi.pmxt.dev`), not under the
    listing path. Guessing `/data/Kalshi/<name>` returns the SPA shell with a
    200, which is exactly the failure mode this project keeps writing down:
    a 200 is not evidence you fetched the thing you asked for.
    """
    seen = set()
    for page in range(1, max_pages + 1):
        url = INDEX if page == 1 else f"{INDEX}?page={page}"
        try:
            html = fetch(url, timeout=90).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            print(f"  index page {page} failed: {e}")
            break
        hrefs = HREF_RE.findall(html)
        if not hrefs:
            break
        fresh = 0
        for h in hrefs:
            m = FILE_RE.search(h)
            if not m or h in seen:
                continue
            seen.add(h)
            fresh += 1
            yield m.group(2), m.group(3), h
        if fresh == 0:
            break
        time.sleep(1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-05-15")
    ap.add_argument("--until", default="2026-05-27",
                    help="exclusive-ish upper bound; the default is the slice "
                         "Kalshi's own 69-day window has already dropped")
    ap.add_argument("--prefixes", default=",".join(DEFAULT_PREFIXES))
    ap.add_argument("--list", action="store_true",
                    help="enumerate what would be pulled and stop")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    prefixes = tuple(p.strip() for p in args.prefixes.split(",") if p.strip())
    print(f"window {args.since} .. {args.until}   prefixes {prefixes}")

    targets = [(d, h, u) for d, h, u in index_pages()
               if args.since <= d <= args.until]
    targets.sort()
    if args.limit:
        targets = targets[:args.limit]
    print(f"{len(targets)} hourly files in the window")
    if args.list:
        for d, h, u in targets[:10]:
            print(f"  {d}T{h}  {u}")
        print(f"  ... ({len(targets)} total)")
        return

    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    con = db.connect()
    done = kept_rows = skipped = failed = 0
    t_start = time.time()
    bytes_in = 0

    for i, (d, h, url) in enumerate(targets, 1):
        out_path = os.path.join(OUT, f"kalshi_{d}T{h}.parquet")
        if os.path.exists(out_path):
            skipped += 1
            continue
        try:
            blob = fetch(url)
        except Exception as e:  # noqa: BLE001
            print(f"  [{i}/{len(targets)}] {d}T{h} FAILED: "
                  f"{type(e).__name__}: {e}", flush=True)
            failed += 1
            continue
        bytes_in += len(blob)

        # Row-group at a time so a 128 MB file never becomes a 20M-row table in
        # memory all at once.
        try:
            pf = pq.ParquetFile(io.BytesIO(blob))
            batches = []
            for rg in range(pf.num_row_groups):
                t = pf.read_row_group(rg)
                tick = t.column("market_ticker")
                mask = None
                for p in prefixes:
                    m = pc.starts_with(tick, pattern=p)
                    mask = m if mask is None else pc.or_(mask, m)
                if mask is not None:
                    t = t.filter(mask)
                if t.num_rows:
                    batches.append(t)
            if batches:
                out = pa.concat_tables(batches)
                pq.write_table(out, out_path, compression="zstd")
                kept_rows += out.num_rows
                n_out = out.num_rows
            else:
                # Write nothing, but remember we looked, so a resume skips it.
                open(out_path + ".empty", "w").close()
                n_out = 0
        except Exception as e:  # noqa: BLE001
            print(f"  [{i}/{len(targets)}] {d}T{h} PARSE FAILED: "
                  f"{type(e).__name__}: {e}", flush=True)
            failed += 1
            continue

        done += 1
        if done % 10 == 0 or n_out == 0:
            el = time.time() - t_start
            print(f"  [{i}/{len(targets)}] {d}T{h}  kept {n_out:,} rows  "
                  f"| {bytes_in/1e9:.1f} GB in, {kept_rows:,} rows kept, "
                  f"{el/60:.0f} min", flush=True)
        time.sleep(PACE)

    el = time.time() - t_start
    msg = (f"files={done} skipped={skipped} failed={failed} "
           f"rows_kept={kept_rows} gb_in={bytes_in/1e9:.1f} min={el/60:.0f}")
    print("\n" + msg)
    print(f"  -> {OUT}")
    db.log(con, "pull_kalshi_archive", msg)
    con.close()


if __name__ == "__main__":
    main()
