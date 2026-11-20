# Fase 3 — tempo como entrada

A fase faz a data de análise virar entrada: `AnalysisService.analisar(ticker, as_of)` responde por uma data passada lendo só o banco único (`MotorHistorico`), com as fontes oficiais carregadas ponto no tempo (CVM, COTAHIST, B3, macro), a disponibilidade pela data de publicação (decisão 40) e as abstenções com motivo; o backtest ponto no tempo (`backtesting/backtest_pit.py`) mede as lentes por data, lente e motivo. Não é recomendação nem sugestão de carteira.

Branch `v2/fase-3`, a partir da `main` `284165f`; ativação em `da0a78c`. Fila, diário, resumos das metades e este resumo arquivados em `docs/loop/historico/fase-3/` neste item. A fila ativa passa a ter o F3-10c (README, pedido do Marcos em 19/11/2026) e o `[DECISÃO]` do checkpoint.

## Gate da fase (PLANO §6, decisão 4 do Marcos de 15/11/2026)

| Condição | Demonstração |
|---|---|
| `as_of` = hoje reproduz o resultado atual | golden dos motores com o mesmo SHA256 `500645a3263ad25e…bcc` da baseline em todos os gates da fase; `test_equivalencia_motores.py` e seções A, B e C de `test_financeiro_pre_refactor.py` intactas |
| Backtest reprodutível | `test_backtest_pit_e2e.py`: duas execuções com o mesmo `hash_insumos`, `hash_resultado` e observações, recálculo imutável em `resultados_analise` |
| Operacional por amostra declarada, com cobertura por lente e ano e abstenção com motivo | sonda final única do F3-3D-SONDA (oito datas de junho de 2018 a 2025, universo elegível inteiro): 15.292 observações; cobertura por lente e ano no diário arquivado e em `outputs/f3-3d-sonda/cobertura.txt`; a varredura completa fica como limitação registrada |
| Universo com deslistadas | `test_universo_pit.py` (ALL e Americanas pelo FCA oficial, BUG-3-24, `sem_identificacao`); universo em D com correções e identidades oficiais cortadas por data (BUG-3-55, DD-89) |
| Limitações na proveniência | abstenções com motivo por campo e fonte; exploratório separado e rotulado (D17); limitações declaradas abaixo |

## Cobertura da sonda final (12 meses)

Por lente e ano de D: com valor / universo da lente (com valor e retorno), na sonda única do F3-3D-SONDA, depois da recoleta da B3. Fonte: `outputs/f3-3d-sonda/sonda/observacoes.json` (fora do git), conta reproduzível por `outputs/f3-3d-sonda/cobertura.py`.

| Lente | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|
| Bancos | 0/75 (0) | 0/86 (0) | 0/124 (0) | 0/115 (0) | 0/152 (0) | 3/173 (2) | 1/146 (0) | 3/145 (0) |
| Bazin | 3/75 (3) | 2/86 (2) | 1/124 (1) | 2/115 (2) | 14/152 (14) | 7/173 (7) | 13/146 (12) | 15/145 (15) |
| Gordon | 0/75 (0) | 0/86 (0) | 1/124 (1) | 22/115 (10) | 44/152 (13) | 43/173 (14) | 40/146 (21) | 39/145 (17) |
| Graham | 0/75 (0) | 0/86 (0) | 0/124 (0) | 0/115 (0) | 0/152 (0) | 0/173 (0) | 0/146 (0) | 41/145 (15) |
| Lynch | 0/75 (0) | 0/86 (0) | 0/124 (0) | 0/115 (0) | 0/152 (0) | 0/173 (0) | 0/146 (0) | 1/145 (1) |
| Rendimento do FII | 0/40 (0) | 0/59 (0) | 0/94 (0) | 0/122 (0) | 0/134 (0) | 0/141 (0) | 0/156 (0) | 0/150 (0) |

## Testes

| Momento | Suíte | Golden |
|---|---|---|
| Ativação (`da0a78c`) | 3599 passed, 1 skipped, 8 xfailed | `500645a3…bcc` |
| Fim da 3-b (`675f24d`) | 4823 passed, 1 skipped, 0 xfailed | igual |
| Agora (fim da 3-d) | 5181 passed, 1 skipped, 24 xfailed | igual |

Os 24 xfails estritos são limitações declaradas: 8 do BUG-3-49 (F3-AUD-GA1b) e 15 do BUG-3-50 (F3-AUD-GA2b), pelas decisões 49 e 50, e 1 do FII no E2E (decisão do Marcos de 19/11). Todos têm destino na proposta da Fase 4 (`docs/loop/fila-fase4-proposta.md`, bloco H). Ruff CI e Ruff completo em `sentinela/data` e `sentinela/methods` verdes; mutação acima de 80% nas funções tocadas, item a item, no diário.

## Itens, commits e executores

175 commits em `main..HEAD` antes deste (`git log --oneline main..HEAD`); pela linha `Executor:`, claude-code em 155 e codex em 20. Resumo das metades: `resumo-3a.md` e `resumo-3b.md` (arquivados). Depois deste item, a fila nova leva o último item da fase, F3-10c (README do fim da Fase 3, pedido do Marcos em 19/11/2026), antes do `[DECISÃO]`. Na 3-c e na 3-d: o backtest ponto no tempo e a banda neutra só como proposta (F3-8), a limpeza (F3-9), a auditoria completa da fase (Gemini e Codex, `docs/loop/auditorias/fase-3-*.md`) e os itens de cada achado (F3-AUD-*, BUG-3-44 a BUG-3-58), o E2E pelos produtores reais, a recoleta da B3 com backup verificado, a sonda final e a proposta da Fase 4.

```
63f3068 docs: propose the phase 4 queue
4e82941 docs: run the final historical probe once
0ec4cf7 chore: collect B3 issuer dividends for all eight dates
1fb7b8a test: prove historical numeric lenses through real producers
97f929a docs: record Marcos decisions of 19/11 and add the README item
2170e22 fix: decide historical availability by the service date, not the clock
34ba4ac test: vary the clock with a fixed historical service date
5b0bc77 docs: record unconfirmed finding for distinct dividend dates test
fb62f4c docs: diagnose the missing TGMA3 window field
65d481b fix: name missing Gordon input fields
10e89ea fix: report backtest abstentions by date and real lens
b0a2c5c fix: load proven identity corrections in historical consumers
1a3298b fix: exclude record dates at the return horizon
4bb3270 fix: cut corporate action factors by publication
7fd3cc2 fix: cut historical equity events by publication
70b855c fix: exclude open and future FII reference months
508c5ae docs: close GA1b and GA2b with declared phase 3 limitation (decision 50)
11d67c5 docs: let phase 3 audit items continue after a third code rejection
ee90214 fix: abstain final CVM year when its delivered DFP is unreadable at D
0f6cc0b docs: show V1 to V2 evolution in README
2ea5f2a fix: abstain unavailable current FII document versions
6153707 fix: cut terminal FCA evidence at horizon deliveries
11db38a fix: require evidence for terminal trading state
6aa7932 fix: abstain unsupported cash event natures in backtests
19ed708 fix: derive backtest dividend species from proven ISIN
a341ae2 docs: schedule the authorized phase 3 audit follow-up
3b04b57 fix: disable destructive database reset
2fe4d1e docs: archive phase 3 audits and cross-review delegated decisions
9b0e74c fix: abstain returns for events issuing a different security
5d7c3f0 chore: remove the retired audit script
d4bef87 test: guard the BUG-2C-58 invariant in the app lens presenter
4222554 refactor: move tickers_oficiais to the ticker domain module
7b995c1 docs: record the Marcos decisions of 2026-11-16 night and the HGLG share issuance finding
e524819 chore: remove the retired database maintenance script
bbd529a chore: retire the legacy cascade cache
2e2125d refactor: remove duplicated orchestration from app.py
7b233e3 docs: survey the source of FII distributions for the historical total return
690976d docs: measure the neutral band on the full eligible stock universe at the declared dates
4e829bf docs: survey share counts for fiscal years before 2020
b88dbee docs: record the Marcos decisions of 16/11 and queue F3-8j-uni
1beca25 fix: read the fund in the pre-2021 FII Informe layout
7800b17 docs: rerun the neutral band proposal on the declared sample and record why no band can form
86cd60d test: register BUG-3-42 and queue F3-8j-fii for the pre-2021 FII Informe layout
8529e01 docs: allow the executor to delete the mutmut cache, as policy section 4 says
82914db docs: wait on a saved PID or output file, never on a self-matching pgrep
d3933b7 fix: accept the annual COTAHIST generated on the last trading day as full coverage
1cbb929 docs: close F3-8i with proof that the historical real rate already reads series_macro
7b4ca8f test: register BUG-3-41 and ratify DD-79 and DD-80 (decision 44)
6a54c71 docs: require Brazilian Portuguese in every answer
2994f72 feat: measure historical dividend yield from stored B3 dividends and COTAHIST
9305449 fix: require stored COTAHIST coverage for the historical ex-date calendar
a3607e9 feat: assemble the historical Bazin block from the COTAHIST price
b4be279 fix: abstain on a fiscal year without an end date before the IPCA window
7aa48d6 docs: load the monthly IPCA into the stored macro series
caf48c3 feat: read year-end IPCA for the historical windows from the stored series
c003f5e refactor: extract the IPCA index computation from the SIDRA download
8b09423 docs: recollect B3 cash distributions for the declared sample
808fa74 fix: prove the ticker ISIN from the COTAHIST session before abstaining on issuer identity
57bb9aa docs: record Marcos's 15/11 decisions and queue F3-8d-fix
3ba9ee3 perf: reuse the historical CVM reassembly across analyses of the same day
4d04b3c docs: propose neutral band calibration out of sample
3d498d9 docs: record Marcos's ratifications of F3-8b decisions
2dfe5ac chore: remove fabricated backtest CSVs
e2e4338 feat: run the point-in-time lens backtest
e6b3bf9 test: specify the point-in-time backtest contract
41f1b01 docs: approve the backtest specification after the focused audit
29d14c9 docs: align backtest reinvestment and return boundaries
648d769 docs: record backtest specification audit and decision reviews
07c8034 docs: write the point-in-time backtest specification
f26789a docs: close the 3-b checkpoint with the step 6 annotation
341243c docs: summarize phase 3-b
675f24d fix: prove historical availability by delivery in the engine guards
5af1831 docs: record the phase 3-b cross audit
5f87185 docs: correct the F3-3e question
e654cba feat: connect point-in-time readers to the analysis service
a34c8c1 docs: unblock F3-3d by the strict cut already decided (DD-61)
1c16bcb docs: specify detection of corporate reorganizations
6261970 docs: study the reading model and undemonstrated sources
5828654 docs: study scope of health and benefit operators
3b29f85 docs: study ON/PN attribution of distinct rights
1c28d68 docs: review codex delegated decisions and apply DD-60
5487b7d docs: study preferred share identity without FCA symbol
7c49280 docs: block F3-3d pending the CVM cut decision
1ec90ed fix: load legacy FII reports and withhold conflicting CVM documents
8685525 feat: backfill point-in-time history with cash distributions and benchmarks
9df3bc9 feat: store cash distributions and benchmarks by date
c859f76 feat: produce the annual dividend calendar for the quality lens
304b37a docs: specify the annual dividend calendar producer
c4bd010 fix: drop companies whose latest FCA lists no securities
852aa86 feat: build point-in-time universe including delisted companies
d75ab34 feat: build event-adjusted price series separate from raw prices
cf8b36e feat: store corporate events with official B3 factors
926d331 feat: store long COTAHIST price history
3b0b4f0 docs: record Focus and real-rate follow-ups from the F3-A reviews
7dfb0df fix: pass the cascade as_of to the real rate
3c96c85 fix: find the December Focus edition in early January
2d1d504 fix: keep unpublished IPCA months out and complete the bank registry
0e66316 fix: read the Treasury history from its latest collection
cc29cd2 test: record BUG-3-23 Treasury conflict kept across collections as strict xfail
0bf7dd8 fix: store Treasury history without aborting on duplicate rows
65c0e64 test: record Gemini audit findings 2 to 5 as strict xfail
edd040d docs: keep tests and mutation runs out of the tmpfs /tmp
17a1dd3 fix: report partial FII reports and per-month unreadable versions
7764aeb docs: record reader edge cases from the F3-3c review
5cdbf2a feat: read statements as delivered up to as_of
3c1d584 docs: record pending Gemini findings and provenance gaps
b3b21f1 fix: store each Selic window with its own provenance
334e871 test: record BUG-3-18 Selic stored with the first window hash as strict xfail
8dad17e feat: ingest CVM statements with delivery versions
7624f5f feat: add point-in-time statement tables
419f010 feat: store historical real-rate inputs by date
79bca53 feat: compute the real rate at a past date
d5f6146 docs: split F3-1c and record the IBGE calendar coverage
603727f docs: specify strict history contract for FII reports and rates
ea5b53c docs: close the post-L1 decision with the measured numbers
211c2d5 docs: measure point-in-time source availability
a4faeee docs: raise the raw data volume stop limit to 100 GB
1eb01f0 docs: close the 3-a checkpoint with the DD-31 annotation
7403a6e fix: accept only a valid last close as the yfinance price
5f947db test: exercise the FII Selic production path with as_of today
b8673fd test: record BUG-3-17 invalid yfinance last close as strict xfail
a821324 fix: record the price date at the cascade boundary
b34bb82 test: raise the ai_core mutation score to the module gate
fa26766 fix: check the staged golden blob in the gate
1528e57 docs: record the phase 3-a cross audit and its regression tests
cf76415 docs: summarize phase 3-a
d7043fc docs: record the phase 3 process rules in the phase cycle
d1aac6e feat: run the cross-family audit from the loop
0d57094 docs: record F3-0e as blocked after the fourth review rejection
4cdd991 feat: add the phase closing script
966c4d6 docs: record F3-0e as blocked after the third review rejection
9f952f7 feat: add a mechanical gate runner for queue items
89fcaa6 fix: identify inferred asset class in the AI context
a8265d4 fix: use explicit as_of in the CVM series cut
c57e34b feat: pass as_of from the service through cascade and engines
33acf20 refactor: call AnalysisService from the Streamlit app
917994e feat: orchestrate analysis through AnalysisService with as_of
9ae3006 feat: store immutable analysis results by ticker, as_of, method and version
82984cd feat: migrate both local databases into the single store
be7a33d refactor: wrap the by-date macro record docstring
83e83d3 fix: keep provenance and finite results in macro by date
2380f4d fix: keep each backup run in its own stamped folder
554f6fe fix: resolve B3 issuer by CVM code
418fc15 docs: record autonomous decision policy, decisions 33-36 and regressions BUG-3-06 to BUG-3-10
4701c1e feat: add numbered SQLite migrations with schema version
9dd62d8 feat: add verified SQLite backup and restore
291971b fix: keep average cost on partial position reduction
2860508 docs: block F3-P01 again pending ISIN check rule for B3 dividends
f9af84f docs: record decisions 30-32 and add regressions BUG-3-03 to BUG-3-05
d5556d8 fix: reject FII reports when every version is unreadable
76be92e fix: weight unit components in reported EPS check
cb93c6f fix: report FII report failures in data risks
f2ed7c4 docs: block F3-P01 pending decision on B3 issuer resolution
8891765 fix: escape OData literals for IF.data institution codes
a27b0f6 feat: provide macro context by date from full SGS series
f4af8fd fix: stop network access when importing config
da0a78c chore: activate phase 3 queue
2b677a3 docs: record round 5 approval and decision 29, close F3-0 block 1 and archive its queue and journal
1299ccb docs: incorporate the fourth F3-0 addendum and decisions 25 to 28 into the phase 3 proposal
018d359 docs: record decision 24 on tolerant verdict parsing in F3-0f and the F3-0h pending note
6a0dbe5 docs: incorporate the third F3-0 addendum and decisions 18 to 23 into the phase 3 proposal
8b619e1 docs: update the execution step for the blocked-item rule
0cd8d04 fix: treat root files as paths in queue independence
8c7bcf8 docs: queue F3-0j and F3-0k from the second F3-0 package addendum
6562cd2 docs: align the goal and the blocked-item rule
51bd10e fix: make queue independence conservative
a3288f0 docs: queue F3-0h and F3-0i from the F3-0 package addendum
adc49fd docs: let independent items continue after a blocked item
52e4068 docs: read loop files by excerpt during execution
4f7167c feat: add a queue helper for status, next item and diary entries
09ac499 docs: queue the F3-0 loop process package before phase 3 activation
03a0916 docs: incorporate round 2 document audit decisions into phase 3 proposal
b1317d0 docs: record answers to the open phase 3 proposal questions
baa5157 docs: incorporate phase 3 document audit decisions into the queue proposal
36be431 docs: propose the phase 3 queue from the approved decision package
```

## Decisões

- **Do Marcos:** do pacote da fase (`docs/decisoes/decisoes-fase3.md`) às decisões 46 a 50 e às de 19/11/2026, transcritas no diário arquivado e em `pendencias.md`. A 49 e a 50 mudaram a política só até o fim da Fase 3 (terceira reprovação de código de item de auditoria não para o loop).
- **Delegadas (DD-01 a DD-89):** texto de cada uma em `docs/loop/pendencias.md`. Pela marca na própria linha, 21 estão ratificadas e 65 não trazem a marca (parte foi tratada em bloco nos checkpoints das metades: `resumo-3a.md` e `resumo-3b.md`). Revisões cruzadas pendentes citadas na fila: DD-88 e DD-89 (esta ratificada em 19/11).

## Limitações declaradas da Fase 3

- GA1b (BUG-3-49) e GA2b (BUG-3-50), com os xfails estritos e o diff reprovado do GA2 só local em `outputs/f3-aud-ga2-d47-full-stage.patch`.
- Lente do FII com número numa data passada não provada de ponta a ponta (fixtures do HGLG11 sem COTAHIST, 13 meses do Informe e NTN-B).
- Graham e Lynch só a partir de 2025 nas datas da sonda (sem Composição do Capital antes de 2020; o FRE ficou para a Fase 4, decisão 48).
- Retorno do FII sem ligação (F3-8l); banda neutra só como proposta (Gordon 12 meses, "não calibrada, dados insuficientes").
- Escolha da coleta B3 mais recente mesmo posterior a D (Codex A-1): na sonda final, 265 retornos de 12 meses perdidos pela coleta nova sem identidade comprovada.

## Resíduos para o Marcos

- Backups em `outputs/` (fora do git): `outputs/f3-3d-col-backup/` (32,5 GB, 19/11) e os anteriores; decidir a retenção.
- `stash@{0}` (wip do GC5, já commitado) e `stash@{1}` (F3-2a-fix antigo): nada foi apagado.
- O `AGENTS.md` (seção "Fase atual", do Marcos) ainda traz a suíte de 3525 passed e 8 xfailed e descreve a fase em curso; o `CLAUDE.md` deve dizer o mesmo que ele, e a atualização é do Marcos.
- Texto antigo do `CLAUDE.md` fora do aceite deste item (por exemplo "Reconstrução ponto-no-tempo na Fase 3", a leitura de `date.today()` "(Fase 3)" e a camada `services/analyze_asset.py` listada como não conectada): revisão no checkpoint.

## O que revisar primeiro

1. As limitações declaradas e o bloco H da proposta da Fase 4.
2. As correções da auditoria que mudam valor gravado ou disponibilidade: BUG-3-53 (fator B3 pela publicação), BUG-3-55 com a DD-89, BUG-3-56 (relatório sem pseudo-lente), BUG-3-58 (relógio).
3. O efeito da recoleta na sonda final (265 retornos perdidos, Codex A-1) antes de qualquer recoleta nova.
4. As decisões delegadas sem marca de ratificação.
