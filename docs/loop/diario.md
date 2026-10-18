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

### F2B-8 — fix: keep non-positive CVM figures over stale positive values
- **Executor:** claude-code (claude-opus-5-5); começado e retomado na mesma sessão, depois de uma pausa por limite de uso (passagem em `outputs/passagem.md`).
- **Status:** sucesso
- **O que foi feito:** [AUDITORIA] em (a), decisão do Marcos de 18/10/2026. Em `market_engine._is_field_missing`, nos campos `pl`, `pvp`, `roe`, `lpa` e `vpa`, ausente passou a ser só `None` ou não finito (o `is_missing` do início da função). O valor ≤ 0 deixou de ser ausente: o merge com `overwrite` da CVM grava o prejuízo e o PL negativo sobre o yfinance e a brapi, o cache não é consultado por eles, e eles não contam em `list_missing_required_fields`. Ficou a regra do `pl_confiavel is False` (P/L que o yfinance marcou como não confiável, negativo ou acima de 80), que é de confiabilidade da fonte, não do sinal do número.
- **Testes novos:** `tests/test_market_engine_valores_negativos.py`, com cascata falsa (yfinance com `trailingPE` 8, ROE 10% e DY; CVM com lucro dos controladores −2.000 e LPA divulgado −2,1):
  - `test_prejuizo_da_cvm_nao_e_trocado_por_valor_positivo` (LPA −2,0, P/L −10, ROE −0,2);
  - `test_cache_nao_repoe_valor_que_a_cvm_entregou` (cache com valores positivos não entra);
  - `test_lpa_cvm_e_valor_final_concordam` (`lpa_cvm` e `valores_por_fonte['CVM']` iguais ao valor final);
  - `test_prejuizo_nao_conta_como_campo_faltando` (sem P/L e ROE no yfinance: `fundamentos_incompletos` False e `campos_faltantes` vazio; P/L, P/VP e ROE negativos fora de `list_missing_required_fields`).
  Os quatro entraram com xfail estrito e falharam com `--runxfail` pelo sintoma (`KeyError: 'lpa'`, `assert 8.0 == -10.0`, `KeyError: 'lpa'`, `assert True is False`); depois da correção deram XPASS(strict), e a marca saiu. O BUG-2A-01 (`tests/regressao/test_bug_2a_01_cvm_nao_positivo_descartado.py`, três testes, sete casos) teve a marca retirada e está em PASS; o registro diz "corrigido".
- **Testes que mudaram** (fixavam ≤ 0 como ausente; o item manda o primeiro e lista os demais aqui), em `tests/test_market_engine.py`:
  - `test_quality_helpers_respect_zero_dy_but_not_zero_price`: P/L e ROE zero deixaram de ser faltantes (`== []`); a parte do preço zero passou a ser conferida em `list_missing_market_fields` (`["preco_atual", "historico"]`), importado no teste;
  - `test_brapi_does_not_overwrite_valid_fields_with_missing_values`: o dublê da brapi mandava `pvp: 0` e `roe: 0` como "ausentes"; passou a mandar `None` e `nan` (o teste continua provando que ausente não sobrescreve). O provedor real da brapi já descarta P/L, P/VP, LPA e VPA ≤ 0 na fronteira (`brapi_provider._positive_float`), então os zeros só existiam no dublê;
  - `test_merge_if_valid_only_fills_missing_fields`: a base trazia `pvp: 0` como ausente; passou a `None`.
- **Medição** (`outputs/f2b8_candidatos.py` e `outputs/f2b8_cascata.py`, fora do git; DFP 2025 local; cascata real com rede só de leitura, sem cache SQLite e sem liquidez). Das 38 ações atuais do universo inicial, cinco têm prejuízo na DFP 2025 (nenhuma tem PL negativo). Antes → depois:

  | Ticker | P/L | LPA | ROE | VPA | `fundamentos_incompletos` |
  |---|---|---|---|---|---|
  | CSAN3 | — → −1,26 | — → −3,89 | −0,272 (yfinance) → −1,833 (CVM) | 1,34 → 1,34 | True → False |
  | HAPV3 | — → −29,61 | — → −0,28 | −0,0036 (yfinance) → −0,0029 (CVM) | 101,63 → 101,63 | True → False |
  | LWSA3 | — → −12,68 | — → −0,41 | −0,078 (yfinance) → −0,091 (CVM) | 4,48 → 4,48 | True → False |
  | MRVE3 | — → −3,90 | — → −1,85 | −0,100 (yfinance) → −0,196 (CVM) | 9,47 → 9,47 | True → False |
  | USIM5 | — → — | — → — | −0,081 (yfinance) → −0,148 (CVM) | 16,91 → 16,91 | True → True |

  Antes, o ROE negativo da CVM era descartado e ficava o do yfinance, também negativo, mas de outro período e sem a regra dos controladores. A USIM5 segue sem P/L e LPA porque o LPA da CVM se abstém (linha "PN" única com classes PNA e PNB; regra 3, ponto (c) da ficha 1.1, F2B-12), e o P/L negativo do yfinance é descartado com `pl_confiavel` False; por isso segue com `fundamentos_incompletos`.
- **Dificuldades:** a primeira versão de `test_prejuizo_nao_conta_como_campo_faltando` passava sem a correção na primeira asserção: o yfinance falso preenchia P/L e ROE positivos.
- **Como resolvi:** o teste usa uma cascata em que o yfinance só traz o DY, e P/L e ROE vêm só da CVM.
- **Testes:** 1374 passed, 1 skipped, 25 xfailed → 1385 passed, 1 skipped, 18 xfailed (+4 novos; os sete casos do BUG-2A-01 passaram de xfailed a passed). Golden sem diferença (`git diff --exit-code HEAD -- tests/fixtures/golden_motores.jsonl`); `tests/test_financeiro_pre_refactor.py` sem mudança neste item. `ruff format` nos dois arquivos de teste novos ou reescritos; o import de `tests/test_market_engine.py` reordenado pelo ruff (I001).
- **Mutação** (módulo V1 tocado, sem meta): `market_engine` 1.487/2.099 (70,8%); no fim da 2A, 1.472/2.093 (70,3%). Em `_is_field_missing`, 33 mortos e 15 sobreviventes.
- **Resíduos:** nenhum no repositório. `outputs/f2b8_*.py` e `.json` ficam fora do git.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:**
  - A brapi real deixa passar ROE zero (`roe_na_fronteira` não descarta zero). Com a correção, um ROE zero da brapi passa a sobrescrever o do yfinance; antes era tratado como ausente.
  - A regra do `pl_confiavel is False` ficou de propósito: ela não depende do sinal do número, e a decisão (a) trata de ≤ 0.
  - O motor de ações recebe agora LPA e P/L negativos; cada método se abstém pela própria regra (golden inalterado, porque a mudança é da cascata).
  - O motor de ações ainda soma "Dados incompletos" e −10 de confiança quando `pl <= 0 or pvp <= 0` (`valuation_engine.py:269-271`). Com o P/L negativo da CVM chegando ao motor, a empresa com prejuízo continua com esse risco, o que contradiz "prejuízo é dado". O ajuste muda o golden e é do motor, fora deste item; candidato ao F2C-3 (insumo ausente que o motor converte em 0 e penaliza).
  - A média de P/L dos pares (`peers_engine.py:86-93`, "P/L médio peers" na tela) passa a receber P/L negativo da CVM, e média aritmética com P/L negativo não tem sentido econômico. `peers_engine.py` é arquivo do ticket C-C do Jules; fica para a 2C.
  - Zero em `pl` e `pvp` passou a contar como dado, mas com preço > 0 não pode ser real (é marcador de ausência). A brapi o barra na fronteira; o `priceToBook` do yfinance entra sem filtro, e um zero dele agora impede a consulta ao cache. É a decisão literal ("só None ou não finito"); se o Marcos quiser, o zero de P/L e P/VP volta a ser ausente na fronteira do provedor, num item à parte.

### F2B-10 — fix: infer share scale from consolidated earnings when controlling earnings abstain
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** ficha por ação 1.1, decisão 7.7 (ficha aprovada em 18/10/2026).
  - `sentinela/data/acoes_cvm.py`: `confirmar_escala` (Q_CVM, as ações em circulação da Composição do Capital na escala escolhida, ÷ ações por unit na unit; Q_yf, a `sharesOutstanding`; confirmada só com `0,1 < Q_CVM ÷ Q_yf < 10`, desigualdades estritas, e não confirmada com Q_yf ausente, ≤ 0 ou não finito), `FAIXA_DA_CONFIRMACAO`, `NOTA_ESCALA_PELO_CONSOLIDADO` (o texto da ficha) e `MOTIVO_ESCALA_NAO_CONFIRMADA`. `derivar_por_acao` ganhou `lucro_consolidado` e `shares_outstanding`, opcionais: com o lucro dos controladores `None` e o consolidado informado, a escala sai de `inferir_escala` pelo consolidado (mesma faixa [0,1; 10] da 7.1, contra o LPA divulgado coerente pela 7.6) e só vale confirmada; sem confirmação, abstém-se com o motivo e o registro da consulta. O LPA recalculado continua `None` (sem lucro dos controladores), e o consolidado não entra no LPA nem no ROE. `PorAcao` e `Abstencao` ganharam o campo `escala_pelo_consolidado` (o registro da consulta).
  - `market_engine._por_acao_cvm` passa o lucro consolidado (`lucro_liquido`) e a `_shares_outstanding` do yfinance, e grava o registro em `dados['escala_pelo_consolidado']`, inclusive quando a confirmação falha (D16). Na proveniência do VPA da CVM, a chave `escala` traz o mesmo registro.
  - `sentinela/data/series_cvm.py` não mudou: não passa o consolidado nem o yfinance, e a série de cinco anos segue com a escala indeterminada nesses casos (D17).
  - `ai_core.py`: `escala_pelo_consolidado` na lista `excluir` de `_formatar_dados` (bloco estruturado novo em `dados`).
- **Testes novos** (os seis do aceite em `tests/test_market_engine_acoes_cvm.py`, com xfail estrito, falharam com `--runxfail` e deram XPASS(strict) com a correção; a marca saiu):
  - `test_escala_pelo_consolidado_quando_controladores_se_abstem` (VPA 10, P/VP 2, escala UNIDADE, razão 2.500 ÷ 1.000 ÷ 2,1);
  - `test_consolidado_nao_entra_no_lpa_nem_no_roe` (ticker ON do índice falso: recalculado `None`, LPA = divulgado 2,1, ROE ausente);
  - `test_escala_pelo_consolidado_na_proveniencia` (nota, Q_CVM 1.000, Q_yf 400, razão 2,5, confirmada; o mesmo registro na proveniência do VPA e em `dados`);
  - `test_escala_pelo_consolidado_exige_a_confirmacao_do_yfinance`, parametrizado nos casos sintéticos da ficha (5.3): razão 1,0226 aceita; 1.000, 0,1, 10 e 0,0999 recusam;
  - `test_sem_yfinance_a_abstencao_continua`, com `sharesOutstanding` `None`, 0 e −1 (sem VPA, registro não confirmado com razão `None`, motivo em `riscos_dados`);
  - `test_exemplo_da_ficha_klbn11` (D28): 6.135.427.665 ações, razão 1,1965352, VPA da unit 6,4265659 (tolerância 1e−6), LPA recalculado `None`.
  - `tests/test_cvm_series.py::test_serie_nao_usa_a_confirmacao_do_yfinance`: sem xfail, porque já passa e deve continuar passando (a série não tem a `sharesOutstanding`): com o lucro dos controladores `None`, ações e VPA ausentes, motivo `MOTIVO_ESCALA`.
- **Dificuldades:** duas montagens erradas na primeira versão. Sem espécie no índice falso, o LPA dos métodos é o recalculado, que se abstém, e o teste esperava o divulgado; e a proveniência do VPA só é gravada quando o `ind` traz `proveniencia`, que o `_ind` dos testes não traz.
- **Como resolvi:** o teste do LPA usa um ticker ON do índice falso (`FakeReferencia`), e o da proveniência passa um `proveniencia` no `ind`. Como os dois mudaram depois da correção, rodei os testes novos contra o código do `HEAD` numa worktree destacada no scratchpad (removida depois): os 12 casos falham lá (`KeyError: 'vpa'`, `KeyError: 'acoes_cvm'`, `AttributeError` de `confirmar_escala`, `KeyError: 'escala_pelo_consolidado'`, `TypeError` de `lucro_consolidado`).
- **Medição** (`outputs/f2b10_cascata.py`, fora do git; DFP 2025 local; cascata real com rede só de leitura, sem cache SQLite; "antes" com o código do `HEAD` numa worktree). As nove companhias da 7.7:

  | Companhia | Ticker | Razão (consolidado) | Q_CVM ÷ Q_yf | Confirmação | Escala | VPA antes → depois |
  |---|---|---|---|---|---|---|
  | Klabin | KLBN11 | 1,1965352 | 1.227.085.533 ÷ 1.214.936.096 = 1,0100 | sim | UNIDADE | — → 6,4265659 (P/VP 2,35 do yfinance → 2,82 da CVM) |
  | Cambuci | CAMB3 | 0,9999981 | 41.839.573 ÷ 41.830.573 = 1,0002 | sim | UNIDADE | — → 7,3033 (P/VP 1,14 → 1,19) |
  | Mundial | MNDL3 | 0,9999999 | 9.917.976 ÷ 9.917.976 = 1,0000 | sim | UNIDADE | — → 13,5594 (P/VP 1,64 → 1,32) |
  | Sul 116 | OPTS3 | 0,532 (ficha) | — | sem yfinance | — | — → — (o yfinance não tem preço; a cascata para antes da CVM) |
  | Lifemed, Cantu e VLI | sem ticker no índice | 0,162; 0,972; 2,067 (ficha) | — | — | — | sem cotação, não passam pela cascata |
  | Aliperti | APTI3, APTI4 | — | — | — | — | — → — (sem preço no yfinance; e, pela ficha, linhas ON e PN zeradas) |
  | Cataguases | sem ticker no índice | — | — | — | — | sem LPA por espécie (ficha); fica em abstenção |

  Os três casos confirmados ficam com razão perto de 1, longe dos limites; nenhum caso medido foi recusado pela confirmação.
- **Testes:** 1385 passed, 1 skipped, 18 xfailed → 1409 passed, 1 skipped, 18 xfailed (+24: os 6 do aceite, com 5 e 3 casos nos parametrizados, o da série e os 6 de unidade, dois deles parametrizados com 5 e 2 casos). Golden sem diferença; `tests/test_financeiro_pre_refactor.py` sem mudança. `ruff format` em `sentinela/data/acoes_cvm.py` e nos três arquivos de teste; `ruff check sentinela/data/` verde.
- **Mutação** (`python -m mutmut run "sentinela.data.acoes_cvm*"`, meta ≥ 80%): 344/371 (92,7%) na primeira rodada, com seis sobreviventes em `confirmar_escala` e três na passagem do consolidado em `derivar_por_acao`; com cinco testes de unidade novos em `tests/test_acoes_cvm.py` (divisão pelas ações por unit só na unit, Q_yf ausente, zero, negativo e não finito, Q_yf fracionário positivo, motivo da escala quando o consolidado não a infere, unit confirmada pelas units), 353/371 (95,1%). Seguem quatro sobreviventes em `derivar_por_acao` (8, 10, 86 e 87).
- **Resíduos:** nenhum no repositório; `outputs/f2b10_*` fora do git.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:**
  - Na KLBN11, o yfinance conta as units (1.214.936.096), e a CVM, ÷ 5 ações por unit, dá 1.227.085.533: a hipótese da ficha (os dois medem a mesma coisa) vale aqui.
  - Quando a confirmação vale, o P/VP da CVM passa a sobrescrever o do yfinance (KLBN11 2,35 → 2,82), pela ordem da cascata (CVM > yfinance).
  - O `market_engine.py` ficou com as mudanças deste item fora do stage enquanto o F2B-8 era commitado (`44d0666`): o commit do F2B-8 levou só o stage revisado dele.
- **Revisão:** 1ª rodada aprovada com médios. Corrigido antes do commit: o registro da consulta gravava a nota da ficha ("… e confirmada pela quantidade do yfinance") também quando a confirmação falhava; agora a nota é a da ficha só com a escala confirmada, e, sem confirmação, o `MOTIVO_ESCALA_NAO_CONFIRMADA` (dois asserts novos em `tests/test_acoes_cvm.py`). Ficam registrados:
  - `dados['acoes_cvm']['razao_lpa_calculado_sobre_divulgado']`, nesses casos, é a razão pelo lucro consolidado; a origem está no registro ao lado (`dados['escala_pelo_consolidado']` e `proveniencia['vpa']['escala']`), não no `acoes_cvm`;
  - o registro guarda Q_yf só com o valor; a fonte e a data da `sharesOutstanding` são as do yfinance na proveniência da cascata (seção 2 da ficha), sem cópia no registro;
  - na cascata, `sharesOutstanding` 0 e −1 já chegam como `None` (`market_engine.py` só grava `_shares_outstanding` positivo); o caminho ≤ 0 da função é coberto pelos testes de unidade.
- **Revisão, 2ª rodada:** reprovada porque o stage tinha a versão de `tests/test_acoes_cvm.py` com o import fora de ordem (I001); o arquivo corrigido no disco não tinha ido para o stage. Corrigido e refeito o stage; `ruff check` passou a rodar também nos arquivos de teste do item e no `market_engine.py` (os três erros que restam em `tests/test_acoes_cvm.py` são do `HEAD`, sem correção segura). Também nesta rodada: o teste dos limites ganhou um caso com razões 0,1 e 10 exatas (`test_confirmacao_recusa_os_limites_exatos`), porque o caso da ficha com `6.135.427.665 ÷ 0,1` depende do arredondamento. Ficam registrados:
  - nesses casos, a `divergencia_acoes` compara com a mesma `sharesOutstanding` que confirmou a escala, então não é conferência independente (mesma família da armadilha 2);
  - a proveniência do VPA recebe a chave `escala` pela existência do registro, não pela confirmação; hoje é equivalente (sem confirmação, o VPA da CVM não é gravado), mas depende da ordem da cascata.

### F2B-11 — fix: read the aggregate EPS line as the EPS of a single-class company
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** ficha por ação 1.1, decisão 7.8 (ficha aprovada em 18/10/2026).
  - `cvm_provider.lpa_basico_agregado`: os valores das linhas agregadas 3.99.01 e 3.99 da DRE consolidada (sem a escala monetária, como as demais 3.99), com zero e não numérico como `None`; vai para o `ind` como `lpa_basico_agregado`.
  - `sentinela/data/acoes_cvm.linhas_da_especie_unica` (função pura): sem linha de LPA por espécie na DRE e com uma só espécie da companhia no FCA, a 3.99.01 vira a linha dessa espécie; zerada ou ausente, vale a 3.99, só se o recalculado (lucro dos controladores ÷ ações, na escala que a própria 3.99 escolhe pela faixa da 7.1) ficar a até 10% dela (`LIMIAR_DA_LINHA_399`, o limiar da 7.3). Devolve as linhas e o registro da linha usada (conta, espécie, razão no caso da 3.99, e a nota `NOTA_LINHA_AGREGADA`, o texto da ficha). Mais de uma espécie, linha por espécie existente ou nenhuma linha agregada: nada muda. A coerência (7.5 e 7.6) continua em `divulgados_coerentes`, sobre as linhas que essa função devolve, e a linha usada serve à escala.
  - `market_engine`: `_aplicar_referencia` grava `dados['especies_da_companhia']` (as espécies dos registros do índice com o mesmo CNPJ; para unit, as espécies da composição). `_por_acao_cvm` passa as linhas por `linhas_da_especie_unica` antes da coerência e, quando o LPA dos métodos é o divulgado vindo da linha agregada, acrescenta ao `lpa_cvm` o registro (`linha_agregada`) e a nota (proveniência do LPA, D16).
  - `ai_core.py`: `especies_da_companhia` na lista `excluir`.
  - A série de cinco anos (`series_cvm`) não mudou: o item fala só da cascata.
- **Testes:**
  - Com xfail estrito → XPASS(strict) → marca retirada: `tests/test_market_engine_acoes_cvm.py::test_linha_agregada_vale_para_companhia_de_especie_unica` (3.99.01 = 2,0 numa companhia ON: LPA 2,0 de origem "divulgado", registro da 3.99.01, nota, VPA 10) e os três casos de `::test_linha_399_vale_so_com_o_recalculado_a_ate_10_por_cento` em que a 3.99 vale (2,0, 2,2 e 1,82: razões 1, 0,909 e 1,099); `::test_exemplo_da_ficha_bbas3` (D28: 3.99.01 = 0, 3.99 = 2,40, recalculado 13.698.124.000 ÷ (5.730.834.040 − 22.370.399); razão 0,9998402 com tolerância 1e−6).
  - Sem marca, porque já passam e devem continuar passando: `::test_linha_agregada_nao_vale_com_mais_de_uma_especie` (o Pine: duas espécies, abstenção) e os dois casos do parametrizado em que a 3.99 é recusada (1,8 e 2,3: razões 1,111 e 0,870).
  - `::test_provedor_le_as_linhas_agregadas_sem_zeros` (leitura do provedor, com 3.99.01 zerada e documento vazio) e quatro testes de unidade em `tests/test_acoes_cvm.py` (linha por espécie dispensa a agregada; sem linha agregada nada muda; o registro com conta e espécie nas duas linhas; 3.99 sem lucro dos controladores não entra).
- **Dificuldades:** a primeira contagem das companhias deu 3.99 = 2.400 no BBAS3: o script lia a DRE por `parsear_demonstrativo`, que aplica a escala monetária (MIL) também às linhas por ação.
- **Como resolvi:** o script lê a DRE como o provedor lê as 3.99 (`_read_raw`, ordem "ÚLTIMO", sem a escala monetária).
- **Medição** (`outputs/f2b11_contagem.py` e `outputs/f2b11_cascata.py`, fora do git; DFP 2025 local; cascata real com rede só de leitura, sem cache SQLite; "antes" com o código do `HEAD` numa worktree):
  - Companhias da DFP 2025 (última versão de cada CNPJ) só com a linha agregada (sem linha 3.99.01.xx por espécie e com 3.99.01 ou 3.99 diferente de zero): **duas**. Uma espécie: 1, pela 3.99 (Banco do Brasil, razão 0,9998); duas espécies: 1, nenhuma linha usada (Pine). Nenhuma pela 3.99.01.
  - Antes → depois:

    | Ticker | LPA | VPA | P/VP |
    |---|---|---|---|
    | BBAS3 | — → 2,40 (linha 3.99, razão 0,9998) | — → 33,1451 | 0,7413 (yfinance) → 0,7129 (CVM) |
    | PINE3 | — → — | — → — | 1,9128 (yfinance) → 1,9128 |
    | PINE4 | — → — | — → — | 2,2304 (yfinance) → 2,2304 |

    O Pine segue com "escala das ações indeterminada".
- **Testes:** 1409 passed, 1 skipped, 18 xfailed → 1422 passed, 1 skipped, 18 xfailed (+13: 9 em `tests/test_market_engine_acoes_cvm.py`, um deles com 5 casos, e 4 em `tests/test_acoes_cvm.py`). Golden sem diferença; `tests/test_financeiro_pre_refactor.py` sem mudança. `ruff format` em `sentinela/data/acoes_cvm.py` e nos dois arquivos de teste; nos arquivos da raiz (`cvm_provider.py`, `market_engine.py`, `ai_core.py`), o `ruff check` dá a mesma contagem do `HEAD` (8, 11 e 7), sem erro novo.
- **Mutação** (`sentinela.data.acoes_cvm*`, meta ≥ 80%): 394/419 (94,0%) na primeira rodada, com sete sobreviventes em `linhas_da_especie_unica`; com os quatro testes de unidade, 400/419 (95,5%). Sobra um em `linhas_da_especie_unica` (`>` → `>=` no limiar de 10%), equivalente na prática: em ponto flutuante, nenhuma razão dá desvio de exatamente 0,10 (1,1 − 1 = 0,10000000000000009).
- **Resíduos:** nenhum no repositório; `outputs/f2b11_*` fora do git.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:**
  - O BBAS3 passa a ter LPA, VPA e P/VP da CVM, e o P/VP da CVM sobrescreve o do yfinance pela ordem da cascata; o VPA vem do PL dos controladores pelo modelo de banco (F2A-9).
  - "Espécies no FCA" é lido pelo índice oficial (registros do mesmo CNPJ), que só traz os papéis ativos com código de negociação; uma espécie sem código no FCA não conta.

### F2B-12 — fix: apply one preferred-class rule to units and standalone shares
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** ficha por ação 1.1, decisão 7.9, opção (i) (ficha aprovada em 18/10/2026).
  - `sentinela/data/acoes_cvm._lpa_da_classe`: com mais de uma classe preferencial no FCA e sem a linha da classe na DRE, a linha básica "PN" única é atribuída à classe como LPA divulgado, com a marca `nota_linha_pn_unica(classe)` ("LPA da linha PN única, aplicado à classe <classe>"); a linha "PN" incoerente (7.5) leva a classe à abstenção; a linha da própria classe, coerente ou não, continua tendo precedência; o recalculado comum segue proibido para essas classes (regra 3). `especie_da_classe` (PN, PNA, PNB… → PN) passou a dar a espécie do componente da unit, que antes era a própria chave: a ação avulsa e o componente seguem a mesma ordem (a linha da classe e, sem ela, a "PN" única).
  - `sentinela/data/referencia/montagem._especie_do_texto`: a composição da unit guarda a sigla da classe ("1 ON E 2 PNA" → `{"ON": 1, "PNA": 2}`), por `^PN([A-H])$`; "PN", "PNS" e os textos por extenso seguem como "PN".
  - `market_engine._aplicar_referencia`: as espécies da companhia (F2B-11) passam a normalizar as chaves da composição da unit por `especie_da_classe`, para "PNA" não contar como espécie à parte.
  - O índice salvo em `data/referencia/` só ganha as siglas na próxima montagem; até lá, as units seguem com "PN" na composição, e a linha "PN" vale para elas diretamente, sem a marca.
- **Testes:**
  - Com xfail estrito → marca retirada → PASS: `tests/test_market_engine_acoes_cvm.py::test_linha_pn_unica_com_classes_distintas` (ação avulsa PNA, como a USIM5, e unit `{"ON": 1, "PNA": 2}` no mesmo teste: LPA 2,3 com a marca na avulsa; 2,1 + 2 × 2,3 na unit, com a marca no componente PNA) e `::test_unit_com_componente_pna_usa_a_linha_da_classe` (o parser guarda "PNA"; a unit usa a linha PNA, sem marca). A primeira versão dos dois falhava por `TypeError` na montagem (o `_unit` dos testes já fixa a composição); corrigida a montagem com um `_unit_com`, conferi numa worktree do `HEAD` que os dois falham pelo sintoma (`KeyError: 'lpa'` e `{'ON': 1, 'PN': 2} == {'ON': 1, 'PNA': 2}`) e, com a correção, deram XPASS(strict).
  - **Teste que mudou:** `tests/test_referencia.py::test_parser_de_acoes_por_unit`, o caso `"1 ON E 2 PNA"`, de `{"ON": 1, "PN": 2}` para `{"ON": 1, "PNA": 2}`: é a mudança que a decisão 7.9 pede ("a composição da unit guarda a sigla da classe").
  - `test_pna_e_pnb_nao_usam_lpa_comum` e `test_unit_com_componente_sem_reserva_abstem` seguem verdes sem mudança: sem linha "PN" na DRE, a PNB e o componente PN continuam em abstenção.
- **Medição** (`outputs/f2b12_contagem.py` e `outputs/f2b12_cascata.py`, fora do git; DFP 2025 local; cascata real com rede só de leitura, sem cache SQLite; "antes" com o código do `HEAD` numa worktree):
  - Companhias da DFP 2025 com mais de uma classe preferencial no FCA (índice oficial): nove (CEB, MRS, Sansuy, Sondotécnica, Unipar, Braskem, Suzano Holding, Usiminas e Banrisul). Com uma só linha "PN" na DRE: **uma**, a Usiminas. A CEB não traz linha preferencial na DRE, e a Sondotécnica traz PNA e PNE (FCA: PNA e PNB); as duas seguem sem mudança.
  - Antes → depois:

    | Ticker | LPA | Origem |
    |---|---|---|
    | USIM5 (PNA) | — → −2,50 | linha "PN" única, aplicada à classe PNA (ficha, 5.3: −2,50) |
    | USIM6 (PNB) | — → −2,50 | linha "PN" única, aplicada à classe PNB |
    | USIM3 (ON) | −2,50 → −2,50 | divulgado ON, sem mudança |

    VPA (16,91) e P/VP não mudam. O "CVM sem LPA: mais de uma classe preferencial…" saiu dos riscos da USIM5 e da USIM6.
- **Testes:** 1422 passed, 1 skipped, 18 xfailed → 1430 passed, 1 skipped, 18 xfailed (+8: 2 da cascata, 5 de unidade e 1 caso no parser). Golden sem diferença; `tests/test_financeiro_pre_refactor.py` sem mudança. `ruff format` nos módulos de `sentinela/data/` alterados e no arquivo de teste; `ruff check sentinela/data/` verde.
- **Mutação** (meta ≥ 80% nos módulos de `sentinela/data/` alterados): primeira rodada, `sentinela.data.acoes_cvm` 419/452 (92,7%) e `sentinela.data.referencia.montagem` 625/677 (92,3%), com 16 sobreviventes no código novo (`especie_da_classe` e o desvio da linha "PN" em `_lpa_da_classe`) e um no parser. Com cinco testes de unidade em `tests/test_acoes_cvm.py` (espécie da classe; a linha "PN" com a marca, com e sem a nota do sinal; linha "PN" incoerente ou ausente e a precedência da linha da classe; a chave "PN" de índice antigo; o componente PNA da unit com várias e com uma classe preferencial) e um caso no parser ("1 ON + 2 PNA + 1 PNA" soma na mesma classe), e sem a condição `classe != "PN"`, que era redundante (a chave "PN" já é achada no laço da classe): `acoes_cvm` 432/448 (96,4%), `montagem` 626/677 (92,5%). O sobrevivente que resta em `_lpa_da_classe` é do código anterior (`classe or especie` no recalculado).
- **Resíduos:** nenhum no repositório; `outputs/f2b12_*` fora do git.
- **Decisões que ficaram para o Marcos:** nenhuma deste item. Duas ressalvas da revisão do F2B-11, registradas aqui porque o commit dele saiu como revisado:
  - "sem linha de LPA por espécie" é lido como "sem linha por espécie diferente de zero": `cvm_provider.lpa_basico_por_classe` descarta os zeros, então uma companhia de espécie única com a 3.99.01.01 ON zerada e a 3.99.01 diferente de zero recebe a 3.99.01, sem a conferência pelo recalculado. Nenhum caso na DFP 2025 (os dois só com linha agregada são o Banco do Brasil e o Pine), mas a ficha fala em linha ausente; separar "ausente" de "zerada" muda a regra e precisa da decisão;
  - a espécie única vem do índice (papéis com código de negociação), sem conferência pela Composição do Capital do mesmo documento; uma salvaguarda possível é recusar a linha agregada quando a Composição traz ações da outra espécie, o que também é regra nova.
- **Para o Marcos revisar:** com a marca, a USIM5 e a USIM6 recebem o mesmo LPA, embora o CPC 41 peça o número por classe quando os direitos diferem; a ficha (7.9) declara isso como aproximação.

### F2B-13 — fix: correct share species through the source corrections table
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** ficha por ação 1.1, decisão 7.10 (ficha aprovada em 18/10/2026), com a regra [CORREÇÕES] de 5/10/2026.
  - `sentinela/data/referencia/correcoes.py`: `Correcao` ganhou `campo` e `valor`, opcionais (a tabela antiga, sem as duas colunas, segue válida, e `para_dict` só as traz na correção de campo). `_validar_campo`: campo conhecido (`CAMPOS_CORRIGIVEIS`, hoje só `especie`, com ON ou PN), valor permitido e, na espécie, as duas evidências do mesmo documento citadas em `arquivo` (Composição do Capital e DRE); com uma só, `CorrecaoInvalida`. Continua caso a caso: só vale a linha da tabela, para o (CNPJ, código) dela.
  - `sentinela/data/referencia/montagem.montar_companhias`: com a correção de espécie, o código fica, e a espécie do registro é a da tabela; corrigida para ON, a classe preferencial do registro sai.
  - `sentinela/reports/rastreabilidade._texto_referencia`: a correção de espécie aparece no relatório do F1-12 como "espécie da tabela de correções, não do arquivo da fonte: ON para MGLU3 (evidência: …)"; a de código segue como antes.
  - `sentinela/data/referencia/correcoes.csv`: colunas `campo` e `valor` (vazias nas linhas da CSN e do TRXF11) e a linha da MGLU3, com a evidência conferida nos arquivos locais: FCA 2025 e 2026, versão 1 (`Valor_Mobiliario` "Ações Preferenciais", `Sigla_Classe_Acao_Preferencial` PNA); DFP 2025, versão 1, `DT_REFER` 2025-12-31: Composição do Capital com 775.945.010 ON, 0 PN e 1.343.449 ON em tesouraria; DRE com 3.99.01.01 "ON" = 0,264, e 3.99 e 3.99.01 zeradas.
  - **Intervalo de validade:** a linha traz a data da evidência (`data`, 2025-12-31) e cita os documentos (FCA 2025 e 2026, DFP 2025); a tabela não tem coluna de fim, e a correção vale para o índice montado a partir desses FCAs. A ficha diz que ela não se estende sozinha a outros documentos: um FCA novo, com outra versão, só herda a correção se a linha for revista.
- **Testes** (em `tests/test_referencia_correcoes.py`, os três do aceite com xfail estrito → falharam com `--runxfail` pela falta do campo (`TypeError` no `Correcao` e `KeyError: 'campo'`) → XPASS(strict) → marca retirada):
  - `test_correcao_de_especie_com_evidencia` (FCA preferencial PNA com a correção → ON, sem classe preferencial, regra "correcao"; sem a correção, PN e PNA);
  - `test_correcao_de_especie_sem_evidencia_e_rejeitada`, parametrizado com só a Composição e só a DRE (e, no mesmo teste, campo e valor desconhecidos);
  - `test_correcao_de_especie_na_proveniencia` (a linha lida do CSV com as colunas novas; `campo` e `valor` no registro; o texto do relatório do F1-12).
  - Nenhum teste existente mudou: `test_correcao_aparece_na_proveniencia` segue com o dicionário de sete campos, porque `para_dict` omite `campo` e `valor` vazios.
- **Dificuldades:** o texto da evidência dos testes tinha ";", o separador do CSV, e a linha lida saía com as colunas deslocadas.
- **Como resolvi:** a evidência usa " + " entre os documentos, nos testes e na linha real da tabela.
- **Medição** (índice reconstruído com `python -m sentinela.data.referencia --cobertura` a partir das fontes já baixadas em `data/fontes/`; "antes" com o código do `HEAD` numa worktree e `--pasta` apontando para `data/`; a cópia do índice anterior, de 13/10/2026, ficou em `/tmp/claude-1000/-home-marcos-projetos-Sentinela-B3/8db88202-c1da-45af-9f93-bb8140794803/scratchpad/indice_antes_f2b13.json`; cascata real com rede só de leitura, sem cache SQLite):
  - MGLU3 no índice: espécie PN, classe PNA, regra `fca:codigo_ativo` → espécie ON, sem classe, regra `correcao` (campo `especie`).
  - LPA da MGLU3: 0,2641397 (recalculado, com a marca "ações do fim do período", classe PNA) → 0,264 (divulgado da ON), os dois valores da ficha (5.3). VPA (14,5598) e P/VP (0,7631) sem mudança.
  - Cobertura do índice, antes e depois iguais: 2.528 registros e 51 exceções; companhias 454 de 482 códigos ativos no FCA; FIIs 291 pela junção e 394 pela reserva, de 706 listados; 1.043 BDR e 345 UNKNOWN. Só a lista de correções muda: STOCK `["CSNA3"]` → `["CSNA3", "MGLU3"]` (FII: TRXF11).
- **Testes:** 1430 passed, 1 skipped, 18 xfailed → 1434 passed, 1 skipped, 18 xfailed (+4: três testes, um com dois casos). Golden sem diferença; `tests/test_financeiro_pre_refactor.py` sem mudança. `ruff format` nos arquivos alterados; `ruff check sentinela/data/` verde; em `sentinela/reports/rastreabilidade.py` e `tests/test_referencia_correcoes.py`, a mesma contagem de erros do `HEAD` (o `dict()` de `_correcao`, linha 38, já existia).
- **Mutação** (`python -m mutmut run "sentinela.data.referencia*"`, meta ≥ 80%): pacote 1.312/1.479 (88,7%); `correcoes` 60/69 (87,0%), `montagem` 638/689 (92,6%). Sobreviventes do código novo, equivalentes na prática: "XX" no fim da mensagem de rejeição (o teste casa por trecho), `especie_corrigida = ""` no lugar de `None` (os dois são falsos) e o filtro das colunas opcionais em `ler_correcoes` (as obrigatórias já foram conferidas no cabeçalho). Os demais são de código anterior (encoding da leitura, nome empresarial, unit).
- **Resíduos:** o índice local (`data/referencia/indice.json`, fora do git) foi reconstruído duas vezes; o final é o do código novo, com as correções da tabela e a composição das units com a sigla da classe (F2B-12). `outputs/f2b13_*` fora do git.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:**
  - A tabela não tem coluna de fim do intervalo; ver "Intervalo de validade" acima.
  - A conferência das duas evidências é textual (o `arquivo` precisa citar a Composição do Capital e a DRE); o loop conferiu os números nos arquivos, mas a tabela não guarda os valores.
  - Ressalva da revisão do F2B-12: o parser da unit guarda a sigla só em "PNA" a "PNH" no singular; "2 PNAs" e o código do papel ("KLBN4") seguem como "PN", que com várias classes preferenciais casa direto com a linha "PN", sem a marca do F2B-12.

### F2B-14 — fix: cross-check recalculated EPS only against coherent reported EPS
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** corrige o BUG-2A-11 (achado 6 da auditoria; ficha por ação, 7.3 e 7.5). `market_engine._lpa_divulgado_comparado` passou a ler o dicionário de divulgados coerentes (`acoes_cvm.divulgados_coerentes`, o mesmo que decide o LPA dos métodos pela D19), e não mais `lpa_divulgado_por_especie` e `lpa_divulgado` brutos. Classe ou espécie do ticker com divulgado incoerente (sinal oposto, linhas conflitantes, lucro zero ou sinal não conferível): sem comparação (`None`), e o alerta é só o da incoerência ("CVM sem LPA: <motivo>", que já existia). Sem classe (unit ou fora do índice), vale o divulgado coerente da escala (ON, depois PN, depois as classes em ordem), como `divulgado_da_escala`.
- **Testes:**
  - `tests/regressao/test_bug_2a_11_alerta_lpa_antes_da_coerencia.py` (BUG-2A-11): marca retirada, em PASS; registro em "corrigido".
  - `tests/test_data_quality_fontes.py::test_divulgado_incoerente_nao_entra_na_conferencia`: xfail estrito, falhou com `--runxfail` pelo sintoma (`assert {'especie': 'PN', 'valor': -2.0} is None`), XPASS(strict) com a correção, marca retirada. Afirma também que o alerta de divergência não sai e que o risco da incoerência está lá.
  - `::test_divulgado_coerente_segue_conferido`: a conferência da PN coerente (2,5 contra o recalculado 2,0) segue com o alerta de 20%.
  - Nenhum teste existente mudou; os que conferiam o comparado (`test_sem_especie_compara_com_o_lpa_da_escala`, `test_lpa_de_unit_compara_por_acao`, `test_lpa_comparado_com_o_divulgado_da_mesma_especie`) seguem verdes.
- **Medição** (`outputs/f2b14_alertas.py`, fora do git; as 38 ações atuais do universo inicial; cascata real com rede só de leitura, sem cache SQLite; "antes" com o código do `HEAD` numa worktree): uma só muda.
  - **BBAS3:** o comparado era `None` (o ticker é ON, e `lpa_divulgado_por_especie` vinha vazio: o LPA da linha agregada do F2B-11 não entrava na conferência) e passa a ser ON 2,40, a linha agregada coerente; sem alerta (razão 0,9998).
  - **QUAL3** (duas linhas ON conflitantes): sem mudança. A escala fica indeterminada, a CVM não deriva os números por ação, e a conferência não roda, antes e depois; o risco "CVM sem LPA: LPA divulgado com linhas conflitantes para a espécie" segue.
  - Nenhuma ação atual do universo tem, na DFP 2025, divulgado de sinal oposto ao lucro dos controladores com escala determinada: o caso do bug não aparece nos dados de hoje.
- **Testes:** 1434 passed, 1 skipped, 18 xfailed → 1437 passed, 1 skipped, 17 xfailed (+2 novos; o BUG-2A-11 passou de xfailed a passed). Golden sem diferença; `tests/test_financeiro_pre_refactor.py` sem mudança. `ruff format` nos dois arquivos de teste; `ruff check` verde neles.
- **Mutação** (módulo V1 tocado, sem meta): `market_engine` 1.575/2.196 (71,7%; no F2B-8, 1.487/2.099), sem sobrevivente em `_lpa_divulgado_comparado`.
- **Resíduos:** nenhum no repositório; `outputs/f2b14_*` fora do git.
- **Decisões que ficaram para o Marcos:** nenhuma deste item. Ressalvas da revisão do F2B-13, registradas aqui porque o commit dele saiu como revisado:
  - a correção de espécie não exige `ticker == codigo_na_fonte`: uma linha com ticker diferente do código passaria, o índice gravaria o código da fonte e o relatório citaria o ticker da linha;
  - a conferência das duas evidências é textual e não confere que elas são do mesmo documento ("DFP 2025 + ITR 2024" passaria), e o trecho "dre" é curto;
  - a MGLU3 corrigida para ON ainda carrega `classes_preferenciais=["PNA"]` (calculado antes da correção); sem efeito hoje, porque o único leitor só age com mais de uma classe PN;
  - correção de espécie em linha de unit ou em chave de FII é aceita sem efeito (ou com o efeito da correção de código, no FII); a validação não restringe a correção de espécie às ações avulsas;
  - `cobertura["correcoes"]` passou a misturar correção de código e de espécie; a docstring de `cobertura.py` fala em tickers "ligados" pela tabela.
- **Para o Marcos revisar:** o comparado do BBAS3 passa a aparecer na conferência; antes, o banco não tinha nenhuma conferência de LPA.

### F2B-16 — fix: record FII figures per source for the cross-checks
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** corrige o BUG-2A-12 (achado 7; pendência do F2A-11; armadilha 2, no trecho de FII).
  - `market_engine._buscar_cvm_fii`: antes do merge, `_guardar_por_fonte(dados, 'CVM', campos)` grava em `valores_por_fonte['CVM']` o que o Informe Mensal entregou (VPA, PL e o P/VP pelo preço). Com isso, a checagem 3 da validação cruzada passa a reconhecer a identidade (P/VP e VPA da mesma fonte) e é pulada, pela regra do F2A-5.
  - `data_quality._alertas_pvp_do_fii`: P/VP da CVM × P/VP de cada fonte de mercado que o entregou (yfinance e brapi, em `valores_por_fonte`), com alerta acima de 10% (`_LIMIAR_PVP_FII`, o limiar dos checks 2 e 3; decisão do Marcos de 18/10/2026, [AUDITORIA]), medido sobre o P/VP da CVM. Só para o FII com o Informe aplicado (`cvm_fii_dt_referencia`); fonte sem P/VP, ou com P/VP ≤ 0, não é comparada.
- **Testes:**
  - `tests/regressao/test_bug_2a_12_fii_sem_valores_por_fonte.py` (BUG-2A-12): marca retirada, em PASS; registro em "corrigido".
  - Com xfail estrito → falharam com `--runxfail` pelo sintoma → XPASS(strict) → marca retirada: `tests/test_market_engine_fii_cvm.py::test_informe_grava_valores_por_fonte` (`KeyError: 'CVM'`; agora VPA 100, P/VP 0,9 e PL do Informe, e o P/VP 1,5 do yfinance ao lado), `tests/test_data_quality_fontes.py::test_identidade_do_fii_e_reconhecida` (`_mesma_fonte("pvp", "vpa")` False → True) e os três casos com alerta de `::test_pvp_do_fii_divergente_da_fonte_de_mercado_gera_alerta` (P/VP do yfinance 1,5, 0,999 e 0,8 contra 0,90 da CVM: 66,7%, 11,0% e 11,1%).
  - Sem marca, porque já passam e devem continuar: os dois casos sem alerta do mesmo teste (0,99, exatos 10%, e 0,95, 5,6%).
- **Testes:** 1437 passed, 1 skipped, 17 xfailed → 1447 passed, 1 skipped, 16 xfailed (+9 novos: 1 + 1 + 5 casos do aceite e 2 de unidade da mutação; o BUG-2A-12 passou de xfailed a passed). Golden sem diferença; `tests/test_financeiro_pre_refactor.py` sem mudança. `ruff format` nos três arquivos de teste; em `data_quality.py` e `market_engine.py`, a mesma contagem do `ruff check` do `HEAD` (1 e 11).
- **Mutação** (módulo V1 tocado, sem meta): `data_quality` 385/477 (80,7%) na primeira rodada, com seis sobreviventes em `_alertas_pvp_do_fii`; com dois testes de unidade diretos em `tests/test_data_quality_fontes.py` (`test_alerta_do_pvp_do_fii_so_com_o_informe_e_valores_validos` e `test_alerta_do_pvp_do_fii_confere_cada_fonte_de_mercado`: sem o Informe, P/VP da CVM ≤ 0, P/VP de mercado zero, só a brapi e as duas fontes), 388/477 (81,3%). Os três que restam no código novo são equivalentes: com o P/VP da CVM negativo, a divergência sai negativa e não alerta; o zero já cai em `not cvm`; e `>=` contra `>` só difere na folga de 1e−9.
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma deste item. Ressalvas da revisão do F2B-14, registradas aqui porque o commit dele saiu como revisado:
  - quando o LPA do banco vem da linha 3.99 (F2B-11; o BBAS3 é esse caso: 3.99.01 zerada, razão 0,9998), ela só é aceita com o recalculado a até 10%, e o alerta do F2A-5 dispara acima dos mesmos 10%: a conferência nunca alerta nesse caminho (família da armadilha 2). Com a 3.99.01, a conferência vale. Tirar a conferência da 3.99 ou marcá-la como não independente é item novo;
  - a ordem da escala em `_lpa_divulgado_comparado` repete a de `acoes_cvm.divulgado_da_escala`; juntar as duas é refactor, em commit à parte;
  - o comparado não leva a nota do divulgado (por exemplo, o sinal conferido pelo consolidado).
- **Para o Marcos revisar:** o alerta compara com cada fonte de mercado que entregou P/VP, então um FII pode ganhar dois alertas (yfinance e brapi). O yfinance e a brapi calculam o P/VP com o VPA deles, de data diferente da do Informe; parte da divergência é defasagem, não erro.

### F2B-17 — fix: stop flagging FIIs as outside CVM company coverage
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** corrige o BUG-2A-13 (achado 8; pendências do F2A-11 e da revisão do F2A-31). Em `market_engine.py`:
  - `buscar_dados_ticker`: sem índice, "referência oficial indisponível: dados da CVM não consultados" é gravado logo depois da etapa da referência, para qualquer classe e uma só vez, sem depender de a CVM estar injetada.
  - `_buscar_cvm`: sem CD_CVM, o aviso "ticker fora da cobertura da CVM" sai só para quem não é FII e com o índice disponível (o FII é coberto pelo Informe Mensal, não pelas DFPs).
  - `_buscar_cvm_fii`: FII sem CNPJ no índice (com o índice disponível) recebe `RISCO_FII_FORA_DO_INFORME`, "FII fora da cobertura do Informe Mensal".
- **Testes:**
  - `tests/regressao/test_bug_2a_13_fii_risco_fora_da_cvm.py` (BUG-2A-13): marca retirada, em PASS; registro em "corrigido".
  - Com xfail estrito → falharam com `--runxfail` pelo sintoma → XPASS(strict) → marca retirada, em `tests/test_market_engine_fii_cvm.py`: `test_fii_nao_recebe_o_aviso_de_cobertura_das_companhias` (`'ticker fora da cobertura da CVM' not in [...]`), `test_fii_sem_indice_tem_o_aviso_de_referencia` (`assert 0 == 1`: sem a CVM injetada, o aviso não saía) e `test_fii_sem_cnpj_tem_o_aviso_do_informe` (a constante não existia).
  - **Testes que mudam:** nenhum. Nenhum teste existente afirmava o aviso de cobertura das companhias para FII; os que o afirmam para ação (`tests/test_market_engine_referencia.py`, linhas 95, 168 e 186) e os do aviso de referência (195 e 405) seguem verdes sem mudança.
- **Testes:** 1447 passed, 1 skipped, 16 xfailed → 1451 passed, 1 skipped, 15 xfailed (+3 novos; o BUG-2A-13 passou de xfailed a passed). Golden sem diferença; `tests/test_financeiro_pre_refactor.py` sem mudança. `ruff format` nos dois arquivos de teste; `market_engine.py` com a mesma contagem do `ruff check` do `HEAD` (11).
- **Mutação** (módulo V1 tocado, sem meta): `market_engine` 1.601/2.226 (71,9%; no F2B-14, 1.575/2.196).
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** motores montados sem o índice nos testes (`_engine` sem `referencia`) passam a ter o aviso de referência em `riscos_dados`; nenhum teste fixava a lista vazia nesse caso. Na aplicação, a referência é sempre injetada (`MarketEngine.__init__`), e o aviso só aparece quando o índice está indisponível.

### F2B-18 — fix: discard implausible negative ROE at the provider boundary
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** corrige o BUG-2A-21 (decisão C da auditoria do Gemini; pendência do F2A-30). Decisão do Marcos de 18/10/2026, [AUDITORIA] em (a): piso de −2, simétrico ao teto de 2, só nas fontes de mercado.
  - `sentinela/data/normalizacao.py`: `ROE_MIN = -2.0` e `MOTIVO_ROE_ABAIXO` ("ROE abaixo de −2 (−200%) depois da conversão: descartado"); `guardar_roe` ganhou `com_piso` (padrão verdadeiro): abaixo do piso, ausente com o motivo, como acima do teto. A docstring do módulo diz onde o piso vale.
  - `market_engine._roe_guardado`: passa `com_piso=False` para a CVM, então o ROE dos controladores não passa pelo piso; yfinance e brapi passam.
- **Testes:**
  - `tests/regressao/test_bug_2a_21_roe_sem_piso.py` (BUG-2A-21): marca retirada, em PASS; registro em "corrigido".
  - `tests/test_roe_fronteira.py::test_roe_abaixo_do_piso_vira_ausente_com_motivo`: xfail estrito, falhou com `--runxfail` (a constante do piso não existia), XPASS(strict) com a correção, marca retirada. Confere −2,0 aceito, −2,0001 descartado e o cenário da auditoria na cascata (yfinance com −21: ROE ausente e "ROE descartado (yfinance): …").
  - `::test_roe_negativo_acima_do_piso_passa` (−1,5 na guarda; −0,9 da brapi na cascata) e `::test_roe_dos_controladores_da_cvm_nao_passa_pelo_piso` (ROE −3,0 da CVM fica): sem marca, porque já passavam e devem continuar. O da CVM falhou no meio da correção, com o piso aplicado a toda fonte, até a chamada da CVM passar `com_piso=False`.
- **Dificuldades:** o F2B-18 foi começado com o F2B-17 ainda em revisão, e o teste da CVM quebraria o gate do commit dele.
- **Como resolvi:** guardei o trabalho parcial num stash nomeado ("wip F2B-18 claude-code…"), commitei o F2B-17 com a árvore dele e restaurei o stash (`git stash pop`); só depois mexi no `market_engine.py`.
- **Testes:** 1451 passed, 1 skipped, 15 xfailed → 1455 passed, 1 skipped, 14 xfailed (+3 novos; o BUG-2A-21 passou de xfailed a passed). Golden sem diferença (o score não mudava: todo ROE abaixo de `ROE_PENALIDADE_MAX` leva a mesma penalidade); `tests/test_financeiro_pre_refactor.py` sem mudança. `ruff format` em `normalizacao.py` e nos dois testes; `market_engine.py` com a mesma contagem do `ruff check` do `HEAD` (11).
- **Mutação:** `sentinela.data.normalizacao` 64/64 (100%, meta ≥ 80%); `market_engine` (V1, sem meta) 1.607/2.232 (72,0%), sem sobrevivente na linha nova (os dois de `_roe_guardado` são do `setdefault` de `riscos_dados`, que sempre existe).
- **Resíduos:** nenhum. O stash foi restaurado e apagado pelo próprio `pop`; resta o do F2B-20, que volta no item seguinte.
- **Decisões que ficaram para o Marcos:** nenhuma deste item. Ressalvas da revisão do F2B-17, registradas aqui porque o commit dele saiu como revisado:
  - em `test_fii_sem_cnpj_tem_o_aviso_do_informe`, a asserção sobre "ticker fora da cobertura da CVM" passa sempre (o motor do teste não tem a CVM injetada); o ramo corrigido é coberto por `test_fii_nao_recebe_o_aviso_de_cobertura_das_companhias`;
  - nenhum teste confere que, sem índice, o FII não recebe "FII fora da cobertura do Informe Mensal" (a guarda por `_sem_referencia` em `_buscar_cvm_fii`);
  - um FII com CNPJ cujo Informe vem vazio segue sem aviso; um ticker fora do índice que o classificador trata como FII recebe os dois avisos (fora da referência e fora do Informe);
  - a evidência do BUG-2A-13 no registro ainda aponta `market_engine.py:748`; o trecho está perto da linha 775.
- **Para o Marcos revisar:** o ROE dos controladores da CVM pode ficar abaixo de −2 (por exemplo, PL pequeno com prejuízo grande); o piso não o alcança, pela decisão.

### F2B-20 — fix: refuse non-positive prices in both engines
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** corrige o BUG-2A-22 (ressalva da auditoria do Gemini ao F2A-25). O motor de ações (`valuation_engine.processar`) recusava só o preço zero (pelo `not dados.get('preco_atual')`) e o não finito; o de FII (`fii_engine.analisar`), só `p == 0` e o não finito. Os dois passam a devolver `None` com preço ≤ 0, como com o zero (F2A-24).
- **Golden** (regra da 2A): regenerado com `GERAR_GOLDEN=1 python -m pytest tests/test_equivalencia_motores.py::test_gerar_golden`; `python scripts/golden_diff.py --onde "(entrada.get('preco_atual') or 0) < 0"` sai com 0: 2 alterados (`acoes/preco-negativo`, que saía com Graham de R$ 12,25 e Bazin de R$ −5,52, e `fii/preco-negativo`, com Bazin FII de R$ −8,11), agora `None`; 0 incluídos, 0 removidos, 0 fora do predicado. Arquivo com 926.957 bytes.
- **Testes:**
  - `tests/regressao/test_bug_2a_22_preco_negativo_nos_motores.py` (BUG-2A-22, os dois motores): marca retirada, em PASS; registro em "corrigido".
  - `tests/test_saidas_finitas.py::test_preco_negativo_nao_e_analisado`, parametrizado com −10 e −0,01, nos dois motores: xfail estrito, falhou com `--runxfail` pelo sintoma (o resultado com Graham de R$ 12,25), XPASS(strict) com a correção, marca retirada.
  - Seções A, B e C intactas: `git diff v2-fase-2a -- tests/test_financeiro_pre_refactor.py` mostra só a mudança do F2B-7; `-m preservar` com 12 passed.
- **Dificuldades:** o F2B-20 foi começado com o F2B-17 em revisão e guardado num stash nomeado para não quebrar o gate dele. Criado com o F2B-17 em stage, o stash guardou também aquele índice; no `git stash pop`, depois dos commits do F2B-17 e do F2B-18, o diário entrou em conflito.
- **Como resolvi:** o lado do stash no conflito estava vazio (o índice guardado era o do F2B-17, já commitado), e `fila.md`, `market_engine.py` e o registro saíram do `pop` iguais ao `HEAD` (`git diff HEAD` vazio). Restaurei o diário pelo `HEAD`, tirei do stage os três arquivos do item e, conferido o diff deles, apaguei o stash (`git stash drop`). Nenhum conteúdo se perdeu.
- **Testes:** 1455 passed, 1 skipped, 14 xfailed → 1459 passed, 1 skipped, 12 xfailed (+2 casos novos; os 2 casos do BUG-2A-22 passaram de xfailed a passed). `ruff format` nos dois arquivos de teste; nos motores, a mesma contagem do `ruff check` do `HEAD` (2 e 2).
- **Mutação** (módulos V1 tocados, sem meta): `valuation_engine` 646/721 (89,6%; no F2B-7, 645/718) e `fii_engine` 247/274 (90,1%, igual ao F2B-7).
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** a docstring de `tests/test_roe_fronteira.py` e a regra do ROE em "Regras econômicas vigentes" do `CLAUDE.md` ainda não citam o piso de −2 do F2B-18 (ressalva da revisão do F2B-18); o `CLAUDE.md` é do F2B-33, que sincroniza as instruções no fim da fase.

### F2B-37 — fix: apply the controlling-interest rule to the trailing twelve months
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** corrige o BUG-2A-10 (achado 5 do Gemini). `cvm_provider.CVMProvider._acumulados_do_arquivo` lia o lucro dos controladores de cada documento do TTM direto da conta, e a 3.11.01 zerada entrava como zero.
  - Cada documento do TTM passa por `lucro_controladores_com_reserva` (D20 e decisão 7.2, a mesma leitura da série anual), com o balanço consolidado (`BPP_con`) do mesmo documento (`DT_REFER` e `VERSAO`). Arquivo sem `BPP_con` lido: a leitura segue com o balanço vazio (2.03.09 ausente).
  - `series_cvm.Acumulado` ganhou `motivos` (por campo, opcional), e o provedor grava nele o motivo da abstenção do lucro dos controladores do documento.
  - `series_cvm.ttm`: com o campo abstido em algum documento dos quatro trimestres, o motivo do TTM é o genérico seguido do motivo do documento ("campo ausente em ao menos um dos documentos dos quatro trimestres: lucro dos controladores não separado no documento, com não controladores no balanço"); sem motivo no documento, segue o genérico.
- **Testes:**
  - `tests/regressao/test_bug_2a_10_ttm_sem_regra_7_2.py` (BUG-2A-10): marca retirada, em PASS; registro em "corrigido".
  - `tests/test_cvm_series.py::test_ttm_abstem_quando_um_documento_se_abstem`: xfail estrito, falhou com `--runxfail` (`Acumulado` sem `motivos`), XPASS(strict) com a correção, marca retirada. O `import pytest` que eu tinha acrescentado só para a marca saiu com ela.
- **Dificuldades:** o arquivo sintético do teste de regressão não traz `BPP_con`, e a primeira versão deixava o `FileNotFoundError` escapar.
- **Como resolvi:** a leitura do balanço trata `OSError` (do qual `FileNotFoundError` é subclasse), `KeyError` e `ValueError` como balanço vazio.
- **Medição** (`outputs/f2b37_ttm.py`, fora do git; as 38 ações atuais do universo inicial; ITR de 2024 a 2026 e DFPs já em `data/cvm/`; cascata real com rede só de leitura, sem cache SQLite; "antes" com o código do `HEAD` numa worktree): 34 iguais, quatro mudam. Lucro dos controladores do TTM, antes → depois (lucro líquido do TTM igual nos dois):

  | Ticker | Antes | Depois | Leitura |
  |---|---|---|---|
  | KLBN11 | −973.308.000 | — (abstenção) | 3.11.01 zerada com não controladores no balanço (7.2); lucro líquido do TTM 535.987.000 |
  | SBSP3 | 3.196.215.000 | — (abstenção) | o mesmo motivo; lucro líquido 8.057.470.000 |
  | LWSA3 | 25.225.000 | −200.225.000 | trimestres com a 3.11.01 zerada, sem não controladores: a reserva dá o lucro total, igual ao lucro líquido |
  | RECV3 | 638.352.000 | 499.164.000 | o mesmo; igual ao lucro líquido |

  Antes, os trimestres zerados entravam como zero e misturavam escopos: a KLBN11 chegava a um lucro dos controladores negativo com o lucro líquido positivo.
- **Testes:** 1459 passed, 1 skipped, 12 xfailed → 1462 passed, 1 skipped, 11 xfailed (+2 novos, o do aceite e o do balanço; o BUG-2A-10 passou de xfailed a passed). Golden sem diferença (o TTM é informativo, só no relatório; o F2C-1 vai consumi-lo); `tests/test_financeiro_pre_refactor.py` sem mudança. `ruff format` nos arquivos alterados de `sentinela/data/` e de teste.
- **Mutação:** `sentinela.data.series_cvm` 350/363 (96,4%, meta ≥ 80%; um sobrevivente em `ttm`). `cvm_provider` (V1, sem meta): 1.264/1.430 (88,4%) na primeira rodada, com 35 sobreviventes em `_acumulados_do_arquivo` (o ramo do balanço não tinha teste de provedor); com `tests/test_cvm_series.py::test_ttm_le_o_balanco_do_mesmo_documento_para_a_reserva` (ITR sintético com `BPP_con`: março, versão 1, sem não controladores, leva a reserva, 100.000, e a versão 2 do balanço, com eles, não vale para a 1; junho, com não controladores, se abstém, com o motivo), 1.289/1.430 (90,1%), com 10 sobreviventes no ramo.
- **Resíduos:** nenhum no repositório; `outputs/f2b37_*` fora do git.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Revisão:** 1ª rodada aprovada com médios. Corrigido antes do commit: no teste do balanço, a versão 1 de março tinha não controladores e a versão 2 não; sem o filtro por `VERSAO`, as duas linhas divergentes também dariam abstenção, e o teste não provava o filtro. Os valores foram invertidos (versão 1 sem, versão 2 com), e o mesmo teste agora falha sem o filtro. Ficam registrados: `zipfile.BadZipFile` fora do `except` da leitura do balanço (a DRE do mesmo ZIP já foi lida antes); o filtro por `DT_REFER` e `VERSAO` fora do `try`; e, para o F2C-1, que um trimestre isolado pode subtrair documentos de escopos diferentes (um pela reserva, outro com a 3.11.01 preenchida), com erro limitado, porque a reserva só vale sem não controladores no balanço daquela data. A docstring de `_acumulados_do_arquivo` ainda não cita o `BPP_con` nem os motivos.
- **Para o Marcos revisar:** o TTM da KLBN11 e da SBSP3 passa a se abster do lucro dos controladores, com o motivo em `dados['ttm_cvm']['motivos']`; o relatório do F1-12 (`rastreabilidade.py:518`) mostra só o período do TTM ou a abstenção inteira, não o motivo por campo. O lucro líquido do TTM segue disponível.

### F2B-38 — fix: pick the latest version of a restated FII monthly report
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** corrige o BUG-2A-14. `cvm_fii_provider.CVMFIIProvider.obter_dados_fii` ordenava as linhas do fundo só por `Data_Referencia`; com duas versões da mesma data, ficava a primeira do arquivo. Agora ordena por `Data_Referencia` e pela `Versao` lida como número (`pd.to_numeric(..., errors="coerce")`), as duas em ordem decrescente: na mesma data, vale a reapresentação (maior `Versao`), a regra que o F2B-28 usa nos 12 meses. Versão ilegível vira NaN e fica atrás (o `sort_values` põe NaN no fim).
- **Testes:**
  - `tests/regressao/test_bug_2a_14_informe_sem_desempate_por_versao.py` (BUG-2A-14): a marca saiu e ele passa; registro em "corrigido".
  - `tests/test_cvm_fii_provider.py::test_versao_ilegivel_nao_impede_o_desempate` (versão "1a" contra a 2: vale a 2, sem erro), acrescentado pela mutação. Com versão vazia, o teste não discriminava: o leitor do CSV já a lê como NaN.
  - `::test_versao_e_comparada_como_numero` (versão "10" contra "9": vale a 10), acrescentado na revisão: os outros dois passariam com a `Versao` ordenada como texto. Conferido numa worktree com a conversão retirada: falha com `170.0 == 190.0`.
- **Suíte:** 1462 passed, 1 skipped, 11 xfailed → 1465 passed, 1 skipped, 10 xfailed (+2 novos; o BUG-2A-14 passou de xfailed a passed). Golden sem diferença. `ruff format` nos dois arquivos de teste; `cvm_fii_provider.py` com a mesma contagem do `ruff check` do `HEAD` (2).
- **Mutação** (módulo V1 tocado, sem meta): `cvm_fii_provider` 227/285 (79,6%; no fim da 2A, 208/266), sem sobrevivente na linha nova.
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma deste item. Ressalvas da 2ª revisão do F2B-37, registradas aqui porque o commit dele saiu como revisado:
  - balanço ilegível, ou documento sem linha de balanço com o mesmo `DT_REFER` e `VERSAO`, é tratado como "sem não controladores", e a reserva da 7.2 libera o lucro total; a série anual faz o mesmo com o balanço vazio, então não é regressão, mas a falta do balanço não prova a ausência de minoritários. Distinguir "balanço ausente" de "2.03.09 ausente" muda a regra e cabe ao F2C-1, quando o TTM for consumido;
  - `test_ttm_abstem_quando_um_documento_se_abstem` confere o motivo do documento por `in`, não pela igualdade com o prefixo genérico; é o sobrevivente que restou em `series_cvm.ttm`.
- **Para o Marcos revisar:** nada além do acima.

### F2B-39 — fix: keep a valid dividend yield over an out-of-range later source
- **Executor:** claude-code (claude-opus-5-5)
- **Status:** sucesso
- **O que foi feito:** corrige o BUG-2A-15. No merge da brapi (`overwrite=True`), qualquer DY finito sobrescrevia o anterior; um 0,40 apagava o 0,06 válido do yfinance, e o invariante dos motores só o zerava depois. `market_engine._dy_guardado` aplica `config._normalizar_dy` (o invariante, armadilha 4) ao DY da brapi antes do merge: fora de 0–25%, o DY não entra, o válido anterior fica, e o descarte vai para `riscos_dados` ("DY descartado (brapi): …") e para `dados['proveniencia']['dy_descartes']` (fonte, valor e `MOTIVO_DY_FORA_DA_FAIXA`), no mesmo molde do `_roe_guardado`. Nenhuma conversão de percentual nova: a da fronteira continua a única. DY zero ("sem proventos") é dado e entra.
- **Testes:**
  - `tests/regressao/test_bug_2a_15_dy_invalido_sobrescreve_valido.py` (BUG-2A-15): marca retirada, em PASS; registro em "corrigido".
  - `tests/test_dy_fronteira.py::test_dy_fora_da_faixa_nao_entra_no_merge`: xfail estrito, falhou com `--runxfail` (a constante do motivo não existia), XPASS(strict) com a correção, marca retirada. Confere o 0,06 do yfinance que fica, o P/L da brapi que entra, o risco e o registro do descarte, e que DY 0 e 0,12 da brapi entram sem descarte.
- **Suíte:** 1465 passed, 1 skipped, 10 xfailed → 1467 passed, 1 skipped, 9 xfailed (+1 novo; o BUG-2A-15 passou de xfailed a passed). Golden sem diferença; `tests/test_financeiro_pre_refactor.py` sem mudança. `ruff format` nos dois arquivos de teste; `market_engine.py` com a mesma contagem do `ruff check` do `HEAD` (11).
- **Mutação** (módulo V1 tocado, sem meta): `market_engine` 1.650/2.279 (72,4%; no F2B-18, 1.607/2.232). Os quatro sobreviventes de `_dy_guardado` trocam o padrão do `setdefault` de `riscos_dados` e de `proveniencia`, chaves que já existem nesse ponto da cascata: equivalentes na prática.
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:**
  - O guarda vale para o DY da brapi, a única fonte posterior que sobrescreve o DY na cascata (a CVM e o Informe Mensal não entregam DY; o cache de fundamentos só preenche o que falta, e grava o que já passou pela cascata). O yfinance, primeira fonte, segue sem ele: o motor aplica o invariante na entrada.
  - Como no ROE, o DY descartado também sai de `valores_por_fonte['brapi']` (a guarda vem antes do registro por fonte).
- **Ressalvas da revisão, realocadas nesta retomada:** o texto de `MOTIVO_DY_FORA_DA_FAIXA` fixa "0–25%", e o limite real é `MACRO.DY_SANIDADE_MAX`; `market_engine` passou a importar `config._normalizar_dy`, função privada; e não há teste do DY negativo da brapi, das bordas 0,25 e 0,2500001 no merge, nem do DY descartado sem DY anterior (o campo fica ausente).

### F2B-40 — fix: treat an empty COTAHIST archive as a failed download
- **Executor:** claude-code (claude-opus-5-5); conclusão e validação: codex
- **Status:** sucesso
- **O que foi feito:** corrige o BUG-2A-16. Em `sentinela/data/providers/b3_cotahist.py`:
  - `ler_zip`: ZIP sem arquivo levanta `zipfile.BadZipFile` ("ZIP sem arquivo"), o caminho do arquivo corrompido; `HistoricoRecente.coletar` já trata essa exceção, então o mês fica em `meses_ausentes`, com o aviso no log, em vez de o `IndexError` derrubar a coleta inteira.
  - `_completo`: além de baixado depois do fim do mês (mais a folga), o ZIP precisa abrir e trazer ao menos um arquivo (`_tem_arquivo`); o vazio ou corrompido não é a cópia definitiva e expira como a do mês corrente.
- **Testes:**
  - `tests/regressao/test_bug_2a_16_cotahist_zip_vazio.py` (BUG-2A-16): marca retirada, em PASS; registro em "corrigido".
  - `tests/test_cotahist.py::test_zip_vazio_nao_conta_como_completo`: xfail estrito, falhou com `--runxfail` pelo sintoma (`assert 0 == 1`: o ZIP vazio de dezembro, baixado em 13/01/2026, era aceito sem novo download), XPASS(strict) com a correção, marca retirada. Confere também o `BadZipFile` de `ler_zip`.
  - `::test_so_zip_que_abre_e_traz_arquivo_conta_como_completo` (ZIP com arquivo conta; arquivo corrompido não), acrescentado pela mutação.
- **Suíte:** HEAD: 1467 passed, 1 skipped, 9 xfailed → 1470 passed, 1 skipped, 8 xfailed (+2 testes novos; o BUG-2A-16 passou de xfailed a passed). A execução intermediária com 10 xfailed incluía o teste do aceite fora do stage, ainda marcado; não é a base commitada. Golden sem diferença. `ruff format` no módulo (só as linhas do item) e nos testes; `ruff check sentinela/data/` verde.
- **Mutação** (`sentinela.data.providers.b3_cotahist*`, meta ≥ 80%): 272/306 (88,9%) na primeira rodada; com o teste de `_completo`, 274/306 (89,5%). Sobreviventes nas linhas novas, equivalentes: a mensagem do `BadZipFile` (`None` no lugar do texto) e `>` contra `>=` na comparação do instante, que já existia.
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** nada além do acima.
- **Retomada pelo Codex:** suíte e gates de Ruff conferidos novamente; golden inalterado; metadados existentes do mutmut confirmam 274/306 (89,5%). Primeira revisão pediu correção da base da suíte e realocação das ressalvas do F2B-39 para sua própria seção; corrigido antes da segunda revisão.
