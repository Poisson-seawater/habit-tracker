#!/usr/bin/env bash
# Sert la doc en local (le navigateur refuse de lire les .md en file://).
# Usage : bash serve.sh   →   ouvre http://localhost:8000/
set -e
cd "$(dirname "$0")"
PORT="${1:-8000}"
URL="http://localhost:${PORT}/"
echo "Documentation servie sur ${URL}  (Ctrl-C pour arrêter)"
( sleep 1; command -v xdg-open >/dev/null && xdg-open "$URL" >/dev/null 2>&1 ) &
exec python3 -m http.server "$PORT"
