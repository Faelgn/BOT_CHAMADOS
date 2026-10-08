#!/usr/bin/env bash
# Backup do codigo do bot (mantem as N copias mais recentes).
set -euo pipefail
export TZ=America/Sao_Paulo

# BASE = raiz do projeto (pasta que contem este script/..)
BASE="${BOT_BASE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DEST="$BASE/backups/codigo"
KEEP=40
mkdir -p "$DEST"
TS="$(date +%Y%m%d-%H%M%S)"
cp -p "$BASE/src/bot.py" "$DEST/bot.py.$TS"
ls -1t "$DEST"/bot.py.* 2>/dev/null | tail -n +$((KEEP+1)) | xargs -r rm -f
echo "backup codigo -> bot.py.$TS"
