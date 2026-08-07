"""Does the pmxt L2 archive carry CRYPTO? This decides weeks vs now.

The open question after MM_RESULTS_MAKER.md section 6b is the other half of
market making: adverse selection costs ~0.5c per contract, and we do not know
what a resting order CAPTURES. That needs the order book.

⚠ A CORRECTION TO MY OWN STATEMENT FIRST. I told the user the book is "free and
already recording". It is free. It is NOT recording for crypto:
`bot-hunt/src/record.py`'s KALSHI_SERIES lists soccer, tennis, esports, MLB and
weather -- **zero KXBTC/KXETH entries**. The book is being recorded for five
families and crypto is not one of them.

So there are two possible routes and this script decides which:

  A. `archive.pmxt.dev` already holds full Kalshi L2 for 2026-05-19 -> 06-11.
     If crypto is in it, the test is runnable on ~24 days of HISTORY, now.
  B. If it is not, the only route is forward recording, which means adding
     crypto to the recorder and waiting weeks.

bot-hunt/RESULTS.md section 5 sampled one hour and reported tennis 10.8%,
esports 2.58%, MLB 0.37%, soccer 0.00%. **It never checked crypto.**

Reads ONE hourly file over HTTP range requests, reusing bot-hunt's HttpFile so
only the footer and one column are transferred rather than the whole ~2 GB.
"""
from __future__ import annotations

import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "bot-hunt" / "src"))
from pull_l2 import HttpFile, INDEX, UA  # noqa: E402

HREF = re.compile(r'href="(https?://[^"]*kalshi_orderbook_[^"]*\.parquet)"')


def main() -> None:
    req = urllib.request.Request(INDEX, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        html = r.read().decode("utf-8", "replace")
    urls = sorted(set(HREF.findall(html)))
    if not urls:
        print("no archive files listed - the index may have moved")
        return
    print(f"archive lists {len(urls)} hourly files")
    print(f"   first {urls[0].rsplit('/', 1)[-1]}")
    print(f"   last  {urls[-1].rsplit('/', 1)[-1]}")

    # A DAYTIME hour. RESULTS.md section 5 recorded that an overnight hour gave a
    # tennis share 18x lower than a daytime one, and a sibling's disk estimate
    # was wrong because of exactly that. Crypto trades around the clock, but the
    # DENOMINATOR does not, so the share is only meaningful at a stated hour.
    target = [u for u in urls if "T17.parquet" in u]
    url = target[len(target) // 2] if target else urls[len(urls) // 2]
    print(f"\nsampling {url.rsplit('/', 1)[-1]}")

    hf = HttpFile(url)
    print(f"   file size {hf.size / 1e9:.2f} GB")
    pf = pq.ParquetFile(hf)
    n_rows = pf.metadata.num_rows
    print(f"   rows in the hour {n_rows:,}")

    # one column only
    tbl = pf.read(columns=["market_ticker"])
    tk = tbl.column("market_ticker").to_pylist()
    pre = Counter(str(t).split("-")[0] for t in tk if t)
    print(f"   transferred {hf.bytes_read / 1e6:.1f} MB in {hf.requests} "
          f"range requests, of a {hf.size / 1e9:.2f} GB file")

    crypto = {k: v for k, v in pre.items()
              if k.startswith("KXBTC") or k.startswith("KXETH")}
    print("\n== CRYPTO IN THE ARCHIVE")
    if crypto:
        for k, v in sorted(crypto.items(), key=lambda x: -x[1]):
            print(f"   {k:14} {v:>10,} rows   {100*v/n_rows:6.3f}% of the hour")
        print(f"   distinct crypto tickers: "
              f"{len({t for t in tk if str(t).startswith(('KXBTC','KXETH'))}):,}")
        print("\n   => ROUTE A. The test is runnable on ~24 days of HISTORY.")
    else:
        print("   NONE. Zero KXBTC/KXETH rows in this hour.")
        print("\n   => ROUTE B. Forward recording only: add crypto to the "
              "recorder and wait.")

    print("\n== the whole hour, for context")
    for k, v in pre.most_common(12):
        print(f"   {k:22} {v:>10,}  {100*v/n_rows:6.3f}%")


if __name__ == "__main__":
    main()
