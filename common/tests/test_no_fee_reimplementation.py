"""Repo-wide guard: nothing may reimplement the Kalshi fee formula.

GUARDS #6 records this bug appearing *independently in three codebases*. By
2026-08-03 there were **seventeen** copies of the formula across five projects,
nine of them carrying the float-dust bug, two of those in the live-money path.
Consolidating them was a one-off fix. This test is the part that lasts.

The rule: a Python file that looks like it computes a Kalshi fee must either

  (a) import the shared implementation (`common/kalshi_fees.py`), or
  (b) appear in ALLOWED below, with a reason.

The allowlist is the point. It is not a way to silence the check — it is a
place where somebody had to write down *why* a fee literal is sitting in a file
that does not use the shared module. A new entry should be rare and should feel
like it needs justifying.

    C:\\Users\\vinig\\trading\\kalshi-market-scan\\.venv\\Scripts\\python.exe -m pytest common/tests -q
"""
import os
import re

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules", "site-packages",
             "_archive", "data", "reports", ".pytest_cache", "build", "dist"}

#: Kalshi's taker rate and the maker rate that applies on the 130 series.
RATE = re.compile(r"(?<![\d.])0\.07(?![\d])|(?<![\d.])0\.0175(?![\d])")
#: the quadratic term, in either the dollars form (1-p) or the cents form (100-p)
QUAD = re.compile(r"\(\s*1(?:\.0+)?\s*-\s*\w+\s*\)|\(\s*100\s*-\s*\w+\s*\)")
CEIL = re.compile(r"\bceil\b")
#: any reference to the one true implementation
SHARED = re.compile(r"kalshi_fees|kalshi_research\.fees|costbar|"
                    r"from\s+fees\s+import|import\s+fees\b")

#: path -> why this file may carry a fee literal without importing the module.
ALLOWED = {
    # Polymarket work. 0.07 is the DOCUMENTED Polymarket rate, retained
    # specifically to prove it wrong: it matched 0.0% of 4,310 on-chain fills.
    # The real Polymarket fee is 0.10*min(p,1-p) (LEDGER C004 / W015).
    "crypto/src/poly_fee_resolve.py":
        "Polymarket formula bake-off; 0.07 is the documented form under test",
    "crypto/src/poly_fee_verify.py":
        "Polymarket verification; 0.07 is the documented form being refuted",
    "wallet-copy-study/src/accounting.py":
        "Polymarket accounting; 0.07 is the documented form, kept to contrast",
    "wallet-copy-study/tests/test_accounting.py":
        "asserts the documented Polymarket form does NOT match real fills",

    # Prose, not arithmetic.
    "crypto/src/streak_fade.py":
        "0.07 appears only in the module docstring, not in code",
    "kalshi-inplay-bot/backtest/generate_report.py":
        "0.07 appears only inside a markdown string in a generated report",

    # Another session's audit of fee CLAIMS. The literals are the data being
    # audited, not a calculation. See commit e3b87d7.
    "signal-github/src/fee_audit.py":
        "audits published fee claims; the rates are its subject matter",

    # The implementation and its own tests.
    "common/kalshi_fees.py":
        "IS the single implementation every other file must import",
    "common/tests/test_no_fee_reimplementation.py":
        "is this guard; the literals here are the detector's own patterns",
}


def _iter_py():
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".py"):
                p = os.path.join(dirpath, fn)
                yield p, os.path.relpath(p, REPO).replace("\\", "/")


def _looks_like_a_fee(src):
    return bool(RATE.search(src)) and bool(QUAD.search(src) or CEIL.search(src))


def test_no_file_reimplements_the_kalshi_fee():
    """Every fee-shaped file imports the shared module or is allowlisted."""
    offenders = []
    for path, rel in _iter_py():
        try:
            src = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if not _looks_like_a_fee(src):
            continue
        if rel in ALLOWED or SHARED.search(src):
            continue
        offenders.append(rel)

    assert not offenders, (
        "These files look like they compute a Kalshi fee but do not use "
        "common/kalshi_fees.py:\n  "
        + "\n  ".join(sorted(offenders))
        + "\n\nImport the shared module. This formula has been reimplemented "
          "17 times in this repo and 9 of those copies overcharged by a cent "
          "on ~6% of order sizes. If the literal genuinely is not a Kalshi "
          "fee (Polymarket work, prose, an audit of published rates), add it "
          "to ALLOWED with a reason."
    )


def test_allowlist_has_no_dead_entries():
    """An allowlisted file that no longer trips the check should be removed.

    Keeps the allowlist honest: entries expire when the reason does, so it
    cannot quietly grow into a blanket exemption.
    """
    dead = []
    for rel in ALLOWED:
        path = os.path.join(REPO, rel)
        if not os.path.exists(path):
            dead.append(f"{rel} (file no longer exists)")
            continue
        src = open(path, encoding="utf-8", errors="replace").read()
        if not _looks_like_a_fee(src):
            dead.append(f"{rel} (no longer contains a fee fingerprint)")
    assert not dead, (
        "Stale ALLOWED entries — delete them:\n  " + "\n  ".join(dead))


def test_every_allowlist_entry_states_a_reason():
    for rel, reason in ALLOWED.items():
        assert reason and len(reason) > 15, (
            f"{rel} needs a real reason, got {reason!r}")


def test_the_guard_actually_catches_a_reimplementation(tmp_path):
    """Prove the detector fires, so a passing run means something.

    Guard-rot protection (GUARDS #9): a check that cannot fail is not a check.
    """
    naive = (
        "import math\n"
        "def fee(contracts, price_cents):\n"
        "    p = price_cents / 100\n"
        "    return math.ceil(0.07 * contracts * p * (1 - p) * 100) / 100\n"
    )
    assert _looks_like_a_fee(naive), "the detector missed the canonical bug"

    # the cents form too
    cents = "RATE = 0.07\nf = RATE * p * (100 - p) / 100\n"
    assert _looks_like_a_fee(cents)

    # and it must not fire on unrelated code
    assert not _looks_like_a_fee("x = 0.07  # a correlation threshold\n")
    assert not _looks_like_a_fee("import math\nmath.ceil(1.5)\n")


def test_shared_module_is_importable_from_every_project_that_uses_it():
    """The sys.path shims must actually resolve, from any working directory.

    A broken shim fails at import time in the live bot, which is loud, but in
    an analysis script it might not surface until a long run is half done.
    """
    import subprocess
    import sys

    targets = [
        "kalshi-inplay-bot/tennis_engine.py",
        "kalshi-inplay-bot/backtest/engine.py",
        "set1_overshoot/src/fees.py",
        "common/costbar.py",
    ]
    for rel in targets:
        path = os.path.join(REPO, rel)
        if not os.path.exists(path):
            continue
        d, base = os.path.split(path)
        mod = base[:-3]
        # run from a neutral cwd to prove the shim is not cwd-dependent
        code = (f"import sys; sys.path.insert(0, {d!r}); "
                f"import {mod}; print('ok')")
        r = subprocess.run([sys.executable, "-c", code], cwd=REPO,
                           capture_output=True, text=True)
        if r.returncode != 0 and "ModuleNotFoundError" in r.stderr:
            missing = r.stderr.strip().splitlines()[-1]
            # a third-party dep the test env lacks is not our concern;
            # a missing kalshi_fees is.
            assert "kalshi_fees" not in missing, (
                f"{rel} cannot reach the shared fee module: {missing}")
