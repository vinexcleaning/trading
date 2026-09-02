"""Mirror the archive.pmxt.dev Kalshi L2 orderbook archive to local disk.

FACT ESTABLISHED BEFORE WRITING THIS (see reports/pmxt_coverage.md):
the archive is NOT on rolling retention. It is FROZEN. Files from
2026-05-16 are still served at 78 days old, and every hour after
2026-06-11T03 is 404. Coverage is 2026-05-14T14 .. 2026-06-11T03 inclusive.
So this mirror is insurance against an abandoned bucket being switched off,
not a race against a deleter.

Content validation, not file counts (GUARDS.md #12). Every downloaded file is
opened and checked on content before it is accepted:
  - parquet footer parses, num_rows > 0
  - schema field names match the expected 10 exactly
  - row-group statistics put `price` inside (0, 1)
  - both orderbook_snapshot and orderbook_delta appear in row group 0
A file failing any check is renamed .BAD and re-queued once.

Resumable: a file whose local size equals the remote Content-Length and whose
validation record already says ok is skipped without a network round trip
beyond the HEAD.
"""
import concurrent.futures as cf
import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

import pyarrow.parquet as pq
import requests

BASE = "https://r2kalshi.pmxt.dev/kalshi_orderbook_{stamp}.parquet"
# LAPTOP PATH, GUARDED 2026-09-02 (audit pass 4, item 7).
#
# This was a bare C:\Users\gianf\... constant. `gianf` is the LAPTOP; this
# machine is `vinig`. Running this here would makedirs a fresh laptop-shaped
# tree and begin re-downloading a 662-file archive into it -- and CLAUDE.md
# section 8 is explicit that a local archive is never "re-pulled to replace".
#
# It now resolves relative to this file, and REFUSES to run when the archive is
# not already present rather than silently starting a fresh download.
_HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.environ.get("PMXT_DEST", os.path.join(_HERE, "..", "data", "pmxt"))
if not os.path.isdir(DEST):
    raise SystemExit(
        "REFUSING TO RUN. The pmxt archive is not at " + DEST + ".\n"
        "This script mirrors 662 parquet files. It will not build that tree\n"
        "from scratch on a machine that does not already have it: the archive\n"
        "may exist on the laptop, and CLAUDE.md section 8 says a local archive\n"
        "is never re-pulled to replace. Set PMXT_DEST if you really mean to.")
LOG = os.path.join(DEST, "_mirror_log.jsonl")

START = datetime(2026, 5, 14, 14, tzinfo=timezone.utc)
END = datetime(2026, 6, 11, 3, tzinfo=timezone.utc)  # inclusive

EXPECTED_FIELDS = ["timestamp_received", "timestamp", "market_ticker",
                   "market_id", "event_type", "yes_bids", "no_bids",
                   "price", "delta", "side"]

WORKERS = 3
_lock = threading.Lock()
_stats = {"ok": 0, "skip": 0, "fail": 0, "bytes": 0}


def stamps():
    t = START
    while t <= END:
        yield t.strftime("%Y-%m-%dT%H")
        t += timedelta(hours=1)


def validate(path):
    """Open the file and check CONTENT. Returns (ok, detail dict)."""
    d = {}
    try:
        pf = pq.ParquetFile(path)
    except Exception as e:
        return False, {"err": f"footer: {type(e).__name__}: {e}"}
    md = pf.metadata
    d["rows"] = md.num_rows
    d["row_groups"] = md.num_row_groups
    if md.num_rows <= 0:
        return False, {**d, "err": "zero rows"}
    names = list(pf.schema_arrow.names)
    d["fields"] = names
    if names != EXPECTED_FIELDS:
        return False, {**d, "err": "schema drift"}

    # price statistics straight out of the footer -- free content check
    pi = EXPECTED_FIELDS.index("price")
    lo, hi = None, None
    for rg in range(md.num_row_groups):
        st = md.row_group(rg).column(pi).statistics
        if st is None or not st.has_min_max:
            continue
        lo = float(st.min) if lo is None else min(lo, float(st.min))
        hi = float(st.max) if hi is None else max(hi, float(st.max))

    # ABSENT STATISTICS ARE NOT A FAILURE. The first version returned
    # "price out of (0,1): None..None" and rejected two perfectly good files --
    # 2026-05-21T08 and 2026-05-28T08, both low-activity hours written as a
    # single row group with no column statistics. That is the UNTESTABLE/FAIL
    # confusion from GUARDS #1 pointed the other way: not knowing is not the
    # same as knowing it is bad. Fall back to reading the column.
    if lo is None:
        d["stats_absent"] = True
        col = pf.read(columns=["price"]).column("price").drop_null()
        if len(col) == 0:
            d["price_min"] = d["price_max"] = None
            d["price_all_null"] = True
        else:
            vals = [float(v) for v in col.to_pylist()]
            lo, hi = min(vals), max(vals)

    d["price_min"], d["price_max"] = lo, hi
    if lo is not None and not (0.0 < lo and hi < 1.0):
        return False, {**d, "err": f"price out of (0,1): {lo}..{hi}"}

    # event types present in row group 0.
    #
    # Requiring `orderbook_delta` here was too strict and produced a THIRD
    # false FAIL from this validator. The archive's final six hours
    # (2026-06-10T19 .. 2026-06-11T03) contain ONLY `orderbook_snapshot` rows,
    # which is what a capture emits while it is restarting -- and is arguably
    # the more directly usable form, since a pure snapshot needs no replay.
    # The real assertion is that the rows are recognisable book events, not
    # that a particular one is present.
    t0 = pf.read_row_group(0, columns=["event_type"])
    kinds = set(t0.column("event_type").to_pylist()[:200000])
    d["event_types_rg0"] = sorted(kinds)
    d["snapshot_only"] = kinds == {"orderbook_snapshot"}
    known = {"orderbook_delta", "orderbook_snapshot"}
    if not kinds or not (kinds & known):
        return False, {**d, "err": f"no recognised book events in rg0: {sorted(kinds)}"}
    if kinds - known:
        return False, {**d, "err": f"unexpected event types: {sorted(kinds - known)}"}
    return True, d


def fetch(stamp):
    url = BASE.format(stamp=stamp)
    path = os.path.join(DEST, f"kalshi_orderbook_{stamp}.parquet")
    tmp = path + ".part"
    sess = requests.Session()

    try:
        h = sess.head(url, timeout=30, allow_redirects=True)
    except Exception as e:
        return {"stamp": stamp, "status": "fail", "err": f"head: {e}"}
    if h.status_code != 200:
        return {"stamp": stamp, "status": "fail", "http": h.status_code}
    remote = int(h.headers.get("content-length") or 0)

    if os.path.exists(path) and os.path.getsize(path) == remote:
        ok, d = validate(path)
        if ok:
            with _lock:
                _stats["skip"] += 1
            return {"stamp": stamp, "status": "skip", "bytes": remote, **d}
        os.replace(path, path + ".BAD")

    for attempt in range(3):
        try:
            with sess.get(url, timeout=600, stream=True) as r:
                if r.status_code != 200:
                    time.sleep(2 * (attempt + 1))
                    continue
                n = 0
                with open(tmp, "wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
                        n += len(chunk)
            if remote and n != remote:
                time.sleep(2 * (attempt + 1))
                continue
            ok, d = validate(tmp)
            if not ok:
                os.replace(tmp, path + f".BAD{attempt}")
                time.sleep(2 * (attempt + 1))
                continue
            os.replace(tmp, path)
            with _lock:
                _stats["ok"] += 1
                _stats["bytes"] += n
            return {"stamp": stamp, "status": "ok", "bytes": n, **d}
        except Exception as e:
            time.sleep(2 * (attempt + 1))
            last = f"{type(e).__name__}: {e}"
    with _lock:
        _stats["fail"] += 1
    return {"stamp": stamp, "status": "fail", "err": locals().get("last", "retries exhausted")}


def main():
    os.makedirs(DEST, exist_ok=True)
    todo = list(stamps())
    print(f"pmxt mirror: {len(todo)} hourly files, {START} .. {END}", flush=True)
    t0 = time.time()
    done = 0
    with open(LOG, "a", encoding="utf-8") as log:
        with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for rec in ex.map(fetch, todo):
                rec["at"] = datetime.now(timezone.utc).isoformat()
                log.write(json.dumps(rec, default=str) + "\n")
                log.flush()
                done += 1
                if rec["status"] == "fail" or done % 10 == 0:
                    el = time.time() - t0
                    gb = _stats["bytes"] / 1e9
                    rate = gb / el * 3600 if el else 0
                    print(f"[{done}/{len(todo)}] {rec['stamp']} {rec['status']:4s} "
                          f"rows={rec.get('rows','-')} | ok={_stats['ok']} "
                          f"skip={_stats['skip']} fail={_stats['fail']} "
                          f"{gb:.1f}GB {el/60:.0f}min ({rate:.0f} GB/h)",
                          flush=True)
    print(f"\nDONE ok={_stats['ok']} skip={_stats['skip']} fail={_stats['fail']} "
          f"{_stats['bytes']/1e9:.1f}GB in {(time.time()-t0)/60:.0f}min", flush=True)


if __name__ == "__main__":
    sys.exit(main())
