"""Do Kalshi's 130 maker-fee series also hold its liquidity?

Correction C1 established that Kalshi charges makers on exactly 130 of 12,396
series — 1.0% by count — which makes "Kalshi makers pay nothing" true on its
face. Whether it is true where you would actually want to quote is a different
question, and this measures it.

**Method, and why not the obvious one.** Paginating `/markets?status=open` does
not work: the cursor is ordered by series, so the first 85,000 markets returned
cover 32 of 12,396 series — a capped scan answers nothing. Instead, query volume
per series directly for all 130 maker-fee series and for a random sample of 300
taker-only series, then compare with rank statistics rather than by projecting
the sample onto the population. Open volume is heavy-tailed enough that such a
projection has an interval far wider than the effect.

**Caveat that belongs on the answer.** `volume` on an open market is cumulative
since that market opened, so long-dated series — which many of the 130 are —
accumulate more purely by age. `open_interest` is a stock rather than a flow and
is not age-biased in the same way, so both are reported; they agree.

    python src/kalshi_liquidity_survey.py [--sample 300]
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
import time
import urllib.request

API = "https://api.elections.kalshi.com/trade-api/v2"
UA = "signal-github/0.2 (research)"
WITH_MAKER = "quadratic_with_maker_fees"
SEED = 20260803


def get(path: str, tries: int = 4):
    last = None
    for i in range(tries):
        req = urllib.request.Request(API + path,
                                     headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001 - the API times out under load
            last = e
            time.sleep(1.5 + 2 * i)
    raise last


def all_series() -> list[dict]:
    out, cursor, pages = [], "", 0
    while True:
        d = get(f"/series?limit=1000" + (f"&cursor={cursor}" if cursor else ""))
        b = d.get("series", [])
        out.extend(b)
        pages += 1
        cursor = d.get("cursor") or ""
        if not cursor or not b or pages > 60:
            break
    return out


def series_liquidity(ticker: str):
    """Total open volume, open interest and market count for one series."""
    vol = oi = 0.0
    n, cursor, pages = 0, "", 0
    while True:
        d = get(f"/markets?limit=200&status=open&series_ticker={ticker}"
                + (f"&cursor={cursor}" if cursor else ""))
        ms = d.get("markets", [])
        for m in ms:
            vol += float(m.get("volume_fp") or m.get("volume") or 0)
            oi += float(m.get("open_interest_fp") or m.get("open_interest") or 0)
        n += len(ms)
        pages += 1
        cursor = d.get("cursor") or ""
        if not cursor or not ms or pages > 25:
            break
    return vol, oi, n


def mannwhitney(a, b):
    """U and a two-sided normal-approximation p, tie-corrected. Returns p as a
    float that may underflow to 0.0 — report it as an upper bound, not as zero."""
    comb = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    n1, n2, n = len(a), len(b), len(a) + len(b)
    rsum_a, i, ties = 0.0, 0, []
    while i < len(comb):
        j = i
        while j + 1 < len(comb) and comb[j + 1][0] == comb[i][0]:
            j += 1
        r = (i + j) / 2.0 + 1
        ties.append(j - i + 1)
        rsum_a += sum(r for k in range(i, j + 1) if comb[k][1] == 0)
        i = j + 1
    u = rsum_a - n1 * (n1 + 1) / 2.0
    tie_term = sum(t ** 3 - t for t in ties)
    sd = math.sqrt(n1 * n2 / 12.0 * ((n + 1) - tie_term / (n * (n - 1))))
    if sd == 0:
        return u, 1.0, 0.0
    z = (u - n1 * n2 / 2.0) / sd
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return u, p, z


def main():
    sample_n = 300
    if "--sample" in sys.argv:
        sample_n = int(sys.argv[sys.argv.index("--sample") + 1])
    random.seed(SEED)

    series = all_series()
    maker = [s for s in series if s.get("fee_type") == WITH_MAKER]
    taker = [s for s in series if s.get("fee_type") != WITH_MAKER]
    sample = random.sample(taker, min(sample_n, len(taker)))
    print(f"{len(series)} series: {len(maker)} maker-fee, {len(taker)} taker-only "
          f"({len(sample)} sampled)\n", flush=True)

    def survey(group, label):
        out = []
        for i, s in enumerate(group, 1):
            try:
                v, o, n = series_liquidity(s["ticker"])
            except Exception as e:  # noqa: BLE001
                print(f"  ! {s['ticker']}: {type(e).__name__}", flush=True)
                continue
            out.append((s["ticker"], v, o, n, s.get("category")))
            if i % 50 == 0:
                print(f"  {label} {i}/{len(group)}", flush=True)
        return out

    mk = survey(maker, "maker-fee")
    tk = survey(sample, "taker-only")

    for idx, label in ((1, "open volume"), (2, "open interest")):
        a = [r[idx] for r in mk]
        b = [r[idx] for r in tk]
        u, p, z = mannwhitney(a, b)
        asr, bsr = sorted(a), sorted(b)
        print(f"\n=== {label} per series ===")
        print(f"  maker-fee  n={len(a):4}  median {asr[len(a)//2]:>12,.0f}  "
              f"mean {sum(a)/len(a):>14,.0f}  nonzero {sum(1 for x in a if x>0)}")
        print(f"  taker-only n={len(b):4}  median {bsr[len(b)//2]:>12,.0f}  "
              f"mean {sum(b)/len(b):>14,.0f}  nonzero {sum(1 for x in b if x>0)}")
        pstr = f"{p:.3g}" if p > 0 else "< 1e-15 (underflow)"
        print(f"  Mann-Whitney U={u:,.0f}  z={z:.1f}  p={pstr}")

    comb = sorted([(r[1], "maker") for r in mk] + [(r[1], "taker") for r in tk],
                  key=lambda x: -x[0])
    print(f"\nrank position (survey base rate: {len(mk)}/{len(comb)} = "
          f"{100*len(mk)/len(comb):.0f}% maker-fee):")
    for topn in (10, 25, 50, 100):
        if topn > len(comb):
            break
        nm = sum(1 for _v, g in comb[:topn] if g == "maker")
        print(f"  top {topn:4} by open volume: {nm} maker-fee ({100*nm/topn:.0f}%)")

    print("\ntop 15 maker-fee series by open volume:")
    for t, v, o, n, c in sorted(mk, key=lambda x: -x[1])[:15]:
        print(f"  {t:26} {v:14,.0f}  {n:4} open markets  {c}")

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "reports", "kalshi_liquidity_survey.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"seed": SEED, "maker": mk, "taker_sample": tk}, fh)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
