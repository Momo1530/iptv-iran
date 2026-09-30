"""Prüft jeden Stream ECHT — läuft die HLS-Kette bis zum Media-Segment durch.

Ein Stream gilt nur als 'ok', wenn am Ende ein echter Videosegment-Download
mit Bytes zurückkommt. Reine „Link erreichbar"-Tests reichen nicht, weil
viele Anbieter tote Playlists mit HTTP 200 ausliefern.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import re
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urljoin

import lib

MAX_DEPTH = 4


def _bandwidth(tag):
    m = re.search(r"BANDWIDTH=(\d+)", tag or "")
    return int(m.group(1)) if m else 0


def walk(url, depth=0):
    """Folgt der Playlist-Kette → (segment_url, 'ok') oder (None, fehlergrund)."""
    if depth > MAX_DEPTH:
        return None, "zu-tief"
    st, _, body = lib.http(url, timeout=12, max_bytes=400_000)
    if st in (401, 403, 451):
        return None, "geo"
    # 206 = Partial Content: der Range-Header oben schneidet die Antwort ab,
    # das ist bei Playlists genauso gültig wie 200.
    if st not in (200, 206) or not body:
        return None, f"http-{st}"
    text = body.decode("utf-8", "ignore")
    if "#EXTM3U" not in text:
        return None, "kein-hls"

    # Master-Playlist → beste Variante wählen
    if "#EXT-X-STREAM-INF" in text:
        lines = text.splitlines()
        variants = []
        for i, l in enumerate(lines):
            if l.startswith("#EXT-X-STREAM-INF"):
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not lines[j].startswith("#"):
                        variants.append((l, lines[j].strip()))
                        break
        if not variants:
            return None, "master-ohne-variante"
        variants.sort(key=lambda v: _bandwidth(v[0]), reverse=True)
        return walk(urljoin(url, variants[0][1]), depth + 1)

    # Media-Playlist → erstes Segment
    seg = None
    for l in text.splitlines():
        if l.strip() and not l.startswith("#"):
            seg = urljoin(url, l.strip())
            break
    if not seg:
        return None, "kein-segment"

    st2, _, data = lib.http(seg, timeout=12, max_bytes=4096)
    if st2 in (401, 403, 451):
        return None, "geo"
    if st2 in (200, 206) and len(data) > 188:
        return seg, "ok"
    return None, f"segment-{st2}"


def probe(url):
    seg, verdict = walk(url)
    return {
        "url": url,
        "status": verdict,
        "segment": seg or "",
        "checked": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main():
    cands = lib.read_json(lib.BUILD / "candidates.json", [])
    urls = sorted({c["url"] for c in cands})
    print(f"Prüfe {len(urls)} eindeutige Streams (das dauert ~1–2 Min) …")

    old = lib.read_json(lib.DATA / "status.json", {}) or {}
    results = {}

    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        for res in ex.map(probe, urls):
            u = res["url"]
            prev = old.get(u, {})
            res["first_seen"] = prev.get("first_seen", res["checked"])
            if res["status"] == "ok":
                res["last_ok"] = res["checked"]
                res["fails"] = 0
            else:
                res["last_ok"] = prev.get("last_ok", "")
                res["fails"] = prev.get("fails", 0) + 1
            results[u] = res

    lib.write_json(lib.DATA / "status.json", results)
    c = Counter(r["status"] for r in results.values())
    ok = c.get("ok", 0)
    print(f"→ data/status.json  |  Ergebnis: {ok} ok, {c.get('geo', 0)} geo-blockiert, {len(urls) - ok - c.get('geo', 0)} tot")
    print("   Detail:", dict(c.most_common()))


if __name__ == "__main__":
    main()
