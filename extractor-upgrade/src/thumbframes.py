"""PERMITTED frame acquisition. This overturns a conclusion I published today.

`FINDINGS_T2.md` said "frame acquisition from YouTube is closed". **That was too
strong and it is corrected here.** What is closed is *arbitrary-timestamp*
acquisition, which needs the media stream. What is OPEN is this:

    https://i.ytimg.com/vi/<video_id>/maxres1.jpg     1280x720, ~110 KB
    https://i.ytimg.com/vi/<video_id>/maxres2.jpg
    https://i.ytimg.com/vi/<video_id>/maxres3.jpg

Those are **auto-extracted video frames at roughly 25%, 50% and 75% of the
runtime** - not the uploader's designed thumbnail, which is `maxresdefault`.

Why it is permitted, checked rather than assumed:

    i.ytimg.com/robots.txt   User-agent: *
                             Disallow: /sb/          <- storyboards only

`/sb/` is the storyboard path and is forbidden. **`/vi/` is not mentioned**, so
a generic agent is permitted on it. Compare with the routes that ARE closed:

    youtube.com          Disallow: /get_video /get_video_info /file_download
                                  /youtubei/ /api/
    *.googlevideo.com    Disallow: /            <- ALL media hosts, checked on
                                                   three of them

So the media stream is forbidden at every hop, including through a third-party
downloader, which fetches from `googlevideo.com` on your behalf - the same act
with an extra hop, which is the reasoning `social-signal` already applied to X.
But three full-resolution frames per video are simply allowed, and they are
enough to read code, a terminal, a dashboard or an account balance.

    python src/thumbframes.py --all          every scored video
    python src/thumbframes.py --id VIDEO_ID
    python src/thumbframes.py --read-set     the 38 that have been read

Disk: 3 frames x ~110 KB = ~330 KB per video. The whole 1,200-video corpus
would be ~400 MB. `--max-mb` caps it and `prune()` deletes frames once their
evidence row is filled, per the standing instruction that images are ephemeral
and transcripts are not.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpora  # noqa: E402
import frames as F  # noqa: E402

UA = "extractor-upgrade/1.0 (+trading repo; permitted /vi/ frames)"
FRAMES = corpora.HERE.parent / "frames"
EVIDENCE = corpora.DATA / "screen_evidence.json"

# name -> nominal position through the runtime. YouTube generates 1/2/3 at
# roughly the quarter points; the exact offsets are not published, so the
# fraction is recorded as APPROXIMATE and never used as if it were a timestamp.
VARIANTS = [("maxres1", 0.25), ("maxres2", 0.50), ("maxres3", 0.75)]
FALLBACK = [("sd1", 0.25), ("sd2", 0.50), ("sd3", 0.75)]


def fetch(vid: str, out_dir: Path, pace: float = 0.25):
    """Highest permitted resolution, with a documented fallback.

    `maxres*` exists only when the source was uploaded at >=720p. `sd*`
    (640x480) is the fallback and is still readable for a terminal.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    got = []
    for names in (VARIANTS, FALLBACK):
        got = []
        for name, frac in names:
            p = out_dir / f"{name}.jpg"
            if p.exists() and p.stat().st_size > 2000:
                got.append((p, frac, name))
                continue
            url = f"https://i.ytimg.com/vi/{vid}/{name}.jpg"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=25) as r:
                    b = r.read()
            except urllib.error.HTTPError:
                b = b""
            except Exception:
                b = b""
            # A 120x90 placeholder comes back when the real frame is absent.
            if len(b) > 2000:
                p.write_bytes(b)
                got.append((p, frac, name))
            time.sleep(pace)
        if len(got) == 3:
            return got
    return got


def spoken_at(corpus: str, vid: str, frac: float, window: int = 25):
    """What the transcript says around that fraction of the runtime.

    The frame position is APPROXIMATE, so the window is deliberately wide -
    +/-25 s - and the report says so. Pinning a screen claim to a spoken
    sentence more tightly than the source supports is the same error as
    quoting an n you did not measure.
    """
    con = corpora.ro(corpus)
    row = con.execute("SELECT duration_s FROM videos WHERE video_id = ?",
                      (vid,)).fetchone()
    t = con.execute("SELECT snippets_json FROM transcripts WHERE video_id = ?",
                    (vid,)).fetchone()
    con.close()
    if not row or not row["duration_s"] or not t:
        return 0.0, ""
    at = float(row["duration_s"]) * frac
    snips = json.loads(t["snippets_json"])
    txt = " ".join(s["text"] for s in snips
                   if at - window <= float(s["start"]) <= at + window)
    return at, " ".join(txt.split())


def scored_videos(read_only=True):
    out = []
    for corpus in ("yt", "yt_kalshi"):
        con = corpora.ro(corpus)
        q = ("SELECT s.video_id, v.title, v.channel_name, v.duration_s "
             "FROM scores s JOIN videos v ON v.video_id = s.video_id"
             if read_only else
             "SELECT v.video_id, v.title, v.channel_name, v.duration_s "
             "FROM videos v JOIN transcripts t ON t.video_id = v.video_id")
        for r in con.execute(q):
            out.append((corpus, dict(r)))
        con.close()
    return out


def sheet_for(corpus: str, vid: str, title: str = ""):
    d = FRAMES / vid
    got = fetch(vid, d)
    if len(got) < 2:
        return None, []
    rows, labels, paths = [], [], []
    for p, frac, name in got:
        at, spoken = spoken_at(corpus, vid, frac)
        flat, why = F.is_flat(p)
        labels.append(f"{name} ~{int(at//60)}m{int(at%60):02d}s"
                      + ("  [FLAT]" if flat else ""))
        paths.append(p)
        rows.append(F.ScreenEvidence(
            video_id=vid, corpus=corpus, t=round(at, 1), frame=str(p),
            cue_kind=f"permitted_thumb:{name}", spoken=spoken[:500],
            note="frame position is APPROXIMATE (~25/50/75% of runtime); "
                 "spoken window is +/-25 s"))
    sheet = F.contact(paths, d / "sheet.jpg", cols=3, tile_w=760, labels=labels)
    return sheet, rows


def prune(keep_evidence=True):
    """Delete the frame images, keep the evidence rows.

    The standing instruction: pull what you need out of an image, then delete
    it. Transcripts are kept because they are text and cost nothing; frames are
    ephemeral because they are not.
    """
    n = size = 0
    for p in FRAMES.rglob("*.jpg"):
        if "_selftest" in p.parts:
            continue
        size += p.stat().st_size
        p.unlink()
        n += 1
    return n, size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id")
    ap.add_argument("--read-set", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--corpus", default="yt")
    ap.add_argument("--max-mb", type=float, default=600.0)
    ap.add_argument("--prune", action="store_true",
                    help="delete every frame image, keep the evidence rows")
    a = ap.parse_args()

    if a.prune:
        n, size = prune()
        print(f"  deleted {n} frames, {size/1e6:.1f} MB; "
              f"evidence rows in {EVIDENCE} kept")
        return

    if a.id:
        targets = [(a.corpus, {"video_id": a.id, "title": "", "channel_name": ""})]
    else:
        targets = scored_videos(read_only=not a.all)

    rows, sheets, mb = [], [], 0.0
    for corpus, v in targets:
        sheet, ev = sheet_for(corpus, v["video_id"], v.get("title", ""))
        if not sheet:
            print(f"  {v['video_id']}  no permitted frames")
            continue
        got = sum(p.stat().st_size for p in (FRAMES / v['video_id']).glob("*.jpg"))
        mb += got / 1e6
        rows += ev
        sheets.append((corpus, v, sheet))
        print(f"  {v['video_id']}  {len(ev)} frames  {got/1e6:.2f} MB  "
              f"{(v.get('title') or '')[:52]}")
        if mb > a.max_mb:
            print(f"  !! disk cap {a.max_mb} MB reached; stopping")
            break

    F.save_evidence(rows, EVIDENCE)
    print(f"\n  {len(rows)} evidence rows -> {EVIDENCE}")
    print(f"  {len(sheets)} contact sheets, {mb:.1f} MB on disk")
    print("  frames are EPHEMERAL: run --prune once the rows are filled in")


if __name__ == "__main__":
    main()
