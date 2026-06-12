---
name: changelog-generator
description: Gera resumo legível das mudanças recentes.
context: fork
agent: junior-dev
---

Gere changelog com foco em: $ARGUMENTS

1. Rode `git log --oneline -20` ou `git diff`
2. Agrupe por tipo: feat, fix, docs, test, refactor, chore
3. Nao altere arquivos

Saída:
- Resumo curto
- Mudanças por categoria
- Impacto para usuário
- Riscos conhecidos
