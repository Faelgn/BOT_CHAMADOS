"""Testes das funcoes utilitarias do bot (sem dependencia de rede)."""
from datetime import datetime

import bot


# --------------------------------------------------------------------------
# slugify / nomes de arquivo / cabecalhos
# --------------------------------------------------------------------------

def test_slugify_remove_acentos_e_espacos():
    assert bot.slugify("João da Silva") == "joao-da-silva"


def test_slugify_limite_e_fallback():
    assert bot.slugify("") == "usuario"
    assert len(bot.slugify("a" * 100)) <= 25


def test_safe_filename_remove_barras():
    assert bot.safe_filename("../../etc/passwd") == ".._.._etc_passwd"
    assert bot.safe_filename("") == "arquivo"
    assert "/" not in bot.safe_filename("a/b")

def test_sanitize_header_remove_quebras_e_limita():
    assert "\n" not in bot.sanitize_header("assunto\nBcc: x@y.z")
    assert "\r" not in bot.sanitize_header("assunto\rquebra")
    assert bot.sanitize_header("x" * 500) == "x" * 200


# --------------------------------------------------------------------------
# datas
# --------------------------------------------------------------------------

def test_parse_ticket_datetime_formatos():
    assert bot.parse_ticket_datetime("2026-10-08 09:12") == datetime(2026, 10, 8, 9, 12)
    assert bot.parse_ticket_datetime("2026-10-08 09:12:00") == datetime(2026, 10, 8, 9, 12)
    assert bot.parse_ticket_datetime("08-10-2026") == datetime(2026, 10, 8)
    # Sufixo de fuso legado deve ser ignorado
    assert bot.parse_ticket_datetime("2026-10-08 09:12:00 UTC") == datetime(2026, 10, 8, 9, 12)


def test_parse_ticket_datetime_invalido():
    assert bot.parse_ticket_datetime("") is None
    assert bot.parse_ticket_datetime("nao e data") is None


# --------------------------------------------------------------------------
# taxonomia
# --------------------------------------------------------------------------

def test_canon_department_aliases():
    assert bot.canon_department("fiscal") == "Fiscal"
    assert bot.canon_department("TI") == "Tecnologia"
    assert bot.canon_department("departamento pessoal") == "Departamento Pessoal"
    assert bot.canon_department("algo inexistente") == "Outros"


def test_canon_category_aliases():
    assert bot.canon_category("certificado") == "Certificado Digital"
    assert bot.canon_category("VPN") == "Acesso remoto"
    assert bot.canon_category("algo inexistente") == "Outros"


def test_label_de_teste():
    assert bot.canon_department("teste") == bot.TEST_LABEL
    assert bot.canon_category("teste 123") == bot.TEST_LABEL


def test_is_test_ticket():
    assert bot.is_test_ticket({"department": bot.TEST_LABEL}) is True
    assert bot.is_test_ticket({"category": bot.TEST_LABEL}) is True
    assert bot.is_test_ticket({"department": "Fiscal"}) is False


# --------------------------------------------------------------------------
# formatacao
# --------------------------------------------------------------------------

def test_month_label():
    assert bot.month_label(10, 2026) == "Outubro/2026"


def test_average_minutes():
    assert bot.average_minutes([]) == "0 min"
    assert bot.average_minutes([30]) == "30 min"
    assert bot.average_minutes([60, 120]) == "1h 30min"


def test_ticket_thread_name():
    assert bot.ticket_thread_name("João", "Maria") == "M joao"
    assert bot.ticket_thread_name(None) == "atendimento"
