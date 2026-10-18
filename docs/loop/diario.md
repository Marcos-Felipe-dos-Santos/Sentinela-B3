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
