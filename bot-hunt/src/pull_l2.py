"""Pull Kalshi L2 order-book history for the esports families, over HTTP RANGE.

Why this exists. H10 (rest a passive bid inside the touch) is the one
pre-registered strategy never run, and it is the one that matters: the
maker-vs-taker question is the largest unresolved tension in this programme.
`signal-github` concluded maker-only quoting is the one strategy whose income
need not overcome a fee first; a 20-year professional in the YouTube corpus says
be a taker, because a resting order is filled only when it is good for the other
side. The only number anyone has put on it is the **38% of gross** that adverse
selection cost the esports arb author.

It became runnable because the brief's premise was wrong. `archive.pmxt.dev`
carries Kalshi FULL L2 - 550 hourly files, 2026-05-19T06 -> 2026-06-11T03 - and
one sampled hour holds 498,434 esports rows across 74 tickers.

**It reads over HTTP range requests instead of downloading whole files.**
Measured: the origin returns 206 with `Accept-Ranges: bytes`. Parquet stores
each column chunk contiguously, so fetching the footer and then only the needed
column chunks transfers a fraction of a 128 MB file. This is somebody else's
volunteer-run archive and a sibling session is already pulling the same files;
taking 37 GB to answer one question would be rude and unnecessary.

Writes one filtered parquet per hour to data/l2/, resumable, and never
re-downloads a file it already has.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "l2"
INDEX = "https://archive.pmxt.dev/Kalshi"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/127.0 Safari/537.36")
HREF = re.compile(r'href="(https?://[^"]*kalshi_orderbook_[^"]*\.parquet)"')
FILE_RE = re.compile(r"kalshi_orderbook_(\d{4}-\d{2}-\d{2})T(\d{2})\.parquet")

PREFIXES = ("KXCS2GAME", "KXLOLGAME", "KXVALORANTGAME")
# Overridable from the command line (--prefixes / --tag) so the same streaming
# reader can serve the crypto maker-viability test without a second copy of it.
# Defaults are unchanged, so every existing `es_*.parquet` pull still reproduces
# byte for byte.
OUT_TAG = "es"
# Everything H10 needs and nothing it does not. `timestamp_received` and
# `market_id` are dropped, which is pure transfer saved.
COLS = ["timestamp", "market_ticker", "event_type", "yes_bids", "no_bids",
        "price", "delta", "side"]
PACE = 2.0


class HttpFile(io.RawIOBase):
    """A seekable read-only file over HTTP range requests.

    pyarrow asks for byte ranges (footer, then column chunks); each becomes one
    Range request. `bytes_read` is the honest transfer counter - the point of
    the exercise is to keep it far below the file size.
    """

    def __init__(self, url: str, size: int | None = None):
        self.url = url
        self._pos = 0
        self.bytes_read = 0
        self.requests = 0
        self.size = size if size is not None else self._head()

    def _head(self) -> int:
        req = urllib.request.Request(self.url, headers={"User-Agent": UA,
                                                        "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            cr = r.headers.get("Content-Range", "")
            r.read()
        return int(cr.split("/")[-1])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self._pos

    def seek(self, off, whence=0):
        if whence == 0:
            self._pos = off
        elif whence == 1:
            self._pos += off
        else:
            self._pos = self.size + off
        return self._pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self._pos
        if n == 0 or self._pos >= self.size:
            return b""
        end = min(self._pos + n, self.size) - 1
        hdr = {"User-Agent": UA, "Range": f"bytes={self._pos}-{end}"}
        for attempt in range(4):
            try:
                req = urllib.request.Request(self.url, headers=hdr)
                with urllib.request.urlopen(req, timeout=300) as r:
                    buf = r.read()
                break
            except Exception:  # noqa: BLE001
                if attempt == 3:
                    raise
                time.sleep(5 * (attempt + 1))
        self._pos += len(buf)
        self.bytes_read += len(buf)
        self.requests += 1
        return buf

    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)


def fetch_text(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def index(max_pages=12):
    seen = {}
    for page in range(1, max_pages + 1):
        u = INDEX if page == 1 else f"{INDEX}?page={page}"
        try:
            html = fetch_text(u)
        except Exception as exc:  # noqa: BLE001
            print(f"  index page {page}: {type(exc).__name__}")
            break
        hs = HREF.findall(html)
        if not hs:
            break
        for h in hs:
            m = FILE_RE.search(h)
            if m:
                seen[f"{m.group(1)}T{m.group(2)}"] = h
        time.sleep(0.8)
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-05-30")
    ap.add_argument("--until", default="2026-05-30")
    ap.add_argument("--hours", default="",
                    help="comma list of UTC hours, e.g. 12,13,14; blank = all")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--prefixes", default="",
                    help="comma list of ticker prefixes; default is esports")
    ap.add_argument("--tag", default="",
                    help="output filename prefix; default 'es'")
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    want_hours = {h.strip().zfill(2) for h in a.hours.split(",") if h.strip()}
    idx = index()
    keys = sorted(k for k in idx
                  if a.since <= k[:10] <= a.until
                  and (not want_hours or k[-2:] in want_hours))
    if a.limit:
        keys = keys[:a.limit]
    print(f"{len(keys)} hourly files in window {a.since}..{a.until} "
          f"hours={sorted(want_hours) or 'all'}")
    if a.list:
        for k in keys:
            print(" ", k, idx[k])
        return

    global PREFIXES, OUT_TAG
    if a.prefixes:
        PREFIXES = tuple(x.strip() for x in a.prefixes.split(",") if x.strip())
    if a.tag:
        OUT_TAG = a.tag
    print(f"prefixes={PREFIXES}  tag={OUT_TAG}", flush=True)

    tot_read = tot_size = kept = done = failed = 0
    t0 = time.time()
    for i, k in enumerate(keys, 1):
        out_path = OUT / f"{OUT_TAG}_{k}.parquet"
        if out_path.exists() or (OUT / f"{OUT_TAG}_{k}.empty").exists():
            continue
        try:
            hf = HttpFile(idx[k])
            pf = pq.ParquetFile(hf)
            batches = []
            for rg in range(pf.num_row_groups):
                t = pf.read_row_group(rg, columns=COLS)
                tick = t.column("market_ticker")
                mask = None
                for p in PREFIXES:
                    m = pc.starts_with(tick, pattern=p)
                    mask = m if mask is None else pc.or_(mask, m)
                t = t.filter(mask)
                if t.num_rows:
                    batches.append(t)
            n_out = 0
            if batches:
                out = pa.concat_tables(batches)
                pq.write_table(out, out_path, compression="zstd")
                n_out = out.num_rows
                kept += n_out
            else:
                (OUT / f"{OUT_TAG}_{k}.empty").touch()
            tot_read += hf.bytes_read
            tot_size += hf.size
            done += 1
            print(f"  [{i}/{len(keys)}] {k}  kept {n_out:>8,} rows  "
                  f"transferred {hf.bytes_read/1e6:>6.1f} MB of "
                  f"{hf.size/1e6:.0f} MB ({100*hf.bytes_read/hf.size:.0f}%) "
                  f"in {hf.requests} requests", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(keys)}] {k} FAILED: {type(exc).__name__}: "
                  f"{str(exc)[:160]}", flush=True)
            failed += 1
        time.sleep(PACE)

    el = (time.time() - t0) / 60
    print(f"\nfiles={done} failed={failed} rows_kept={kept:,}")
    if tot_size:
        print(f"transferred {tot_read/1e9:.2f} GB of a possible "
              f"{tot_size/1e9:.2f} GB  ({100*tot_read/tot_size:.1f}%) "
              f"in {el:.0f} min")
    print(f"  -> {OUT}")


if __name__ == "__main__":
    main()
