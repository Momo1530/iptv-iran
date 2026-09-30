"""Baut die fertigen Playlists aus Kandidaten + Prüfergebnis + Konfiguration."""
from __future__ import annotations

from collections import Counter

import re

import lib


def status_rank(status):
    if status == "ok":
        return 0
    if status == "geo":
        return 3
    return 2


QUALITY_RANK = {"4k": 4, "2160p": 4, "uhd": 4, "fhd": 3, "1080p": 3, "hd": 2, "720p": 2}


def quality_rank(channel):
    q = (channel.get("quality") or "").lower()
    return QUALITY_RANK.get(q, 1 if q else 0)


def pick_better(a, b):
    """Wählt zwischen zwei Streams desselben Kanals den besseren."""
    def key(c):
        return (status_rank(c.get("status")), 0 if c.get("logo") else 1, -quality_rank(c))
    return a if key(a) <= key(b) else b


def group_rank(group, cfg):
    order = cfg.get("group_order") or []
    try:
        return order.index(group)
    except ValueError:
        return len(order) + 1


# Kanäle ohne Gruppenangabe (z. B. iptv-org) nach Namen einsortieren.
NAME_RULES = [
    ("Satellite · News & Current Affairs",
     ("news", "khabar", "press", "al alam", "alalam", "irinn", "rt ", "cnn", "bbc")),
    ("Satellite · Sports",
     ("sport", "varzesh", "football", "behboud", "wrestl")),
    ("Satellite · Film & Series",
     ("film", "movie", "cinema", "series", "show", "serial", "namayesh", "ava ", "salamat")),
    ("Satellite · Music",
     ("music", "musiqi", "song", "javan", "radio javan", "navahang", "moosighi")),
    ("Satellite · Children",
     ("kids", "child", "koodak", "toon", "animation", "pooya", "omid", "babyt")),
    ("Religious · Islamic",
     ("quran", "islam", "mahdi", "kawthar", "wilayah", "assirat", "alzahra", "nabi", "velayat")),
    ("Religious · Christian",
     ("christ", "jesus", "gospel", "church", "sat7", "catholic")),
]


def base_id(channel):
    """'irib1.ir@SD' → 'irib1.ir'  (iptv-org hängt Qualität an)"""
    return (channel.get("id") or "").split("@")[0].strip().lower()


def name_key(channel):
    """Namensschlüssel ohne Rauschen: 'IRIB TV1' / 'IRIB1' → 'irib1'"""
    raw = f'{channel.get("name", "")}'
    raw = raw.lower().replace("tv", "").replace("irib", "irib")
    return re.sub(r"[^a-z0-9]", "", raw)


def categorize(channel, group_by_id, group_by_name):
    """Gruppe bestimmen: vorhandene → Kanal-ID → Name → Heuristik."""
    g = channel.get("group")
    if g and g != "Other":
        return g
    for table, key in ((group_by_id, base_id(channel)), (group_by_name, name_key(channel))):
        hit = table.get(key)
        if hit and hit != "Other":
            return hit
    haystack = f'{channel.get("name", "")} {channel.get("label", "")}'.lower()
    for group, keys in NAME_RULES:
        if any(k in haystack for k in keys):
            return group
    return g or "Other"


def main():
    cfg = lib.load_config()
    cands = lib.read_json(lib.BUILD / "candidates.json", [])
    status = lib.read_json(lib.DATA / "status.json", {}) or {}

    include = cfg.get("include") or []
    exclude = cfg.get("exclude") or []
    overrides = cfg.get("overrides") or {}
    custom = cfg.get("custom") or []
    verified_only = bool(cfg.get("verified_only"))

    for c in cands:
        if c["id"] in overrides:
            c["url"] = overrides[c["id"]]

    kept = []
    for c in cands:
        if include and not any(lib.matches(p, c["id"], c["name"], c["label"]) for p in include):
            continue
        if exclude and any(lib.matches(p, c["id"], c["name"], c["label"]) for p in exclude):
            continue
        c["status"] = (status.get(c["url"]) or {}).get("status", "unbekannt")
        kept.append(c)

    # Vererbungstabellen: Kanal-ID/Name → Gruppe, aus allen Kandidaten mit
    # echter Gruppenangabe. So bekommen iptv-org-Kanäle ohne Gruppe
    # dieselbe Kategorie wie ihr Gegenstück in der shayanline-Liste.
    group_by_id, group_by_name = {}, {}
    for c in cands:
        if c.get("group") and c["group"] != "Other":
            group_by_id.setdefault(base_id(c), c["group"])
            group_by_name.setdefault(name_key(c), c["group"])
    for c in cands:
        c["group"] = categorize(c, group_by_id, group_by_name)

    # Auf Kanal-Ebene deduplizieren: derselbe Kanal aus mehreren Quellen
    # wird auf EINEN Stream reduziert (bester Status, dann beste Qualität).
    #
    # Der Schlüssel enthält den Namensschlüssel NUR, wenn die Quelle keine
    # echte tvg-id hatte. Sonst liegt derselbe Kanal unter derselben ID mit
    # unterschiedlichen Namen vor — iptv-org nennt ihn "Nasim", shayanline
    # "IRIB Nasim" — und würde fälschlich zweimal geführt.
    channels = {}
    for c in kept:
        if c.get("synthetic_id"):
            key = ("~name", name_key(c))
        else:
            key = ("id", base_id(c))
        cur = channels.get(key)
        channels[key] = c if cur is None else pick_better(cur, c)
    chosen = list(channels.values())

    # Sicherheitsnetz: identische Stream-URLs nie doppelt ausliefern
    by_url = {}
    for c in chosen:
        cur = by_url.get(c["url"])
        by_url[c["url"]] = c if cur is None else pick_better(cur, c)
    chosen = list(by_url.values())

    if verified_only:
        chosen = [c for c in chosen if c["status"] == "ok"]

    # Eigene Kanäle zuerst
    own = []
    for i, cu in enumerate(custom, 1):
        own.append({
            "id": cu.get("id") or f"custom-{i}",
            "name": cu.get("name") or f"Eigener {i}",
            "label": cu.get("name") or "",
            "logo": cu.get("logo", ""),
            "group": cu.get("group", "Eigene"),
            "language": cu.get("language", ""),
            "quality": cu.get("quality", ""),
            "url": cu["url"],
            "status": "ok",
        })

    final = own + sorted(chosen, key=lambda c: (group_rank(c["group"], cfg), c["name"].lower()))

    # Eindeutige tvg-IDs erzwingen: manche Quellen vergeben dieselbe ID an
    # zwei verschiedene Kanäle. Die ID bleibt stabil (kein Zufall), damit
    # Player ihre Favoriten beim Neuaufbau nicht verlieren.
    used = {}
    for c in final:
        base = c.get("id") or lib.slug(c["name"])
        n = used.get(base, 0) + 1
        used[base] = n
        c["id"] = base if n == 1 else f"{base}-{n}"

    # Geo-blockierte im Namen markieren.
    # Achtung: manche Quellen schreiben "[IR]" schon selbst ins Label (aus
    # ihrer eigenen Sicht). Diese Fremdmarkierung wird zuerst entfernt,
    # damit nur UNSER Prüfergebnis zählt — sonst steht [IR] an Sendern,
    # die hier nachweislich laufen.
    for c in final:
        label = re.sub(r"\s*\[IR\]\s*", " ", c.get("label") or c["name"]).strip()
        c["label"] = f"{label} [IR]" if c["status"] == "geo" else label

    n = lib.write_m3u(final, lib.PLAYLISTS / "momo.m3u",
                      "Deine IPTV — alle Kanäle (1 Stream je Kanal)")
    ok_only = own + [c for c in final if c["status"] == "ok"]
    lib.write_m3u(ok_only, lib.PLAYLISTS / "momo-verified.m3u",
                  "Deine IPTV — nur geprüfte, laufende Streams")

    # Optional: ohne iranisches VPN sind die geo-blockierten Sender nutzlos
    if cfg.get("drop_geo"):
        n = lib.write_m3u([c for c in final if c["status"] != "geo"],
                          lib.PLAYLISTS / "momo.m3u",
                          "Deine IPTV — ohne geo-blockierte Sender")

    cats = {}
    for c in final:
        cats.setdefault(c["group"], []).append(c)
    for g, items in cats.items():
        lib.write_m3u(items, lib.PLAYLISTS / "categories" / f"{lib.slug(g)}.m3u", g)

    lib.write_json(lib.DATA / "channels.json", final)

    print(f"✓ {n} Kanäle            → playlists/momo.m3u")
    print(f"✓ {len(ok_only)} geprüft ok       → playlists/momo-verified.m3u")
    print(f"✓ {len(cats)} Kategorien      → playlists/categories/")
    print("  Status:", dict(Counter(c["status"] for c in final).most_common()))


if __name__ == "__main__":
    main()
