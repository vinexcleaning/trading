"""Mastodon extractor — the one X-shaped platform that permits this agent.

**Why Mastodon and not X, TikTok, Instagram, Facebook or Bluesky.** Measured, per
platform, in `reports/T4d_robots_policy.md` and `T4c_platform_probe.md`:

| platform  | robots verdict for THIS agent | technically reachable keyless |
|-----------|-------------------------------|-------------------------------|
| TikTok    | **REFUSED_BY_NAME** — names `anthropic-ai`, `ClaudeBot`, `Claude-User`, `Claude-SearchBot` and disallows `/` | (moot) |
| X         | REFUSED_VIA_STAR (`Disallow: /`) | API 401, oEmbed now 404 |
| Reddit    | REFUSED_VIA_STAR (`Disallow: /`) | `.json` 403 — archive used instead |
| Facebook  | names `ClaudeBot` with a path list, not a blanket refusal | every endpoint 400 |
| Instagram | serves 400 KB of HTML at `/robots.txt` — no policy at all | login wall |
| Bluesky   | PERMITTED | **403 to bot AND browser UA** |
| **Mastodon** | **PERMITTED** | **200, full text, keyless** |

TikTok is the sharp one. Its `User-agent: *` block *explicitly allows* `/tag`,
`/discover` and `/foryou` — a complete discovery path — but a named group lists
this agent four times and disallows everything, and robots specificity means the
named group wins. The permissive block is for search engines. Using it would
mean not identifying as what we are.

**What Mastodon gives, keyless, that the others do not:** full post text, author
handle, ISO timestamp, favourite and reply counts, and two discovery routes that
work without a token — `/api/v1/timelines/tag/<tag>` and
`/api/v1/timelines/public`. That is everything the ported rubric needs.

Column mapping into the shared `rd_posts` table: `subreddit` <- "instance/tag",
`score` <- favourites_count, `num_comments` <- replies_count, `permalink` <- url,
`selftext` <- the post text with HTML stripped.

    python src/mastodon_fetch.py --tags trading,kalshi,polymarket
    python src/mastodon_fetch.py --probe          # which instances answer keyless
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

UA = ("social-signal/0.1 (research; personal, non-commercial; "
      "+https://github.com/vinexcleaning/trading)")

# Instances measured serving public timelines without a token. `mastodon.social`
# refuses `/timelines/public` unauthenticated but still serves hashtag
# timelines, so it is kept for tags only.
INSTANCES = ["mastodon.social", "mas.to", "fosstodon.org", "mstdn.social"]
PUBLIC_TIMELINE_OK = {"mas.to", "fosstodon.org", "mstdn.social"}

TAGS = ["trading", "algotrading", "quant", "kalshi", "polymarket",
        "predictionmarkets", "betting", "crypto", "finance", "python"]

PACE = 1.5
_TAG_RE = re.compile(r"<[^>]+>")
# `truncated` counts tags whose pagination was REFUSED part-way, as opposed to
# running out of posts. A run with truncated > 0 has an INCOMPLETE corpus and
# any "we found N posts about X" built on it is a floor, not a count.
STATS = {"calls": 0, "errors": 0, "rows": 0, "429s": 0, "truncated": 0}


def strip_html(s: str) -> str:
    """Mastodon serves `content` as HTML. The rubric scores prose, so tags go —
    but paragraph breaks are preserved, because losing them glues sentences
    together and the quote-extraction rule needs readable spans."""
    s = re.sub(r"</p>\s*<p>", "\n\n", s or "")
    s = re.sub(r"<br\s*/?>", "\n", s)
    return html.unescape(_TAG_RE.sub("", s)).strip()


def call(url: str, retries: int = 2):
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                STATS["calls"] += 1
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            STATS["calls"] += 1
            if e.code == 429:
                STATS["429s"] += 1
                time.sleep(30 * (attempt + 1))
                continue
            if e.code in (401, 422):      # this instance wants a token
                return None
            if attempt >= retries:
                STATS["errors"] += 1
                return None
            time.sleep(4 * (attempt + 1))
        except Exception:  # noqa: BLE001
            if attempt >= retries:
                STATS["errors"] += 1
                return None
            time.sleep(4 * (attempt + 1))
        finally:
            time.sleep(PACE)
    return None


def store(con, rows, instance: str, bucket: str, query: str) -> int:
    n = 0
    for s in rows:
        if not isinstance(s, dict) or not s.get("id"):
            continue
        acct = s.get("account") or {}
        text = strip_html(s.get("content") or "")
        created = s.get("created_at") or ""
        try:
            ts = datetime.datetime.fromisoformat(
                created.replace("Z", "+00:00")).timestamp()
        except ValueError:
            ts = 0.0
        con.execute("""
            INSERT OR IGNORE INTO rd_posts
              (post_id, subreddit, title, selftext, author, created_utc, score,
               upvote_ratio, num_comments, permalink, is_self, url, link_flair,
               over_18, query, fetched_utc, platform)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f"mastodon:{instance}:{s['id']}", f"{instance}/{bucket}",
             text[:120], text, acct.get("acct") or "", ts,
             s.get("favourites_count") or 0, None,
             s.get("replies_count") or 0, s.get("url") or "", 1,
             s.get("url") or "", (s.get("language") or ""),
             1 if s.get("sensitive") else 0, query, db.now(), "mastodon"))
        n += 1
    STATS["rows"] += n
    return n


def probe():
    print("instance            /timelines/public   /timelines/tag/trading")
    for host in INSTANCES:
        a = call(f"https://{host}/api/v1/timelines/public?limit=2")
        b = call(f"https://{host}/api/v1/timelines/tag/trading?limit=2")
        print(f"  {host:<20}{('OK ' + str(len(a))) if a is not None else 'no token':<18}"
              f"{('OK ' + str(len(b))) if b is not None else 'refused'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", default=",".join(TAGS))
    ap.add_argument("--instances", default=",".join(INSTANCES))
    ap.add_argument("--pages", type=int, default=5,
                    help="pages of 40 per tag per instance, walked back by max_id")
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()

    if args.probe:
        probe()
        return

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    instances = [i.strip() for i in args.instances.split(",") if i.strip()]
    con = db.connect()
    t0 = time.time()
    total = 0

    for host in instances:
        for tag in tags:
            got, max_id = 0, None
            for _ in range(args.pages):
                url = (f"https://{host}/api/v1/timelines/tag/"
                       f"{urllib.parse.quote(tag)}?limit=40")
                if max_id:
                    url += f"&max_id={max_id}"
                rows = call(url)
                # **`None` is a refusal; `[]` is the end of the results.**
                # These used to both `break`, so a 429 or a timeout part-way
                # through pagination silently truncated the harvest and was
                # recorded as "that is all there was". GUARDS #25 — and this
                # one is worse than a wrong absence claim in a report, because
                # it quietly shrinks the corpus every later count is built on.
                if rows is None:
                    STATS["truncated"] = STATS.get("truncated", 0) + 1
                    print(f"    !! {host} #{tag}: REFUSED mid-pagination after "
                          f"{got} posts — this tag is INCOMPLETE, not exhausted",
                          flush=True)
                    break
                if not rows:
                    break
                got += store(con, rows, host, f"tag:{tag}", f"tag:{tag}")
                con.commit()
                max_id = rows[-1].get("id")
                if len(rows) < 40:
                    break
            total += got
            if got:
                print(f"  {host:<18} #{tag:<20} {got:>5} posts", flush=True)

        if host in PUBLIC_TIMELINE_OK:
            rows = call(f"https://{host}/api/v1/timelines/public?limit=40")
            if rows:
                n = store(con, rows, host, "public", "public")
                con.commit()
                total += n
                print(f"  {host:<18} {'public timeline':<21} {n:>5} posts",
                      flush=True)

    n_all = con.execute("SELECT COUNT(*) c FROM rd_posts WHERE platform='mastodon'"
                        ).fetchone()["c"]
    print(f"\n  {total} stored this run; {n_all} mastodon posts in the corpus")
    print(f"  transport: {json.dumps(STATS)}  {time.time()-t0:.0f}s")
    db.log(con, "mastodon_fetch",
           f"stored={total} total={n_all} " + json.dumps(STATS))
    con.close()


if __name__ == "__main__":
    main()
