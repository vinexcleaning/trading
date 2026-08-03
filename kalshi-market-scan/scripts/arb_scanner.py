"""Phase 2: live no-arbitrage scanner.

Polls structural families on a loop and logs violations net of fees, with the
persistence of each violation tracked across scans. Persistence is the whole
question: a violation lasting 200ms is a data artifact, one lasting 30s with real
depth is exploitable.

Writes reports/arb_log.parquet. Read-only; no order endpoints.
"""

from __future__ import annotations

import json
import signal
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.api import KalshiPublicClient  # noqa: E402
from kalshi_research.arb import (  # noqa: E402
    Quote,
    check_bucket_sum,
    check_monotone_ladder,
    classify_family,
    verify_bucket_coverage,
)
from kalshi_research.clock import now_ns  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)
LOG = ROOT / "data" / "arb_scanner.log"
STOP = threading.Event()

# Families with a checkable internal constraint. "bucket" = mutually exclusive and
# exhaustive within one event; "ladder" = nested thresholds monotone in strike.
BUCKET_FAMILIES = [
    "KXBTC", "KXBTCD", "KXETH", "KXETHD", "KXSOLD", "KXXRPD", "KXDOGED",
    "KXINX", "KXINXU", "KXNASDAQ100", "KXNASDAQ100U", "KXDJI",
    "KXCPIYOY", "KXCPI", "KXFED", "KXGDP",
    "KXHIGHNY", "KXHIGHCHI", "KXHIGHMIA", "KXHIGHAUS",
    "KXHIGHLAX", "KXHIGHDEN", "KXHIGHPHIL",
]
LADDER_FAMILIES = [
    "KXTEMPDCH", "KXTEMPLAXH", "KXTEMPCHIH", "KXTEMPAUSH",
    "KXTEMPNYH", "KXTEMPMIAH", "KXTEMPDENH", "KXTEMPPHILH",
]
# The split above is only a polling list; the actual constraint applied to each
# event is decided by classify_family() from live strike_type data.
ALL_FAMILIES = BUCKET_FAMILIES + LADDER_FAMILIES


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _f(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def quotes_for(c: KalshiPublicClient, series: str) -> dict[str, list[Quote]]:
    """Group a series' open markets into per-event families of Quotes.

    Grouping by event_ticker matters: buckets are only mutually exclusive and
    exhaustive *within one event* (one expiry), never across expiries.
    """
    try:
        d = c.get("/markets", {"series_ticker": series, "status": "open", "limit": 1000})
    except Exception as e:  # noqa: BLE001
        log(f"[{series}] fetch ERROR {type(e).__name__}: {str(e)[:70]}")
        return {}
    fam: dict[str, list[Quote]] = defaultdict(list)
    for m in d.get("markets") or []:
        if m.get("mve_collection_ticker"):
            continue  # combos are not part of the exhaustive set
        fam[m.get("event_ticker") or series].append(
            Quote(
                ticker=m["ticker"],
                yes_bid=_f(m.get("yes_bid_dollars")),
                yes_ask=_f(m.get("yes_ask_dollars")),
                yes_bid_size=float(m.get("yes_bid_size_fp") or 0),
                yes_ask_size=float(m.get("yes_ask_size_fp") or 0),
                floor_strike=m.get("floor_strike"),
                cap_strike=m.get("cap_strike"),
                strike_type=m.get("strike_type"),
            )
        )
    return fam


def scan_once(c: KalshiPublicClient) -> list[dict]:
    """Classify each event from its strike_type mix, then apply only the
    constraint that actually holds for it. Never assume the family shape from the
    series ticker -- KXDJI looks like a bucket family and is in fact a 60-rung
    nested ladder, and summing it produces a nonsensical 1,300c 'arb'.
    """
    rows: list[dict] = []
    ts = now_ns()
    for series in ALL_FAMILIES:
        for event, qs in quotes_for(c, series).items():
            if len(qs) < 2:
                continue
            kind = classify_family(qs)
            if kind == "bucket":
                ok, why = verify_bucket_coverage(qs)
                if not ok:
                    continue
                vs = check_bucket_sum(event, qs, require_coverage=True)
            elif kind == "ladder":
                vs = check_monotone_ladder(event, qs)
            else:
                continue
            for v in vs:
                rows.append(
                    {
                        "scan_ns": ts,
                        "series": series,
                        "family_kind": kind,
                        "event": event,
                        "kind": v.kind,
                        "tickers": ",".join(v.tickers),
                        "n_legs": len(v.tickers),
                        "gross_edge_cents": v.gross_edge_cents,
                        "fee_cents": v.fee_cents,
                        "net_edge_cents": v.net_edge_cents,
                        "size_available": v.size_available,
                        "is_arb": v.is_arb,
                        "detail": v.detail,
                        # identity for persistence tracking across scans
                        "vid": f"{v.kind}|{event}|{','.join(v.tickers)}",
                    }
                )
    return rows


def main(interval: float = 30.0, max_scans: int | None = None) -> None:
    def handler(signum, frame):  # noqa: ANN001, ARG001
        STOP.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handler)
        except Exception:  # noqa: BLE001,S110
            pass

    c = KalshiPublicClient(rps=4.0)
    all_rows: list[dict] = []
    first_seen: dict[str, int] = {}
    last_seen: dict[str, int] = {}
    n = 0
    log(f"[arb] START interval={interval}s "
        f"families={len(BUCKET_FAMILIES)}bucket+{len(LADDER_FAMILIES)}ladder")

    while not STOP.is_set():
        t0 = time.time()
        try:
            status = c.get("/exchange/status")
            trading = bool(status.get("trading_active"))
        except Exception:  # noqa: BLE001
            trading = True
        rows = scan_once(c)
        n += 1
        ts = rows[0]["scan_ns"] if rows else now_ns()
        live = {r["vid"] for r in rows}
        for vid in live:
            first_seen.setdefault(vid, ts)
            last_seen[vid] = ts
        for r in rows:
            r["trading_active"] = trading
            r["first_seen_ns"] = first_seen[r["vid"]]
            r["persist_s"] = (ts - first_seen[r["vid"]]) / 1e9
        all_rows += rows
        arbs = [r for r in rows if r["is_arb"]]
        log(
            f"[arb] scan {n}: trading={trading} violations={len(rows)} "
            f"net-positive={len(arbs)} req={c.n_req} 429={c.n_429}"
        )
        for r in arbs[:5]:
            log(
                f"    ARB {r['kind']} {r['event']} net={r['net_edge_cents']:.2f}c "
                f"size={r['size_available']:.0f} persist={r['persist_s']:.0f}s"
            )
        if all_rows:
            pd.DataFrame(all_rows).to_parquet(
                REPORTS / "arb_log.parquet", index=False, compression="zstd"
            )
            (REPORTS / "arb_scan_meta.json").write_text(
                json.dumps(
                    {
                        "scans": n,
                        "rows": len(all_rows),
                        "distinct_violations": len(first_seen),
                        "updated_ns": now_ns(),
                    },
                    indent=1,
                )
            )
        if max_scans and n >= max_scans:
            break
        STOP.wait(max(1.0, interval - (time.time() - t0)))
    log(f"[arb] STOPPED scans={n} rows={len(all_rows)}")


if __name__ == "__main__":
    iv = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
    ms = int(sys.argv[2]) if len(sys.argv) > 2 else None
    main(iv, ms)
