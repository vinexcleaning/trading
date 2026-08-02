"""TASK 4 — broad depth + quote recorder across candidate market families.

WHY THIS STARTS BEFORE THE ANALYSIS FINISHES. Kalshi publishes no historical
order-book endpoint. Depth exists only in what is recorded live and every hour
not recorded is gone permanently (LEDGER: the API is a ~69-day window and
closed markets 404). Recording accrues in wall-clock time and cannot be
backfilled, so it starts as soon as a family is a *candidate*, not once it is
confirmed. Recording a family that is later killed costs disk. Not recording
one that survives costs the night.

It doubles as the measurement instrument for dimension A (two-sided quote
uptime) and B (depth at the touch), which need repeated sampling over time
and cannot be got from a single snapshot.

THE KEY NAME. Depth comes from `orderbook_fp.yes_dollars` / `no_dollars`.
There is no `orderbook` key and no `yes` / `no` key in the response. Reading
those returns an empty book from an HTTP 200 on every market -- see
reports/orderbook_resolution.md.

CONTENT VALIDATION, NOT ROW COUNTS (GUARDS #12). Every row is checked as it is
written: levels must parse, prices must be strictly inside (0,100), sizes must
be non-negative and finite. Per-cycle counters record how many snapshots were
genuinely non-empty. A cycle whose non-empty fraction collapses prints a loud
warning rather than continuing to write correct-looking counts of empty rows.

API COURTESY: single-threaded, one request in flight, paced, backoff on 429.
Read-only public endpoints. No credentials, no orders.
"""
import datetime as dt
import json
import os
import pathlib
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import kalshi_api as K  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "depth_broad"
DUMP = ROOT / "data" / "kalshi_markets_open.jsonl"

PACE = 0.15
REFRESH_MIN = 25          # re-pick markets this often
DEPTH = 20                # 20 a side is the server maximum
N_SERIES = 85             # candidate families to cover
PER_SERIES = 3            # markets per family per cycle
HEALTH_EVERY = 5          # cycles between content-health reports

# Families are ranked by TRADES PER DAY off the public tape, not by 24h dollar
# volume off the market dump. Volume is dominated by a few enormous prints;
# trade count is what dimension A actually asks about (does a counterparty
# exist), and the first version of this recorder -- ranked by volume -- missed
# KXMLSGAME, KXBOXING, KXITFWMATCH, KXVALORANTGAME and every 15-minute crypto
# series despite all of them out-trading most of what it did cover.
TAPE = ROOT / "data" / "kalshi_trades_24h.jsonl"

# The two exotic parlay series are 83% of the 419,828-market universe and would
# swamp the sample. They get a token allocation so they are still measured.
PARLAY = {"KXMVESPORTSMULTIGAMEEXTENDED", "KXMVECROSSCATEGORY"}


def now():
    return dt.datetime.now(dt.timezone.utc)


def log(m):
    print(f"[{now():%Y-%m-%d %H:%M:%S}] {m}", flush=True)


def rank_series():
    """Families ranked by trades/day off the tape, with a volume fallback."""
    counts = Counter()
    if TAPE.exists():
        with open(TAPE, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    tk = json.loads(line).get("ticker")
                except json.JSONDecodeError:
                    continue      # the tape may still be being written
                if tk:
                    counts[K.series_of(tk)] += 1
    return [s for s, _ in counts.most_common()]


def pick_markets():
    """Top N_SERIES families by trades/day, PER_SERIES busiest markets each.

    Selecting the busiest market inside each family is deliberate and is a
    statement about what is being measured: this is each family's BEST case.
    A family whose busiest markets are untradeable is safely killed. A family
    that looks good here has only been shown to have one good market, which is
    why the analysis reports markets-traded-per-day separately.
    """
    ranked = rank_series()
    if not ranked:
        # tape not written yet -- fall back to 24h volume off the static dump
        by_series = defaultdict(list)
        with open(DUMP, encoding="utf-8") as fh:
            for line in fh:
                m = json.loads(line)
                v = K.f(m.get("volume_24h_fp")) or 0.0
                by_series[K.series_of(m["ticker"])].append((v, m["ticker"]))
        ranked = [s for _, s in sorted(
            ((sum(v for v, _ in ms), s) for s, ms in by_series.items()),
            reverse=True)]

    # RE-LIST LIVE, PER SERIES. An earlier version chose tickers from the
    # static market dump, which was captured once and never refreshed. Markets
    # settle; the list did not. Long-lived families (MLB games listed days
    # ahead) were unaffected, but short-lived ones silently accumulated closed
    # tickers, and a closed book reads as "no counterparty":
    #   KXBTC15M   recorded 0.0% two-sided over 36 snapshots
    #              -- a fresh listing shows it quoted two-sided at a 0.1c spread
    #   KXNPBGAME  recorded 27.9% over 129 snapshots
    #              -- a fresh listing shows 100%, 2,043 contracts at the touch
    # The instrument was measuring its own staleness. Now every refresh asks
    # the API which markets are actually open.
    picked, fams = [], 0
    for s in ranked:
        if fams >= N_SERIES:
            break
        r = K.get("/markets", {"series_ticker": s, "status": "open",
                               "limit": 200})
        if r is None or r.status_code != 200:
            continue
        ms = r.json().get("markets", [])
        if not ms:
            continue        # traded recently but nothing open right now
        ms.sort(key=lambda m: -(K.f(m.get("volume_24h_fp")) or 0.0))
        n = 1 if s in PARLAY else PER_SERIES
        for m in ms[:n]:
            picked.append((s, m["ticker"]))
        fams += 1
    return picked


def valid(levels):
    """Content check on one parsed ladder. Returns (ok, n_levels)."""
    for p, sz in levels:
        if not (0.0 < p < 100.0):
            return False, len(levels)
        if sz < 0 or sz != sz or sz in (float("inf"), float("-inf")):
            return False, len(levels)
    return True, len(levels)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mkts, last_refresh, cycle = [], None, 0
    tot = Counter()

    log(f"broad depth recorder starting -- read-only, {PACE}s pacing, "
        f"{DEPTH} levels/side")
    while True:
        if last_refresh is None or (now() - last_refresh).total_seconds() > REFRESH_MIN * 60:
            try:
                mkts = pick_markets()
            except Exception as e:  # noqa: BLE001
                log(f"market refresh failed: {type(e).__name__}: {e}")
                time.sleep(60)
                continue
            last_refresh = now()
            log(f"tracking {len(mkts)} markets across "
                f"{len({s for s, _ in mkts})} series")
            if not mkts:
                time.sleep(300)
                continue

        t = now()
        d = OUT / f"{t:%Y-%m-%d}" / f"{t:%H}"
        d.mkdir(parents=True, exist_ok=True)
        path = d / "depth.jsonl"

        cyc = Counter()
        bad_rows = []
        t_start = time.time()
        # buffering=1 -> line buffered. Default block buffering held up to 8 KB
        # of an unbackfillable recording in memory and made the file look
        # stalled for a whole cycle; a crash would have silently lost it.
        with open(path, "a", encoding="utf-8", buffering=1) as fh:
            for series, tk in mkts:
                yes, no = K.orderbook(tk, DEPTH)
                ts = now()
                if yes is None and no is None:
                    cyc["http_fail"] += 1
                    continue
                yes, no = yes or [], no or []
                oky, ny = valid(yes)
                okn, nn = valid(no)
                if not (oky and okn):
                    cyc["invalid"] += 1
                    bad_rows.append(tk)
                    continue
                yb, ya, ybs, yas = K.touch(yes, no)
                cyc["rows"] += 1
                if ny or nn:
                    cyc["nonempty"] += 1
                if ny and nn:
                    cyc["two_sided"] += 1
                fh.write(json.dumps({
                    "ts": ts.isoformat(), "ticker": tk, "series": series,
                    "yes": yes, "no": no,
                    "yes_bid_c": yb, "yes_ask_c": ya,
                    "bid_sz": ybs, "ask_sz": yas,
                }) + "\n")
                time.sleep(PACE)

        cycle += 1
        for k, v in cyc.items():
            tot[k] += v
        el = time.time() - t_start
        ne = cyc["nonempty"] / cyc["rows"] if cyc["rows"] else 0.0
        ts_ = cyc["two_sided"] / cyc["rows"] if cyc["rows"] else 0.0
        log(f"cycle {cycle}: {cyc['rows']} rows in {el:.0f}s | "
            f"non-empty {ne*100:.1f}% | two-sided {ts_*100:.1f}% | "
            f"invalid {cyc['invalid']} | http_fail {cyc['http_fail']} -> {path.parent}")

        if cycle % HEALTH_EVERY == 0:
            g = tot["nonempty"] / tot["rows"] if tot["rows"] else 0.0
            log(f"HEALTH after {cycle} cycles: rows={tot['rows']} "
                f"non-empty={g*100:.1f}% two-sided="
                f"{tot['two_sided']/max(tot['rows'],1)*100:.1f}% "
                f"invalid={tot['invalid']} http_fail={tot['http_fail']}")
            # The failure this exists to catch: correct-looking counts of
            # empty rows. Row count alone would look fine here.
            if tot["rows"] > 300 and g < 0.05:
                log("WARNING: <5% of snapshots carry any depth. The recorder "
                    "is writing well-formed nothing. CHECK THE KEY NAME "
                    "(orderbook_fp.yes_dollars) BEFORE TRUSTING ANY ROW.")
        if bad_rows:
            log(f"  invalid content on: {bad_rows[:5]}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
