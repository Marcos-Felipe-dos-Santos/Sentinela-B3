# Resumo da Fase 3-b para o checkpoint

**Status:** os 31 itens da 3-b estão concluídos no branch `v2/fase-3`, entre o fechamento do checkpoint da 3-a (`1eb01f0`) e o commit `675f24d` (F3-3e). Os 46 commits do intervalo (31 itens e 15 registros) são todos `Executor: claude-code`. Não houve push nem PR. Este resumo prepara o `[DECISÃO]` do checkpoint da 3-b. A próxima parada planejada é a ficha do backtest (F3-F1), sempre do Marcos.

## Itens e commits

| Item | Commit | Executor | Título |
|---|---|---|---|
| F3-L1 | `211c2d5` | claude-code | docs: measure point-in-time source availability |
| F3-P12 | `603727f` | claude-code | docs: specify strict history contract for FII reports and rates |
| F3-1c-a | `79bca53` | claude-code | feat: compute the real rate at a past date |
| F3-1c | `419f010` | claude-code | feat: store historical real-rate inputs by date |
| F3-3a | `7624f5f` | claude-code | feat: add point-in-time statement tables |
| F3-3b | `8dad17e` | claude-code | feat: ingest CVM statements with delivery versions |
| F3-A-F6 | `b3b21f1` | claude-code | fix: store each Selic window with its own provenance |
| F3-3c | `5cdbf2a` | claude-code | feat: read statements as delivered up to as_of |
| F3-3c-fix | `17a1dd3` | claude-code | fix: report partial FII reports and per-month unreadable versions |
| F3-A-F7 | `0bf7dd8` | claude-code | fix: store Treasury history without aborting on duplicate rows |
| F3-A-F7b | `0e66316` | claude-code | fix: read the Treasury history from its latest collection |
| F3-A-F8 | `2d1d504` | claude-code | fix: keep unpublished IPCA months out and complete the bank registry |
| F3-A-F9 | `3c96c85` | claude-code | fix: find the December Focus edition in early January |
| F3-A-F10 | `7dfb0df` | claude-code | fix: pass the cascade as_of to the real rate |
| F3-4a | `926d331` | claude-code | feat: store long COTAHIST price history |
| F3-4b | `cf8b36e` | claude-code | feat: store corporate events with official B3 factors |
| F3-4c | `d75ab34` | claude-code | feat: build event-adjusted price series separate from raw prices |
| F3-5 | `852aa86` | claude-code | feat: build point-in-time universe including delisted companies |
| F3-5-fix | `c4bd010` | claude-code | fix: drop companies whose latest FCA lists no securities |
| F3-P14a | `304b37a` | claude-code | docs: specify the annual dividend calendar producer |
| F3-P14b | `c859f76` | claude-code | feat: produce the annual dividend calendar for the quality lens |
| F3-7a | `9df3bc9` | claude-code | feat: store cash distributions and benchmarks by date |
| F3-7b | `8685525` | claude-code | feat: backfill point-in-time history with cash distributions and benchmarks |
| F3-3b-fix | `1ec90ed` | claude-code | fix: load legacy FII reports and withhold conflicting CVM documents |
| F3-3d | `e654cba` | claude-code | feat: connect point-in-time readers to the analysis service |
| F3-3e | `675f24d` | claude-code | fix: prove historical availability by delivery in the engine guards |
| F3-P07 | `5487b7d` | claude-code | docs: study preferred share identity without FCA symbol |
| F3-P09 | `3b29f85` | claude-code | docs: study ON/PN attribution of distinct rights |
| F3-P10 | `5828654` | claude-code | docs: study scope of health and benefit operators |
| F3-P11 | `6261970` | claude-code | docs: study the reading model and undemonstrated sources |
| F3-P15 | `1c16bcb` | claude-code | docs: specify detection of corporate reorganizations |

### Commits fora dos itens (registro, bloqueio e ajuste)

| Commit | Executor | Título |
|---|---|---|
| `a4faeee` | claude-code | docs: raise the raw data volume stop limit to 100 GB |
| `ea5b53c` | claude-code | docs: close the post-L1 decision with the measured numbers |
| `d5f6146` | claude-code | docs: split F3-1c and record the IBGE calendar coverage |
| `334e871` | claude-code | test: record BUG-3-18 Selic stored with the first window hash as strict xfail |
| `3c1d584` | claude-code | docs: record pending Gemini findings and provenance gaps |
| `7764aeb` | claude-code | docs: record reader edge cases from the F3-3c review |
| `edd040d` | claude-code | docs: keep tests and mutation runs out of the tmpfs /tmp |
| `65c0e64` | claude-code | test: record Gemini audit findings 2 to 5 as strict xfail |
| `cc29cd2` | claude-code | test: record BUG-3-23 Treasury conflict kept across collections as strict xfail |
| `3b0b4f0` | claude-code | docs: record Focus and real-rate follow-ups from the F3-A reviews |
| `7c49280` | claude-code | docs: block F3-3d pending the CVM cut decision |
| `1c28d68` | claude-code | docs: review codex delegated decisions and apply DD-60 |
| `a34c8c1` | claude-code | docs: unblock F3-3d by the strict cut already decided (DD-61); sem revisão leve (desvio no diário) |
| `5f87185` | claude-code | docs: correct the F3-3e question |
| `5af1831` | claude-code | docs: record the phase 3-b cross audit |

## Testes

| Momento | Suíte | Golden SHA256 |
|---|---|---|
| Começo da 3-b (`1eb01f0`, diário) | 4188 passed, 1 skipped, 6 xfailed | `500645a3263ad25e…bcc` |
| Agora (`675f24d`) | 4823 passed, 1 skipped, 0 xfailed | `500645a3263ad25e…bcc` |

São +635 PASS. Os seis xfails do começo da 3-b e os criados nela (BUG-3-15 a BUG-3-27) estão todos em PASS: nenhum xfail estrito ficou aberto. Ruff CI e Ruff completo estão verdes. A mutação de cada item, sempre acima de 80% no código tocado, está no diário.

## Gate da 3-b

- **Só o que existia em D chega ao motor** (F3-3d, F3-3e). Com `as_of` passado, o serviço usa a cascata do banco único: ZIPs da CVM remontados como existiam em D, preço do último pregão antes de D, índice em D, proventos pela aprovação antes de D e taxa real pelo `series_macro`. Não usa yfinance, brapi, IF.data, cache nem pares.
  - O [e2e] `tests/test_servico_historico.py` põe valor corrente e histórico diferentes no preço e na demonstração. Espiões falham se uma fonte corrente for consultada.
  - Pela decisão 40 (F3-3e), a disponibilidade em D é a data de publicação de cada fonte. A coleta continua só na proveniência.
- **Com `as_of` de hoje, nada muda.** O golden tem o mesmo SHA em todos os commits. O recorte e a marca da data passada só valem para um dia anterior a hoje no fuso de São Paulo, com teste também com o relógio do sistema em UTC.
  - Ressalva herdada da 3-a: o harness do golden usa `as_of` fixo (20/10/2026). O caminho com `as_of` = hoje é provado pelos testes do F3-6c, da tela e do recorte.
- **O banco real foi alterado só com backup verificado antes** (política §3, caso 3):
  - `outputs/f3-7b-backup/` antes do backfill;
  - `outputs/f3-3b-fix-backup/` antes da releitura.

  Um teste abriu o banco real uma vez, só para leitura, durante o F3-3d. O banco não foi escrito. O desvio está registrado em `pendencias.md` e foi corrigido antes do commit.

## Volume real

| Medida | Valor | Projeção do L1 |
|---|---:|---:|
| Brutos baixados (`data/fontes/backfill/`) | 1,27 GB | 1,26 GB |
| Banco único (`sentinela_store.db`) | 32,5 GB | 16,7 GB (18,0 GB com os brutos) |
| Disco livre | 903 GB | — |

Os brutos ficaram na projeção, muito abaixo do limite de 100 GB da decisão 39. O banco ficou cerca de 1,9 vez acima da projeção, porque o ITR tem de 2,5 a 3,7 milhões de linhas por ano. O detalhe está em `docs/decisoes/backfill-fase3.md` §5.

## Cobertura do histórico por fonte e ano

| Fonte | Anos | Arquivos | Linhas gravadas | Observação |
|---|---|---:|---:|---|
| FCA | 2010 a 2026 | 17 | 144.995 | sem código de negociação antes da referência de 2018 (F3-P07, DD-60) |
| DFP | 2010 a 2026 | 17 | 16.979.816 | 2026 parcial |
| ITR | 2011 a 2026 | 16 | 49.927.011 | o ITR aberto começa em 2011 |
| Informe de FII | 2016 a 2026 | 11 | 192.724 + 58.224 da releitura (2016 a 2020, BUG-3-25) | leiaute anterior à Resolução 175 até 2020 |
| COTAHIST anual | 2010 a 2026 | 17 | 3.136.594 | uma linha de 2026 recusada (campo ilegível) |
| Ibovespa (B3) | 2010 a 2026 | 17 | 4.182 fechamentos | de 245 a 251 por ano completo |
| CDI (SGS 12) | 1986 a 2026 | — | 10.180 taxas | — |
| Macro (Tesouro, ANBIMA, Focus, IPCA, Selic) | conforme cada série | — | 130.908 linhas | `series_macro` |
| Proventos em dinheiro (B3) | conforme a companhia | 323 coletas | 19.170 registros | só companhias listadas hoje (DD-35); identidade conferida em 138 delas |

**Universo em D** (`docs/decisoes/identidade-preferenciais-3.md` §4):
- FIIs a partir de 2016 (46 no fim de 2016; 298 em meados de 2022).
- Ações só a partir da primeira entrega do FCA com código, no primeiro semestre de 2018 (293 em 28/09/2018). Antes disso, `sem_identificacao` (DD-60).

**Proventos com identidade conferida**: de 19% a 28% das companhias com FCA provado por ano, um teto (`backfill-fase3.md` §4).

## Versões observáveis

- As DFPs, os ITRs e os FCAs abertos guardam só a última versão de cada documento (DD-34). No estrito, a versão vigente em D sem números na fonte se abstém; a última versão, com o aviso, só entra no modo exploratório (adendo de 09/11, DD-64).
- Arquivos com mais de uma versão do mesmo documento: FCA de 2022, DFP de 2021 e Informe de 2021 e 2025.
- Pelo FCA, de 102 (2010) a 456 (2021) companhias por fim de ano ficam `sem_prova` em D (DD-53).
- Conflitos da CVM, a mesma chave com valores diferentes: 1.099 casos distintos em `conflitos_carga`. O documento sai da leitura com o motivo (DD-57). No índice do FCA, vale a entrega mais tardia (DD-58).

## Propostas dos estudos para decisão

| Estudo | Proposta | Onde |
|---|---|---|
| F3-P07, preferencial sem sigla no FCA | `fix:` pela especificação e pelo ISIN do COTAHIST do mesmo código; resolve CGAS5, e EKTR4 continua abstendo. Também: o FCA aberto não tem código antes de 2018, com três caminhos para o universo de ações antes disso (DD-60 aplicou o caminho (a)) | `docs/decisoes/identidade-preferenciais-3.md` §3 e §4 |
| F3-P09, direitos distintos ON/PN | ficha com tabela de referência curada (FRE 18.1 ou estatuto) para VPA e D0; sem linha, regra atual com aviso; 54 de 121 companhias com LPA diferente por classe | `docs/decisoes/direitos-on-pn-3.md` §4 |
| F3-P10, escopo de saúde e benefícios | quatro caminhos, sem limiar: manter, materialidade por valor, segmentos, operadora como escopo próprio; histórico de quando cada ticker mudou | `docs/decisoes/escopo-saude-beneficios-3.md` §4 |
| F3-P11, modelo de leitura | manter; ler pelo BPP da última DFP entregue antes de D, com corte da janela na troca; BPP individual sem consolidado | `docs/decisoes/modelo-de-leitura-3.md` §3 |
| F3-P15, reorganizações | ruptura por evento da B3, comparativo reapresentado, fato relevante do IPE e ações emitidas sem evento (caso da Azzas 2154); limiares a decidir | `docs/decisoes/reorganizacoes-3.md` §3 |

## Decisões do Marcos e decisões delegadas

**Decisões do Marcos nesta metade:** 37 a 39 (auditor e volume, 11/11) e 40 (disponibilidade pela publicação, 13/11, aplicada no F3-3e).

**Decisões delegadas da 3-b:** DD-34 a DD-65, todas da família claude-code. O texto de cada uma, no formato da política, está em `docs/loop/pendencias.md`. As que mais pedem ratificação:
- **DD-34:** só a última versão nas fontes abertas.
- **DD-35:** proventos de deslistadas sem fonte.
- **DD-53:** FCA vigente sem conteúdo fica `sem_prova`.
- **DD-57 e DD-58:** conflitos da carga.
- **DD-60:** universo de ações a partir de 2018, contra a decisão 4.
- **DD-61:** corte da série CVM pela entrega, que muda o `test_bug_3_12`.
- **DD-62:** remontagem dos ZIPs.
- **DD-63:** IA desligada em data passada.
- **DD-64:** decisão 40 lida com o adendo de 09/11.
- **DD-65:** alcance da decisão 40, com a lista do F3-3e ampliada até `methods/qualidade.py`.

**Revisões cruzadas:** a família claude-code revisou as DD-12 a DD-22 do Codex e marcou todas como "confere" (`pendencias.md`). As DD-34 a DD-65 esperam o "confere" ou "contesta" do Codex.

## Pendências principais, antes do F3-8

Todas registradas em `pendencias.md`. Numa data passada, ainda não há número para:
- **FII e Lynch:** falta DY no histórico, que hoje só vem do yfinance e da brapi.
- **Bazin:** falta a montagem pelo preço do COTAHIST.
- **Graham e Lynch:** falta o IPCA de fim de exercício pelo `series_macro`.
- **Gordon e Bancos:** falta a taxa real com as séries do `series_macro` carregadas. O backfill gravou o macro, mas o [e2e] usa um banco sem série.

Outros pontos:
- custo e disco da remontagem e do recorte no backtest;
- Selic do FII histórico pela rede;
- duas fontes de "hoje";
- modo exploratório no registro do resultado.

## Resíduos para o Marcos

Todos fora do git. Nada foi apagado (decisão 35).

**Dados:**
- `data/fontes/backfill/` (1,27 GB de brutos);
- `data/fontes/l1/cvm/fre/`;
- `data/cache/historico/2026-11-09/` (do desvio do F3-3d);
- `data/cvm/recorte/` (se houver);
- o banco `sentinela_store.db` (32,5 GB).

**Saídas:**
- `outputs/backfill/` (estado, relatórios e logs);
- `outputs/f3-7b-backup/` e `outputs/f3-3b-fix-backup/`;
- logs e estatísticas de mutação `outputs/f3-*-mutmut-*` e `outputs/mutmut-stats-*`.

**Cache do executor:** `~/.cache/sentinela-testes-claude/`, com os scripts de medição dos estudos.

## O que auditar primeiro (família Codex sobre os commits claude-code)

O relatório da auditoria cruzada da 3-b está em `docs/loop/auditorias/3-b-claude-code.md`. Nenhum commit do Codex caiu na 3-b. Por risco, a ordem para o Codex auditar é:

1. `e654cba` F3-3d e `675f24d` F3-3e:
   - o motor histórico e a remontagem;
   - o recorte pela entrega;
   - a marca da data passada em todas as guardas;
   - a ampliação da DD-65 até `methods/qualidade.py`.
2. `1ec90ed` F3-3b-fix e `8685525` F3-7b: a releitura e o backfill no banco real, conferindo os backups.
3. `852aa86` e `c4bd010` (F3-5): o universo em D e a DD-60.
4. `5cdbf2a` F3-3c: o leitor estrito, base de todo o histórico.
5. As decisões delegadas DD-34 a DD-65.
