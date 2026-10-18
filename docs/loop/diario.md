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

### F2B-36 — test: register the IF.data audit bugs and point open bugs to their items
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** cinco arquivos novos em `tests/regressao/`, um por bug, todos xfail estrito com `reason="BUG-2A-NN · <sintoma> · corrige: <item>"`:
  - `test_bug_2a_19_ifdata_sem_proveniencia.py` (→ F2B-44): `IFDataProvider.capital` com `requests.get` falso; pede o `.proveniencia.json` lateral de cada arquivo gravado e um `proveniencia` não nulo no `Capital`;
  - `test_bug_2a_20_ifdata_cache_pelo_relogio.py` (→ F2B-44), dois testes: com o cache da data-base mais recente gravado e `time.time` trocado por um que levanta erro, a Basileia sai sem o provedor ler o relógio; com o IF.data respondendo `value: []`, a segunda análise consulta de novo as quatro datas-base (a resposta vazia não ficou no cache);
  - `test_bug_2a_21_roe_sem_piso.py` (→ F2B-18): `guardar_roe(-21.0)` devolve `(None, motivo)`;
  - `test_bug_2a_22_preco_negativo_nos_motores.py` (→ F2B-20), parametrizado nos dois motores: preço −10 devolve `None`;
  - `test_bug_2a_23_divida_em_texto_avaliada.py` (→ F2B-45): dívida "9,5" em texto não leva "Dívida elevada" e ganha o aviso "alavancagem não avaliada" (o texto do aviso é o do F2B-45).
  - `tests/regressao/README.md`: cinco linhas novas (BUG-2A-19 a 23, com evidência arquivo:linha, origem, teste, item e "aberto") e os destinos trocados de "proposta da 2B" para o item: BUG-2A-10 → F2B-37; 11 → F2B-14; 12 → F2B-16; 13 → F2B-17; 14 → F2B-38; 15 → F2B-39; 16 → F2B-40; 17 → F2B-41; 18 → F2B-42. O mesmo destino no `reason` de cada um dos nove testes. A nota "proposta da 2B = item a definir" do cabeçalho do registro passou a dizer que os destinos foram trocados no F2B-36.
- **Dificuldades:** a primeira versão do teste do relógio passou sem a correção: gravei o cache da data-base 202606, mas para 13/10/2026 a primeira tentada é 202609; sem cache dela, o provedor ia direto à rede falsa e não lia o relógio.
- **Como resolvi:** o cache gravado é o de 202609 (cadastro e capital); com `--tb=short`, a falha sai de `sentinela/data/providers/ifdata.py:159` (`time.time()`). O teste não fixa como a correção mede a validade (cache usado ou consultado de novo): só que o relógio não é lido.
- **Testes:** 1362 passed, 1 skipped, 18 xfailed → 1362 passed, 1 skipped, 25 xfailed (+7 casos: 1 + 2 + 1 + 2 + 1). Rito `test`: mutação não se aplica a teste xfail (como no F2A-40); cumprido pela execução com `--runxfail`, em que os cinco bugs se reproduziram (nenhum "não reproduzido"). Linha de falha de cada um (`python -m pytest tests/regressao -q --runxfail --tb=line`):
  - BUG-2A-19: `…19…py:52: assert False` (arquivo gravado sem registro lateral);
  - BUG-2A-20: `…20…py:40: AssertionError: o provedor leu o relógio` (chamado de `ifdata.py:159`); `…20…py:61: assert 4 == (2 * 4)`;
  - BUG-2A-21: `…21…py:20: assert -21.0 is None`;
  - BUG-2A-22: `…22…py:30` nos dois motores (ações: `'Graham: R$12.25, Bazin: R$-5.52'`; FII: `'Bazin FII: R$-8.11'`);
  - BUG-2A-23: `…23…py:30: assert 'Dívida elevada' not in ['Métodos divergentes', 'Dívida elevada']`.
  Os nove testes com destino trocado seguem falhando pelo mesmo sintoma do F2A-40. Nenhum código de produção mudou; golden sem diferença (`git diff --exit-code HEAD -- tests/fixtures/golden_motores.jsonl`); `tests/test_financeiro_pre_refactor.py` sem diferença desde `v2-fase-2a`. `ruff format` nos cinco arquivos novos (um reformatado).
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:**
  - O BUG-2A-20 fixa um sintoma: `time.time` não é chamado. Se o F2B-44 ler o relógio por outra via (`datetime.now`), o teste passa sem a correção completa; o aceite do F2B-44 (instante de referência como parâmetro) é que fecha a regra.
  - O BUG-2A-23 muda um comportamento além do texto inválido: hoje "9,5" vira 9,5 e é penalizado; pela regra do F2B-45, texto não é avaliado (sem penalidade, com aviso). O teste segue essa regra.

### F2B-7 — test: move rate-dependent section A checks to section B
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** [SEÇÃO A] em (c), decisão do Marcos de 18/10/2026. Em `tests/test_financeiro_pre_refactor.py`:
  - **Seção A** (`-m preservar`): os três testes de método da ação ficam com o mesmo nome, parametrizados na taxa que o próprio teste injeta (`TAXAS = (0.06, 0.10, 0.1475, 0.20)`, Selic do `get_selic_atual` falso). Afirmam, para cada taxa: três métodos com valores distintos, preço justo igual ao do meio e diferente da média (`test_a_fair_value_com_tres_metodos_e_a_mediana_nao_a_media`); dois métodos, preço justo igual à média dos dois (`test_a_fair_value_com_dois_metodos_e_a_media_inclusive_com_divergencia`); Bazin ausente com DY 4,9% e presente com 5% (`test_a_bazin_nao_dispara_abaixo_de_5_por_cento`). O teste do FII (`test_a_fii_compara_dy_com_a_selic_liquida_de_ir`) saiu da seção A inteiro: a única coisa que ele afirma é o número pela Selic líquida.
  - **Seção B** (`-m quebra_esperada`), quatro testes novos, cada um com a asserção numérica que saiu da A:
    - 60,00 de preço justo com Graham, Bazin e Gordon (Selic 10%) → `test_b_mediana_de_tres_metodos_pela_selic`, marcas F-4 e F-5 (a mediana é o Bazin, e o Gordon passa a mediana se subir acima de 60);
    - 105,00 com Graham e Bazin, e o risco "Métodos divergentes" (150 ÷ 60 > 2) → `test_b_media_de_dois_metodos_pela_selic`, marca F-5;
    - Bazin de 50,00 no limite de 5% → `test_b_bazin_no_limite_de_5_por_cento_pela_selic`, marca F-5;
    - FII com preço justo 110,00 e upside 10% pela Selic líquida → `test_b_fii_compara_dy_com_a_selic_liquida_de_ir`, marca F-9.
  - `pytest.ini`: marca `f5_bazin_selic` registrada (o `--strict-markers` a exige).
- **Dificuldades:** as propriedades da A precisavam valer para qualquer taxa; com Selic abaixo de 5%, o piso do Bazin tornaria os valores iguais aos de 5%.
- **Como resolvi:** antes de escrever, conferi os valores nas quatro taxas (6%: Graham 150, Bazin 100, Gordon 76,68; 10%: 150, 60, 51,54; 14,75%: 150, 40,68, 37,10; 20%: 150, 30, 28,32): três valores distintos e mediana longe da média em todas. A asserção do risco "Métodos divergentes" saiu da A porque depende da taxa (com Selic 6%, 150 ÷ 100 < 2).
- **Testes:** 1362 passed, 1 skipped, 25 xfailed → 1374 passed, 1 skipped, 25 xfailed (+12: a seção A passou de 4 testes a 3 × 4 taxas = 12 casos, +8; a seção B ganhou 4). `python -m pytest -m preservar`: 12 passed; `-m quebra_esperada`: 11 passed. Nenhuma asserção enfraquecida: as seis asserções numéricas (60; 105 e a flag; 50; 110 e 10%) estão na B com o mesmo valor e a mesma tolerância. `git diff v2-fase-2a -- tests/test_financeiro_pre_refactor.py` mostra só esta mudança de seção. Nenhum código de produção mudou; golden sem diferença.
- **Mutação** (`python -m mutmut run "valuation_engine*" "fii_engine*"`), antes → depois: `valuation_engine` 645/718 (89,8%) → 645/718 (89,8%); `fii_engine` 247/274 (90,1%) → 247/274 (90,1%). Sem queda.
- **Resíduos:** nenhum no repositório. Antes da primeira rodada da mutação apaguei o diretório `mutants/` (ignorado pelo git, gerado pelo mutmut) para a base sair limpa; a regra do loop manda nunca apagar arquivo não rastreado, e esse diretório não deveria ter sido apagado sem estar na lista do Marcos. Não havia nada nele que não seja regenerado pelo mutmut.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** a docstring do módulo ainda diz "Na Fase 2 só a B muda"; ficou como estava, porque o aceite pede o diff só com a mudança de seção. Marcas na seção B: F-4 em `test_b_mediana_de_tres_metodos_pela_selic` (além dos dois do F-4 que já existiam); F-5 nos três testes novos de ação; F-9 no novo do FII (além do `test_b_fii_nao_considera_o_patrimonio_no_fair_value`). A mediana de três tem duas marcas.
- **Revisão:** 1ª rodada aprovada com médios. Corrigido antes do commit: o comentário de `test_b_mediana_de_tres_metodos_pela_selic` passou a citar o checkpoint da Fase 0, seção 4, item 2 (o teste do FII já citava o item 3). Ficam registrados para o F2B-1: os testes da seção A injetam só a Selic (`valuation_engine.get_selic_atual`); quando o Gordon ler a taxa real por outra via, o F2B-1 precisa injetá-la neles também, senão o Gordon se abstém (ou tenta rede) e um teste `preservar` quebra pela correção. O nome `test_a_fair_value_com_dois_metodos_e_a_media_inclusive_com_divergencia` ficou, embora a flag de divergência tenha ido para a B (o aceite pede só a mudança de seção). A remoção do `mutants/` (acima, em "Resíduos") é desvio de processo, declarado.
