# Fila do loop — Fase 2A (Dados corretos)

> **Proposta, não ativa.** Escrita no F1-19 pelo `fable-architect`. Quem a coloca em `docs/loop/fila.md` é o Marcos, depois de aprovar, responder às decisões marcadas e cumprir as condições de ativação.

Branch: `v2/fase-2a` · Protocolo: `docs/loop/protocolo.md` · Diário: `docs/loop/diario.md`
Plano: `docs/PLANO.md` (seção 6, "Fase 2A"; seções 8, 10 e 11) · Decisões: `docs/decisoes/checkpoint-fase0.md`, `docs/adr/0001-refactor-v2.md` e `docs/adr/0002-loop-tempo-dados.md`
Auditoria: `docs/auditoria/2026-09-red-team.md` · Dossiê: `docs/decisoes/dossie-fase2.md` · Inventário: `docs/limpeza/inventario.md` · Jules: `docs/jules-backlog.md` · Fase 1: `docs/loop/historico/fase-1/`

**Condições de ativação** (todas, antes do `git mv`):
1. Fase 1 integrada na `main`, com a tag `v2-fase-1`. A invalidação do cache pedida no diário do F1-15 já foi rodada pelo Marcos, porque o script sai no F2A-13.
2. Mergeados na `main` os tickets do Jules:
   - B4.1, B4.2 e B4.3, em `cvm_provider.py` e `cvm_fii_provider.py`;
   - C-D, em `data_quality.py`.

   A fila parte do que eles entregam:
   - o parser único com escala (B4.1);
   - a maior `VERSAO` por (CNPJ, `DT_REFER`), com `cvm_dt_refer` e `cvm_versao` em `dados` (B4.2);
   - o módulo compartilhado de download atômico (B4.3).
3. Respondidas neste arquivo:
   - a regra do golden;
   - a **[LIQUIDEZ]** (sem resposta, o F2A-10 sai da fila);
   - a **[CORREÇÕES]** (sem resposta, vale o estado atual).
4. Ativação (PLANO, seção 7): `git switch -c v2/fase-2a main`, `git mv -f docs/loop/fila-fase2a-proposta.md docs/loop/fila.md` e `git commit -m "chore: activate phase 2A queue"`.
5. O Marcos troca a seção "Fase atual" do `AGENTS.md` pelo texto abaixo. O loop nunca toca nessa seção.

```
**Fase 2A — Dados corretos.** O mantenedor trabalha num branch local por fase e só
publica no fim de cada fase. Baseie seu branch sempre na `main` mais recente.

Arquivos travados enquanto esta fase estiver em andamento. Não abra PR que toque
em nenhum deles:

market_engine.py  cvm_provider.py  cvm_fii_provider.py  cvm_ticker_map.py  cvm_fii_map.py
fii_engine.py  valuation_engine.py  brapi_provider.py  data_quality.py  config.py
fundamentus_scraper.py  ai_core.py  requirements.txt
sentinela/data/  sentinela/domain/  sentinela/methods/  sentinela/services/  sentinela/reports/
scripts/  tests/conftest.py  tests/fixtures/  tests/golden_motores.py
tests/test_market_engine*.py  tests/test_cvm_*.py  tests/test_fii_engine*.py
tests/test_valuation_engine*.py  tests/test_brapi_provider.py  tests/test_data_quality*.py
tests/test_asset_classifier*.py  tests/test_fundamentus_scraper.py  tests/test_ai_core.py
tests/test_methods_*.py  tests/test_registry.py  tests/test_rastreabilidade.py

Tickets com janela nesta fase: B1, B3, C-A, C-B e C-C. O B2 está cancelado (o scraper
sai nesta fase). O C-E perdeu a janela se não foi mergeado na Fase 1.
```

**Linhas citadas.** São de 2/10/2026, e só em arquivos que nem o F1-13 nem o Jules mexem antes da ativação: `market_engine.py`, `fii_engine.py`, `config.py`, `brapi_provider.py`, `app.py` e `portfolio_engine.py`. Nos demais arquivos, a fila cita a função.

**Comportamento.** Esta fase corrige dados, então muda número e texto na saída.
- Cada mudança tem um item `fix:` próprio, com teste xfail estrito antes (XPASS, depois marca retirada), e nunca divide o commit com refactor.
- Os itens `feat:` acrescentam dado sem mudar a saída dos motores. O único refactor (F2A-17) não muda nada.
- Saída dos motores muda (e por isso o golden) só nos itens marcados **[golden]**: F2A-22, F2A-4, F2A-11, F2A-23, F2A-24, F2A-25, F2A-10 e F2A-13 (este, só com remoções).
- Os demais itens mudam a cascata (`dados`), o relatório de qualidade ou o relatório do F1-12.

**IDs e ordem.** Os itens F2A-1 a F2A-14 mantêm o significado da tabela do PLANO; os novos são F2A-15 a F2A-28. A execução segue a ordem da lista, não a numérica:
1. ferramenta do golden e cache da CVM;
2. COTAHIST e levantamento das fontes;
3. dados de referência e os consumidores deles;
4. E-1, E-3 e E-2;
5. séries de cinco anos, dívida líquida, saída do Fundamentus e bancos;
6. DY;
7. FII;
8. abstenções nos motores;
9. ticker;
10. liquidez;
11. documentação, proposta da 2B, limpeza e resumo.

**Intocáveis nesta fase:**
- `tests/test_financeiro_pre_refactor.py`. A seção A nunca muda. A B muda só no F2A-8 (`test_b_divida_pl_da_cvm_e_endividamento_contabil_total_rotulado_como_liquido`). A C muda só no F2A-4, com a retirada do xfail de `test_c_dy_percentual_acima_de_30_nao_pode_sair_confiavel`.
- `tests/fixtures/golden_motores.jsonl` e `tests/golden_motores.py`: só nos itens **[golden]**, pela regra abaixo. `tests/test_equivalencia_motores.py` não muda.
- `config.py`, em três partes:
  - `_normalizar_dy` muda só no F2A-4, e é a única mudança do arquivo na fase;
  - o `MacroContext` não muda: é a fonte única dos parâmetros da V1 até o F3-1 e das ids do golden;
  - `FII_MANUAL_FALLBACK` fica sem leitor no F2A-23 e sai no F2C-10, com as outras constantes de `config.py` sem leitor.
- `app.py` (Fases 3 e 7) e `portfolio_engine.py` (F2C-9) não mudam. O que o app precisa mostrar chega pela cascata (`dados`, `riscos_dados`) ou pelos motores.
- Itens que podem mexer em cada arquivo restrito:
  - `valuation_engine.py`: F2A-22, F2A-4, F2A-24 e F2A-10;
  - `fii_engine.py`: F2A-4, F2A-11, F2A-23, F2A-24, F2A-10 e F2A-13;
  - `sentinela/methods/`: F2A-21 (Bazin 1.0.1), F2A-25 (Gordon 1.1.0) e F2A-13 (flag `erro_scraper` do `MethodInputs`). O contrato de pureza do F1-10 vale para tudo.
- Os singletons dos motores (`_GRAHAM`, `_BAZIN`, `_LYNCH`, `_GORDON`, `_FII_YIELD`, `_FII_NAV`): o relatório do F1-12 depende deles. Nenhum item os renomeia sem atualizar `sentinela/reports/rastreabilidade.py` no mesmo commit. O ponto de extensão público é do F2C ou do F3.
- Arquivos dos tickets do Jules com janela nesta fase: `peers_engine.py` e `tests/test_peers_engine.py` (C-C), `database.py` (o B3 só cria `tests/test_database_posicoes.py`), `technical_engine.py` (B1), `README.md` (C-A) e `.env.example` (C-B). Nenhum item os toca.
- Teste existente só muda onde o item manda; a lista está em cada item, e a justificativa, no diário.

**Regra do golden** (proposta; decisão do Marcos, item 6 do checkpoint da Fase 1). O gate da Fase 1, de commit único no golden, cai.
- Item **[golden]** regenera com `GERAR_GOLDEN=1 python -m pytest tests/test_equivalencia_motores.py::test_gerar_golden`, no mesmo commit da mudança.
- `python scripts/golden_diff.py --onde "<predicado do item>"` (F2A-15) sai com 0: toda linha alterada satisfaz o predicado. Inclusões e remoções, só onde o item declara.
- O diff do golden é a evidência do escopo. O diário traz o predicado, a contagem e os ids (até 50; acima disso, a contagem por grupo).
- Item sem **[golden]**: `git diff --exit-code HEAD -- tests/fixtures/golden_motores.jsonl` antes do stage.
- As ids dependem das constantes do `MacroContext`, que o harness lê. Como ele não muda nesta fase, as ids ficam estáveis.

**Gate da fase (todo item):**
- `git diff v2-fase-1 -- tests/test_financeiro_pre_refactor.py` mostra só as duas mudanças previstas, depois dos itens que as fazem;
- o golden segue a regra acima;
- `python -m pytest -q` e `ruff check --select E9,F63,F7,F82 .` verdes;
- mutação:
  - módulos novos de `sentinela/data/`, `sentinela/domain/ticker.py` e `sentinela/services/asset_classifier.py`: ≥ 80% no item que os cria ou altera;
  - `sentinela.methods*`: ≥ 80% depois do F2A-21 e do F2A-25 (hoje está em 100%);
  - módulos V1 tocados: o score vai para o diário, sem meta.

**Gate de refactor (F2A-17):** o gate da fase, o golden e as seções inalterados, e nenhum teste existente alterado: `git diff --cached --name-status -- tests/` só mostra `A`.

**Rito dos dados:**
- **Onde fica o código.** Lógica nova de dados vira função pura em `sentinela/data/`, e o `market_engine.py` só orquestra. Os provedores da raiz ficam onde estão.
- **Isolamento.** Os módulos novos não importam `config`, que faz rede no import (armadilha 8). O teste do F1-10 já impede `sentinela/methods/` de importar `sentinela/data/`.
- **Download.** Com cache em `data/` (ignorado pelo git), com TTL e pelo módulo compartilhado do B4.3. Se a rede falha, vale o cache existente, com aviso. Nada de rede no import.
- **Testes.** Sem rede, com arquivos sintéticos em `tmp_path` montados pela especificação oficial (dicionário de dados da CVM, layout da B3), nunca a partir de valor calculado pelo código.
- **Provedor novo no `MarketEngine`.** Entra por atributo lido com `getattr(self, ..., None)`, como o `cvm` (`market_engine.py:477`). Assim, os testes que montam o motor com `__new__` não mudam.
- **Prompt.** Bloco estruturado novo em `dados` (dicionário ou série) entra, no mesmo item, na lista `excluir` de `_formatar_dados` do `ai_core.py`. Chave escalar nova pode aparecer no prompt.
- **Rede.** Só de leitura (CVM, B3, BCB, yfinance), só no levantamento ou na verificação descrita no item, nunca em teste.
- **Tempo.** Código novo recebe a data de referência como parâmetro; só o ponto de entrada da V1 lê o relógio. `analisar(ticker, as_of)` e o `date.today()` dos motores ficam para o F3-6.

**Paralelo do Jules (o loop não executa nenhum ticket nem toca nos arquivos deles):**
- B4.1 a B4.3 e C-D: condição de ativação.
- B1, B3, C-A, C-B e C-C seguem em paralelo. Nenhum item desta fila toca `technical_engine.py`, `database.py`, `README.md`, `.env.example`, `peers_engine.py` nem os testes deles.
- B2: cancelar. O próprio ticket manda cancelar se o scraper sair, e ele sai no F2A-22.
- C-E: a janela era a Fase 1. Se não foi mergeado, cancelar: a 2A trava `config.py`, e o F2A-2 traz o segmento oficial dos FIIs.
- Grupo A: revisão do PR da fase, no checkpoint.

**Decisões:**
- **[P1]**, **[P5]**, **[P6]** e **[P7]**: perguntas do dossiê respondidas no checkpoint da Fase 0 (seção 4). O item segue a resposta. As leituras que a fila adota e o efeito de cada resposta diferente estão na última seção.
- **[D7]**: aceita no checkpoint (Composição do Capital e COTAHIST).
- **[LIQUIDEZ]**: limiar em aberto.
- **[CORREÇÕES]**: tabela de correções de fonte.
- **[golden]**: o item regenera o golden pela regra acima.

**Privacidade:** o repositório é público. Nenhum dado da carteira do Marcos (posições, pesos, lista de ativos) entra em arquivo versionado: nem em fixture, nem no golden, nem no diário, nem nos documentos de levantamento.
- Fixtures usam tickers genéricos (`TST3`, `TST11`) ou os dos mapas públicos do código.
- Scripts desta fila nunca leem a carteira.

**Vocabulário:** nunca "recomendação", "compra" ou "venda" em código novo, tabela, coluna, chave de `dados` ou texto de risco. Os rótulos da V1 (COMPRA/NEUTRO/VENDA) ficam até o F2C-4.

Legenda: `[ ]` pendente · `[x]` feito · `[!]` bloqueado · `[DECISÃO]` o loop para aqui

## Itens

- [ ] **F2A-15** · chore · `chore: add golden diff tool for scoped regeneration`
  A partir desta fase, o golden muda nos itens que mudam saída. Este item cria a ferramenta que prova o escopo de cada mudança: `scripts/golden_diff.py`.
  - **Comparação.** Por (motor, id), entre o golden do `HEAD` (`git show`) e o da árvore de trabalho. Lista os casos alterados, incluídos e removidos. `--base <arquivo>` troca o `HEAD` por um arquivo.
  - **`--onde "<expressão>"`.** Sai com 1 se algum caso alterado não satisfizer a expressão, avaliada com `caso`, `entrada`, `saida_antiga` e `saida_nova`.
  - **`--par "<antigo>=<novo>"`.** Pareia removidos e incluídos cujo id só difere pelo trecho e mostra a diferença das saídas. Serve ao item que renomeia uma chave da grade.
  - Não roda o gerador, não altera o golden e não traz dependência nova.

  **Aceite:**
  - `tests/test_golden_diff.py::test_lista_alterados_incluidos_e_removidos`, `::test_onde_falha_com_caso_fora_do_predicado` e `::test_par_compara_casos_renomeados`, com `--base` e arquivos em `tmp_path`;
  - rodado sem mudança no golden, lista zero casos;
  - gate da fase.

- [ ] **F2A-17** · refactor · `refactor: cache parsed CVM statements per file`
  **Por quê.** E-16: cada `calcular_indicadores` relê os CSVs completos do ZIP. O F2A-3, o F2A-7 e o F2A-8 multiplicam as leituras (cinco anos, ITR, Composição do Capital, DVA), e o `peers_engine` dispara análises em paralelo.

  **O que muda:**
  - memoização, por processo, do DataFrame já filtrado de cada (arquivo, tipo), só com as colunas usadas;
  - a chave inclui o `mtime` e o tamanho do ZIP, então download novo invalida a entrada;
  - trava por chave, para duas threads não lerem o mesmo arquivo;
  - limite de entradas;
  - nada de Parquet nem dependência nova.

  Mesmos valores e mesmas exceções de antes.

  **Aceite:**
  - gate de refactor;
  - `tests/test_cvm_provider_cache.py::test_segunda_leitura_nao_rele_o_csv` e `::test_zip_novo_invalida_o_cache`;
  - diário: tempo de `calcular_indicadores(cd, anos=5)` para um ticker do mapa público, com os ZIPs já em `data/cvm/`, antes → depois, e a memória do processo.

- [ ] **F2A-18** · feat · `feat: add B3 COTAHIST provider` · **[D7]** **[P6]**
  Cria `sentinela/data/__init__.py`, `sentinela/data/providers/__init__.py` e `sentinela/data/providers/b3_cotahist.py`. É aditivo: os consumidores são o F2A-1 e o F2A-26.
  - **Especificação externa:** o layout oficial das Séries Históricas da B3, citado no módulo. Vale o registro 01 (cotação); o 00 e o 99 são ignorados.
  - **Campos por registro:**
    - data, código de negociação, `CODBDI`, tipo de mercado, especificação (`ESPECI`) e ISIN;
    - fechamento bruto, volume financeiro, quantidade e negócios;
    - preços e volume com as duas casas implícitas e o fator de cotação aplicado.
  - **Download do arquivo mensal,** com cache em `data/cotahist/`: o mês corrente expira em um dia; os meses fechados não expiram. O mês é parâmetro, e o parser não lê relógio.

  **Aceite:**
  - `tests/test_cotahist.py::test_registro_01_segue_o_layout_oficial`, `::test_fator_de_cotacao_mil`, `::test_header_e_trailer_ignorados` e `::test_filtra_mercado_a_vista`, com linhas sintéticas montadas pelo layout, sem rede;
  - mutation ≥ 80% em `sentinela.data.providers.b3_cotahist*`;
  - gate da fase.

  O download real fica no F2A-16, que registra o resultado. Um COTAHIST inacessível não para este item.

- [ ] **F2A-16** · levantamento · `docs: survey official sources for phase 2A`
  Confere nos arquivos reais os fatos de que os itens seguintes dependem. Grava `docs/decisoes/fontes-fase2a.md` e `scripts/levantamento_fase2a.py`.
  - **Rede e cache.** Rede só de leitura, com cache em `outputs/levantamento_cache/`. O script não importa `config` e não usa token da brapi (o loop não lê `.env`).
  - **Amostra.** Tickers dos mapas públicos do código, nunca a carteira.
  - **Formato.** Cada pergunta traz a evidência (arquivo, coluna, amostra) e a consequência para o item afetado.

  As perguntas:
  1. **FCA (F2A-1, F2A-3):**
     - colunas do `valor_mobiliario` e valores de `Valor_Mobiliario`;
     - se há composição das units (ações ON e PN por unit) e ISIN;
     - códigos de negociação fora do formato de ticker (a CSN usa `4030`, o próprio CD_CVM);
     - códigos sem data de fim que não negociam no COTAHIST (BRML3 e outros).
  2. **Escala da Composição do Capital (F2A-3, F2A-5; armadilha 10):**
     - a regra de escala aplicada às 38 ações da seção 1 do dossiê: a escala certa é a que aproxima lucro ÷ ações do LPA básico divulgado no mesmo documento (DRE, conta 3.99);
     - quantas ela determina e o confronto com a escala que o dossiê inferiu pelo yfinance;
     - se a linha 3.99 passa pela `ESCALA_MOEDA`;
     - a distribuição da diferença entre o LPA calculado e o divulgado.
  3. **DFP e ITR (F2A-7, F2A-8):**
     - subcontas de empréstimos, debêntures e arrendamento do passivo, e de caixa e aplicações do ativo;
     - códigos da DVA para depreciação e amortização e para dividendos e JCP, e se são estáveis entre companhias do modelo comum;
     - no ITR, como separar o trimestre do acumulado, e se a Composição do Capital vem nele.
  4. **Bancos e seguradoras (F2A-8, F2A-9):**
     - contas de PL e de lucro no modelo de instituição financeira (os 3 bancos do dossiê e os demais do setor);
     - valores de `SETOR_ATIV` de bancos e de seguradoras.
  5. **IF.data (F2A-9):**
     - uma chamada de controle a um relatório que responda;
     - os relatórios de capital (Basileia) e de carteira por nível de risco;
     - como achar a instituição a partir do CNPJ.
  6. **COTAHIST (F2A-1, F2A-26):**
     - URL e download real de um mês, com contagem de registros;
     - valores de `ESPECI` para ações, units, cotas de fundo e BDRs;
     - se algum dado oficial separa ETF de outro fundo listado.
  7. **Informe Mensal de FII (F2A-1, F2A-2):**
     - colunas de ISIN, mercado e segmento;
     - cobertura da junção pelo ISIN do COTAHIST e da reserva pela regra do ISIN;
     - os 3 FIIs do mapa manual fora dos listados em bolsa (dossiê, seção 7).
  8. **Representação do DY (F2A-4):**
     - yfinance: versão instalada, e `dividendYield` contra proventos de 12 meses ÷ preço em tickers públicos;
     - brapi: pela documentação pública;
     - `Percentual_Dividend_Yield_Mes` do Informe Mensal, só como registro.
  9. **Liquidez (insumo da [LIQUIDEZ]):**
     - volume financeiro diário mediano, negócios e presença em 21 e 63 pregões, separados entre ações, units e FIIs;
     - quantos ativos ficam abaixo de R$ 100 mil, 500 mil, 1 milhão e 5 milhões por dia, e de 80%, 90% e 95% de presença.

  **Aceite:**
  - cada uma das nove perguntas respondida ou marcada "não determinado", com a consequência escrita para o item afetado, sem decidir nada novo;
  - script reproduzível;
  - nenhum módulo de produção alterado;
  - gate da fase.

- [ ] **F2A-1** · feat · `feat: build official reference of tickers, issuers and asset classes` · **[P6]** **[P7]**
  Cria `sentinela/data/referencia/`: lê os arquivos oficiais, monta o índice ticker → registro e o grava em `data/referencia/indice.json`. É aditivo: os consumidores são o F2A-19 e o F2A-20.

  **Regras:**
  - **Companhias.**
    - Para cada CNPJ vale o FCA mais recente entregue: o do ano corrente, ou o anterior se o do ano ainda não foi entregue. Dele entram os códigos sem data de fim.
    - CNPJ → CD_CVM pelo cadastro, registro ativo primeiro (a regra de `cd_oficial` do dossiê).
    - `Valor_Mobiliario` dá a classe: ação ordinária ou preferencial vira `STOCK`, com a espécie (ON ou PN); unit vira `UNIT`, com as ações por unit quando o F2A-16 as achar no FCA.
  - **FIIs [P6].** Junção do Informe Mensal (`Mercado_Negociacao_Bolsa = S`) com o COTAHIST pelo ISIN. Quando o ISIN não aparece no COTAHIST, vale a reserva: letras 3 a 6 do ISIN + "11", marcada no registro.
  - **BDR e ETF [P7].** Pelo dado oficial que o F2A-16 achar. Cota de fundo listada que não é FII nem ETF identificado vira `UNKNOWN`, com o motivo. Nunca pelo sufixo.
  - **Exceções.** Código fora do formato de ticker vai para a lista de exceções, com o motivo. O tratamento é do F2A-19 e da **[CORREÇÕES]**.
  - **Registro.** Ticker, classe, espécie, CNPJ, CD_CVM (companhias), nome, ações por unit, regra usada e fonte (arquivo e data).
  - **Montagem e download.** A montagem é função pura dos arquivos. O download tem cache e TTL; se a rede falhar, vale o índice salvo, com aviso.

  **`CVMTickerMap` não é consertada.** Só os testes a instanciam, `_seed_manual_map` usa `INSERT OR IGNORE` e não corrige linha velha, e `refresh` nunca preenche `ticker`. O índice a substitui, e ela sai no F2A-13.

  **Cobertura (gate do PLANO).** `python -m sentinela.data.referencia --cobertura`, sobre os arquivos reais, mostra mapeáveis e mapeados por grupo:
  - companhias: códigos ativos no FCA;
  - FIIs: listados em bolsa, mapeados pela junção ou pela reserva.

  Ordem de grandeza esperada (dossiê, seção 7): 482 tickers de 366 companhias e 710 FIIs.

  **Diário:**
  - a cobertura e as exceções;
  - os tickers que saíram do mapa no F1-15 (CSNA3, BRFS3, EMBR3, CPLE6, SOMA3) e os `fca_2025` (JBSS3, ELET3, NTCO3, AZUL4, PETZ3), cada um com a situação no índice e o ticker que o FCA aponta hoje para a mesma companhia (ticker novo depois de evento societário);
  - BRML3;
  - as units, com as ações por unit (KLBN11: 1 ON + 4 PN, se o FCA confirmar), e BRBI11 e IGTI11, que o classificador trata como FII;
  - o `cvm_fii_map.py` conferido pela junção e pela regra do ISIN, e os 3 FIIs dele fora dos listados;
  - toda divergência entre os mapas manuais e o índice.

  **Aceite:**
  - `tests/test_referencia.py`, com arquivos sintéticos em `tmp_path`, sem rede:
    - `::test_codigo_ativo_no_fca_mais_recente_entra`;
    - `::test_codigo_com_data_de_fim_sai`;
    - `::test_fca_do_ano_anterior_vale_se_o_atual_nao_foi_entregue`;
    - `::test_fii_pelo_isin_do_cotahist`;
    - `::test_fii_pela_reserva_do_isin_fica_marcado`;
    - `::test_unit_tem_classe_unit`;
    - `::test_cota_de_fundo_sem_informe_vira_unknown`;
    - `::test_codigo_fora_do_formato_vai_para_excecoes`;
    - `::test_indice_grava_e_le_igual`;
  - mutation ≥ 80% em `sentinela.data.referencia*`;
  - cobertura de 100% dos mapeáveis, ou cada exceção com motivo no diário;
  - gate da fase.

- [ ] **F2A-2** · feat · `feat: add sector, FII segment and control type to the reference`
  Acrescenta ao índice, a partir de arquivos que o projeto já baixa:
  - o setor (`SETOR_ATIV` do cadastro);
  - a espécie de controle acionário (do cadastro ou do FCA, conforme o F2A-16);
  - o segmento do FII (`Segmento_Atuacao` do Informe Mensal).

  O "grupo de controle" do PLANO, aqui, é a espécie de controle, que o arquivo oficial traz. Quem controla (grupo econômico, para a concentração do F4-7) está no Formulário de Referência, que o projeto não baixa, e fica fora da fase.

  Nenhum cálculo lê esses campos nesta fase:
  - o setor define o conjunto de bancos e seguradoras do F2A-8 e do F2A-9;
  - o segmento é insumo da 2B e do F2C-7, e não substitui o `tipo` que o motor de FII exibe.

  **Aceite:**
  - `tests/test_referencia_atributos.py::test_setor_do_cadastro`, `::test_segmento_do_informe_mensal` e `::test_especie_de_controle`;
  - mutation ≥ 80% em `sentinela.data.referencia*`;
  - diário com os valores distintos de setor e de segmento;
  - gate da fase.

- [ ] **F2A-19** · fix · `fix: resolve CVM codes and asset data from the official reference` · **[CORREÇÕES]**
  A cascata passa a ler o índice. O mapa manual de `cvm_ticker_map.py` vira fallback, usado só quando o índice não tem o ticker ou não está disponível.
  - **Registro em `dados`.** No começo de `buscar_dados_ticker`, o registro do ticker entra em `dados`, com a fonte: `classe_ativo`, `especie`, `cnpj`, `cd_cvm`, `setor`, `segmento_fii`, `controle_acionario` e `acoes_por_unit`.
  - **CD_CVM.** `_buscar_cvm` usa o do índice; sem ele, o do mapa manual (`market_engine.py:481`). Sem nenhum dos dois, `riscos_dados` ganha "ticker fora da cobertura da CVM". Isso fecha o F-30 sem tocar no `app.py`, que já exibe `riscos_dados`.
  - **Ticker fora do índice.** `riscos_dados` ganha "ticker fora da referência oficial", com o motivo quando houver (negociação encerrada, por exemplo).
  - **Carga.** O índice carrega uma vez por processo, com trava, porque o `peers_engine` usa threads. Recarrega quando o TTL vence.
  - **[CORREÇÕES].**
    - Aprovada: `sentinela/data/referencia/correcoes.csv` (ticker, CNPJ, motivo, evidência oficial) corrige defeito de fonte documentado, como a CSNA3, e entra no índice como regra própria.
    - Sem aprovação: o item segue sem tabela, que é o estado atual. A CSNA3 continua fora da CVM, agora com o motivo em `riscos_dados`. Nenhum código é inventado.

  **Aceite:**
  - `tests/test_market_engine_referencia.py::test_ticker_fora_do_mapa_manual_recebe_cvm_pelo_indice` passa por xfail estrito → XPASS;
  - `::test_sem_indice_usa_o_mapa_manual`, `::test_ticker_fora_da_cvm_tem_motivo_em_riscos_dados` e `::test_registro_do_indice_entra_em_dados`;
  - nenhum teste existente muda;
  - diário: os tickers do mapa público cujo código vem do índice, e as diferenças em relação ao mapa manual (esperado: nenhuma);
  - gate da fase.

- [ ] **F2A-20** · fix · `fix: classify assets from official data instead of ticker suffix` · **[P7]**
  `sentinela/services/asset_classifier.py` deixa de deduzir a classe do sufixo (armadilha 14, E-9). A ordem de consulta passa a ser:
  1. `dados['classe_ativo']`, que a cascata preenche desde o F2A-19. É o caminho do `app.py:216`, que não muda;
  2. o índice local, lido sem rede na primeira consulta, para quem chama sem `dados` (`portfolio_engine.py:114-115`);
  3. `FIIS_CONHECIDOS` e `UNITS_CONHECIDAS`, como fallback sem índice;
  4. `UNKNOWN`.

  Também:
  - **Regras que saem:** a do sufixo "11" e a do `quoteType` `MUTUALFUND`. O yfinance não é fonte oficial e devolve `EQUITY` para FII.
  - **Testes isolados:** os testes nunca leem o índice da máquina. O diretório de dados vem de uma variável de ambiente, que o `tests/conftest.py` aponta para uma pasta temporária.
  - **`applies_to`:** continua só declarado (F2B-4). Até lá, ETF, BDR e `UNKNOWN` deixam de ser FII e caem no motor de ações pelo `app.py`, que só distingue FII. O resultado continua sem sentido para eles, como hoje (risco na última seção).

  **Testes que mudam.** Passam a afirmar a regra nova; os demais casos não mudam:
  - `tests/test_asset_classifier.py::test_suffix_11_classifies_as_fii_when_not_unit` e `::test_mutualfund_quote_type_classifies_as_fii`;
  - em `tests/test_asset_classifier_equivalence.py`, os casos que fixam o sufixo e o `MUTUALFUND` (ABCD11 e variações, ABCD3 com `MUTUALFUND`);
  - `tests/test_market_engine.py::test_market_engine_suffix_11_non_unit_still_fii`.

  **Aceite:**
  - passam por xfail estrito → XPASS, com `dados` da cascata ou índice falso: `tests/test_asset_classifier_oficial.py::test_etf_nao_e_fii`, `::test_unit_fora_da_lista_e_unit` (BRBI11, IGTI11), `::test_fii_fora_da_lista_e_fii_pelo_indice` e `::test_sufixo_sozinho_nao_define_classe`;
  - `::test_testes_nao_leem_o_indice_local`;
  - mutation ≥ 80% em `sentinela.services.asset_classifier*`;
  - seções A, B e C intactas: o teste do Markowitz na seção B usa HGLG11, que segue FII pela lista;
  - gate da fase.

- [ ] **F2A-3** · fix · `fix: derive per-share figures from CVM share composition` · **[P1]** **[D7]**
  E-1 (armadilha 3). Esta é a decisão do checkpoint (seção 4, item 1):
  - **Ações.** As da Composição do Capital da DFP, ON + PN − tesouraria. Vêm do mesmo documento do lucro e do PL: mesmo CNPJ, `DT_REFER` e `VERSAO` (critério do B4.2).
  - **Escala** (armadilha 10). O CSV não traz a escala; vale a regra conferida no F2A-16. É unidade ou mil, a que deixar a razão (lucro ÷ ações) ÷ (LPA básico divulgado no mesmo documento) mais perto de 1, dentro da faixa que o F2A-16 mostrou separar os dois casos. A conversão passa por `QuantidadeAcoes` do `units.py`.
  - **LPA e VPA.** LPA = lucro ÷ ações e VPA = PL ÷ ações. P/L e P/VP usam o preço do próprio ticker. Para unit, LPA e VPA são multiplicados pelas ações por unit do índice.
  - **Abstenção só quando a própria CVM falha.** Isto é: falta a linha de Composição do Capital do documento, a escala fica indeterminada, o total de ações é ≤ 0, ou a unit não tem composição oficial.
    - A CVM não deriva LPA, VPA, P/L nem P/VP; os das outras fontes ficam, com a fonte deles.
    - `riscos_dados` registra o motivo.
  - **Divergência com o yfinance.** Alerta, nunca abstenção.
    - `dados['divergencia_acoes']` compara, por espécie, as ações da espécie do ticker na CVM (ON ou PN, menos a tesouraria da espécie) com o `sharesOutstanding` do ticker. Para unit, compara o total ÷ ações por unit.
    - O alerta acima de 5% aparece no relatório de qualidade a partir do F2A-5.
    - O `_shares_outstanding` deixa de entrar no cálculo (`market_engine.py:501-518`).
  - **Organização.** A lógica fica num módulo puro em `sentinela/data/`.
  - **Relatório do F1-12.** Troca o limite "E-1" e a proveniência de LPA e VPA (`LIMITES` e `PROVENIENCIA_DERIVADA`) pelo documento e pela escala usados.

  **Testes que mudam:** `tests/test_market_engine.py::test_cvm_computes_pl_pvp_from_shares`, que fixa a divisão pelo `sharesOutstanding`, e os testes do relatório que fixam o texto do E-1.

  **Aceite:**
  - `tests/test_market_engine_acoes_cvm.py::test_lpa_usa_on_mais_pn_menos_tesouraria` passa por xfail estrito → XPASS. A empresa sintética tem ON e PN, e o yfinance informa só a PN;
  - `::test_escala_em_milhares_vira_unidades`, `::test_escala_indeterminada_abstem`, `::test_documento_diferente_do_lucro_abstem`, `::test_unit_multiplica_pelas_acoes_por_unit`, `::test_divergencia_por_especie_e_registrada` e `::test_sem_composicao_mantem_multiplos_das_outras_fontes`;
  - mutation ≥ 80% no módulo puro;
  - diário: as 38 ações da seção 1 do dossiê, com ações, escala, divergência e LPA antes → depois;
  - golden inalterado;
  - gate da fase.

- [ ] **F2A-6** · fix · `fix: keep collected values intact for quality checks`
  E-3. O `app.py:236` faz `dados.update(analise)` antes do `DataQualityReport` (`app.py:264`) e da gravação. Como o `app.py` não muda nesta fase, a correção fica na cascata e no relatório de qualidade:
  - **Cópia na cascata.** No fim da cascata, `dados['valores_coletados']` guarda uma cópia dos campos de `FUNDAMENTAL_KEYS` e do preço, como a cascata os entregou: um dicionário simples, serializável.
  - **Relatório de qualidade.** `DataQualityReport` avalia a cópia quando ela existe. Os valores de `dados` só valem quando não existe cópia (testes e chamadas antigas).
  - **Gravação.** A análise gravada passa a levar a cópia, separada dos valores que os motores sobrescreveram.
  - **Prompt.** A cópia fica fora do prompt (rito dos dados).

  **Aceite:**
  - `tests/test_data_quality_retrato.py::test_saida_do_motor_nao_muda_o_que_o_relatorio_avalia` passa por xfail estrito → XPASS. O teste usa cascata falsa e depois um `dados.update` que sobrescreve `dy` e `pvp`, como o `app.py`;
  - `::test_retrato_e_serializavel_em_json`;
  - nenhum teste existente muda;
  - gate da fase.

- [ ] **F2A-5** · fix · `fix: cross-check per-share data against independent sources`
  E-2 (armadilha 2). Hoje a validação compara o P/L com preço ÷ LPA, mas no caminho da CVM o P/L é definido assim: a divergência é sempre zero. A validação passa a comparar fontes independentes:
  - **ações da CVM × yfinance:** a divergência do F2A-3 acima de 5% vira alerta (checkpoint, seção 4, item 1);
  - **LPA da cascata × LPA básico divulgado pela companhia** no mesmo documento (DRE 3.99): divergência acima de 10% vira alerta. É o limiar que a V1 já usa;
  - **checks 2 e 3 atuais** (P/L × preço ÷ LPA, P/VP × preço ÷ VPA): só rodam quando os dois lados vêm de fontes diferentes. Quando a CVM derivou os dois, são pulados, porque é identidade.

  Para comparar, a cascata guarda o que cada fonte entregou antes do merge, em `dados['valores_por_fonte']`, fora do prompt.

  **Aceite:**
  - `tests/test_data_quality_fontes.py::test_acoes_da_cvm_divergentes_do_yfinance_geram_alerta` passa por xfail estrito → XPASS. É o caminho da CVM em que o check atual não dispara;
  - `::test_lpa_divergente_do_divulgado_gera_alerta`, `::test_identidade_da_cvm_nao_e_comparada` e `::test_fontes_diferentes_seguem_comparadas`;
  - os testes atuais de `validacao_cruzada` não mudam;
  - gate da fase.

- [ ] **F2A-7** · feat · `feat: add five-year CVM series and trailing twelve months`
  F-24, F-8 e as janelas decididas no checkpoint (seção 4, item 4):
  - Bazin: dividendos médios de 5 anos;
  - Graham: LPA médio de 5 anos;
  - Lynch: CAGR de 5 anos;
  - Gordon: dividendo dos últimos 12 meses.

  Este item só disponibiliza os dados; quem passa a usá-los é o F2C-1.
  - **`dados['serie_cvm']`.** Até cinco exercícios da DFP, cada um com lucro, PL, receita, EBIT, ações e LPA e VPA do próprio documento (regras do F2A-3), e proventos declarados: dividendos e JCP da DVA, se o F2A-16 achou código estável. Sem código estável, a lacuna vai para o diário.
  - **`dados['ttm_cvm']`.** Lucro, receita e proventos dos últimos quatro trimestres pelo ITR (`baixar_itr`, hoje sem consumidor). O quarto trimestre é a DFP menos o acumulado de nove meses (PLANO). Traz data e versão de cada documento.
  - **Campos que alimentam os métodos.** Não mudam: continuam do exercício que a V1 usa hoje, e exercício mais antigo nunca vira corrente.
  - **Especificação externa.** Os metadados da DFP e do ITR que a CVM publica, e a aritmética do TTM. A data de referência é parâmetro, e a conta fica em função pura.

  **Aceite:**
  - `tests/test_cvm_series.py::test_serie_tem_ate_cinco_exercicios`, `::test_ttm_soma_quatro_trimestres`, `::test_quarto_trimestre_e_dfp_menos_nove_meses`, `::test_exercicio_antigo_nao_vira_corrente` e `::test_ttm_usa_a_versao_mais_recente`;
  - golden e seções A, B e C inalterados; nenhum teste existente muda;
  - mutation ≥ 80% no módulo puro;
  - diário: tempo da primeira análise e das seguintes, com o cache do F2A-17;
  - gate da fase.

- [ ] **F2A-8** · fix · `fix: measure leverage by net financial debt`
  F-12, armadilha 17 e o bug do checkpoint (seção 7).
  - **Medida.** Dívida financeira líquida = empréstimos e financiamentos (com debêntures, circulantes e não circulantes) − caixa e aplicações financeiras, do último DFP, com as contas que o F2A-16 conferiu.
    - `divida_liq_ebitda` = dívida líquida ÷ (EBIT + depreciação e amortização da DVA);
    - `div_liq_patrimonio` = dívida líquida ÷ PL.
  - **Abstenção.** Banco ou seguradora (setor do F2A-2), EBITDA ≤ 0 ou conta ausente: a CVM não entrega a medida, e `riscos_dados` registra o motivo.
  - **Fonte única.** `divida_liq_ebitda` passa a vir só da CVM. Os valores da brapi e do Fundamentus para esse campo saem da cascata, porque a definição deles não é conhecida (escolha de desenho, na última seção).
  - **`divida_pl`.** Passivo total menos PL, sobre o PL: deixa de ser mapeado para `div_liq_patrimonio`.
  - **Bug do checkpoint.** "Sem o dado, a penalidade de alavancagem se abstém."
    - O motor já não penaliza sem o dado: o 0,0 interno dá o mesmo número que não aplicar.
    - O que muda é a abstenção ficar visível: o relatório do F1-12 mostra "alavancagem não avaliada", com o motivo.
    - O motor e o golden não mudam.
  - **`data_quality.py`.** O comentário que diz que a CVM só fornece `div_liq_patrimonio`, e o `_CVM_CAMPOS`, passam a refletir a medida nova.

  **Seção B.** `test_b_divida_pl_da_cvm_e_endividamento_contabil_total_rotulado_como_liquido` passa a afirmar a correção. É reescrito primeiro como xfail estrito, depois XPASS, e a marca sai, com o comentário "resolvida no F2A-8". O teste do limite 3,0 em qualquer setor não muda.

  **Testes que mudam:** os de `tests/test_market_engine.py` que fixam `divida_pl` como `div_liq_patrimonio`, se houver (lista no diário).

  **Aceite:**
  - o teste da seção B, por xfail estrito → XPASS;
  - `tests/test_cvm_divida_liquida.py::test_divida_liquida_por_ebitda`, `::test_caixa_maior_que_divida_da_negativo`, `::test_banco_nao_recebe_medida`, `::test_ebitda_nao_positivo_abstem` e `::test_brapi_nao_preenche_a_alavancagem`;
  - `tests/test_rastreabilidade.py::test_alavancagem_ausente_aparece_como_nao_avaliada`;
  - mutation ≥ 80% no módulo puro;
  - golden inalterado;
  - gate da fase.

- [ ] **F2A-22** · fix · `fix: replace Fundamentus fallback with a missing-data check` · **[golden]**
  Decidido no checkpoint (seção 2):
  - o scraper sai depois do F2A-1 e do F2A-8;
  - o `cloudscraper` não é declarado;
  - `erro_scraper` vira checagem genérica de campos obrigatórios faltando, sem citar o scraper;
  - `roic` e `margem_bruta`, se fizerem falta, saem da DFP no F2C-2.

  O que o item faz:
  - **Cascata.** Perde o passo 4 (`market_engine.py:337-341` e o `self.scraper` da linha 196). `fundamentus_scraper.py` e `tests/test_fundamentus_scraper.py` saem com `git rm`, e `beautifulsoup4` sai do `requirements.txt`, porque só o scraper o usa.
  - **Flag nova.** A cascata grava `dados['fundamentos_incompletos']`: verdadeiro quando falta campo obrigatório depois de todas as fontes (a lista de `list_missing_required_fields`).
  - **Motor de ações.** O `valuation_engine` troca `erro_scraper` por `fundamentos_incompletos` nos dois pontos: a confiança −30 e o rebaixamento para "DADOS INSUFICIENTES — AGUARDAR". O risco passa a se chamar "Dados fundamentais obrigatórios ausentes". Números e rótulos da V1 não mudam.
  - **Efeito em produção.** O rebaixamento deixa de disparar quando o scraper falhava e outras fontes completavam os campos.
  - **Relatório do F1-12.** Troca a flag na lista de flags.
  - **`app.py`.** Continua lendo `erro_scraper` (o indicador "Erro Scraper" na linha 314 e a mensagem das linhas 325-329). É resíduo de arquivo travado, listado para o F3-6.
  - **Golden.** No harness, a chave `erro_scraper` da grade vira `fundamentos_incompletos`. `scripts/golden_diff.py --par "erro_scraper=fundamentos_incompletos"` e `--onde` mostram que a única diferença das saídas é o texto do risco.
  - **Jules.** B2 cancelado.

  **Testes que mudam:**
  - em `tests/test_market_engine.py`: `test_yfinance_data_is_preserved_when_fundamentus_fails`, `test_fundamentus_fills_only_missing_fields`, `test_scraper_failure_does_not_make_data_partial_when_brapi_complete` e o `FakeScraper` do helper `_engine`. Passam a afirmar a cascata sem o passo 4;
  - em `tests/test_valuation_engine.py`, os três que usam `erro_scraper`. Passam a usar a chave nova.

  **Aceite:**
  - `tests/test_cascata_sem_fundamentus.py::test_cascata_nao_chama_o_fundamentus` e `::test_campos_completos_nao_rebaixam_a_classificacao` passam por xfail estrito → XPASS;
  - `::test_campo_obrigatorio_faltando_rebaixa_como_antes`;
  - golden pela regra, com o diff descrito acima;
  - `deptry .` sem achado novo, e o `cloudscraper` some dos achados;
  - gate da fase.

- [ ] **F2A-9** · fix · `fix: read bank equity and earnings from the financial template` · **[P5]**
  Decidido no checkpoint (seção 4, item 5): os bancos terão lente própria, com P/VP justificado pelo ROE (F2B-3). Basileia e inadimplência são opcionais; quando faltam, a limitação é declarada. Nesta fase entram só os dados:
  - **Banco.** É a companhia com setor de banco no F2A-2. PL, lucro e ROE vêm das contas do modelo de instituição financeira que o F2A-16 conferiu, não das contas genéricas (F-13). No dossiê, o ITUB4 ficou sem lucro e PL utilizáveis. LPA e VPA seguem o F2A-3.
  - **Campos sem significado para banco.** Receita, margem e alavancagem não são preenchidas, com o motivo em `riscos_dados`.
  - **Basileia e inadimplência.**
    - Se o F2A-16 confirmou o IF.data com a chamada de controle: um provedor em `sentinela/data/providers/` grava `basileia` e `inadimplencia` em `dados`, com a fonte e a data-base.
    - Se não confirmou: o provedor não é escrito, e `riscos_dados` declara a limitação.
  - **Seguradoras.** Só a identificação pelo setor. A lente e a abstenção dos métodos são do F2B-3 e do F2B-4.

  **Aceite:**
  - `tests/test_cvm_bancos.py::test_banco_usa_contas_do_modelo_financeiro` passa por xfail estrito → XPASS;
  - `::test_banco_nao_recebe_margem_nem_alavancagem` e `::test_sem_ifdata_a_limitacao_e_declarada`;
  - se houver provedor, `::test_ifdata_grava_basileia_e_inadimplencia`, com resposta sintética e sem rede;
  - mutation ≥ 80% nos módulos puros;
  - diário: ROE, PL e lucro antes → depois para os bancos do mapa público;
  - golden inalterado;
  - gate da fase.

- [ ] **F2A-4** · fix · `fix: normalize DY once at the provider boundary` · **[golden]**
  E-4 e E-5 (armadilha 4). Hoje há três normalizadores em cascata:
  - `config._normalizar_dy` (`config.py:308-314`);
  - a divisão por 100 do yfinance (`market_engine.py:377-378`);
  - `_percent_to_decimal` da brapi, com `assume_subunit_percent` (`brapi_provider.py:35-43` e `:151-154`) e o corte acima de 0,30 (`:170-171`).

  O que o item faz:
  - **Um normalizador.** `sentinela/data/normalizacao.py`, puro e sem `config`. Converte pela representação declarada do provedor, via `Percent` e `Ratio` do `units.py`, e não valida.
  - **Representação por provedor.** yfinance e brapi, com a evidência do F2A-16 citada no código. Se o F2A-16 não determinou a de um provedor, vale para ele a regra da V1 (acima de 1 é percentual), declarada como inferência e marcada na proveniência do campo.
  - **Os outros dois saem.** Sai o trecho do yfinance. Da brapi, sai o tratamento de DY; `_percent_to_decimal` fica só para o ROE, sem o parâmetro que era do DY.
  - **`config._normalizar_dy`.** Vira só o invariante dos motores: devolve `(dy, True)` se 0 ≤ DY ≤ `DY_SANIDADE_MAX`, e `(0.0, False)` fora disso ou se não for finito. O nome fica porque a seção C o importa.
  - **Ajustes no mesmo item:**
    - os logs "DY normalizado" dos motores saem;
    - o texto do DY no relatório do F1-12 é atualizado;
    - `scripts/dossie_fase2.py` passa a usar o normalizador de fronteira para o yfinance.

  **Seção C.** `test_c_dy_percentual_acima_de_30_nao_pode_sair_confiavel` sai de xfail (XPASS estrito → marca retirada).

  **Testes que mudam:**
  - os que fixam a conversão de percentual no motor passam a testar a fronteira: `tests/test_valuation_engine.py::test_dy_normalization_percentual` e os equivalentes do FII;
  - os da brapi que fixam a heurística (lista no diário).

  **Golden.** Só mudam os casos com DY de entrada acima de 1, negativo ou não finito.

  **Aceite:**
  - o xfail da seção C → XPASS;
  - `tests/test_dy_fronteira.py::test_motor_nao_converte_percentual` passa por xfail estrito → XPASS;
  - para cada provedor que a regra atual erra, um caso de `::test_mesmo_dy_mesma_razao_em_cada_fronteira` também passa (por exemplo, 0,5% vindo em percentual vira 0,005);
  - `git grep -n "dy_raw / 100\|assume_subunit_percent" -- '*.py'` vazio;
  - mutation ≥ 80% em `sentinela.data.normalizacao*`;
  - golden pela regra;
  - gate da fase.

- [ ] **F2A-21** · fix · `fix: report untrusted DY as the Bazin abstention reason`
  Registrado no diário do F1-6. Com DY não confiável, o `_normalizar_dy` zera o DY, e o Bazin 1.0.0 testa o mínimo antes da confiança: o motivo sai "DY abaixo do mínimo". O número não muda, mas o relatório do F1-12 já mostra o motivo.

  O Bazin 1.0.1 testa "DY não confiável" antes do DY mínimo. Entra no changelog do registro com a nota "motivo da abstenção; nenhum número muda".

  **Testes que mudam:** os do registro e do relatório que fixam a versão 1.0.0 do Bazin passam a ler a versão vigente; o de `tests/test_methods_bazin.py` que fixar a ordem antiga, se houver.

  **Aceite:**
  - `tests/test_methods_bazin.py::test_dy_nao_confiavel_tem_prioridade_sobre_o_minimo` passa por xfail estrito → XPASS;
  - golden inalterado, porque o motor não expõe o motivo;
  - mutation de `sentinela.methods*` ≥ 80%, por módulo no diário;
  - gate da fase.

- [ ] **F2A-11** · fix · `fix: feed FII book value from CVM and abstain without it` · **[golden]**
  E-10 e armadilha 9: o `CVMFIIProvider` nunca roda, porque o `app.py:158` monta `FIIEngine()` sem provedor, e o `app.py` não muda nesta fase. A ligação vai para a cascata, onde o PLANO quer a busca de dado:
  - **Cascata.** Para FII (classe do F2A-20), busca no Informe Mensal o CNPJ do índice, com `cvm_fii_map.py` como fallback. Grava, com fonte CVM:
    - `vpa` (valor da cota);
    - `pvp` (preço ÷ valor da cota), sobrescrevendo as outras fontes;
    - `patrimonio_liquido`, `cotas_emitidas` e a data de referência.

    `cvm_disponivel` passa a valer também para FII.
  - **Motor de FII.** P/VP ausente ou não positivo deixa de virar 1,0 (`fii_engine.py:127`). A lente de P/VP não é calculada e, como a faixa neutra de antes, não pontua. A saída traz `pvp` nulo.
  - **Caminho de provedor do motor.** `FIIEngine(cvm_provider)` e `_obter_cvm_dados` ficam até o F2A-13: em produção já não rodam, e o golden ainda os cobre.

  **Golden.** Só mudam os casos de FII em que o P/VP efetivo era o 1,0 padrão: sem P/VP positivo na entrada e sem `valor_cota` positivo do provedor falso. A saída muda só no campo `pvp`.

  **Aceite:**
  - `tests/test_market_engine_fii_cvm.py::test_fii_recebe_pvp_oficial_pela_cascata` e `tests/test_fii_engine_pvp.py::test_pvp_ausente_vira_abstencao` passam por xfail estrito → XPASS;
  - `::test_falha_do_informe_mantem_as_outras_fontes`;
  - seções A, B e C intactas;
  - golden pela regra;
  - gate da fase.

- [ ] **F2A-23** · fix · `fix: stop using manual FII estimates` · **[golden]**
  E-25 e F-10. São estimativas sem data nem fonte; duas delas atribuem vacância física a fundos de papel:
  - `VACANCIA_CONHECIDA` (`fii_engine.py:27-34`, lida em `:139-141`);
  - `FII_MANUAL_FALLBACK` (`config.py:72-76`, lida em `market_engine.py:621`).

  O que muda:
  - o motor de FII deixa de ler `VACANCIA_CONHECIDA`. Vacância, só de fonte oficial, e o Informe Mensal não a traz (`vacancia_fisica` é sempre nula);
  - a cascata deixa de chamar `_aplicar_fallback_manual_fii`;
  - as duas tabelas ficam sem leitor: `VACANCIA_CONHECIDA` sai no F2A-13, e `FII_MANUAL_FALLBACK` no F2C-10, porque `config.py` só muda no F2A-4.

  **Testes que mudam.** Passam a afirmar que a estimativa manual não entra:
  - `tests/test_fii_engine.py::test_fii_engine_vacancy_adjustment` e `::test_fii_vacancia_manual_tem_flag`;
  - `tests/test_market_engine.py::test_manual_fii_fallback_fills_missing_dy_pvp` e `::test_manual_fallback_provenance_marks_manual_fields`.

  **Golden.** Só mudam os casos de TST11 e TST13 (vacância manual no harness) sem vacância do provedor falso.

  **Aceite:**
  - `tests/test_fii_sem_estimativa_manual.py::test_vacancia_manual_nao_altera_dy_nem_score` e `::test_fii_sem_fonte_nao_recebe_estimativa_manual` passam por xfail estrito → XPASS;
  - seção C intacta. `test_c_score_do_fii_fica_entre_0_e_100` usa a CVBI11, que tinha vacância manual;
  - golden pela regra;
  - gate da fase.

- [ ] **F2A-24** · fix · `fix: keep non-finite values out of engine outputs` · **[golden]**
  Registrado no F1-7 e no F1-16: a V1 propaga NaN e infinito até a saída. Nas ações, isso vem do preço não finito. No FII, o método não calculado vira NaN em `fair_value` e `upside`, e a Selic zero caiu nesse caminho.

  Regra deste item: nenhuma saída dos motores tem NaN ou infinito.
  - **Preço não finito.** Os dois motores devolvem `None`, como hoje com preço zero.
  - **FII sem método calculado** (Selic zero ou não finita, vacância não finita). Devolve o resultado do DY inválido, com o motivo da abstenção do método em `metodos_usados`.
  - **Fica de fora:** o que fazer com ROE e P/L ausentes ou não finitos no score, porque isso muda classificação, e não só NaN (decisão na última seção).

  **Golden.** Só inclusões: preço NaN e infinito nos dois motores; Selic zero e não finita no FII. Nenhum caso existente muda, porque o DY não finito já mudou no F2A-4.

  **Aceite:**
  - `tests/test_saidas_finitas.py::test_acao_com_preco_nao_finito_devolve_none` e `::test_fii_com_selic_zero_nao_devolve_nan` passam por xfail estrito → XPASS;
  - `::test_golden_sem_nan_nem_infinito` percorre o golden inteiro;
  - golden pela regra;
  - gate da fase.

- [ ] **F2A-25** · fix · `fix: abstain Gordon when earnings per share is not positive` · **[golden]**
  Com LPA ≤ 0, o Gordon 1.0.0 usa payout de 50%. É o fallback da V1, declarado em `assumptions`; o F1-6 diz que ele "só vira abstenção com versão nova". É número degradado, contra o contrato de método.
  - Gordon 1.1.0: LPA não positivo → `Abstention("LPA não positivo")`, depois dos testes de DY e de ROE.
  - Saem `PAYOUT_SEM_LPA` e a premissa do fallback; entra a versão 1.1.0 no changelog.

  **Testes que mudam:**
  - `tests/test_registry.py::test_parametros_da_1_0_0_fixados`, que importa `PAYOUT_SEM_LPA`, e os testes que fixam a versão 1.0.0 do Gordon (registro e relatório): passam a fixar os parâmetros e a versão vigentes;
  - o teste do fallback em `tests/test_methods_gordon.py` vira o teste da abstenção.

  **Golden.** Só mudam os casos de ações em que o Gordon calculava com P/L ausente, não positivo ou não finito: `--onde "'Gordon' in saida_antiga['metodos_usados'] and not ((entrada.get('pl') or 0) > 0)"`.

  **Aceite:**
  - `tests/test_methods_gordon.py::test_lpa_nao_positivo_abstem` passa por xfail estrito → XPASS;
  - mutation de `sentinela.methods*` ≥ 80%, por módulo no diário;
  - seções A, B e C intactas: o caso do Gordon na seção B tem LPA 10;
  - golden pela regra;
  - gate da fase.

- [ ] **F2A-12** · fix · `fix: validate tickers against an allowlist before URLs and prompts`
  E-18. O ticker digitado (`app.py:202`) chega sem validação a três lugares: a URL da brapi (`brapi_provider.py:115`), o yfinance (`market_engine.py:365`) e o prompt do LLM (`_montar_prompt` do `ai_core.py`). O `app.py` não muda, então a validação fica em cada fronteira:
  - **A função.** `sentinela/domain/ticker.py`, pura. Normaliza (maiúsculas, sem espaços, sem `.SA`) e só aceita `^[A-Z0-9]{4}[0-9]{1,2}$`: raiz de 4 caracteres e 1 ou 2 dígitos. Isso cobre ações, units, FIIs, ETFs e BDRs como `A1MD34`. Não exige que o ticker esteja no índice; fora dele, a classe é `UNKNOWN` (F2A-20).
  - **Quem chama:**
    - `MarketEngine.buscar_dados_ticker`: inválido → `None`, sem chamada externa. O app já mostra "Ativo não encontrado";
    - a brapi, antes de montar a URL;
    - o `SentinelaAI`, antes do prompt: inválido → resposta fixa, sem chamar provedor;
    - o relatório do F1-12, que troca a regex própria pela função.

  **Aceite:**
  - `tests/test_ticker_allowlist.py::test_ticker_invalido_nao_chega_ao_yfinance`, `::test_ticker_invalido_nao_vira_url_da_brapi` e `::test_ticker_invalido_nao_entra_no_prompt` passam por xfail estrito → XPASS;
  - `::test_formatos_validos`: PETR4, KLBN11, HGLG11, BOVA11, AAPL34, A1MD34 e `petr4.sa`;
  - `::test_formatos_invalidos`: vazio, espaço interno, `&`, `/`, `;`, quebra de linha e mais de 6 caracteres;
  - mutation ≥ 80% em `sentinela.domain.ticker*`;
  - golden inalterado;
  - gate da fase.

- [ ] **F2A-26** · feat · `feat: add liquidity metrics from COTAHIST` · **[D7]**
  Insumo do F2A-10 e da **[LIQUIDEZ]**. É aditivo: nenhum motor lê.
  - **`dados['liquidez']`.** A cascata grava, pelo COTAHIST do F2A-18, para 21 e 63 pregões:
    - volume financeiro diário mediano e médio;
    - negócios por dia (mediana);
    - presença: fração de pregões do arquivo com negócio no ticker;
    - a data final e a fonte.

    O bloco fica fora do prompt.
  - **Relatório do F1-12.** Mostra a liquidez.
  - **Organização.** A conta fica em função pura em `sentinela/data/`.

  **Aceite:**
  - `tests/test_liquidez.py::test_mediana_do_volume`, `::test_presenca_conta_pregoes_sem_negocio` e `::test_janela_de_63_pregoes`, com COTAHIST sintético;
  - mutation ≥ 80% no módulo puro;
  - golden inalterado;
  - gate da fase.

  Se o F2A-16 registrou COTAHIST inacessível, o item fica `[!]`.

- [ ] **F2A-10** · fix · `fix: abstain below the liquidity threshold` · **[LIQUIDEZ]** **[D7]** **[golden]**
  **Só entra com a [LIQUIDEZ] escrita aqui na ativação.** Sem ela, o Marcos tira o item da fila na ativação, e ele vai para a fila da 2B. O loop nunca o executa sem o limiar.
  - Janela: ___ · Métrica: ___ · Valor: ___
  - Texto da abstenção: ___
  - Sem dado de liquidez: ___ (seguir sem gate, com o relatório dizendo "não verificada", ou abster-se)

  Abaixo do limiar, os dois motores devolvem o resultado de abstenção: o texto decidido, a liquidez em `riscos`, sem métodos e sem classificação.

  **Golden.** Só inclusões: casos abaixo, no limite e acima do limiar, e sem dado de liquidez.

  **Aceite:**
  - `tests/test_gate_liquidez.py::test_abaixo_do_limiar_abstem` passa por xfail estrito → XPASS;
  - `::test_no_limiar` e `::test_sem_dado_de_liquidez_segue_a_decisao`;
  - golden pela regra;
  - gate da fase.

- [ ] **F2A-27** · docs · `docs: sync agent instructions with phase 2A data layer`
  Valida contra o código e corrige três arquivos: `CLAUDE.md`, `AGENTS.md` (menos a seção "Fase atual", que é do Marcos) e a tabela da Fase 2A do `docs/PLANO.md`, que ganha os IDs finais e a ordem desta fila.

  **No `CLAUDE.md`:**
  - "Arquitetura real": contagens de linha e a camada `sentinela/data/`;
  - "Fluxo de dados real": o índice no começo, sem Fundamentus, com a CVM de FII e a liquidez;
  - regras econômicas: o normalizador de fronteira e o invariante `_normalizar_dy`;
  - armadilhas 2, 3, 4, 9, 10, 14 e 15, resolvidas ou atualizadas, e a 17 com o que a 2A fez;
  - "Segurança": o ticker validado;
  - a contagem da suíte e as "Fases".

  **No `AGENTS.md`:** a contagem da suíte e o "Contexto que evita retrabalho": cascata sem Fundamentus, e a linha do `cloudscraper` sai.

  Se algo divergir, corrige o documento, nunca o código.

  **Aceite:**
  - diff só nesses três arquivos;
  - cada linha citada conferida com `grep -n` e listada no diário;
  - `CLAUDE.md` e `AGENTS.md` sem contradição entre si.

- [ ] **F2A-28** · levantamento · `docs: propose phase 2B queue`
  O `fable-architect` propõe a fila da 2B em `docs/loop/fila-fase2b-proposta.md`, no formato desta. Partes:
  - a seção "Fase 2B" do PLANO;
  - o dossiê, perguntas 2, 3 e 5;
  - o checkpoint da Fase 0, seção 4, itens 2, 3 e 5: prêmio-base de 5%, sensibilidade de 4% e 7%, e o prêmio fixado só depois de repetir a coleta da NTN-B com o Tesouro respondendo;
  - o diário desta fase;
  - o F2A-10, se ele saiu desta fila.

  Nada é implementado.

  **Aceite:** arquivo no formato desta fila; todo item com aceite verificável; nenhuma decisão do Marcos tomada pelo texto.

- [ ] **F2A-13** · limpeza · `chore: clean up phase 2A residue` · **[golden]**
  Faz só o que segue, conforme o inventário (seções 1.2, 3.1, 5 e 7), o PLANO (seção 11) e o checkpoint da Fase 0 (seção 3):
  - **Vacância manual.** `VACANCIA_CONHECIDA`, sem leitor desde o F2A-23, junto com o patch dela no harness e o import em `tests/test_fii_engine.py`.
  - **Caminho de provedor do motor de FII,** sem uso em produção desde o F2A-11:
    - o parâmetro `cvm_provider`, `_obter_cvm_dados` e o import de `get_cnpj_fii`;
    - a resolução de P/VP e de vacância pelo provedor, e o ramo de vacância do score, que fica sem fonte;
    - no harness, `_ProvedorFalso`, o patch de `get_cnpj_fii` e os casos com `cvm`;
    - em `tests/test_fii_engine.py`, os testes desse caminho; o equivalente na cascata entrou no F2A-11.

    Golden: só remoções, exatamente os casos com `cvm`. A vacância só volta com fonte oficial e decisão de método (F-10).
  - **Atualizador e scripts.**
    - A `CVMTickerMap` (classe, `_seed_manual_map`, `refresh`, `ensure_seeded`) e os testes dela;
    - `scripts/gerar_mapa_cvm.py`;
    - `scripts/invalidar_cache_cvm.py` e `tests/test_invalidar_cache_cvm.py`, porque o Marcos já rodou a invalidação.
  - **Mapas manuais (PLANO: só se o mapa automático cobrir o universo).**
    - Vale a remoção se o diário do F2A-1 registrou 100% dos mapeáveis e nenhum ticker dos mapas diverge do índice.
    - Nesse caso saem `cvm_ticker_map.py`, `cvm_fii_map.py`, `tests/test_cvm_ticker_map.py`, os testes de mapa em `tests/test_cvm_fii_provider.py` e `tests/fixtures/cvm_codigos_oficiais.csv`.
    - A cascata fica só com o índice. Os testes de CVM de `tests/test_market_engine.py` passam a injetar um índice falso, sem mudar asserção. `scripts/dossie_fase2.py` passa a ter a própria amostra, os mesmos tickers públicos.
    - Única mudança de comportamento da limpeza: sem índice local, a CVM deixa de ser consultada. Fica registrada no diário.
    - Se a condição não vale, os mapas ficam como fallback, com o motivo no diário.
  - **Investigar, decidido no checkpoint da Fase 0 (seção 3).**
    - `market_engine.buscar_noticias` (`market_engine.py:677`).
    - `brapi_provider.get_quote` (`brapi_provider.py:125`), depois de confirmar por teste que o preço reserva da brapi passa por `get_fundamentals`; o teste usado vai citado no diário.
  - **Sobras do scraper.** A flag `erro_scraper` do `MethodInputs` (`sentinela/methods/base.py`, sem leitor), com os testes de contrato que a citam, e a fonte `fundamentus` do `data_quality.py`.
  - **`dy_mes_decimal` do `CVMFIIProvider`,** sem leitor (E-30).
  - **`vulture_whitelist.py`.** `ETF` e `BDR` saem, porque agora têm uso; falso positivo novo entra com o motivo.
  - **Correções automáticas seguras** (inventário, seção 3.1: UP045, UP006, UP037, I001, F541, FURB188, PYI041), nos arquivos travados até aqui: `market_engine.py`, `brapi_provider.py`, `cvm_provider.py`, `cvm_fii_provider.py`, `fii_engine.py`, `data_quality.py` e, se ficarem, os dois mapas. `config.py` não entra.
  - **Não saem nesta fase:**
    - `FIIS_CONHECIDOS` e `UNITS_CONHECIDAS`: fallback do classificador sem índice, de que o teste do Markowitz na seção B depende até o F2C-9;
    - `FII_MANUAL_FALLBACK` (F2C-10);
    - `erro_scraper` de `sentinela/domain/models.py` (modelo desconectado, F3-6), de `backtesting/` e de `auditar_recomendacoes.py` (F3);
    - os resíduos do `app.py` (F3-6).

  Depois, roda de novo o vulture, o `ruff check . --statistics` e o deptry, e atualiza `docs/limpeza/inventario.md` (antes → depois), com os resíduos que ficaram para outras fases.

  **Aceite:**
  - gate da fase;
  - golden só com as remoções dos casos com `cvm`;
  - testes alterados só nos pontos listados, sem asserção enfraquecida (conferido no diff);
  - `git grep` de cada nome removido sem resultado fora de `docs/`;
  - referências de linha do `CLAUDE.md` e do `AGENTS.md` para os arquivos tocados conferidas;
  - inventário atualizado;
  - lista para o Marcos apagar à mão: `data/cotahist/`, `data/referencia/`, `outputs/levantamento_cache/` e `outputs/dossie_cache/`.

- [ ] **F2A-14** · docs · `docs: add phase 2A summary and archive loop files`
  Nesta ordem:
  1. escrever `docs/loop/pr-fase-2a.md` a partir do diário, com:
     - itens e commits;
     - testes antes → depois;
     - mutação dos módulos novos e de `sentinela/methods/`;
     - cada mudança de comportamento, com o efeito medido e o diff do golden (predicado e contagem);
     - a cobertura do índice;
     - decisões pendentes;
     - resíduos que ficaram para o Marcos;
     - o que revisar primeiro;
  2. registrar este item no diário e marcá-lo `[x]`;
  3. mover com `git mv` os arquivos `fila.md`, `diario.md` e `pr-fase-2a.md` para `docs/loop/historico/fase-2a/`;
  4. criar um `docs/loop/fila.md` novo contendo só:
     `[DECISÃO] Fase 2A encerrada. Histórico em docs/loop/historico/fase-2a/. Próxima fila aguardando aprovação: docs/loop/fila-fase2b-proposta.md.`
  5. commitar e rodar `cat docs/loop/fila.md`.

- [DECISÃO] **Fim da Fase 2A.** O Marcos:
  1. revisa as mudanças de comportamento na ordem do resumo, com o diff do golden de cada uma;
  2. confere a cobertura do índice (F2A-1) e as exceções, inclusive a CSNA3;
  3. gera relatórios reais com o F1-12 para uma ação com ON e PN, uma unit, um banco e um FII. Confere ações, escala, documento, P/VP oficial, alavancagem e liquidez. Os relatórios saem em `outputs/`, fora do git;
  4. apaga as linhas de `fundamentals_cache` do banco local, ou espera o TTL de 7 dias: os valores gravados antes da fase continuam servindo de reserva;
  5. responde à [LIQUIDEZ], se o F2A-10 saiu desta fila, e lê a proposta da 2B (F2A-28);
  6. faz o push do branch `v2/fase-2a` e abre o PR da fase (um PR por fase, checkpoint da Fase 0, seção 6), com `docs/loop/historico/fase-2a/pr-fase-2a.md` como corpo. O Jules revisa (grupo A);
  7. depois do merge, marca a tag `v2-fase-2a`, apaga o branch, atualiza a "Fase atual" do `AGENTS.md` e apaga à mão os caches listados no F2A-13.

## Riscos e decisões do Marcos

- **Perguntas do dossiê.** Foram respondidas no checkpoint da Fase 0 (seção 4). Os itens seguem as respostas. Abaixo, as leituras que a fila adota (o Marcos confirma ou corrige na aprovação) e o que muda se uma resposta for revista.
  - **P1, quantidade de ações (F2A-3, F2A-5, F2A-7).**
    - **Resposta:**
      - sempre a Composição do Capital;
      - divergência com o yfinance acima de 5% é alerta;
      - abstenção só quando a CVM falha;
      - LPA = lucro ÷ (ON + PN − tesouraria);
      - P/L com o preço da própria classe;
      - unit multiplicada pelas ações que contém.

      O limiar de divergência das ações, portanto, já está decidido.
    - **Comparação por espécie.** O alerta compara as ações da espécie do ticker com o `sharesOutstanding` dele. Comparando o total, o alerta dispararia para quase toda empresa com ON e PN, porque o yfinance informa a classe: no dossiê (seção 1), 8 de 9 dessas empresas divergem mais de 5%.
    - **Escala pelo LPA divulgado** (DRE 3.99, mesmo documento). Pela razão contra o yfinance, como fez o dossiê, o yfinance decidiria a escala. Isso contraria "abstenção só quando a CVM falha" e a D7.
    - **"A CVM falha"** = sem Composição do Capital do mesmo documento, escala indeterminada, total ≤ 0 ou unit sem composição oficial.
    - **Contas de lucro e PL.** São as que a V1 usa hoje: consolidado, com não controladores. Usar o lucro e o PL atribuíveis aos controladores (F-13) é pergunta nova. Se o Marcos quiser, o F2A-3 troca as contas, e o efeito aparece no diário (holdings e empresas com minoritários relevantes).
    - **Se a resposta virar "abster-se quando divergir mais de 5%":** o F2A-3 troca o alerta por abstenção, o que dá ao yfinance o poder de vetar a CVM, e o F2A-5 perde o alerta de ações.
  - **P5, bancos (F2A-9, F2A-8).**
    - **Resposta:** lente própria com P/VP justificado pelo ROE (F2B-3); Basileia e inadimplência opcionais, com a limitação declarada.
    - **Efeito:** o F2A-9 traz PL, lucro e ROE do modelo financeiro. Só escreve o provedor do IF.data se o F2A-16 o confirmar; no dossiê, todas as chamadas deram HTTP 500.
    - **Se Basileia e inadimplência virarem obrigatórias:** o F2A-9 fica `[!]` enquanto o IF.data não responder.
    - **Se virar "só abstenção para bancos"** (alternativa rejeitada no ADR-0002): o F2A-9 encolhe à identificação, e a 2B perde o F2B-3.
  - **P6, mapa dos FIIs (F2A-18, F2A-1).**
    - **Resposta:** junção do ISIN do COTAHIST com o do Informe Mensal; regra do ISIN como reserva.
    - **Se virar "só a regra do ISIN":** o F2A-1 dispensa o COTAHIST, que segue necessário para liquidez, BDR e ETF.
    - **Se virar "lista da B3":** é fonte nova, sem levantamento, e o F2A-1 fica `[!]` até o F2A-16 cobri-la.
  - **P7, escopo (F2A-1, F2A-20, F2A-3).**
    - **Resposta:** units entram, com o ajuste de ações por unit; ETFs e BDRs ficam fora dos métodos, com abstenção e motivo, mas entram na camada de risco.
    - **Efeito:** a classe vem de dado oficial já na 2A; a abstenção dos métodos é o F2B-4.
    - **No intervalo,** o `app.py`, travado, manda ETF, BDR e `UNKNOWN` ao motor de ações, que calcula sem sentido para eles, como hoje (hoje o ETF vai ao motor de FII). Se o Marcos não aceitar o intervalo, um item a mais na 2A antecipa a abstenção dessas classes no `valuation_engine`. Muda saída; o golden só ganha casos novos.
    - **Se a resposta virar "classes próprias com métodos":** são lentes novas, fora da 2A.
- **[LIQUIDEZ]** (F2A-10). O PLANO previa decidir antes da 2A (seção 15), mas o dossiê não mediu liquidez. O F2A-16 mede, só que depois da ativação. A decisão tem cinco partes:
  - **janela:** 21 pregões (reage rápido, com mais ruído), 63 (um trimestre) ou 252 (exige a série anual do COTAHIST, que é do F3-4);
  - **métrica:** volume financeiro diário mediano (resiste a pico) ou médio, negócios por dia, presença em pregões, ou uma combinação;
  - **valor:** decidir já exige um valor de convenção; o F2A-16 mostra quantos ativos ficam abaixo de cada candidato;
  - **texto da abstenção,** sem "compra" nem "venda";
  - **comportamento sem dado de liquidez.**

  Com a decisão escrita, o F2A-10 entra como está. Sem ela, sai da fila e vai para a 2B, e o F2A-26 deixa a distribuição no diário.
- **Regra do golden** (checkpoint da Fase 1, item 6). Opções:
  - **(a) a proposta do cabeçalho:** a fila fica como está;
  - **(b) congelar o golden como registro da V1** e substituí-lo por testes de método e de cascata: os itens **[golden]** trocam a regeneração por testes novos, e o F2A-17 (refactor) perde o juiz;
  - **(c) regenerar só no fim da fase:** inviável, porque o protocolo exige a suíte verde a cada item.

  Sem decisão, os itens **[golden]** param em `[!]`.
- **[CORREÇÕES]** (F2A-19). A CSN preenche `Codigo_Negociacao` com `4030`, o próprio CD_CVM, nos FCA de 2025 e 2026. A proposta é uma tabela versionada de correções de defeito de fonte, cada linha com evidência oficial e revisada pelo Marcos.
  - **Aprovada:** a CSNA3 volta à CVM pelo CNPJ.
  - **Recusada:** a CSNA3 fica fora, como está desde o F1-15, agora com o motivo visível.

  Em nenhum dos casos se inventa código.
- **Escolhas de desenho que a aprovação confirma:**
  - **Alavancagem só da CVM (F2A-8).** Se o Marcos preferir a brapi como reserva fora da cobertura, as definições se misturam no mesmo campo, que é o defeito apontado no F-12.
  - **LPA divulgado como segunda referência do E-2, com o limiar de 10% da V1 (F2A-5).** Comparar P/L e P/VP com yfinance ou brapi dispararia por diferença de data-base: TTM de um lado, exercício do outro.
  - **CVM de FII pela cascata, e não pelo `app.py:158` (F2A-11).** O `app.py` está travado, e o PLANO põe a busca de dado na camada de dados. Por isso o caminho de provedor do motor sai no F2A-13, levando a vacância junto.
  - **`CVMTickerMap` substituída, não consertada (F2A-1, F2A-13).** O PLANO fala em "conserto", mas a classe nunca rodou em produção.
  - **Prazos diferentes dos documentos de origem:**
    - `FII_MANUAL_FALLBACK` sai no F2C-10, e não no F2A-13, porque `config.py` só muda no F2A-4;
    - o gerador do mapa e o script de invalidação saem no F2A-13, e não no F2A-1 (inventário, seção 5), porque a invalidação roda no checkpoint da Fase 1.
  - **Mapas manuais (F2A-13).** A remoção condicional custa adaptar testes e o `scripts/dossie_fase2.py`, e muda o caso sem índice local. A alternativa é mantê-los como fallback até o F3-9.
  - **Ruff bloqueante em `sentinela/methods/` e `sentinela/data/`.** Se o Marcos quiser, ele muda o passo 4 do protocolo e a skill `/safe-commit` antes da ativação; a fila não muda.
- **Fora da fase, pendente:**
  - ROE e P/L ausentes no score. Ausente vira 0 e penaliza; NaN escapa;
  - JCP no DY (F-7);
  - ROE do yfinance sem guarda (E-15);
  - Selic sem proveniência e rede no import (E-6, F3-1);
  - `analisar(ticker, as_of)` e o `date.today()` dos motores (F3-6);
  - `applies_to` (F2B-4);
  - vocabulário (F2C-4);
  - um ponto de extensão público no lugar dos singletons (F2C ou F3);
  - grupo econômico (F4-7);
  - DY do Informe Mensal de FII;
  - o texto de dívida em pt-BR no motor: sem fonte de texto depois do F2A-22, mas o golden o fixa.
- **Riscos:**
  - **Fatos do levantamento.** O F2A-16 pode mostrar fatos que deixam itens `[!]`:
    - COTAHIST inacessível trava o F2A-26 e o F2A-10;
    - DVA sem código estável abre lacuna nos proventos (F2A-7) e faz o EBITDA se abster (F2A-8);
    - contas de banco indeterminadas travam o F2A-9.
  - **Volume local.** Cinco anos de DFP, ITR, COTAHIST e Informe Mensal somam centenas de MB em `data/`, e a primeira análise fica mais lenta. O F2A-17 mitiga o processamento, não o disco.
  - **Golden.** Com as inclusões, pode passar de 1 MB. O diário registra o tamanho a cada item **[golden]**.
  - **Muitos testes mudam por decisão.** Todos estão listados nos itens; o `/review-diff` confere que nenhuma asserção foi enfraquecida.
  - **Resíduos do `app.py`** (travado) até o F3-6: o indicador "Erro Scraper", a mensagem do Fundamentus e o `tipo` do FII como "TIPO INDISPONÍVEL".
  - **Jules:**
    - B4.1 a B4.3 e C-D precisam estar mergeados;
    - B2 cancelado;
    - C-E sem janela;
    - C-C segue, e nenhum item toca `peers_engine.py`.