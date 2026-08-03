"""STEP 1 -- select the 60 videos to read.

THE RULE (deterministic, seeded, re-runnable):

  1. ANCHOR   -- every PASSing video from Nates Tokens. Known-good, on-topic,
                 low-view. If the read cannot score these well, it cannot score.
  2. LONGEST  -- the single longest PASSing video in the corpus, whatever it is.
                 This is the compression test in 5c.
  3. STRATIFIED -- the remaining slots, filled round-robin across a grid of
                 (family bucket x view band) so no cell can dominate, sampled
                 without replacement with a fixed seed.

Family buckets are deliberately EXCLUSIVE, so an F1-only video is one that F2 and
F2B never found. Those are the videos needed for the 5b comparison and they are
exactly the ones it is tempting to skip, because they look less promising.

View bands are <1k / 1k-5k / 5k-50k / >50k. The 5k boundary matches the low-view
definition used throughout Phase 1, so 5b and 7b remain comparable.
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db_phase2  # noqa: E402
import db as _db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TARGET = 60
SEED = 20260802
NATES = "UCEFnH0KShNRHb-NMeurBxQQ"

BANDS = [("<1k", 0, 1_000), ("1k-5k", 1_000, 5_000),
         ("5k-50k", 5_000, 50_000), (">50k", 50_000, 10**12)]


def band(v):
    v = v or 0
    for name, lo, hi in BANDS:
        if lo <= v < hi:
            return name
    return ">50k"


def main():
    con = db_phase2.connect()
    rnd = random.Random(SEED)

    fam = {}
    for r in con.execute("SELECT DISTINCT video_id, family FROM retrieval_hits"):
        fam.setdefault(r["video_id"], set()).add(r["family"])

    rows = con.execute(
        """SELECT video_id, channel_id, channel_name, title, view_count, duration_s
           FROM videos WHERE gate_status='PASS' AND source='search'"""
    ).fetchall()
    pool = {}
    for r in rows:
        f = fam.get(r["video_id"], set())
        if not f:
            continue
        if f == {"F1"}:
            bucket = "F1_only"
        elif f == {"F2"}:
            bucket = "F2_only"
        elif f == {"F2B"}:
            bucket = "F2B_only"
        else:
            bucket = "multi"
        pool[r["video_id"]] = {
            "video_id": r["video_id"], "channel_id": r["channel_id"],
            "channel": r["channel_name"], "title": r["title"],
            "views": r["view_count"], "duration_s": r["duration_s"],
            "families": sorted(f), "bucket": bucket, "band": band(r["view_count"]),
        }

    print(f"eligible pool (PASS, retrieved by search): {len(pool)}\n")

    chosen = {}

    # 1 -- anchor
    for v in pool.values():
        if v["channel_id"] == NATES:
            chosen[v["video_id"]] = ("anchor", v)
    print(f"1. ANCHOR  Nates Tokens PASSing videos: {len(chosen)}")
    for _, v in chosen.values():
        print(f"     {v['views'] or '?':>7} views  {v['band']:<7} {v['title'][:52]}")

    # 2 -- longest
    longest = max((v for v in pool.values() if v["duration_s"]),
                  key=lambda v: v["duration_s"])
    if longest["video_id"] not in chosen:
        chosen[longest["video_id"]] = ("longest", longest)
    print(f"\n2. LONGEST {longest['duration_s']/60:.1f} min  "
          f"{longest['channel']} -- {longest['title'][:48]}")

    # 3 -- stratified round robin
    cells = {}
    for v in pool.values():
        if v["video_id"] in chosen:
            continue
        cells.setdefault((v["bucket"], v["band"]), []).append(v)
    for k in cells:
        rnd.shuffle(cells[k])

    order = sorted(cells.keys())
    print(f"\n3. STRATIFIED across {len(order)} non-empty cells, "
          f"{TARGET - len(chosen)} slots")
    i = 0
    while len(chosen) < TARGET and any(cells.values()):
        k = order[i % len(order)]
        i += 1
        if cells[k]:
            v = cells[k].pop()
            chosen[v["video_id"]] = ("stratified", v)

    # ---- persist ----
    con.execute("DELETE FROM read_set")
    for vid, (rule, v) in chosen.items():
        con.execute(
            "INSERT INTO read_set (video_id, selection_rule, view_band,"
            " family_bucket, selected_utc) VALUES (?,?,?,?,?)",
            (vid, rule, v["band"], v["bucket"], _db.now()))
    con.commit()

    # ---- report ----
    print(f"\nSELECTED {len(chosen)} videos\n")
    print("  by selection rule:")
    for rule in ("anchor", "longest", "stratified"):
        n = sum(1 for r, _ in chosen.values() if r == rule)
        print(f"    {rule:<12} {n}")

    print("\n  by family bucket x view band:")
    grid = {}
    for _, v in chosen.values():
        grid[(v["bucket"], v["band"])] = grid.get((v["bucket"], v["band"]), 0) + 1
    buckets = ["F1_only", "F2_only", "F2B_only", "multi"]
    print(f"    {'':<10}" + "".join(f"{b:>9}" for b, _, _ in BANDS) + f"{'total':>8}")
    for b in buckets:
        row = [grid.get((b, band_name), 0) for band_name, _, _ in BANDS]
        print(f"    {b:<10}" + "".join(f"{x:>9}" for x in row) + f"{sum(row):>8}")
    tot = [sum(grid.get((b, bn), 0) for b in buckets) for bn, _, _ in BANDS]
    print(f"    {'TOTAL':<10}" + "".join(f"{x:>9}" for x in tot) + f"{sum(tot):>8}")

    lows = sum(1 for _, v in chosen.values() if (v["views"] or 0) < 5000)
    print(f"\n  under 5k views: {lows}/{len(chosen)} ({100*lows/len(chosen):.0f}%)")
    mins = sum(v["duration_s"] or 0 for _, v in chosen.values()) / 60
    print(f"  total runtime : {mins:.0f} min ({mins/60:.1f} h) across "
          f"{len(chosen)} videos")
    print(f"  distinct channels: "
          f"{len({v['channel_id'] for _, v in chosen.values()})}")

    (ROOT / "reports" / "read_set.json").write_text(json.dumps(
        [{"rule": r, **v} for r, v in chosen.values()], indent=2), encoding="utf-8")
    print(f"\nwrote reports/read_set.json and the read_set table")
    con.close()


if __name__ == "__main__":
    main()
