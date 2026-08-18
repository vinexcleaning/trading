"""Re-pull, at REAL minute resolution, every market our own bots traded.

The full 12,059-market re-pull takes over an hour. This does the 139 markets
that our own positions actually sit on, so his question gets answered now
rather than after the sweep. Also adds markets traded after the capture cutoff.
"""
from __future__ import annotations
import sys, time
from datetime import datetime, timezone
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import capture_truth as C, engine as E, kalshi as K   # noqa: E402

con, t = E.connect(), C.db()
need = sorted({r[0] for r in con.execute(
    "SELECT DISTINCT ticker FROM positions WHERE status IN ('settled','closed')")})
have = {r[0] for r in t.execute("SELECT ticker FROM market")}
now = datetime.now(timezone.utc).isoformat(timespec="seconds")

# markets traded after the capture cutoff have no market row yet
for tk in need:
    if tk in have:
        continue
    p = K.ticker_parts(tk)
    if not p:
        continue
    t.execute("INSERT OR IGNORE INTO market (ticker, series, game_date, "
              "starts_utc, away, home, suffix, captured_utc) VALUES "
              "(?,?,?,?,?,?,?,?)",
              (tk, "KXMLBGAME", p["starts"].date().isoformat(),
               p["starts"].isoformat(), p["away"], p["home"], p["suffix"], now))
t.commit()

got = fail = rows = 0
for i, tk in enumerate(need, 1):
    r = t.execute("SELECT starts_utc FROM market WHERE ticker=?", (tk,)).fetchone()
    if not r:
        continue
    st = int(datetime.fromisoformat(r["starts_utc"]).timestamp())
    try:
        d = K.get(f"/series/KXMLBGAME/markets/{tk}/candlesticks",
                  start_ts=st - 72 * 3600, end_ts=st + 6 * 3600,
                  period_interval=1)
    except Exception as e:                              # noqa: BLE001
        fail += 1
        print(f"  ! {tk}: {type(e).__name__}")
        time.sleep(0.35)
        continue
    cs = d.get("candlesticks") or []
    for c in cs:
        t.execute("INSERT OR REPLACE INTO candle (ticker, end_ts, "
                  "yes_bid_close_c, yes_ask_close_c, price_close_c, volume, "
                  "open_interest) VALUES (?,?,?,?,?,?,?)",
                  (tk, c.get("end_period_ts"),
                   C._c((c.get("yes_bid") or {}).get("close_dollars")),
                   C._c((c.get("yes_ask") or {}).get("close_dollars")),
                   C._c((c.get("price") or {}).get("close_dollars")),
                   c.get("volume_fp"), c.get("open_interest_fp")))
    rows += len(cs)
    if cs:
        got += 1
    if i % 25 == 0:
        t.commit()
        print(f"  {i}/{len(need)}  markets {got}, rows {rows}, failed {fail}")
    time.sleep(0.3)
t.commit()
print(f"\n  {got} markets re-pulled at 1-minute resolution, {rows} rows, {fail} failed")
con.close(); t.close()
