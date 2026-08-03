"""Resolve creator names to channel IDs and pull per-channel stats.

Deliberately keyless (yt-dlp). The names in the prompt were given from memory, so
resolution is search-based rather than handle-based -- a wrong handle 404s, but a
search still finds a misspelled name and reports the correction.
"""

import statistics

from yt_dlp import YoutubeDL

_FLAT = {"quiet": True, "skip_download": True, "extract_flat": True, "no_warnings": True}


def _ydl(opts=None):
    o = dict(_FLAT)
    o.update(opts or {})
    return YoutubeDL(o)


def search_videos(query, n=25):
    """Keyless video search. Returns flat entries (id/title/channel/channel_id/
    view_count/duration). Costs zero API quota."""
    with _ydl() as ydl:
        info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
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


def resolve_by_search(name, probe=12):
    """Find the channel that best matches a creator name typed from memory.

    Strategy: search the name as a query, then take the channel that appears most
    often among the top hits. Ties break toward the higher-ranked hit.
    """
    hits = search_videos(name, n=probe)
    tally = {}
    for rank, h in enumerate(hits):
        cid = h.get("channel_id")
        if not cid:
            continue
        rec = tally.setdefault(cid, {"channel": h["channel"], "count": 0, "best_rank": rank})
        rec["count"] += 1
        rec["best_rank"] = min(rec["best_rank"], rank)
    if not tally:
        return None
    cid, rec = max(tally.items(), key=lambda kv: (kv[1]["count"], -kv[1]["best_rank"]))
    return {
        "query": name,
        "channel_id": cid,
        "resolved_name": rec["channel"],
        "name_matches_prompt": rec["channel"].strip().lower() == name.strip().lower(),
        "hits_in_top": rec["count"],
        "probe_size": len(hits),
        "best_rank": rec["best_rank"],
    }


def channel_stats(channel_id, cap=200):
    """Subscriber count, upload count, and median views, from the uploads tab.

    `cap` bounds how many uploads are enumerated. upload_count is reported as an
    exact number only when the tab was exhausted below the cap; otherwise it is
    a floor, flagged via `upload_count_is_floor`.
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
        "sample": [
            {
                "video_id": e["id"],
                "title": e.get("title"),
                "view_count": e.get("view_count"),
                "duration_s": e.get("duration"),
            }
            for e in entries[:5]
        ],
    }
