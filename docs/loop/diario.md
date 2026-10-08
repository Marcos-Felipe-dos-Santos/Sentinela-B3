# Diário do loop — Fase 2A

**Estado inicial (preparação):** branch `v2/fase-2a`, `which python` → `venv/bin/python`, documentos obrigatórios presentes. `python -m pytest -q`: 685 passed, 1 skipped, 2 xfailed.

### F2A-15 — chore: add golden diff tool for scoped regeneration
- **Status:** sucesso
- **O que foi feito:** `scripts/golden_diff.py` compara o golden do `HEAD` (`git show`) ou de `--base` com o da árvore de trabalho, por (motor, id): lista alterados, incluídos e removidos. `--onde` avalia a expressão (com `caso`, `entrada`, `saida_antiga`, `saida_nova`) só nos alterados e sai com 1 se algum falhar. `--par ANTIGO=NOVO` pareia removidos e incluídos e mostra a diferença campo a campo. Sem dependência nova; não roda o gerador nem altera o golden.
- **Dificuldades:** `eval` com escopo local não enxerga as variáveis dentro de geradores (`any(... for ...)`).
- **Como resolvi:** as variáveis do predicado vão no dicionário de globals do `eval`, com builtins restritos a uma lista curta.
- **Testes:** 685 passed, 1 skipped, 2 xfailed → 691 passed, 1 skipped, 2 xfailed (6 novos em `tests/test_golden_diff.py`, incluindo os 3 do aceite). Rodado sem mudança no golden: 0 alterados, 0 incluídos, 0 removidos.
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** o `eval` do `--onde` é ferramenta de desenvolvimento, para expressões escritas por quem roda o script.
