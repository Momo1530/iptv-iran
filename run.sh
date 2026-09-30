#!/usr/bin/env bash
# Kompletter Rebuild: sammeln → prüfen → bauen → validieren
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  . .venv/bin/activate
  pip install -q -r requirements.txt
else
  . .venv/bin/activate
fi

echo "═══ 1/4  Kandidaten sammeln ═══"; python scripts/sources.py
echo "═══ 2/4  Streams prüfen ═══";     python scripts/probe.py
echo "═══ 3/4  Playlists bauen ═══";    python scripts/build.py
echo "═══ 4/4  Validieren ═══";         python scripts/validate.py
echo "✅ Fertig."
