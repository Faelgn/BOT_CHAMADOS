# Contribuindo

Obrigado pelo interesse em contribuir com o BOT_CHAMADOS!

## Fluxo de trabalho

1. Crie uma branch a partir da `main`:
   ```bash
   git checkout -b feat/minha-melhoria
   ```
2. Faca commits pequenos e descritivos.
3. Abra um Pull Request explicando o "por que" da mudanca.

## Padroes

- Python 3.11+, seguindo o estilo do arquivo existente (PEP 8).
- **Nunca** faca commit de `.env`, tokens, senhas, IDs internos ou dados reais
  de chamados.
- Ao adicionar dependencia, atualize o `requirements.txt`.
- Descreva mudancas visiveis ao usuario no `CHANGELOG.md`.

## Checklist antes do PR

- [ ] O codigo roda (`python src/bot.py`) sem erros de importacao.
- [ ] Nenhum segredo ou dado pessoal foi adicionado.
- [ ] `CHANGELOG.md` atualizado quando aplicavel.
