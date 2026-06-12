---
name: project-audit
description: Audita o estado atual do projeto antes de qualquer trabalho.
context: fork
---

Audite o projeto com foco em: $ARGUMENTS

1. Rode `git status` e `git log --oneline -10`
2. Leia CLAUDE.md, README.md e pyproject.toml
3. Liste arquivos .py com responsabilidades
4. Leia a seção "Bugs conhecidos" do CLAUDE.md
5. Não altere nenhum arquivo

Saída:
- Resumo executivo (3 linhas)
- Arquivos principais e responsabilidades
- Comandos de test/lint/run detectados
- Bugs conhecidos confirmados no código
- Próxima ação mais segura
