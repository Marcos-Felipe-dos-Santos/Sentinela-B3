# Diário do loop — Fase 2B

**Estado inicial (preparação):** branch `v2/fase-2b`, `which python` → `venv/bin/python`, documentos obrigatórios presentes. `python -m pytest -q`: 1362 passed, 1 skipped, 18 xfailed.

### F2B-35 — docs: sync agent instructions after the phase 2A closure
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** cada linha conferida com `grep -n` contra o código e o git:
  - `CLAUDE.md:28` (Comandos): suíte em ~1.380 testes, 94 módulos, ~10 s (`python -m pytest --collect-only -q`: 1.381 coletados; `--collect-only` lista 94 `<Module>`; a suíte rodou em 7–10 s).
  - `CLAUDE.md:50` (linha do `valuation_engine.py`) e `CLAUDE.md:199-203` (armadilha 14): fora do índice, a cascata grava a classe do classificador e a guarda do motor atua. Conferido em `market_engine.py` (bloco do F2A-43 logo depois de `_aplicar_referencia`, commit `8f2badb`) e em `valuation_engine.py:125` (`classe = dados.get('classe_ativo')`).
  - `CLAUDE.md:141-142` (armadilha 2): o F2A-11 fica como origem do P/VP da CVM; a pendência é o BUG-2A-12, aberto, corrigido pelo F2B-16 (`tests/regressao/README.md:45`; o destino no registro troca no F2B-36).
  - `CLAUDE.md:255` (Fases): 2A concluída com a tag `v2-fase-2a` (`git tag` confirma), 2B em execução no branch `v2/fase-2b`.
  - `CLAUDE.md:300` (Testes): rito da D27, xfail estrito → correção → marca retirada → PASS.
  - `CLAUDE.md:310-319`: seção "Bugs e regressão", com o texto do `AGENTS.md:109-118` (só "mantenedor" → "Marcos", como no resto do `CLAUDE.md`).
  - `AGENTS.md:11`: a mesma contagem da suíte. A "Fase atual" não foi tocada.
  - `docs/PLANO.md`: saiu o parágrafo "O ADR-0003 acrescenta, antes do F2A-7: …" (os sete itens que ele cita, F2A-32 a F2A-38, estão na tabela da Fase 2A); o gate da Fase 2B (`:258`) diz "seção A muda só no F2B-7 ([SEÇÃO A] em (c), decisão de 18/10/2026)".
- **Dificuldades:** nenhuma.
- **Como resolvi:** —
- **Testes:** 1362 passed, 1 skipped, 18 xfailed → sem mudança (só documentos). Golden: `git diff --exit-code HEAD -- tests/fixtures/golden_motores.jsonl` sem diferença; `tests/test_financeiro_pre_refactor.py` sem diferença desde `v2-fase-2a`.
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** a armadilha 7 do `CLAUDE.md` (`:165`) ainda diz "33 dos 76 módulos não usam mock"; o item manda só a contagem de "Comandos", então a frase ficou como estava (recontar os módulos sem mock é trabalho à parte). O cabeçalho da `docs/loop/fila.md` ainda diz "Proposta, não ativa", herdado do `git mv`.
