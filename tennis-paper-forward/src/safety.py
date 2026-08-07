"""safety.py — the paper-only enforcement layer.

THIS PACKAGE MUST NEVER BE ABLE TO PLACE AN ORDER. Not "does not", not
"is configured not to" — *cannot*, because the only HTTP door out of the
package refuses to open for anything except a GET to an allowlisted
read-only path.

Three independent layers, each of which alone would be sufficient:

  1. `get()` below is the ONLY network call in the package. It hard-refuses
     any method other than GET, and any URL whose path is not on
     `READ_ONLY_PATHS`. Kalshi's order endpoints live under
     `/trade-api/v2/portfolio/*`, which is not on the list and never will be.

  2. No credential is ever read. `assert_no_credentials()` walks the process
     environment and raises if a Kalshi key variable is set, so a machine that
     happens to have live credentials exported cannot quietly hand them to
     this code. It also refuses to run if a private key file is reachable from
     the package directory.

  3. `tests/test_paper_only.py` greps every source file in the package for
     order-shaped tokens (`portfolio/orders`, `create_order`, `requests.post`,
     `private_key`, `sign_pss`, ...) and fails the build if one appears.

GUARDS #13 applies to all of it: a 200 is not a correct file. `get()` returns
the parsed body and the caller is expected to assert something about the
CONTENT, never that the call returned.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

PKG_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PKG_DIR.parent

# --------------------------------------------------------------------------
# Layer 1 — the allowlist
# --------------------------------------------------------------------------

USER_AGENT = (
    "tennis-paper-forward/1.0 (read-only paper research; "
    "github.com/vinexcleaning/trading)"
)

# Host -> tuple of path PREFIXES that may be requested. Anything else raises.
# Kalshi's order path is /trade-api/v2/portfolio/orders. It is absent here and
# adding it would also have to defeat layer 3.
READ_ONLY_PATHS: dict[str, tuple[str, ...]] = {
    "api.elections.kalshi.com": (
        "/trade-api/v2/markets",
        "/trade-api/v2/events",
        "/trade-api/v2/series",
        "/trade-api/v2/exchange/status",
    ),
    "raw.githubusercontent.com": ("/",),
    "api.github.com": ("/repos/",),
}

# Hosts whose robots.txt we could not read, or which forbid us. Requests to
# these are refused unless the caller passes allow_undecidable=True, which the
# runner only does when TPF_ALLOW_UNDECIDABLE_SOURCES=1 is explicitly set.
# See DECISIONS.md D3.
UNDECIDABLE_HOSTS = frozenset({"www.sofascore.com", "api.sofascore.com"})


class PaperOnlyViolation(RuntimeError):
    """Raised when anything in this package tries to reach a write path."""


def _check(method: str, url: str, allow_undecidable: bool) -> None:
    if method.upper() != "GET":
        raise PaperOnlyViolation(
            f"{method} is refused. This package is read-only by construction."
        )
    p = urlparse(url)
    host = p.hostname or ""
    if host in UNDECIDABLE_HOSTS:
        if not allow_undecidable:
            raise PaperOnlyViolation(
                f"{host} serves no readable robots.txt (403). GUARDS #14: a host "
                f"that serves no robots.txt is UNDECIDABLE, not permitted. "
                f"Set TPF_ALLOW_UNDECIDABLE_SOURCES=1 to override deliberately."
            )
        return
    allowed = READ_ONLY_PATHS.get(host)
    if allowed is None:
        raise PaperOnlyViolation(f"host not on the read-only allowlist: {host!r}")
    if not any(p.path.startswith(a) for a in allowed):
        raise PaperOnlyViolation(
            f"path not on the read-only allowlist for {host}: {p.path!r}"
        )


# --------------------------------------------------------------------------
# Layer 2 — no credentials, ever
# --------------------------------------------------------------------------

_CREDENTIAL_ENV = (
    "KALSHI_KEY_ID",
    "KALSHI_KEY_PATH",
    "KALSHI_API_KEY",
    "KALSHI_PRIVATE_KEY",
    "KALSHI_SECRET",
    "KALSHI_EMAIL",
    "KALSHI_PASSWORD",
)


def assert_no_credentials() -> None:
    """Refuse to run on a process that carries Kalshi credentials.

    A live key in the environment is not dangerous to code that cannot sign.
    Refusing anyway is cheap and removes the whole class of "someone later
    added signing and nobody noticed" from consideration.
    """
    present = [k for k in _CREDENTIAL_ENV if os.environ.get(k)]
    if present:
        raise PaperOnlyViolation(
            "Kalshi credentials are present in this process environment: "
            f"{present}. This package is paper-only and refuses to run "
            "alongside them. Start it from a shell where they are unset."
        )
    # .venv is excluded: certifi legitimately ships cacert.pem, a public CA
    # bundle. Scanning it would make the guard fire on every install and a
    # guard that always fires is a guard that gets deleted.
    skip = {".venv", "__pycache__", "site-packages"}
    for pat in ("**/*private_key*", "**/*.pem", "**/*.p12", "**/*.key"):
        for hit in PROJECT_DIR.glob(pat):
            if skip & set(hit.parts):
                continue
            raise PaperOnlyViolation(f"key material inside a paper-only package: {hit}")


# --------------------------------------------------------------------------
# The one network call
# --------------------------------------------------------------------------

_SESSION: requests.Session | None = None
_LAST_CALL: dict[str, float] = {}
MIN_INTERVAL_SEC = 0.35  # per-host politeness floor


def _session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        _SESSION = s
    return _SESSION


def get(
    url: str,
    *,
    params: dict | None = None,
    timeout: float = 20.0,
    retries: int = 3,
    allow_undecidable: bool = False,
    expect_json: bool = True,
) -> Any:
    """The only outbound call in this package. GET, allowlisted, rate-limited.

    Returns the parsed JSON body (or text when expect_json is False).
    Raises on transport failure after `retries`; the caller decides what a
    missing source means. GUARDS #15: a 404 is returned as None rather than
    treated as death.
    """
    _check("GET", url, allow_undecidable)
    host = urlparse(url).hostname or ""
    gap = time.time() - _LAST_CALL.get(host, 0.0)
    if gap < MIN_INTERVAL_SEC:
        time.sleep(MIN_INTERVAL_SEC - gap)

    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = _session().get(url, params=params, timeout=timeout)
            _LAST_CALL[host] = time.time()
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(2.0 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json() if expect_json else r.text
        except Exception as exc:  # noqa: BLE001 - re-raised below
            last = exc
            _LAST_CALL[host] = time.time()
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} attempts: {url}") from last


def banner() -> str:
    return (
        "PAPER ONLY — no credentials, no order endpoint, GET-only allowlist. "
        "Nothing in this package can place a trade."
    )
