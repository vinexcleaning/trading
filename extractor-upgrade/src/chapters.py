"""Chapters: a free, author-written table of contents that nothing was reading.

**396 of 1,197 descriptions already on disk carry three or more timestamp
markers.** YouTube chapters live in the description, the descriptions were
fetched long ago, and no component in any extractor touches them.

Why they matter more than they sound:

  1  A chapter list is written BY THE AUTHOR. `frames.cues()` guesses where the
     interesting parts are from phrases like "as you can see here". The author
     already told you, in a structured field, for free.
  2  Chapter TITLES are a searchable index of what is inside a video without
     reading a word of its transcript. "Placing your first order", "Backtest
     results", "My P&L" - that is retrieval, and it costs nothing.
  3  A chapter titled "results" or "live account" is a **screen-content
     predictor**, which is exactly what the permitted 3-frame sample needs in
     order to be pointed somewhere useful. Three frames at fixed 25/50/75%
     positions are a lottery; three frames chosen against a chapter list are not
     - and while the fixed positions cannot be changed, knowing WHICH chapter a
     frame landed in turns a guess into a labelled observation.

YouTube's own rule for a description to become chapters: the first stamp must be
`0:00`, there must be at least three, and they must be at least 10 seconds
apart. That rule is implemented here rather than assumed, because a video with
timestamps that do NOT satisfy it shows no chapter bar to a viewer - and the
difference between "the author wrote a contents list" and "the author mentioned
some times" is exactly the kind of distinction this programme keeps getting
wrong in the other direction.

    python src/chapters.py            report over both corpora
    python src/chapters.py --search "backtest|results|p&l"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpora  # noqa: E402

# A timestamp at the start of a line, optionally bracketed, then a title.
STAMP = re.compile(
    r"^[\s\-•*|>]*\(?\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\)?\s*[-–—:|]?\s*(.{2,90})$",
    re.M)

# Chapter titles that predict SCREEN content - the thing a transcript misses.
SCREEN_TITLE = re.compile(
    r"\b(demo|demonstration|walk ?through|live|results?|p&?l|pnl|profit|"
    r"account|balance|wallet|dashboard|backtest|code|coding|terminal|"
    r"setup|install|api|order|placing|execution|chart|screen|proof|"
    r"performance|track record|my (bot|account|trades?))\b", re.I)

# Titles that are structurally NOT content: the sponsor read and the outro.
NOISE_TITLE = re.compile(
    r"^(intro(duction)?|outro|conclusion|thanks|thank you|sponsor|ad|"
    r"disclaimer|subscribe|like and subscribe|end|the end|recap|summary)\W*$",
    re.I)


def to_seconds(s: str) -> int:
    p = [int(x) for x in s.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def parse(description: str, duration_s: float | None = None):
    """Returns (chapters, why_not). `chapters` is [] unless YouTube's own rule
    is satisfied, and `why_not` says which clause failed."""
    if not description:
        return [], "no description"
    raw = []
    for m in STAMP.finditer(description):
        t = to_seconds(m.group(1))
        title = m.group(2).strip(" -–—:|•")
        if title:
            raw.append((t, title))
    if len(raw) < 3:
        return [], f"only {len(raw)} timestamp lines (YouTube needs 3)"
    raw.sort()
    if raw[0][0] != 0:
        return [], f"first stamp is {raw[0][0]}s, not 0:00"
    # >=10 s apart, and inside the runtime if we know it.
    out = [raw[0]]
    for t, title in raw[1:]:
        if t - out[-1][0] >= 10:
            out.append((t, title))
    if duration_s and out[-1][0] > float(duration_s) + 5:
        return [], (f"last stamp {out[-1][0]}s exceeds the {int(duration_s)}s "
                    "runtime - these are references, not chapters")
    if len(out) < 3:
        return [], "fewer than 3 stamps at least 10 s apart"
    return out, ""


def which_chapter(chapters, t: float):
    """Which chapter a given second falls in - this is what turns a fixed
    25/50/75% frame from a guess into a labelled observation."""
    cur = None
    for start, title in chapters:
        if start <= t:
            cur = (start, title)
        else:
            break
    return cur


def scan():
    rows = []
    for corpus in ("yt", "yt_kalshi"):
        con = corpora.ro(corpus)
        for r in con.execute(
                "SELECT v.video_id, v.title, v.description, v.duration_s, "
                "       v.channel_name, v.view_count, "
                "       (SELECT COUNT(*) FROM scores s "
                "         WHERE s.video_id = v.video_id) AS is_read "
                "FROM videos v WHERE v.description IS NOT NULL "
                "  AND v.description <> ''"):
            ch, why = parse(r["description"], r["duration_s"])
            rows.append({
                "corpus": corpus, "video_id": r["video_id"],
                "title": r["title"], "channel": r["channel_name"],
                "duration_s": r["duration_s"], "views": r["view_count"],
                "is_read": bool(r["is_read"]),
                "chapters": ch, "why_not": why,
            })
        con.close()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", help="regex over chapter TITLES")
    a = ap.parse_args()

    rows = scan()
    have = [r for r in rows if r["chapters"]]
    n = len(rows)

    if a.search:
        rx = re.compile(a.search, re.I)
        print(f"chapter titles matching /{a.search}/ across {len(have)} videos "
              "with chapters:\n")
        hits = 0
        for r in have:
            m = [(t, ti) for t, ti in r["chapters"] if rx.search(ti)]
            if not m:
                continue
            hits += 1
            print(f"  {r['video_id']} {'[READ]' if r['is_read'] else '      '} "
                  f"{(r['title'] or '')[:58]}")
            for t, ti in m:
                print(f"      {t//60:>3}m{t%60:02d}s  {ti[:70]}")
        print(f"\n  {hits} videos matched. **No transcript was read to find "
              "them.**")
        return

    # ---- how much of the runtime do chapters cover, vs watch_segments
    seg_by_video = {}
    for corpus in ("yt", "yt_kalshi"):
        con = corpora.ro(corpus)
        for r in con.execute("SELECT video_id, ts_start, ts_end "
                             "FROM watch_segments"):
            seg_by_video.setdefault(r["video_id"], []).append(
                (float(r["ts_start"]), float(r["ts_end"])))
        con.close()

    screen_ch = noise_ch = total_ch = 0
    title_words = Counter()
    for r in have:
        for t, ti in r["chapters"]:
            total_ch += 1
            if NOISE_TITLE.match(ti):
                noise_ch += 1
            elif SCREEN_TITLE.search(ti):
                screen_ch += 1
                # findall returns tuples when the pattern has groups; the
                # whole match is what we want, so iterate matches instead.
                for m in SCREEN_TITLE.finditer(ti):
                    title_words[m.group(0).lower()] += 1

    read = [r for r in rows if r["is_read"]]
    read_have = [r for r in read if r["chapters"]]

    # For read videos: does a watch_segment sit inside a screen-titled chapter?
    agree = seg_total = 0
    for r in read_have:
        segs = seg_by_video.get(r["video_id"], [])
        for s, e in segs:
            seg_total += 1
            c = which_chapter(r["chapters"], (s + e) / 2)
            if c and SCREEN_TITLE.search(c[1]):
                agree += 1

    L, w = [], None
    L = []
    w = L.append
    w("# Chapters - the free table of contents nothing was reading\n")
    w(f"| | |\n|---|---|")
    w(f"| descriptions on disk | **{n:,}** |")
    w(f"| satisfying YouTube's own chapter rule | **{len(have):,} "
      f"({len(have)/n:.1%})** |")
    w(f"| total chapters | **{total_ch:,}** |")
    w(f"| median chapters per video | "
      f"{sorted(len(r['chapters']) for r in have)[len(have)//2]} |")
    w(f"| chapters whose TITLE predicts screen content | **{screen_ch:,} "
      f"({screen_ch/total_ch:.1%})** |")
    w(f"| structural noise (intro/outro/sponsor) | {noise_ch:,} "
      f"({noise_ch/total_ch:.1%}) |")
    w(f"| videos already READ that have chapters | **{len(read_have)} of "
      f"{len(read)}** |")
    w("")
    w("The rule is implemented, not assumed: YouTube shows a chapter bar only "
      "when the first stamp is `0:00`, there are at least three, and they are "
      "at least 10 seconds apart. A description with timestamps that fails that "
      "test shows no chapters to a viewer, and **the difference between 'the "
      "author wrote a contents list' and 'the author mentioned some times' is "
      "exactly the distinction this programme keeps getting wrong in the other "
      "direction.**\n")

    if seg_total:
        w("## Do chapters agree with the readers' own `watch_segments`?\n")
        w(f"On the {len(read_have)} read videos that have chapters, "
          f"**{agree} of {seg_total} watch_segments ({agree/seg_total:.0%}) "
          "fall inside a chapter whose title predicts screen content.**\n")
        w("That is a cheap validation of a free signal against an expensive "
          "one: `watch_segments` cost a full model read of the transcript, and "
          "the chapter titles were sitting in a field that was already "
          "fetched.\n")

    w("## What the authors call their own screen sections\n")
    w("| word in a chapter title | chapters |\n|---|---|")
    for word, c in title_words.most_common(18):
        w(f"| {word} | {c} |")
    w("")

    w("## The immediate use: a searchable index with no transcript read\n")
    w("```bash\npython src/chapters.py --search \"results|p&l|live|backtest\"\n"
      "```\n")
    w("A chapter titled *'Backtest results'* or *'My live account'* is a "
      "**screen-content predictor**. The permitted frame sample sits at fixed "
      "25/50/75% positions and cannot be moved - but knowing which chapter each "
      "frame landed in turns a lottery ticket into a labelled observation, and "
      "that label is free.\n")

    w("## Worked example, on videos already read\n")
    for r in read_have[:8]:
        w(f"### `{r['video_id']}` {(r['title'] or '')[:64]}\n")
        for t, ti in r["chapters"][:10]:
            mark = ""
            if NOISE_TITLE.match(ti):
                mark = " *(noise)*"
            elif SCREEN_TITLE.search(ti):
                mark = " **<- screen**"
            w(f"- `{t//60:>3}m{t%60:02d}s` {ti[:72]}{mark}")
        # where the three permitted frames land
        if r["duration_s"]:
            w("")
            for frac, nm in ((0.25, "maxres1"), (0.50, "maxres2"),
                             (0.75, "maxres3")):
                at = float(r["duration_s"]) * frac
                c = which_chapter(r["chapters"], at)
                w(f"  - `{nm}` (~{int(at//60)}m{int(at%60):02d}s) lands in "
                  f"**{c[1][:56] if c else 'before the first chapter'}**")
        w("")

    out = corpora.REPORTS / "T7_chapters.md"
    out.write_text("\n".join(L), encoding="utf-8")
    (corpora.DATA / "chapters.json").write_text(
        json.dumps([{k: v for k, v in r.items() if k != "description"}
                    for r in have], indent=2), encoding="utf-8")
    print(f"  {len(have):,}/{n:,} videos have real chapters "
          f"({len(have)/n:.1%}), {total_ch:,} chapters, "
          f"{screen_ch/total_ch:.0%} screen-predictive")
    if seg_total:
        print(f"  watch_segments inside a screen-titled chapter: "
              f"{agree}/{seg_total} = {agree/seg_total:.0%}")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()
