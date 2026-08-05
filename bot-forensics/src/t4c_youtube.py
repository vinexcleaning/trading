"""
t4c_youtube.py - TASK 4, the YouTube arm.

Queries the two youtube-signal corpora that already exist (750 + 470 videos,
692 + 443 cached transcripts) rather than crawling again. Read-only: opened
with SQLite URI mode `?mode=ro`, so a concurrent sibling session cannot be
disturbed and nothing is written.

The questions are the same four. The corpora were built for Kalshi/Polymarket
edge-hunting, so the honest expectation is that Q1 and Q4 are partly covered
and Q2/Q3 (tennis data plumbing) are not covered at all. Whether that is true
is the finding; inventing sources when the corpus is silent is the failure
mode this project's own rules name.
"""
from __future__ import annotations
import sqlite3, os, re, sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
DBS = [
    ("broad", r"C:\Users\vinig\trading\youtube-signal\data\signal.db"),
    ("kalshi_edge", r"C:\Users\vinig\trading\youtube-signal\data\signal_kalshi_edge.db"),
]

TERMS = {
    "Q1 in-play tennis": [r"\btennis\b", r"in.?play", r"live betting", r"betfair"],
    "Q2 score/odds feeds": [r"sofascore", r"flashscore", r"odds api", r"the.odds.api",
                            r"scrape.{0,20}odds", r"live score"],
    "Q3 ITF": [r"\bITF\b", r"challenger tour", r"futures tennis"],
    "Q4 time of day": [r"overnight", r"time of day", r"off.hours", r"thin market",
                       r"illiquid.{0,20}hour", r"late night"],
}


def scan():
    lines = []
    for name, path in DBS:
        if not os.path.exists(path):
            lines.append(f"{name}: MISSING at {path}")
            continue
        c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        c.row_factory = sqlite3.Row
        lines.append("=" * 78)
        lines.append(f"CORPUS: {name}")
        lines.append("=" * 78)
        vids = {r["video_id"]: r for r in c.execute(
            "select * from videos") if "video_id" in r.keys()}
        # The transcript text lives in `snippets_json`, not a `text` column.
        # The first version of this scan looked for `text`, found nothing, and
        # reported "0 transcript hits" for all four questions - a clean answer
        # that was entirely an artifact of the wrong column name. That is the
        # silent-failure-inflates-a-denominator trap, caught by the fact that
        # a corpus of 443 finance transcripts containing ZERO instances of
        # "odds" is not believable.
        tx = {r["video_id"]: (r["snippets_json"] or "")
              for r in c.execute("select video_id, snippets_json from transcripts")}
        assert sum(len(v) for v in tx.values()) > 10_000, \
            "transcripts came back empty - schema changed again"
        lines.append(f"videos {len(vids)}  transcripts {len(tx)}")
        lines.append(f"transcript chars: {sum(len(v) for v in tx.values()):,}")
        # canary: a term that MUST appear if the scan is working at all
        can = sum(len(re.findall(r"market", v, re.I)) for v in tx.values())
        lines.append(f"canary - 'market' appears {can:,} times across the "
                     f"transcripts (zero here means the scan is broken)")
        for q, pats in TERMS.items():
            hitv, hitt = set(), {}
            rx = [re.compile(p, re.I) for p in pats]
            for vid, r in vids.items():
                blob = " ".join(str(r[k]) for k in r.keys()
                                if isinstance(r[k], str))
                if any(p.search(blob) for p in rx):
                    hitv.add(vid)
            for vid, t in tx.items():
                if not t:
                    continue
                n = sum(len(p.findall(t)) for p in rx)
                if n:
                    hitt[vid] = n
            lines.append(f"\n--- {q}")
            lines.append(f"    title/description hits : {len(hitv)}")
            lines.append(f"    transcript hits        : {len(hitt)} videos, "
                         f"{sum(hitt.values())} mentions")
            for vid, n in sorted(hitt.items(), key=lambda z: -z[1])[:6]:
                r = vids.get(vid)
                title = (r["title"] if r is not None and "title" in r.keys()
                         else "?")
                lines.append(f"      {n:5d}x  {vid}  {str(title)[:88]}")
                # one line of context per top video
                t = tx[vid]
                for p in rx:
                    m = p.search(t)
                    if m:
                        s = max(0, m.start() - 140)
                        ctx = " ".join(t[s:m.end() + 180].split())
                        lines.append(f"             ...{ctx[:260]}...")
                        break
        c.close()
    return "\n".join(lines)


if __name__ == "__main__":
    txt = scan()
    print(txt)
    open(os.path.join(OUT, "t4c_youtube.txt"), "w", encoding="utf-8").write(txt)
