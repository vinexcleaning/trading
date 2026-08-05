"""Does the Kalshi L2 archive carry the families bot-hunt actually cares about?

A sibling session refuted the premise my brief was written on: `archive.pmxt.dev`
holds Kalshi **full L2** — microsecond timestamps, yes_bids/no_bids ladders,
20.7M rows for one hour, 642,054 distinct tickers. Their own retraction is the
model here: they had verified that the FILES EXIST, not that the DATA was what
they said. So this opens exactly ONE file and counts rows per family.

Why only one. The full window is ~288 files ~= 37 GB from a volunteer-run
archive and a sibling is already pulling those same files for tennis. Spending
15 GB of someone else's bandwidth to answer "is esports in here?" before knowing
whether the cheap candle test says anything is the wrong order. One file
answers the existence question; the pull decision comes after the grid.

Costs one ~128 MB download.
"""
from __future__ import annotations

import io
import json
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "reports"
INDEX = "https://archive.pmxt.dev/Kalshi"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/127.0 Safari/537.36")
HREF = re.compile(r'href="(https?://[^"]*kalshi_orderbook_[^"]*\.parquet)"')
FILE_RE = re.compile(r"kalshi_orderbook_(\d{4}-\d{2}-\d{2})T(\d{2})\.parquet")

# The families this project ranked. Esports is the one with the only reconciled
# live P&L; MLB is the negative control; tennis is what the sibling is pulling
# and is included so the two measurements can be compared.
FAMILIES = {
    "esports": ("KXCS2GAME", "KXLOLGAME", "KXVALORANTGAME"),
    "tennis": ("KXATPMATCH", "KXWTAMATCH", "KXITFMATCH", "KXITFWMATCH"),
    "mlb": ("KXMLBGAME", "KXMLBRFI"),
    "soccer_sa": ("KXLIGAMXGAME", "KXARGPREMDIVGAME", "KXMLSGAME"),
}


def fetch(url, timeout=300):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("enumerating the Kalshi archive index ...")
    urls = []
    for page in range(1, 12):
        u = INDEX if page == 1 else f"{INDEX}?page={page}"
        try:
            html = fetch(u, timeout=90).decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            print(f"  page {page}: {type(exc).__name__}")
            break
        hs = HREF.findall(html)
        if not hs:
            break
        urls += hs
        time.sleep(1.0)
    seen = {}
    for h in urls:
        m = FILE_RE.search(h)
        if m:
            seen[f"{m.group(1)}T{m.group(2)}"] = h
    keys = sorted(seen)
    print(f"  {len(keys)} hourly files; range {keys[0] if keys else '-'} .. "
          f"{keys[-1] if keys else '-'}")
    if not keys:
        return

    # Pick an hour in the MIDDLE of the window, not the edge: the first and last
    # files of a feed are the ones most likely to be partial.
    pick = keys[len(keys) // 2]
    url = seen[pick]
    print(f"\nopening ONE file: {pick}\n  {url}")
    t0 = time.time()
    blob = fetch(url)
    print(f"  {len(blob):,} bytes in {time.time()-t0:.0f}s")

    import pyarrow.parquet as pq
    import pyarrow.compute as pc

    pf = pq.ParquetFile(io.BytesIO(blob))
    print(f"  row groups={pf.num_row_groups} rows={pf.metadata.num_rows:,}")
    print(f"  columns: {pf.schema_arrow.names}")

    fam_rows = Counter()
    fam_tickers = {k: set() for k in FAMILIES}
    types = Counter()
    total = 0
    for rg in range(pf.num_row_groups):
        t = pf.read_row_group(rg)
        total += t.num_rows
        if "type" in t.column_names:
            for v, c in zip(*[x.to_pylist() for x in
                              pc.value_counts(t.column("type")).flatten()]):
                types[v] += c
        tick = t.column("market_ticker")
        for fam, prefixes in FAMILIES.items():
            mask = None
            for p in prefixes:
                m = pc.starts_with(tick, pattern=p)
                mask = m if mask is None else pc.or_(mask, m)
            sub = t.filter(mask)
            if sub.num_rows:
                fam_rows[fam] += sub.num_rows
                fam_tickers[fam].update(sub.column("market_ticker").to_pylist())

    print(f"\n  message types: {dict(types)}")
    print(f"\n  {'family':12} {'rows':>10} {'% of hour':>10} {'tickers':>8}")
    for fam in FAMILIES:
        n = fam_rows[fam]
        print(f"  {fam:12} {n:>10,} {100*n/max(total,1):>9.3f}% "
              f"{len(fam_tickers[fam]):>8}")

    rep = {"file": pick, "url": url, "bytes": len(blob), "rows": total,
           "types": dict(types),
           "families": {k: {"rows": fam_rows[k], "tickers": len(fam_tickers[k]),
                            "sample": sorted(fam_tickers[k])[:5]}
                        for k in FAMILIES},
           "index_first": keys[0], "index_last": keys[-1],
           "n_files": len(keys)}
    (OUT / "archive_esports_probe.json").write_text(
        json.dumps(rep, indent=1), encoding="utf-8")
    print("\nwrote reports/archive_esports_probe.json")

    est = {k: fam_rows[k] / max(total, 1) for k in FAMILIES}
    print("\n  if the whole window were pulled and filtered, disk would be "
          "roughly:")
    for k, frac in est.items():
        print(f"    {k:12} {frac*37_000:>8.0f} MB of a ~37 GB transfer")


if __name__ == "__main__":
    main()
