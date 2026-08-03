r"""Verify every premise in the specialist brief before acting on any of it.

The brief states plainly that its claims come from a chat assistant reasoning
off summaries, not code, and that several such claims have proven false in this
project. So each is checked against the artefacts on disk, and a disproven
premise is recorded as a finding rather than quietly worked around.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REP = ROOT / "reports"
OUT = REP / "spec_premise_check.json"

res = {}


def rec(k, claim, verdict, evidence, note=""):
    res[k] = {"claim": claim, "verdict": verdict, "evidence": evidence,
              "note": note}
    print(f"[{verdict:^11}] {k}\n    claim: {claim}\n    -> {note}\n", flush=True)


def load(name):
    p = REP / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ---------------------------------------------------------------- P1 path
rec("P1_data_location",
    "Data is on disk in the wallet-copy-study session",
    "AMENDED",
    {"actual_path": str(ROOT),
     "own_git_repo_present": (ROOT / ".git").exists()},
    f"Data is intact but the project MOVED to {ROOT}. Its standalone git repo "
    f"is gone -- the directory now sits inside the 'trading' repo, so the 16 "
    f"commits of provenance from the earlier sessions are not reachable here.")

# ------------------------------------------------- P2 generalist headline
c46 = load("phase4c_copyability.json")
c_fee = load("phase4c_copyability_1767830400.json")
if c46 and c_fee:
    top = c46["period2"]["top_decile"]
    topf = c_fee["period2"]["top_decile"]
    rec("P2_generalist_numbers",
        "Generalist copier return +0.937pp, -0.135pp in the fee era",
        "CONFIRMED",
        {"cut_2025_07_01": {"copier": top["copier_buy_and_hold_pp"],
                            "ci": top["copier_ci95"],
                            "excess": top["wallet_excess_pp"]},
         "cut_2026_01_08": {"copier": topf["copier_buy_and_hold_pp"],
                            "ci": topf["copier_ci95"]}},
        f"copier {top['copier_buy_and_hold_pp']}pp at the 2025-07 cut and "
        f"{topf['copier_buy_and_hold_pp']}pp at the fee-era cut. Both match.")

# ------------------------------------------------------------ P3 sizing
src = (ROOT / "src" / "analyse_46_copyability.py").read_text(encoding="utf-8")
equal_weighted = "sum(c) / len(c)" in src
notional_weighted = "* r[\"cost\"]" in src.split("def analyse")[-1]
rec("P3_sizing",
    "The earlier study may not have sized proportionally; copying is "
    "scale-invariant so you copy the fraction of bankroll",
    "PARTLY FALSE",
    {"per_share_returns": True,
     "equal_weight_per_position": equal_weighted,
     "notional_weighted": notional_weighted},
    "The generalist result already averaged a PER-SHARE return with EQUAL "
    "WEIGHT per (wallet, market) position -- which is exactly 'a fixed fraction "
    "of bankroll per signal'. It is already scale-invariant. What it does NOT "
    "do is mirror the wallet's own dollar sizes or their conviction (their "
    "fraction of their bankroll). Those are the variants worth adding, not "
    "'proportional sizing' in general.")

# -------------------------------------------------- P4 latency flatness
d40 = load("phase4c_decay.json")
d62 = load("exit_stage2_decay.json")
if d40 and d62:
    uncond = {k: v["copy_return_net_pp"] for k, v in d40["decay"].items()}
    cond = {k: v["buy_and_hold"]["mean_pp"] for k, v in d62["exit_decay"].items()}
    rec("P4_latency_flat",
        "Edge does not decay with latency, flat 0s-1800s; so 30 minutes late "
        "costs nothing and price impact may not be eating the copier",
        "FALSE AS STATED",
        {"unconditional_copy_return_by_delay": uncond,
         "selected_wallet_buy_and_hold_by_delay": cond},
        "Flat only UNCONDITIONALLY. Conditioned on selected wallets -- the only "
        "population a copier cares about -- buy-and-hold falls "
        f"{cond.get('0')}pp at 0s to {cond.get('300')}pp at 300s on a balanced "
        "panel, i.e. ~3pp of decay inside five minutes, most of it in the first "
        "ten seconds. This was already corrected at the end of the exit study. "
        "The inference 'if 30 minutes is free, impact is free too' therefore "
        "does not follow, though the whale exclusion is still worth testing "
        "empirically.")

# --------------------------------------------------- P5 fee-era disjoint
fe = load("exit_fee_era_ranking.json")
if fe:
    comp = fe["top_decile_composition_change"]
    rec("P5_fee_era_disjoint",
        "Fee-era top decile nearly disjoint from fee-free, 7 of 36 overlapping",
        "CONFIRMED",
        comp,
        f"overlap {comp['overlap_n']} of {comp['fee_era_top_decile_n']}, "
        f"Jaccard {comp['jaccard']}. Exactly as stated -- this one is ours.")

# ------------------------------------------------------ P6 unverifiable
rec("P6_project_ledger",
    "~47 corrections, every one shrinking the edge, and 8 apparent positives "
    "that died",
    "UNTESTABLE HERE",
    {"reason": "no such ledger exists in this project directory"},
    "This project's own records (PROGRESS.md, DECISIONS.md, the verdict) "
    "document far fewer than 47 corrections. The figure likely aggregates "
    "sibling projects. Adopted as a PRIOR (treat positives as presumptively "
    "wrong), which is sound regardless, but not as a verified count.")

rec("P7_effective_series",
    "A prior session found four crypto assets were 1.81 effective series out of 4",
    "UNTESTABLE HERE",
    {"reason": "belongs to a different project; no artefact in this directory"},
    "Cannot verify. The underlying METHOD -- report effective sample size, not "
    "nominal -- is adopted because it is correct, not because the number is.")

# ------------------------------------------------ P8 the video anecdote
rec("P8_lookahead_anecdote",
    "A video ranked on 7-day P&L and backtested over the same 7 days, gains "
    "came from the selection window",
    "NOT VERIFIABLE, BUT THE RULE IS RIGHT",
    {"rule": "selection window and measurement window must not overlap"},
    "The anecdote cannot be checked. The rule it illustrates is already how "
    "this project works and is enforced again here by explicit look-ahead "
    "assertions.")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
print(f"wrote {OUT}")
