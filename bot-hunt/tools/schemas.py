"""Print table names + row counts for every extractor corpus this repo holds.

Read-only. Opens each DB in immutable mode so a sibling session's writer is
never blocked (social-signal lost 45 minutes of collection to exactly that).
"""
import sqlite3
from pathlib import Path

DBS = {
    "github": r"C:\Users\vinig\trading\signal-github\data\github.db",
    "yt_broad": r"C:\Users\vinig\trading\youtube-signal\data\signal.db",
    "yt_kalshi": r"C:\Users\vinig\trading\youtube-signal\data\signal_kalshi_edge.db",
    "social": r"C:\Users\vinig\trading\social-signal\data\social.db",
}


def ro(path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)


def main() -> None:
    for name, path in DBS.items():
        if not Path(path).exists():
            print(f"== {name}: MISSING {path}")
            continue
        con = ro(path)
        print(f"== {name}  {path}")
        rows = con.execute(
            "select name from sqlite_master where type='table' order by name"
        ).fetchall()
        for (t,) in rows:
            try:
                n = con.execute(f'select count(*) from "{t}"').fetchone()[0]
            except sqlite3.Error as exc:
                n = f"ERR {exc}"
            cols = [r[1] for r in con.execute(f'pragma table_info("{t}")')]
            print(f"   {t:28} {str(n):>8}  {','.join(cols)}")
        con.close()
        print()


if __name__ == "__main__":
    main()
