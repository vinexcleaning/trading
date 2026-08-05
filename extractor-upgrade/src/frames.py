"""TASK 2 - frame sampling: pick the moments that matter, cut them, read them.

WHAT THIS DOES
  cues()        decide WHICH seconds are worth a frame, from two independent
                signals: the timestamps of recorded claims, and the phrases in
                the transcript where a speaker turns to the screen
  extract()     cut those seconds out of a LOCAL video file with ffmpeg
  contact()     lay the frames out as a contact sheet so one image covers a
                whole video's worth of moments
  Evidence      screen-derived findings, stored SEPARATELY from
                transcript-derived ones so a claim's provenance stays auditable

WHAT THIS DOES NOT DO, AND WHY
  It does not download from YouTube. See `FINDINGS_T2.md`. YouTube's own
  robots.txt disallows `/get_video`, `/get_video_info`, `/file_download` and
  `/youtubei/`, and `i.ytimg.com/robots.txt` disallows `/sb/` - the storyboard
  path, which was the cheap route. Every mechanism for obtaining a frame is
  named in a Disallow line. `social-signal` killed Reddit's own JSON API, X,
  TikTok and Instagram on exactly this reasoning and wrote it down: a
  User-Agent string is not consent. Applying that standard to Reddit and not
  to YouTube would make it a preference rather than a standard.

  So the pipeline is built, validated end to end against a synthetic video
  with known content at known timestamps, and pointed at local files. It runs
  the moment a permitted source exists: a file the user owns, a licensed
  archive, a screen recording, or a venue that permits it in writing.

    python src/frames.py --selftest        build a synthetic video and prove
                                           the whole loop, no network at all
    python src/frames.py --video FILE --id VID
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpora  # noqa: E402

HERE = Path(__file__).resolve().parent
FRAMES = HERE.parent / "frames"
DATA = HERE.parent / "data"


def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


# ------------------------------------------------------------------- cues
# The phrases a speaker uses when the answer moves from their mouth to the
# screen. Deliberately narrow: a cue that fires everywhere costs a frame
# everywhere, and frames are the expensive part.
DEMO_CUES = re.compile(
    r"\b(as you can see|you can see (here|that|this)|let me show you|"
    r"i'?ll show you|here'?s (my|the) (account|balance|wallet|p&?l|pnl|"
    r"results?|dashboard|terminal|code|repo)|look at (this|the screen)|"
    r"on (the |my )?screen|if i (run|click|refresh)|right here|"
    r"this is (my|the) (actual|real|live) |pull(ing)? up|"
    r"screenshot|scroll (down|up)|zoom in)\b", re.I)

# Where a NUMBER is spoken. A number said aloud and a number on screen is the
# single comparison that can catch a fabricated result, so these are the
# highest-value frames in the video.
SPOKEN_NUMBER = re.compile(
    r"(\$\s?\d[\d,]*(\.\d+)?|\b\d+(\.\d+)?\s?(percent|%)|"
    r"\b\d[\d,]{2,}\s+(trades?|dollars))", re.I)


@dataclass
class Cue:
    t: float
    kind: str          # claim | demo | number
    why: str


def cues(corpus: str, video_id: str, max_frames: int = 40) -> list[Cue]:
    """Every second worth a frame, deduplicated and capped.

    Three sources, ranked. Claims first: those are the assertions the whole
    system exists to check.
    """
    con = corpora.ro(corpus)
    out: list[Cue] = []

    rows = con.execute(
        "SELECT timestamp_s, claim_type, claim_text FROM claims "
        "WHERE video_id = ? AND timestamp_s IS NOT NULL", (video_id,)).fetchall()
    for r in rows:
        pri = "claim" if r["claim_type"] == "result" else "claim"
        out.append(Cue(float(r["timestamp_s"]), pri,
                       f"{r['claim_type']}: {(r['claim_text'] or '')[:90]}"))

    for r in con.execute(
            "SELECT ts_start, ts_end, why FROM watch_segments "
            "WHERE video_id = ?", (video_id,)):
        mid = (float(r["ts_start"]) + float(r["ts_end"])) / 2
        out.append(Cue(mid, "demo", f"watch_segment: {r['why']}"))

    t = con.execute("SELECT snippets_json FROM transcripts WHERE video_id = ?",
                    (video_id,)).fetchone()
    con.close()
    if t:
        for s in json.loads(t["snippets_json"]):
            txt = s["text"]
            if DEMO_CUES.search(txt):
                out.append(Cue(float(s["start"]) + 2.0, "demo", txt[:90]))
            elif SPOKEN_NUMBER.search(txt):
                out.append(Cue(float(s["start"]) + 1.0, "number", txt[:90]))

    # Dedupe to a 4-second grid, claims winning ties, then cap by priority.
    order = {"claim": 0, "demo": 1, "number": 2}
    best: dict[int, Cue] = {}
    for c in sorted(out, key=lambda c: (order[c.kind], c.t)):
        k = int(c.t // 4)
        best.setdefault(k, c)
    picked = sorted(best.values(), key=lambda c: (order[c.kind], c.t))
    picked = picked[:max_frames]
    return sorted(picked, key=lambda c: c.t)


# ---------------------------------------------------------------- extract

def extract(video_path: str, times: list[float], out_dir: Path,
            width: int = 1280) -> list[Path]:
    """One ffmpeg invocation per timestamp, seeking before decode so a
    20-minute file costs milliseconds per frame instead of a full decode."""
    out_dir.mkdir(parents=True, exist_ok=True)
    exe = ffmpeg()
    written = []
    for t in times:
        p = out_dir / f"t{int(round(t)):06d}.jpg"
        cmd = [exe, "-loglevel", "error", "-y", "-ss", f"{t:.2f}",
               "-i", str(video_path), "-frames:v", "1",
               "-vf", f"scale={width}:-2", "-q:v", "3", str(p)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not p.exists() or p.stat().st_size == 0:
            print(f"  ffmpeg failed at {t:.1f}s: {r.stderr.strip()[:120]}")
            continue
        flat, why = is_flat(p)
        if flat:
            # A 0 exit code is not a rendered frame. See the three silent
            # ffmpeg traps documented in selftest(): a blank image came back
            # with returncode 0 and an empty stderr. The same shape as
            # bot-hunt's "a 200 is not a correct file".
            print(f"  BLANK frame at {t:.1f}s ({why}) - kept and flagged")
        written.append(p)
    return written


def is_flat(path: Path, tol: float = 2.0):
    """Is this frame effectively featureless? Returns (flat, why).

    Cheap canary, not a quality judgment: a genuinely dark scene will trip it
    and that is fine, because the caller is told rather than silently handed a
    blank.
    """
    from PIL import Image, ImageStat
    im = Image.open(path).convert("L")
    st = ImageStat.Stat(im)
    sd = st.stddev[0]
    return (sd < tol, f"stddev={sd:.2f} < {tol}")


def contact(paths: list[Path], out: Path, cols: int = 4, tile_w: int = 640,
            labels: list[str] | None = None) -> Path:
    """A contact sheet. One image of a whole video's decisive moments costs a
    fraction of what forty separate reads cost, and the comparison a reader
    needs - does the screen say what the mouth said - is between frames."""
    from PIL import Image, ImageDraw
    if not paths:
        raise ValueError("no frames")
    ims = [Image.open(p).convert("RGB") for p in paths]
    tile_h = max(1, int(tile_w * ims[0].height / ims[0].width))
    rows = math.ceil(len(ims) / cols)
    bar = 22
    sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + bar)), "black")
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        x, y = (i % cols) * tile_w, (i // cols) * (tile_h + bar)
        sheet.paste(im.resize((tile_w, tile_h)), (x, y + bar))
        d.text((x + 4, y + 5), (labels[i] if labels else paths[i].stem),
               fill="white")
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)
    return out


# ------------------------------------------------- provenance-separated store

@dataclass
class ScreenEvidence:
    """Screen-derived, and kept apart from anything transcript-derived.

    `spoken` is what the transcript says at that second. `shown` is what the
    frame shows. `agreement` is the only field a verdict may read, and it is
    filled by whoever looked at the frame - never inferred from the transcript.
    """
    video_id: str
    corpus: str
    t: float
    frame: str
    cue_kind: str
    spoken: str
    shown: str = ""
    agreement: str = "UNREAD"   # CONFIRMS | CONTRADICTS | ADDS | ABSENT | UNREAD
    note: str = ""

    def as_row(self):
        return asdict(self)


def save_evidence(rows: list[ScreenEvidence], path: Path | None = None):
    path = path or (DATA / "screen_evidence.json")
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    keys = {(r["video_id"], r["t"]) for r in old}
    old += [r.as_row() for r in rows if (r.video_id, r.t) not in keys]
    path.write_text(json.dumps(old, indent=2), encoding="utf-8")
    return path


# ------------------------------------------------------------------ selftest

SELFTEST_SCENES = [
    (0, "SPOKEN: I made 40 percent this month"),
    (5, "SCREEN: Total P/L  -18.4%"),
    (10, "SCREEN: 33 trades   net +$23.53"),
    (15, "SCREEN: pip install py-clob-client"),
    (20, "SCREEN: Traceback: 401 Unauthorized"),
]


def selftest():
    """Build a video whose content at each second is known, then prove the
    whole loop: cut the right seconds, and produce one sheet a reader can read.

    This validates the CAPABILITY without fetching anything from anywhere. If
    the sheet shows the five scenes in order, frame sampling works and the only
    thing missing is a source whose terms permit it.
    """
    out = FRAMES / "_selftest"
    out.mkdir(parents=True, exist_ok=True)
    vid = out / "synthetic.mp4"
    exe = ffmpeg()

    parts = []
    for i, (t, label) in enumerate(SELFTEST_SCENES):
        seg = out / f"seg{i}.mp4"
        # THREE ffmpeg traps, each found by looking at the output rather than
        # at the exit code, and every one of them SILENT:
        #  1  `%` in drawtext text renders the WHOLE caption as nothing, with
        #     exit code 0 and empty stderr. Bisected: "Total 18%" -> 1,002
        #     bytes (blank), "Total 18 pct" -> 3,007 bytes (text). `\%` does
        #     not help and neither does `textfile=`.
        #  2  the cure is `expansion=none`, which turns off the whole
        #     text-expansion layer. Same string, 4,471 bytes.
        #  3  a Windows drive letter's colon is a separator inside a filter
        #     string, so the textfile path must be relative with cwd set.
        tf = out / f"cap{i}.txt"
        tf.write_text(f"{label}\n[t={t}s]", encoding="utf-8")
        subprocess.run(
            [exe, "-loglevel", "error", "-y", "-f", "lavfi",
             "-i", "color=c=0x101820:s=1280x720:d=5",
             "-vf", (f"drawtext=textfile={tf.name}:expansion=none:"
                     f"fontcolor=white:fontsize=44:line_spacing=18:"
                     f"x=(w-text_w)/2:y=(h-text_h)/2"),
             "-r", "10", "-pix_fmt", "yuv420p", seg.name],
            check=True, capture_output=True, cwd=out)
        parts.append(seg)
        tf.unlink(missing_ok=True)

    lst = out / "parts.txt"
    lst.write_text("\n".join(f"file '{p.name}'" for p in parts),
                   encoding="utf-8")
    subprocess.run([exe, "-loglevel", "error", "-y", "-f", "concat",
                    "-safe", "0", "-i", str(lst), "-c", "copy", str(vid)],
                   check=True, capture_output=True, cwd=out)
    print(f"  synthetic video: {vid} ({vid.stat().st_size:,} bytes)")

    times = [t + 2.5 for t, _ in SELFTEST_SCENES]
    got = extract(str(vid), times, out / "shots")
    print(f"  extracted {len(got)}/{len(times)} frames")
    sheet = contact(got, out / "contact.jpg", cols=3,
                    labels=[f"t={int(t)}s" for t in times])
    print(f"  contact sheet: {sheet} ({sheet.stat().st_size:,} bytes)")
    for p in parts:
        p.unlink(missing_ok=True)
    lst.unlink(missing_ok=True)
    return sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--video", help="a LOCAL video file")
    ap.add_argument("--id", help="video_id, to look cues up in a corpus")
    ap.add_argument("--corpus", default="yt")
    ap.add_argument("--max", type=int, default=24)
    ap.add_argument("--cues-only", action="store_true",
                    help="print the cue plan without touching a video")
    a = ap.parse_args()

    if a.selftest:
        selftest()
        return
    if not a.id:
        ap.error("--id is required")

    plan = cues(a.corpus, a.id, max_frames=a.max)
    print(f"  {len(plan)} cues for {a.id}")
    for c in plan:
        print(f"    {c.t:8.1f}s {c.kind:7s} {c.why[:80]}")
    if a.cues_only or not a.video:
        return

    out = FRAMES / a.id
    got = extract(a.video, [c.t for c in plan], out)
    contact(got, out / "contact.jpg",
            labels=[f"{int(c.t)}s {c.kind}" for c in plan])
    con = corpora.ro(a.corpus)
    snip = json.loads(con.execute(
        "SELECT snippets_json FROM transcripts WHERE video_id=?",
        (a.id,)).fetchone()["snippets_json"])
    con.close()
    rows = []
    for c, p in zip(plan, got):
        spoken = " ".join(s["text"] for s in snip
                          if c.t - 6 <= s["start"] <= c.t + 6)
        rows.append(ScreenEvidence(a.id, a.corpus, c.t, str(p), c.kind,
                                   spoken[:400]))
    print(f"  evidence rows staged: {save_evidence(rows)}")


if __name__ == "__main__":
    main()
