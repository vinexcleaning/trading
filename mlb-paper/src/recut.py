"""The re-cut he approved: drop the games where `early` was near a coin flip.

Mailbox 023 job 1. His words: "run the recut that drops the coin flip games".

The reason it exists: `early` calls 53 in 100 games within 5 cents of even, its
fair sitting a median 4.7c from a coin flip across 1,873 live decisions. On
those games which side it takes turns on a cent or two of price -- so
"agreed" and "opposite" are labelled by noise rather than by two models
disagreeing.

⚠ Conviction is read for EVERY game, not just the ones `early` entered. On an
`alone` game `early` still formed a view and then declined, and that view is in
its decline reasoning. Reading conviction only off entries would have silently
dropped every `alone` game from the filtered cut and left the comparison
meaningless.

    python src/recut.py
"""
from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import engine as E                                     # noqa: E402

CUTS = (3, 5, 7)


def conviction(con):
    """How far `early`'s own fair value sat from an even game, per game.

    Entries store it as `stated_prob_c`; declines and shadows store
    `fair_home_c` inside `detail`. Both are read -- see the warning above.
    """
    out = {}
    for r in con.execute(
            "SELECT game_key, kind, stated_prob_c, reasoning_json "
            "FROM decisions WHERE mentality='early'"):
        f = None
        d = json.loads(r["reasoning_json"] or "{}")
        if r["kind"] == "entry":
            f = r["stated_prob_c"]
            if f is None:
                f = (d.get("reasoning") or {}).get("fair_home_c")
        else:
            f = (d.get("detail") or d).get("fair_home_c")
        if f is None:
            continue
        v = abs(float(f) - 50.0)
        out[r["game_key"]] = max(out.get(r["game_key"], 0.0), v)
    return out


def buckets(con):
    pos = {}
    for r in con.execute(
            "SELECT bot, game_key, ticker, opened_utc, pnl_c, entry_price_c, "
            "contracts, entry_fee_c FROM positions WHERE bot IN "
            "('starter__hold','early__hold') AND status IN "
            "('settled','closed')"):
        pos.setdefault(r["game_key"], {})[r["bot"].split("__")[0]] = dict(r)
    out = {}
    for g, d in pos.items():
        s = d.get("starter")
        if not s:
            continue
        e = d.get("early")
        if e is None or e["opened_utc"] > s["opened_utc"]:
            out[g] = ("alone", s)
        elif e["ticker"] == s["ticker"]:
            out[g] = ("agreed", s)
        else:
            out[g] = ("opposite", s)
    return out


def sm(v):
    if not v:
        return 0, None, 0.0
    p = sum((x["pnl_c"] or 0) / 100 for x in v)
    st = sum(x["contracts"] * x["entry_price_c"] / 100
             + (x["entry_fee_c"] or 0) / 100 for x in v)
    return len(v), (100 * p / st if st else 0.0), p


if __name__ == "__main__":
    con = E.connect()
    conv = conviction(con)
    b = buckets(con)
    have = [g for g in b if g in conv]
    print(f"settled games classified: {len(b)}")
    print(f"of those with a recorded `early` view: {len(have)}")
    print(f"missing a view (cannot be cut either way): {len(b) - len(have)}")
    if have:
        print(f"median conviction: {statistics.median(conv[g] for g in have):.1f}c "
              f"from an even game\n")

    for cut in CUTS:
        keep = collections.defaultdict(list)
        drop = collections.defaultdict(list)
        for g in have:
            k, s = b[g]
            (keep if conv[g] > cut else drop)[k].append(s)
        nk = sum(len(v) for v in keep.values())
        nd = sum(len(v) for v in drop.values())
        print(f"===== cut at {cut}c  --  KEPT {nk} games, DROPPED {nd} =====")
        print(f"  {'bucket':<10}{'KEPT (early had a view)':>28}"
              f"{'DROPPED (coin flip)':>26}")
        for k in ("agreed", "opposite", "alone"):
            n1, r1, _ = sm(keep[k])
            n2, r2, _ = sm(drop[k])
            a = f"{r1:+.1f}% ({n1}g)" if n1 else "0 games"
            c = f"{r2:+.1f}% ({n2}g)" if n2 else "0 games"
            print(f"  {k:<10}{a:>28}{c:>26}")
        print()
    con.close()
