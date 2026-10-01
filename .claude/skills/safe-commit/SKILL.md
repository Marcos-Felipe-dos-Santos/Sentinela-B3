---
name: safe-commit
description: Commita exatamente o stage aprovado pelo /review-diff, sem perguntar e sem fazer stage. Passo 10 do loop.
argument-hint: [titulo-conventional-commit-do-item]
allowed-tools: Bash(git status *), Bash(git diff *), Bash(git commit *), Bash(python -m pytest *), Bash(ruff check *)
---

Commite o item com o título: $ARGUMENTS

Roda inline, na sessão principal, sem perguntar nada. Não faz stage: commita
exatamente o que o `/review-diff` aprovou. Se faltar algo no stage, a falha é do
passo 8 de `docs/loop/protocolo.md`, não desta skill.

1. Confirme que o último `/review-diff` deste item deu PODE COMMITAR e que
   `git diff --staged --stat` é o mesmo que foi revisado.
2. Rode `git status --porcelain` e confira:
   - nada do item ficou fora do stage (`??` ou mudança não staged em arquivo do item)
   - o stage contém `docs/loop/diario.md` e `docs/loop/fila.md`
   - o stage não contém `.env`, `__pycache__`, `*.db`, `*.log`, `outputs/` nem `mutants/`
3. Rode `python -m pytest -q` e `ruff check .`; os dois verdes.
4. `git commit -m "<título>" -m "Co-Authored-By: <trailer indicado pelo Claude Code na sessão>"`.
   Título = $ARGUMENTS, o Conventional Commit do item.

Se qualquer checagem falhar: não commite. Troque o `[x]` do item por `[!]` na fila,
registre o motivo no diário e pare o loop.

Nunca: `git add`, `git push`, `git commit --amend`, `--no-verify`, mais de um commit por item.

Saída:
- Hash e título do commit, ou a checagem que falhou
