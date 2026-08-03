"""Buffered parquet writer, partitioned by source/date/hour, with a manifest."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import pandas as pd

from .clock import now_ns


class PartitionedWriter:
    """Append rows, flush to parquet partitioned by source/date/hour.

    One file per (source, date, hour, flush) so writes are atomic and idempotent
    by construction; readers glob the partition.
    """

    def __init__(
        self,
        root: Path,
        source: str,
        flush_rows: int = 2000,
        flush_seconds: float = 60.0,
    ) -> None:
        self.root = Path(root)
        self.source = source
        self.flush_rows = flush_rows
        self.flush_seconds = flush_seconds
        self._buf: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._last_flush = time.monotonic()
        self._seq = 0
        self.rows_written = 0

    def add(self, row: dict[str, Any]) -> None:
        with self._lock:
            self._buf.append(row)
            due = (
                len(self._buf) >= self.flush_rows
                or (time.monotonic() - self._last_flush) >= self.flush_seconds
            )
        if due:
            self.flush()

    def maybe_flush(self) -> int:
        """Flush if the time-based interval has elapsed, even with no new rows.

        Callers that may go long stretches without data must use this, otherwise
        a partially-filled buffer is never persisted.
        """
        with self._lock:
            due = bool(self._buf) and (
                time.monotonic() - self._last_flush
            ) >= self.flush_seconds
        return self.flush() if due else 0

    def add_many(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            self.maybe_flush()
            return
        with self._lock:
            self._buf.extend(rows)
            due = (
                len(self._buf) >= self.flush_rows
                or (time.monotonic() - self._last_flush) >= self.flush_seconds
            )
        if due:
            self.flush()

    def flush(self) -> int:
        with self._lock:
            if not self._buf:
                self._last_flush = time.monotonic()
                return 0
            rows, self._buf = self._buf, []
            self._last_flush = time.monotonic()
            self._seq += 1
            seq = self._seq
        df = pd.DataFrame(rows)
        ns = now_ns()
        t = time.gmtime(ns // 1_000_000_000)
        part = (
            self.root
            / f"source={self.source}"
            / f"date={time.strftime('%Y-%m-%d', t)}"
            / f"hour={t.tm_hour:02d}"
        )
        part.mkdir(parents=True, exist_ok=True)
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].apply(
                    lambda v: json.dumps(v) if isinstance(v, (dict, list)) else v
                )
        path = part / f"{self.source}-{ns}-{seq:06d}.parquet"
        df.to_parquet(path, index=False, compression="zstd")
        self.rows_written += len(df)
        return len(df)


def build_manifest(root: Path, out: Path) -> dict:
    """Row counts, first/last timestamps and file checksums per partition."""
    import hashlib

    root = Path(root)
    entries = []
    for f in sorted(root.rglob("*.parquet")):
        try:
            df = pd.read_parquet(f, columns=None)
        except Exception as e:  # noqa: BLE001
            entries.append({"file": str(f.relative_to(root)), "error": str(e)})
            continue
        ts_col = next(
            (c for c in ("recv_ns", "event_ns", "write_ns", "ts_ns") if c in df.columns), None
        )
        h = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
        entries.append(
            {
                "file": str(f.relative_to(root)),
                "rows": int(len(df)),
                "first_ns": int(df[ts_col].min()) if ts_col and len(df) else None,
                "last_ns": int(df[ts_col].max()) if ts_col and len(df) else None,
                "sha256_16": h,
                "bytes": f.stat().st_size,
            }
        )
    man = {
        "generated_ns": now_ns(),
        "root": str(root),
        "n_files": len(entries),
        "total_rows": sum(e.get("rows", 0) or 0 for e in entries),
        "files": entries,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(man, indent=1))
    return man
