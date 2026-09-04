"""The other guards, as tests: no mid-fill, no fee copy, the settlement
strike, the martingale refusal, and the mismatched-pair placebo.

Each of these corresponds to a defect this repo has already paid for, and the
test exists so the defect cannot come back quietly.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT.parent))

import engine as E          # noqa: E402
import mentalities as MEN   # noqa: E402


# ------------------------------------------------------ GUARD 7: never the mid

def test_no_fill_path_reads_the_mid():
    """A tennis result of +14.4% to +24.6% became -24.3% to -30.9% when fills
    stopped happening at the mid. `_exec_price` is the only function in the
    engine that produces a fill price and it must touch bid and ask only."""
    src = (SRC / "engine.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_exec_price")
    # Strip the docstring before scanning. Its whole job is to SAY there is no
    # mid here, so a naive substring check flags the warning label itself --
    # which is what the first version of this test did.
    body = list(fn.body)
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    code = "\n".join(ast.get_source_segment(src, n) or "" for n in body)
    assert "mid" not in code, f"_exec_price computes a mid:\n{code}"
    ids = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
    consts = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant)
              and isinstance(n.value, str)}
    assert "mid" not in ids | attrs
    assert not any("mid" in c for c in consts if len(c) < 40)


def test_exec_price_is_the_far_side():
    row = {"bid": 44, "ask": 47, "bid_size": 100.0, "ask_size": 200.0}
    assert E._exec_price(row, "YES", "open") == (47, 200.0)     # pay the ask
    assert E._exec_price(row, "YES", "close") == (44, 100.0)    # hit the bid
    assert E._exec_price(row, "NO", "open") == (56, 100.0)      # 100 - bid
    assert E._exec_price(row, "NO", "close") == (53, 200.0)     # 100 - ask
    # the mid, 45.5, appears nowhere in any of those
    for r in (E._exec_price(row, s, a) for s in ("YES", "NO")
              for a in ("open", "close")):
        assert r[0] != 45 and r[0] != 46


# --------------------------------------------- GUARD 6: one fee implementation

def test_fees_are_not_reimplemented_here():
    """common/tests/test_no_fee_reimplementation.py enforces this repo-wide;
    this asserts it locally so mlb-paper fails on its own too. The formula went
    from 3 copies to 17 while the rule was only a convention."""
    for p in SRC.rglob("*.py"):
        t = p.read_text(encoding="utf-8", errors="replace")
        if "0.07" in t and "kalshi_fees" not in t:
            raise AssertionError(f"{p.name} looks like a fee copy")


def test_fee_comes_from_the_shared_module():
    from common.kalshi_fees import fee_order_cents
    # the quadratic peaks at 50c; 7% * 0.5 * 0.5 * 100 = 1.75c, rounded up
    assert float(fee_order_cents(50, 1)) == 2.0
    assert float(fee_order_cents(50, 100)) == 175.0


# ------------------------------- settlement: the strike is not the rung index

def test_totals_strike_is_never_read_from_the_suffix():
    """'KXMLBTOTAL-26AUG072145TBSEA-9' is the NINTH RUNG and its strike is 8.5.

    Reading the suffix as the strike settles every totals position exactly half
    a run high, which is one full tick of the ladder and would invert every
    close call. The strike is captured from the live market object while the
    market is still open, because Kalshi's window is ~69 days and closed
    markets 404 for good.
    """
    E.load_strikes([{"ticker": "KXMLBTOTAL-26AUG072145TBSEA-9",
                     "floor_strike": 8.5}])
    assert E._strike_for("KXMLBTOTAL-26AUG072145TBSEA-9") == 8.5
    assert E._strike_for("KXMLBTOTAL-26AUG072145TBSEA-77") is None


def test_settlement_directions():
    pos_yes = {"ticker": "KXMLBGAME-26AUG072145TBSEA-SEA", "side": "YES"}
    pos_no = dict(pos_yes, side="NO")
    home_win = {"away_runs": 2, "home_runs": 5, "total_runs": 7}
    away_win = {"away_runs": 6, "home_runs": 1, "total_runs": 7}
    # SEA is the HOME club in 'TBSEA' (Kalshi lists away first)
    assert E.settle_value_c(pos_yes, home_win) == 100
    assert E.settle_value_c(pos_yes, away_win) == 0
    assert E.settle_value_c(pos_no, home_win) == 0

    E.load_strikes([{"ticker": "KXMLBTOTAL-26AUG072145TBSEA-9",
                     "floor_strike": 8.5}])
    t = {"ticker": "KXMLBTOTAL-26AUG072145TBSEA-9", "side": "YES"}
    assert E.settle_value_c(t, {"away_runs": 5, "home_runs": 5,
                                "total_runs": 10}) == 100      # 10 > 8.5
    assert E.settle_value_c(t, {"away_runs": 4, "home_runs": 4,
                                "total_runs": 8}) == 0         # 8 < 8.5


# ------------------------------------------- the martingale refusal, by number

def test_reentry_never_larger_than_the_first_entry():
    """The exact sequence that cost -$7.56 on one tennis match in 50 minutes:
    a fixed DOLLAR stake buys more contracts as the price falls, so 12 -> 20 ->
    32. Nobody designed it. Every individual size was arithmetically correct."""
    assert E.contracts_for(6.25, 49, 1e9) == 12
    assert E.contracts_for(6.25, 31, 1e9) == 20
    assert E.contracts_for(6.25, 19, 1e9) == 25    # MAX_CONTRACTS caps it at 25
    # and the re-entry cap is what actually refuses it
    con = E.connect(":memory:")
    con.execute(
        "INSERT INTO positions (id, bot, game_key, ticker, side, contracts, "
        "entry_price_c, entry_fee_c, opened_utc, exit_mode, status, "
        "decision_id) VALUES ('p1','x__free','g','t','YES',12,49,2.0,"
        "'2026-01-01T00:00:00+00:00','free','closed','d')")
    assert E.reentry_size_cap(con, "x__free", "g") == 12
    con.close()


def test_depth_cap_never_consumes_size_the_book_did_not_show():
    assert E.contracts_for(100.0, 50, book_size=8) == 2      # 25% of 8
    assert E.contracts_for(100.0, 50, book_size=0) == 0


# ------------------------------------------------------- bots and denominator

def test_twenty_one_bots_exactly():
    """The fleet size is pinned so it cannot drift without a decision.

    Was 16 until 2026-09-03. FOUR entry strategies were added to the slots
    freed when ten of the original sixteen turned out to be bit-identical
    duplicates -- the exit dimension fired 3 times in 1,516 positions.

    Eleven candidates were screened, five earned a slot, and a fifth
    (`rested`) was dropped in the dry run when it turned out it could never
    fire: it needs a rest-day gap of 2+, which has never occurred in 2,125
    games. See the note above MENTALITIES.update in mentalities.py.

    THE DENOMINATOR RISES AND DOES NOT FALL. JOINT_MULTIPLICITY.md counts one
    denominator across this fleet and tennis's, so the repo goes 16 + 16 = 32
    -> 21 + 16 = 37, and every previously reported number is recomputed
    against 37. That cost lands on the tennis fleet too.

    This test failing is the correct behaviour when someone adds a bot without
    updating PREREGISTRATION_FLEET2.md. Do not simply raise the number.
    """
    assert len(MEN.BOT_IDS) == 21
    assert MEN.BOT_IDS.count("control__no-trade") == 1
    assert len(set(MEN.BOT_IDS)) == 21


def test_the_five_new_strategies_are_hold_only():
    """Adding the exit triple to the new five would buy ten more duplicates.

    The exit dimension produced zero information across 1,516 positions
    (3 fires). Every strategy added in 2026-09 is hold-only, and this pins it.
    """
    for m in MEN.HOLD_ONLY:
        assert f"{m}__hold" in MEN.BOT_IDS
        assert f"{m}__exit-once" not in MEN.BOT_IDS
        assert f"{m}__free" not in MEN.BOT_IDS


def test_every_mentality_has_a_declared_target_and_windows():
    """Every strategy declares a market, and the runner actually fetches it.

    This checked against a hardcoded ("KXMLBGAME", "KXMLBTOTAL") until
    2026-09-04. That was a SECOND copy of the runner's own SERIES list, and it
    failed the moment `bullpen-f5` needed KXMLBF5TOTAL -- correctly, but for
    the wrong reason: the risk it should be guarding is a strategy pointed at a
    market the runner never reads, which would decline every game forever. That
    is the `lineup` and `rested` failure, twice already.

    So it now compares against `run.SERIES` itself. One list, not two.
    """
    import run as RUN
    for m in MEN.MENTALITIES:
        assert m in MEN.TARGET, f"{m} declares no target market"
        assert MEN.TARGET[m] in RUN.SERIES, (
            f"{m} targets {MEN.TARGET[m]}, which run.py never fetches -- "
            f"it would decline every game forever")
        assert MEN.WINDOWS_FOR[m], f"{m} declares no windows"


def test_windows_do_not_overlap_ambiguously():
    for h in [x / 4 for x in range(0, 4 * 60)]:
        w = MEN.window_for(h)
        if w is None:
            continue
        assert abs(h - MEN.WINDOW_HOURS[w]) <= MEN.WINDOW_TOL_H[w]


# ---------------------------------------------- missing stays missing, always

def test_a_mentality_declines_rather_than_defaulting():
    """soccer/'s feature builder defaulted missing features to 0.0. That is a
    recorded defect here. Every mentality must decline on a missing input."""
    empty = {"away_team": "A", "home_team": "B", "starters":
             {"away": {"announced": False}, "home": {"announced": False}},
             "market": {"kalshi": {}}, "park": {}, "weather": {},
             "form": {}, "bullpen": None, "lineup": {},
             "venue": {}, "hours_to_first_pitch": 6.0}
    for name, fn in MEN.MENTALITIES.items():
        for w in MEN.WINDOWS_FOR[name]:
            r = fn(empty, w)
            assert isinstance(r, MEN.Decline), \
                f"{name} produced an Intent from an empty brief"
            assert r.reason
