# Politica de Seguranca

## Versoes suportadas

Apenas a versao mais recente na branch `main` recebe correcoes de seguranca.

| Versao | Suporte |
| ------ | ------- |
| Atual  | Sim     |
| Antigas | Nao    |

## Reportando uma vulnerabilidade

Se voce encontrar uma falha de seguranca, **nao abra uma issue publica**.
Envie um relato privado para o mantenedor do projeto (ver contato no README)
com:

1. Descricao da falha e impacto potencial.
2. Passos para reproduzir.
3. Versao/commit afetado.
4. Sugestao de correcao (se tiver).

Voce recebera um retorno assim que possivel. Pedimos que nao divulgue a falha
publicamente antes de uma correcao ser publicada.

## Praticas adotadas neste projeto

- **Nenhum segredo no codigo.** Token do Discord, SMTP e IDs vem de variaveis
  de ambiente (`.env`), que nunca e versionado.
- **Nenhum dado de pessoas no repositorio.** `ticket_data.json`,
  `ticket_email_attachments/` e `backups/` estao no `.gitignore`.
- **Imagem Docker sem privilegios.** O container roda como usuario nao-root.
- **Envio de e-mail com TLS** e verificacao de certificado
  (`ssl.create_default_context`).
- **Sanitizacao de nomes de arquivo** de anexos antes de gravar em disco.
- **Cabecalho de e-mail sanitizado** contra injecao (`\r`/`\n`).

## Se um segredo vazar

1. **Revogue imediatamente**: regenere o token do bot no Discord Developer
   Portal e troque a senha de app do SMTP.
2. Remova o segredo do historico do Git (ex.: `git filter-repo`) e faca force
   push, ou recrie o repositorio.
3. Audite os logs do bot e do provedor.

> Regenerar o token invalida o antigo na hora, entao essa e a prioridade numero 1.
