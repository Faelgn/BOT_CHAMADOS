# 🎫 BOT_CHAMADOS

Bot de Discord para abertura e gestao de **chamados de TI**: fila de
atendimento, aceite por tecnicos, threads privadas por chamado, dashboards de
produtividade, ranking e envio do historico por e-mail.

> Repositorio **publico**. Nenhum token, senha, ID interno ou dado de pessoa
> real esta versionado. Toda a configuracao sensivel vive em um arquivo `.env`
> local (ver [`.env.example`](.env.example)).

---

## ✨ Funcionalidades

- **Abertura de chamado** por botao no canal de painel, com selecao de
  setor/categoria, descricao, detalhe opcional e anexo de imagens.
- **Fila de atendimento** com cards atualizados (posicao na fila e tempo de
  espera), notificacao por DM para a equipe e botao "Assumir chamado".
- **Atendimento em thread privada** entre solicitante e tecnico responsavel,
  com botoes de status (Aguardando usuario / Concluir / Adicionar participante).
- **Conclusao** do chamado com registro de tempo de resolucao.
- **Envio do historico** completo do chamado (texto + HTML + anexos) por e-mail.
- **Dashboards**: visao geral, produtividade da equipe e operacao, incluindo
  consulta por mes/ano.
- **Ranking** de tecnicos por chamados concluidos.
- **Verificacao de integridade**: detecta cards/threads orfaos e alerta no
  canal de logs.
- **Backups** automatizados do codigo e da base `ticket_data.json`.

## 🧱 Arquitetura

```text
Usuario no Discord
        │  (botao "Abrir chamado")
        ▼
  [ Modal / Etapas ]  setor + categoria + descricao + anexo
        │
        ▼
  [ #fila-ti ]  card do chamado + botao "Assumir"
        │  (tecnico aceita)
        ▼
  [ Thread privada ]  solicitante + tecnico
        │  (Concluir)
        ▼
  [ Historico ]  -> e-mail (SMTP)
```

- **Runtime:** Python 3.11 + `discord.py` 2.7.1.
- **Estado:** arquivo JSON (`ticket_data.json`) + anexos em disco.
- **Integracoes:** Discord (bot) e SMTP (e-mail).
- **Deploy:** Docker / Docker Compose.

Detalhes em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md).

## 📁 Estrutura do repositorio

```text
BOT_CHAMADOS/
├── src/
│   └── bot.py                  # Codigo do bot (versao atual)
├── docs/
│   ├── ARQUITETURA.md          # Visao tecnica e fluxo
│   ├── INSTALACAO.md           # Como rodar localmente
│   ├── IMPLANTACAO.md          # Deploy, systemd, Docker, backups
│   ├── OPERACAO.md             # Comandos e uso no dia a dia
│   ├── SEGURANCA.md            # Checklist e hardening
│   └── HISTORICO.md            # Evolucao das versoes do projeto
├── scripts/
│   ├── backup_codigo.sh        # Backup do codigo
│   └── backup_ticket_data.sh   # Backup validado da base JSON
├── deploy/
│   ├── systemd/                # Unidade de exemplo
│   └── cron/                   # Agendamento dos backups
├── .env.example                # Modelo de configuracao (sem segredos)
├── .gitignore                  # Bloqueia segredos e dados
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── CHANGELOG.md
├── SECURITY.md
├── CONTRIBUTING.md
└── LICENSE
```

## 🚀 Inicio rapido

```bash
# 1. Clone
git clone https://github.com/<SEU_USUARIO>/BOT_CHAMADOS.git
cd BOT_CHAMADOS

# 2. Configure
cp .env.example .env      # preencha os valores reais

# 3. Instale as dependencias
python -m venv venv
# Windows: venv\Scripts\activate   |  Linux: source venv/bin/activate
pip install -r requirements.txt

# 4. Rode
python src/bot.py
```

Passo a passo detalhado em [`docs/INSTALACAO.md`](docs/INSTALACAO.md) e
[`docs/IMPLANTACAO.md`](docs/IMPLANTACAO.md).

## 🐳 Docker

```bash
cp .env.example .env      # preencha
docker compose up -d --build
docker compose logs -f
```

## 🤖 Comandos do bot

| Comando | Descricao | Permissao |
| ------- | --------- | --------- |
| `/painel` | Publica o painel de abertura de chamados | Equipe TI / Admin |
| `/ranking` | Ranking de chamados concluidos | Equipe TI / Admin |
| `/status` | Resumo do chamado do canal atual | Participantes |
| `/meus_chamados` | Seus chamados em aberto/recentes | Todos |
| `/dashboard_publicar` | Publica/recria o dashboard | Equipe TI / Admin |
| `/dashboard_atualizar` | Atualiza o dashboard | Equipe TI / Admin |
| `!sync` | Sincroniza os comandos de barra (dono do bot) | Dono |

## 🔐 Seguranca

Leia [`SECURITY.md`](SECURITY.md) e [`docs/SEGURANCA.md`](docs/SEGURANCA.md).
Resumo:

- Segredos apenas em `.env` (nunca versionado).
- Dados de chamados e anexos fora do repositorio (LGPD).
- Container roda como usuario nao-root.
- Cabecalho de e-mail sanitizado e anexos com nome seguro.
- Se um token vazar: **revogue primeiro**, depois limpe o historico.

## 📜 Licenca

Distribuido sob a licenca MIT. Veja [`LICENSE`](LICENSE).
