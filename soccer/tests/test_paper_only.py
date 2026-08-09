"""The guard that makes "paper only" structural rather than a promise.

Walks every .py in this package and fails the build if order-shaped code,
credential reads, or non-GET HTTP appear anywhere. Includes a **guard-rot
check** (GUARDS #9): the detector is run against a deliberately planted
violation, so a detector that has silently stopped detecting fails too.

    python -m pytest tests/ -q
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

# Substrings that must not appear in this package's source at all.
FORBIDDEN = [
    # Kalshi's order path
    "/portfolio/orders", "create_order", "place_order", "CreateOrder",
    "batch_create_orders", "cancel_order", "/portfolio/positions",
    "/portfolio/balance", "/portfolio/fills",
    # credentials
    "KALSHI_API_KEY", "KALSHI_PRIVATE_KEY", "private_key", "PRIVATE KEY",
    "load_pem_private_key", "kalshi_private_key", ".pem",
    "KALSHI_EMAIL", "KALSHI_PASSWORD", "api_secret", "Bearer ",
    # signing
    "PSS(", "padding.PSS", "rsa.sign", "sign_pss_text",
]
# Modules that must not be imported.
FORBIDDEN_IMPORTS = {"cryptography", "kalshi_python", "kalshi_client",
                     "py_clob_client", "web3", "eth_account"}
# HTTP verbs other than GET.
VERB = re.compile(r"""(?:method\s*=\s*["'](?:POST|PUT|DELETE|PATCH)["'])"""
                  r"""|(?:requests\.(?:post|put|delete|patch)\s*\()"""
                  r"""|(?:\.post\s*\()""", re.I)


def _sources():
    return sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in str(p))


def scan_text(text):
    """Return a list of violations found in one source text."""
    bad = []
    for f in FORBIDDEN:
        if f in text:
            bad.append(f"forbidden token {f!r}")
    if VERB.search(text):
        bad.append("non-GET HTTP verb")
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return bad + [f"does not parse: {e}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                if root in FORBIDDEN_IMPORTS:
                    bad.append(f"forbidden import {a.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in FORBIDDEN_IMPORTS:
                bad.append(f"forbidden import from {node.module}")
    return bad


def test_no_order_path_anywhere():
    problems = {}
    for p in _sources():
        if p.name == "test_paper_only.py":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        bad = scan_text(text)
        if bad:
            problems[p.name] = bad
    assert not problems, f"PAPER-ONLY VIOLATION: {problems}"


def test_the_detector_still_detects():
    """GUARDS #9 -- guard rot. A guard nobody has tested against a real
    violation is a guard nobody knows still works. Three planted violations,
    one per detection mechanism."""
    planted = [
        ("token", "def f():\n    url = '/portfolio/orders'\n"),
        ("verb", "import requests\ndef f():\n    requests.post('x')\n"),
        ("import", "from cryptography.hazmat.primitives import hashes\n"),
    ]
    for name, src in planted:
        assert scan_text(src), f"detector missed a planted {name} violation"


def test_clean_source_passes():
    """And it must not fire on ordinary code, or it would be ignored."""
    assert not scan_text(
        "import json\nimport urllib.request\n"
        "def get(u):\n    return json.load(urllib.request.urlopen(u))\n")
