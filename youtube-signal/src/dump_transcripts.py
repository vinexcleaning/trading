"""Print selected transcripts, timestamped, for Claude to read directly in chat.

This is the free path. Instead of paying an API to read transcripts, the
transcripts are printed here and read in the session that is already running.
Same model quality or better, no key, no cost. The limit is context, not money.

Usage:  python src/dump_transcripts.py <video_id> [<video_id> ...]
        python src/dump_transcripts.py --top 3     (top N by proxy score)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db_phase2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GROUP_SECONDS = 30          # collapse snippets into ~30s blocks to save context


def dump(con, vid):
    r = con.execute(
        """SELECT v.title, v.channel_name, v.view_count, v.duration_s,
                  v.upload_date, t.snippets_json
           FROM videos v JOIN transcripts t ON t.video_id=v.video_id
           WHERE v.video_id=?""", (vid,)).fetchone()
    if not r:
        print(f"### {vid}: no cached transcript")
        return
    snips = json.loads(r["snippets_json"])
    print("=" * 78)
    print(f"VIDEO {vid}")
    print(f"TITLE   {r['title']}")
    print(f"CHANNEL {r['channel_name']}")
    print(f"VIEWS   {r['view_count']:,}" if r["view_count"] is not None else "VIEWS   ?")
    print(f"LENGTH  {(r['duration_s'] or 0)/60:.0f} min   UPLOADED {r['upload_date']}")
    print(f"URL     https://www.youtube.com/watch?v={vid}")
    print("=" * 78)

    buf, block_start = [], None
    for s in snips:
        if block_start is None:
            block_start = s["start"]
        buf.append(s["text"].strip())
        if s["start"] - block_start >= GROUP_SECONDS:
            print(f"[{int(block_start)}] " + " ".join(buf))
            buf, block_start = [], None
    if buf:
        print(f"[{int(block_start or 0)}] " + " ".join(buf))
    print()


def main():
    con = db_phase2.connect()
    args = sys.argv[1:]
    if args and args[0] == "--top":
        n = int(args[1]) if len(args) > 1 else 3
        rank = json.loads(
            (ROOT / "reports" / "substance_ranking.json").read_text(encoding="utf-8"))
        ids = [x["video_id"] for x in rank[:n]]
    else:
        ids = args
    for vid in ids:
        dump(con, vid)
    con.close()


if __name__ == "__main__":
    main()
