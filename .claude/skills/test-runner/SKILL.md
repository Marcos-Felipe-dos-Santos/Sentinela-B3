---
name: test-runner
description: Executa o menor conjunto de testes relevante para a mudança atual.
context: fork
agent: junior-dev
---

Execute testes com foco em: $ARGUMENTS

1. Identifique arquivos alterados com `git diff --name-only`
2. Encontre o teste correspondente em tests/
3. Rode: `python -m pytest tests/test_arquivo.py -v --tb=short`
4. Se nao houver teste específico, rode a suite completa
5. Nao altere arquivos

Saída:
- Comandos executados
- Resultado (passou/falhou)
- Falhas com causa provável
