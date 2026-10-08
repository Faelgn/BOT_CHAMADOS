# Historico e evolucao do projeto

O bot evoluiu de um script simples para um sistema de atendimento completo. As
versoes abaixo (`main0001` ... `main0015`) foram etapas de desenvolvimento; esta
versao publica consolida o estado final em `src/bot.py`.

## Linha do tempo

| Versao | Marco principal |
| ------ | --------------- |
| `main0001` | Primeira versao funcional: abertura de chamado, aceite, conclusao e envio de e-mail. |
| `main0002`–`main0008` | Ajustes de fluxo, permissoes, mensagens e estabilidade. |
| `main0009` | Introducao do **ranking/leaderboard** de tecnicos. |
| `main0010`–`main0011` | Refinos do ranking e das mensagens. |
| `main0012` | Introducao do **dashboard** de metricas. |
| `main0013`–`main0015` | Dashboards por periodo, historico mensal e melhorias gerais. |
| Producao `main0015` (servidor) | Amadurecimento em operacao real: taxonomia de setores/categorias, fuso horario, painel de fila, threads privadas (com fallback para canal), anexos do solicitante, DMs, verificacao de integridade, migracao automatica e modal Components V2. |

## O que esta nesta versao publica

- Codigo consolidado da versao de producao (`main0015`, ~2150 linhas).
- Reorganizacao em `src/bot.py` e separacao de scripts, docs e deploy.
- Correcoes de seguranca aplicadas na preparacao para publicacao:
  - sanitizacao do assunto de e-mail;
  - limite de tamanho de anexo;
  - caminhos de dados configuraveis por ambiente.
- Remocao de qualquer segredo, ID interno ou dado real.

## Como consultar o historico antigo

As versoes antigas **nao** fazem parte deste repositorio (decisao de manter o
projeto enxuto e sem codigo obsoleto com riscos). Elas permanecem nos backups do
servidor de producao e no ambiente local de desenvolvimento.

Se quiser consultar uma etapa especifica, use o backup correspondente:

```bash
ls -1t backups/codigo/main0015.py.*
```

> As versoes antigas usavam a mesma base de configuracao por variavel de
> ambiente, portanto nao continham segredos embutidos.
