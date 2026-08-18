"""Does selling out when the other mentality disagrees beat holding?

Mailbox 017, his idea, pre-registered in PREREGISTRATION_SELLOUT.md.

    "would it make more sense for us to just sell the bet and take the one
     dollar loss than to hold on and risk nine dollars on something that's
     much riskier?"

⚠ THE TRIGGER IS INFORMATION, NOT PRICE. Everything already measured in this
repo about stopping out -- his in-play bot (-2.29c -> -9.36c), the copy-trading
bot (8 of 9 recovered), our own exit-once arm -- fires on a PRICE MOVE. None of
them can see what another mentality decided. So none of them answer this.

Prices are REAL: bid and ask from the 12,059 rescued markets, at the minute the
second mentality entered. Not `100 - what they paid`. Exit fee from
common/kalshi_fees.py, which is the only fee implementation in this repo.

    python src/sellout.py
"""
from __future__ import annotations

import random
import sqlite3
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import engine as E                                    # noqa: E402
from common.kalshi_fees import fee_order_cents        # noqa: E402

TRUTH = HERE.parent / "data" / "kalshi_truth.db"
A, B = "starter__hold", "early__hold"


def firings(con):
    """Games where `A` held a live position when `B` entered the same game."""
    rows = {}
    for bot in (A, B):
        for r in con.execute(
                "SELECT bot, game_key, ticker, contracts, entry_price_c, "
                "entry_fee_c, pnl_c, opened_utc, closed_utc FROM positions "
                "WHERE bot=? AND status IN ('settled','closed')", (bot,)):
            rows.setdefault(r["game_key"], {})[bot] = dict(r)
    out = []
    for g, d in rows.items():
        if A not in d or B not in d:
            continue
        a, b = d[A], d[B]
        if b["opened_utc"] <= a["opened_utc"]:
            continue                       # B was already in; nothing to react to
        out.append({"game": g, "held": a, "trigger": b,
                    "disagree": a["ticker"] != b["ticker"]})
    out.sort(key=lambda x: x["trigger"]["opened_utc"])
    return out


def sell_price_c(tcon, ticker, when_utc):
    """REAL bid at the minute the other bot entered. None if the tape has no row.

    We sell what we hold, so we hit the BID -- never the mid, never the ask.
    """
    ts = int(datetime.fromisoformat(when_utc).replace(
        tzinfo=timezone.utc).timestamp())
    r = tcon.execute(
        "SELECT end_ts, yes_bid_close_c, yes_ask_close_c FROM candle "
        "WHERE ticker=? AND yes_bid_close_c IS NOT NULL "
        "ORDER BY ABS(end_ts-?) LIMIT 1", (ticker, ts)).fetchone()
    if not r or abs(r["end_ts"] - ts) > 3600:
        return None, None
    return r["yes_bid_close_c"], r["yes_ask_close_c"]


def pnl_if_sold(pos, bid_c):
    """Money if we sell the whole position at `bid_c`, fee included."""
    n = pos["contracts"]
    paid = n * pos["entry_price_c"] / 100.0 + (pos["entry_fee_c"] or 0) / 100.0
    got = n * bid_c / 100.0 - float(fee_order_cents(bid_c, n)) / 100.0
    return got - paid


def arms(fs, tcon, label_of):
    """Four arms on the SAME games. label_of(f) -> True means 'sell'."""
    res = {k: 0.0 for k in ("hold", "sell")}
    fired = moved = 0
    moves = []
    for f in fs:
        held = f["held"]
        hold_pnl = (held["pnl_c"] or 0) / 100.0
        if not label_of(f):
            res["hold"] += hold_pnl
            res["sell"] += hold_pnl        # arm did not fire -> same as holding
            continue
        bid, ask = sell_price_c(tcon, held["ticker"],
                                f["trigger"]["opened_utc"])
        if bid is None:
            res["hold"] += hold_pnl
            res["sell"] += hold_pnl
            continue
        fired += 1
        moves.append(bid - held["entry_price_c"])
        res["hold"] += hold_pnl
        res["sell"] += pnl_if_sold(held, bid)
    return res, fired, moves


if __name__ == "__main__":
    con = E.connect()
    tcon = sqlite3.connect(TRUTH)
    tcon.row_factory = sqlite3.Row
    fs = firings(con)
    dis = [f for f in fs if f["disagree"]]
    print(f"games where the other bot entered AFTER we were already in: "
          f"{len(fs)}")
    print(f"  of those, it took the OPPOSITE side: {len(dis)}")
    print(f"  so this rule fires on about 1 game in "
          f"{round(72/max(1,len(dis)))} of everything the bot does\n")

    print("=" * 74)
    print("THE FOUR ARMS -- same games, same prices, only the rule differs")
    print("=" * 74)
    named = (("1 never sell (what happens now)", lambda f: False),
             ("2 sell when they DISAGREE (his idea)", lambda f: f["disagree"]),
             ("3 sell when they AGREE (the placebo)", lambda f: not f["disagree"]),
             ("4 sell on either (does selling itself matter)", lambda f: True))
    for nm, fn in named:
        r, fired, mv = arms(fs, tcon, fn)
        print(f"{nm:<44} fired {fired:>2}  -> ${r['sell']:>7.2f}   "
              f"(holding: ${r['hold']:.2f})")

    print("\n" + "=" * 74)
    print("THE SHUFFLED CONTROL -- labels randomly reassigned, 200 times")
    print("  If selling 'works' on shuffled labels, every number above is void.")
    print("=" * 74)
    rng = random.Random(20260817)
    base_hold = arms(fs, tcon, lambda f: False)[0]["hold"]
    outs = []
    for _ in range(200):
        lab = {f["game"]: rng.random() < (len(dis) / max(1, len(fs)))
               for f in fs}
        r, _, _ = arms(fs, tcon, lambda f: lab[f["game"]])
        outs.append(r["sell"] - base_hold)
    outs.sort()
    real = arms(fs, tcon, lambda f: f["disagree"])[0]
    print(f"  shuffled: middle ${statistics.median(outs):.2f}, "
          f"range ${outs[5]:.2f} to ${outs[-6]:.2f}")
    print(f"  his rule: ${real['sell'] - base_hold:.2f} against holding")

    print("\n" + "=" * 74)
    print("THE SELL PRICE -- his premise is that the price has run away by now")
    print("=" * 74)
    for f in dis:
        h = f["held"]
        bid, ask = sell_price_c(tcon, h["ticker"], f["trigger"]["opened_utc"])
        got = "no tape" if bid is None else f"{bid:.0f}c bid"
        d = "" if bid is None else f"  ({bid - h['entry_price_c']:+.0f}c)"
        print(f"  {f['game']:<22} bought {h['entry_price_c']:.0f}c  "
              f"-> {got}{d}")
    con.close()
    tcon.close()
