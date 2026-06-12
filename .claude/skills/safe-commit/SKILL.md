---
name: safe-commit
description: Revisa alterações, valida testes e prepara commit seguro. Invoke manualmente.
disable-model-invocation: true
context: fork
agent: senior-reviewer
argument-hint: [tipo-ou-escopo-opcional]
---

Prepare commit com escopo: $ARGUMENTS

1. Rode `git status` e `git diff --staged`
2. Verifique arquivos que nao devem entrar: .env, __pycache__, *.db, *.log
3. Confirme: `python -m pytest tests/ -x -q`
4. Confirme: `ruff check .`
5. Sugira mensagem (feat/fix/test/docs/refactor/chore)
6. Execute `git commit` SOMENTE se aprovado explicitamente
7. NUNCA execute git push

Saída:
- Arquivos que entrarão
- Arquivos que devem ser excluídos
- Resultado dos testes
- Mensagem de commit sugerida
- Comando exato a executar
