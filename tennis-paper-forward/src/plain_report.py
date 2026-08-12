"""plain_report.py — the weekly page, in money. No statistics words.

    .venv\\Scripts\\python.exe -m src.plain_report

Read-only. Answers four questions and nothing else:

  1. what each bot has actually done, in dollars, ranked
  2. how likely it is that the best of them looks good purely by luck
  3. how long an answer really takes, and whether fewer bots makes it sooner
  4. what kind of tennis the sample is made of, and whether that is changing

Everything here is paper. No money exists anywhere in this project.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

DATA = ROOT / "data"
LOGS = ROOT / "logs"

SD_CENTS = 45.0          # spread of one match's result, from the archive
COST_BAR = 4.79          # measured round trip on this pool: 2.67 fees + 2.12 spread
ENTRY_RATE = 0.40        # a bot bets on about 40% of matches
SEED = 20260811


def _z(p: float) -> float:
    from scipy.stats import norm
    return float(norm.ppf(p))


def matches_needed(n_bots: int, effect: float = COST_BAR) -> int:
    """How many bets ONE bot needs before an edge this size would show up.

    More bots being judged at once means a higher bar for any single one, so the
    same bot needs more bets. That is the whole reason the number is large.
    """
    q = 0.10
    alpha = 0.05 if n_bots == 1 else q / n_bots
    k = _z(1 - alpha / 2) + _z(0.80)
    return int(math.ceil((k * SD_CENTS / effect) ** 2))


def load():
    state = json.loads((DATA / "state.json").read_text(encoding="utf-8"))
    briefs = {}
    bd = DATA / "briefs"
    if bd.exists():
        for p in bd.glob("*.json"):
            try:
                briefs[p.stem] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
    return state, briefs


def per_bot(state) -> dict:
    out = {}
    for bot, lg in (state.get("engine", {}).get("ledgers") or {}).items():
        closed = [p for p in lg.get("positions", [])
                  if p.get("pnl_cents") is not None]
        if not closed:
            out[bot] = None
            continue
        staked = sum(p["qty"] * p["entry_price"] for p in closed)
        pnl = sum(p["pnl_cents"] for p in closed)
        won = sum(1 for p in closed if p["pnl_cents"] > 0)
        prices = [p["entry_price"] for p in closed]
        out[bot] = {
            "bets": len(closed),
            "won": won,
            "win_pct": 100.0 * won / len(closed),
            "avg_price": float(np.mean(prices)),
            "staked_dollars": staked / 100.0,
            "pnl_dollars": pnl / 100.0,
            "return_pct": 100.0 * pnl / staked if staked else 0.0,
            "prices": prices,
            "qtys": [p["qty"] for p in closed],
        }
    return out


def luck(bots: dict, n_sims: int = 20000) -> tuple[float, float, str]:
    """If every bot were guessing, how often would the BEST of them look this good?

    The null is the market's own price: a bet at 70c wins 70 times in 100. Each
    bot keeps its real bets, real sizes and real prices; only the outcome is
    redrawn. Then take the best bot, 20,000 times over.
    """
    live = {b: v for b, v in bots.items() if v and not b.startswith("control")}
    if not live:
        return (float("nan"), float("nan"), "")
    best_bot = max(live, key=lambda b: live[b]["return_pct"])
    observed = live[best_bot]["return_pct"]

    rng = np.random.default_rng(SEED)
    sims = np.zeros(n_sims)
    packs = []
    for v in live.values():
        pr = np.array(v["prices"], dtype=float)
        qt = np.array(v["qtys"], dtype=float)
        packs.append((pr, qt, float(np.sum(pr * qt))))
    for i in range(n_sims):
        best = -1e9
        for pr, qt, staked in packs:
            wins = rng.random(len(pr)) < (pr / 100.0)
            pnl = np.sum(np.where(wins, (100.0 - pr) * qt, -pr * qt))
            r = 100.0 * pnl / staked if staked else 0.0
            if r > best:
                best = r
        sims[i] = best
    p = float(np.mean(sims >= observed))
    return observed, p, best_bot


def sample_mix(state, briefs) -> dict:
    settled = state.get("settled_events") or {}
    tiers, surfaces = Counter(), Counter()
    for et in settled:
        b = briefs.get(et)
        if not b:
            continue
        tiers[b.get("tier", "?")] += 1
        surfaces[b.get("surface") or "unknown"] += 1
    return {"tiers": tiers, "surfaces": surfaces, "n": sum(tiers.values())}


def rate(state) -> float:
    """Settled matches per day, over time the runner was actually running."""
    h = []
    for p in sorted(LOGS.glob("health.jsonl*")) + [LOGS / "health.jsonl"]:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    h.append(json.loads(line))
                except Exception:
                    pass
    h = [x for x in h if x.get("settled_total") is not None]
    if len(h) < 3:
        return 0.0
    ts = [datetime.fromisoformat(x["ts"]) for x in h]
    run = sum((b - a).total_seconds() for a, b in zip(ts, ts[1:])
              if (b - a).total_seconds() <= 300)
    if run <= 0:
        return 0.0
    return (h[-1]["settled_total"] - h[0]["settled_total"]) / (run / 86400.0)


def main() -> int:
    state, briefs = load()
    bots = per_bot(state)
    settled = len(state.get("settled_events") or {})
    per_day = rate(state)

    print("=" * 78)
    print(" TENNIS PAPER TEST - WHERE IT ACTUALLY STANDS")
    print(" Every figure below is pretend money. Nothing here can place a real bet.")
    print("=" * 78)
    print(f"\n {settled} matches finished so far, arriving at about {per_day:.0f} a day.\n")

    live = {b: v for b, v in bots.items() if v and not b.startswith("control")}
    dead = [b for b, v in bots.items() if not v]

    print(" WHAT EACH BOT HAS DONE, BEST FIRST")
    print(" " + "-" * 76)
    print(f" {'bot':26s} {'bets':>5s} {'won':>5s} {'won%':>6s} {'avg buy':>8s} "
          f"{'staked':>9s} {'made/lost':>10s} {'return':>8s}")
    for b in sorted(live, key=lambda x: -live[x]["return_pct"]):
        v = live[b]
        print(f" {b:26s} {v['bets']:5d} {v['won']:5d} {v['win_pct']:5.1f}% "
              f"{v['avg_price']:7.0f}c ${v['staked_dollars']:8,.0f} "
              f"${v['pnl_dollars']:9,.2f} {v['return_pct']:+7.2f}%")
    if dead:
        print(f"\n NEVER TRADED: {', '.join(dead)}")
        print("   (the no-trade control never bets - that is its job)")

    tot_staked = sum(v["staked_dollars"] for v in live.values())
    tot_pnl = sum(v["pnl_dollars"] for v in live.values())
    print(f"\n ALL BOTS TOGETHER: staked ${tot_staked:,.0f}, "
          f"{'made' if tot_pnl>=0 else 'lost'} ${abs(tot_pnl):,.2f} "
          f"({100*tot_pnl/tot_staked:+.2f}%)")

    obs, p, best = luck(bots)
    if not math.isnan(p):
        print("\n IS THE BEST ONE REAL?")
        print(" " + "-" * 76)
        print(f" Best is {best} at {obs:+.2f}%.")
        print(f" If every bot were simply guessing at the market's own odds, the best")
        print(f" of them would look at least this good about {round(100*p)} times in 100.")
        if p > 0.10:
            print(" So this is what luck looks like. It is not a finding.")

    print("\n HOW LONG UNTIL AN ANSWER - AND FEWER BOTS IS THE ONLY REAL LEVER")
    print(" " + "-" * 76)
    print(f" To trust a bot, its winnings must clear the {COST_BAR:.2f}c it costs to")
    print(" get in and out of each bet. Judging many bots at once means each needs")
    print(" more bets before you can believe it.\n")
    print(f" {'bots judged':>12s} {'bets each needs':>16s} {'matches to watch':>18s} {'days from now':>15s}")
    for n_bots in (1, 3, 16, 32):
        need = matches_needed(n_bots)
        matches = int(math.ceil(need / ENTRY_RATE))
        days = (matches - settled) / per_day if per_day > 0 else float("inf")
        lab = {32: "32 (today)", 16: "16 (tennis only)"}.get(n_bots, str(n_bots))
        print(f" {lab:>12s} {need:>16,d} {matches:>18,d} "
              f"{('already there' if days<=0 else f'{days:,.0f}'):>15s}")
    print("\n 'bots judged' is how many are in the running at once. Today it is 32,")
    print(" because the baseball test's 16 are judged alongside these 16.")

    mix = sample_mix(state, briefs)
    print("\n WHAT KIND OF TENNIS THIS SAMPLE IS")
    print(" " + "-" * 76)
    for k, c in mix["tiers"].most_common():
        print(f"   {k:8s} {c:5d}  ({100*c/max(1,mix['n']):.0f}%)")
    print("   surfaces: " + ", ".join(f"{k} {v}" for k, v in mix["surfaces"].most_common()))
    print("\n   The tennis calendar moves on. A sample gathered over two months is")
    print("   NOT the same population as today's, and a bot judged across both is")
    print("   judged on two different games. This is a real threat to the test and")
    print("   it is the reason a shorter run is worth more than a longer one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
