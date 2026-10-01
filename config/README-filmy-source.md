# Quell-Liste für die Film- & Serien-Playlists (`scripts/filmy.py`).

Diese Datei wird **nicht** ausgeliefert — sie ist die Rohliste mit Kurzlinks
(bit.ly / lnk.sk / wsfiles), aus der `playlists/filmy.m3u` und
`playlists/serialy.m3u` gebaut werden.

## Herkunft

- Ursprung: `github.com/MichalDela/IPTV-FILMY-2021` (Stand 2023-12-26)
- 1.237 Einträge, CZ/SK Filme und Serienfolgen
- Die Links sind **Kurz-/Proxy-Links** (bit.ly 1.078, lnk.sk 97, wsfiles.cz 44),
  die beim Abruf auf echte Video-Dateien weiterleiten.

## Wie `filmy.py` damit umgeht

1. **Auflösen:** jeder Kurzlink wird per `curl -L` verfolgt bis zum Endziel
2. **Beweisen:** Range-GET über 300 KB — fließen Bytes, ist der Titel lebend
3. **Aussortieren:** HTML-Ziele (Web-Verifikationsseiten) zählen als tot
4. **Messen:** Dateigröße per HEAD `content-length`
5. **Trennen:** Serienfolgen (Erkennung an `E01`, `S01E02`, `dil`, `všechn`) → `serialy.m3u`

## Beim Austausch der Quelle

Wenn diese Datei durch eine aktuellere Liste ersetzt wird:

- Format beibehalten: `#EXTINF`-Zeile (Titel nach dem Komma) + Folgezeile mit URL
- Kurzlinks sind ausdrücklich erlaubt — sie werden automatisch aufgelöst
- Direkte Video-URLs funktionieren genauso

Danach neu bauen:

```bash
cd scripts && python filmy.py
```

## Stand

- Letzter Bau: 888 von 1.230 Einträgen lebend → 310 Filme + 205 Serienfolgen
- Aussortiert: 150× HTTP 403, 121× HTTP 404, 9× HTTP 200 ohne Video-Bytes
- Volumen: ~789 GB
