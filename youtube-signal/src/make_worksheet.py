"""Blind calibration worksheet: 15 videos, no scores shown.

The point is to capture the user's judgment BEFORE he has seen any machine score,
so the two can be compared without the machine anchoring him.

This run is more blind than intended, and that is an accident worth keeping:
Step 2 never ran (no ANTHROPIC_API_KEY), so there are no machine scores yet. The
worksheet is therefore filled in first and the scores computed afterwards --
which is the stronger ordering. Whatever he writes cannot have been influenced.

Selection: 15 of the 60-video read set, spread across view bands and family
buckets, seeded so the same 15 come back on a re-run. Ordering is shuffled so the
strata are not readable from the layout.
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db_phase2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
N = 15
SEED = 4242


def hms(sec):
    if not sec:
        return "?"
    sec = int(sec)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def main():
    con = db_phase2.connect()
    rows = con.execute(
        """SELECT r.video_id, r.view_band, r.family_bucket, r.selection_rule,
                  v.title, v.channel_name, v.view_count, v.duration_s
           FROM read_set r JOIN videos v ON v.video_id = r.video_id"""
    ).fetchall()
    if not rows:
        print("read_set empty -- run select_read_set.py first")
        raise SystemExit(1)

    rnd = random.Random(SEED)
    cells = {}
    for r in rows:
        cells.setdefault((r["family_bucket"], r["view_band"]), []).append(dict(r))
    for k in cells:
        cells[k].sort(key=lambda x: x["video_id"])
        rnd.shuffle(cells[k])

    order = sorted(cells.keys())
    picked, i = [], 0
    while len(picked) < N and any(cells.values()):
        k = order[i % len(order)]
        i += 1
        if cells[k]:
            picked.append(cells[k].pop())
    rnd.shuffle(picked)

    lines = [
        "# Blind calibration worksheet — 2026-08-02",
        "",
        "15 videos from the Phase 2 read set. **No machine scores are shown, and at",
        "the time this was generated none existed** — Step 2 could not run without an",
        "API key. So your marks here cannot be anchored by anything the pipeline thinks.",
        "",
        "For each: from the title, channel, view count and a quick skim of the video,",
        "mark one box. Don't watch them properly — a skim is the point.",
        "",
        "- **G** — Good. Real specifics: named tools, actual numbers, a mechanism.",
        "- **M** — Middle. Some substance, mostly generic.",
        "- **K** — Marketing. Selling something; the content is the pitch.",
        "",
        "Add a few words on why where you can be bothered. The disagreements are the",
        "useful part, so please don't smooth them out.",
        "",
        "---",
        "",
    ]
    for n, p in enumerate(picked, 1):
        views = f"{p['view_count']:,}" if p["view_count"] is not None else "?"
        lines += [
            f"### {n}. {p['title']}",
            "",
            f"- **Channel:** {p['channel_name']}",
            f"- **Views:** {views}  |  **Length:** {hms(p['duration_s'])}",
            f"- **Link:** https://www.youtube.com/watch?v={p['video_id']}",
            "",
            "  `[ ] G` &nbsp;&nbsp; `[ ] M` &nbsp;&nbsp; `[ ] K`",
            "",
            "  Why: ",
            "",
            "---",
            "",
        ]
    (ROOT / "reports" / "worksheet_2026-08-02.md").write_text(
        "\n".join(lines), encoding="utf-8")

    # Stored separately so the answer key never sits next to the questions.
    (ROOT / "reports" / "worksheet_key_2026-08-02.json").write_text(json.dumps(
        [{"n": n, "video_id": p["video_id"], "view_band": p["view_band"],
          "family_bucket": p["family_bucket"], "selection_rule": p["selection_rule"],
          "machine_s": None, "machine_h": None, "machine_verdict": None}
         for n, p in enumerate(picked, 1)], indent=2), encoding="utf-8")

    print(f"wrote reports/worksheet_2026-08-02.md ({len(picked)} videos)")
    print("wrote reports/worksheet_key_2026-08-02.json "
          "(strata + empty score slots, kept separate)\n")
    for n, p in enumerate(picked, 1):
        v = f"{p['view_count']:,}" if p["view_count"] is not None else "?"
        print(f"  {n:>2}. {v:>9} views  {p['family_bucket']:<9} "
              f"{hms(p['duration_s']):>7}  {p['title'][:44]}")
    con.close()


if __name__ == "__main__":
    main()
