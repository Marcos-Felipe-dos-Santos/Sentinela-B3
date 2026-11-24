# Diário — Fase 4 (blocos 0 e 1)

Fila ativa: `docs/loop/fila.md`. Protocolo: `docs/loop/protocolo.md`. Decisões: `docs/decisoes/decisoes-fase4.md`. A fila e o diário do checkpoint da Fase 3 foram arquivados na ativação em `docs/loop/historico/fase-3/fila-checkpoint.md` e `diario-checkpoint.md`.

### ATIVACAO — chore: activate phase 4 queue
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** ativação dos blocos 0 e 1 pela decisão do Marcos de 24/11/2026, depois da segunda rodada da auditoria DOCUMENTO do Codex (`docs/loop/auditorias/documento-fase4-codex-2.md`, commit `bcb4139`). `git mv` da proposta para `docs/loop/fila.md`; a fila e o diário do checkpoint da Fase 3 (o `[DECISÃO]` dele foi resolvido pelo merge do PR #28 e pela tag `v2-fase-3`) arquivados em `docs/loop/historico/fase-3/`; a "Fase atual" do `AGENTS.md`, escrita pelo Marcos, entra neste commit sem edição do loop; o "Estado da fase", a contagem da suíte e a lista "Fases" (2C e 3 fechadas, 4 ativa nos blocos 0 e 1) do `CLAUDE.md` atualizados para a ativação.
- **Baseline reconferida:** branch `v2/fase-4`, `which python` → `venv/bin/python`; suíte 5220 passed, 1 skipped, 24 xfailed (8 do BUG-3-49, 15 do BUG-3-50, 1 do FII do E2E); Ruff CI e Ruff completo em `sentinela/data` e `sentinela/methods` limpos; golden `500645a3263ad25e…` igual ao `HEAD`; `python scripts/fila.py proximo` → F4-A00a.
- **Dificuldades:** a "Fase atual" trava o `database.py` sem exceção (o F4-A11 precisa dele) e não diz se a exceção `logging_config` cobre o bloco do `logging.basicConfig` no `config.py` (o F4-A00a precisa dele). Os dois casos estão escritos na fila, seção "Permissões".
- **Como resolvi:** nenhum código tocado; os dois pontos ficam para o Marcos antes dos itens.
- **Testes:** 5220 passed, 1 skipped, 24 xfailed → igual.
- **Resíduos:** nenhum. `stash@{0}` antigo (F3-2a-fix) segue guardado.
- **Decisões que ficaram para o Marcos:** exceção escrita para o `database.py` no F4-A11; confirmação de que a exceção `logging_config` cobre o `basicConfig` do `config.py` no F4-A00a.
- **Para o Marcos revisar:** a fila ativa (bloco 0 com 23 itens até o primeiro `[DECISÃO]`).
