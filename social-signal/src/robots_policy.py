"""Which platforms permit an agent of THIS kind — and which name it and refuse?

This is the foundation every extractor in this project sits on, and it was
nearly missed. The obvious reading of a `robots.txt` is the `User-agent: *`
block. TikTok's `*` block is permissive — it **explicitly allows** `/tag`,
`/discover`, `/foryou` and `/music`, which is a complete discovery path for a
hashtag-based extractor.

But TikTok's file opens with a different group:

    User-agent: GPTBot / OAI-SearchBot / anthropic-ai / ClaudeBot /
                Claude-User / Claude-SearchBot / PerplexityBot /
                Google-Extended / meta-externalagent / CCBot / Bytespider / ...
    Disallow: /

**`robots.txt` specificity means the named group wins over `*`.** TikTok has not
merely restricted crawlers; it has singled out AI agents — including this one by
name, four times — and refused the entire site. The permissive `*` block is for
search engines, and reading it as permission would mean relying on not
identifying as what I am.

So the question this module answers is not *"what does robots.txt say"*. It is:

    **Is there a group that names an agent of my kind, and what does it say?**

An extractor is built for a platform only when the answer is no group names us
and the `*` block permits the path. Everything else is recorded as refused, with
the exact line that refuses it.

    python src/robots_policy.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/127.0 Safari/537.36")

# Tokens that identify an agent of this kind. If a robots group names any of
# them, that group binds us regardless of what `*` says.
OUR_KIND = (
    "anthropic-ai", "claudebot", "claude-user", "claude-searchbot", "claude-web",
)
# Named alongside us in practice; recorded because a platform that blocks the
# whole AI cohort is making a policy statement, not a technical one.
AI_COHORT = (
    "gptbot", "oai-searchbot", "chatgpt-user", "perplexitybot", "perplexity-user",
    "google-extended", "applebot-extended", "meta-externalagent", "ccbot",
    "bytespider", "ai2bot", "mistralai-user", "duckassistbot", "cohere-ai",
    "diffbot", "omgili", "timpibot", "youbot", "amazonbot",
)

SITES = {
    "tiktok": "https://www.tiktok.com/robots.txt",
    "instagram": "https://www.instagram.com/robots.txt",
    "facebook": "https://www.facebook.com/robots.txt",
    "x": "https://x.com/robots.txt",
    "reddit": "https://www.reddit.com/robots.txt",
    "arctic_shift": "https://arctic-shift.photon-reddit.com/robots.txt",
    "youtube": "https://www.youtube.com/robots.txt",
    "threads": "https://www.threads.net/robots.txt",
    "bluesky": "https://bsky.app/robots.txt",
    "mastodon": "https://mastodon.social/robots.txt",
}


def fetch(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER,
                                               "Accept": "text/plain,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(400_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:2000].decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def parse_groups(txt: str):
    """[(agents, rules)] in file order. Blank lines and comments end a group."""
    groups, agents, rules = [], [], []
    for raw in txt.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            if agents and rules:
                groups.append((agents, rules))
                agents, rules = [], []
            continue
        low = s.lower()
        if low.startswith("user-agent:"):
            if rules:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(s.split(":", 1)[1].strip())
        elif ":" in s:
            rules.append(s)
    if agents and rules:
        groups.append((agents, rules))
    return groups


def classify(txt: str):
    """Return the verdict for an agent of our kind."""
    if not txt.lstrip().lower().startswith(("user-agent", "#", "sitemap", "allow",
                                            "disallow")):
        # Several platforms serve their app shell at /robots.txt. That is not a
        # permissive robots file; it is no robots file, and it must not be read
        # as consent.
        return {"verdict": "NO_ROBOTS_SERVED", "matched_group": "",
                "rule": "", "star_rules": [],
                "detail": f"{len(txt):,} chars and it is not a robots.txt "
                          "(looks like HTML). Absence of a policy is not permission."}
    groups = parse_groups(txt)
    star_rules, ours, cohort = [], None, []
    for agents, rules in groups:
        low = [a.lower() for a in agents]
        if any(a == "*" for a in low):
            star_rules = rules
        if any(a in OUR_KIND for a in low):
            ours = (agents, rules)
        if any(a in AI_COHORT for a in low):
            cohort.append(agents)
    if ours:
        agents, rules = ours
        blanket = [r for r in rules if r.lower().replace(" ", "") == "disallow:/"]
        named = [a for a in agents if a.lower() in OUR_KIND]
        return {
            "verdict": "REFUSED_BY_NAME" if blanket else "NAMED_WITH_RULES",
            "matched_group": ", ".join(agents[:6]) + (" …" if len(agents) > 6 else ""),
            "rule": (blanket[0] if blanket else "; ".join(rules[:4])),
            "star_rules": star_rules,
            "detail": f"names us {len(named)}x ({', '.join(named)}); "
                      f"the '*' block does NOT apply — specificity wins",
        }
    star_blanket = [r for r in star_rules
                    if r.lower().replace(" ", "") == "disallow:/"]
    if star_blanket:
        return {"verdict": "REFUSED_VIA_STAR", "matched_group": "*",
                "rule": star_blanket[0], "star_rules": star_rules,
                "detail": "no group names us; the '*' block refuses everything"}
    if not star_rules:
        return {"verdict": "NO_STAR_BLOCK", "matched_group": "", "rule": "",
                "star_rules": [], "detail": "robots served but no '*' group"}
    allows = [r for r in star_rules if r.lower().startswith("allow:")]
    return {"verdict": "PERMITTED", "matched_group": "*",
            "rule": "; ".join(star_rules[:6]), "star_rules": star_rules,
            "detail": f"{len(allows)} Allow rules; no group names us"}


BUILD = {"PERMITTED": "BUILD", "NAMED_WITH_RULES": "BUILD WITHIN THE NAMED RULES"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = []
    for name, url in SITES.items():
        status, txt = fetch(url)
        c = classify(txt) if status == 200 else {
            "verdict": f"HTTP_{status}", "matched_group": "", "rule": "",
            "star_rules": [], "detail": txt[:120]}
        rows.append({"platform": name, "url": url, "status": status, **c})
        print(f"  {name:<14} {status:<4} {c['verdict']:<18} {c['detail'][:70]}")
        time.sleep(1.0)

    out = os.path.join(db.REPORTS, "T4d_robots_policy.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Which platforms permit an agent of this kind\n\n")
        fh.write("The `User-agent: *` block is **not** the answer. Where a "
                 "platform names AI agents in their own group, that group binds "
                 "us and `*` does not — robots.txt specificity means the more "
                 "specific match wins.\n\n")
        fh.write("`REFUSED_BY_NAME` means the platform lists this agent "
                 "explicitly and disallows everything. Reading its permissive "
                 "`*` block as consent would mean not identifying as what we "
                 "are.\n\n")
        fh.write("| platform | verdict | the group that binds us | the rule | build? |\n")
        fh.write("|---|---|---|---|---|\n")
        for r in rows:
            fh.write(f"| {r['platform']} | **{r['verdict']}** | "
                     f"{r['matched_group'] or '—'} | `{r['rule'][:70] or '—'}` | "
                     f"{BUILD.get(r['verdict'], 'NO')} |\n")
        fh.write("\n## Detail\n\n")
        for r in rows:
            fh.write(f"### {r['platform']} — {r['verdict']}\n\n{r['detail']}\n\n")
            if r["star_rules"]:
                fh.write("The `*` block, for reference — **not what binds "
                         "us where a named group exists**:\n\n```\n"
                         + "\n".join(r["star_rules"][:14]) + "\n```\n\n")
    print(f"\n  wrote {out}")
    if args.json:
        print(json.dumps(rows, indent=1))
    con = db.connect()
    db.log(con, "robots_policy",
           " ".join(f"{r['platform']}={r['verdict']}" for r in rows))
    con.close()
    return rows


if __name__ == "__main__":
    main()
