"""Capture video DESCRIPTIONS. This was a real gap, caught by the user.

Why it matters more than it sounds:

The transcript is SPOKEN audio, auto-captioned. Product names get garbled there --
"Kreo" was transcribed "Creo", and a repo name came through so mangled that a
guessed URL 404'd and was nearly logged as a dead tool. The description is TYPED
by the creator and contains the literal, exact URL. It is the authoritative source
for every link in the video, and we were throwing it away.

It also carries things the audio never says out loud:
  * affiliate and referral disclosures (H5, is_referral_link)
  * discount codes and countdowns (H8 urgency)
  * chapter timestamps
  * repo, docs and dataset links the creator never reads aloud

Backfills read videos first, since those are the ones with extracted tools whose
URLs can now be corrected.
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from yt_dlp import YoutubeDL  # noqa: E402

import db_phase2  # noqa: E402

PAUSE_S = 1.5
URL_RE = re.compile(r"https?://[^\s<>\"')]+")
AFFIL_RE = re.compile(
    r"affiliate|referral|sponsor|paid promotion|commission|discount code|"
    r"promo code|use code|my link|partner link", re.I)


def ensure_columns(con):
    for stmt in ("ALTER TABLE videos ADD COLUMN description TEXT",
                 "ALTER TABLE videos ADD COLUMN description_urls TEXT",
                 "ALTER TABLE videos ADD COLUMN description_has_affiliate INTEGER",
                 "ALTER TABLE videos ADD COLUMN description_fetched_utc TEXT"):
        try:
            con.execute(stmt)
        except Exception:  # noqa: BLE001 - column exists
            pass
    con.commit()


def fetch_description(vid):
    with YoutubeDL({"quiet": True, "skip_download": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}",
                                download=False)
    return info.get("description") or ""


def main():
    con = db_phase2.connect()
    ensure_columns(con)

    only_read = "--read-only" in sys.argv or "--read" in sys.argv
    limit = 0
    for a in sys.argv:
        if a.startswith("--limit="):
            limit = int(a.split("=")[1])

    if only_read:
        q = ("SELECT v.video_id, v.title FROM videos v JOIN scores s "
             "ON s.video_id=v.video_id WHERE v.description IS NULL")
    else:
        q = ("SELECT video_id, title FROM videos WHERE description IS NULL "
             "AND video_id IN (SELECT video_id FROM transcripts)")
    rows = con.execute(q).fetchall()
    if limit:
        rows = rows[:limit]
    print(f"fetching descriptions for {len(rows)} videos\n")

    n_urls = n_affil = 0
    for i, r in enumerate(rows, 1):
        try:
            desc = fetch_description(r["video_id"])
        except Exception as exc:  # noqa: BLE001
            print(f"  {r['video_id']}  FAILED {type(exc).__name__}")
            con.execute("UPDATE videos SET description='', description_fetched_utc=?"
                        " WHERE video_id=?", (db_phase2.db.now(), r["video_id"]))
            continue
        urls = sorted({u.rstrip(".,);") for u in URL_RE.findall(desc)})
        affil = bool(AFFIL_RE.search(desc))
        n_urls += len(urls)
        n_affil += int(affil)
        con.execute(
            "UPDATE videos SET description=?, description_urls=?,"
            " description_has_affiliate=?, description_fetched_utc=? WHERE video_id=?",
            (desc, "\n".join(urls), int(affil), db_phase2.db.now(), r["video_id"]))
        con.commit()
        flag = "  [AFFILIATE/PROMO LANGUAGE]" if affil else ""
        print(f"  {i:>3}/{len(rows)}  {r['title'][:44]:<46} "
              f"{len(desc):>5} chars, {len(urls):>2} urls{flag}")
        time.sleep(PAUSE_S)

    print(f"\n  {n_urls} URLs captured, {n_affil} videos with affiliate/promo wording")
    con.close()


if __name__ == "__main__":
    main()
