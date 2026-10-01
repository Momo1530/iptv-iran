"""Sammelt automatisch alle verfügbaren Adel-Sendungen (عادل فردوسی‌پور) von football360.ir.

Ablauf:
  1. Live-Sections von football360.ir abrufen
  2. Posts mit Adel filtern (Sende-Sektionen livemoon / gozareshostad)
  3. Direktlink (upload_video_link) per Range-GET prüfen — ältere Folgen werden
     vom Anbieter gelöscht, nur echte Bytes zählen
  4. Ergebnis nach data/adel.json schreiben

build.py liest data/adel.json und hängt die Sendungen als Gruppe "Adel" an.

Wichtig: Schlägt der Abruf fehl, bleibt die VORHERIGE data/adel.json bestehen —
so verschwinden die Sendungen nicht wegen eines einzelnen Netzwerkfehlers.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import re
import sys

import lib

API = "https://football360.ir/api/cms/v2/sections/page/video_live/"
REFERER = "https://football360.ir/"
OUT = lib.DATA / "adel.json"

# Sektionen, in denen Adels Sendungen liegen
SEKTIONEN = {"livemoon", "gozareshostad"}
# Titel, die als Adel-Sendung gelten
ADEL_RE = re.compile(r"عادل\s*فردوسی|گزارش عادل")

WORKERS = 6
MIN_BYTES = 204800          # 200 KB – kleiner ist eine Fehlerseite
MAX_ALT = 40                # so viele Sendungen höchstens prüfen


def hole_sections():
    """Alle Seiten der Live-Sections abrufen."""
    posts = []
    for offset in (0, 20, 40, 60):
        st, txt = lib.http_text(
            f"{API}?offset={offset}&limit=20",
            timeout=25,
            headers={"Referer": REFERER, "Accept": "application/json"},
        )
        if st != 200 or not txt:
            continue
        try:
            d = json.loads(txt)
        except ValueError:
            continue
        for sec in d.get("data", []):
            if sec.get("key") in SEKTIONEN:
                for p in sec.get("posts", []):
                    posts.append(p)
    return posts


def titel(p):
    return (p.get("title") or "").strip()


def link(p):
    pm = p.get("primary_media")
    if isinstance(pm, dict):
        v = pm.get("upload_video_link")
        if isinstance(v, str) and v.startswith("http"):
            return v
    return ""


def pruefe(item):
    """Range-GET: fließen echte Bytes?"""
    t, url = item
    st, hdrs, body = lib.http(url, timeout=30, max_bytes=MIN_BYTES + 1)
    ct = (hdrs.get("Content-Type") or "").lower()
    ok = st in (200, 206) and len(body) >= MIN_BYTES and "html" not in ct
    return {"name": aufraeumen(t), "url": url, "status": st, "bytes": len(body), "ok": ok}


def aufraeumen(t):
    """'لایو ۳۶۰ با عادل فردوسی‌پور | خانه‌ای برای همیشه!' → 'Adel · خانه‌ای برای همیشه!'"""
    n = t
    n = re.sub(r"^لایو\s*۳۶۰\s*با\s*عادل\s*فردوسی‌پور\s*[|؛،]?\s*", "Adel · ", n)
    n = n.replace("لایو ۳۶۰ با عادل فردوسی‌پور", "Adel")
    n = n.replace("خلاصه بازی", "Highlights:")
    n = n.replace("تماشای کامل بازی", "Spiel komplett:")
    n = re.sub(r"با گزارش عادل فردوسی‌پور", "(Adel)", n)
    n = n.replace("|", "·")
    n = re.sub(r"\s{2,}", " ", n).strip(" ·")
    return n or t


def main():
    alt = []
    if OUT.exists():
        try:
            alt = json.loads(OUT.read_text(encoding="utf-8"))
        except ValueError:
            alt = []

    posts = hole_sections()
    if not posts:
        print(f"✗ Keine Posts abrufbar — behalte {len(alt)} Sendungen aus dem letzten Lauf")
        sys.exit(0 if alt else 1)

    # Adel-Posts, eindeutig nach Titel
    kandidaten = {}
    for p in posts:
        t = titel(p)
        u = link(p)
        if not u or not ADEL_RE.search(t):
            continue
        kandidaten.setdefault(t, u)

    # Nur die neuesten N prüfen (die alten sind ohnehin gelöscht)
    items = list(kandidaten.items())[:MAX_ALT]
    print(f"Adel-Posts gefunden: {len(kandidaten)} — prüfe {len(items)}")

    ergebnis = []
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for r in ex.map(pruefe, items):
            print(f"   {'✓' if r['ok'] else '✗'} {r['status']:>4} {r['bytes']:>9} B  {r['name'][:56]}")
            if r["ok"]:
                ergebnis.append({"name": r["name"], "url": r["url"]})

    if not ergebnis:
        print(f"✗ Keine laufende Sendung — behalte {len(alt)} aus dem letzten Lauf")
        sys.exit(0 if alt else 1)

    lib.write_json(OUT, ergebnis)
    print(f"\n✓ {len(ergebnis)} Adel-Sendungen → data/adel.json")


if __name__ == "__main__":
    main()
