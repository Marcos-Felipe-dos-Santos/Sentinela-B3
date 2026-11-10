# Diário — Fase 3 (Tempo como entrada)

Fila ativa: `docs/loop/fila.md`, ativada em 10/11/2026 (`da0a78c`). O diário do Processo F3-0, bloco 1, está em `docs/loop/historico/fase-3/processo-f3-0/diario.md`.

### Preparação — ativação da 3-a e baseline de ativação (decisão 20)
- **Executor:** claude-code (Claude Opus 5.5).
- **Estado inicial:** branch `v2/fase-3` @ `da0a78c`; `which python` → `venv/bin/python`; documentos obrigatórios da preparação do protocolo presentes.
- **Baseline de ativação** (HEAD `da0a78c`, com o Bloco 1 do F3-0 e as rodadas F3-0h a F3-0k; `git --no-pager log --oneline 284165f..HEAD`: 19 commits):
  - Suíte: `python -m pytest -q` → **3599 passed, 1 skipped, 8 xfailed, 1 warning**.
  - Golden: SHA256 `500645a3263ad25e492bff56e00c9b3552b84a243136d3397f520d4a79c24bcc`, igual à histórica.
  - Ruff CI e Ruff completo em `sentinela/methods` e `sentinela/data`: verdes. `ruff check .`: 161 apontamentos.
  - Vulture (mesmo comando): 3 apontamentos. `deptry .`: 1 apontamento.
- **Diferença para a histórica (`284165f`):** +74 testes, todos em `tests/test_script_fila.py`, o único arquivo de `tests/` alterado no intervalo (`git diff --stat 284165f..HEAD -- tests/`: 1 arquivo, 612 inserções); 38 do F3-0a, 31 do F3-0h, 5 do F3-0j. Ruff, vulture, deptry e golden iguais. Nenhuma divergência sem explicação no git.

### F3-1a — fix: stop network access when importing config
- **Executor:** claude-code (Claude Opus 5.5).
- **Status:** sucesso.
- **O que foi feito:** `MacroContext.__init__` guarda só a Selic explícita (`None` sem argumento); `selic` devolve a explícita ou `get_selic_atual()` sob demanda, com o cache de 24 h e o `SELIC_FALLBACK` que já existiam; `selic_liquida` passa a ler `self.selic`. `MACRO = MacroContext()` continua no módulo, sem rede no import. `tests/conftest.py` (quebra autorizada F3-1): sai o stub de `requests.get` durante o import; a semente 14,75% vai direto para o cache de `get_selic_atual` (`_selic_cache_value`, `_selic_cache_time = inf`, válido pela sessão); mesmo valor, outro mecanismo; a fixture `_selic_semeada` não mudou. Testes que fazem `patch.object(MACRO, "_selic", ...)` (seção A protegida, `test_bazin_motor.py`) continuam valendo, porque o atributo é o mesmo.
- **Regressão:** BUG-3-01 (E-6), `tests/regressao/test_bug_3_01_config_import_com_rede.py`, registrada no README na seção nova "Fase 3". Em subprocesso, com `socket.connect` e `requests.get` bloqueados, importa `config` do zero e conta as tentativas. Antes, com xfail estrito e `--runxfail`: falhava com `requests.get https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json`; depois da correção, XPASS estrito derrubou a suíte; marca retirada, PASS.
- **Mutação:** `python -m mutmut run "config.xǁMacroContextǁ*"`: `__init__` 3/3 mortos; o mutmut 3 não muta métodos com `@property`, então `selic` e `selic_liquida` foram quebrados à mão (`outputs/f3-1a-mao.txt`): ignorar a explícita e não carregar sob demanda morreram na suíte; `selic_liquida` pelo atributo cru sobreviveu e ganhou `test_selic_sem_argumento_e_lida_sob_demanda` em `tests/test_macro_context.py`, que a mata. Os fetchers `_fetch_bcb` (sem teste) e `_fetch_ipca_acumulado` (17 sobreviventes) não mudaram neste item: dívida antiga, fora do escopo.
- **Testes:** 3599 passed, 1 skipped, 8 xfailed → 3601 passed, 1 skipped, 8 xfailed (+2: a regressão e o teste da carga sob demanda). Ruff CI, Ruff completo em `sentinela/methods` e `sentinela/data`: verdes. Golden SHA igual.
- **Resíduos:** nenhum; `mutants/` fora do git.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** a semente no cache com `_selic_cache_time = inf` (só nos testes); o ID novo BUG-3-01 para o E-6, que não tinha ID de bug. Revisão: PODE COMMITAR; docstring de `tests/test_macro_context.py` atualizada. Ficam para depois: o fallback da Selic não vai ao cache, então com o BCB fora cada leitura de `MACRO.selic` tenta de novo (único leitor de produção hoje: `scripts/dossie_fase2.py`); as armadilhas 7 e 8 do `CLAUDE.md` ainda dizem que o import faz rede (fora dos arquivos do item).
