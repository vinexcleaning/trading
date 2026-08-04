"""Show the shape of one cached whole-repo archive so the scanner can be written
against the real structure rather than a guess."""
import json
import sys
from pathlib import Path

CACHE = Path(r"C:\Users\vinig\trading\signal-github\cache")

p = sorted(CACHE.glob("*.arch.json"))[0]
d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
print("file:", p.name, f"{p.stat().st_size/1024:.0f} KB")
print("type:", type(d).__name__)
if isinstance(d, dict):
    for k, v in d.items():
        if isinstance(v, (list, dict)):
            print(f"  {k}: {type(v).__name__} len={len(v)}")
            if isinstance(v, list) and v:
                print(f"     [0] = {str(v[0])[:200]}")
            if isinstance(v, dict) and v:
                k0 = next(iter(v))
                print(f"     {k0!r} -> {str(v[k0])[:200]}")
        else:
            print(f"  {k}: {str(v)[:200]}")
