"""Paced, logged, cached retrieval via yt-dlp. No API key, no quota.

Everything that touches the network goes through here so that pacing, throttle
detection and caching cannot be bypassed by accident.

Premise 2 of this phase (yt-dlp survives 30+ searches in a session) is tested by
instrumenting rather than by hoping: every call records wall-clock and result
count, and `throttle_report()` compares the first half of the session to the
second. A soft block shows up as result counts collapsing or latency climbing.
"""

import datetime as dt
import time
import urllib.parse
import urllib.request

from yt_dlp import YoutubeDL

import db

SEARCH_GAP_S = 2.0
TRANSCRIPT_GAP_S = 1.5
BLOCK_ERRORS = {"IpBlocked", "RequestBlocked", "PoTokenRequired"}
MAX_CONSECUTIVE_BLOCKS = 3

_FLAT = {"quiet": True, "skip_download": True, "extract_flat": True, "no_warnings": True}
_FULL = {"quiet": True, "skip_download": True, "no_warnings": True}


class BlockedError(RuntimeError):
    """Raised when transcript fetching is blocked 3 times consecutively."""


class Retriever:
    def __init__(self, con, today=None):
        self.con = con
        self.today = today or dt.date.today()
        self._last_search = 0.0
        self._last_transcript = 0.0
        self._consecutive_blocks = 0
        self.block_events = []

    # ---------- pacing ----------

    def _pace(self, attr, gap):
        elapsed = time.time() - getattr(self, attr)
        if elapsed < gap:
            time.sleep(gap - elapsed)
        setattr(self, attr, time.time())

    # ---------- search ----------

    def search(self, query, family, run_idx, sp=None, n=25):
        """One search call. Logged whether it succeeds or fails."""
        self._pace("_last_search", SEARCH_GAP_S)
        if sp is None:
            url, opts = f"ytsearch{n}:{query}", dict(_FLAT)
        else:
            q = urllib.parse.quote_plus(query)
            url = f"https://www.youtube.com/results?search_query={q}&sp={sp}"
            opts = dict(_FLAT, playlistend=n)

        t0 = time.time()
        entries, ok, err = [], 1, None
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            entries = [e for e in (info.get("entries") or []) if e and e.get("id")]
        except Exception as exc:  # noqa: BLE001
            ok, err = 0, f"{type(exc).__name__}: {str(exc).strip().splitlines()[0][:180]}"
        secs = round(time.time() - t0, 2)

        self.con.execute(
            "INSERT INTO retrieval_log (ts_utc, family, query, run_idx, n_results,"
            " seconds, ok, error) VALUES (?,?,?,?,?,?,?,?)",
            (db.now(), family, query, run_idx, len(entries), secs, ok, err),
        )
        self.con.commit()
        return entries, secs, err

    def record_hits(self, entries, family, query, run_idx):
        """Persist per-run hits and upsert the video row with flat metadata."""
        for rank, e in enumerate(entries):
            vid = e["id"]
            self.con.execute(
                "INSERT OR IGNORE INTO retrieval_hits (video_id, family, query,"
                " run_idx, rank) VALUES (?,?,?,?,?)",
                (vid, family, query, run_idx, rank),
            )
            self.con.execute(
                """INSERT INTO videos (video_id, channel_id, channel_name, title,
                       view_count, duration_s, source, created_utc)
                   VALUES (?,?,?,?,?,?,'search',?)
                   ON CONFLICT(video_id) DO UPDATE SET
                       view_count   = COALESCE(excluded.view_count, videos.view_count),
                       duration_s   = COALESCE(excluded.duration_s, videos.duration_s),
                       channel_id   = COALESCE(videos.channel_id, excluded.channel_id),
                       channel_name = COALESCE(videos.channel_name, excluded.channel_name)""",
                (
                    vid,
                    e.get("channel_id") or e.get("uploader_id"),
                    e.get("channel") or e.get("uploader"),
                    e.get("title"),
                    e.get("view_count"),
                    e.get("duration"),
                    db.now(),
                ),
            )
        self.con.commit()

    # ---------- channel enumeration ----------

    def channel_uploads(self, channel_id, cap=200):
        """Full uploads list, newest first. 1 call, no quota."""
        self._pace("_last_search", SEARCH_GAP_S)
        url = f"https://www.youtube.com/channel/{channel_id}/videos"
        with YoutubeDL(dict(_FLAT, playlistend=cap)) as ydl:
            info = ydl.extract_info(url, download=False)
        entries = [e for e in (info.get("entries") or []) if e and e.get("id")]
        return info, entries

    # ---------- per-video metadata ----------

    def video_metadata(self, video_id):
        """Full extraction: upload_date (which flat mode does not carry), plus the
        caption tracks, so one call serves both G2 and G1."""
        self._pace("_last_transcript", TRANSCRIPT_GAP_S)
        with YoutubeDL(_FULL) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
        ud = info.get("upload_date")
        d = dt.datetime.strptime(ud, "%Y%m%d").date() if ud else None
        return {
            "info": info,
            "upload_date": d.isoformat() if d else None,
            "age_months": round((self.today - d).days / 30.44, 2) if d else None,
            "title": info.get("title"),
            "channel_id": info.get("channel_id"),
            "channel_name": info.get("channel"),
            "view_count": info.get("view_count"),
            "duration_s": info.get("duration"),
        }

    # ---------- transcripts ----------

    def transcript(self, video_id, info=None):
        """Try youtube-transcript-api, then the caption track yt-dlp already
        resolved. Counts consecutive block errors and halts the run at 3."""
        import transcripts as T

        self._pace("_last_transcript", TRANSCRIPT_GAP_S)
        snippets, via, errors = None, None, {}

        try:
            snippets, _meta = T.fetch_via_api(video_id)
            via = "youtube-transcript-api"
        except Exception as exc:  # noqa: BLE001
            cls = type(exc).__name__
            errors["youtube-transcript-api"] = cls
            if cls in BLOCK_ERRORS:
                self._consecutive_blocks += 1
                self.block_events.append((db.now(), video_id, cls))
                if self._consecutive_blocks >= MAX_CONSECUTIVE_BLOCKS:
                    raise BlockedError(
                        f"{self._consecutive_blocks} consecutive transcript blocks; "
                        f"last was {cls} on {video_id}. Halting -- not retrying "
                        f"through a block."
                    ) from exc

        if snippets is None and info is not None:
            try:
                url, ext, bucket, lang = T._pick_caption_track(
                    info, ["en", "en-US", "en-GB"]
                )
                if url:
                    req = urllib.request.Request(url, headers={"User-Agent": T._UA})
                    raw = urllib.request.urlopen(req, timeout=30).read().decode(
                        "utf-8", "replace"
                    )
                    snippets = (
                        T._parse_json3(raw) if ext == "json3" else T._parse_vtt(raw)
                    )
                    via = "yt-dlp"
                else:
                    errors["yt-dlp"] = "no english caption track"
            except Exception as exc:  # noqa: BLE001
                errors["yt-dlp"] = type(exc).__name__

        if snippets:
            self._consecutive_blocks = 0
        return snippets, via, errors

    # ---------- instrumentation ----------

    def throttle_report(self):
        """Premise 2. Split the session's successful searches in half and compare.
        Degrading result counts or climbing latency = soft block."""
        rows = self.con.execute(
            "SELECT n_results, seconds, ok FROM retrieval_log ORDER BY id"
        ).fetchall()
        if len(rows) < 6:
            return {"n_calls": len(rows), "verdict": "too few calls to judge"}
        ok_rows = [r for r in rows if r["ok"]]
        half = len(ok_rows) // 2
        a, b = ok_rows[:half], ok_rows[half:]

        def avg(rs, k):
            return round(sum(r[k] for r in rs) / len(rs), 2) if rs else None

        first_n, second_n = avg(a, "n_results"), avg(b, "n_results")
        first_s, second_s = avg(a, "seconds"), avg(b, "seconds")
        failures = sum(1 for r in rows if not r["ok"])
        empties = sum(1 for r in ok_rows if r["n_results"] == 0)
        degraded = (
            (second_n is not None and first_n and second_n < 0.75 * first_n)
            or (second_s is not None and first_s and second_s > 2.0 * first_s)
            or empties > 0
        )
        return {
            "n_calls": len(rows),
            "failed_calls": failures,
            "empty_results": empties,
            "mean_results_first_half": first_n,
            "mean_results_second_half": second_n,
            "mean_seconds_first_half": first_s,
            "mean_seconds_second_half": second_s,
            "verdict": "DEGRADED" if degraded else "no degradation detected",
        }
