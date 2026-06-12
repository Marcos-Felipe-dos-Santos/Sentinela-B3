---
name: refactor-suggester
description: Sugere refatoração incremental e segura. Nunca altera arquivos.
context: fork
agent: senior-reviewer
argument-hint: [arquivo-ou-módulo]
---

Sugira refatoração para: $ARGUMENTS

1. Leia apenas os arquivos relevantes
2. Identifique acoplamento, duplicação e responsabilidades misturadas
3. Proponha mudanças pequenas e ordenadas
4. Nao altere arquivos

Saída:
- Problema principal
- Refatoração sugerida em ordem de commits
- Testes necessários
- Riscos e critérios de sucesso
