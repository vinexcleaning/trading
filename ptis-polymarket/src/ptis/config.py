from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    database_path: Path
    raw_data_dir: Path
    request_timeout_seconds: float = 20.0

    @classmethod
    def default(cls) -> "Settings":
        root = Path.cwd()
        return cls(
            project_root=root,
            database_path=root / "data" / "processed" / "ptis.sqlite3",
            raw_data_dir=root / "data" / "raw",
        )
