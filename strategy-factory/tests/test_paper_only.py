"""The guard that makes "paper only" structural rather than a promise.

Copied from `mlb-paper/tests/test_paper_only.py` rather than reinvented, on the
standing rule in `CLAUDE.md` section 10: "Copy the existing test; do not invent
a third style." Two changes, both strengthenings, both explained below.

Walks every .py in this package and fails the build if order-shaped code,
credential reads, or non-GET HTTP appear anywhere. Includes a **guard-rot
check** (GUARDS #9): the detector is run against a deliberately planted
violation, so a detector that has silently stopped detecting fails too.

CHANGE 1 - IT ALSO SCANS THE MODULES THIS PACKAGE IMPORTS FROM OTHER FOLDERS.
The factory deliberately imports `bot-hunt/src/venues.py` instead of copying it
(DECISIONS.md D2). A paper-only test that walks only its own folder would
therefore certify a package whose actual network code it never read. The
original test could assume its package was self-contained; this one cannot, so
it does not.

CHANGE 2 - IT FAILS IF THE IMPORTED MODULE IS MISSING RATHER THAN PASSING.
An absent file reading as "nothing to scan, all clear" is GUARDS #23 exactly: a
missing key reads None and becomes a silent zero.

    py -3 -m pytest strategy-factory/tests -q
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
REPO = HERE.parent.parent

#: Modules from OUTSIDE this package that this package imports at runtime.
#: Every entry here is code that runs inside the factory's process and is
#: therefore inside the paper-only promise, wherever it happens to live.
EXTERNAL_IMPORTS = [
    REPO / "bot-hunt" / "src" / "venues.py",
]

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
            bad.append("forbidden token %r" % f)
    if VERB.search(text):
        bad.append("non-GET HTTP verb")
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return bad + ["does not parse: %s" % e]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                if root in FORBIDDEN_IMPORTS:
                    bad.append("forbidden import %s" % a.name)
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in FORBIDDEN_IMPORTS:
                bad.append("forbidden import from %s" % node.module)
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
    assert not problems, "PAPER-ONLY VIOLATION: %s" % problems


def test_imported_external_modules_are_also_paper_only():
    """The factory's network code lives in another chat's folder. It is still
    the factory's network code."""
    problems = {}
    for p in EXTERNAL_IMPORTS:
        if not p.exists():
            problems[str(p)] = ["MISSING - cannot certify what is not there"]
            continue
        bad = scan_text(p.read_text(encoding="utf-8", errors="replace"))
        if bad:
            problems[str(p)] = bad
    assert not problems, "PAPER-ONLY VIOLATION in an imported module: %s" % problems


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
        assert scan_text(src), "detector missed a planted %s violation" % name


def test_clean_source_passes():
    """And it must not fire on ordinary code, or it would be ignored."""
    assert not scan_text(
        "import json\nimport urllib.request\n"
        "def get(u):\n    return json.load(urllib.request.urlopen(u))\n")
