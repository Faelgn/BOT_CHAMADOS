#!/usr/bin/env bash
# Backup validado da base JSON de chamados (mantem as N copias mais recentes).
set -euo pipefail
export TZ=America/Sao_Paulo

# BASE = raiz do projeto (pasta que contem este script/..)
BASE="${BOT_BASE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SRC="${DATA_FILE:-$BASE/ticket_data.json}"
DEST="${BOT_BACKUP_DIR:-$BASE/backups/dados}"
KEEP=30
mkdir -p "$DEST"
TS="$(date +%Y%m%d-%H%M%S)"
TMP="$DEST/.ticket_data_${TS}.tmp"
cp -p "$SRC" "$TMP"
if python3 -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8'))" "$TMP" 2>/dev/null; then
    mv -f "$TMP" "$DEST/ticket_data_${TS}.json"
    ls -1t "$DEST"/ticket_data_*.json 2>/dev/null | tail -n +$((KEEP+1)) | xargs -r rm -f
    echo "$(date '+%Y-%m-%d %H:%M:%S') backup ok -> ticket_data_${TS}.json"
else
    rm -f "$TMP"
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERRO: backup invalido (json corrompido); mantido o anterior" >&2
    exit 1
fi
