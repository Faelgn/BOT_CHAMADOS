import os
import re
import json
import ssl
import html
import asyncio
import mimetypes
import smtplib
import unicodedata
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional
from email.message import EmailMessage
from email.utils import make_msgid

import discord
from discord.ext import commands, tasks

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variável de ambiente ausente: {name}")
    return value


TOKEN = required_env("DISCORD_TOKEN")
GUILD_ID = int(required_env("GUILD_ID"))
CATEGORY_OPEN_ID = int(os.getenv("CATEGORY_OPEN_ID") or 0)
CATEGORY_CLOSED_ID = int(os.getenv("CATEGORY_CLOSED_ID") or 0)
CHANNEL_PANEL_ID = int(required_env("CHANNEL_PANEL_ID"))
CHANNEL_LOGS_ID = int(required_env("CHANNEL_LOGS_ID"))
ROLE_SUPPORT_ID = int(required_env("ROLE_SUPPORT_ID"))
ROLE_ADMIN_ID = int(os.getenv("ROLE_ADMIN_ID", str(ROLE_SUPPORT_ID)))
CHANNEL_QUEUE_ID = int(required_env("CHANNEL_QUEUE_ID"))
CHANNEL_TICKETS_ID = int(os.getenv("CHANNEL_TICKETS_ID") or 0) or CHANNEL_QUEUE_ID
CHANNEL_THREADS_ID = int(os.getenv("CHANNEL_THREADS_ID") or 0) or CHANNEL_PANEL_ID
CHANNEL_DASHBOARD_ID = int(required_env("CHANNEL_DASHBOARD_ID"))
SMTP_HOST = required_env("SMTP_HOST")
SMTP_PORT = int(required_env("SMTP_PORT"))
SMTP_USER = required_env("SMTP_USER")
SMTP_PASS = required_env("SMTP_PASS")
EMAIL_FROM = required_env("EMAIL_FROM")
EMAIL_TO = required_env("EMAIL_TO")
SMTP_SSL_MODE = os.getenv("SMTP_SSL_MODE", "auto").lower()

DATA_FILE = os.getenv("DATA_FILE", "ticket_data.json")
ATTACHMENTS_DIR = Path(os.getenv("ATTACHMENTS_DIR", "ticket_email_attachments"))
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Limite de tamanho por anexo (protecao contra exaustao de disco).
MAX_ATTACHMENT_BYTES = int(os.getenv("MAX_ATTACHMENT_BYTES", str(25 * 1024 * 1024)))

STATUS_LABELS = {
    "novo": "Novo na fila",
    "em_andamento": "Em andamento",
    "aguardando_usuario": "Aguardando usuário",
    "concluido": "Concluído",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

MONTH_NAMES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def month_label(month: int, year: int) -> str:
    return f"{MONTH_NAMES.get(month, month)}/{year}"


# ---------------------------------------------------------------------------
# Taxonomia estruturada (substitui campos de texto livre do formulario)
# ---------------------------------------------------------------------------

DEPARTMENTS = [
    "Fiscal",
    "Contábil",
    "Simples Nacional",
    "Lucro Presumido",
    "Trabalhista",
    "Departamento Pessoal",
    "BPO",
    "Tecnologia",
    "Administrativo",
    "Financeiro",
    "Comercial",
    "Diretoria",
    "Outros",
]

CATEGORIES = [
    "Certificado Digital",
    "Questor",
    "Sistema Interno",
    "Tareffa",
    "Rede / Pasta de rede",
    "Acesso remoto",
    "E-mail",
    "Impressora",
    "Computador / Hardware",
    "Telefonia",
    "Backup",
    "SharePoint",
    "Liberação de empresa/acesso",
    "Outros",
]

TEST_LABEL = "Teste"


def normalize_key(text: str) -> str:
    """Minusculas, sem acentos e sem pontuacao, para agrupar variacoes de escrita."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return text


DEPT_ALIASES = {
    "fiscal": "Fiscal",
    "fiscal presumido": "Fiscal",
    "presumido fiscal": "Fiscal",
    "contabil": "Contábil",
    "contabilidade": "Contábil",
    "contbail": "Contábil",
    "contabil presumido": "Contábil",
    "simples nacional": "Simples Nacional",
    "simples": "Simples Nacional",
    "sinples": "Simples Nacional",
    "usn": "Simples Nacional",
    "presumido": "Lucro Presumido",
    "lucro presumido": "Lucro Presumido",
    "presumid0": "Lucro Presumido",
    "trabalhista": "Trabalhista",
    "tabralhista": "Trabalhista",
    "trabalhado": "Trabalhista",
    "dp": "Departamento Pessoal",
    "dp1": "Departamento Pessoal",
    "pessoal": "Departamento Pessoal",
    "departamento pessoal": "Departamento Pessoal",
    "dep pessoal": "Departamento Pessoal",
    "d pessoal": "Departamento Pessoal",
    "setor pessoal": "Departamento Pessoal",
    "bpo": "BPO",
    "tecnologia": "Tecnologia",
    "ti": "Tecnologia",
    "adm": "Administrativo",
    "administrativo": "Administrativo",
    "financeiro": "Financeiro",
    "comercial": "Comercial",
    "diretoria": "Diretoria",
}

CAT_ALIASES = {
    "certificado": "Certificado Digital",
    "certificados": "Certificado Digital",
    "certificado digital": "Certificado Digital",
    "liberacao de certificado": "Certificado Digital",
    "liberacao de certificado digital": "Certificado Digital",
    "sistema certificados": "Certificado Digital",
    "sistema de certificados": "Certificado Digital",
    "certify": "Certificado Digital",
    "questor": "Questor",
    "questor zen": "Questor",
    "questor folha": "Questor",
    "sistema questor": "Questor",
    "zen": "Questor",
    "interno": "Sistema Interno",
    "sistema": "Sistema Interno",
    "sistema interno": "Sistema Interno",
    "tareffa": "Tareffa",
    "tareffas": "Tareffa",
    "tarefas": "Tareffa",
    "sistema tareffa": "Tareffa",
    "rede": "Rede / Pasta de rede",
    "pasta na rede": "Rede / Pasta de rede",
    "pastas da rede": "Rede / Pasta de rede",
    "acesso remoto": "Acesso remoto",
    "remoto": "Acesso remoto",
    "sharepoint": "SharePoint",
    "email": "E-mail",
    "e mail": "E-mail",
    "computador": "Computador / Hardware",
    "hardware": "Computador / Hardware",
    "notebook": "Computador / Hardware",
    "monitor": "Computador / Hardware",
    "impressora": "Impressora",
    "telefonia": "Telefonia",
    "backup": "Backup",
    "home office": "Acesso remoto",
    "vpn": "Acesso remoto",
    "pasta": "Rede / Pasta de rede",
    "pastas": "Rede / Pasta de rede",
    "drive": "Rede / Pasta de rede",
    "onedrive": "Rede / Pasta de rede",
    "ecac": "Liberação de empresa/acesso",
    "liberacao de empresa": "Liberação de empresa/acesso",
    "liberacao de empresas": "Liberação de empresa/acesso",
    "liberar empresa": "Liberação de empresa/acesso",
    "liberar empresas": "Liberação de empresa/acesso",
    "liberacao de acesso": "Liberação de empresa/acesso",
    "liberar no questor": "Liberação de empresa/acesso",
    "liberar empresa no questor": "Liberação de empresa/acesso",
    "liberacao de empresa no questor": "Liberação de empresa/acesso",
}


def canon_department(raw: str) -> str:
    key = normalize_key(raw)
    if not key:
        return "Outros"
    if key.startswith("teste"):
        return TEST_LABEL
    return DEPT_ALIASES.get(key, "Outros")


def canon_category(raw: str) -> str:
    key = normalize_key(raw)
    if not key:
        return "Outros"
    if key.startswith("teste"):
        return TEST_LABEL
    return CAT_ALIASES.get(key, "Outros")


def is_test_ticket(ticket: dict) -> bool:
    return ticket.get("department") == TEST_LABEL or ticket.get("category") == TEST_LABEL


async def notify_user(user: Optional[discord.abc.User], text: str):
    if user is None:
        return
    try:
        await user.send(text)
    except Exception:
        pass


def parse_ticket_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    # Compatibilidade com registros legados que gravavam sufixo de fuso
    for suffix in (" UTC", " GMT", "Z"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d-%m-%Y %H:%M", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def filter_tickets_by_month_year(month: int, year: int) -> list[dict]:
    tickets = []
    for ticket in store.data.get("tickets", {}).values():
        if is_test_ticket(ticket):
            continue
        created_dt = parse_ticket_datetime(ticket.get("created_at", ""))
        if created_dt and created_dt.month == month and created_dt.year == year:
            tickets.append(ticket)
    return tickets


def build_dashboard_embeds_for_month(guild: discord.Guild, month: int, year: int) -> list[discord.Embed]:
    tickets = filter_tickets_by_month_year(month, year)
    now = now_local()
    opened = len(tickets)
    concluded = [t for t in tickets if t.get("status") == "concluido"]
    in_progress = [t for t in tickets if t.get("status") == "em_andamento"]
    waiting_user = [t for t in tickets if t.get("status") == "aguardando_usuario"]
    queued = [t for t in tickets if t.get("status") == "novo"]
    resolution_minutes = []
    for t in concluded:
        created_dt = parse_ticket_datetime(t.get("created_at"))
        closed_dt = parse_ticket_datetime(t.get("closed_at"))
        if not created_dt or not closed_dt:
            continue
        diff = (closed_dt - created_dt).total_seconds() / 60
        if diff >= 0:
            resolution_minutes.append(diff)
    ranking = {}
    for t in concluded:
        uid = t.get("assignee_id")
        if uid:
            ranking[uid] = ranking.get(uid, 0) + 1
    ordered_ranking = sorted(ranking.items(), key=lambda x: (-x[1], x[0]))
    top_member = guild.get_member(ordered_ranking[0][0]) if ordered_ranking else None
    by_sector = {}
    by_category = {}
    for t in tickets:
        sector = t.get("department", "Não informado")
        category = t.get("category", "Não informado")
        by_sector[sector] = by_sector.get(sector, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1
    top_sectors = sorted(by_sector.items(), key=lambda x: (-x[1], x[0]))[:5]
    top_categories = sorted(by_category.items(), key=lambda x: (-x[1], x[0]))[:5]
    open_tickets = [t for t in store.data.get("tickets", {}).values() if t.get("status") != "concluido" and not is_test_ticket(t)]
    oldest_ticket = None
    oldest_dt = None
    for t in open_tickets:
        created_dt = parse_ticket_datetime(t.get("created_at"))
        if not created_dt:
            continue
        if oldest_dt is None or created_dt < oldest_dt:
            oldest_dt = created_dt
            oldest_ticket = t
    latest_concluded = sorted(
        [t for t in concluded if t.get("closed_at")],
        key=lambda x: parse_ticket_datetime(x.get("closed_at")) or datetime.min,
        reverse=True,
    )[:5]
    latest_opened = sorted(
        tickets,
        key=lambda x: parse_ticket_datetime(x.get("created_at")) or datetime.min,
        reverse=True,
    )[:5]

    embed1 = discord.Embed(
        title="Painel TI • Visão Geral",
        description=f"Resumo executivo da operação de chamados.\nPeríodo selecionado: **{month_label(month, year)}**",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    embed1.add_field(name="Período", value=month_label(month, year), inline=True)
    embed1.add_field(name="Abertos", value=str(opened), inline=True)
    embed1.add_field(name="Concluídos", value=str(len(concluded)), inline=True)
    embed1.add_field(name="Em andamento", value=str(len(in_progress)), inline=True)
    embed1.add_field(name="Aguardando usuário", value=str(len(waiting_user)), inline=True)
    embed1.add_field(name="Na fila", value=str(len(queued)), inline=True)
    taxa = (len(concluded) / opened * 100) if opened else 0
    embed1.add_field(name="Taxa de conclusão", value=f"{taxa:.1f}%", inline=True)
    embed1.add_field(name="Tempo médio até concluir", value=average_minutes(resolution_minutes), inline=True)
    embed1.add_field(name="Técnicos ativos", value=str(len(ranking)), inline=True)
    embed1.set_footer(text=f"Atualizado em {now.strftime('%d/%m/%Y %H:%M')}")

    embed2 = discord.Embed(
        title="Painel TI • Equipe",
        description=f"Produtividade da equipe em {month_label(month, year)}.",
        color=discord.Color.gold(),
        timestamp=datetime.utcnow(),
    )
    if top_member:
        embed2.set_thumbnail(url=top_member.display_avatar.url)
        embed2.add_field(
            name="Lenda do mês",
            value=f"🏆 {top_member.mention} liderou o mês e virou o rosto oficial do TI em {month_label(month, year)}.",
            inline=False,
        )
    ranking_lines = []
    for idx, (uid, total) in enumerate(ordered_ranking[:10], start=1):
        member = guild.get_member(uid)
        name = member.display_name if member else f"ID {uid}"
        ranking_lines.append(f"{idx}. {name} — {total}")
    embed2.add_field(name="Ranking do período", value="\n".join(ranking_lines) if ranking_lines else "Sem chamados concluídos no período.", inline=False)
    busiest_progress = {}
    for t in in_progress:
        uid = t.get("assignee_id")
        if uid:
            busiest_progress[uid] = busiest_progress.get(uid, 0) + 1
    top_progress = sorted(busiest_progress.items(), key=lambda x: (-x[1], x[0]))[:5]
    progress_lines = []
    for uid, total in top_progress:
        member = guild.get_member(uid)
        name = member.display_name if member else f"ID {uid}"
        progress_lines.append(f"{name} — {total}")
    embed2.add_field(name="Mais chamados em andamento", value="\n".join(progress_lines) if progress_lines else "Nenhum chamado em andamento.", inline=False)

    embed3 = discord.Embed(
        title="Painel TI • Operação",
        description=f"Distribuição da demanda e tickets recentes em {month_label(month, year)}.",
        color=discord.Color.green(),
        timestamp=datetime.utcnow(),
    )
    embed3.add_field(name="Top setores", value="\n".join([f"{k} — {v}" for k, v in top_sectors]) if top_sectors else "Sem dados.", inline=True)
    embed3.add_field(name="Top categorias", value="\n".join([f"{k} — {v}" for k, v in top_categories]) if top_categories else "Sem dados.", inline=True)
    if oldest_ticket:
        embed3.add_field(
            name="Chamado mais antigo aberto",
            value=f"{oldest_ticket.get('ticket_code', 'Sem código')} • {oldest_ticket.get('department', 'Sem setor')} • {STATUS_LABELS.get(oldest_ticket.get('status'), oldest_ticket.get('status'))}",
            inline=False,
        )
    embed3.add_field(
        name="Últimos concluídos",
        value="\n".join([
            f"{t.get('ticket_code', 'Sem código')} • {guild.get_member(t.get('assignee_id')).display_name if guild.get_member(t.get('assignee_id')) else 'Sem técnico'}"
            for t in latest_concluded
        ]) if latest_concluded else "Nenhum chamado concluído.",
        inline=False,
    )
    embed3.add_field(
        name="Últimos abertos",
        value="\n".join([
            f"{t.get('ticket_code', 'Sem código')} • {t.get('department', 'Sem setor')}"
            for t in latest_opened
        ]) if latest_opened else "Nenhum chamado aberto.",
        inline=False,
    )
    return [embed1, embed2, embed3]


class DashboardHistoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ver histórico", style=discord.ButtonStyle.primary, custom_id="dashboard_history_open")
    async def open_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in {ROLE_SUPPORT_ID, ROLE_ADMIN_ID} for role in interaction.user.roles):
            await interaction.response.send_message("Você não tem permissão para consultar o histórico.", ephemeral=True)
            return
        await interaction.response.send_message("Selecione o mês e o ano do dashboard histórico.", view=DashboardHistoryPickerView(), ephemeral=True)


class DashboardMonthSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=MONTH_NAMES[i], value=str(i)) for i in range(1, 13)]
        super().__init__(placeholder="Selecione o mês", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_month = int(self.values[0])
        await interaction.response.defer()


class DashboardYearSelect(discord.ui.Select):
    def __init__(self):
        current_year = now_local().year
        options = [discord.SelectOption(label=str(y), value=str(y)) for y in range(current_year - 5, current_year + 1)]
        super().__init__(placeholder="Selecione o ano", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_year = int(self.values[0])
        await interaction.response.defer()


class DashboardHistoryPickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        now = now_local()
        self.selected_month = now.month
        self.selected_year = now.year
        self.add_item(DashboardMonthSelect())
        self.add_item(DashboardYearSelect())

    @discord.ui.button(label="Gerar dashboard", style=discord.ButtonStyle.success)
    async def generate_dashboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_month or not self.selected_year:
            await interaction.response.send_message("Selecione primeiro o mês e o ano.", ephemeral=True)
            return
        embeds = build_dashboard_embeds_for_month(interaction.guild, self.selected_month, self.selected_year)
        period_label = month_label(self.selected_month, self.selected_year)
        await interaction.response.send_message(content=f"Dashboard histórico de {period_label}", embeds=embeds, ephemeral=True)


intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = False

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

@tree.command(name="dashboard_publicar", description="Publica ou recria o painel da TI")
async def dashboard_publicar(interaction: discord.Interaction):
    if not any(role.id in {ROLE_SUPPORT_ID, ROLE_ADMIN_ID} for role in interaction.user.roles):
        await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
        return
    _, message_id = await publish_or_update_dashboard(interaction.guild, force_new=True)
    await interaction.response.send_message(f"Dashboard publicado com sucesso. Message ID: {message_id}", ephemeral=True)


@tree.command(name="dashboard_atualizar", description="Atualiza o painel da TI")
async def dashboard_atualizar(interaction: discord.Interaction):
    if not any(role.id in {ROLE_SUPPORT_ID, ROLE_ADMIN_ID} for role in interaction.user.roles):
        await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
        return
    _, message_id = await publish_or_update_dashboard(interaction.guild)
    await interaction.response.send_message(f"Dashboard atualizado com sucesso. Message ID: {message_id}", ephemeral=True)



@tasks.loop(minutes=10)
async def dashboard_auto_update():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return
    try:
        await publish_or_update_dashboard(guild)
    except Exception as e:
        print(f"[dashboard] erro ao atualizar: {e}")


@dashboard_auto_update.before_loop
async def before_dashboard_auto_update():
    await bot.wait_until_ready()


@tasks.loop(minutes=10)
async def waiting_cards_refresh():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return
    try:
        await refresh_waiting_cards(guild)
        await limpar_cards_orfaos(guild)
        await check_integrity(guild)
    except Exception as e:
        print(f"[fila] erro ao atualizar cards: {e}")


@waiting_cards_refresh.before_loop
async def before_waiting_cards_refresh():
    await bot.wait_until_ready()


@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx):
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    await ctx.send(f"Sincronizados {len(synced)} comandos na guild.")



LOCAL_TZ = timezone(timedelta(hours=-3))  # America/Sao_Paulo (sem horario de verao desde 2019)


def now_local() -> datetime:
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ).replace(tzinfo=None)


def current_ticket_day() -> str:
    return now_local().strftime("%d-%m-%Y")


def current_ticket_day_compact() -> str:
    return now_local().strftime("%d-%m-%Y")


def current_ticket_day_channel() -> str:
    return now_local().strftime("%d-%m-%Y")


class TicketStore:
    def __init__(self, path: str):
        self.path = path
        self.data = {"counter": 0, "last_counter_date": None, "tickets": {}}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        self.data.setdefault("counter", 0)
        self.data.setdefault("last_counter_date", None)
        self.data.setdefault("tickets", {})
        self.data.setdefault("dashboard", {})
        self.data.setdefault("queue_panel", {})

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def next_daily_number(self) -> tuple[int, str, str]:
        today = current_ticket_day()
        compact = current_ticket_day_compact()
        if self.data.get("last_counter_date") != today:
            self.data["counter"] = 0
            self.data["last_counter_date"] = today
        # Garante codigo unico: se por algum motivo o numero ja existir,
        # avanca o contador ate encontrar um livre (evita sobrescrever chamado).
        existing = self.data.setdefault("tickets", {})
        while True:
            self.data["counter"] += 1
            ticket_code = f"CH-{compact}-{self.data['counter']:04d}"
            if ticket_code not in existing:
                break
        self.save()
        return self.data["counter"], ticket_code, today

    def set_ticket(self, ticket_id: str, payload: dict):
        self.data["tickets"][ticket_id] = payload
        self.save()

    def get_ticket(self, ticket_id: str) -> Optional[dict]:
        return self.data["tickets"].get(ticket_id)

    def get_ticket_by_queue_message(self, message_id: int) -> Optional[tuple[str, dict]]:
        for k, v in self.data["tickets"].items():
            if v.get("queue_message_id") == message_id:
                return k, v
        return None

    def get_ticket_by_channel(self, channel_id: int) -> Optional[tuple[str, dict]]:
        for k, v in self.data["tickets"].items():
            if v.get("channel_id") == channel_id:
                return k, v
        return None

    def set_dashboard_message(self, channel_id: int, message_id: int):
        self.data["dashboard"] = {"channel_id": channel_id, "message_id": message_id}
        self.save()

    def get_dashboard_message(self) -> dict:
        return self.data.get("dashboard", {})

    def set_queue_panel(self, channel_id: int, message_id: int):
        self.data["queue_panel"] = {"channel_id": channel_id, "message_id": message_id}
        self.save()

    def get_queue_panel(self) -> dict:
        return self.data.get("queue_panel", {})

    def update_ticket(self, ticket_id: str, **updates):
        if ticket_id not in self.data["tickets"]:
            return None
        self.data["tickets"][ticket_id].update(updates)
        self.save()
        return self.data["tickets"][ticket_id]


store = TicketStore(DATA_FILE)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9áàãâéêíóôõúç -]", "", text)
    replacements = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u",
        "ç": "c",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = text.replace(" ", "-")
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:25] or "usuario"


def ticket_thread_name(opener_name: Optional[str], tech_name: Optional[str] = None) -> str:
    """Nome da thread SEM o codigo do chamado (o codigo fica so no card)."""
    requester = slugify(opener_name) if opener_name else "atendimento"
    if tech_name:
        raw = slugify(tech_name)[:1] or tech_name[:1]
        return f"{(raw or 'T').upper()} {requester}"[:100]
    return requester[:100]


def safe_filename(name: str) -> str:
    name = name.strip().replace("/", "_").replace("\\", "_")
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or "arquivo"


def sanitize_header(value: str, max_length: int = 200) -> str:
    """Remove quebras de linha e caracteres de controle (anti injecao de cabecalho)."""
    text = str(value or "")
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    return text.strip()[:max_length]


async def log_action(guild: discord.Guild, message: str):
    channel = guild.get_channel(CHANNEL_LOGS_ID)
    if channel:
        await channel.send(message)

def filter_tickets_by_period(period: str) -> list[dict]:
    now = now_local()
    tickets = []
    for ticket in store.data.get("tickets", {}).values():
        if is_test_ticket(ticket):
            continue
        created_at = ticket.get("created_at", "")
        if not created_at:
            continue
        try:
            created_dt = datetime.fromisoformat(created_at)
        except Exception:
            try:
                created_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
        include = False
        if period == "hoje":
            include = created_dt.date() == now.date()
        elif period == "semana":
            include = created_dt.isocalendar()[:2] == now.isocalendar()[:2]
        elif period == "mes":
            include = created_dt.year == now.year and created_dt.month == now.month
        else:
            include = True
        if include:
            tickets.append(ticket)
    return tickets


def average_minutes(values: list[float]) -> str:
    if not values:
        return "0 min"
    avg = sum(values) / len(values)
    if avg >= 60:
        hours = int(avg // 60)
        minutes = int(avg % 60)
        return f"{hours}h {minutes}min"
    return f"{int(avg)} min"


def build_dashboard_embeds(guild: discord.Guild, period: str = "mes") -> list[discord.Embed]:
    tickets = filter_tickets_by_period(period)
    now = now_local()

    opened = len(tickets)
    concluded = [t for t in tickets if t.get("status") == "concluido"]
    in_progress = [t for t in tickets if t.get("status") == "em_andamento"]
    waiting_user = [t for t in tickets if t.get("status") == "aguardando_usuario"]
    queued = [t for t in tickets if t.get("status") == "novo"]

    resolution_minutes = []
    for t in concluded:
        created_at = t.get("created_at")
        closed_at = t.get("closed_at")
        if not created_at or not closed_at:
            continue
        try:
            created_dt = datetime.fromisoformat(created_at)
        except Exception:
            try:
                created_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
        try:
            closed_dt = datetime.fromisoformat(closed_at)
        except Exception:
            try:
                closed_dt = datetime.strptime(closed_at, "%Y-%m-%d %H:%M")
            except Exception:
                continue
        diff = (closed_dt - created_dt).total_seconds() / 60
        if diff >= 0:
            resolution_minutes.append(diff)

    ranking = {}
    for t in concluded:
        uid = t.get("assignee_id")
        if not uid:
            continue
        ranking[uid] = ranking.get(uid, 0) + 1
    ordered_ranking = sorted(ranking.items(), key=lambda x: (-x[1], x[0]))

    by_sector = {}
    by_category = {}
    for t in tickets:
        sector = t.get("department", "Não informado")
        category = t.get("category", "Não informado")
        by_sector[sector] = by_sector.get(sector, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1
    top_sectors = sorted(by_sector.items(), key=lambda x: (-x[1], x[0]))[:5]
    top_categories = sorted(by_category.items(), key=lambda x: (-x[1], x[0]))[:5]

    open_tickets = [t for t in store.data.get("tickets", {}).values() if t.get("status") != "concluido" and not is_test_ticket(t)]
    oldest_ticket = None
    oldest_dt = None
    for t in open_tickets:
        created_at = t.get("created_at")
        if not created_at:
            continue
        try:
            created_dt = datetime.fromisoformat(created_at)
        except Exception:
            try:
                created_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
        if oldest_dt is None or created_dt < oldest_dt:
            oldest_dt = created_dt
            oldest_ticket = t

    latest_concluded = sorted(
        [t for t in concluded if t.get("closed_at")],
        key=lambda x: x.get("closed_at", ""),
        reverse=True,
    )[:5]
    latest_opened = sorted(
        tickets,
        key=lambda x: x.get("created_at", ""),
        reverse=True,
    )[:5]

    embed1 = discord.Embed(
        title="Painel TI • Visão Geral",
        description="Resumo executivo da operação de chamados.",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    embed1.add_field(name="Período", value=period.capitalize(), inline=True)
    embed1.add_field(name="Abertos", value=str(opened), inline=True)
    embed1.add_field(name="Concluídos", value=str(len(concluded)), inline=True)
    embed1.add_field(name="Em andamento", value=str(len(in_progress)), inline=True)
    embed1.add_field(name="Aguardando usuário", value=str(len(waiting_user)), inline=True)
    embed1.add_field(name="Na fila", value=str(len(queued)), inline=True)
    taxa = (len(concluded) / opened * 100) if opened else 0
    embed1.add_field(name="Taxa de conclusão", value=f"{taxa:.1f}%", inline=True)
    embed1.add_field(name="Tempo médio até concluir", value=average_minutes(resolution_minutes), inline=True)
    embed1.add_field(name="Técnicos ativos", value=str(len(ranking)), inline=True)
    embed1.set_footer(text=f"Atualizado em {now.strftime('%d/%m/%Y %H:%M')}")

    embed2 = discord.Embed(
        title="Painel TI • Equipe",
        description="Produtividade da equipe no período.",
        color=discord.Color.gold(),
        timestamp=datetime.utcnow(),
    )
    ranking_lines = []
    for idx, (uid, total) in enumerate(ordered_ranking[:10], start=1):
        member = guild.get_member(uid)
        name = member.display_name if member else f"ID {uid}"
        ranking_lines.append(f"{idx}. {name} — {total}")
    embed2.add_field(
        name="Ranking do período",
        value="\n".join(ranking_lines) if ranking_lines else "Sem chamados concluídos no período.",
        inline=False,
    )
    busiest_progress = {}
    for t in in_progress:
        uid = t.get("assignee_id")
        if not uid:
            continue
        busiest_progress[uid] = busiest_progress.get(uid, 0) + 1
    top_progress = sorted(busiest_progress.items(), key=lambda x: (-x[1], x[0]))[:5]
    progress_lines = []
    for uid, total in top_progress:
        member = guild.get_member(uid)
        name = member.display_name if member else f"ID {uid}"
        progress_lines.append(f"{name} — {total}")
    embed2.add_field(
        name="Mais chamados em andamento",
        value="\n".join(progress_lines) if progress_lines else "Nenhum chamado em andamento.",
        inline=False,
    )

    embed3 = discord.Embed(
        title="Painel TI • Operação",
        description="Distribuição da demanda e tickets recentes.",
        color=discord.Color.green(),
        timestamp=datetime.utcnow(),
    )
    embed3.add_field(
        name="Top setores",
        value="\n".join([f"{k} — {v}" for k, v in top_sectors]) if top_sectors else "Sem dados.",
        inline=True,
    )
    embed3.add_field(
        name="Top categorias",
        value="\n".join([f"{k} — {v}" for k, v in top_categories]) if top_categories else "Sem dados.",
        inline=True,
    )
    if oldest_ticket:
        embed3.add_field(
            name="Chamado mais antigo aberto",
            value=f"{oldest_ticket.get('ticket_code', 'Sem código')} • {oldest_ticket.get('department', 'Sem setor')} • {STATUS_LABELS.get(oldest_ticket.get('status'), oldest_ticket.get('status'))}",
            inline=False,
        )
    embed3.add_field(
        name="Últimos concluídos",
        value="\n".join([
            f"{t.get('ticket_code', 'Sem código')} • {guild.get_member(t.get('assignee_id')).display_name if guild.get_member(t.get('assignee_id')) else 'Sem técnico'}"
            for t in latest_concluded
        ]) if latest_concluded else "Nenhum chamado concluído.",
        inline=False,
    )
    embed3.add_field(
        name="Últimos abertos",
        value="\n".join([
            f"{t.get('ticket_code', 'Sem código')} • {t.get('department', 'Sem setor')}"
            for t in latest_opened
        ]) if latest_opened else "Nenhum chamado aberto.",
        inline=False,
    )

    return [embed1, embed2, embed3]


async def publish_or_update_dashboard(guild: discord.Guild, force_new: bool = False) -> tuple[str, int]:
    channel = guild.get_channel(CHANNEL_DASHBOARD_ID)
    if not channel:
        raise RuntimeError("Canal de dashboard não encontrado.")
    embeds = build_dashboard_embeds(guild, period="mes")
    dashboard_cfg = store.get_dashboard_message()
    if not force_new and dashboard_cfg.get("channel_id") == channel.id and dashboard_cfg.get("message_id"):
        try:
            message = await channel.fetch_message(dashboard_cfg["message_id"])
            await message.edit(embeds=embeds, view=DashboardHistoryView())
            return "updated", message.id
        except Exception:
            pass
    message = await channel.send(embeds=embeds, view=DashboardHistoryView())
    store.set_dashboard_message(channel.id, message.id)
    return "created", message.id


def build_support_leaderboard(guild: discord.Guild) -> discord.Embed:
    ranking = {}
    for ticket in store.data.get("tickets", {}).values():
        if ticket.get("status") != "concluido":
            continue
        if is_test_ticket(ticket):
            continue
        assignee_id = ticket.get("assignee_id")
        if not assignee_id:
            continue
        ranking[assignee_id] = ranking.get(assignee_id, 0) + 1

    ordered = sorted(ranking.items(), key=lambda x: (-x[1], x[0]))
    embed = discord.Embed(
        title="Leaderboard de chamados concluídos",
        color=discord.Color.gold(),
        timestamp=datetime.utcnow(),
    )

    if not ordered:
        embed.description = "Ainda não há chamados concluídos para montar o ranking."
        return embed

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for idx, (user_id, total) in enumerate(ordered[:10], start=1):
        member = guild.get_member(user_id)
        nome = member.display_name if member else f"ID {user_id}"
        prefixo = medals[idx - 1] if idx <= 3 else f"{idx}."
        palavra = "chamado" if total == 1 else "chamados"
        lines.append(f"{prefixo} {nome} — **{total}** {palavra}")

    embed.description = "\n".join(lines)
    embed.set_footer(text=f"Total de técnicos no ranking: {len(ordered)}")
    return embed


def get_queue_rank(ticket_id: str) -> int:
    pending = []
    for key, ticket in store.data["tickets"].items():
        if ticket.get("status") != "novo":
            continue
        pending.append((
            ticket.get("created_at", ""),
            key,
        ))
    pending.sort(key=lambda x: x[0])
    for idx, (_, t_id) in enumerate(pending, start=1):
        if t_id == ticket_id:
            return idx
    return 0


def fmt_dt_br(value: str) -> str:
    dt = parse_ticket_datetime(value)
    if not dt:
        return value or "?"
    return dt.strftime("%d/%m/%Y %H:%M")


async def build_queue_embed(guild: discord.Guild, ticket_id: str) -> discord.Embed:
    ticket = store.get_ticket(ticket_id)
    opener = guild.get_member(ticket["opener_id"]) if ticket else None
    embed = discord.Embed(
        title="🎫 Novo chamado na fila",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow(),
    )
    embed.add_field(name="Solicitante", value=opener.mention if opener else f"ID {ticket['opener_id']}", inline=True)
    embed.add_field(name="Setor", value=ticket["department"], inline=True)
    embed.add_field(name="Categoria", value=ticket["category"], inline=True)
    anexos = ticket.get("opener_attachments") or []
    if anexos:
        embed.add_field(name="📎 Anexo", value=f"{len(anexos)} arquivo(s)", inline=True)
    if ticket.get("detail"):
        embed.add_field(name="Detalhe", value=str(ticket["detail"])[:1024], inline=False)
    embed.add_field(name="Aberto em", value=fmt_dt_br(ticket.get("created_at", "")), inline=True)
    embed.add_field(name="Posição na fila", value=str(get_queue_rank(ticket_id)) if ticket["status"] == "novo" else "Fora da fila", inline=True)
    embed.add_field(name="Aguardando há", value=waited_label(ticket.get("created_at", "")), inline=True)
    embed.add_field(name="Descrição", value=ticket["description"][:1024], inline=False)
    embed.set_footer(text="Use o botão abaixo para assumir o chamado")
    return embed


async def build_ticket_embed(guild: discord.Guild, ticket_id: str) -> discord.Embed:
    ticket = store.get_ticket(ticket_id)
    opener = guild.get_member(ticket["opener_id"]) if ticket else None
    assignee = guild.get_member(ticket["assignee_id"] ) if ticket and ticket.get("assignee_id") else None
    color = discord.Color.blurple() if ticket.get("status") != "concluido" else discord.Color.green()
    embed = discord.Embed(
        title=f"Atendimento • {ticket_id}",
        color=color,
        timestamp=datetime.utcnow(),
    )
    embed.add_field(name="Número diário", value=f"{ticket['daily_number']:04d}", inline=True)
    embed.add_field(name="Data", value=ticket["ticket_date"], inline=True)
    embed.add_field(name="Setor", value=ticket["department"], inline=True)
    embed.add_field(name="Categoria", value=ticket["category"], inline=True)
    embed.add_field(name="Status", value=STATUS_LABELS.get(ticket["status"], ticket["status"]), inline=True)
    embed.add_field(name="Solicitante", value=opener.mention if opener else f"ID {ticket['opener_id']}", inline=True)
    embed.add_field(name="Responsável", value=assignee.mention if assignee else "Não atribuído", inline=True)
    embed.add_field(name="Descrição", value=ticket["description"][:1024], inline=False)
    return embed


async def download_attachment_obj(attachment: discord.Attachment, dest: Path):
    size = getattr(attachment, "size", None)
    if size is not None and size > MAX_ATTACHMENT_BYTES:
        raise ValueError(f"anexo excede o limite de {MAX_ATTACHMENT_BYTES} bytes")
    data = await attachment.read(use_cached=True)
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise ValueError(f"anexo excede o limite de {MAX_ATTACHMENT_BYTES} bytes")
    dest.write_bytes(data)


async def build_email_bundle(channel: discord.TextChannel, ticket_id: str, guild: discord.Guild):
    ticket = store.get_ticket(ticket_id)
    safe_ticket = ticket_id.lower().replace("-", "_")
    ticket_dir = ATTACHMENTS_DIR / safe_ticket
    ticket_dir.mkdir(parents=True, exist_ok=True)

    text_lines = [
        f"Histórico do chamado {ticket_id}",
        f"Servidor: {guild.name}",
        f"Canal: #{channel.name}",
        f"Setor: {ticket.get('department')}",
        f"Categoria: {ticket.get('category')}",
        f"Status: {ticket.get('status')}",
        "",
        "=== Histórico ===",
        "",
    ]

    html_parts = [
        "<html><body style='font-family:Arial,Helvetica,sans-serif;background:#f5f7fb;color:#1f2937;padding:20px;'>",
        f"<h2 style='margin-bottom:4px;'>Histórico do chamado {ticket_id}</h2>",
        f"<p><strong>Servidor:</strong> {html.escape(guild.name)}<br>",
        f"<strong>Canal:</strong> #{html.escape(channel.name)}<br>",
        f"<strong>Setor:</strong> {html.escape(str(ticket.get('department')))}<br>",
        f"<strong>Categoria:</strong> {html.escape(str(ticket.get('category')))}<br>",
        f"<strong>Status:</strong> {html.escape(str(ticket.get('status')))}</p>",
        "<hr>",
    ]

    regular_attachments = []
    inline_images = []

    async for msg in channel.history(limit=None, oldest_first=True):
        created = msg.created_at.strftime("%d-%m-%Y %H:%M:%S UTC")
        author = html.escape(msg.author.display_name)
        content_text = msg.content.strip() if msg.content else "[sem texto]"
        content_html = html.escape(content_text).replace("\n", "<br>")

        text_lines.append(f"[{created}] {msg.author.display_name}: {content_text}")
        html_parts.append(
            "<div style='background:#ffffff;border:1px solid #dbe3f0;border-radius:10px;padding:12px;margin:12px 0;'>"
            f"<div style='font-size:13px;color:#6b7280;margin-bottom:6px;'><strong>{author}</strong> • {created}</div>"
            f"<div style='font-size:14px;line-height:1.5;'>{content_html}</div>"
        )

        if msg.attachments:
            for idx, att in enumerate(msg.attachments, start=1):
                original_name = att.filename or f"arquivo_{msg.id}_{idx}"
                filename = safe_filename(original_name)
                dest = ticket_dir / f"{msg.id}_{idx}_{filename}"
                try:
                    await download_attachment_obj(att, dest)
                    suffix = dest.suffix.lower()
                    text_lines.append(f"  Anexo: {original_name}")
                    if suffix in IMAGE_EXTENSIONS:
                        cid = make_msgid(domain="ticket.local")[1:-1]
                        inline_images.append({"path": dest, "cid": cid, "name": original_name})
                        html_parts.append(
                            f"<div style='margin-top:10px;'><div style='font-size:12px;color:#6b7280;margin-bottom:6px;'>Imagem: {html.escape(original_name)}</div>"
                            f"<img src='cid:{cid}' alt='{html.escape(original_name)}' style='max-width:100%;border-radius:8px;border:1px solid #d1d5db;'></div>"
                        )
                    else:
                        regular_attachments.append(dest)
                        html_parts.append(
                            f"<div style='margin-top:10px;font-size:13px;'>Anexo: {html.escape(original_name)}</div>"
                        )
                except Exception as e:
                    text_lines.append(f"  Anexo não baixado: {original_name} ({e})")
                    html_parts.append(
                        f"<div style='margin-top:10px;font-size:13px;color:#b91c1c;'>Anexo não baixado: {html.escape(original_name)}</div>"
                    )

        if msg.embeds:
            text_lines.append(f"  Embeds: {len(msg.embeds)}")
            html_parts.append(f"<div style='margin-top:10px;font-size:13px;color:#6b7280;'>Embeds detectados: {len(msg.embeds)}</div>")

        html_parts.append("</div>")
        text_lines.append("")

    html_parts.append("</body></html>")

    report_path = ticket_dir / f"historico_{safe_ticket}.txt"
    report_path.write_text("\n".join(text_lines), encoding="utf-8")
    regular_attachments.insert(0, report_path)

    return {
        "text": "\n".join(text_lines),
        "html": "".join(html_parts),
        "attachments": regular_attachments,
        "inline_images": inline_images,
    }


def send_email_sync(bundle: dict, ticket_id: str, opener_name: str):
    msg = EmailMessage()
    msg["Subject"] = sanitize_header(f"Histórico do chamado {ticket_id} - {opener_name}")
    msg["From"] = sanitize_header(EMAIL_FROM)
    msg["To"] = sanitize_header(EMAIL_TO)
    msg.set_content(bundle["text"][:200000])
    msg.add_alternative(bundle["html"], subtype="html")

    html_part = msg.get_payload()[-1]

    for img in bundle["inline_images"]:
        mime_type, _ = mimetypes.guess_type(str(img["path"]))
        maintype, subtype = (mime_type.split("/", 1) if mime_type else ("image", "png"))
        with open(img["path"], "rb") as f:
            html_part.add_related(f.read(), maintype=maintype, subtype=subtype, cid=f"<{img['cid']}>", filename=img["path"].name)

    for file_path in bundle["attachments"]:
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        with open(file_path, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=file_path.name)

    context = ssl.create_default_context()
    timeout = 30

    if SMTP_SSL_MODE == "ssl" or (SMTP_SSL_MODE == "auto" and SMTP_PORT == 465):
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=timeout) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=timeout) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)


async def send_ticket_email(channel: discord.TextChannel, ticket_id: str, guild: discord.Guild):
    bundle = await build_email_bundle(channel, ticket_id, guild)
    ticket = store.get_ticket(ticket_id)
    opener_name = ticket.get("opener_name", "Solicitante")
    await asyncio.to_thread(send_email_sync, bundle, ticket_id, opener_name)


# ---------------------------------------------------------------------------
# Fila: painel unico (mensagem fixa) + threads privadas por chamado
# ---------------------------------------------------------------------------

def waited_label(created_at: str) -> str:
    created = parse_ticket_datetime(created_at)
    if not created:
        return "?"
    minutes = int((now_local() - created).total_seconds() // 60)
    if minutes < 60:
        return f"{minutes}min"
    if minutes < 1440:
        return f"{minutes // 60}h{minutes % 60:02d}"
    return f"{minutes // 1440}d{minutes % 1440 // 60}h"


def waiting_tickets() -> list[dict]:
    waiting = [t for t in store.data.get("tickets", {}).values() if t.get("status") == "novo"]
    waiting.sort(key=lambda t: t.get("created_at", ""))
    return waiting


def build_queue_panel_embeds(guild: discord.Guild, waiting: list[dict]) -> list[discord.Embed]:
    embed = discord.Embed(
        title="Fila de atendimento • TI",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow(),
    )
    if not waiting:
        embed.description = "✅ Nenhum chamado aguardando. Fila vazia."
    else:
        linhas = []
        for idx, t in enumerate(waiting[:20], start=1):
            linhas.append(
                f"`{idx:02d}` • `{t.get('ticket_code', '?')}` • **{t.get('opener_name', '?')}** • "
                f"{t.get('department', '?')} / {t.get('category', '?')} • ⏱ {waited_label(t.get('created_at', ''))}"
            )
        embed.description = "\n".join(linhas)
        if len(waiting) > 20:
            embed.description += f"\n\n… e mais {len(waiting) - 20} chamado(s)."
    embed.set_footer(text=f"Total na fila: {len(waiting)} • atualizado {now_local().strftime('%d/%m/%Y %H:%M')}")
    return [embed]


def queue_panel_options(waiting: list[dict]) -> list[discord.SelectOption]:
    options = []
    for idx, t in enumerate(waiting[:25], start=1):
        label = (
            f"{idx:02d}. {t.get('opener_name', '?')} — "
            f"{t.get('department', '?')}/{t.get('category', '?')}"
        )
        options.append(
            discord.SelectOption(
                label=label[:100],
                value=t.get("ticket_code"),
                description=f"⏱ esperando {waited_label(t.get('created_at', ''))}"[:100],
            )
        )
    return options or [discord.SelectOption(label="Fila vazia", value="__vazio__")]


class QueuePanelSelect(discord.ui.Select):
    def __init__(self, waiting: Optional[list[dict]] = None):
        super().__init__(
            placeholder="Selecione um chamado da fila…",
            min_values=1,
            max_values=1,
            custom_id="queue_panel_select",
            options=queue_panel_options(waiting or []),
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected = self.values[0]
        await interaction.response.defer()


class QueuePanelView(discord.ui.View):
    def __init__(self, waiting: Optional[list[dict]] = None):
        super().__init__(timeout=None)
        self.selected: Optional[str] = None
        self.add_item(QueuePanelSelect(waiting))

    @discord.ui.button(label="Assumir chamado", style=discord.ButtonStyle.primary, emoji="🙋", custom_id="queue_panel_assumir")
    async def assumir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        support_role = interaction.guild.get_role(ROLE_SUPPORT_ID)
        if not support_role or support_role not in interaction.user.roles:
            await interaction.followup.send("Apenas a equipe de Tecnologia pode assumir chamados.", ephemeral=True)
            return
        code = self.selected
        if not code or code == "__vazio__":
            await interaction.followup.send("Selecione um chamado na lista antes de assumir.", ephemeral=True)
            return
        ticket = store.get_ticket(code)
        if not ticket or ticket.get("status") != "novo":
            await interaction.followup.send("Este chamado não está mais na fila.", ephemeral=True)
            await publish_or_update_queue_panel(interaction.guild)
            return
        await assume_ticket(interaction, code, ticket)


async def publish_or_update_queue_panel(guild: discord.Guild, force_new: bool = False) -> tuple[str, int]:
    channel = guild.get_channel(CHANNEL_TICKETS_ID)
    if not isinstance(channel, discord.TextChannel):
        raise RuntimeError("Canal de chamados não encontrado.")
    waiting = waiting_tickets()
    embeds = build_queue_panel_embeds(guild, waiting)
    view = QueuePanelView(waiting)
    cfg = store.get_queue_panel()
    if not force_new and cfg.get("channel_id") == channel.id and cfg.get("message_id"):
        try:
            message = await channel.fetch_message(cfg["message_id"])
            await message.edit(embeds=embeds, view=view)
            return "updated", message.id
        except Exception:
            pass
    message = await channel.send(embeds=embeds, view=view)
    try:
        await message.pin()
    except Exception:
        pass
    store.set_queue_panel(channel.id, message.id)
    return "created", message.id


async def assume_ticket(interaction: discord.Interaction, ticket_id: str, ticket: dict):
    guild = interaction.guild
    opener = guild.get_member(ticket.get("opener_id"))
    if opener is None:
        await interaction.followup.send("Não consegui localizar o solicitante no servidor.", ephemeral=True)
        return

    channel_destino = guild.get_channel(CHANNEL_THREADS_ID)
    if not isinstance(channel_destino, discord.TextChannel):
        await interaction.followup.send("Canal de atendimentos não encontrado.", ephemeral=True)
        return

    thread_name = ticket_thread_name(opener.display_name, interaction.user.display_name)

    nao_adicionados = []
    try:
        place = await channel_destino.create_thread(
            name=thread_name,
            type=discord.ChannelType.private_thread,
            invitable=False,
            auto_archive_duration=10080,
            reason=f"Chamado {ticket_id} assumido por {interaction.user}",
        )
        modo = "thread"
        for membro in (opener, interaction.user):
            try:
                await place.add_user(membro)
            except Exception:
                nao_adicionados.append(membro)
    except discord.Forbidden:
        # Fallback: sem permissao de "Criar Threads Privadas", usa canal de texto
        modo = "canal"
        open_category = guild.get_channel(CATEGORY_OPEN_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            opener: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_messages=True, read_message_history=True),
        }
        place = await guild.create_text_channel(
            name=thread_name,
            category=open_category if isinstance(open_category, discord.CategoryChannel) else None,
            overwrites=overwrites,
            topic=f"{ticket_id} | solicitante={ticket['opener_id']} | responsavel={interaction.user.id}",
            reason=f"Chamado {ticket_id} assumido por {interaction.user}",
        )

    store.update_ticket(
        ticket_id,
        status="em_andamento",
        assignee_id=interaction.user.id,
        channel_id=place.id,
        accepted_at=now_local().strftime("%Y-%m-%d %H:%M"),
        channel_name=thread_name,
        thread_parent_id=CHANNEL_THREADS_ID if modo == "thread" else None,
    )

    # Garante a remocao do card da fila (evita card orfao)
    qmid = ticket.get("queue_message_id")
    if qmid:
        try:
            canal_fila = guild.get_channel(CHANNEL_TICKETS_ID)
            if isinstance(canal_fila, discord.TextChannel):
                msg = await canal_fila.fetch_message(int(qmid))
                await msg.delete()
        except Exception:
            pass
        store.update_ticket(ticket_id, queue_message_id=None)

    ticket_embed = await build_ticket_embed(guild, ticket_id)
    mensagem = await place.send(
        content=f"{opener.mention} {interaction.user.mention}",
        embed=ticket_embed,
        view=OpenTicketView(),
    )
    store.update_ticket(ticket_id, embed_message_id=mensagem.id)

    anexos = ticket.get("opener_attachments") or []
    arquivos = []
    for caminho in anexos:
        try:
            arquivos.append(discord.File(caminho))
        except Exception:
            pass
    if arquivos:
        try:
            await place.send(content="📎 Anexo(s) enviado(s) pelo solicitante:", files=arquivos)
        except Exception:
            pass

    rotulo = "Thread" if modo == "thread" else "Canal"
    aviso = ""
    if opener in nao_adicionados:
        aviso = ("\n⚠️ Não consegui adicionar o solicitante automaticamente. "
                 "Confirme se ele tem permissão de **Ver Canal** no canal pai das threads.")
    await interaction.followup.send(
        f"Chamado {ticket_id} assumido. {rotulo} criado(a): {place.mention}{aviso}", ephemeral=True
    )
    await log_action(guild, f"📌 {interaction.user.mention} assumiu {ticket_id}. {rotulo}: {place.mention}.")
    if opener not in nao_adicionados:
        await notify_user(
            opener,
            f"🎫 Seu chamado **{ticket_id}** foi assumido por **{interaction.user.display_name}**.\n"
            f"Acompanhe o atendimento em: https://discord.com/channels/{guild.id}/{place.id}",
        )
    await refresh_waiting_cards(guild)


async def migrate_open_tickets(guild: discord.Guild):
    """Move threads abertas criadas no canal errado para o canal de atendimentos."""
    destino = guild.get_channel(CHANNEL_THREADS_ID)
    if not isinstance(destino, discord.TextChannel):
        return
    for key, t in list(store.data.get("tickets", {}).items()):
        if t.get("status") not in ("em_andamento", "aguardando_usuario") or not t.get("channel_id"):
            continue
        try:
            canal = guild.get_channel(t["channel_id"]) or await guild.fetch_channel(t["channel_id"])
        except Exception:
            continue
        opener = guild.get_member(t.get("opener_id"))
        assignee = guild.get_member(t.get("assignee_id")) if t.get("assignee_id") else None
        nome_novo = ticket_thread_name(
            opener.display_name if opener else None,
            assignee.display_name if assignee else None,
        )
        if getattr(canal, "parent_id", None) == CHANNEL_THREADS_ID:
            # ja esta no lugar certo: apenas remove o codigo do titulo, se houver
            try:
                if getattr(canal, "name", None) != nome_novo:
                    await canal.edit(name=nome_novo)
                    store.update_ticket(key, channel_name=nome_novo)
            except Exception:
                pass
            continue
        try:
            nova = await destino.create_thread(
                name=nome_novo,
                type=discord.ChannelType.private_thread,
                invitable=False,
                auto_archive_duration=10080,
                reason=f"Migracao do chamado {key} para o canal de atendimentos",
            )
            for membro in (opener, assignee):
                if membro is not None:
                    try:
                        await nova.add_user(membro)
                    except Exception:
                        pass
            emb = await build_ticket_embed(guild, key)
            msg = await nova.send(embed=emb, view=OpenTicketView())
            store.update_ticket(key, channel_id=nova.id, embed_message_id=msg.id,
                                thread_parent_id=CHANNEL_THREADS_ID)
            try:
                await canal.send("↪️ Atendimento movido para uma nova thread no canal de atendimentos.")
                await canal.edit(archived=True)
            except Exception:
                pass
        except Exception:
            continue


async def refresh_waiting_cards(guild: discord.Guild):
    """Re-renderiza os cards dos chamados na fila (posicao e tempo de espera atualizados)."""
    canal = guild.get_channel(CHANNEL_TICKETS_ID)
    if not isinstance(canal, discord.TextChannel):
        return
    for key, t in list(store.data.get("tickets", {}).items()):
        if t.get("status") != "novo":
            continue
        try:
            emb = await build_queue_embed(guild, key)
        except Exception:
            continue
        if t.get("queue_message_id"):
            try:
                msg = await canal.fetch_message(t["queue_message_id"])
                await msg.edit(embed=emb, view=QueueControlView())
                await asyncio.sleep(0.7)
                continue
            except Exception:
                pass
        try:
            msg = await canal.send(embed=emb, view=QueueControlView())
            store.update_ticket(key, queue_message_id=msg.id)
            await asyncio.sleep(0.7)
        except Exception:
            pass


async def check_integrity(guild: discord.Guild):
    """Detecta chamados com card/thread/canal inexistente e alerta no canal de logs."""
    problemas = []
    canal_fila = guild.get_channel(CHANNEL_TICKETS_ID)
    for key, t in list(store.data.get("tickets", {}).items()):
        st = t.get("status")
        if st == "novo":
            mid = t.get("queue_message_id")
            if mid and isinstance(canal_fila, discord.TextChannel):
                try:
                    await canal_fila.fetch_message(int(mid))
                except Exception:
                    problemas.append((key, "card da fila apagado"))
            continue
        if st in ("em_andamento", "aguardando_usuario"):
            cid = t.get("channel_id")
            if not cid:
                problemas.append((key, "sem thread/canal vinculado"))
                continue
            try:
                guild.get_channel(cid) or await guild.fetch_channel(cid)
            except Exception:
                problemas.append((key, "thread/canal apagado"))
    if problemas:
        linhas = "\n".join(f"• `{k}` — {motivo}" for k, motivo in problemas)
        try:
            await log_action(
                guild,
                f"⚠️ **Verificação de integridade** — {len(problemas)} chamado(s) com problema:\n{linhas}",
            )
        except Exception:
            pass
        print("[integridade]", problemas)
    return problemas


async def limpar_cards_orfaos(guild: discord.Guild):
    """Remove cards no #fila-ti que nao correspondem a chamados aguardando."""
    canal = guild.get_channel(CHANNEL_TICKETS_ID)
    if not isinstance(canal, discord.TextChannel):
        return
    esperados = {
        str(t.get("queue_message_id"))
        for t in store.data.get("tickets", {}).values()
        if t.get("status") == "novo" and t.get("queue_message_id")
    }
    try:
        mensagens = [m async for m in canal.history(limit=50)]
    except Exception:
        return
    for m in mensagens:
        if not m.author.bot:
            continue
        if not any((e.title or "").startswith("🎫 Novo chamado na fila") for e in m.embeds):
            continue
        if str(m.id) in esperados:
            continue
        try:
            await m.delete()
        except Exception:
            continue
        for kk, vv in store.data["tickets"].items():
            if str(vv.get("queue_message_id")) == str(m.id):
                store.update_ticket(kk, queue_message_id=None)
                break
        await asyncio.sleep(0.7)


class QueueControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Assumir chamado", style=discord.ButtonStyle.primary, custom_id="queue_assumir")
    async def assumir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        support_role = interaction.guild.get_role(ROLE_SUPPORT_ID)
        if not support_role or support_role not in interaction.user.roles:
            await interaction.followup.send("Apenas a equipe de Tecnologia pode assumir chamados.", ephemeral=True)
            return

        found = store.get_ticket_by_queue_message(interaction.message.id)
        if not found:
            await interaction.followup.send("Chamado da fila não encontrado.", ephemeral=True)
            return
        ticket_id, ticket = found

        if ticket.get("status") != "novo":
            await interaction.followup.send("Este chamado já foi assumido por outro técnico.", ephemeral=True)
            return

        try:
            await interaction.message.delete()
        except Exception:
            pass
        await assume_ticket(interaction, ticket_id, ticket)


class QueueLockedView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Chamado já assumido", style=discord.ButtonStyle.secondary, disabled=True))


class AddMemberSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(
            placeholder="Selecione uma ou mais pessoas para adicionar…",
            min_values=1,
            max_values=10,
        )

    async def callback(self, interaction: discord.Interaction):
        thread = interaction.channel
        adicionados, falhas = [], []
        for alvo in self.values:
            try:
                await thread.add_user(alvo)
                adicionados.append(alvo)
            except Exception:
                falhas.append(alvo)

        partes = []
        if adicionados:
            partes.append("Adicionado(s): " + ", ".join(m.mention for m in adicionados))
        if falhas:
            partes.append("Não consegui adicionar: " + ", ".join(
                getattr(m, "display_name", str(m)) for m in falhas))
        await interaction.response.send_message("\n".join(partes) or "Nada foi alterado.", ephemeral=True)

        if adicionados:
            mencoes = " ".join(m.mention for m in adicionados)
            try:
                await thread.send(f"➕ {mencoes} — adicionado(s) ao atendimento por {interaction.user.mention}.")
            except Exception:
                pass
            found = store.get_ticket_by_channel(thread.id)
            tid = found[0] if found else "?"
            await log_action(interaction.guild, f"👥 {interaction.user.mention} adicionou {mencoes} em {tid}.")


class AddMemberView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(AddMemberSelect())


class OpenTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def refresh(self, interaction: discord.Interaction, ticket_id: str):
        embed = await build_ticket_embed(interaction.guild, ticket_id)
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Aguardando usuário", style=discord.ButtonStyle.secondary, custom_id="ticket_aguardando")
    async def aguardando(self, interaction: discord.Interaction, button: discord.ui.Button):
        found = store.get_ticket_by_channel(interaction.channel.id)
        if not found:
            await interaction.response.send_message("Este canal não está vinculado a um chamado.", ephemeral=True)
            return
        ticket_id, ticket = found
        if interaction.user.id != ticket.get("assignee_id"):
            await interaction.response.send_message("Somente o técnico responsável pode alterar este status.", ephemeral=True)
            return

        store.update_ticket(ticket_id, status="aguardando_usuario")
        await interaction.response.send_message("Status alterado para aguardando usuário.", ephemeral=True)
        await self.refresh(interaction, ticket_id)
        await log_action(interaction.guild, f"⏸️ {ticket_id} ficou aguardando usuário por {interaction.user.mention}.")
        await notify_user(
            interaction.guild.get_member(ticket.get("opener_id")),
            f"⏳ O chamado **{ticket_id}** está aguardando a sua resposta. Por favor, responda no canal do atendimento.",
        )

    @discord.ui.button(label="Concluir", style=discord.ButtonStyle.success, custom_id="ticket_concluir")
    async def concluir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        found = store.get_ticket_by_channel(interaction.channel.id)
        if not found:
            await interaction.followup.send("Este canal não está vinculado a um chamado.", ephemeral=True)
            return
        ticket_id, ticket = found
        if interaction.user.id != ticket.get("assignee_id"):
            await interaction.followup.send("Somente o técnico responsável pode concluir este chamado.", ephemeral=True)
            return

        store.update_ticket(ticket_id, status="concluido", closed_at=now_local().strftime("%Y-%m-%d %H:%M"))
        embed = await build_ticket_embed(interaction.guild, ticket_id)
        await interaction.message.edit(embed=embed, view=ClosedTicketView())
        await interaction.followup.send("Chamado concluído.", ephemeral=True)
        await log_action(interaction.guild, f"✅ {ticket_id} concluído por {interaction.user.mention}.")
        await notify_user(
            interaction.guild.get_member(ticket.get("opener_id")),
            f"✅ Seu chamado **{ticket_id}** foi marcado como concluído. "
            f"Se ainda precisar de algo, responda na thread do atendimento.",
        )

    @discord.ui.button(label="Adicionar participante", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="ticket_add_member")
    async def adicionar(self, interaction: discord.Interaction, button: discord.ui.Button):
        found = store.get_ticket_by_channel(interaction.channel.id)
        if not found:
            await interaction.response.send_message("Este canal não está vinculado a um chamado.", ephemeral=True)
            return
        _, ticket = found
        support = interaction.guild.get_role(ROLE_SUPPORT_ID)
        admin = interaction.guild.get_role(ROLE_ADMIN_ID)
        eh_responsavel = interaction.user.id == ticket.get("assignee_id")
        eh_equipe = (support and support in interaction.user.roles) or (admin and admin in interaction.user.roles)
        if not (eh_responsavel or eh_equipe):
            await interaction.response.send_message(
                "Somente o técnico responsável ou a equipe de TI podem adicionar participantes.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            "Selecione quem você quer adicionar a este atendimento:",
            view=AddMemberView(),
            ephemeral=True,
        )


class ClosedTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enviar E-mail", style=discord.ButtonStyle.primary, custom_id="ticket_email")
    async def enviar_email(self, interaction: discord.Interaction, button: discord.ui.Button):
        found = store.get_ticket_by_channel(interaction.channel.id)
        if not found:
            await interaction.response.send_message("Este canal não está vinculado a um chamado.", ephemeral=True)
            return
        ticket_id, _ = found

        support_role = interaction.guild.get_role(ROLE_SUPPORT_ID)
        admin_role = interaction.guild.get_role(ROLE_ADMIN_ID)
        allowed = (support_role and support_role in interaction.user.roles) or (admin_role and admin_role in interaction.user.roles)
        if not allowed:
            await interaction.response.send_message("Apenas a equipe de Tecnologia pode enviar o e-mail do histórico.", ephemeral=True)
            return

        await interaction.response.send_message("Gerando histórico em HTML e enviando e-mail...", ephemeral=True)
        try:
            await send_ticket_email(interaction.channel, ticket_id, interaction.guild)
            await interaction.followup.send(f"Histórico do {ticket_id} enviado para {EMAIL_TO}.", ephemeral=True)
            await log_action(interaction.guild, f"📧 Histórico HTML do {ticket_id} enviado por {interaction.user.mention} para {EMAIL_TO}.")
        except Exception as e:
            await interaction.followup.send(f"Erro ao enviar e-mail: {e}", ephemeral=True)

    @discord.ui.button(label="Fechar", style=discord.ButtonStyle.danger, custom_id="ticket_fechar")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        found = store.get_ticket_by_channel(interaction.channel.id)
        if not found:
            await interaction.response.send_message("Este canal não está vinculado a um chamado.", ephemeral=True)
            return
        ticket_id, ticket = found
        opener_id = ticket.get("opener_id")
        assignee_id = ticket.get("assignee_id")
        admin_role = interaction.guild.get_role(ROLE_ADMIN_ID)
        allowed_admin = admin_role and admin_role in interaction.user.roles
        allowed_participant = interaction.user.id in {opener_id, assignee_id}
        if not (allowed_admin or allowed_participant):
            await interaction.response.send_message("Somente o solicitante, o técnico responsável ou um administrador podem fechar o chamado.", ephemeral=True)
            return

        eh_thread = isinstance(interaction.channel, discord.Thread)
        if eh_thread:
            await interaction.response.send_message(
                "Encerrando o atendimento: a thread será **arquivada e travada** (o histórico continua disponível).",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "Encerrando o atendimento: este canal será **excluído** em 5 segundos.",
                ephemeral=True,
            )
        updates = {"archived": True, "archived_at": now_local().strftime("%Y-%m-%d %H:%M")}
        if ticket.get("status") != "concluido":
            updates["status"] = "concluido"
            updates.setdefault("closed_at", now_local().strftime("%Y-%m-%d %H:%M"))
        store.update_ticket(ticket_id, **updates)
        await log_action(interaction.guild, f"🗄️ {ticket_id} encerrado por {interaction.user.mention}.")
        await asyncio.sleep(2 if eh_thread else 5)
        try:
            if eh_thread:
                await interaction.channel.edit(
                    archived=True, locked=True, reason=f"{ticket_id} arquivado por {interaction.user}"
                )
            else:
                await interaction.channel.delete(reason=f"{ticket_id} encerrado por {interaction.user}")
        except Exception as e:
            await interaction.followup.send(f"Não consegui encerrar: {e}", ephemeral=True)


class _DepartmentSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="1) Selecione o setor / departamento",
            options=[discord.SelectOption(label=d, value=d) for d in DEPARTMENTS],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.departamento = self.values[0]
        await interaction.response.defer()


class _CategorySelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="2) Selecione a categoria",
            options=[discord.SelectOption(label=c, value=c) for c in CATEGORIES],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.categoria = self.values[0]
        await interaction.response.defer()


async def criar_chamado(interaction: discord.Interaction, department: str, category: str,
                        description: str, detail: str, anexos: Optional[list] = None):
    guild = interaction.guild
    tickets_channel = guild.get_channel(CHANNEL_TICKETS_ID)
    if not isinstance(tickets_channel, discord.TextChannel):
        await interaction.response.send_message("Canal de chamados da TI não encontrado.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    daily_number, ticket_code, ticket_date = store.next_daily_number()
    payload = {
        "opener_id": interaction.user.id,
        "opener_name": interaction.user.display_name,
        "department": department,
        "category": category,
        "detail": (detail or "").strip() or None,
        "description": (description or "").strip(),
        "status": "novo",
        "assignee_id": None,
        "channel_id": None,
        "queue_message_id": None,
        "created_at": now_local().strftime("%Y-%m-%d %H:%M"),
        "ticket_date": ticket_date,
        "channel_date": current_ticket_day_channel(),
        "daily_number": daily_number,
        "ticket_code": ticket_code,
    }
    store.set_ticket(ticket_code, payload)

    # Salva anexos enviados pelo solicitante (imagens do problema)
    if anexos:
        destino = ATTACHMENTS_DIR / ticket_code.lower().replace("-", "_")
        destino.mkdir(parents=True, exist_ok=True)
        salvos = []
        for i, att in enumerate(anexos, start=1):
            try:
                if getattr(att, "size", 0) and att.size > MAX_ATTACHMENT_BYTES:
                    continue
                data = await att.read()
                if len(data) > MAX_ATTACHMENT_BYTES:
                    continue
                nome = safe_filename(getattr(att, "filename", None) or f"anexo_{i}")
                caminho = destino / f"origem_{i}_{nome}"
                caminho.write_bytes(data)
                salvos.append(str(caminho))
            except Exception:
                pass
        if salvos:
            store.update_ticket(ticket_code, opener_attachments=salvos)

    await refresh_waiting_cards(guild)

    support_role = guild.get_role(ROLE_SUPPORT_ID)
    if support_role:
        dm_text = (
            f"Novo chamado na fila: {ticket_code}\n"
            f"Solicitante: {interaction.user.display_name}\n"
            f"Setor: {department}\n"
            f"Categoria: {category}\n"
            f"Descrição: {payload['description']}"
        )
        sent = 0
        for member in support_role.members:
            if member.bot:
                continue
            try:
                await member.send(dm_text)
                sent += 1
            except Exception:
                pass
        await log_action(guild, f"Notificação privada enviada para {sent} membros da TI sobre {ticket_code}.")

    aviso = ""
    if anexos:
        aviso = " A(s) imagem(ns) que você anexou ficará(ão) disponível(is) na thread do atendimento."
    await interaction.followup.send(
        f"Seu chamado {ticket_code} foi enviado para a fila da TI. "
        f"Assim que um técnico assumir, o bot criará uma thread privada entre vocês.{aviso}",
        ephemeral=True,
    )
    await log_action(guild, f"{ticket_code} entrou na fila da TI por {interaction.user.mention}.")


class TicketSetupView(discord.ui.View):
    """Etapa 1: escolha de setor e categoria (Select nao e aceito dentro de Modal)."""

    def __init__(self):
        super().__init__(timeout=300)
        self.departamento: Optional[str] = None
        self.categoria: Optional[str] = None
        self.add_item(_DepartmentSelect())
        self.add_item(_CategorySelect())

    @discord.ui.button(label="Continuar", style=discord.ButtonStyle.success, emoji="➡️", row=2)
    async def continuar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.departamento or not self.categoria:
            await interaction.response.send_message(
                "Selecione o **setor** e a **categoria** antes de continuar.", ephemeral=True
            )
            return
        await interaction.response.send_modal(
            TicketDescriptionModal(self.departamento, self.categoria)
        )


class TicketDescriptionModal(discord.ui.Modal, title="Descrição do chamado"):
    def __init__(self, department: str, category: str):
        super().__init__()
        self.department = department
        self.category = category
        self.descricao = discord.ui.TextInput(
            label="Descrição do problema",
            style=discord.TextStyle.paragraph,
            max_length=1000,
        )
        self.detalhe = discord.ui.TextInput(
            label="Detalhe (opcional)",
            required=False,
            max_length=120,
            placeholder="Ex.: empresa X, sistema Y, nº do certificado",
        )
        self.add_item(self.descricao)
        self.add_item(self.detalhe)

    async def on_submit(self, interaction: discord.Interaction):
        await criar_chamado(
            interaction,
            self.department,
            self.category,
            self.descricao.value,
            self.detalhe.value,
            [],
        )


class TicketModal(discord.ui.Modal, title="Abrir chamado de TI"):
    """Modal unico (Components V2) com setor, categoria, descricao e anexo."""

    def __init__(self):
        super().__init__()
        self.departamento = discord.ui.Select(
            placeholder="Selecione o setor…",
            options=[discord.SelectOption(label=d, value=d) for d in DEPARTMENTS],
            min_values=1,
            max_values=1,
        )
        self.categoria = discord.ui.Select(
            placeholder="Selecione a categoria…",
            options=[discord.SelectOption(label=c, value=c) for c in CATEGORIES],
            min_values=1,
            max_values=1,
        )
        self.descricao = discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            max_length=1000,
        )
        self.detalhe = discord.ui.TextInput(
            required=False,
            max_length=120,
            placeholder="Ex.: empresa X, sistema Y, nº do certificado",
        )
        self.anexo = discord.ui.FileUpload(required=False, max_values=3)
        self.add_item(discord.ui.Label(text="Setor / Departamento", component=self.departamento))
        self.add_item(discord.ui.Label(text="Categoria", component=self.categoria))
        self.add_item(discord.ui.Label(text="Descrição do problema", component=self.descricao))
        self.add_item(discord.ui.Label(text="Detalhe (opcional)", component=self.detalhe))
        self.add_item(discord.ui.Label(text="Anexar imagem (opcional)", component=self.anexo))

    async def on_submit(self, interaction: discord.Interaction):
        await criar_chamado(
            interaction,
            self.departamento.values[0],
            self.categoria.values[0],
            self.descricao.value,
            self.detalhe.value,
            list(getattr(self.anexo, "values", []) or []),
        )


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir chamado", style=discord.ButtonStyle.success, emoji="🎫", custom_id="abrir_chamado")
    async def abrir_chamado(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TicketModal())
        except Exception as e:
            detalhe = getattr(e, "text", None) or str(e)
            print(f"[modal] falha ao abrir TicketModal (V2): {type(e).__name__}: {detalhe}")
            try:
                await interaction.response.send_message(
                    "Vamos por etapas: escolha o setor e a categoria abaixo.",
                    view=TicketSetupView(),
                    ephemeral=True,
                )
            except Exception:
                pass


@bot.event
async def on_ready():
    if not dashboard_auto_update.is_running():
        dashboard_auto_update.start()
    if not waiting_cards_refresh.is_running():
        waiting_cards_refresh.start()
    bot.add_view(TicketPanelView())
    bot.add_view(QueueControlView())
    bot.add_view(OpenTicketView())
    bot.add_view(ClosedTicketView())
    bot.add_view(DashboardHistoryView())
    # Atualiza o card das threads abertas para incluir os botoes novos (ex.: Adicionar participante)
    guild0 = bot.get_guild(GUILD_ID)
    if guild0 is not None:
        try:
            await migrate_open_tickets(guild0)
        except Exception as e:
            print(f"[migracao] erro: {e}")
    for _, t in list(store.data.get("tickets", {}).items()):
        if (t.get("status") in ("em_andamento", "aguardando_usuario")
                and t.get("channel_id") and t.get("embed_message_id")):
            try:
                canal = bot.get_channel(t["channel_id"]) or await bot.fetch_channel(t["channel_id"])
                msg = await canal.fetch_message(t["embed_message_id"])
                await msg.edit(view=OpenTicketView())
            except Exception:
                pass
    # Remove o painel-fila antigo (formato antigo), se ainda existir
    cfg = store.get_queue_panel()
    if cfg.get("channel_id") and cfg.get("message_id"):
        try:
            canal = bot.get_channel(cfg["channel_id"]) or await bot.fetch_channel(cfg["channel_id"])
            msg = await canal.fetch_message(cfg["message_id"])
            await msg.delete()
        except Exception:
            pass
        store.data["queue_panel"] = {}
        store.save()
    # Garante/atualiza os cards da fila
    guild = bot.get_guild(GUILD_ID)
    if guild is not None:
        try:
            await refresh_waiting_cards(guild)
        except Exception:
            pass
        try:
            await limpar_cards_orfaos(guild)
        except Exception:
            pass
        try:
            await check_integrity(guild)
        except Exception:
            pass
    try:
        synced = await tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")
    print(f"Bot online como {bot.user} ({bot.user.id})")


@tree.command(name="painel", description="Publica o painel de abertura de chamados", guild=discord.Object(id=GUILD_ID))
async def painel(interaction: discord.Interaction):
    support_role = interaction.guild.get_role(ROLE_SUPPORT_ID)
    admin_role = interaction.guild.get_role(ROLE_ADMIN_ID)
    allowed = (support_role and support_role in interaction.user.roles) or (admin_role and admin_role in interaction.user.roles)
    if not allowed:
        await interaction.response.send_message("Apenas a equipe de Tecnologia pode publicar o painel.", ephemeral=True)
        return

    panel_channel = interaction.guild.get_channel(CHANNEL_PANEL_ID)
    if not isinstance(panel_channel, discord.TextChannel):
        await interaction.response.send_message("Canal do painel não encontrado.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Central de Chamados de TI",
        description=(
            "Clique no botão abaixo para abrir um chamado com a equipe de Tecnologia.\n\n"
            "O chamado entrará na fila interna da TI. Quando um técnico assumir, o bot criará uma thread privada entre vocês."
        ),
        color=discord.Color.green(),
    )
    embed.set_footer(text="Fluxo: abertura > fila-ti > aceite do técnico > thread privada")

    await panel_channel.send(embed=embed, view=TicketPanelView())
    await interaction.response.send_message(f"Painel publicado em {panel_channel.mention}.", ephemeral=True)
    await log_action(interaction.guild, f"📨 Painel publicado por {interaction.user.mention} em {panel_channel.mention}.")


@tree.command(name="ranking", description="Mostra o ranking de chamados concluídos", guild=discord.Object(id=GUILD_ID))
async def ranking(interaction: discord.Interaction):
    support_role = interaction.guild.get_role(ROLE_SUPPORT_ID)
    admin_role = interaction.guild.get_role(ROLE_ADMIN_ID)
    allowed = (support_role and support_role in interaction.user.roles) or (admin_role and admin_role in interaction.user.roles)
    if not allowed:
        await interaction.response.send_message("Apenas a equipe de Tecnologia e administradores podem ver o ranking.", ephemeral=True)
        return

    embed = build_support_leaderboard(interaction.guild)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="status", description="Mostra um resumo do chamado atual", guild=discord.Object(id=GUILD_ID))
async def status(interaction: discord.Interaction):
    found = store.get_ticket_by_channel(interaction.channel.id)
    if not found:
        await interaction.response.send_message("Este canal não está vinculado a um chamado individual.", ephemeral=True)
        return
    ticket_id, _ = found
    embed = await build_ticket_embed(interaction.guild, ticket_id)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="meus_chamados", description="Mostra os seus chamados em aberto e os recentes", guild=discord.Object(id=GUILD_ID))
async def meus_chamados(interaction: discord.Interaction):
    tickets = [
        t for t in store.data.get("tickets", {}).values()
        if t.get("opener_id") == interaction.user.id
    ]
    tickets.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    abertos = [t for t in tickets if t.get("status") != "concluido" and not t.get("archived")]
    if abertos:
        alvo = abertos
        titulo = "Seus chamados em aberto"
    else:
        alvo = tickets[:5]
        titulo = "Seus últimos chamados"
    if not alvo:
        await interaction.response.send_message("Você ainda não abriu nenhum chamado.", ephemeral=True)
        return

    linhas = []
    for t in alvo[:10]:
        status = STATUS_LABELS.get(t.get("status"), t.get("status"))
        linha = (
            f"`{t.get('ticket_code', '?')}` • **{status}**\n"
            f"{t.get('department', '?')} / {t.get('category', '?')} • aberto em {t.get('created_at', '?')}"
        )
        if t.get("archived"):
            linha += "\n_thread arquivada_"
        else:
            canal = interaction.guild.get_channel(t["channel_id"]) if t.get("channel_id") else None
            if canal is not None:
                linha += f"\n{canal.mention}"
            elif t.get("channel_name"):
                linha += f"\n_thread #{t['channel_name']} (encerrada)_"
        linhas.append(linha)

    embed = discord.Embed(
        title=titulo,
        description="\n\n".join(linhas),
        color=discord.Color.blurple(),
    )
    embed.set_footer(text=f"Total de chamados seus: {len(tickets)}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    bot.run(TOKEN)
