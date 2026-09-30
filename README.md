# 📺 Meine IPTV-Playlist

Automatisch gebaute, wöchentlich geprüfte IPTV-Playlist für **iranische & persische Sender**.

Der Build läuft komplett in **GitHub Actions** — du musst nichts installieren.
Jeden Montag werden alle Streams echt getestet und die Listen neu erzeugt.

## 🚀 Playlists

Direkt-Link in jeden IPTV-Player einfügen (VLC, Kodi, TiviMate, IPTV Smarters, OTT Navigator …):

| Playlist | Inhalt | Link |
|---|---|---|
| **Alle Kanäle** | alles, 1 Stream pro Kanal, Geo-Blockierte mit `[IR]` markiert | `https://raw.githubusercontent.com/Momo1530/iptv-iran/main/playlists/momo.m3u` |
| **Nur geprüfte** | ausschließlich getestete, laufende Streams | `https://raw.githubusercontent.com/Momo1530/iptv-iran/main/playlists/momo-verified.m3u` |

**Nach Kategorie** — `playlists/categories/<name>.m3u`:

| Gruppe | Datei |
|---|---|
| IRIB National Networks | `irib-national-networks.m3u` |
| IRIB Provincial Networks | `irib-provincial-networks.m3u` |
| IRIB International Services | `irib-international-services.m3u` |
| Satellite · News & Current Affairs | `satellite-news-current-affairs.m3u` |
| Satellite · Film & Series | `satellite-film-series.m3u` |
| Satellite · General & Variety | `satellite-general-variety.m3u` |
| Satellite · Music | `satellite-music.m3u` |
| Satellite · Sports | `satellite-sports.m3u` |
| Satellite · Children | `satellite-children.m3u` |
| Satellite · Factual, Culture & Lifestyle | `satellite-factual-culture-lifestyle.m3u` |
| Religious · Islamic | `religious-islamic.m3u` |
| Religious · Christian | `religious-christian.m3u` |
| Religious · Other Faiths & Spiritual | `religious-other-faiths-spiritual.m3u` |

## ⚠️ `[IR]` = braucht iranische IP

Die offiziellen **IRIB-Sender** (TV1–TV5, Nasim, Ofogh, Mostanad …) laufen über Telewebion
und sind **geo-blockiert**. Aus Österreich gibt der Server `403` zurück.

Damit sie laufen:
- **iranisches VPN** davor schalten, **oder**
- in einem Player testen, der andere Header sendet

Alle Kanäle **ohne** `[IR]` laufen direkt, ohne VPN.

## 🔍 Wie die Prüfung funktioniert

Reine „Link antwortet mit 200"-Tests sind wertlos — viele Anbieter liefern tote
Playlists mit HTTP 200 aus. Deshalb läuft `probe.py` die **komplette HLS-Kette** durch:

1. Master-Playlist laden
2. Beste Bitrate-Variante wählen
3. Media-Playlist laden
4. **Erstes echtes Videosegment herunterladen**

Nur wenn am Ende Bytes zurückkommen, gilt der Stream als `ok`.

## ⚙️ Anpassen

Alles über **eine** Datei: [`config/channels.yml`](config/channels.yml)

```yaml
# Nur bestimmte Kanäle behalten (leer = alle)
include:
  - "IRIB*"
  - "Persiana*"

# Kanäle entfernen
exclude:
  - "*shopping*"

# Nur geprüfte Streams?
verified_only: false

# Eigene Kanäle (stehen immer ganz oben)
custom:
  - name: "Mein Sender"
    url: "https://example.com/stream.m3u8"
    logo: "https://example.com/logo.png"
    group: "Eigene"

# Stream eines Kanals durch bessere Quelle ersetzen
overrides:
  IRIB1.ir: "https://andere-url.example/stream.m3u8"
```

Nach jeder Änderung committen → GitHub Actions baut die Listen automatisch neu.

## 🛠️ Lokal bauen

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python scripts/sources.py    # Kandidaten sammeln
python scripts/probe.py      # alle Streams echt prüfen (~2 Min)
python scripts/build.py      # Playlists bauen
python scripts/validate.py   # Konsistenz prüfen
```

## 📁 Struktur

```
config/channels.yml      ← hier stellst du alles ein
scripts/sources.py       ← Kandidaten aus den Quellen sammeln
scripts/probe.py         ← Streams echt testen
scripts/build.py         ← Playlists erzeugen
scripts/validate.py      ← Ergebnis prüfen
data/status.json         ← Prüfergebnis pro Stream
data/channels.json       ← die fertige Kanalliste
playlists/               ← die .m3u-Dateien
```

## Quellen

- [shayanline/iptv-iran](https://github.com/shayanline/iptv-iran) — kuratierte Iran-Listen
- [iptv-org/iptv](https://github.com/iptv-org/iptv) — offene IPTV-Datenbank (`ir.m3u`, `ir_telewebion.m3u`)

## Lizenz

MIT — Streams gehören ihren jeweiligen Rechteinhabern.
