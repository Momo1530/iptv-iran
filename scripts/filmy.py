"""Baut die Film- & Serien-Playlists (CZ/SK).

Quelle: config/filmy-source.m3u — Kurzlink-Liste (bit.ly / lnk.sk / wsfiles),
die auf echte Video-Dateien verweist.

Ablauf:
  1. Kurzlink auflösen (Redirects folgen) und Endziel echt anprüfen
  2. HTML-/Webseiten-Ziele aussortieren (kein abspielbares Video)
  3. Dateigröße per HEAD holen
  4. Nur lebende Titel in die Playlists schreiben, Filme und Serien getrennt

Ergebnis:
  playlists/filmy.m3u    — Filme
  playlists/serialy.m3u  — Serienfolgen
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import re
import sys
from collections import Counter

import lib

SOURCE = lib.ROOT / "config" / "filmy-source.m3u"
REPORT = lib.DATA / "filmy-report.json"
OUT_FILM = lib.PLAYLISTS / "filmy.m3u"
OUT_SERIE = lib.PLAYLISTS / "serialy.m3u"

WORKERS = 12
UA = lib.UA

# Erkennung von Serienfolgen im Titel
SERIE_RE = re.compile(
    r"\b(E\d{1,3}|S\d{1,2}\s?E\d{1,3}|Dil|dil|vsech|seria|séria|season|epizoda|diel)\b",
    re.IGNORECASE,
)


def read_source():
    """→ [(name, kurzlink)]"""
    text = SOURCE.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    out = []
    for i, l in enumerate(lines):
        if l.startswith("#EXTINF"):
            name = l.rsplit(",", 1)[-1].strip()
            url = next(
                (x.strip() for x in lines[i + 1 : i + 3] if x.strip().startswith(("http", "rtmp"))),
                "",
            )
            if url:
                out.append((name, url))
    return out


def curl(args, timeout=30):
    import subprocess

    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except Exception:
        return 1, ""


def check(item):
    """Kurzlink auflösen und Endziel per Range-GET (300 KB) beweisen."""
    name, src = item
    rc, out = curl([
        "curl", "-s", "-o", "/dev/null", "-r", "0-307199", "-m", "25",
        "-H", "User-Agent: " + UA, "-L",
        "-w", "%{http_code}|%{size_download}|%{content_type}|%{url_effective}", src,
    ])
    p = (out or "").split("|")
    while len(p) < 4:
        p.append("")
    code, got, ct, final = p[0], p[1], p[2], p[3]
    try:
        n = int(got)
    except ValueError:
        n = 0
    # Echtes Video: bytes fließen UND kein HTML (Web-Verifikationsseite)
    ok = code in ("200", "206") and n >= 204800 and "html" not in ct.lower()
    return {"name": name, "src": src, "code": code, "ct": ct,
            "got": n, "final": final or src, "ok": ok}


def length(url):
    """Dateigröße per HEAD (Redirects folgen ⇒ echte content-length)."""
    rc, out = curl(["curl", "-s", "-I", "-L", "-m", "20", "-H", "User-Agent: " + UA, url])
    for l in (out or "").split("\n"):
        if l.lower().startswith("content-length:"):
            v = l.split(":", 1)[1].strip()
            if v.isdigit():
                return int(v)
    return 0


def pretty(name):
    """Aufräumen: '*2020 Titel (2020)' → 'Titel (2020)'"""
    n = re.sub(r"^\*+\s*", "", name).strip()
    n = re.sub(r"^(19|20)\d{2}\s+", "", n).strip()
    return n or name.strip("* ")


def main():
    if not SOURCE.exists():
        print(f"✗ Quelle fehlt: {SOURCE}")
        sys.exit(1)

    ent = read_source()
    print(f"Quelle: {len(ent)} Einträge")

    results = []
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for k, r in enumerate(ex.map(check, ent), 1):
            results.append(r)
            if k % 200 == 0:
                print(f"  {k}/{len(ent)}  live={sum(1 for x in results if x['ok'])}", flush=True)

    live = [r for r in results if r["ok"]]
    print(f"  live: {len(live)}")

    print("Dateigrößen holen …")
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for r, size in zip(live, ex.map(lambda x: length(x["final"]), live)):
            r["bytes"] = size

    json.dump(results, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    films, series = [], []
    for r in live:
        r["title"] = pretty(r["name"])
        (series if SERIE_RE.search(r["title"]) else films).append(r)

    def write(items, path, group):
        seen, kept = set(), []
        for r in items:
            u = r["final"]
            if u in seen:
                continue
            seen.add(u)
            kept.append({
                "id": lib.slug(f'{r["title"]}-{len(seen)}'),
                "name": r["title"],
                "label": r["title"],
                "logo": "",
                "group": group,
                "url": u,
            })
        lib.write_m3u(kept, path, group)
        return len(kept)

    nf = write(films, OUT_FILM, "Filmy CZ/SK")
    ns = write(series, OUT_SERIE, "Serialy CZ/SK")

    tot = sum(r.get("bytes", 0) for r in live)
    print(f"\n✓ {nf:4d} Filme          → playlists/filmy.m3u")
    print(f"✓ {ns:4d} Serienfolgen   → playlists/serialy.m3u")
    print(f"  Volumen: {tot / 1e9:.1f} GB")
    print("  Codes:", dict(Counter(r["code"] for r in results).most_common(6)))


if __name__ == "__main__":
    main()
