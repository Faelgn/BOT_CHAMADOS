# Changelog

Todas as mudancas relevantes deste projeto sao documentadas aqui.
O formato segue a ideia de [Keep a Changelog](https://keepachangelog.com/pt-BR/).

## [1.0.0] - 2026-10-08

### Adicionado

- Primeira versao publica e organizada do BOT_CHAMADOS.
- Codigo consolidado da versao em producao (`main0015`) reorganizado em
  `src/bot.py`.
- Documentacao completa (`README`, arquitetura, instalacao, implantacao,
  operacao, seguranca e historico).
- Templates de ambiente (`.env.example`), `.gitignore` e `.dockerignore`
  reforcados para impedir vazamento de segredos e dados de pessoas.
- `Dockerfile` executando como usuario nao-root e `docker-compose.yml` com
  volumes persistentes de dados.
- Scripts de backup do codigo e da base JSON em `scripts/`.
- Unidade systemd e agendamento de cron de exemplo em `deploy/`.
- **Testes automatizados** (`tests/`, pytest) e configuracao de lint (Ruff).
- Badges de CI, versao do Python e licenca no `README`.

### Seguranca

- Removidos/normalizados pontos de risco antes da publicacao:
  - **Assunto de e-mail sanitizado** para impedir injecao de cabecalho.
  - **Limite de tamanho de anexo** no download, evitando exaustao de disco.
  - Caminhos de dados (`DATA_FILE`, `ATTACHMENTS_DIR`) configuraveis por
    variavel de ambiente.
- Confirmado que **nenhum** token, senha, ID do Discord ou dado real de
  chamado esta presente no codigo versionado.

### Notas

- Esta versao corresponde ao comportamento da versao de producao `main0015`,
  com ajustes de seguranca e organizacao. A versao oficial em execucao no
  servidor **nao** foi alterada.
