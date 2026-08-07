"""The guard that makes 'paper only' a property of the code, not a promise.

GUARDS #9: a guard that silently stops working is worse than no guard, so the
last test in this file plants a violation and asserts the detector bites.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))

from src import safety  # noqa: E402
from src.safety import PaperOnlyViolation  # noqa: E402


# --------------------------------------------------------------------------
# 1. Source-level: no order-shaped code may exist anywhere in the package
# --------------------------------------------------------------------------

FORBIDDEN = [
    (r"portfolio/orders", "the Kalshi order endpoint"),
    (r"\bcreate_order\b", "an order constructor"),
    (r"\bplace_order\b", "an order constructor"),
    (r"\bcancel_order\b", "an order mutation"),
    (r"requests\.(post|put|patch|delete)\b", "a mutating HTTP verb"),
    (r"session\.(post|put|patch|delete)\b", "a mutating HTTP verb"),
    (r"\bsign_pss\b|\bPKCS1v15\b|\bload_pem_private_key\b", "request signing"),
    (r"KALSHI-ACCESS-SIGNATURE", "a Kalshi auth header"),
    (r"\bprivate_key\b", "a signing key"),
]

# Files allowed to MENTION a forbidden token, with a reason. The allowlist is
# the mechanism, not an escape hatch: a dead entry fails the test below, so it
# cannot quietly become a blanket exemption.
ALLOWED: dict[str, str] = {
    "safety.py": "defines the refusal list; the tokens appear inside the guard itself",
}


def _sources() -> list[Path]:
    return sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in str(p))


def test_no_order_shaped_code_in_the_package():
    hits: list[str] = []
    for p in _sources():
        text = p.read_text(encoding="utf-8", errors="replace")
        for pat, what in FORBIDDEN:
            if re.search(pat, text):
                if p.name in ALLOWED:
                    continue
                hits.append(f"{p.relative_to(ROOT)}: {what} ({pat})")
    assert not hits, (
        "order-shaped code found in a package that must not be able to trade:\n  "
        + "\n  ".join(hits)
    )


def test_allowlist_has_no_dead_entries():
    """An allowlisted file that no longer matches must be removed."""
    dead = []
    for name, _reason in ALLOWED.items():
        p = SRC / name
        if not p.exists():
            dead.append(f"{name}: file does not exist")
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if not any(re.search(pat, text) for pat, _ in FORBIDDEN):
            dead.append(f"{name}: no longer matches anything - drop it")
    assert not dead, "stale allowlist entries:\n  " + "\n  ".join(dead)


def test_allowlist_reasons_are_written():
    assert all(len(r.strip()) > 20 for r in ALLOWED.values())


# --------------------------------------------------------------------------
# 2. Runtime: the only door out refuses everything except allowlisted GETs
# --------------------------------------------------------------------------

def test_only_get_is_permitted():
    with pytest.raises(PaperOnlyViolation):
        safety._check("POST", "https://api.elections.kalshi.com/trade-api/v2/markets", False)
    with pytest.raises(PaperOnlyViolation):
        safety._check("DELETE", "https://api.elections.kalshi.com/trade-api/v2/markets", False)


def test_the_order_path_is_refused_even_as_a_get():
    with pytest.raises(PaperOnlyViolation) as e:
        safety._check("GET", "https://api.elections.kalshi.com/trade-api/v2/portfolio/orders", False)
    assert "allowlist" in str(e.value)


def test_unknown_hosts_are_refused():
    with pytest.raises(PaperOnlyViolation):
        safety._check("GET", "https://demo-api.kalshi.co/trade-api/v2/markets", False)
    with pytest.raises(PaperOnlyViolation):
        safety._check("GET", "https://example.com/anything", False)


def test_the_read_paths_we_actually_use_are_permitted():
    for url in (
        "https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXATPMATCH",
        "https://api.elections.kalshi.com/trade-api/v2/series/",
        "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/atp/atp_matches_2026.csv",
    ):
        safety._check("GET", url, False)


def test_undecidable_hosts_are_refused_by_default():
    """GUARDS #14 - a host that serves no readable robots.txt is UNDECIDABLE.

    www.sofascore.com returns 403 on /robots.txt (checked 2026-08-06), so it is
    a door held shut, not an open one. Refusing costs exactly as much as using
    something we are not permitted to use, which is why the override exists and
    is explicit rather than implicit.
    """
    with pytest.raises(PaperOnlyViolation) as e:
        safety._check("GET", "https://www.sofascore.com/api/v1/sport/tennis/events/live", False)
    assert "UNDECIDABLE" in str(e.value)
    safety._check("GET", "https://www.sofascore.com/api/v1/sport/tennis/events/live", True)


# --------------------------------------------------------------------------
# 3. Credentials
# --------------------------------------------------------------------------

def test_refuses_to_run_with_credentials_present(monkeypatch):
    monkeypatch.setenv("KALSHI_KEY_ID", "not-a-real-key")
    with pytest.raises(PaperOnlyViolation) as e:
        safety.assert_no_credentials()
    assert "KALSHI_KEY_ID" in str(e.value)


def test_runs_clean_without_credentials(monkeypatch):
    for k in ("KALSHI_KEY_ID", "KALSHI_KEY_PATH", "KALSHI_API_KEY",
              "KALSHI_PRIVATE_KEY", "KALSHI_SECRET", "KALSHI_EMAIL",
              "KALSHI_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    safety.assert_no_credentials()


def test_no_pem_file_inside_the_package():
    # .venv is excluded: certifi ships cacert.pem, a public CA bundle. A guard
    # that fires on every install is a guard that gets deleted.
    skip = {".venv", "site-packages", "__pycache__"}
    pems = [p for pat in ("**/*.pem", "**/*private_key*", "**/*.key", "**/*.p12")
            for p in ROOT.glob(pat) if not (skip & set(p.parts))]
    assert not pems, f"key material inside a paper-only package: {pems}"


# --------------------------------------------------------------------------
# 4. GUARDS #9 - prove the detector still bites
# --------------------------------------------------------------------------

def test_the_detector_bites_on_a_planted_violation(tmp_path):
    planted = tmp_path / "planted.py"
    planted.write_text(
        "import requests\n"
        "def go():\n"
        "    return requests.post('https://api.elections.kalshi.com"
        "/trade-api/v2/portfolio/orders', json={})\n",
        encoding="utf-8",
    )
    text = planted.read_text(encoding="utf-8")
    fired = [what for pat, what in FORBIDDEN if re.search(pat, text)]
    assert len(fired) >= 2, (
        "the detector failed to fire on code that literally posts an order. "
        "The guard has rotted, not the data."
    )


# --------------------------------------------------------------------------
# 5. Single instance — continuously, not just at startup
# --------------------------------------------------------------------------

def test_the_lock_is_re_asserted_every_tick_not_only_at_startup(monkeypatch, tmp_path):
    """Checking a lock once at startup is a greeting, not a lock.

    Six runners were alive at once on the dev machine because the lock was
    deleted between restarts. Two runners sharing one state.json is the worst
    kind of corruption: the write is atomic, so the file is never malformed -
    it is simply whichever process wrote last, silently discarding the other's
    positions.
    """
    import json as _json
    from src import forward

    lock = tmp_path / ".runner.lock"
    monkeypatch.setattr(forward, "LOCK", lock)
    monkeypatch.setattr(forward, "DATA", tmp_path)

    # we hold it -> fine
    lock.write_text(_json.dumps({"pid": os.getpid()}), encoding="utf-8")
    forward.assert_still_own_lock()

    # somebody else took it -> we must stop
    lock.write_text(_json.dumps({"pid": os.getpid() + 99999}), encoding="utf-8")
    with pytest.raises(forward.LockLost):
        forward.assert_still_own_lock()

    # it vanished -> we re-take it rather than dying
    lock.unlink()
    forward.assert_still_own_lock()
    assert _json.loads(lock.read_text(encoding="utf-8"))["pid"] == os.getpid()


def test_the_runner_loop_actually_calls_the_lock_check():
    """Source-level: the guard existing is not the same as it being wired in."""
    src = (SRC / "forward.py").read_text(encoding="utf-8")
    loop = src.split("while not _STOP:")[1].split("self._save()")[0]
    assert "assert_still_own_lock()" in loop, (
        "the per-tick lock assertion is defined but not called in the run loop")
    assert "except LockLost" in loop, (
        "LockLost is raised but not handled, so it would be swallowed by the "
        "generic `except Exception` that keeps the runner alive through errors")


def test_release_does_not_remove_someone_elses_lock(monkeypatch, tmp_path):
    import json as _json
    from src import forward
    lock = tmp_path / ".runner.lock"
    monkeypatch.setattr(forward, "LOCK", lock)
    lock.write_text(_json.dumps({"pid": os.getpid() + 99999}), encoding="utf-8")
    forward.release_lock()
    assert lock.exists(), "a shutting-down runner deleted the live runner's lock"
