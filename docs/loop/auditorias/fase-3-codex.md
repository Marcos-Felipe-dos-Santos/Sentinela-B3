# Auditoria da Fase 3 — leitura em `v2/fase-3`, `5d7c3f0`

## Resumo (14 linhas)

- Escopo: resultado da análise e do backtest antes da Fase 4; banco aberto com `mode=ro` e `query_only=ON`.
- Achados: **1 BLOQUEANTE, 10 IMPORTANTES, 3 MENORES**.
- **BLOQUEANTE C-1:** dois retornos realizados incluem como desdobramento do papel eventos que emitem outra espécie; a própria série de preços abstém nesses casos.
- A análise retroativa usa cortes documentais, de preço e de universo; há dependências de relógio e seleções retrospectivas que enfraquecem a reprodutibilidade.
- Os seis G-NONE e o NUM terminam em abstenção, sem valor incorreto demonstrado; os quatro PRECO não negociaram em D no banco.
- Cinco retornos com proventos e, em três casos, desdobramentos foram recalculados dos registros brutos e coincidiram com a sonda.
- A banda de 65% é apenas medida, sem adoção; sua calibração usa uma data de início e 15 retornos disponíveis.
- A DD-85 teve perda real de zero lentes porque o cache estava vazio; 348 de 844 análises terminaram com campo obrigatório ausente.
- Não houve correção, coleta em massa, alteração do banco ou teste no repositório.

**Convenção:** FATO é observação de código, artefato ou consulta indicada; HIPÓTESE é causa/efeito ainda não demonstrado. As consultas abaixo usam `sentinela_store.db` em SQLite somente leitura. “Reproduzir” indica a verificação, não uma proposta de alteração.

## A. Vazamento de futuro

### A-1 — IMPORTANTE — Seleção retrospectiva de coletas macro e proventos

**FATO.** `sentinela/data/providers/macro.py:853-860` escolhe a maior `coleta` de cada par `(serie,data)` sem restringi-la a `as_of`; `:886-890` escolhe a última coleta da família Tesouro inteira. O leitor filtra a data-base, publicação e a janela em `:881-945` e `:960-1017`, mas não a versão da coleta. `sentinela/data/providers/b3_proventos.py:543-565` também escolhe a última coleta do emissor, mesmo posterior a D, no modo `por_publicacao=True`; `:617-626` filtra aprovação e data com anteriores a D. A decisão 40 autoriza essa disponibilidade por publicação. A consulta `GROUP BY serie,data HAVING COUNT(DISTINCT valor)>1` para `data<'2025-01-01'` não achou revisão numérica macro neste banco; portanto **não há vazamento de valor demonstrado**. A relação B3 mais recente pode omitir registro que uma coleta anterior trazia: esse efeito não foi medido.

**HIPÓTESE.** Uma revisão retroativa ou retirada de registro pela fonte pode mudar uma análise em D quando o banco recebe coleta posterior. **Reproduzir:** para uma mesma série/data ou emissor, comparar versões distintas por `coleta`, refazer a leitura em D com cada fotografia e confrontar o valor/abstenção. Não interpretar a coleta posterior, por si só, como publicação posterior do fato.

### A-2 — IMPORTANTE — Relógio abaixo da borda histórica

**FATO.** `AnalysisService.analisar` escolhe `MotorHistorico` para `dia < self.hoje` (`sentinela/services/analyze_asset.py:113-157`), mas `MarketEngine.buscar_dados_ticker` marca `disponibilidade_por_publicacao` comparando D com `_hoje_sp()` do relógio (`market_engine.py:529-532`), e `_buscar_cvm` repete essa comparação (`:1163-1171`). `_aplicar_referencia` passa `datetime.now(UTC)` (`:601-603`) à interface, embora `ReferenciaEm.indice` ignore o argumento (`sentinela/services/historico.py:156-159`). `_contexto_janelas` recebe `coletado_em=datetime.now(UTC)` (`market_engine.py:576-579`). Os preços da lente são brutos do último pregão **antes** de D; o histórico ajustado fica em `historico`, campo distinto (`sentinela/services/historico.py:207-246`); não encontrei a série ajustada usada diretamente como preço de múltiplo. As chamadas de rede diretas localizadas em `MarketEngine` pertencem a provedores substituídos no `MotorHistorico`; não foi observada chamada de rede na sonda.

**HIPÓTESE.** Um replay com `self.hoje` fixo mas relógio do sistema em outro dia pode escolher regra de disponibilidade diferente. **Reproduzir:** na cópia isolada, fixar `self.hoje`, variar apenas o relógio injetado/monkeypatch de `_hoje_sp` em torno de D e comparar a marca e as abstenções. A leitura da hora na referência, isoladamente, não prova vazamento porque o adaptador ignora esse parâmetro.

## B. Casos suspeitos do diagnóstico

### B-1 — IMPORTANTE — Seis G-NONE: `None` alcança guarda numérica do Gordon

**FATO.** Na sonda `outputs/f3-8j-uni/sonda/observacoes.json`, os pares de 12 meses são TAEE3/TAEE4/TAEE11 em 2021-06-30, ELMD3 em 2022-06-30, CVCB3 e PRNR3 em 2023-06-30. O motivo persistido em `outputs/f3-8j-uni/sonda/resultados.db`, tabela `resultados_analise`, é `insumo ausente ou inválido do Gordon: must be real number, not NoneType`. `sentinela/data/gordon_cvm.py:192-218` chama `math.isfinite` em `lucro_controladores`, `pl_inicial_controladores` e `proventos_controladores` sem antes testar tipo; `:260-261` transforma o `TypeError` em abstenção genérica. Logo, há **bug confirmado de validação/motivo**, sem valor de lente errado: a abstenção protege a saída. A peça exata que veio `None` em cada par não está no resultado persistido.

**HIPÓTESE causal ainda aberta:** campo documental ausente ou adaptação que deixou `None`; não há prova de falha de backfill. **Reproduzir:** consultar os seis `(ticker,D,metodo='Gordon')` no `resultados.db`; na cópia isolada, inspecionar os três campos de `gordon_cvm` antes da fronteira em cada D. A classificação por par permanece **bug na guarda, origem do dado indeterminada**, sem afirmar seis bugs de carga.

### B-2 — IMPORTANTE — NUM de TGMA3: campo da janela não identificado

**FATO.** TGMA3 em 2025-06-30, Graham, abstém com `insumo numérico ausente ou não finito` na mesma sonda e no `resultados.db`. Esse texto sai de `sentinela/data/janelas_fundamentais.py:26-33`; o percurso do Graham chama `_numero` em ações/fatores (`:50-93`), LPA (`:149-152`), IPCA e VPA (`:194-218`). A exceção vira abstenção, e a sonda não registra qual campo causou a mensagem.

**HIPÓTESE:** limite documental ou adaptação do insumo, sem evidência para classificar como falha de backfill. **Reproduzir:** na cópia isolada, obter `serie_cvm` e `ipca_serie` de TGMA3 em D e registrar qual chamada de `_numero` falha. Classificação atual: **causa raiz não resolvida**, sem número incorreto demonstrado.

### B-3 — IMPORTANTE — Quatro PRECO são falta de negócio em D no banco

**FATO.** BIDI3, BIDI4 e BIDI11 em 2022-06-30, e ELMD3 em 2025-06-30, têm `preco_entrada=None` na sonda. Consulta `precos` por `(codigo_negociacao,data=D)` retorna zero nos quatro; o último negócio anterior de BIDI3 é 2022-06-17 e o de ELMD3 é 2025-06-12; não há negócio posterior no banco para nenhum dos quatro. `backtesting/backtest_pit.py:477-505` exige fechamento de D, enquanto a elegibilidade usa os 63 pregões **anteriores** (`sentinela/data/referencia/universo.py:94-152`). A abstenção é, portanto, coerente com o banco. **Classificação:** ausência legítima de negociação *nos dados carregados*; não foi provado se a fonte original contém cotação omitida.

**Reproduzir:** `SELECT data FROM precos WHERE codigo_negociacao=? AND data BETWEEN ? AND ? ORDER BY data` em torno das duas datas; comparar uma amostra pequena com o COTAHIST original, se necessário, sem download em massa.

## C. Retorno total

### C-1 — BLOQUEANTE — Evento emitido em outra espécie vira fator do ativo

**FATO.** `backtesting/backtest_pit.py:576-611` filtra o evento pelo `isin` de origem do ticker, mas **não confere `ativo_emitido`** antes de acrescentar o fator a `eventos`. Em contraste, `sentinela/data/pit/serie_ajustada.py:136-147` só aplica fator quando `ativo_emitido == isin` e abstém outra espécie. No banco, CYRE3 tem evento com `data_com=2025-12-30`, ex=2026-01-02, `isin=BRCYREACNOR7`, `ativo_emitido=BRCYREACNPR4`, fator 1,18958333333. RENT3 tem `data_com=2025-12-29`, ex=2025-12-30, `isin=BRRENTACNOR4`, `ativo_emitido=BRRENTACNPR1`, fator 1,03846095334. A sonda atribui aos respectivos pares de 12 meses **+13,548538%** e **+11,775629%** como retornos válidos. A conta sem converter espécie dá −4,547639% e +7,635852%, respectivamente, mas esses números alternativos **não são retorno correto comprovado**: a regra vigente exige abstenção quando a reconciliação entre espécies não está demonstrada (`serie_ajustada.py:23-27,136-147`; `docs/metodologia/backtest.md:37-39`). Os dois números reportados são inválidos sob esse contrato.

**Reproduzir:** consultar `eventos_societarios` pelas duas raízes e datas com, relacionar o ISIN do pregão anterior em `precos`, consultar `observacoes.json` pelos pares `(CYRE3,2025-06-30,12)` e `(RENT3,2025-06-30,12)`; comparar os filtros de `_retornos` e `serie_do_banco`. Não usar esses pares em medida de banda/quintil como retornos válidos.

### Conferência manual de cinco pares — sem achado adicional

**FATO.** Li `precos` (centavos divididos por `fator_cotacao`), `proventos` pela relação da coleta selecionada e `eventos_societarios` do banco somente leitura. Calculei independentemente `P_T/(P_D/F_D) × ∏[1+(provento_ex/F_ex)/(P_ex/F_ex)] − 1`, agrupando proventos por data ex, com fronteira `(D,T]`. Todas as cinco contas coincidem com `outputs/f3-8j-uni/sonda/observacoes.json` à precisão exibida:

| Papel; D → T | P_D; P_T (R$) | Evento aplicado | Retorno manual = sonda |
|---|---:|---|---:|
| MULT3; 2018-06-29 → 2019-06-28 | 57,00; 27,76 | 3:1 em 2018-07-23; 3 datas ex | 48,837656% |
| TOTS3; 2019-06-28 → 2020-06-30 | 43,97; 23,15 | 3:1 em 2020-05-04; 3 datas ex | 59,398524% |
| MGLU3; 2020-06-30 → 2021-06-30 | 71,65; 21,15 | 4:1 em 2020-10-14; 2 datas ex | 18,336347% |
| PETR4; 2021-06-30 → 2022-06-30 | 29,43; 27,93 | sem evento; 4 datas ex PN | 37,157145% |
| BBSE3; 2023-06-30 → 2024-06-28 | 30,77; 32,93 | sem evento; 2 datas ex ON | 17,160247% |

**Reproduzir:** selecionar os cinco pares em `observacoes.json`, consultar `precos` no intervalo, `proventos_ate(..., por_publicacao=True, ticker=ticker)` e `eventos_ate(..., T+1)` com conexão `mode=ro`; aplicar a expressão acima sem chamar `retorno_total`. A amostra não valida os outros 387 pares com retorno.

## D. Método e calibração

### D-1 — IMPORTANTE — Banda medida em amostra temporal estreita

**FATO.** `scripts/banda_neutra_fase3.py:126-174` forma quintis por data, corta na posição `ceil(n/2)`, só calibra observações cujo fim não passa da fronteira, e usa mediana de `|distância_ao_preço_pct|`. Coincide com `docs/metodologia/backtest.md:71-77`; não há retorno futuro na definição da largura da banda, e validação é separada por D. A medição de Gordon/12m usa somente D=2022-06-30 na calibração (44 distâncias, **15 retornos**), 43 observações iniciais excluídas por atravessar a fronteira; 65% **não foram adotados** (`docs/decisoes/banda-neutra-proposta-3.md:99-118`). **HIPÓTESE:** a proposta é instável fora dessa data, sem evidência de vazamento da validação. **Reproduzir:** conferir `fronteira`, `n_calibracao` e `excluidas_pela_fronteira` em `outputs/f3-8j-uni/sonda/proposta.json` e cotejar o script. A invalidade C-1 também afeta a confiabilidade das métricas de retorno.

### D-2 — IMPORTANTE — Lentes não são evidências econômicas independentes

**FATO.** Gordon usa distribuição DVA e `custo_capital_real`/NTN-B (`sentinela/methods/gordon.py:43-55,107-125`); a lente de FII usa rendimento/juros reais e spread (`docs/metodologia/fii.md:52,179-184`); Bazin usa proventos brutos e limiar nominal fixo de 6% (`CLAUDE.md:145`; `docs/metodologia/backtest.md:35-39` para os proventos). Assim, Gordon e FII compartilham o choque de juros, enquanto Bazin e as medidas de DY compartilham a família de proventos. **HIPÓTESE:** contar concordância dessas lentes como confirmações independentes exageraria confiança; o relatório atual as separa e não soma score. **Reproduzir:** traçar os campos de entrada de cada método e variar apenas taxa ou provento em casos sintéticos na cópia, observando quais lentes mudam.

## E. Testes

### E-1 — MENOR — Parametrização que não verifica o parâmetro

**FATO.** `tests/test_backtest_pit_retornos.py:535-545` parametriza `data_com` em `[D,T]`, mas o corpo não o usa; os dois casos executam a mesma conta. **Reproduzir:** inspecionar o nome `test_dois_proventos_em_datas_ex_distintas_se_compoem` e contar as referências de `data_com` no corpo. Não encontrei outro caso obviamente vazio nos trechos de A/C inspecionados; isso não é afirmação sobre toda a suíte.

### E-2 — IMPORTANTE — Mutação amostral detecta fronteiras, mas não o erro C-1

**FATO.** Cópia de `HEAD` extraída somente em `/tmp/sentinela-auditoria-f3-copia`; `tests/test_backtest_pit_retornos.py` e `tests/test_serie_ajustada.py` deram **95 passed**. Na cópia, a mutação `ex <= limite` → `ex < limite` em `retorno_total` e a inversão do predicado `ativo_emitido != isin` em `serie_do_banco` resultaram em **7 failed, 88 passed**. A suíte de `serie_ajustada` verifica outra espécie (`tests/test_serie_ajustada.py:160-181`), mas o teste de `_retornos` em `tests/test_backtest_pit_retornos.py:245-265` cobre ISIN de origem de outra espécie, não `ativo_emitido` diferente com ISIN de origem igual. Daí o erro C-1 escapar. O golden em `tests/golden_motores.py:65-73` usa `as_of` fixo e `tests/fixtures/golden_motores.jsonl` contém casos sintéticos em 2026; testes históricos separados existem, mas **esse golden não é uma fotografia de uma data passada contra fonte PIT**. **Reproduzir:** rodar os dois arquivos de teste na cópia antes/depois dessas duas mutações, com `--basetemp` fora do repositório; inspecionar os casos do golden por `as_of` sem regravar o arquivo.

## F. Cobertura atual

### F-1 — IMPORTANTE — 348 análises com campo obrigatório ausente; MRSA3B fora do denominador

**FATO.** Contagem das linhas de `outputs/f3-9b-medida/hoje/linhas.jsonl`: 845 entradas, 844 analisadas, 348 com `faltando` (FUNDO 298, STOCK 49, UNIT 1). Ocorrências de campo, que se sobrepõem: FUNDO `pl` 184, `pvp` 288, `roe` 289, `dy` 255; STOCK `pl` 26, `pvp` 1, `roe` 28, `dy` 1; UNIT `pl` 1. Entre fundos, 170 faltam os quatro campos, 77 faltam P/VP+ROE+DY, 28 P/VP+ROE; sete faltam apenas DY. A linha MRSA3B é `sem_dados=true` e não integra os 348. O banco **tem** 285 preços COTAHIST de MRSA3B, até 2026-11-11; logo “sem dados” se refere à cascata atual, cujo preço vem de yfinance/brapi e que retorna `None` se não obtém fonte de preço (`market_engine.py:545-559`), não à inexistência de preços históricos. A causa exata da falha de ambas as fontes correntes não foi medida.

**Fontes/limite:** o vetor `faltando` registra o campo final, não qual fonte específica falhou em cada ticker. Na cascata atual, ações tentam yfinance → brapi → CVM; fundos também usam Informe CVM e B3 (`CLAUDE.md:121-134`). Portanto atribuir os 348 a uma fonte única seria **HIPÓTESE**. `outputs/f3-9b-medida/resumo.txt:6-15` mede perda real de **zero** lentes porque `fundamentals_cache` tem zero linhas nos dois bancos; preenchimento sintético de campos altera uma lente de um fundo (BTHI11), e nenhuma das 50 ações/units. **Reproduzir:** recontar o JSONL por `classe` e cada nome em `faltando`, consultar apenas `COUNT(*)` em `fundamentals_cache`, comparar a linha de MRSA3B com `precos` e a guarda de preço da cascata. Não chamar ausência de campo de valor zero.

## G. Arquitetura

### G-1 — MENOR — Caminhos legados ainda convivem com PIT

**FATO.** `backtesting/backtest_engine.py:91,176` mantém `simular_analise_mensal` com saída `INDISPONIVEL`; o backtest PIT está em `backtesting/backtest_pit.py`. `database.py:45` ainda cria `fundamentals_cache`, embora a medida DD-85 encontre zero linhas e o leitor/escritor tenham sido aposentados (`docs/loop/diario.md:1643-1646`). `sentinela/domain/` não apresentou importação de `sentinela.data` na busca estática feita; `backtest_pit.py` e `market_engine.py` são orquestração e importam dados. **Reproduzir:** busca de chamadores de `simular_analise_mensal` e `fundamentals_cache`, e `rg 'from sentinela.data|import sentinela.data' sentinela/domain`. Não foi demonstrado que os caminhos legados sejam executados na análise PIT.

## H. Segurança e operação

### H-1 — IMPORTANTE — Banco real legível por outros usuários locais

**FATO.** `stat` de `sentinela_store.db` retorna modo **0644** e proprietário `marcos:marcos`; o esquema inclui `carteira_real` (somente o nome da tabela foi consultado, sem ler posições). Qualquer usuário local com acesso ao caminho pode ler o arquivo SQLite. **Reproduzir:** `stat -c '%a %U:%G %n' sentinela_store.db` e consulta somente de `sqlite_master`; não consultar conteúdo privado. Não se verificaram permissões dos diretórios ancestrais nem usuários efetivos, portanto a exposição prática é **HIPÓTESE** dependente deles.

**Outras verificações limitadas:** `git ls-files` e nomes do histórico só revelaram `.env.example` entre nomes sugestivos de segredo; não li `.env` nem varri valores secretos no histórico. SQL dinâmico encontrado em `leitura.py:184`, `b3_cotahist.py:345-350`, `store/unico.py:133,198` e `store/backup.py:87` compõe identificadores/condições internos; parâmetros externos observados usam `?`. Há testes de restauração de banco sintético em `tests/test_store_backup.py:81-120` e teste de restauração na CLI (`backup.py:189-217`); **não foi testada aqui** a restauração operacional do banco real. Validação de todas as entradas externas não foi auditada.

## I. Documentação e decisões

### I-1 — MENOR — Documentação do cache diverge da DD-85

**FATO.** `CLAUDE.md:134` ainda descreve “10. cache SQLite (7d)”; `market_engine.py:581-588` declara que o cache saiu em F3-9b, e `docs/loop/diario.md:1643-1646` registra a decisão DD-85. A revisão pendente em `outputs/f3-9b-medida/resumo.txt:6-15` confirma **0 perdas reais** com cache vazio e exposição condicional de até um FII com DY faltante; não prova equivalência para um banco cujo cache estivesse preenchido. `AGENTS.md` já descreve a Fase 3 e o cache aposentado no contexto, mas ainda pede cautela com a divergência documental do passo 10. **Reproduzir:** cotejar as três linhas e recontar o JSONL da medida. Esta é revisão da DD-85, não aprovação retroativa de seu aceite condicional.

## o que não foi auditado

- Não comparei os quatro PRECO nem os sete G-NONE/NUM com documentos/COTAHIST originais fora do banco; a peça `None` exata dos seis e o campo exato do NUM continuam indeterminados.
- Não fiz revisão exaustiva de todas as 844 análises, de todos os pares de retorno, de todas as versões históricas das fontes, nem da identidade temporal dos FIIs. A sonda de retorno examinada é STOCK/UNIT; FII não integra seus 1.015 pares.
- Não fiz suíte completa, mutmut 3 integral, varredura de segredos por conteúdo/histórico, teste de restauração do banco real, validação de todas as entradas externas ou download de fonte. As mutações foram apenas duas, na cópia externa.
- Não executei análises com relógio simulado, nem prova de revisão macro/proventos entre coletas; A-1 e A-2 conservam explicitamente o limite de hipótese.
