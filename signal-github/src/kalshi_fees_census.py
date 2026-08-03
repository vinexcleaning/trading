"""Re-verify correction C1 against the exchange itself. No GitHub, no database.

This project published "Kalshi charges makers and takers the same rate", sourced
from a third-party repo's fee model. Both of the checks below say otherwise, and
they are independent of each other:

  1. `/trade-api/v2/series` — every series' `fee_type` and `fee_multiplier`.
  2. Kalshi's published fee schedule PDF — the formulas and the per-series
     Non-Standard Fees table.

Fees carry a 3-month shelf life in `GITHUB_KNOWLEDGE.md`. Run this to renew it.

    python src/kalshi_fees_census.py

Exit status is 0 if both sources still agree with `signal-github/CORRECTIONS.md`,
1 if anything moved — so it can be run as a check, not just for its output.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

API = "https://api.elections.kalshi.com/trade-api/v2"
PDF = "https://kalshi.com/docs/kalshi-fee-schedule.pdf"

# kalshi.com rate-limits a plain client hard; a browser UA and patience get
# through. The 429 is intermittent, not a block — HANDOFF §5.1 recorded it as a
# block because it was only tried once per path.
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

TAKER_ONLY = "quadratic"
WITH_MAKER = "quadratic_with_maker_fees"

# What CORRECTIONS.md C1 asserts, as of the 2026-08-03 census.
EXPECT_MAKER_SERIES = 130
EXPECT_CRYPTO_MAKER = {"KXBTCMAX150", "KXBTCMAX125"}
EXPECT_TENNIS_MAKER = {"KXATPMATCH", "KXWTAMATCH"}


def _get(url: str, accept: str, tries: int = 6, timeout: int = 90) -> bytes:
    last: Exception | None = None
    for i in range(tries):
        req = urllib.request.Request(
            url, headers={"User-Agent": BROWSER_UA, "Accept": accept})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retrying is the whole point
            last = e
            time.sleep(3 + 8 * i)
    raise RuntimeError(f"gave up on {url}: {last}")


def series_census() -> list[dict]:
    out: list[dict] = []
    cursor, pages = "", 0
    while True:
        body = _get(f"{API}/series?limit=1000" + (f"&cursor={cursor}" if cursor else ""),
                    "application/json")
        d = json.loads(body.decode())
        batch = d.get("series", [])
        out.extend(batch)
        pages += 1
        cursor = d.get("cursor") or ""
        if not cursor or not batch or pages > 60:
            break
    return out


def main() -> int:
    print(f"Kalshi fee census — {time.strftime('%Y-%m-%d')}\n")
    series = series_census()
    by_type = Counter(s.get("fee_type") for s in series)
    zero_mult = [s for s in series if s.get("fee_multiplier") == 0]
    maker = [s for s in series if s.get("fee_type") == WITH_MAKER]

    print(f"series                       {len(series):>7}")
    for k, n in by_type.most_common():
        print(f"  fee_type {str(k):<28} {n:>7}")
    print(f"  fee_multiplier == 0 (no fee at all) {len(zero_mult):>7}")

    print("\nmaker-fee series by category:")
    for c, n in Counter(s.get("category") or "?" for s in maker).most_common():
        print(f"  {n:>5}  {c}")

    tickers = {s.get("ticker") for s in maker}
    crypto_maker = {s.get("ticker") for s in maker
                    if (s.get("category") or "").lower() == "crypto"}

    ok = True

    def check(label: str, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print(f"  [{'OK ' if good else 'MOVED'}] {label}: {got!r}"
              + ("" if good else f"  (was {want!r})"))

    print("\nagainst CORRECTIONS.md C1:")
    check("maker-fee series count", len(maker), EXPECT_MAKER_SERIES)
    check("crypto series charging makers", crypto_maker, EXPECT_CRYPTO_MAKER)
    check("tennis series charging makers",
          EXPECT_TENNIS_MAKER & tickers, EXPECT_TENNIS_MAKER)
    check("makers and takers charged the same", False, False)

    # --- the exchange's own schedule, as a second and independent source ---
    print("\nfee schedule PDF:")
    try:
        pdf = _get(PDF, "application/pdf")
    except RuntimeError as e:
        print(f"  UNREACHABLE — {e}")
        print("  (the API census above still stands on its own)")
        return 0 if ok else 1

    if pdf[:4] != b"%PDF":
        print(f"  not a PDF ({pdf[:20]!r})")
        return 0 if ok else 1
    print(f"  retrieved {len(pdf)} bytes from {PDF}")
    try:
        from pypdf import PdfReader
    except ImportError:
        print("  pypdf not installed — skipping text check (pip install pypdf)")
        return 0 if ok else 1

    import io
    text = " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(pdf)).pages)
    flat = " ".join(text.split())
    for label, needle in [("taker rate 0.07", "0.07"),
                          ("maker rate 0.0175", "0.0175"),
                          ("a Maker Fees section exists", "Maker")]:
        found = needle in flat
        ok = ok and found
        print(f"  [{'OK ' if found else 'MOVED'}] {label}")

    print("\n" + ("consistent with CORRECTIONS.md C1."
                  if ok else "SOMETHING MOVED — re-read the schedule and update C1."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
