"""Timestamp discipline: UTC integer nanoseconds, NTP offset, monotonic sequencing."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

NTP_SERVERS = ["pool.ntp.org", "time.google.com", "time.cloudflare.com"]


def now_ns() -> int:
    """Wall-clock UTC nanoseconds."""
    return time.time_ns()


def mono_ns() -> int:
    """Monotonic nanoseconds for sequencing. Not comparable across processes."""
    return time.monotonic_ns()


def parse_iso_ns(ts: str | None) -> int | None:
    """Parse Kalshi ISO8601 (with Z, variable fractional digits) to UTC ns."""
    if not ts:
        return None
    s = ts.rstrip("Z")
    if "." in s:
        head, frac = s.split(".", 1)
        frac = (frac + "000000000")[:9]
    else:
        head, frac = s, "0" * 9
    try:
        st = time.strptime(head, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    import calendar

    return calendar.timegm(st) * 1_000_000_000 + int(frac)


@dataclass
class ClockState:
    ntp_offset_s: float | None = None
    ntp_server: str | None = None
    checked_at_ns: int = 0
    history: list[tuple[int, float | None]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def refresh(self) -> None:
        offset, server = _query_ntp()
        with self._lock:
            self.ntp_offset_s = offset
            self.ntp_server = server
            self.checked_at_ns = now_ns()
            self.history.append((self.checked_at_ns, offset))

    def as_dict(self) -> dict:
        with self._lock:
            return {
                "ntp_offset_s": self.ntp_offset_s,
                "ntp_server": self.ntp_server,
                "checked_at_ns": self.checked_at_ns,
            }


def _query_ntp() -> tuple[float | None, str | None]:
    try:
        import ntplib
    except ImportError:
        return None, None
    c = ntplib.NTPClient()
    for srv in NTP_SERVERS:
        try:
            r = c.request(srv, version=3, timeout=4)
            return float(r.offset), srv
        except Exception:  # noqa: BLE001,S112
            continue
    return None, None


CLOCK = ClockState()
