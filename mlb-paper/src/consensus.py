"""Who else was on this game? — the interface `livedesk` calls.

Mailbox 013, job 1. Built HERE and not in `livedesk`, so there is one
implementation and two tools never edit one folder.

    from consensus import who_else
    who_else("2026-08-14:KC@LAD", asking="starter")

## ⚠ THIS IS INFORMATION, NOT A RULE

It reports what other mentalities did. **It does not filter, rank, veto or
recommend, and it must not be made to.**

The reason is the whole point. The observation behind it — `starter` makes money
on games another bot also traded and loses on the ones it picks alone — **was
found by looking at results, and has never been tested on a game that was not
used to find it.** Applying it as a filter would be fitting a rule to the games
that suggested it. Logging it forward is how it becomes testable: in a month
there will be games where the flag was recorded BEFORE the outcome, and those
games can answer the question honestly.

So: log it, show it, and do not act on it. `livedesk` displays it to a human who
decides.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as E                     # noqa: E402
import mentalities as MEN              # noqa: E402

FAMILIES = tuple(MEN.MENTALITIES)


def who_else(game_key, asking=None, con=None, include_shadows=True):
    """Every mentality with a view on this game, and which side it took.

    Returns a dict, always the same shape, safe to call before or after the
    game and safe to call when nothing is known:

        {
          "game_key": "2026-08-14:KC@LAD",
          "asking": "starter",
          "positions": [                       # actually took money-shaped risk
             {"mentality": "early", "ticker": "...-LAD", "side": "YES",
              "entry_price_c": 54, "contracts": 8, "same_side_as_asking": True,
              "opened_utc": "..."},
          ],
          "views_not_taken": [                 # a real view that failed the bar
             {"mentality": "park-air", "ticker": "...-9", "side": "NO",
              "adjustment_c": 2.9},
          ],
          "n_agree": 1,        # took the SAME contract as `asking`
          "n_oppose": 0,       # took a DIFFERENT contract on the same game
          "alone": False,      # nobody else took a position
          "summary": "early agreed"           # one line, plain English
        }

    `alone` is the field worth showing a human, because it is the one the
    observation was about. It is TRUE when no other mentality took a position,
    which historically is where `starter` lost money.
    """
    close = False
    if con is None:
        con = E.connect()
        close = True
    try:
        mine = None
        if asking:
            row = con.execute(
                "SELECT ticker FROM positions WHERE game_key=? AND bot LIKE ? "
                "ORDER BY opened_utc ASC LIMIT 1",
                (game_key, f"{asking}__%")).fetchone()
            mine = row["ticker"] if row else None

        positions, seen = [], set()
        for r in con.execute(
                "SELECT bot, ticker, side, entry_price_c, contracts, "
                "       opened_utc, status FROM positions WHERE game_key=? "
                "ORDER BY opened_utc ASC", (game_key,)):
            fam = r["bot"].split("__")[0]
            if fam == asking or fam in seen:
                continue
            seen.add(fam)
            positions.append({
                "mentality": fam, "ticker": r["ticker"], "side": r["side"],
                "entry_price_c": r["entry_price_c"],
                "contracts": r["contracts"], "opened_utc": r["opened_utc"],
                "status": r["status"],
                "same_side_as_asking": (None if mine is None
                                        else r["ticker"] == mine),
            })

        views = []
        if include_shadows:
            import json
            for r in con.execute(
                    "SELECT mentality, reasoning_json FROM decisions "
                    "WHERE game_key=? AND kind='shadow'", (game_key,)):
                if r["mentality"] == asking:
                    continue
                try:
                    d = json.loads(r["reasoning_json"])
                except json.JSONDecodeError:
                    continue
                det = d.get("detail") or {}
                views.append({"mentality": r["mentality"],
                              "adjustment_c": det.get("adjustment_c"),
                              "reason": d.get("reason")})

        n_agree = sum(1 for p in positions if p["same_side_as_asking"] is True)
        n_oppose = sum(1 for p in positions if p["same_side_as_asking"] is False)
        alone = not positions

        if alone:
            summary = "NOBODY ELSE took a position on this game"
        else:
            bits = []
            if n_agree:
                bits.append(", ".join(p["mentality"] for p in positions
                                      if p["same_side_as_asking"] is True)
                            + (" agreed" if n_agree == 1 else " agreed"))
            if n_oppose:
                bits.append(", ".join(p["mentality"] for p in positions
                                      if p["same_side_as_asking"] is False)
                            + " took the OTHER side")
            if not bits:
                bits.append(", ".join(p["mentality"] for p in positions)
                            + " also traded it")
            summary = "; ".join(bits)

        return {"game_key": game_key, "asking": asking,
                "positions": positions, "views_not_taken": views,
                "n_agree": n_agree, "n_oppose": n_oppose, "alone": alone,
                "summary": summary,
                "caveat": "INFORMATION ONLY. The pattern behind this was found "
                          "by looking at results and has never been tested on "
                          "an unseen game. Do not filter on it."}
    finally:
        if close:
            con.close()


def decompose(asking="starter", other="early", con=None):
    """The measurement behind the flag, recomputed on demand.

    Kept next to the interface deliberately: anyone who wants to use the flag
    can re-run the evidence for it in one call and see how thin it is.
    """
    close = False
    if con is None:
        con = E.connect()
        close = True
    try:
        def games(bot):
            return {r["game_key"] for r in con.execute(
                "SELECT DISTINCT game_key FROM positions WHERE bot=? "
                "AND status IN ('settled','closed')", (bot,))}

        a, b = f"{asking}__hold", f"{other}__hold"
        ga, gb = games(a), games(b)
        out = {}
        for label, keys in (("agreed_same_side", None),
                            ("opposite_sides", None),
                            ("alone", ga - gb),
                            ("all", ga)):
            pass
        agree, oppose = set(), set()
        for g in ga & gb:
            ta = con.execute("SELECT ticker FROM positions WHERE bot=? AND "
                             "game_key=?", (a, g)).fetchone()
            tb = con.execute("SELECT ticker FROM positions WHERE bot=? AND "
                             "game_key=?", (b, g)).fetchone()
            if not ta or not tb:
                continue
            (agree if ta["ticker"] == tb["ticker"] else oppose).add(g)
        for label, keys in (("agreed_same_side", agree),
                            ("opposite_sides", oppose),
                            ("ALONE", ga - gb), ("everything", ga)):
            if not keys:
                out[label] = {"games": 0}
                continue
            rows = con.execute(
                "SELECT pnl_c, contracts, entry_price_c, entry_fee_c "
                "FROM positions WHERE bot=? AND status IN ('settled','closed') "
                "AND game_key IN (%s)" % ",".join("?" * len(keys)),
                tuple([a] + list(keys))).fetchall()
            pnl = sum(r["pnl_c"] or 0 for r in rows) / 100.0
            staked = sum(r["contracts"] * r["entry_price_c"] + r["entry_fee_c"]
                         for r in rows) / 100.0
            out[label] = {"games": len(keys), "profit": round(pnl, 2),
                          "staked": round(staked, 2),
                          "return_pct": round(100 * pnl / staked, 1)
                          if staked else None}
        return out
    finally:
        if close:
            con.close()


if __name__ == "__main__":
    import json
    con = E.connect()
    print("## the decomposition, recomputed now\n")
    d = decompose(con=con)
    print(f"{'bucket':<20} {'games':>6} {'profit$':>9} {'staked$':>9} {'return':>8}")
    for k, v in d.items():
        if v.get("games"):
            print(f"{k:<20} {v['games']:>6} {v['profit']:>9.2f} "
                  f"{v['staked']:>9.2f} {str(v['return_pct'])+'%':>8}")
    print("\n## the interface, on the most recent game\n")
    g = con.execute("SELECT game_key FROM positions ORDER BY opened_utc DESC "
                    "LIMIT 1").fetchone()
    if g:
        print(json.dumps(who_else(g["game_key"], asking="starter", con=con),
                         indent=2, default=str)[:1400])
    con.close()
