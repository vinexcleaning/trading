"""Phase 2 channel expansion: a SPECIALISATION bar, not a count.

Phase 1 expanded any channel with >=2 videos passing all gates. That admitted
Bloomberg Television, OddsJam Sports Betting Picks and DGFantasy - Prizepicks,
each contributing ~200 uploads of mostly irrelevant material, because a big
generic channel trips a low absolute count by volume alone.

New rule: of the videos RETRIEVED from that channel, >=50% must have passed G3.
That measures what fraction of the channel's retrieved output is on topic, which
is specialisation, and is invariant to channel size.

"Passed G3" means the video was not dropped by either G3 branch. STALE videos
count as G3 passes -- being old is not being off topic.

A floor of MIN_RETRIEVED is kept so the ratio is computed on more than one video;
a channel with a single retrieved video is at 0% or 100% by construction and the
ratio carries no information. The no-floor counterfactual is reported so the
floor's effect is visible rather than assumed.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402
import retrieval  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MIN_RETRIEVED = 2
MIN_G3_SHARE = 0.50
CAP = 200
G3_FAIL = ("DROP_G3_OFF_TOPIC", "DROP_G3_DISCRETIONARY")


def channel_table(con):
    rows = con.execute(
        """SELECT channel_id, channel_name,
                  COUNT(*) AS retrieved,
                  SUM(CASE WHEN gate_status IN ('DROP_G3_OFF_TOPIC',
                                                'DROP_G3_DISCRETIONARY')
                           THEN 0 ELSE 1 END) AS g3_ok,
                  SUM(CASE WHEN gate_status='PASS' THEN 1 ELSE 0 END) AS passing
           FROM videos
           WHERE source='search' AND channel_id IS NOT NULL
             AND gate_status IS NOT NULL AND gate_status != 'DROP_META'
           GROUP BY channel_id"""
    ).fetchall()
    out = []
    for r in rows:
        share = r["g3_ok"] / r["retrieved"] if r["retrieved"] else 0.0
        out.append({
            "channel_id": r["channel_id"], "name": r["channel_name"] or "?",
            "retrieved": r["retrieved"], "g3_ok": r["g3_ok"],
            "passing": r["passing"], "g3_share": share,
        })
    return out


def main(apply=True):
    con = db.connect()
    tbl = channel_table(con)

    old_rule = {c["channel_id"] for c in tbl if c["passing"] >= 2}
    new_rule = {c["channel_id"] for c in tbl
                if c["retrieved"] >= MIN_RETRIEVED and c["g3_share"] >= MIN_G3_SHARE}
    no_floor = {c["channel_id"] for c in tbl if c["g3_share"] >= MIN_G3_SHARE}

    print("CHANNEL EXPANSION -- old count rule vs new specialisation bar\n")
    print(f"  channels with >=1 retrieved+gated video : {len(tbl)}")
    print(f"  OLD rule (>=2 passing all gates)        : {len(old_rule)}")
    print(f"  NEW rule (>=2 retrieved, >=50% pass G3) : {len(new_rule)}")
    print(f"     counterfactual, no >=2 floor         : {len(no_floor)} "
          f"(the floor suppresses {len(no_floor) - len(new_rule)} single-video channels)")
    print(f"  pruned by the new bar                   : {len(old_rule - new_rule)}")
    print(f"  newly admitted by the new bar           : {len(new_rule - old_rule)}")

    by_id = {c["channel_id"]: c for c in tbl}
    print("\n  PRUNED (were expanded, now fail the specialisation bar):")
    for cid in sorted(old_rule - new_rule, key=lambda c: -by_id[c]["retrieved"]):
        c = by_id[cid]
        print(f"    {c['name'][:38]:<40} {c['g3_ok']:>2}/{c['retrieved']:<3} on topic "
              f"({100*c['g3_share']:>5.1f}%)  {c['passing']} passing")

    admitted = sorted(new_rule - old_rule, key=lambda c: -by_id[c]["g3_share"])
    print(f"\n  NEWLY ADMITTED (first 12 of {len(admitted)}):")
    for cid in admitted[:12]:
        c = by_id[cid]
        print(f"    {c['name'][:38]:<40} {c['g3_ok']:>2}/{c['retrieved']:<3} on topic "
              f"({100*c['g3_share']:>5.1f}%)  {c['passing']} passing")

    # ---- rows currently in the DB from now-pruned channels ----
    pruned = old_rule - new_rule
    n_rows = 0
    if pruned:
        marks = ",".join("?" * len(pruned))
        n_rows = con.execute(
            f"""SELECT COUNT(*) c FROM videos WHERE source='channel_expansion'
                AND channel_id IN ({marks})""", tuple(pruned)
        ).fetchone()["c"]
    total_exp = con.execute(
        "SELECT COUNT(*) c FROM videos WHERE source='channel_expansion'"
    ).fetchone()["c"]
    print(f"\n  expansion rows in DB                : {total_exp}")
    print(f"  rows from pruned channels           : {n_rows} "
          f"({100*n_rows/total_exp:.1f}% of the expansion corpus)")

    if not apply:
        con.close()
        return

    # Delete rows from pruned channels. Only ever touches channel_expansion rows;
    # a search-retrieved video is evidence and is never deleted.
    if pruned:
        marks = ",".join("?" * len(pruned))
        con.execute(
            f"""DELETE FROM videos WHERE source='channel_expansion'
                AND channel_id IN ({marks})""", tuple(pruned))
        con.execute(
            f"UPDATE channels SET expanded=0 WHERE channel_id IN ({marks})",
            tuple(pruned))
        con.commit()
        print(f"  deleted {n_rows} rows from {len(pruned)} pruned channels")

    # Expand the newly admitted ones.
    r = retrieval.Retriever(con)
    todo = [cid for cid in new_rule
            if not (con.execute("SELECT expanded FROM channels WHERE channel_id=?",
                                (cid,)).fetchone() or {"expanded": 0})["expanded"]]
    print(f"\n  expanding {len(todo)} channels not already expanded...")
    added = 0
    for cid in todo:
        c = by_id[cid]
        try:
            info, entries = r.channel_uploads(cid, cap=CAP)
        except Exception as exc:  # noqa: BLE001
            print(f"    {c['name'][:36]:<38} FAILED {type(exc).__name__}")
            continue
        views = sorted(e["view_count"] for e in entries
                       if e.get("view_count") is not None)
        med = views[len(views) // 2] if views else None
        con.execute(
            """INSERT INTO channels (channel_id, name, subscribers, median_views,
                   upload_count, expanded, first_seen_utc, last_refresh_utc)
               VALUES (?,?,?,?,?,1,?,?)
               ON CONFLICT(channel_id) DO UPDATE SET
                   name=excluded.name, subscribers=excluded.subscribers,
                   median_views=excluded.median_views,
                   upload_count=excluded.upload_count, expanded=1,
                   last_refresh_utc=excluded.last_refresh_utc""",
            (cid, info.get("channel") or c["name"], info.get("channel_follower_count"),
             med, len(entries), db.now(), db.now()))
        new_here = 0
        for e in entries:
            if con.execute("SELECT 1 FROM videos WHERE video_id=?",
                           (e["id"],)).fetchone():
                continue
            con.execute(
                """INSERT INTO videos (video_id, channel_id, channel_name, title,
                       view_count, duration_s, source, created_utc)
                   VALUES (?,?,?,?,?,?,'channel_expansion',?)""",
                (e["id"], cid, info.get("channel") or c["name"], e.get("title"),
                 e.get("view_count"), e.get("duration"), db.now()))
            new_here += 1
        added += new_here
        con.commit()
        print(f"    {(info.get('channel') or '?')[:36]:<38} "
              f"{100*c['g3_share']:>5.1f}% on topic -> {len(entries):>3} uploads, "
              f"{new_here:>3} new")

    final = con.execute("SELECT COUNT(*) c FROM videos").fetchone()["c"]
    final_exp = con.execute(
        "SELECT COUNT(*) c FROM videos WHERE source='channel_expansion'").fetchone()["c"]
    print(f"\n  expansion corpus: {total_exp} -> {final_exp}   total videos: {final}")

    (ROOT / "reports" / "expansion_v2.json").write_text(json.dumps({
        "min_retrieved": MIN_RETRIEVED, "min_g3_share": MIN_G3_SHARE,
        "channels_old_rule": len(old_rule), "channels_new_rule": len(new_rule),
        "no_floor_counterfactual": len(no_floor),
        "pruned": len(pruned), "newly_admitted": len(new_rule - old_rule),
        "rows_deleted": n_rows, "rows_added": added,
        "expansion_before": total_exp, "expansion_after": final_exp,
        "pruned_channels": [by_id[c]["name"] for c in pruned],
    }, indent=2), encoding="utf-8")
    con.close()


if __name__ == "__main__":
    main(apply="--dry-run" not in sys.argv)
