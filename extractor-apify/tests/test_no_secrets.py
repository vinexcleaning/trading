"""The guard that makes "no credential is in this folder" structural.

Adapted from `livedesk/tests/test_paper_only.py`. Same shape, different
question. That file asks "could this package reach production"; this one asks
**"could this folder leak a token"**, because this repo is PUBLIC and a token
was already pasted into a chat window once, on 2026-08-14.

The rule the guard enforces:

    The Apify token lives at C:\\Users\\vinig\\keys\\apify.txt, OUTSIDE this
    repo, and is read at runtime. It is never copied here, never printed,
    never logged, never put in an error message.

`.gitignore` blocks `apify.txt`, `*apify*token*`, `*_token.txt` and `keys/`.
That is a backstop, not permission -- a gitignore only helps for names somebody
thought of in advance, and this test does not depend on the name.

**Every file is scanned, not only .py.** The recorded failure mode was a token
in a chat, and the things that look most like a chat in a repo are the Markdown
files. A guard that only reads source would have missed the actual incident.

    py -3 -m pytest extractor-apify\\tests -q
"""
from __future__ import annotations

import re
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent

# Directories that are not ours to police and would only produce noise.
SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules", ".pytest_cache"}

# Extensions with no plausible token in them.
SKIP_EXT = {".db", ".sqlite", ".sqlite3", ".png", ".jpg", ".jpeg", ".gif",
            ".pdf", ".zip", ".gz", ".xlsx", ".pyc"}

# Shapes that are a credential, not a word. Each is a real vendor's format
# rather than a guess, so the test says WHICH vendor when it fires.
SECRET_SHAPES = [
    ("apify api token", re.compile(r"apify_api_[A-Za-z0-9]{20,}")),
    ("apify legacy token", re.compile(r"\bapify[_-]?token\s*[=:]\s*['\"]?"
                                      r"[A-Za-z0-9]{25,}")),
    ("openai key", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("anthropic key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("google api key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer literal", re.compile(r"[Bb]earer\s+[A-Za-z0-9\-._~+/]{25,}")),
    ("bluesky app password", re.compile(r"\b[a-z0-9]{4}-[a-z0-9]{4}-"
                                        r"[a-z0-9]{4}-[a-z0-9]{4}\b")),
    # Bright Data hands out a UUID-shaped key. A BARE uuid is deliberately not
    # flagged -- snapshot ids, dataset ids and request ids all look like that
    # and appear in every log line and report. What is flagged is a uuid
    # sitting next to a Bright Data word, which is what a paste looks like.
    ("brightdata api key",
     re.compile(r"(bright ?data|brd_|BRIGHTDATA_TOKEN)[^\n]{0,40}"
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-"
                r"[0-9a-f]{12}", re.I)),
    ("brightdata proxy credential",
     re.compile(r"brd-customer-[A-Za-z0-9_\-]{6,}")),
    # A long unbroken high-entropy run assigned to a credential-shaped name.
    ("secret-shaped assignment",
     re.compile(r"\b(token|secret|api[_-]?key|password|passwd|apikey)\b"
                r"\s*[=:]\s*['\"][A-Za-z0-9+/=_\-]{24,}['\"]", re.I)),
]

# The token must be READ from outside the repo, so the path itself is allowed
# to appear. Anything that looks like the value is not.
ALLOWED_SUBSTRINGS = [
    r"C:\Users\vinig\keys\apify.txt",
    r"C:\Users\vinig\keys\brightdata.txt",
    "keys/apify.txt",
    "keys/brightdata.txt",
    "apify.txt",
    "brightdata.txt",
]


def _files():
    for p in sorted(FOLDER.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in SKIP_EXT:
            continue
        yield p


def scan_text(text: str, filename: str = "") -> list:
    """Return every credential-shaped thing in one document."""
    bad = []
    for name, pat in SECRET_SHAPES:
        for m in pat.finditer(text):
            span = m.group(0)
            if any(a in span for a in ALLOWED_SUBSTRINGS):
                continue
            # Report the SHAPE and the position. Never the value -- a guard
            # that prints the secret into a test log has leaked it itself.
            bad.append(f"{name} at offset {m.start()} "
                       f"({len(span)} chars, not shown)")
    return bad


def test_no_credential_anywhere_in_this_folder():
    problems = {}
    for p in _files():
        if p.name == "test_no_secrets.py":
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        bad = scan_text(text, p.name)
        if bad:
            problems[str(p.relative_to(FOLDER))] = bad
    assert not problems, f"CREDENTIAL IN A PUBLIC REPO: {problems}"


def test_the_detector_still_detects():
    """GUARDS #9 -- guard rot. A guard nobody has tested against a real
    violation is a guard nobody knows still works. One plant per shape."""
    planted = [
        ("an apify token pasted in",
         "TOKEN = 'apify_api_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8'"),
        ("an apify token in a markdown note",
         "he sent me apify_api_" + "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"),
        ("a named legacy token",
         "apify_token = '" + "Q" * 30 + "'"),
        ("an openai key", "key = 'sk-" + "B" * 40 + "'"),
        ("an anthropic key", "sk-ant-" + "C" * 40),
        ("a github token", "ghp_" + "D" * 36),
        ("an aws key", "AKIA" + "E" * 16),
        ("a slack token", "xoxb-" + "1234567890abcdef"),
        ("a google key", "AIza" + "F" * 35),
        ("a private key block", "-----BEGIN RSA PRIVATE KEY-----"),
        ("a bearer literal", "Authorization: Bearer " + "G" * 30),
        ("a bluesky app password", "pw is abcd-efgh-ijkl-mnop"),
        ("a bright data key next to its own name",
         "BRIGHTDATA_TOKEN=8f3a1c2d-4b5e-6f70-8a9b-0c1d2e3f4a5b"),
        ("a bright data key in prose",
         "the bright data key is 8f3a1c2d-4b5e-6f70-8a9b-0c1d2e3f4a5b"),
        ("a bright data proxy login", "brd-customer-hl_1a2b3c4d-zone-web"),
        ("a generic secret assignment",
         'password = "' + "H" * 30 + '"'),
    ]
    for name, src in planted:
        assert scan_text(src), f"detector missed a planted {name}"


def test_the_detector_does_not_cry_wolf():
    """A guard that fires on ordinary prose gets suppressed, and a suppressed
    guard is how a real violation walks straight through."""
    clean = [
        "Read the token from C:\\Users\\vinig\\keys\\apify.txt at runtime.",
        "The token lives at keys/apify.txt, outside this public repo.",
        "url = 'https://api.bsky.app/xrpc/app.bsky.feed.searchPosts'",
        "# apify costs $0.40 per 1,000 tweets, measured 2026-08-14",
        "cursor = 'eyJzIjpbMTc4Njc0ODU4MjAwMCwiZGlkOnBsYzpn'",
        "def load_token(path): return open(path).read().strip()",
        "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/3kkzc3swzy22c",
        "snapshot_id = 8f3a1c2d-4b5e-6f70-8a9b-0c1d2e3f4a5b",
        "dataset_id=gd_lwxmeb2u1cniijd7t4 type=discover_new",
        "Read the token from " + chr(92) + chr(92) + "keys" + chr(92) + chr(92) + "brightdata.txt",
    ]
    for c in clean:
        assert not scan_text(c), f"detector cried wolf on: {c[:60]}"


def test_the_token_is_not_read_from_inside_the_repo():
    """Whatever loads the token must point OUTSIDE this repo. A loader that
    falls back to a local file is the same defect with an extra step."""
    for p in FOLDER.rglob("*.py"):
        if "__pycache__" in p.parts or p.name == "test_no_secrets.py":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if not any(n in line for n in ("apify.txt", "brightdata.txt")):
                continue
            assert ("keys" in line or "KEYS" in line), (
                f"{p.name} names a key file without the outside-the-repo keys "
                f"path: {line.strip()[:80]}")
