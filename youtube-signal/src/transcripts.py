"""Transcript fetching, two independent paths.

Path A: youtube-transcript-api  -- fast, hits the timedtext endpoint directly.
Path B: yt-dlp                  -- slower, but resolves the player and can pick
                                   up captions path A is refused.

Neither path costs YouTube Data API quota. Both are IP-sensitive: YouTube blocks
datacenter ranges outright, so this must run from a residential connection.
"""

import json
import urllib.request

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def _classify(exc):
    """Map an exception to a stable error class so failures can be counted."""
    return type(exc).__name__


def fetch_via_api(video_id, languages=("en", "en-US", "en-GB")):
    """Path A. Returns (snippets, meta) or raises."""
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id, languages=list(languages))
    snippets = [
        {"start": s.start, "duration": s.duration, "text": s.text} for s in fetched
    ]
    meta = {
        "language": getattr(fetched, "language", None),
        "language_code": getattr(fetched, "language_code", None),
        "is_generated": getattr(fetched, "is_generated", None),
    }
    return snippets, meta


def _pick_caption_track(info, languages):
    """Prefer manual subtitles over auto-captions, and json3 over other formats."""
    for bucket in ("subtitles", "automatic_captions"):
        tracks = info.get(bucket) or {}
        for lang in languages:
            if lang in tracks:
                fmts = tracks[lang]
                for want in ("json3", "srv3", "vtt"):
                    for f in fmts:
                        if f.get("ext") == want:
                            return f["url"], want, bucket, lang
                if fmts:
                    return fmts[0]["url"], fmts[0].get("ext"), bucket, lang
        # fall back to any en-* variant
        for code in tracks:
            if code.startswith("en"):
                fmts = tracks[code]
                for want in ("json3", "srv3", "vtt"):
                    for f in fmts:
                        if f.get("ext") == want:
                            return f["url"], want, bucket, code
    return None, None, None, None


def _parse_json3(raw):
    doc = json.loads(raw)
    out = []
    for ev in doc.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text:
            continue
        out.append(
            {
                "start": ev.get("tStartMs", 0) / 1000.0,
                "duration": ev.get("dDurationMs", 0) / 1000.0,
                "text": text,
            }
        )
    return out


def _parse_vtt(raw):
    out = []
    block_time, block_text = None, []

    def _secs(ts):
        ts = ts.replace(",", ".")
        parts = ts.split(":")
        h, m, s = (["0"] * (3 - len(parts))) + parts
        return int(h) * 3600 + int(m) * 60 + float(s)

    for line in raw.splitlines():
        line = line.strip()
        if "-->" in line:
            if block_time is not None and block_text:
                out.append(
                    {"start": block_time, "duration": 0.0, "text": " ".join(block_text)}
                )
            a, b = line.split("-->")[:2]
            block_time, block_text = _secs(a.strip().split()[0]), []
        elif line and block_time is not None and not line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            block_text.append(line)
    if block_time is not None and block_text:
        out.append({"start": block_time, "duration": 0.0, "text": " ".join(block_text)})
    return out


def fetch_via_ytdlp(video_id, languages=("en", "en-US", "en-GB")):
    """Path B. Returns (snippets, meta) or raises."""
    from yt_dlp import YoutubeDL

    opts = {"quiet": True, "skip_download": True, "no_warnings": True}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}", download=False
        )
    url, ext, bucket, lang = _pick_caption_track(info, list(languages))
    if not url:
        raise LookupError("no english caption track exposed by yt-dlp")
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    snippets = _parse_json3(raw) if ext == "json3" else _parse_vtt(raw)
    if not snippets:
        raise LookupError(f"caption track parsed to zero snippets (ext={ext})")
    meta = {
        "language_code": lang,
        "is_generated": bucket == "automatic_captions",
        "format": ext,
        "duration_s": info.get("duration"),
        "title": info.get("title"),
        "channel": info.get("channel"),
        "channel_id": info.get("channel_id"),
        "view_count": info.get("view_count"),
        "upload_date": info.get("upload_date"),
    }
    return snippets, meta


def fetch(video_id, prefer="api"):
    """Try both paths. Returns a dict describing exactly what happened on each --
    Phase 0 needs the per-path outcome, not just the winner."""
    order = (
        [("youtube-transcript-api", fetch_via_api), ("yt-dlp", fetch_via_ytdlp)]
        if prefer == "api"
        else [("yt-dlp", fetch_via_ytdlp), ("youtube-transcript-api", fetch_via_api)]
    )
    result = {"video_id": video_id, "paths": {}, "snippets": None, "meta": None, "via": None}
    for name, fn in order:
        try:
            snippets, meta = fn(video_id)
        except Exception as exc:  # noqa: BLE001 - we are cataloguing error classes
            result["paths"][name] = {
                "ok": False,
                "error_class": _classify(exc),
                "error": str(exc).strip().splitlines()[0][:200],
            }
            continue
        result["paths"][name] = {
            "ok": True,
            "n_snippets": len(snippets),
            "n_words": sum(len(s["text"].split()) for s in snippets),
            "generated": meta.get("is_generated"),
        }
        if result["snippets"] is None:
            result["snippets"], result["meta"], result["via"] = snippets, meta, name
    return result
