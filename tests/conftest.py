"""Configuracao compartilhada dos testes.

As variaveis de ambiente e o diretorio de trabalho sao definidos ANTES de
importar ``src/bot.py``, porque o modulo exige as variaveis no momento do
import e grava arquivos de dados no diretorio atual.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Diretorio temporario isolado para os dados gerados nos testes
_TMP = Path(tempfile.mkdtemp(prefix="bot_chamados_tests_"))
os.chdir(_TMP)

_FAKE_ID = "123456789012345678"
os.environ.update(
    {
        "DISCORD_TOKEN": "test-token",
        "GUILD_ID": _FAKE_ID,
        "CHANNEL_PANEL_ID": _FAKE_ID,
        "CHANNEL_LOGS_ID": _FAKE_ID,
        "CHANNEL_QUEUE_ID": _FAKE_ID,
        "CHANNEL_DASHBOARD_ID": _FAKE_ID,
        "ROLE_SUPPORT_ID": _FAKE_ID,
        "ROLE_ADMIN_ID": _FAKE_ID,
        "SMTP_HOST": "localhost",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@example.com",
        "SMTP_PASS": "secret",
        "EMAIL_FROM": "test@example.com",
        "EMAIL_TO": "dest@example.com",
        "DATA_FILE": str(_TMP / "ticket_data.json"),
        "ATTACHMENTS_DIR": str(_TMP / "attachments"),
    }
)
