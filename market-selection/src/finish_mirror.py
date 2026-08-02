"""Fetch whichever pmxt hours are still missing, with the corrected validator.

The main run reported fail=8. Two of those were recovered by hand once the
validator's absent-statistics bug was fixed. This finds whatever is genuinely
still missing from disk -- not from the log, which is stale -- and fetches it.
Disk is the source of truth.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, os.path.dirname(__file__))
from mirror_pmxt import DEST, LOG, START, END, validate  # noqa: E402

UA = {"User-Agent": "market-selection-research/1.0"}


def stamps():
    t = START
    while t <= END:
        yield t.strftime("%Y-%m-%dT%H")
        t += timedelta(hours=1)


def main():
    missing = [s for s in stamps()
               if not os.path.exists(os.path.join(
                   DEST, f"kalshi_orderbook_{s}.parquet"))]
    print(f"{len(missing)} of 662 hours missing from disk")
    if not missing:
        print("mirror is complete")
        return
    for s in missing:
        print(f"  {s}", end=" ", flush=True)
        url = f"https://r2kalshi.pmxt.dev/kalshi_orderbook_{s}.parquet"
        path = os.path.join(DEST, f"kalshi_orderbook_{s}.parquet")
        tmp = path + ".part"
        ok = False
        for attempt in range(3):
            try:
                r = requests.get(url, headers=UA, timeout=600)
            except requests.RequestException as e:
                print(f"[net {type(e).__name__}]", end=" ")
                continue
            if r.status_code != 200:
                print(f"[http {r.status_code}]", end=" ")
                break
            with open(tmp, "wb") as fh:
                fh.write(r.content)
            good, d = validate(tmp)
            if good:
                os.replace(tmp, path)
                rec = {"stamp": s, "status": "ok", "bytes": len(r.content),
                       "at": datetime.now(timezone.utc).isoformat(), **d}
                with open(LOG, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, default=str) + "\n")
                print(f"OK rows={d['rows']} price={d.get('price_min')}-"
                      f"{d.get('price_max')}")
                ok = True
                break
            print(f"[invalid: {d.get('err')}]", end=" ")
            os.remove(tmp)
        if not ok:
            print("STILL MISSING")

    left = [s for s in stamps()
            if not os.path.exists(os.path.join(
                DEST, f"kalshi_orderbook_{s}.parquet"))]
    n = 662 - len(left)
    gb = sum(os.path.getsize(os.path.join(DEST, f))
             for f in os.listdir(DEST) if f.endswith(".parquet")) / 1e9
    print(f"\nmirror now {n}/662 files, {gb:.1f} GB")
    if left:
        print(f"still missing: {left}")


if __name__ == "__main__":
    main()
