"""Settlement, replayed against REAL finished games.

The highest-risk untested path in the package. Nothing had settled when the run
of record started, so a broken settlement would not have shown up for hours --
and by then Kalshi's ~69-day window is the only place the strike lives, because
closed markets 404 for good.

This builds synthetic positions on the real tickers of games that have actually
finished, runs the real settlement code, and checks the answer against the real
box score. It writes to a throwaway in-memory database and never touches
`data/paper.db`.

    python -m pytest tests/test_settlement_live.py -q -s

Marked `live` because it fetches. It is skipped automatically if the network is
not available, so the normal test run stays offline and fast.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))

import engine as E        # noqa: E402
import kalshi as K        # noqa: E402
import statsapi as S      # noqa: E402


def _finished_games(days_back=1, limit=6):
    day = datetime.now(timezone.utc).date() - timedelta(days=days_back)
    try:
        games = S.schedule(day)
    except RuntimeError:
        pytest.skip("statsapi unreachable; this test needs the network")
    out = []
    for g in games:
        if (g.get("status") or {}).get("abstractGameState") != "Final":
            continue
        try:
            f = S.final_score(g["gamePk"])
        except RuntimeError:
            continue
        if f and f["is_final"]:
            out.append((g, f))
        if len(out) >= limit:
            break
    if not out:
        pytest.skip(f"no finished games on {day}")
    return out


def _kalshi_ticker_for(g, series):
    """The real Kalshi ticker for a finished game, if it is still listed.

    Settled markets are what this needs, and Kalshi keeps them for ~69 days.
    Built from the schedule rather than guessed, and skipped if absent -- a
    missing ticker is a listing fact, not a settlement bug.
    """
    starts = datetime.fromisoformat(g["gameDate"].replace("Z", "+00:00"))
    try:
        mkts = K.markets(series, status="settled")
    except RuntimeError:
        pytest.skip("kalshi unreachable")
    hits = []
    for m in mkts:
        p = K.ticker_parts(m["ticker"])
        if not p:
            continue
        if abs((p["starts"] - starts).total_seconds()) > 20 * 60:
            continue
        if (K.CODE.get(p["home"]) == g["teams"]["home"]["team"]["name"]
                and K.CODE.get(p["away"]) == g["teams"]["away"]["team"]["name"]):
            hits.append((m, p))
    return hits


@pytest.mark.parametrize("days_back", [1])
def test_moneyline_settles_to_the_real_winner(days_back):
    checked = 0
    for g, f in _finished_games(days_back):
        for m, p in _kalshi_ticker_for(g, "KXMLBGAME"):
            pos_yes = {"ticker": m["ticker"], "side": "YES"}
            pos_no = {"ticker": m["ticker"], "side": "NO"}
            val = E.settle_value_c(pos_yes, f)
            if val is None:
                continue
            club = K.CODE[p["suffix"]]
            won = ((f["home_runs"] > f["away_runs"])
                   == (club == g["teams"]["home"]["team"]["name"]))
            assert val == (100 if won else 0), (
                f"{m['ticker']}: {club} "
                f"{'won' if won else 'lost'} "
                f"{f['away_runs']}-{f['home_runs']} but settled {val}")
            assert E.settle_value_c(pos_no, f) == 100 - val

            # and cross-check against Kalshi's OWN recorded result, which is
            # an entirely independent source from the box score
            res = (m.get("result") or "").lower()
            if res in ("yes", "no"):
                assert val == (100 if res == "yes" else 0), (
                    f"{m['ticker']}: box score says {val}, "
                    f"Kalshi says result={res}")
            checked += 1
            print(f"  OK {m['ticker']:<42} {club:<24} "
                  f"{f['away_runs']}-{f['home_runs']} -> {val} "
                  f"(kalshi result={res or 'n/a'})")
    if checked == 0:
        pytest.skip("no settled KXMLBGAME markets matched a finished game")
    assert checked >= 2


def test_totals_settle_against_the_recorded_strike():
    """And the strike must come from the recorded map, never the rung index."""
    checked = 0
    for g, f in _finished_games(1):
        for m, p in _kalshi_ticker_for(g, "KXMLBTOTAL"):
            strike = m.get("floor_strike")
            if strike is None:
                continue
            E.load_strikes([{"ticker": m["ticker"], "floor_strike": strike}])
            val = E.settle_value_c({"ticker": m["ticker"], "side": "YES"}, f)
            if val is None:
                continue
            expect = 100 if f["total_runs"] > float(strike) else 0
            assert val == expect, (
                f"{m['ticker']}: total {f['total_runs']} vs strike {strike} "
                f"-> expected {expect}, got {val}")
            res = (m.get("result") or "").lower()
            if res in ("yes", "no"):
                assert val == (100 if res == "yes" else 0), (
                    f"{m['ticker']}: strike {strike}, total {f['total_runs']} "
                    f"gives {val}, but Kalshi says result={res}. "
                    f"If this fires, the RUNG INDEX has been read as the "
                    f"strike somewhere.")
            checked += 1
            print(f"  OK {m['ticker']:<44} strike {strike:<5} "
                  f"total {f['total_runs']:<3} -> {val} "
                  f"(kalshi result={res or 'n/a'})")
    if checked == 0:
        pytest.skip("no settled KXMLBTOTAL markets matched a finished game")
    assert checked >= 3


def test_full_settlement_pass_updates_positions_and_pnl():
    """End to end through the real `settle_open_positions`, in a scratch DB."""
    games = _finished_games(1, limit=2)
    g, f = games[0]
    hits = _kalshi_ticker_for(g, "KXMLBGAME")
    if not hits:
        pytest.skip("no settled moneyline market for that game")
    m, p = hits[0]

    con = E.connect(":memory:")
    con.execute(
        "INSERT INTO positions (id, bot, game_key, game_pk, ticker, side, "
        "contracts, entry_price_c, entry_fee_c, opened_utc, exit_mode, "
        "status, decision_id) VALUES ('p1','starter__hold','g',?,?, 'YES', "
        "10, 45, 5.0, '2026-01-01T00:00:00+00:00','hold','open','d')",
        (g["gamePk"], m["ticker"]))
    con.commit()
    n = E.settle_open_positions(con, {g["gamePk"]: f})
    assert n == 1
    row = con.execute("SELECT * FROM positions WHERE id='p1'").fetchone()
    assert row["status"] == "settled"
    assert row["settle_value_c"] in (0, 100)
    # P&L = (settle - entry) * contracts - the ONE entry fee. A position held
    # to settlement pays one fee, not two, because Kalshi charges on the trade.
    assert row["pnl_c"] == (row["settle_value_c"] - 45) * 10 - 5.0
    print(f"  OK end-to-end: {m['ticker']} settled {row['settle_value_c']}, "
          f"pnl {row['pnl_c']}c on 10 contracts bought at 45c")
    con.close()
