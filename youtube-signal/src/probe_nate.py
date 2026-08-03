"""Focused check on 'Nate Tokens'.

The prompt describes this creator as ~30k subs / ~2k median views. Search-based
resolution returned a 309k-sub channel called 'Nate B Jones', which contradicts
that description -- so the resolver probably fuzzy-matched the wrong person.
Try handle URLs directly, which either 404 or return the real channel.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import channels  # noqa: E402

HANDLES = ["natetokens", "NateTokens", "nate_tokens", "NateToken", "thenatetokens"]

print("=== direct handle probes ===")
for h in HANDLES:
    url = f"https://www.youtube.com/@{h}"
    try:
        with channels._ydl({"playlistend": 1}) as ydl:
            info = ydl.extract_info(f"{url}/videos", download=False)
        print(f"  @{h:<14} EXISTS  id={info.get('channel_id')} "
              f"name={info.get('channel')!r} subs={info.get('channel_follower_count')}")
    except Exception as exc:  # noqa: BLE001
        print(f"  @{h:<14} {type(exc).__name__}: {str(exc).strip().splitlines()[0][:110]}")

print("\n=== who does a literal search return, ranked ===")
for q in ['"Nate Tokens"', "Nate Tokens prediction markets", "Nate Tokens Kalshi"]:
    print(f"\n  query: {q}")
    try:
        for i, h in enumerate(channels.search_videos(q, n=8)):
            v = h["view_count"]
            print(f"    {i}. {h['channel']!r:<46} views={v if v is not None else '?'}  "
                  f"{(h['title'] or '')[:44]}")
    except Exception as exc:  # noqa: BLE001
        print(f"    FAILED {type(exc).__name__}: {str(exc)[:120]}")
