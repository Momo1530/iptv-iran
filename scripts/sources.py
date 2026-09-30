"""Sammelt Kandidaten-Streams aus den in config/channels.yml definierten Quellen."""
from __future__ import annotations

import lib


def main():
    cfg = lib.load_config()
    src = cfg.get("sources") or {}

    targets = []
    sh = src.get("shayanline") or {}
    if sh.get("enabled") and sh.get("url"):
        targets.append(("shayanline", sh["url"]))
    sha = src.get("shayanline_all") or {}
    if sha.get("enabled") and sha.get("url"):
        targets.append(("shayanline-all", sha["url"]))
    io = src.get("iptv_org") or {}
    if io.get("enabled"):
        for u in io.get("urls") or []:
            targets.append(("iptv-org", u))

    if not targets:
        print("! Keine Quellen aktiviert.")
        return

    cands, seen = [], set()
    for source, url in targets:
        st, text = lib.http_text(url, timeout=45)
        if st != 200 or "#EXTM3U" not in text:
            print(f"  ! {source}: HTTP {st} — {url}")
            continue
        items = lib.parse_m3u(text)
        added = 0
        for it in items:
            key = (it["id"], it["url"])
            if key in seen:
                continue
            seen.add(key)
            it["source"] = source
            cands.append(it)
            added += 1
        print(f"  ✓ {source}: {len(items)} Einträge ({added} neu)")

    lib.write_json(lib.BUILD / "candidates.json", cands)
    print(f"→ {len(cands)} Kandidaten in build/candidates.json")


if __name__ == "__main__":
    main()
