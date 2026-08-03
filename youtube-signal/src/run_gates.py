"""STEP 6 -- apply G1/G2/G3 to the union set, then expand qualifying channels.

Resumable: only videos with gate_status IS NULL are processed, so a block or a
crash costs nothing already done.

Cost note. upload_date (needed by G2) is not carried by yt-dlp's flat extraction,
so each video needs one full extraction. That same extraction already resolves the
caption tracks, so the transcript comes from it at no extra request --
youtube-transcript-api is used only as the fallback. One video = one paced fetch,
not two.
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402
import gates  # noqa: E402
import retrieval  # noqa: E402
import transcripts as T  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EXPANSION_CAP = 200
MIN_PASSING_FOR_EXPANSION = 2


def get_transcript(info, video_id, r):
    """Caption track from the extraction we already paid for; fall back to
    youtube-transcript-api only if yt-dlp exposed no english track."""
    try:
        url, ext, bucket, lang = T._pick_caption_track(info, ["en", "en-US", "en-GB"])
        if url:
            req = urllib.request.Request(url, headers={"User-Agent": T._UA})
            raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            snips = T._parse_json3(raw) if ext == "json3" else T._parse_vtt(raw)
            if snips:
                return snips, "yt-dlp", None
    except Exception as exc:  # noqa: BLE001
        pass
    snips, via, errors = r.transcript(video_id, info=None)
    return snips, via, errors


def main():
    con = db.connect()
    r = retrieval.Retriever(con)

    todo = con.execute(
        "SELECT video_id, title FROM videos WHERE source='search' AND gate_status IS NULL"
    ).fetchall()
    print(f"to gate: {len(todo)} videos")

    counts, t0, blocked = {}, time.time(), None
    for i, row in enumerate(todo, 1):
        vid = row["video_id"]
        try:
            meta = r.video_metadata(vid)
        except retrieval.BlockedError as exc:
            blocked = str(exc)
            break
        except Exception as exc:  # noqa: BLE001
            reason = f"{type(exc).__name__}: {str(exc).strip().splitlines()[0][:120]}"
            con.execute("UPDATE videos SET gate_status='DROP_META' WHERE video_id=?", (vid,))
            con.execute(
                "INSERT OR REPLACE INTO drops (video_id, gate, reason, ts_utc)"
                " VALUES (?,?,?,?)", (vid, "META", reason, db.now())
            )
            counts["DROP_META"] = counts.get("DROP_META", 0) + 1
            if i % 10 == 0:
                con.commit()
            continue

        try:
            snips, via, _err = get_transcript(meta["info"], vid, r)
        except retrieval.BlockedError as exc:
            blocked = str(exc)
            break

        video = {"title": meta["title"], "age_months": meta["age_months"]}
        status, detail = gates.classify(video, snips)
        counts[status] = counts.get(status, 0) + 1

        if snips:
            con.execute(
                "INSERT OR REPLACE INTO transcripts (video_id, via, n_snippets,"
                " n_words, snippets_json, fetched_utc) VALUES (?,?,?,?,?,?)",
                (vid, via, len(snips),
                 sum(len(s["text"].split()) for s in snips),
                 json.dumps(snips, separators=(",", ":")), db.now()),
            )

        con.execute(
            """UPDATE videos SET channel_id=COALESCE(?, channel_id),
                   channel_name=COALESCE(?, channel_name), title=COALESCE(?, title),
                   view_count=COALESCE(?, view_count), duration_s=COALESCE(?, duration_s),
                   upload_date=?, age_months=?, transcript_words=?, transcript_via=?,
                   is_stale=?, gate_status=?, metadata_fetched=1
               WHERE video_id=?""",
            (
                meta["channel_id"], meta["channel_name"], meta["title"],
                meta["view_count"], meta["duration_s"], meta["upload_date"],
                meta["age_months"],
                sum(len(s["text"].split()) for s in snips) if snips else 0,
                via,
                1 if status == "STALE_G2" else 0,
                status, vid,
            ),
        )
        if status.startswith("DROP") or status == "STALE_G2":
            gate = ("G1" if "G1" in status else "G3" if "G3" in status else "G2")
            reason = {
                "DROP_G1_NO_TRANSCRIPT": "no english transcript on either path",
                "DROP_G3_OFF_TOPIC": f"g3 rule: {detail.get('g3', {}).get('rule')}",
                "DROP_G2_NO_DATE": "no upload_date available",
                "STALE_G2": f"age {detail.get('age_months')} mo > {gates.STALE_MONTHS}",
            }.get(status, status)
            con.execute(
                "INSERT OR REPLACE INTO drops (video_id, gate, reason, ts_utc)"
                " VALUES (?,?,?,?)", (vid, gate, reason, db.now())
            )

        if i % 10 == 0:
            con.commit()
        if i % 25 == 0:
            rate = (time.time() - t0) / i
            left = (len(todo) - i) * rate / 60
            print(f"  {i}/{len(todo)}  {rate:.1f}s/video  ~{left:.0f} min left   {counts}")
    con.commit()

    print(f"\ngate census: {counts}")
    if blocked:
        print(f"\n*** HALTED ON BLOCK: {blocked}")
        print(f"block events: {r.block_events}")

    # ---------- channel expansion ----------
    # Phase 2 replaced this count rule with src/expansion_v2.py. Skip it here so
    # the two rules never both run.
    if "--no-expansion" in sys.argv:
        print("\n(skipping legacy count-based expansion; use expansion_v2.py)")
        (ROOT / "reports" / "step6_gates.json").write_text(
            json.dumps({"gate_census": counts, "blocked": blocked,
                        "throttle": r.throttle_report()}, indent=2, default=str),
            encoding="utf-8")
        con.close()
        return

    print("\n===== CHANNEL EXPANSION =====")
    qualifying = con.execute(
        """SELECT channel_id, channel_name, COUNT(*) n FROM videos
           WHERE gate_status='PASS' AND channel_id IS NOT NULL
           GROUP BY channel_id HAVING n >= ? ORDER BY n DESC""",
        (MIN_PASSING_FOR_EXPANSION,),
    ).fetchall()
    print(f"channels with >={MIN_PASSING_FOR_EXPANSION} passing videos: {len(qualifying)}")

    expanded, added = 0, 0
    for row in qualifying:
        cid = row["channel_id"]
        done = con.execute(
            "SELECT expanded FROM channels WHERE channel_id=?", (cid,)
        ).fetchone()
        if done and done["expanded"]:
            continue
        try:
            info, entries = r.channel_uploads(cid, cap=EXPANSION_CAP)
        except Exception as exc:  # noqa: BLE001
            print(f"  {row['channel_name'][:38]:<40} EXPANSION FAILED "
                  f"{type(exc).__name__}: {str(exc)[:60]}")
            continue
        views = [e["view_count"] for e in entries if e.get("view_count") is not None]
        views.sort()
        med = views[len(views) // 2] if views else None
        con.execute(
            """INSERT INTO channels (channel_id, name, subscribers, median_views,
                   upload_count, expanded, first_seen_utc, last_refresh_utc)
               VALUES (?,?,?,?,?,1,?,?)
               ON CONFLICT(channel_id) DO UPDATE SET
                   name=excluded.name, subscribers=excluded.subscribers,
                   median_views=excluded.median_views, upload_count=excluded.upload_count,
                   expanded=1, last_refresh_utc=excluded.last_refresh_utc""",
            (cid, info.get("channel") or row["channel_name"],
             info.get("channel_follower_count"), med, len(entries), db.now(), db.now()),
        )
        new_here = 0
        for e in entries:
            cur = con.execute(
                "SELECT 1 FROM videos WHERE video_id=?", (e["id"],)
            ).fetchone()
            if cur:
                continue
            con.execute(
                """INSERT INTO videos (video_id, channel_id, channel_name, title,
                       view_count, duration_s, source, created_utc)
                   VALUES (?,?,?,?,?,?,'channel_expansion',?)""",
                (e["id"], cid, info.get("channel") or row["channel_name"],
                 e.get("title"), e.get("view_count"), e.get("duration"), db.now()),
            )
            new_here += 1
        added += new_here
        expanded += 1
        con.commit()
        print(f"  {(info.get('channel') or '?')[:38]:<40} {row['n']:>2} passing -> "
              f"{len(entries):>3} uploads, {new_here:>3} new")

    print(f"\nexpanded {expanded} channels, added {added} new video rows "
          f"(metadata only; transcripts are Phase 2)")

    out = {
        "gate_census": counts,
        "blocked": blocked,
        "block_events": r.block_events,
        "channels_expanded": expanded,
        "videos_added_by_expansion": added,
        "throttle": r.throttle_report(),
    }
    (ROOT / "reports" / "step6_gates.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    print(f"wrote {ROOT / 'reports' / 'step6_gates.json'}")
    con.close()


if __name__ == "__main__":
    main()
