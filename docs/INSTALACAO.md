# Instalacao (ambiente local)

## Pre-requisitos

- Python 3.11 ou superior.
- Uma aplicacao de bot no [Discord Developer Portal](https://discord.com/developers/applications).
- Acesso a um servidor SMTP (para o envio de historico por e-mail).

## 1. Clonar o repositorio

```bash
git clone https://github.com/Faelgn/BOT_CHAMADOS.git
cd BOT_CHAMADOS
```

## 2. Criar e ativar o ambiente virtual

```bash
python -m venv venv

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate
```

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

## 4. Configurar o `.env`

```bash
cp .env.example .env
```

Preencha o `.env`. Para obter cada ID no Discord:

1. Ative **Configuracoes do usuario > Avancado > Modo desenvolvedor**.
2. Clique com o botao direito no servidor/canal/cargo/mensagem e escolha
   **Copiar ID**.

Campos obrigatorios: `DISCORD_TOKEN`, `GUILD_ID`, `CHANNEL_PANEL_ID`,
`CHANNEL_LOGS_ID`, `CHANNEL_QUEUE_ID`, `CHANNEL_DASHBOARD_ID`,
`ROLE_SUPPORT_ID`, e os campos de SMTP.

## 5. Habilitar os *Intents* no Developer Portal

Em **Bot > Privileged Gateway Intents**, ative:

- **Server Members Intent** (necessario para listar a equipe e o cargo).

O codigo usa `message_content = False`, entao o intent de conteudo de mensagem
**nao** e necessario.

## 6. Convidar o bot

Em **OAuth2 > URL Generator**, marque os escopos `bot` e `applications.commands`
e as permissoes: *Manage Channels*, *Manage Threads*, *Send Messages*,
*Embed Links*, *Attach Files*, *Read Message History*.

## 7. Rodar

```bash
python src/bot.py
```

Na primeira execucao o bot cria `ticket_data.json` e a pasta de anexos
automaticamente. Publicar o painel com `/painel` (como membro da equipe de TI).

## Dicas de teste

- Use um servidor Discord de testes para nao interferir na operacao real.
- Para simular envio de e-mail, configure um SMTP de teste (ex.: Mailtrap) no
  `.env`.
