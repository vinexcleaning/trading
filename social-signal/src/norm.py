"""Name and URL normalisation for the cross-platform join.

The whole project turns on one question: is the thing a YouTuber calls
"py-clob-client" the same thing a GitHub repo imports as `py_clob_client` and
the same thing a Reddit thread calls "the Polymarket python client"?

Two rules learned from the sibling projects, both of which cost them a wrong
answer once:

1. **A garbled name is evidence about the transcript, not about the tool.**
   youtube-signal recorded "Creo" as NO_FOOTPRINT; the product is "Kreo" and it
   has a documented security history. Auto-captions garble product names, so a
   join key must survive vowel-level noise where that is cheap, and where it is
   not, the miss must be visible rather than silent.

2. **Never resolve a tool by free-text name search.** Both siblings found that
   returns a different project at rank 0, confidently. So this module only
   produces *keys*; matching is exact-on-key, and anything unmatched is reported
   as unmatched rather than guessed at.
"""
from __future__ import annotations

import re

# Words that carry no identity. "the Polymarket API" and "Polymarket" are the
# same entity for reputation purposes; "Polymarket" and "Polymarket Analytics"
# are not, so only pure noise is stripped.
STOP = {
    "the", "a", "an", "of", "for", "and", "official", "python", "py", "js",
    "sdk", "client", "api", "bot", "tool", "app", "site", "website", "library",
    "lib", "package", "v1", "v2", "com", "io", "xyz", "dev", "ai",
}

_PAREN = re.compile(r"\([^)]*\)")
_DASHED_TAIL = re.compile(r"\s+[—–-]{1,2}\s+.*$")
_NONWORD = re.compile(r"[^a-z0-9]+")
_GH = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
_DOMAIN = re.compile(r"https?://([^/\s]+)")


def strip_descriptor(name: str) -> str:
    """Drop the human gloss creators attach to a tool name.

    "Kreo (Telegram copy-trading bot)" and "upside.tools - Plus EV Sniper" both
    carry the product name first and a description after. The description is
    what makes two records of the same product fail to join.
    """
    s = _PAREN.sub(" ", name or "")
    s = _DASHED_TAIL.sub("", s)
    return s.strip()


def key(name: str) -> str:
    """The join key. Lowercase alphanumerics only, stop-words removed.

    `py-clob-client` -> `clob`; `Polymarket CLOB API` -> `polymarketclob`.
    Deliberately lossy: a key collision is visible in the report and a missed
    join is not.
    """
    s = strip_descriptor(name).lower()
    parts = [p for p in _NONWORD.split(s) if p]
    parts = [p for p in parts if p not in STOP] or parts
    return "".join(parts)


def compact(name: str) -> str:
    """Every alphanumeric, nothing removed. Used as a secondary key so that
    `pyclobclient` still matches `py-clob-client` when the stop-word pass has
    eaten too much."""
    return _NONWORD.sub("", strip_descriptor(name).lower())


def github_repo(url: str) -> str | None:
    """owner/name from any github URL, or None. Trailing `.git`, `#anchor` and
    `?query` are stripped; a bare `github.com` (which youtube-signal stores for
    one tool) yields None rather than a fake repo."""
    if not url:
        return None
    m = _GH.search(url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    repo = repo.split("#")[0].split("?")[0]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo or repo in ("", "."):
        return None
    return f"{owner}/{repo}"


def github_owner(url: str) -> str | None:
    """Just the account, for tools recorded as a GitHub *account* rather than a
    repo (`https://github.com/moondevonyt`)."""
    if not url:
        return None
    m = re.search(r"github\.com/([A-Za-z0-9_.-]+)/?$", url.rstrip("/"))
    return m.group(1) if m else None


def domain(url: str) -> str | None:
    if not url:
        return None
    m = _DOMAIN.match(url.strip())
    if not m:
        # bare hostnames are stored unprefixed by youtube-signal
        cand = url.strip().split("/")[0]
        return cand.lower().lstrip("www.") if "." in cand else None
    return m.group(1).lower().removeprefix("www.")
