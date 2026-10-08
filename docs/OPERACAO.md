# Operacao

Guia do dia a dia para a equipe de Tecnologia.

## Comandos

| Comando | O que faz | Quem pode |
| ------- | --------- | --------- |
| `/painel` | Publica o painel com o botao "Abrir chamado" | Equipe TI / Admin |
| `/ranking` | Ranking de tecnicos por chamados concluidos | Equipe TI / Admin |
| `/dashboard_publicar` | Publica ou recria o dashboard | Equipe TI / Admin |
| `/dashboard_atualizar` | Forca a atualizacao do dashboard | Equipe TI / Admin |
| `/status` | Mostra o resumo do chamado do canal atual | Participantes |
| `/meus_chamados` | Lista seus chamados em aberto/recentes | Todos |
| `!sync` | Sincroniza os comandos de barra | Dono do bot |

## Fluxo do tecnico

1. Ao abrir um chamado, o bot envia **DM** para a equipe.
2. Veja a fila em `#fila-ti` e clique em **Assumir chamado** (pelo card ou pelo
   seletor do painel).
3. Atenda na **thread privada**. Use:
   - **Aguardando usuario** — quando depende de resposta do solicitante.
   - **Adicionar participante** — para incluir outra pessoa no atendimento.
   - **Concluir** — ao finalizar.
4. Apos concluir, use **Enviar E-mail** para registrar o historico.

## Fluxo do solicitante

1. Clique em **Abrir chamado** no painel.
2. Escolha setor e categoria, descreva o problema e anexe imagens se precisar.
3. Acompanhe pela thread privada criada quando o tecnico assumir.
4. Recebe DM quando o chamado for assumido, ficar aguardando resposta ou for
   concluido.

## Dashboard

- Publicado no canal de dashboard e atualizado a cada 10 minutos.
- Botao **Ver historico** permite consultar qualquer mes/ano.
- Chamados marcados como "Teste" sao ignorados nas metricas.

## Manutencao

| Situacao | Acao |
| -------- | ---- |
| Card orfao na fila | O bot limpa automaticamente a cada 10 min |
| Thread/canal apagado | O bot alerta no canal de logs |
| Bot fora do ar | Reinicie o servico (`systemctl restart` / `docker compose up -d`) |
| Token comprometido | Regenere no Developer Portal e atualize o `.env` |

## Solucao de problemas

- **Bot nao abre o modal** — versao do `discord.py` antiga; o codigo tem
  fallback em etapas. Atualize para `2.7.1`.
- **"Nao consegui adicionar o solicitante"** — verifique se o cargo/pessoa tem
  **Ver Canal** no canal pai das threads.
- **E-mail nao envia** — confira `SMTP_*` no `.env`; portas 587 (starttls) ou
  465 (ssl). Ajuste `SMTP_SSL_MODE` se necessario.
- **Comandos nao aparecem** — rode `!sync` como dono do bot.
