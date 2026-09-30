"""Prüft die erzeugten Playlists auf Konsistenz, bevor sie veröffentlicht werden."""
from __future__ import annotations

import sys

import lib


def main():
    problems = []
    for name in ("momo.m3u", "momo-verified.m3u"):
        p = lib.PLAYLISTS / name
        if not p.exists():
            problems.append(f"{name} fehlt")
            continue
        text = p.read_text(encoding="utf-8")
        if not text.startswith("#EXTM3U"):
            problems.append(f"{name}: kein #EXTM3U-Header")
            continue
        items = lib.parse_m3u(text)
        if not items:
            problems.append(f"{name}: keine Kanäle")
            continue
        urls = [i["url"] for i in items]
        bad = [u for u in urls if not u.startswith("http")]
        if bad:
            problems.append(f"{name}: {len(bad)} ungültige URLs")
        dup = {u for u in urls if urls.count(u) > 1}
        if dup:
            problems.append(f"{name}: {len(dup)} doppelte URLs")
        ids = [i["id"] for i in items]
        dupids = {i for i in ids if ids.count(i) > 1}
        if dupids:
            problems.append(f"{name}: doppelte Kanal-IDs {sorted(dupids)[:5]}")
        print(f"  {name}: {len(items)} Kanäle, {len(set(urls))} eindeutige URLs")

    if problems:
        for p in problems:
            print("✗", p)
        sys.exit(1)
    print("✓ Validierung ok")


if __name__ == "__main__":
    main()
