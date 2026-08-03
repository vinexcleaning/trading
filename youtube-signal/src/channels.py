"""Channel identity and stats.

THERE IS DELIBERATELY NO NAME-SEARCH RESOLVER IN THIS MODULE.

Phase 0 had one. It resolved the string "Nate Tokens" to a different human
(Nate B Jones, 309k subs) at rank 0 with 6/12 agreement -- confidently, and
wrongly. It was caught only because an externally stated subscriber count failed
to reconcile. If you are about to add `resolve_by_search`, that is the bug this
module exists to prevent.

Channel identity comes from exactly two places:
  1. channels.json  -- the four seeds, pinned and verified.
  2. a retrieved video's own channel_id -- video -> channel, never name -> channel.
"""

import json
import statistics
import urllib.parse
from pathlib import Path

from yt_dlp import YoutubeDL

ROOT = Path(__file__).resolve().parent.parent
CHANNELS_JSON = ROOT / "channels.json"

_FLAT = {"quiet": True, "skip_download": True, "extract_flat": True, "no_warnings": True}

# A refresh that moves a stat by more than this factor means the wrong channel was
# resolved, not that the channel grew. Flag, never overwrite.
DRIFT_FACTOR = 5.0


def _ydl(opts=None):
    o = dict(_FLAT)
    o.update(opts or {})
    return YoutubeDL(o)


def load_seeds():
    doc = json.loads(CHANNELS_JSON.read_text(encoding="utf-8"))
    return doc["seeds"]


def search_videos(query, n=25, sp=None):
    """Keyless video search. Kept here only for ad-hoc probing; the pipeline goes
    through retrieval.Retriever.search so pacing and logging are enforced."""
    if sp is None:
        url, opts = f"ytsearch{n}:{query}", {}
    else:
        url = (
            f"https://www.youtube.com/results?"
            f"search_query={urllib.parse.quote_plus(query)}&sp={sp}"
        )
        opts = {"playlistend": n}
    with _ydl(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    out = []
    for e in info.get("entries") or []:
        if not e or not e.get("id"):
            continue
        out.append(
            {
                "video_id": e.get("id"),
                "title": e.get("title"),
                "channel": e.get("channel") or e.get("uploader"),
                "channel_id": e.get("channel_id") or e.get("uploader_id"),
                "view_count": e.get("view_count"),
                "duration_s": e.get("duration"),
            }
        )
    return out


def channel_stats(channel_id, cap=200):
    """Subscriber count, upload count, median views, from the uploads tab.

    upload_count is exact only when the tab was exhausted below `cap`; otherwise
    it is a floor, flagged by upload_count_is_floor.
    """
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    with _ydl({"playlistend": cap}) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = [e for e in (info.get("entries") or []) if e and e.get("id")]
    views = [e["view_count"] for e in entries if e.get("view_count") is not None]
    return {
        "channel_id": channel_id,
        "channel": info.get("channel") or info.get("uploader") or info.get("title"),
        "subscribers": info.get("channel_follower_count"),
        "upload_count": len(entries),
        "upload_count_is_floor": len(entries) >= cap,
        "videos_with_view_data": len(views),
        "median_views": int(statistics.median(views)) if views else None,
        "min_views": min(views) if views else None,
        "max_views": max(views) if views else None,
        "entries": entries,
    }


def drift_check(stored, fresh):
    """Compare a refresh against stored stats. Returns a flag string, or None.

    A >5x move in subscribers or median views is the signature of having resolved
    a different person -- so it is reported, never written over the stored value.
    """
    flags = []
    for key in ("subscribers", "median_views"):
        old, new = stored.get(key), fresh.get(key)
        if not old or not new:
            continue
        ratio = max(old, new) / min(old, new)
        if ratio > DRIFT_FACTOR:
            flags.append(f"{key} moved {old:,} -> {new:,} ({ratio:.1f}x)")
    return "; ".join(flags) if flags else None
