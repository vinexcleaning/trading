"""Download Sackmann singles match data from the archival mirror.

Upstream (JeffSackmann/tennis_atp, tennis_wta) is no longer public as of 2026-07;
this pulls the same file set from Aneeshers/tennis-sackmann-archive.
"""
import concurrent.futures as cf
import pathlib
import sys

import requests

REPO = "Aneeshers/tennis-sackmann-archive"
BRANCH = "main"
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "sackmann"

# Singles matches + player/ranking reference data. Doubles and point-by-point
# are not needed for a pre-match singles win-probability model.
WANTED_PREFIXES = (
    "atp/atp_matches_1", "atp/atp_matches_2", "atp/atp_matches_amateur",
    "atp/atp_matches_qual_chall_", "atp/atp_matches_futures_",
    "wta/wta_matches_1", "wta/wta_matches_2", "wta/wta_matches_qual_itf_",
    "atp/atp_players.csv", "wta/wta_players.csv",
    "atp/atp_rankings_", "wta/wta_rankings_",
    "atp/matches_data_dictionary.txt",
    "atp/UPSTREAM_README.md", "wta/UPSTREAM_README.md",
)
EXCLUDE = ("doubles",)


def listing():
    url = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"
    tree = requests.get(url, headers={"User-Agent": "py"}, timeout=120).json()["tree"]
    paths = [n["path"] for n in tree if n["type"] == "blob"]
    return [
        p for p in paths
        if p.startswith(WANTED_PREFIXES) and not any(x in p for x in EXCLUDE)
    ]


def fetch(path):
    dest = OUT / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return path, dest.stat().st_size, "cached"
    r = requests.get(RAW + path, timeout=300)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return path, len(r.content), "ok"


def main():
    paths = listing()
    print(f"{len(paths)} files to fetch", flush=True)
    total = 0
    failed = []
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        for fut in cf.as_completed([ex.submit(fetch, p) for p in paths]):
            try:
                path, size, status = fut.result()
                total += size
            except Exception as e:  # noqa: BLE001
                failed.append(repr(e))
    print(f"done: {total / 1e6:.1f} MB across {len(paths) - len(failed)} files")
    if failed:
        print(f"FAILED {len(failed)}:", *failed[:10], sep="\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
