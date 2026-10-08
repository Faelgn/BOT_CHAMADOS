# Implantacao (producao)

Ha duas formas de colocar em producao: **Docker** (recomendado) ou **systemd
com ambiente virtual**. Em ambos os casos, segredos ficam no `.env` e os dados
persistem fora do repositorio.

> ⚠️ **Nunca** substitua a versao em producao sem antes testar em um ambiente
> separado. Este repositorio foi montado para conviver ao lado da versao
> oficial sem altera-la.

## Opcao A - Docker Compose (recomendado)

```bash
git clone https://github.com/<SEU_USUARIO>/BOT_CHAMADOS.git
cd BOT_CHAMADOS
cp .env.example .env      # preencha os valores reais
mkdir -p data ticket_email_attachments

docker compose up -d --build
docker compose logs -f
```

O `docker-compose.yml`:

- usa `.env` como `env_file`;
- monta `./data` e `./ticket_email_attachments` como volumes persistentes;
- reinicia automaticamente (`restart: unless-stopped`);
- roda como usuario nao-root (definido no `Dockerfile`).

## Opcao B - systemd + venv

1. Clone o projeto em `/opt/BOT_CHAMADOS`.
2. Crie o venv e instale as dependencias.
3. Crie o `.env` a partir do exemplo (permissao `chmod 600 .env`).
4. Copie `deploy/systemd/bot-chamados.service` para
   `/etc/systemd/system/`, ajuste `User`, `WorkingDirectory` e `EnvironmentFile`.
5. Ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bot-chamados
sudo journalctl -u bot-chamados -f
```

## Backups

Os scripts em `scripts/`:

- `backup_codigo.sh` — guarda copias do codigo (`backups/codigo`).
- `backup_ticket_data.sh` — valida o JSON antes de guardar em `backups/dados`.

Exemplo de agendamento (`deploy/cron/crontab.example`):

```cron
0 23 * * * /caminho/BOT_CHAMADOS/scripts/backup_ticket_data.sh >> /var/log/bot_chamados_backup.log 2>&1
30 23 * * * /caminho/BOT_CHAMADOS/scripts/backup_codigo.sh >> /var/log/bot_chamados_backup.log 2>&1
```

> Ajuste os caminhos `BASE` dentro dos scripts para o diretorio real.

## Atualizacao

```bash
git pull
docker compose up -d --build      # ou: sudo systemctl restart bot-chamados
```

## Requisitos de rede

O host precisa de saida HTTPS para a API do Discord e para o servidor SMTP.
Nenhuma porta de entrada e necessaria.

## Checklist pos-deploy

- [ ] `/painel` publica o painel no canal correto.
- [ ] Abrir um chamado de teste e assumir cria a thread privada.
- [ ] Concluir e "Enviar E-mail" entrega o historico.
- [ ] `/dashboard_publicar` e `/ranking` respondem.
- [ ] Logs sem erros recorrentes.
