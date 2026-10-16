# Diário do loop — Fase 2A, fechamento das auditorias

Fila: `docs/loop/fila.md`. Diário da fase arquivado em `docs/loop/historico/fase-2a/diario.md`.

- **Preparação (15/10/2026):** branch `v2/fase-2a`, os seis documentos presentes. O Claude Code abriu sem a venv ativada (`which python` sem resultado); como na sessão anterior, todos os comandos começam com `source venv/bin/activate`, e com ela `which python` → `venv/bin/python`. `python -m pytest -q`: 1.343 passed, 1 skipped, 1 xfailed.

### F2A-40 — test: register audited bugs as strict regression tests
- **Status:** sucesso
- **O que foi feito:** criei `tests/regressao/` com 18 arquivos, um por bug (BUG-2A-01 a 18), todos xfail estrito com `reason="BUG-2A-NN · <sintoma> · corrige: <item>"`; 28 casos no total (o 01 tem três testes, um deles parametrizado nos cinco campos; 02 tem dois; 05, 06 e 17 são parametrizados). `tests/regressao/README.md` traz a regra e o registro (ID, sintoma, evidência arquivo:linha, origem, teste, item que corrige, estado "aberto"). Seção "Bugs e regressão" no `docs/loop/protocolo.md` (antes do formato do diário) e no `AGENTS.md` (antes de "Comandos", fora da "Fase atual"). CI: o passo de testes roda `python -m pytest tests/ --tb=short -rxX`.
- **Dificuldades:** cada teste tinha de exercitar o comportamento correto sem decidir o que a 2B ainda vai decidir. No BUG-2A-10 (TTM) a regra 7.2 admite reserva ou abstenção; no BUG-2A-02, 03 e 17 o texto exato do motivo é do item que corrige. No BUG-2A-14, o desempate do pandas em empate de data mantém a ordem do arquivo.
- **Como resolvi:** os testes afirmam só o que a regra já fixa: no 10, que o lucro dos controladores zerado não entra como zero literal (`!= 0.0`); no 02 e 03, valor nulo, sem reserva e com algum motivo; no 05, o `MOTIVO_PL_INVALIDO` que já existe; no 17 e 18, `Abstention`. No 14, a versão 1 vem antes da 2 no arquivo, e o teste pede a 2. Os helpers vêm dos testes existentes (`_engine`, `_motor`, `_cascata`, `_html`, `_zip`, `_make_inf_zip`), sem duplicar fixture.
- **Testes:** 1.343 passed, 1 skipped, 1 xfailed → 1.343 passed, 1 skipped, 29 xfailed. Rito `test`: mutação não se aplica a teste xfail; cumprido pela execução com `--runxfail` (todos os 18 se reproduziram; nenhum foi para "não reproduzido"). Linha de falha de cada um (`python -m pytest tests/regressao -q --runxfail --tb=line`):
  - BUG-2A-01: `test_bug_2a_01…py:27: assert 2.0 == -1.0` (lpa, vpa, roe, pl, pvp); `:33: assert ['pl', 'roe'] == []`; `:45: assert 0.1 == -0.05 ± 5.0e-08`
  - BUG-2A-02: `…02…py:38: assert 70.0 is None`; `:46: assert 100.0 is None`
  - BUG-2A-03: `…03…py:30: assert 100.0 is None`
  - BUG-2A-04: `…04…py:40: assert 100.0 is None`
  - BUG-2A-05: `…05…py:29: assert None == 'PL dos controladores com valor inválido no documento'` (valor inválido e linhas divergentes)
  - BUG-2A-06: `…06…py:26: assert nan is None`; `assert inf is None`
  - BUG-2A-07: `…07…py:30: assert 'COMPRA' == 'FORA DO ESCOPO DOS MÉTODOS'`
  - BUG-2A-08: `…08…py:21: assert 'P/VP = 1,0' not in '<!doctype h...'`
  - BUG-2A-09: `…09…py:31: assert 'lucro dos controladores ÷' not in '<!doctype h...'`
  - BUG-2A-10: `…10…py:36: assert 0.0 != 0.0`
  - BUG-2A-11: `…11…py:31: assert -2.0 != -2.0`
  - BUG-2A-12: `…12…py:23: assert None == 0.9 ± 9.0e-07`
  - BUG-2A-13: `…13…py:29: assert 'ticker fora da cobertura da CVM' not in ['ticker fora da cobertura da CVM']`
  - BUG-2A-14: `…14…py:30: assert 180.0 == 190.0 ± 1.9e-04`
  - BUG-2A-15: `…15…py:29: assert 0.4 == 0.06 ± 6.0e-08`
  - BUG-2A-16: `sentinela/data/providers/b3_cotahist.py:97: IndexError: list index out of range`
  - BUG-2A-17: `…17…py:29: assert False` (`MethodResult(... alertas=('desconto sobre o patrimônio',))` para 0,0 e −1,0)
  - BUG-2A-18: `sentinela/methods/graham.py:72: TypeError: must be real number, not complex`
- **Resíduos:** nenhum. Nenhum código de produção alterado; golden e `tests/test_financeiro_pre_refactor.py` inalterados.
- **Decisões que ficaram para o Marcos:** o BUG-2A-01 afirma que P/L e P/VP negativos da CVM também sobrescrevem o anterior (é o sintoma da tabela: os cinco campos); se o F2B-8 decidir outra coisa para os múltiplos, o teste muda por decisão escrita, não por enfraquecimento.
- **Revisão (`/review-diff`, 1ª rodada):** aprovada com médios. Corrigidos antes do commit: a tabela do registro ganhou a coluna "Origem" por bug (auditor e passada, com a data), que o aceite pede; o teste do BUG-2A-11 lê `lpa_divulgado_comparado` com `.get` (a correção pode deixar de gravar a chave); a docstring do BUG-2A-18 diz que o caminho real é a cascata misturar P/VP de uma fonte e VPA de outra. Ficam registrados: o BUG-2A-16 fixa a semântica "mês ausente" (o item da 2B herda essa decisão), e as assertivas finais do 16 e do `vpa` no 12 ainda não rodaram (o teste para antes); o revisor conferiu que os valores esperados batem (`"10/2026"` no fuso da B3; `valor_cota` 100,0). O BUG-2A-07 lê `recomendacao`: o F2C-4 deve listá-lo nos testes que mudam.
- **Para o Marcos revisar:** (1) o BUG-2A-17 contradiz dois casos de `tests/test_methods_fii_nav.py::test_faixa_pelos_limites_estritos_da_v1` (P/VP 0,0 e −1,0 → desconto): o item da 2B que o corrigir precisa listar esse teste. (2) A correção do BUG-2A-07 (F2A-43) grava `classe_ativo` fora do índice, e dois testes existentes afirmam o contrário (`tests/test_market_engine_referencia.py::test_sem_indice_nao_usa_o_mapa_manual` e `::test_ticker_fora_do_indice_sem_motivo`, `"classe_ativo" not in dados`); o F2A-43 não os lista em "Testes que mudam". (3) A seção "Bugs e regressão" entrou no `AGENTS.md` e não no `CLAUDE.md` (o item não pede); o `AGENTS.md` deveria ser subconjunto do `CLAUDE.md`.
