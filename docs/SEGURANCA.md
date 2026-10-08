# Seguranca

Este repositorio e **publico**. O objetivo desta pagina e garantir que nada
sensivel seja exposto e que a operacao seja resistente a abusos.

## 1. O que NUNCA pode ser versionado

| Item | Motivo | Onde fica |
| ---- | ------ | --------- |
| `.env` | Contem token do bot e senha de e-mail | local / servidor |
| `ticket_data.json` | Dados de pessoas (LGPD) | servidor |
| `ticket_email_attachments/` | Anexos enviados por usuarios | servidor |
| `backups/` | Copias dos itens acima | servidor |

Todos estao cobertos pelo `.gitignore`. Antes de cada commit, confirme com:

```bash
git status --porcelain
git grep -nE "MT[A-Za-z0-9]{20,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{20,}"  # nao deve retornar nada
```

## 2. Checklist de seguranca do codigo

- [x] Segredos somente via variavel de ambiente (`required_env`).
- [x] IDs de servidor/canal/cargo fora do codigo (`.env`).
- [x] Assunto de e-mail sanitizado (bloqueio de injecao de cabecalho).
- [x] Nomes de arquivo de anexo sanitizados (`safe_filename`).
- [x] Limite de tamanho no download de anexos (anti-exaustao de disco).
- [x] E-mail com TLS e verificacao de certificado
      (`ssl.create_default_context`).
- [x] Container Docker executando como usuario **nao-root**.
- [x] Views persistentes com `custom_id` (sem dependencia de estado em memoria).
- [x] Verificacao de integridade de cards/threads.

## 3. Recomendacoes para a operacao

- **Menor privilegio**: conceda ao bot apenas as permissoes necessarias
  (Manage Channels/Threads, Send Messages, Embed Links, Attach Files).
- **Restringir comandos**: `/painel`, `/ranking` e `/dashboard_*` ja exigem
  cargos de TI/Admin.
- **Protecao do `.env`**: `chmod 600 .env` no servidor.
- **Rotacao periodica** da senha de app do SMTP.
- **Backups fora do host**: guarde uma copia dos backups validados em local
  diferente, evitando perda em caso de falha do servidor.
- **Auditoria**: mantenha o canal de logs do bot restrito a equipe.
- **Nunca** reutilize o servidor de testes para dados reais.

## 4. Resposta a incidente

1. **Conter**: se um token vazar, regenere-o imediatamente no Discord
   Developer Portal (o antigo deixa de funcionar na hora) e troque a senha do
   SMTP. O segredo deve ser considerado invalido mesmo apos regenerar.
2. **Limpar**: remova o segredo do historico do Git
   (`git filter-repo --path .env --invert-paths`) e faca force push, ou
   recrie o repositorio.
3. **Auditar**: revise logs do bot e do provedor de e-mail em busca de uso
   indevido.
4. **Documentar**: registre o ocorrido e a acao tomada.

## 5. Dados pessoais (LGPD)

O bot trata dados de colaboradores (nomes, IDs do Discord, historico de
atendimento e imagens). Boas praticas:

- Retencao limitada: os backups de `ticket_data.json` mantem apenas as ultimas
  copias (o script retem 30).
- Acesso restrito ao host e ao canal de logs.
- Ao descartar o projeto, apague `ticket_data.json` e os anexos com seguranca.
