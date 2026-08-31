"""Mailbox 024: sample Kalshi and Polymarket for the SAME market within SECONDS.

`BH024` could not answer whether cross-venue arbitrage exists, because
`record.py` walks Kalshi, then Polymarket, then Pinnacle -- leaving the two
venues a **median 6.5 minutes apart** inside one `cycle_id`. The skew placebo
settled it: crossings scale linearly with deliberate mis-alignment at
correlation 0.9975, ~14.7 extra "arbitrages" per minute, extrapolating to **7
real against 125 observed. 94 in 100 were the clock.**

**That is an instrument limit, not a finding. This removes it.**

WHAT IT DOES DIFFERENTLY, AND IT IS ONLY ONE THING
---------------------------------------------------
For each matched pair it fires the Kalshi order book and BOTH Polymarket outcome
books **concurrently**, and **records the arrival timestamp of each response**.
The measured gap is stored on every row. Nothing is assumed to have worked --
requirement 1 of the instruction is "do not assume", so the gap is data.

WHAT IT DELIBERATELY REUSES
----------------------------
The matching gate from `crossvenue_arb.py`, unchanged, because it passed: same
clubs + same date + same numeric line, three independent agreements, **969 pairs
across 202 games**. Both venues put the line in the identifier, which is what
makes this family safe to join at all.

⚠ IT WRITES ITS OWN DATABASE AND HOLDS ITS OWN LOCK
-----------------------------------------------------
`data/paired.db`, never `record.db`. Two writers on one SQLite file died with
`database is locked` inside 19 minutes on 2026-08-09, and `kalshi_cycle` holds a
single write transaction for 340-1,400 s. The recorder is the one asset here
that cannot be re-pulled at any price, so nothing else goes near its file.

FEES, BOTH LEGS, FROM PRIMARY SOURCES
--------------------------------------
* Kalshi     `roundup(0.07 x C x P x (1-P))` -- `common/kalshi_fees.py`, the
             repo's only implementation. Schedule effective 2026-07-07.
* Polymarket `C x 0.05 x p x (1-p)` taker on SPORTS; makers free.
             https://docs.polymarket.com/trading/fees, retrieved 2026-08-31.
             ⚠ This repo previously assumed Polymarket was free. It is not (BH025).

NOT A TRADING LOOP. No credentials, no order code, no execution path.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT.parent))
import venues as V  # noqa: E402
from crossvenue_arb import (ALIAS, CLUBS, ET, MON, TSFMT, poly_fee_cents,  # noqa: E402
                            split_pair)
from common.kalshi_fees import fee_rate_cents  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

DB = ROOT / "data" / "paired.db"
UA = {"User-Agent": "bot-hunt-research/1.0"}
SESSION = requests.Session()

SCHEMA = """
create table if not exists samples (
  sample_id integer primary key autoincrement,
  started_utc text, finished_utc text, n_pairs integer,
  median_gap_ms real, p90_gap_ms real, max_gap_ms real, note text);
create table if not exists quotes (
  sample_id integer, pair_key text, game_date text, clubs text, line real,
  kalshi_ticker text, poly_slug text,
  k_ts_utc text, p_ts_utc text, gap_ms real,
  k_bid_c real, k_ask_c real, k_bid_size real, k_ask_size real,
  p_over_bid_c real, p_over_ask_c real, p_over_ask_size real,
  p_under_bid_c real, p_under_ask_c real, p_under_ask_size real,
  first_pitch_utc text, in_play integer);
create index if not exists ix_q on quotes(pair_key, sample_id);
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime(TSFMT)


def _pid_alive(pid: int) -> bool:
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    import ctypes
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x00100000, False, pid)
    if not h:
        return False
    alive = k32.WaitForSingleObject(h, 0) == 0x00000102
    k32.CloseHandle(h)
    return bool(alive)


def claim_lock() -> None:
    """Same per-database lock as record.py. Never os.kill(pid,0) on Windows --
    CPython maps it to TerminateProcess and would kill the holder."""
    lock = DB.with_suffix(DB.suffix + ".lock")
    DB.parent.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        try:
            held = json.loads(lock.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            held = {}
        pid = held.get("pid")
        if isinstance(pid, int) and pid != os.getpid() and _pid_alive(pid):
            print(f"already running: pid {pid} owns {DB.name} -- exiting", flush=True)
            raise SystemExit(0)
        if pid:
            print(f"stale lock from pid {pid}; that process is gone, taking over",
                  flush=True)
    lock.write_text(json.dumps({"pid": os.getpid(), "started": now()}),
                    encoding="utf-8")
    import atexit
    atexit.register(lambda: lock.unlink(missing_ok=True))


# ------------------------------------------------------------- discovery ----

def discover():
    """Matched pairs for games that have NOT started. Returns list of dicts."""
    kal = {}
    for m in V.k_paginate("/markets", {"series_ticker": "KXMLBTOTAL",
                                       "status": "open", "limit": 200},
                          "markets", max_pages=15):
        strike = V.fnum(m.get("floor_strike"))
        if strike is None or m.get("strike_type") != "greater":
            continue
        mm = re.match(r"^KXMLBTOTAL-(\d{2})([A-Z]{3})(\d{2})(\d{2})(\d{2})([A-Z]+)-",
                      m.get("ticker") or "")
        if not mm:
            continue
        pair = split_pair(mm.group(6))
        if not pair:
            continue
        try:
            start = datetime(2000 + int(mm.group(1)), MON[mm.group(2)],
                             int(mm.group(3)), int(mm.group(4)), int(mm.group(5)),
                             tzinfo=ET).astimezone(timezone.utc).strftime(TSFMT)
        except (ValueError, KeyError):
            continue
        d = f"20{mm.group(1)}-{MON[mm.group(2)]:02d}-{mm.group(3)}"
        kal[(d, frozenset(pair), strike)] = (m["ticker"], start)

    poly = {}
    for tag in ("mlb", "baseball"):
        r = V.p_gamma("/events", {"tag_slug": tag, "closed": "false",
                                  "active": "true", "limit": 200,
                                  "order": "volume24hr", "ascending": "false"})
        if r is None or r.status_code != 200:
            continue
        for e in (r.json() or []):
            for m in (e.get("markets") or []):
                slug = m.get("slug") or ""
                mm = re.match(r"^mlb-([a-z]+)-([a-z]+)-(\d{4}-\d{2}-\d{2})"
                              r"-total-(\d+)pt(\d)$", slug)
                if not mm or not m.get("acceptingOrders"):
                    continue
                a, b = mm.group(1).upper(), mm.group(2).upper()
                a, b = ALIAS.get(a, a), ALIAS.get(b, b)
                if a not in CLUBS or b not in CLUBS or a == b:
                    continue
                try:
                    toks = json.loads(m.get("clobTokenIds") or "[]")
                    outs = json.loads(m.get("outcomes") or "[]")
                except (json.JSONDecodeError, TypeError):
                    continue
                if len(toks) < 2 or len(outs) < 2:
                    continue
                tok = {str(o).strip().lower(): t for o, t in zip(outs, toks)}
                if "over" not in tok or "under" not in tok:
                    continue
                poly[(mm.group(3), frozenset((a, b)),
                      float(f"{mm.group(4)}.{mm.group(5)}"))] = (slug, tok)

    out = []
    nowu = now()
    for key in sorted(set(kal) & set(poly)):
        tk, start = kal[key]
        slug, tok = poly[key]
        out.append({"key": key, "ticker": tk, "slug": slug, "tok": tok,
                    "first_pitch": start, "in_play": start <= nowu})
    return out, len(kal), len(poly)


# ------------------------------------------------------- the paired fetch ----

def _get(url, params):
    """Bare fetch with its own arrival timestamp. No global throttle -- the
    whole point is that the two venues are hit at the same moment, and the
    shared pacer in venues.py would serialise them."""
    try:
        r = SESSION.get(url, params=params, headers=UA, timeout=20)
        return r, time.time()
    except requests.RequestException:
        return None, time.time()


def sample_pair(p):
    """Fire Kalshi and BOTH Polymarket books concurrently. Measure the gap."""
    with ThreadPoolExecutor(max_workers=3) as ex:
        fk = ex.submit(_get, f"{V.KALSHI}/markets/{p['ticker']}/orderbook",
                       {"depth": 20})
        fo = ex.submit(_get, f"{V.CLOB}/book", {"token_id": p["tok"]["over"]})
        fu = ex.submit(_get, f"{V.CLOB}/book", {"token_id": p["tok"]["under"]})
        (rk, tk_t), (ro, to_t), (ru, tu_t) = fk.result(), fo.result(), fu.result()
    if rk is None or rk.status_code != 200 or ro is None or ru is None:
        return None
    # ⚠ THE RENAMED-FIELD TRAP, AND I WALKED STRAIGHT INTO IT (GUARDS #12/#23).
    # v1 read `orderbook` -> `yes_fp`/`yes`. The live fields are
    # `orderbook_fp` -> `yes_dollars`/`no_dollars`, and the prices are DOLLARS,
    # so they need x100. v1 therefore captured 0 Kalshi quotes out of 66 while
    # Polymarket filled 66 of 66 -- and the analysis dutifully reported "0
    # crossings", which was a bug wearing a finding's clothes. Caught by
    # counting populated columns before believing the zero, not by care.
    try:
        ob = (rk.json() or {}).get("orderbook_fp") or {}
    except ValueError:
        return None

    def conv(rows):
        out = []
        for row in rows or []:
            try:
                out.append((float(row[0]) * 100.0, float(row[1])))
            except (TypeError, ValueError, IndexError):
                continue
        return out

    ylv, nlv = conv(ob.get("yes_dollars")), conv(ob.get("no_dollars"))
    yb, ya, bs, asz = V.k_touch(ylv or None, nlv or None)
    try:
        ovb, ovask, _, ovsz, _, _ = V.p_touch(ro.json() or {})
        unb, unask, _, unsz, _, _ = V.p_touch(ru.json() or {})
    except ValueError:
        return None
    p_t = max(to_t, tu_t)
    gap_ms = abs(p_t - tk_t) * 1000.0
    return {"k_ts": datetime.fromtimestamp(tk_t, timezone.utc).strftime(TSFMT),
            "p_ts": datetime.fromtimestamp(p_t, timezone.utc).strftime(TSFMT),
            "gap_ms": gap_ms, "k_bid": yb, "k_ask": ya,
            "k_bid_size": bs, "k_ask_size": asz,
            "p_over_bid": ovb, "p_over_ask": ovask, "p_over_ask_size": ovsz,
            "p_under_bid": unb, "p_under_ask": unask, "p_under_ask_size": unsz}


def run_once(con, include_inplay=False):
    pairs, nk, np_ = discover()
    live = [p for p in pairs if include_inplay or not p["in_play"]]
    t0 = now()
    print(f"   {t0}  matched {len(pairs)} pairs "
          f"({nk} kalshi / {np_} poly keyed), {len(live)} pre-game", flush=True)
    cur = con.execute("insert into samples (started_utc, n_pairs) values (?,?)",
                      (t0, len(live)))
    sid = cur.lastrowid
    con.commit()
    rows, gaps = [], []
    for p in live:
        q = sample_pair(p)
        if q is None:
            continue
        gaps.append(q["gap_ms"])
        d, clubs, line = p["key"]
        rows.append((sid, f"{d}|{'/'.join(sorted(clubs))}|{line}", d,
                     "/".join(sorted(clubs)), line, p["ticker"], p["slug"],
                     q["k_ts"], q["p_ts"], q["gap_ms"],
                     q["k_bid"], q["k_ask"], q["k_bid_size"], q["k_ask_size"],
                     q["p_over_bid"], q["p_over_ask"], q["p_over_ask_size"],
                     q["p_under_bid"], q["p_under_ask"], q["p_under_ask_size"],
                     p["first_pitch"], int(p["in_play"])))
        time.sleep(0.25)          # pace BETWEEN pairs, never inside one
    if rows:
        con.executemany("insert into quotes values (" + ",".join(["?"] * 22) + ")",
                        rows)
    gaps.sort()
    med = gaps[len(gaps) // 2] if gaps else None
    con.execute("update samples set finished_utc=?, median_gap_ms=?, p90_gap_ms=?, "
                "max_gap_ms=?, n_pairs=? where sample_id=?",
                (now(), med, gaps[int(0.9 * len(gaps))] if gaps else None,
                 max(gaps) if gaps else None, len(rows), sid))
    con.commit()
    if gaps:
        print(f"      captured {len(rows)} pairs   ⚠ MEASURED venue gap: "
              f"median {med:.0f} ms, p90 {gaps[int(0.9*len(gaps))]:.0f} ms, "
              f"max {max(gaps):.0f} ms", flush=True)
        print(f"      (record.py's equivalent gap was 6.5 MINUTES = 390,000 ms)",
              flush=True)
    else:
        print("      no pairs captured this pass", flush=True)
    return len(rows)



# ------------------------------------------------------------- reporting ----

def report(con):
    """The answer, AND the standing skew placebo beside it.

    Mailbox 024: "Do not re-run the skew placebo once and call it clean. Run it
    on every report. It is now the standard control for this instrument." So the
    same control that killed BH024 runs here every time -- if the venue gap ever
    creeps back up, the placebo will show it instead of the numbers quietly
    degrading.
    """
    import statistics as stx
    rows = con.execute(
        "select sample_id, pair_key, k_bid_c, k_ask_c, k_bid_size, k_ask_size, "
        "p_over_ask_c, p_over_ask_size, p_under_ask_c, p_under_ask_size, gap_ms "
        "from quotes where in_play=0").fetchall()
    ns = con.execute("select count(*) from samples").fetchone()[0]
    gaps = [r[10] for r in rows if r[10] is not None]
    print("=" * 78)
    print("PAIRED SAMPLER — REPORT")
    print("=" * 78)
    print(f"   samples taken            : {ns}")
    print(f"   pre-game observations    : {len(rows):,}")
    if gaps:
        gs = sorted(gaps)
        print(f"   ⚠ MEASURED venue gap     : median {stx.median(gs):.0f} ms, "
              f"p90 {gs[int(0.9*len(gs))]:.0f} ms, max {max(gs):.0f} ms")
        print(f"      record.py's gap was 390,000 ms (6.5 min) — "
              f"this is {390000/max(1,stx.median(gs)):,.0f}x tighter")

    def crossings(by_sample_offset=0):
        idx = {}
        for r in rows:
            idx.setdefault(r[1], {})[r[0]] = r
        n = 0
        for pk, per in idx.items():
            for sid, r in per.items():
                other = per.get(sid + by_sample_offset)
                if other is None:
                    continue
                ka, kb, kasz, kbsz = r[3], r[2], r[5], r[4]
                oa, ua = other[6], other[8]
                if ka is not None and ua is not None and ka + ua < 100:
                    n += 1
                if kb is not None and oa is not None and (100 - kb) + oa < 100:
                    n += 1
        return n

    real = crossings(0)
    print("")
    print(f"   THEORETICAL crossings, venues SIMULTANEOUS : {real}")
    net = 0
    for r in rows:
        ka, kb, oa, ua = r[3], r[2], r[6], r[8]
        if ka is not None and ua is not None:
            g = 100 - (ka + ua)
            if g > float(fee_rate_cents(ka)) + poly_fee_cents(ua):
                net += 1
        if kb is not None and oa is not None:
            g = 100 - ((100 - kb) + oa)
            if g > float(fee_rate_cents(100 - kb)) + poly_fee_cents(oa):
                net += 1
    print(f"   AFTER fees on BOTH legs                    : {net}")

    print("")
    print("   ⚠ STANDING SKEW PLACEBO — the control that killed BH024:")
    print("      deliberately mis-align the venues by whole samples and recount.")
    print("      If these rise with the offset, the instrument is measuring time.")
    for off in (0, 1, 2, 3):
        print(f"        offset {off} sample(s) : {crossings(off):>6}")
    print("      offset 0 is the real measurement; the rest must be higher for")
    print("      the instrument to be believed, and the gap between them is")
    print("      exactly what record.py could not separate.")



def main() -> None:
    if "--report" in sys.argv:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        report(con)
        return
    claim_lock()
    con = sqlite3.connect(DB, timeout=60.0)
    con.execute("pragma journal_mode=WAL")
    con.executescript(SCHEMA)
    every = 600
    if "--every" in sys.argv:
        every = int(sys.argv[sys.argv.index("--every") + 1])
    hours = 0
    if "--hours" in sys.argv:
        hours = float(sys.argv[sys.argv.index("--hours") + 1])
    once = "--once" in sys.argv
    print("=" * 78)
    print("PAIRED SAMPLER — Kalshi and Polymarket within SECONDS, not minutes")
    print("=" * 78)
    print(f"db={DB}  every={every}s  " + ("once" if once else f"hours={hours or 'forever'}"))
    end = time.time() + hours * 3600 if hours else None
    while True:
        t0 = time.time()
        try:
            run_once(con)
        except Exception as e:  # noqa: BLE001
            print(f"   sample failed: {type(e).__name__}: {e}", flush=True)
        if once or (end and time.time() > end):
            break
        time.sleep(max(5.0, every - (time.time() - t0)))
    con.close()


if __name__ == "__main__":
    main()
