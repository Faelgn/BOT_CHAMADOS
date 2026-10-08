# Arquitetura

## Visao geral

O BOT_CHAMADOS e um bot de Discord que implementa um fluxo de *service desk*
de TI. Todo o estado fica em um arquivo JSON local e os anexos em disco; nao ha
banco de dados externo.

## Componentes

| Componente | Papel | Arquivo/Servico |
| ---------- | ----- | --------------- |
| Bot Discord | Interface do usuario e logica do fluxo | `src/bot.py` (`discord.py`) |
| Armazenamento | Chamados, contadores e ponteiros de mensagens | `ticket_data.json` |
| Anexos | Imagens enviadas nos chamados e geradas nos historicos | `ticket_email_attachments/` |
| E-mail | Envio do historico completo do chamado | SMTP (starttls/ssl) |
| Deploy | Empacotamento e execucao | Docker / Compose |

## Fluxo de um chamado

1. **Abertura** — usuario clica em "Abrir chamado" no painel. Um modal
   (Components V2) coleta `setor`, `categoria`, `descricao`, `detalhe` e
   anexos. Ha um fallback em etapas caso o modal V2 nao seja suportado.
2. **Fila** — o chamado e gravado em `ticket_data.json` com status `novo` e
   ganha um card em `#fila-ti`. A equipe recebe DM.
3. **Aceite** — um tecnico clica em "Assumir chamado". O bot cria uma **thread
   privada** entre solicitante e tecnico (ou, em fallback, um canal privado),
   move o card e muda o status para `em_andamento`.
4. **Atendimento** — na thread, botoes permitem `Aguardando usuario`,
   `Adicionar participante` e `Concluir`.
5. **Conclusao** — status `concluido`, com `closed_at` registrado para as
   metricas.
6. **Historico** — opcionalmente, o bot monta um e-mail (texto + HTML com
   imagens embutidas + anexos) e envia via SMTP.
7. **Encerramento** — a thread e arquivada/travada (ou o canal e excluido).

## Estados do chamado

```text
novo ──(assumir)──► em_andamento ──(concluir)──► concluido
                          │  ▲
             (aguardando) │  │ (retomada)
                          ▼  │
                   aguardando_usuario
```

## Estruturas de dados

`ticket_data.json`:

```jsonc
{
  "counter": 15,                 // contador diario
  "last_counter_date": "08-10-2026",
  "tickets": {
    "CH-08-10-2026-0001": {
      "opener_id": 0,            // ID do Discord (nao versionado)
      "department": "Fiscal",
      "category": "Certificado Digital",
      "status": "novo",
      "assignee_id": null,
      "channel_id": null,
      "queue_message_id": null,
      "created_at": "2026-10-08 09:12",
      "daily_number": 1,
      "ticket_code": "CH-08-10-2026-0001"
    }
  },
  "dashboard":   { "channel_id": 0, "message_id": 0 },
  "queue_panel": { "channel_id": 0, "message_id": 0 }
}
```

> Nunca versione este arquivo: ele contem dados de pessoas.

## Tarefas periodicas

- `dashboard_auto_update` — atualiza o dashboard a cada 10 min.
- `waiting_cards_refresh` — recalcula cards da fila, remove cards orfaos e
  executa a verificacao de integridade a cada 10 min.

## Decisoes de projeto

- **IDs por variavel de ambiente**: facilita trocar de servidor sem editar
  codigo e evita vazamento de IDs internos.
- **Armazenamento em JSON**: simples e sem dependencia externa; adequado ao
  volume atual. A migracao para SQLite e um caminho natural de evolucao.
- **Threads privadas** em vez de canais: menos poluicao e historico preservado.
- **Fallback** para canal privado caso o bot nao tenha permissao de criar
  threads privadas.
