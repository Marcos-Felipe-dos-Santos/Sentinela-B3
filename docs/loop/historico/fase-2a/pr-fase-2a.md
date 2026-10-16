# Fase 2A — Dados corretos

Branch `v2/fase-2a` · um commit por item, sobre a tag `v2-fase-1`, mais os merges dos tickets do Jules (B4.1, B4.2, B4.3, C-D e os de janela na fase) e os commits de ativação, de decisão e do ADR-0003 · Fila e diário: `docs/loop/historico/fase-2a/`.
Plano: `docs/PLANO.md` (seção 6, "Fase 2A") · Validade: `docs/adr/0003-validade-dados-metodo-auditoria.md` · Proposta da próxima fila: `docs/loop/fila-fase2b-proposta.md`. **Não é consultoria financeira.**

A fase troca a origem dos dados que entram nos métodos: índice oficial (ticker ↔ CNPJ ↔ CD_CVM ↔ classe) no lugar dos mapas manuais e do sufixo do ticker, números por ação pela Composição do Capital e pelo LPA divulgado da classe, contas da CVM por código e descrição, lucro e PL dos controladores, bancos pelo modelo financeiro, dívida financeira líquida, DY e ROE convertidos uma vez na fronteira, CVM de FII pela cascata, ticker validado, proveniência temporal e liquidez medida. O Fundamentus saiu. **Muda número e texto na saída**: cada mudança veio num `fix:` próprio, com xfail estrito antes; o golden mudou só nos itens **[golden]**.

## Itens e commits

| Item | Commit | Título |
|---|---|---|
| F2A-15 | `8899611` | chore: add golden diff tool for scoped regeneration |
| F2A-17 | `87a5a14` | refactor: cache parsed CVM statements per file |
| F2A-18 | `0146785` | feat: add B3 COTAHIST provider |
| F2A-16 | `0bb000b` | docs: survey official sources for phase 2A |
| F2A-1 | `d31b207` | feat: build official reference of tickers, issuers and asset classes |
| F2A-2 | `c1b0e70` | feat: add sector, FII segment and control type to the reference |
| F2A-19 | `5499ef6` | fix: resolve CVM codes and asset data from the official reference |
| F2A-20 | `486fb1e` | fix: classify assets from official data instead of ticker suffix |
| F2A-3 | `882ef0c` | fix: derive per-share figures from CVM share composition |
| F2A-6 | `b2d5b56` | fix: keep collected values intact for quality checks |
| F2A-5 | `b83dde1` | fix: cross-check per-share data against independent sources |
| F2A-32 | `9a14e54` | feat: record temporal provenance for collected data |
| F2A-33 | `212ee46` | feat: map CVM accounts by code and description |
| F2A-38 | `d4bdb11` | fix: read existing CVM accounts through the code and description table |
| F2A-34 | `9ed6af3` | docs: add methodology sheet for per-share figures |
| F2A-35 | `17603b6` | docs: define the initial universe |
| F2A-36 | `31f3dec` | fix: use reported EPS by share class in valuation inputs |
| F2A-37 | `f760897` | fix: restrict controlling-interest fallbacks to evidence of no minorities |
| F2A-7 | `6f58193` | feat: add five-year CVM series and trailing twelve months |
| F2A-8 | `34dcfbf` | fix: measure leverage by net financial debt |
| F2A-22 | `bbb5e12` | fix: replace Fundamentus fallback with a missing-data check |
| F2A-9 | `aa8a2c5` | fix: read bank equity and earnings from the financial template |
| F2A-4 | `91335e7` | fix: normalize DY once at the provider boundary |
| F2A-29 | `8e68a0c` | fix: abstain stock methods for ETFs, BDRs and unknown assets |
| F2A-30 | `b2518fe` | fix: guard ROE at each provider boundary |
| F2A-21 | `08676ac` | fix: report untrusted DY as the Bazin abstention reason |
| F2A-11 | `d0bd74f` | fix: feed FII book value from CVM and abstain without it |
| F2A-23 | `4092ef7` | fix: stop using manual FII estimates |
| F2A-24 | `09150aa` | fix: keep non-finite values out of engine outputs |
| F2A-25 | `d173a12` | fix: abstain Gordon when earnings per share is not positive |
| F2A-12 | `399a408` | fix: validate tickers against an allowlist before URLs and prompts |
| F2A-26 | `97fe57e` | feat: add liquidity metrics from COTAHIST |
| F2A-31 | `c827920` | fix: resolve CVM data only from the official reference |
| F2A-27 | `c97453c` | docs: sync agent instructions with phase 2A data layer |
| F2A-28 | `1cd4bcf` | docs: propose phase 2B queue |
| F2A-13 | `b1322e1` | chore: clean up phase 2A residue |
| F2A-14 | (este commit) | docs: add phase 2A summary and archive loop files |

Fora da lista: **F2A-39** (BTG Pactual no índice) ficou `[!]` em 13/10/2026 e foi para a 2B por decisão do Marcos (a ligação indireta ISIN ↔ CNPJ não foi aceita); **F2A-10** (abstenção por liquidez) saiu da fila na ativação, sem decisão da [LIQUIDEZ], e também vai para a 2B. Commits de decisão no meio da fase: `3ebd6ec`, `c7a73e0`, `354b6b4` e `9c65be0` (ADR-0003), `939822e`, `45b96d5` e `c97cd47` (ficha por ação e universo), `e3d8f78` (BTG e pendências do F2A-36/37) e `f53d149` (auditoria do Gemini).

## Testes, antes → depois

- **653 passed + 1 skipped + 1 xfailed** na tag `v2-fase-1` → **685 passed + 1 skipped + 2 xfailed** na ativação (tickets do Jules) → **1.343 passed + 1 skipped + 1 xfailed** no fim, em 76 módulos de teste. O skip é o gerador do golden. O xfail que saiu é o da seção C (F2A-4).
- Seções de `tests/test_financeiro_pre_refactor.py`: `git diff v2-fase-1` mostra só as duas mudanças previstas, a seção B no F2A-8 (dívida líquida) e a seção C no F2A-4 (retirada do xfail do DY percentual). A seção A não mudou.
- Testes existentes alterados fora da lista do item, sempre com justificativa no diário: F2A-20 (dois de `test_analysis_service.py`), F2A-37 (dois de `test_contas_cvm_consumidores.py`, um caso NaN saiu da parametrização; aceito pelo Marcos em 13/10/2026), F2A-8 (`test_completude_divida_liq_ebitda_nao_e_cvm` com a asserção invertida), F2A-9 (dois de banco), F2A-4 (fixtures do yfinance em fração), F2A-12 (literais de ticker fora do formato), F2A-25 (um LPA 0 acidental), F2A-31 (helpers e testes que fixavam o mapa manual) e F2A-13 (chamadas a `FIIEngine(cvm_provider=None)` e o que chamava o que saiu).

## Mutação

Configuração do `[tool.mutmut]`, mortos/total, no último item que tocou cada módulo.

| Módulo | Score | Item |
|---|---|---|
| `sentinela.data.providers.b3_cotahist` | 265/298 (88,9%) | F2A-26 |
| `sentinela.data.referencia*` | 1.137/1.308 (86,9%); `montagem` 618/675 no F2A-36 | F2A-20 |
| `sentinela.services.asset_classifier` | 73/81 (90,1%) | F2A-20 |
| `sentinela.data.acoes_cvm` | 277/296 (93,6%) | F2A-36 |
| `sentinela.data.proveniencia` | 154/188 (81,9%) | F2A-32 |
| `sentinela.data.contas_cvm` | 168/178 (94,4%) | F2A-38 |
| `sentinela.data.controladores` | 75/75 (100%) | F2A-37 |
| `sentinela.data.series_cvm` | 346/358 (96,6%) | F2A-7 |
| `sentinela.data.divida_liquida` | 111/114 (97,4%) | F2A-8 |
| `sentinela.data.providers.ifdata` | 180/208 (86,5%) | F2A-9 |
| `sentinela.data.normalizacao` | 61/61 (100%) | F2A-30 |
| `sentinela.domain.ticker` | 12/12 (100%) | F2A-12 |
| `sentinela.data.liquidez` | 71/74 (95,9%) | F2A-26 |
| `sentinela.methods*` | 100% em todos: base 183/183, bazin 61/61, fii_nav 16/16, fii_yield 51/51, gordon 116/116, graham 81/81, lynch 109/109, registry 34/34 | F2A-25 (base de novo no F2A-13) |

V1, sem meta, no F2A-13: `fii_engine` 244/271 (90,0%), `data_quality` 343/430 (79,8%), `brapi_provider` 190/314 (60,5%), `cvm_fii_provider` 208/266 (78,2%), `cvm_provider` 1.210/1.344 (90,0%), `market_engine` 1.472/2.093 (70,3%); `valuation_engine` 645/718 no F2A-24; `ai_core` 74/233 no F2A-32.

## Mudanças de comportamento

### Na saída dos motores (golden)

O golden começou a fase com 2.247 linhas e 1.015.082 bytes e termina com **2.079 linhas e 927.404 bytes**. Cada regeneração passou por `python scripts/golden_diff.py` (F2A-15) com o predicado do item, saindo com 0.

| Item | Predicado (`--onde`) | Alterados | Incluídos | Removidos | Efeito |
|---|---|---|---|---|---|
| F2A-22 | `--par "erro_scraper=fundamentos_incompletos"` e só o texto do risco muda | 246 | 0 | 0 (4 pares renomeados) | flag do scraper vira "campo obrigatório faltando"; risco "Dados fundamentais obrigatórios ausentes"; números iguais para a mesma flag |
| F2A-4 | `isinstance(entrada.get("dy"), (int, float)) and not (0 <= entrada["dy"] <= 1)` | 236 | 0 | 0 | o motor deixa de converter DY percentual; acima de 0,25 é DY não confiável |
| F2A-29 | `False` | 0 | 10 | 0 | ETF, BDR e `UNKNOWN` saem "FORA DO ESCOPO DOS MÉTODOS", sem número |
| F2A-11 | FII sem P/VP positivo nem valor da cota positivo | 6 | 0 | 0 | P/VP ausente ou zero sai `None`, não 1,0; P/VP negativo perde o bônus de +10 (teste próprio) |
| F2A-23 | FII TST13, ou TST11 sem vacância do provedor | 75 | 0 | 0 | vacância manual não é lida: muda DY efetivo, preço justo, upside e score; 15 classificações mudam |
| F2A-24 | `False` | 0 | 7 | 0 | preço NaN ou infinito devolve `None`; FII sem método calculado sai "Dados insuficientes (…)" |
| F2A-25 | Gordon presente e sem P/L e preço positivos | 217 | 0 | 0 | Gordon 1.1.0 se abstém com LPA não positivo; 146 scores e 9 classificações mudam |
| F2A-13 | só remoções, exatamente os casos com `cvm` | 0 | 0 | 185 | saiu o caminho de provedor do motor de FII (32 de vacância, 18 de cota, 9 de provedor, 3 avulsos, 123 aleatórios) |

O F2A-21 mudou só o motivo da abstenção do Bazin (1.0.1; nenhum número) e não aparece no golden.

### Na cascata, nos dados e nos relatórios (fora do golden)

- **F2A-19 e F2A-31 (CVM pelo índice).** O CD_CVM e o CNPJ vêm só do índice oficial; os mapas manuais deixaram de ser lidos. A CSNA3 volta à CVM pela tabela de correções (`4030` no FCA). Sem índice local, nenhum ticker recebe dados da CVM, com o risco "referência oficial indisponível". AZUL4, ELET3, GOLL4, JBSS3, PETZ3, BCFF11, IRDM11 e RBRF11 (históricos) deixam de receber dados da CVM.
- **F2A-20 (classe).** A classe vem do índice; sem ele, das listas, e o final 11 sozinho vira `UNKNOWN`. BRBI11 e IGTI11 passam a `UNIT` (antes, FII); BTCI11 e TRPL11 saem do motor de FII.
- **F2A-3, F2A-36 e F2A-37 (por ação).** Ações pela Composição do Capital do mesmo documento, LPA dos métodos = divulgado da classe, lucro e PL dos controladores com as reservas da D20. Nas 45 ações do mapa: PETR4 LPA 20,31 → 8,54, GOAU4 1,69 → 0,36, BBDC4 4,53 → 2,35, USIM5 −5,51 → abstenção, CMIG4 2,57 → 1,71, GGBR4 1,14 → 0,70; VPA cai onde há minoritários (CSAN3 7,86 → 1,34, ROE −0,33 → −1,83); KLBN11 LPA da unit 1,3676 → 1,1430, com VPA e ROE em abstenção. Abstêm-se ASAI3, NTCO3, COGN3, RECV3, TIMS3, VIVT3, QUAL3, BBAS3 e USIM5.
- **F2A-5 e F2A-6 (qualidade).** Alertas novos: ações da CVM × yfinance acima de 5% (HYPE3 +11,2%, SBSP3 +402%) e LPA recalculado × divulgado acima de 10%; os checks de identidade são pulados quando a fonte é a mesma; o relatório de qualidade avalia o retrato coletado, não a saída do motor.
- **F2A-38 (contas por código e descrição).** Nos 9 bancos com consolidado, os campos genéricos lidos como empresa passam a se abster (o BBAS3 tinha PL de R$ 38,7 bi, as provisões, e `divida_pl` 62,5); BBSE3 e IRBR3 leem o EBIT na 3.07.
- **F2A-8 (alavancagem).** Dívida financeira líquida (2.01.04 + 2.02.01 − 1.01.01 − 1.01.02) ÷ EBITDA e ÷ PL, só da CVM; banco e seguradora e EBITDA ≤ 0 se abstêm. WEGE3 −0,30; PETR4 1,45.
- **F2A-22 (sem Fundamentus).** Prejuízo conta como campo faltando (P/L ≤ 0 e ROE ≤ 0 pela regra antiga de `_is_field_missing`): −30 de confiança e o risco "ausentes" para dado presente (achado 1 do Gemini). Sem yfinance e brapi, não há mais preço de reserva.
- **F2A-9 (bancos).** PL, lucro e controladores pelo modelo financeiro: ITUB4 ROE 21,9%, BBDC4 13,3%, BBAS3 7,2%; VPA da CVM ITUB4 18,55 e BBDC4 16,87; o Graham passa a usá-lo (R$ 41,11 e R$ 29,86). Basileia do IF.data (06/2026: 15,35%, 15,56% e 13,91%). Receita e margem não são preenchidas para banco.
- **F2A-4 e F2A-30 (fronteira).** DY e ROE convertidos uma vez por provedor; percentuais do yfinance abaixo de 1 passam a valer (BBAS3 0,57 → 0,0057); DY estranho da brapi sobrescreve um válido do yfinance e é rejeitado no motor; ROE acima de 2 ou não finito é descartado com motivo; ROE negativo passa.
- **F2A-11 e F2A-13 (FII).** P/VP oficial pelo Informe Mensal na cascata; o motor só lê `dados['pvp']`.
- **F2A-12 (ticker).** Fora do formato, `buscar_dados_ticker` devolve `None` sem chamar fonte; brapi e prompt também validam.
- **Aditivos (sem efeito nos métodos):** proveniência temporal (F2A-32), série de cinco anos e TTM (F2A-7), liquidez (F2A-26), setor, segmento e controle (F2A-2).

## Cobertura do índice (F2A-1, refeita no F2A-19)

Arquivos de 8/10/2026: FCA 2025 e 2026, Informe de FII 2025 e 2026, COTAHIST de jul a set/2026.
- **2.529 registros e 51 exceções** (eram 2.527 e 53 antes da tabela de correções).
- Companhias: 482 pares (CNPJ, código) ativos no FCA, **454 mapeados** (a CSNA3 pela tabela).
- FIIs: 707 listados em bolsa, 686 mapeados no F2A-1 (291 pela junção com o COTAHIST, 395 pela reserva do ISIN), mais o TRXF11 pela tabela no F2A-19.
- Outros: 1.043 BDRs e 345 cotas de fundo `UNKNOWN` (ETF sem ponte de ISIN).
- Exceções: 30 de código fora do formato (BTG `000000`, Rodobens, Embpar, Marfrig e outros), 1 sem código (Livetech), 19 registros de tickers repetidos em CNPJs distintos e 1 do Liquidez Projetos GD (perde o ISIN do TRXF11 pela tabela).
- Mapas manuais × índice: nenhum CD_CVM ou CNPJ divergente; os ausentes são históricos (universo inicial).

## Decisões pendentes

1. **[DECISÃO] da fase**, passos 1 a 9 da fila (revisão do golden, cobertura, relatórios reais, cache, auditoria externa em modo FASE, ficha 1.1, [LIQUIDEZ], push e tag).
2. **Ficha por ação 1.1** (passo 6): KLBN11 sem VPA (escala pelo lucro consolidado?), linha agregada de LPA no BBAS3 e no Banco Pine, USIM5 (PNA e PNB com uma linha "PN"), MGLU3 como "Ações Preferenciais" no FCA.
3. **[LIQUIDEZ]** (F2A-10): janela, métrica, valor, texto e comportamento sem dado; a distribuição por classe está no diário do F2A-26.
4. **Auditoria do Gemini** (`docs/loop/historico/fase-2a/auditoria-gemini-completa.md`): nove achados confirmados no código e as decisões A a D, sem decisão. Os quatro que mudam número ou contrariam decisão registrada:
   - (1) valores ≤ 0 da CVM descartados no merge e prejuízo contado como dado ausente (−30);
   - (2) reserva dos controladores liberada com "sem correspondência", contra a D20;
   - (3) P/VP não finito na saída do motor de FII, contra o F2A-24;
   - (4) ativo fora do índice (BPAC11) recebendo métodos de ação, apesar do F2A-29.
   Os outros: TTM sem a regra 7.2 (5), alerta do F2A-5 antes do filtro de coerência (6), `valores_por_fonte['CVM']` ausente no FII (7), "fora da cobertura da CVM" em todo FII (8) e minoritários lidos só no modelo do setor (9). Todos estão como candidatos na proposta da 2B, sob a [AUDITORIA].
5. **Proposta da 2B** (`docs/loop/fila-fase2b-proposta.md`): [SEÇÃO A], [LIQUIDEZ] e [AUDITORIA] condicionam a ativação; [TAXA], [BAZIN], [FII], [BANCOS], [FINANCEIRAS], [BTG] e [CACHE] ficam para o [DECISÃO] intermediário. Os pontos da 2ª revisão da proposta estão no diário do F2A-28.
6. **Mapas manuais** (F2A-13): os dicionários e `tests/fixtures/cvm_codigos_oficiais.csv` ficaram porque `scripts/levantamento_fase2a.py`, `scripts/dossie_fase2.py` e o índice falso dos testes os leem. Tirá-los pede um item de limpeza.
7. **BTG Pactual** (F2A-39, na 2B): fonte oficial da B3 com ISIN e CNPJ juntos.
8. **Refactor e comportamento no F2A-13**: a fonte `fundamentus` saiu da tabela de confiança no mesmo commit das correções automáticas, porque o item pedia as duas coisas; efeito nulo hoje.

## Resíduos que ficaram para o Marcos

- **Apagar à mão** (fora do git): `data/cotahist/`, `data/referencia/`, `outputs/levantamento_cache/` e `outputs/dossie_cache/`; os scripts de medição em `outputs/` (`f2a3_verificacao.json`, `f2a34_reservas.*`, `f2a36_*`, `f2a37_reservas.*`, `f2a7_medicao.py`, `f2a9_*`, `f2a26_liquidez.py`).
- **Depois do merge:** reconstruir o índice (`python -m sentinela.data.referencia`), porque um `indice.json` anterior ao F2A-36 carrega sem as classes preferenciais; e limpar o cache de fundamentos (passo 4 do [DECISÃO]), porque valores de antes da fase servem de reserva por até 7 dias.
- `mutants/` guarda uma cópia de `sentinela/data/referencia/contas_cvm.csv` atualizada à mão (o mutmut não recopia arquivos que não são `.py`).
- `app.py` (travado até o F3-6): "Erro Scraper" e "Dados Manual" sempre "Não"; ETF, BDR e `UNKNOWN` com valor justo R$ 0,00 e score 0/100; `tipo` do FII "TIPO INDISPONÍVEL".
- Seção "Fase atual" do `AGENTS.md` ainda lista arquivos que saíram (`fundamentus_scraper.py`, `tests/test_fundamentus_scraper.py`) ou mudaram de papel (`cvm_ticker_map.py`, `cvm_fii_map.py`); o `README.md:227` (Jules, C-A) ainda descreve o `cvm_ticker_map.py` como o mapa da CVM.
- Sem leitor, para fases seguintes: `FII_MANUAL_FALLBACK` e `_aplicar_fallback_manual_fii` (F2C-10), `scripts/invalidar_cache_cvm.py` e o teste dele (F2B-5), `erro_scraper` fora do `MethodInputs` (F3 e F3-6), a linha de vacância do relatório do F1-12.

## O que revisar primeiro

1. **O efeito do F2A-22 sobre prejuízo** (achado 1 do Gemini): toda empresa com P/L ou ROE ≤ 0 leva −30 de confiança e o risco "ausentes", somado aos −10 de "Dados incompletos". É a mudança com mais alcance que não aparece no golden.
2. **Os números por ação** (F2A-3, F2A-36, F2A-37): o antes → depois das 45 ações no diário do F2A-3 e do F2A-36, em especial PETR4, CSAN3, KLBN11 e as nove abstenções; e a SBSP3 com +402% contra o yfinance.
3. **Bancos** (F2A-9): o Graham passa a usar o VPA da CVM antes da lente própria (F2B-3); BBAS3 segue sem VPA.
4. **Golden do F2A-25 e do F2A-23**: 9 e 15 classificações mudam; no FII, a ausência de vacância oficial favorece o fundo em silêncio (`fii/TST11-sem-provedor` foi de score 10 para 50).
5. **Testes alterados fora da lista** (seção "Testes"), em especial o caso NaN do F2A-37 e a asserção invertida do F2A-8.
6. **Os outros três achados do Gemini que contrariam decisão** (2, 3 e 4 acima) e a proposta da 2B.

## Fechamento das auditorias

Auditorias externas da fase (Codex, modo FASE, e Gemini 4 Argon, duas passadas), consolidadas em `docs/loop/historico/fase-2a/auditoria-externa.md`. Decisão do Marcos de 15/10/2026: todo bug confirmado vira teste de regressão; os bloqueios criados pela própria 2A são corrigidos agora, e os demais ficam como xfail estrito apontando o item que corrige. Fila e diário deste fechamento: `fila-fechamento.md` e `diario-fechamento.md`, nesta pasta.

### Itens e commits

| Item | Commit | O que fez |
|---|---|---|
| F2A-40 | `82e68a3` | `tests/regressao/` com 18 testes de bug (BUG-2A-01 a 18), xfail estrito; registro `tests/regressao/README.md`; regra "Bugs e regressão" no protocolo e no `AGENTS.md`; `-rxX` no CI |
| F2A-41 | `edce32f` | D20 nas reservas dos controladores: par sem correspondência é abstenção; linha ausente só vale o total sem minoritários no balanço; 2.03.09 lida em qualquer modelo; PL total inválido com motivo |
| F2A-42 | `3b977a9` | P/VP NaN ou infinito vira `None` antes da lente do FII |
| F2A-43 | `8f2badb` | fora do índice, a cascata grava a classe do classificador; a guarda de escopo do F2A-29 passa a valer |
| F2A-44 | `861323f` | relatório de rastreabilidade: LPA da CVM pelo divulgado da classe (F2A-36) e FII sem P/VP com a lente abstida (F2A-11) |
| F2A-45 | este commit | este resumo e o arquivamento |

### Testes, antes → depois

- **1.343 passed + 1 skipped + 1 xfailed** em `c9d72d5` (abertura do fechamento) → **1.362 passed + 1 skipped + 18 xfailed** em `861323f`. Os 17 xfailed novos são os bugs abertos (28 casos registrados no F2A-40; 11 passaram a PASS nas correções). Módulos de teste: 76 → 94 (os 18 de `tests/regressao/`).
- Golden inalterado em todos os itens (no F2A-42, regenerado e idêntico: o golden não tem caso de FII com P/VP não finito). `tests/test_financeiro_pre_refactor.py` inalterado.
- Mutação em `sentinela.data.controladores*` (F2A-41): 98 mortos e 3 sobreviventes pelo mutmut (97,0%); os 3 morrem com os testes existentes quando rodados contra o mutante (o mapa de testes do mutmut não associava os testes antigos à função nova).
- Testes existentes alterados fora da lista do item, com justificativa no diário: F2A-41, `test_controladora_sem_correspondencia_se_abstem` (era `…_vale_o_lucro_total_como_no_f2a_3`) e uma asserção de `test_pl_subtrai_minoritarios_e_reserva_so_sem_evidencia`; F2A-43, `test_sem_indice_nao_usa_o_mapa_manual` e `test_ticker_fora_do_indice_sem_motivo`; F2A-44, `test_relatorio_mostra_documento_e_escala_do_lpa_e_do_vpa` e a reformulação do teste do BUG-2A-09 (a asserção passou do HTML inteiro para a linha do LPA). Todos afirmavam o comportamento que o bug descreve; nenhum foi removido.

### Estado de cada bug (`tests/regressao/README.md`)

| ID | Corrige | Estado |
|---|---|---|
| BUG-2A-01 (≤ 0 da CVM descartado no merge) | F2B-8 | aberto |
| BUG-2A-02 (sem correspondência libera reserva) | F2A-41 | corrigido |
| BUG-2A-03 (ausente com minoritários no balanço) | F2A-41 | corrigido |
| BUG-2A-04 (2.03.09 só no modelo do setor) | F2A-41 | corrigido |
| BUG-2A-05 (PL total inválido sem motivo) | F2A-41 | corrigido |
| BUG-2A-06 (P/VP não finito no FII) | F2A-42 | corrigido |
| BUG-2A-07 (fora do índice recebe métodos) | F2A-43 | corrigido |
| BUG-2A-08 (rastreabilidade: P/VP = 1,0) | F2A-44 | corrigido |
| BUG-2A-09 (rastreabilidade: LPA = lucro ÷ ações) | F2A-44 | corrigido |
| BUG-2A-10 a 18 (TTM sem 7.2; alerta antes da coerência; FII sem `valores_por_fonte`; risco "fora da CVM" no FII; Informe sem desempate por versão; DY inválido sobrescreve válido; ZIP vazio do COTAHIST; `FiiNav` com P/VP ≤ 0; `Graham` com VPA < 0) | proposta da 2B | aberto |

### Correções deste resumo apontadas pelas auditorias

- **"Efeito nulo hoje" do F2A-13 (item 8 das decisões pendentes) não vale para o relatório de qualidade.** Com a fonte `fundamentus` fora de `_FONTE_CONFIANCA`, um registro antigo com `fonte_fundamentos = "fundamentus"` cai no padrão de 10 (`data_quality.py:164`): com os dez campos esperados presentes, a confiança por campo e o `score_confianca` vão de **40 para 10** (conferido rodando `DataQualityReport.completude()` com o `data_quality.py` de `b1322e1~1` e o atual). O efeito sobre os números dos motores segue nulo.
- **"ROE negativo passa" (F2A-4 e F2A-30) depende da fonte (BUG-2A-01).** A fronteira não tem piso, mas o merge descarta ROE ≤ 0. Conferido na cascata com as fixtures da suíte: ROE −0,05 só do yfinance fica, mas conta como campo obrigatório faltando; com yfinance 0,10 e brapi −0,05, fica 0,10; com yfinance 0,10 e CVM −0,05, fica 0,10.
- **"76 módulos de teste" estava certo.** A 2ª passada do Gemini disse 75, supondo que o F2A-13 apagou `tests/test_cvm_ticker_map.py`; o F2A-13 tirou 12 testes do arquivo, mas o arquivo continua rastreado (`git ls-tree -r c05f4ed tests/`: 76 arquivos `test_*.py`). Depois do fechamento são 94.

### Pendências para o Marcos (das revisões deste fechamento)

1. **`CLAUDE.md` desatualizado:** armadilha 14 ("fora do índice, `classe_ativo` não é gravado […] o guard do motor não atua") e a linha do `valuation_engine.py` na tabela de arquitetura, depois do F2A-43; a seção "Bugs e regressão" entrou no `AGENTS.md` e no protocolo, mas não no `CLAUDE.md`, de que o `AGENTS.md` deveria ser subconjunto. Pede item próprio.
2. **Relatório de rastreabilidade:** a nota "ausente: a lente de P/VP se abstém" só aparece com P/VP `None` ou 0; com NaN, infinito ou negativo o motor também se abstém, mas a nota não aparece (a condição é anterior ao F2A-44). Na unit, o texto do VPA não diz que o VPA é multiplicado pelas ações da unit.
3. **Testes de regressão:** os xfail não usam `raises=` (uma mudança de assinatura de helper passaria por "bug aberto"); no BUG-2A-10 a leitura de `valores["lucro_controladores"]` é com `[]` (uma correção por abstenção que não grave a chave daria `KeyError`); o BUG-2A-16 fixa a semântica "mês ausente".
4. **Itens da 2B e da 2C:** o BUG-2A-17 contradiz dois casos de `tests/test_methods_fii_nav.py::test_faixa_pelos_limites_estritos_da_v1` (0,0 e −1,0 como desconto), que o item que o corrigir precisa listar; o teste do BUG-2A-07 lê `recomendacao`, e o F2C-4 deve listá-lo.
5. **Limites conhecidos das correções:** fora do índice, ticker que não termina em 11 (ex.: BDR) segue `STOCK` e recebe os métodos de ação; com a 2.03.09 ilegível, o lucro dos controladores se abstém com o motivo "com não controladores no balanço"; a união dos pares de todos os modelos pode transformar uma 2.03.09 de outra conta num banco em "sem correspondência" (nenhum dos 12 bancos da DFP 2025 é afetado: o levantamento do F2A-41 não achou companhia que mude de lado).
