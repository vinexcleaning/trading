"""analyse.py — the pre-registered gates, computed from the logs.

Run it whenever. It reads only what is on disk and changes nothing.

    .venv\\Scripts\\python.exe -m src.analyse

EVERYTHING HERE WAS FIXED IN PREREGISTRATION.md BEFORE THE RUN
    The gates, the clustering unit, the three-valued verdict, and the
    prediction that the P&L endpoint is UNTESTABLE at fifty matches.

    THE ONE EXCEPTION IS THE BH DENOMINATOR, WHICH ROSE 16 -> 32 AFTER THE RUN
    STARTED AND BEFORE ANY RESULT EXISTED. See N_HYPOTHESES below,
    ../JOINT_MULTIPLICITY.md, and PREREGISTRATION.md amendment A3. A denominator
    that RISES is the only direction a correction may move after the fact; one
    that falls is how a search gets reported as smaller than it was. This module computes them; it does not choose
    them. If a number here looks interesting and is not in the pre-registration,
    it is an observation, and it is labelled EXPLORATORY.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"

BH_Q = 0.10
# THE DENOMINATOR IS 32, NOT 16, AND IT IS JOINT WITH mlb-paper.
#
# PREREGISTRATION.md §6 declared 16 over this test's own bots. Read alone that
# is right. A second sixteen-bot forward test (`mlb-paper/`) is running on the
# same exchange, in the same repo, in the same fortnight, and the two will be
# read side by side by one person - which makes them ONE family. Correcting each
# inside itself and then comparing is a 32-way search reported as two 16-way
# searches.
#
# The joint declaration is ../JOINT_MULTIPLICITY.md, written by the MLB session
# before either test had a settled result. This session has checked its
# arithmetic and AGREES; see PREREGISTRATION.md amendment A3.
#
# What it costs here: the MDE widens 6.2% at every n (22.76c -> 24.16c at n=50),
# and resolving a 3.6c edge goes from ~1,998 to ~2,252 settled matches per bot.
#
# It never falls. If either test adds a bot it rises, and every previously
# reported p-value is recomputed at the new value.
N_HYPOTHESES = 32
N_OWN_BOTS = 16            # this test's own bots, for reporting only
SD_PRIOR_CENTS = 45.0      # set1_overshoot, 3,436 events
BOOTSTRAP = 20_000
SEED = 20260806


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _jsonl(path: Path) -> list[dict]:
    """Read a log AND every rotated generation of it, oldest first.

    Rotation exists so the runner cannot fill the laptop. If the analysis read
    only the live file it would silently analyse the tail of the run and report
    it as the whole thing - a smaller, quieter version of exactly the mistake
    this repo has made most often.
    """
    parts = sorted(path.parent.glob(path.name + ".*"),
                   key=lambda p: p.suffix, reverse=True)
    out: list[dict] = []
    for p in [*parts, path]:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------

def cluster_bootstrap(values_by_match: dict[str, list[float]],
                      weights_by_match: dict[str, list[float]] | None = None,
                      n: int = BOOTSTRAP) -> tuple[float, float, float, int]:
    """Resample MATCHES, not rows. GUARDS #8.

    A match settles once. Two mirrored markets, five ticks of the same
    position, or ten fills inside one event are one observation, not ten.
    Returns (point, lo, hi, n_matches).
    """
    keys = sorted(values_by_match)
    if not keys:
        return (float("nan"), float("nan"), float("nan"), 0)

    def stat(ks: list[str]) -> float:
        num = den = 0.0
        for k in ks:
            vs = values_by_match[k]
            ws = (weights_by_match or {}).get(k, [1.0] * len(vs))
            for v, w in zip(vs, ws):
                num += v * w
                den += w
        return num / den if den else float("nan")

    point = stat(keys)
    rng = np.random.default_rng(SEED)
    idx = np.arange(len(keys))
    draws = np.empty(n)
    for i in range(n):
        pick = [keys[j] for j in rng.choice(idx, len(keys), replace=True)]
        draws[i] = stat(pick)
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    return (point, float(lo), float(hi), len(keys))


def p_from_bootstrap(lo: float, hi: float, point: float) -> float:
    """Two-sided p implied by a symmetric normal with this interval.

    Two-sided on purpose: a loss is a finding here, and a one-sided test would
    hide it. GUARDS #11.
    """
    if any(math.isnan(x) for x in (lo, hi, point)):
        return float("nan")
    se = (hi - lo) / 3.9199
    if se <= 0:
        return float("nan")
    z = abs(point) / se
    return math.erfc(z / math.sqrt(2))


def benjamini_hochberg(pvals: dict[str, float], q: float = BH_Q,
                       m: int | None = None) -> dict[str, bool]:
    """One denominator over every hypothesis, including the ones with no data.

    `m` defaults to N_HYPOTHESES rather than to len(pvals), so a bot that never
    traded cannot quietly shrink the denominator. crypto's CANCELLED convention.
    """
    m = m or N_HYPOTHESES
    items = sorted(((k, v) for k, v in pvals.items() if not math.isnan(v)),
                   key=lambda kv: kv[1])
    passed: dict[str, bool] = {k: False for k in pvals}
    kmax = 0
    for i, (_k, p) in enumerate(items, start=1):
        if p <= (i / m) * q:
            kmax = i
    for k, _p in items[:kmax]:
        passed[k] = True
    return passed


def mde_cents(n_matches: int, alpha: float) -> float:
    """Minimum detectable effect at 80% power. Reported beside every null."""
    if n_matches < 2:
        return float("inf")
    from scipy.stats import norm
    return float((norm.ppf(1 - alpha / 2) + norm.ppf(0.80))
                 * SD_PRIOR_CENTS / math.sqrt(n_matches))


def verdict(point: float, lo: float, hi: float, cost_bar: float,
            bh_pass: bool) -> str:
    """Three values, always. GUARDS #21 - 'I could not tell' is a verdict."""
    if math.isnan(point):
        return "CANCELLED (no settled trades)"
    if bh_pass and lo > 0 and point > cost_bar:
        return "SURVIVES"
    if lo <= 0 <= hi:
        return "UNDERPOWERED"
    if lo > 0 or hi < 0:
        return ("UNDERPOWERED (interval excludes zero but does not survive BH "
                f"across the joint {N_HYPOTHESES})")
    return "COLLAPSES"


# --------------------------------------------------------------------------
# The gates
# --------------------------------------------------------------------------

@dataclass
class Analysis:
    state: dict
    delibs: list[dict]
    health: list[dict]
    briefs: dict[str, dict]

    # -- T1 ----------------------------------------------------------------
    def t1_machinery(self) -> dict:
        if not self.health:
            return {"status": "no health log"}
        secs = [h["secs"] for h in self.health]
        alerts = Counter(a.split(" - ")[0][:60]
                         for h in self.health for a in h.get("alerts", []))
        ticks = [h["tick"] for h in self.health]
        gaps = sum(1 for a, b in zip(ticks, ticks[1:]) if b != a + 1)
        return {
            "ticks_recorded": len(self.health),
            "tick_numbers_span": f"{min(ticks)}..{max(ticks)}",
            "non_contiguous_tick_jumps": gaps,
            "tick_seconds_median": round(float(np.median(secs)), 1),
            "tick_seconds_p95": round(float(np.percentile(secs, 95)), 1),
            "alerts": dict(alerts),
            "result_leak_filtered_total": sum(h.get("result_leak_filtered", 0)
                                              for h in self.health),
        }

    # -- T2 ----------------------------------------------------------------
    def t2_coverage(self) -> dict:
        by_tier: dict[str, Counter] = defaultdict(Counter)
        for b in self.briefs.values():
            t = b.get("tier", "?")
            c = b.get("coverage", {})
            by_tier[t]["matches"] += 1
            by_tier[t]["both_players"] += int(bool(c.get("player_a_resolved"))
                                              and bool(c.get("player_b_resolved")))
            by_tier[t]["surface"] += int(bool(c.get("surface_known")))
            by_tier[t]["round"] += int(bool(c.get("round_known")))
            by_tier[t]["h2h"] += int((c.get("h2h_n") or 0) > 0)
            by_tier[t]["charting_both"] += int((c.get("charting_a") or 0) > 0
                                               and (c.get("charting_b") or 0) > 0)
        out = {}
        for t, c in sorted(by_tier.items()):
            m = c["matches"]
            out[t] = {"matches": m, **{
                k: f"{100*c[k]/m:.1f}%" for k in
                ("both_players", "surface", "round", "h2h", "charting_both")}}
        staleness = [b.get("staleness_days") for b in self.briefs.values()
                     if b.get("staleness_days") is not None]
        out["_archive_staleness_days"] = (int(np.median(staleness))
                                          if staleness else None)
        return out

    # -- T3 ----------------------------------------------------------------
    def t3_execution_cost(self) -> dict:
        """What it actually cost to get in and out, per contract."""
        rows: list[float] = []
        slip: list[float] = []
        spreads: list[float] = []
        fees: list[float] = []
        by_match: dict[str, list[float]] = defaultdict(list)
        for bot, lg in (self.state.get("engine", {}).get("ledgers") or {}).items():
            for f in lg.get("fills", []):
                if f["kind"] == "entry":
                    per = f["fee_cents"] / max(1, f["qty"])
                    fees.append(per)
                    if f.get("slippage_cents") is not None:
                        slip.append(float(f["slippage_cents"]))
            for p in lg.get("positions", []):
                if p.get("pnl_cents") is None:
                    continue
                q = max(1, p["qty"])
                cost = (p["entry_fee_cents"] + p.get("exit_fee_cents", 0.0)) / q
                rows.append(cost)
                by_match[p["event_ticker"]].append(cost)
        if not rows:
            return {"status": "no closed positions yet"}
        pt, lo, hi, nm = cluster_bootstrap(by_match)
        return {
            "round_trip_fee_per_contract_cents": round(float(np.mean(rows)), 3),
            "clustered_ci95": [round(lo, 3), round(hi, 3)],
            "n_matches": nm,
            "entry_fee_per_contract_median": round(float(np.median(fees)), 3) if fees else None,
            "slippage_decision_to_fill_mean_cents": round(float(np.mean(slip)), 3) if slip else None,
            "slippage_n": len(slip),
            "note": ("slippage is the cost of filling on the NEXT tick's book rather "
                     "than the one that triggered the decision"),
        }

    # -- T4 ----------------------------------------------------------------
    def t4_divergence(self) -> dict:
        entered: dict[str, set] = defaultdict(set)
        for d in self.delibs:
            if d["action"] in ("enter", "reenter"):
                entered[d["mentality"]].add(d["event_ticker"])
        ms = sorted(entered)
        pairs = {}
        vals = []
        for i, a in enumerate(ms):
            for b in ms[i + 1:]:
                u = entered[a] | entered[b]
                j = (len(entered[a] & entered[b]) / len(u)) if u else float("nan")
                pairs[f"{a} vs {b}"] = round(j, 3)
                if not math.isnan(j):
                    vals.append(j)
        return {
            "entries_by_mentality": {m: len(entered[m]) for m in ms},
            "pairwise_jaccard": pairs,
            "median_pairwise_jaccard": round(float(np.median(vals)), 3) if vals else None,
            "reading": ("below 0.5 means genuinely different instruments; above 0.8 "
                        "means the labels are decoration and the sixteen-way "
                        "correction is measuring one thing sixteen times"),
        }

    # -- T5 + secondary ----------------------------------------------------
    def per_bot(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        ledgers = self.state.get("engine", {}).get("ledgers") or {}
        for bot, lg in sorted(ledgers.items()):
            pnl_by_match: dict[str, list[float]] = defaultdict(list)
            w_by_match: dict[str, list[float]] = defaultdict(list)
            stakes, percontract, prices, spreads = [], [], [], []
            voided = 0
            for p in lg.get("positions", []):
                if p.get("exit_kind") == "voided":
                    voided += 1
                    continue
                if p.get("pnl_cents") is None:
                    continue
                q = max(1, p["qty"])
                per = p["pnl_cents"] / q
                pnl_by_match[p["event_ticker"]].append(per)
                w_by_match[p["event_ticker"]].append(float(q))
                percontract.append(per)
                stakes.append(q * p["entry_price"])
                prices.append(p["entry_price"])
            if not percontract:
                out[bot] = {"n_matches": 0, "verdict": "CANCELLED (no settled trades)",
                            "voided": voided}
                continue
            pt, lo, hi, nm = cluster_bootstrap(pnl_by_match)
            wpt, wlo, whi, _ = cluster_bootstrap(pnl_by_match, w_by_match)
            p = p_from_bootstrap(lo, hi, pt)
            avg_price = float(np.mean(prices))
            from .engine import hold_cost_cents
            bar = hold_cost_cents(int(round(avg_price)), 2)
            r = float(np.corrcoef(stakes, percontract)[0, 1]) if len(stakes) > 3 else float("nan")
            out[bot] = {
                "n_matches": nm,
                "n_positions": len(percontract),
                "voided": voided,
                "mean_cents_per_contract": round(pt, 3),
                "ci95_clustered": [round(lo, 3), round(hi, 3)],
                "stake_weighted_cents_per_contract": round(wpt, 3),
                "sizing_term_cents": round(wpt - pt, 3),
                "corr_stake_vs_per_contract_pnl": (None if math.isnan(r) else round(r, 3)),
                "mean_entry_price_cents": round(avg_price, 1),
                "own_cost_bar_cents": round(bar, 3),
                "p_two_sided": (None if math.isnan(p) else round(p, 5)),
                "mde_at_this_n_alpha05": round(mde_cents(nm, 0.05), 2),
                "mde_at_this_n_bh_joint32": round(mde_cents(nm, BH_Q / N_HYPOTHESES), 2),
                "mde_if_corrected_alone_bh16": round(mde_cents(nm, BH_Q / N_OWN_BOTS), 2),
                "put_5_dollars_in": round(5.0 * (1 + pt / max(1.0, avg_price)), 2),
            }
        # one BH denominator across all sixteen
        pv = {b: (v.get("p_two_sided") if v.get("p_two_sided") is not None else float("nan"))
              for b, v in out.items()}
        passed = benjamini_hochberg(pv, BH_Q, N_HYPOTHESES)
        for b, v in out.items():
            if v["n_matches"] == 0:
                continue
            v["bh_pass_q10_of_joint32"] = bool(passed.get(b))
            v["verdict"] = verdict(v["mean_cents_per_contract"],
                                   v["ci95_clustered"][0], v["ci95_clustered"][1],
                                   v["own_cost_bar_cents"], bool(passed.get(b)))
        return out

    def t5_execution_gap(self, per_bot: dict[str, dict]) -> dict:
        """The control is FAKE BY CONSTRUCTION. That is what makes it useful."""
        intents = self.state.get("control_intents") or []
        settled = self.state.get("settled_events") or {}
        pnl_by_match: dict[str, list[float]] = defaultdict(list)
        for i in intents:
            et = i["event_ticker"]
            if et not in settled:
                continue
            won = settled[et] == i["ticker"]
            mid = i.get("intended_mid")
            if mid is None:
                continue
            pnl_by_match[et].append((100.0 if won else 0.0) - float(mid))
        if not pnl_by_match:
            return {"status": "no settled control intents yet"}
        pt, lo, hi, nm = cluster_bootstrap(pnl_by_match)
        gaps = {}
        for b, v in per_bot.items():
            if b.startswith("control") or v.get("n_matches", 0) == 0:
                continue
            gaps[b] = round(pt - v["mean_cents_per_contract"], 3)
        return {
            "control_cents_per_contract_AT_THE_MID_ZERO_FEES": round(pt, 3),
            "ci95_clustered": [round(lo, 3), round(hi, 3)],
            "n_matches": nm,
            "gap_to_each_bot_cents": gaps,
            "WARNING": ("this control buys at a price that does not exist and pays no "
                        "fee. It is FAKE BY CONSTRUCTION and is not a strategy. The gap "
                        "is the measurement; the level is not."),
        }

    def naive_benchmark(self) -> dict:
        """Buy the favourite side of every settled match and hold. GUARDS: report
        the naive benchmark next to every result."""
        settled = self.state.get("settled_events") or {}
        rows: dict[str, list[float]] = defaultdict(list)
        for et, winner in settled.items():
            b = self.briefs.get(et)
            if not b or winner is None:
                continue
            m = b.get("market") or {}
            ask, mirror = m.get("yes_ask"), m.get("mirror_yes_ask")
            if ask is None or mirror is None:
                continue
            fav_is_primary = ask >= mirror
            fav_ask = ask if fav_is_primary else mirror
            fav_ticker = m.get("ticker") if fav_is_primary else None
            won = (winner == fav_ticker) if fav_is_primary else (winner != m.get("ticker"))
            from .engine import hold_cost_cents
            fee = hold_cost_cents(fav_ask, 0)
            rows[et].append((100.0 if won else 0.0) - fav_ask - fee)
        if not rows:
            return {"status": "not enough settled matches yet"}
        pt, lo, hi, nm = cluster_bootstrap(rows)
        return {"buy_the_favourite_and_hold_cents_per_contract": round(pt, 3),
                "ci95_clustered": [round(lo, 3), round(hi, 3)], "n_matches": nm,
                "note": "priced at the ask observed when the brief was built, entry fee only"}

    def spread_split(self) -> dict:
        """EXPLORATORY but pre-registered as a check, not a hunt.

        The heavy-favourite 'edge' in the archive was +1.18c where the quote was
        tight and +7.92c where it was over 8c wide. An edge that grows with the
        spread IS the spread.
        """
        buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for lg in (self.state.get("engine", {}).get("ledgers") or {}).values():
            for p in lg.get("positions", []):
                if p.get("pnl_cents") is None:
                    continue
                b = self.briefs.get(p["event_ticker"])
                sp = ((b or {}).get("market") or {}).get("spread")
                if sp is None:
                    continue
                key = "<=2c" if sp <= 2 else ("3-4c" if sp <= 4 else
                                              ("5-8c" if sp <= 8 else ">8c"))
                buckets[key][p["event_ticker"]].append(p["pnl_cents"] / max(1, p["qty"]))
        out = {}
        for k in ("<=2c", "3-4c", "5-8c", ">8c"):
            if k in buckets:
                pt, lo, hi, nm = cluster_bootstrap(buckets[k])
                out[k] = {"cents_per_contract": round(pt, 3),
                          "ci95": [round(lo, 3), round(hi, 3)], "n_matches": nm,
                          "mde_alpha05": round(mde_cents(nm, 0.05), 2)}
        out["reading"] = ("if the number grows as the spread widens, it is the spread "
                          "and not an edge - it gets bigger exactly where you cannot "
                          "trade it")
        return out


def load() -> Analysis:
    state = _load(DATA / "state.json") or {}
    briefs = {}
    bd = DATA / "briefs"
    if bd.exists():
        for p in bd.glob("*.json"):
            try:
                briefs[p.stem] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
    return Analysis(state=state, delibs=_jsonl(LOGS / "reasoning.jsonl"),
                    health=_jsonl(LOGS / "health.jsonl"), briefs=briefs)


def main() -> int:
    a = load()
    per_bot = a.per_bot()
    settled = len(a.state.get("settled_events") or {})
    report = {
        "generated": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "settled_matches": settled,
        "target": 50,
        "PREREGISTERED_WARNING": (
            f"At {settled} settled matches the minimum detectable effect under BH "
            f"across the JOINT denominator of {N_HYPOTHESES} (this test's 16 bots plus "
            f"mlb-paper's 16 - see ../JOINT_MULTIPLICITY.md) is "
            f"{mde_cents(max(2, settled), BH_Q/N_HYPOTHESES):.1f}c against a cost bar of "
            f"about 3.6c. The P&L endpoint was pre-registered as UNTESTABLE at this "
            f"sample size and it still is. About 2,252 settled matches PER BOT would be "
            f"needed to resolve an edge the size of the cost bar."),
        "REPORTING_RULE": (
            "JOINT_MULTIPLICITY.md rule 2: the two forward tests are reported TOGETHER "
            "or neither is reported. A tennis result published alone under a 16-way "
            "correction would be published at the wrong bar."),
        "T1_machinery": a.t1_machinery(),
        "T2_brief_coverage": a.t2_coverage(),
        "T3_execution_cost": a.t3_execution_cost(),
        "T4_divergence": a.t4_divergence(),
        "T5_execution_gap": a.t5_execution_gap(per_bot),
        "naive_benchmark": a.naive_benchmark(),
        "per_bot": per_bot,
        "spread_split_EXPLORATORY": a.spread_split(),
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "results.json").write_text(json.dumps(report, indent=1, default=str),
                                          encoding="utf-8")
    print(json.dumps(report, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
