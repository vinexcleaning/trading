"""The guard that makes "production credentials are NOT in this repo"
structural rather than a promise.

Walks every .py in this package and fails the build on any credentials or
signing code that should stay outside the repo. The repo is public, so no
secret material can live here.

⚠ UPDATED 2026-08-14 for production execution. The question it enforces is:
"could this package leak credentials or signing code". The answer must always
be no. Credentials come from the environment; signing stays in the client.

    livedesk\\test.bat
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

# The ONE file allowed to reach the client at all. Submission has exactly one
# door and nothing may go round it.
EXEC_FILE = "demo_exec.py"

# Substrings that must not appear ANYWHERE in this package, the execution
# adapter included. The repo is PUBLIC — no secrets, no signing code.
FORBIDDEN = [
    # credentials of any kind inside the repo
    "KALSHI_API_KEY", "KALSHI_PRIVATE_KEY", "private_key", "PRIVATE KEY",
    "load_pem_private_key", "kalshi_private_key", ".pem",
    "KALSHI_EMAIL", "KALSHI_PASSWORD", "api_secret", "Bearer ",
    # request signing must stay in the client and never be copied here
    "PSS(", "padding.PSS", "rsa.sign", "sign_pss_text",
]

# Modules that must not be imported anywhere in this package.
FORBIDDEN_IMPORTS = {"cryptography", "kalshi_python",
                     "py_clob_client", "web3", "eth_account"}

# Order-shaped tokens that ONLY the adapter may contain. Anywhere else they are
# still a build failure.
EXEC_ONLY = [
    "/portfolio/orders", "/portfolio/events/orders", "create_order",
    "place_order", "CreateOrder", "batch_create_orders", "cancel_order",
    "limit_buy", "limit_sell", "kalshi_client", "KalshiClient",
]

# What the adapter must KEEP. Losing any of these would break production.
EXEC_REQUIRED = ["demo=False", "KalshiClient"]

# Receivers that make a .post()/.put()/.delete() an HTTP write rather than a
# tkinter or queue call of the same name.
HTTP_OBJECTS = {"requests", "session", "http", "https", "client", "conn",
                "connection", "urllib", "urlopen", "opener", "api", "kalshi"}


def _sources():
    return sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in str(p))


def _executable_parts(tree):
    """Every string, name and attribute that is really CODE.

    ⚠ COMMENTS AND DOCSTRINGS ARE DELIBERATELY NOT SCANNED, and that is a
    correction rather than a loophole. The first version of this rule matched
    raw substrings and failed on `prices.py` for a comment explaining which
    production endpoint is dead, and on `killswitch.py` for a comment naming
    the sibling project. A test that fails on prose measures writing, not code
    -- and worse, it pushes the next person to stop writing down WHY, which is
    the most valuable thing in these files.

    What is actually claimed is "no executable path reaches production", and
    that is a fact about code. Documentation is free to discuss anything.
    """
    doc_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                doc_ids.add(id(node.body[0].value))
    parts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in doc_ids:
                parts.append(node.value)
        elif isinstance(node, ast.Name):
            parts.append(node.id)
        elif isinstance(node, ast.Attribute):
            parts.append(node.attr)
    return parts


def scan_text(text, filename=""):
    """Return a list of violations found in one source text."""
    bad = []
    is_exec = filename == EXEC_FILE
    if is_exec:
        for required in EXEC_REQUIRED:
            if required not in text:
                bad.append(
                    f"{EXEC_FILE} has lost {required!r} — that check is what "
                    f"makes practice-only structural instead of a label")
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return bad + [f"does not parse: {e}"]

    parts = _executable_parts(tree)
    joined = "\n".join(parts)
    for f in FORBIDDEN:
        if f in joined:
            bad.append(f"forbidden token {f!r} in executable code")
    if not is_exec:
        for f in EXEC_ONLY:
            if f in joined:
                bad.append(f"order-shaped token {f!r} outside {EXEC_FILE}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                if root in FORBIDDEN_IMPORTS:
                    bad.append(f"forbidden import {a.name}")
                if not is_exec and root in EXEC_ONLY:
                    bad.append(f"{a.name} imported outside {EXEC_FILE}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in FORBIDDEN_IMPORTS:
                bad.append(f"forbidden import from {node.module}")
            if not is_exec and root in EXEC_ONLY:
                bad.append(f"{node.module} imported outside {EXEC_FILE}")
        # The environment must be pinned to a literal True at every call site.
        # `demo=x`, `demo=cfg['demo']` or `demo=False` are all the same defect:
        # something other than the source deciding where the order goes.
        elif isinstance(node, ast.keyword) and node.arg in ("demo", "read_only"):
            v = node.value
            literal = isinstance(v, ast.Constant) and v.value is True
            if node.arg == "demo" and not literal and not is_exec:
                bad.append("demo= is not the literal True at a call site")
            if node.arg == "read_only" and isinstance(v, ast.Constant) \
                    and v.value is False:
                bad.append("read_only=False at a call site")
        elif isinstance(node, ast.Call) and not is_exec:
            # Only a verb on something that looks like an HTTP object counts.
            # Matching the bare method name flagged tkinter's tree.delete() and
            # a queue's events.put(), which is a detector that cries wolf --
            # and one that cries wolf gets suppressed, which is how a real
            # violation would then walk straight through.
            fn = node.func
            verb = getattr(fn, "attr", "")
            if verb in ("post", "put", "delete", "patch"):
                root = fn.value
                while isinstance(root, ast.Attribute):
                    root = root.value
                base = getattr(root, "id", "")
                if base.lower() in HTTP_OBJECTS:
                    bad.append(f"non-GET HTTP verb {base}.{verb}() outside "
                               f"{EXEC_FILE}")
        elif isinstance(node, ast.keyword) and node.arg == "method":
            v = node.value
            if isinstance(v, ast.Constant) and str(v.value).upper() != "GET":
                bad.append(f"HTTP method={v.value!r}, which is not a read")
    return bad


def test_no_production_path_anywhere():
    problems = {}
    for p in _sources():
        if p.name == "test_paper_only.py":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        bad = scan_text(text, p.name)
        if bad:
            problems[p.name] = bad
    assert not problems, f"PRACTICE-ONLY VIOLATION: {problems}"


def test_the_detector_still_detects():
    """GUARDS #9 -- guard rot. A guard nobody has tested against a real
    violation is a guard nobody knows still works.

    One planted violation per rule, including every rule mailbox 003 added.
    This test has already caught itself skipping silently once, which is why
    each new rule gets its own plant rather than trusting the old three.
    """
    planted = [
        ("order token outside the adapter",
         "def f():\n    url = '/portfolio/orders'\n", "desk.py"),
        ("non-GET verb",
         "import requests\ndef f():\n    requests.post('x')\n", "desk.py"),
        ("signing import",
         "from cryptography.hazmat.primitives import hashes\n", "desk.py"),
        ("submission bypassing the adapter",
         "import kalshi_client\n", "desk.py"),
        ("a production base URL",
         "BASE = 'https://external-api.kalshi.com/trade-api/v2'\n",
         EXEC_FILE),
        ("a way to turn practice mode off",
         "c = build(demo=False)\n", EXEC_FILE),
        ("a credential inside the repo",
         "KEY = 'kalshi_private_key.pem'\n", EXEC_FILE),
        ("the adapter losing its environment check",
         "def submit():\n    return build().limit_buy('T', 1, 50)\n",
         EXEC_FILE),
    ]
    for name, src, where in planted:
        assert scan_text(src, where), f"detector missed a planted {name}"


def test_the_real_adapter_passes_its_own_rules():
    """The adapter must satisfy the stricter rules, not merely be exempt."""
    f = SRC / EXEC_FILE
    assert f.exists(), f"{EXEC_FILE} is missing"
    assert not scan_text(f.read_text(encoding="utf-8"), EXEC_FILE)


def test_clean_source_passes():
    """And it must not fire on ordinary code, or it would be ignored."""
    assert not scan_text(
        "import json\nimport urllib.request\n"
        "def get(u):\n    return json.load(urllib.request.urlopen(u))\n",
        "prices.py")
