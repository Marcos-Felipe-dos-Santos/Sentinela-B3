---
name: review-diff
description: Revisa o diff atual. Use sempre antes de qualquer commit.
context: fork
agent: senior-reviewer
---

Revise o diff com foco em: $ARGUMENTS

1. Rode `git diff` e `git diff --staged`
2. Para cada arquivo alterado avalie:
   - Bug lógico ou regressão?
   - Fórmula financeira correta economicamente?
   - Teste cobre o caso novo?
   - Segredo ou dado sensível acidental?
   - Linguagem sugere recomendação de investimento?
3. Não altere arquivos

Saída:
- Veredito: PODE COMMITAR / NAO PODE COMMITAR
- Problemas críticos
- Problemas médios
- Mensagem de commit sugerida (Conventional Commits)
