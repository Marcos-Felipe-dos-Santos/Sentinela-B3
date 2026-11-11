# Resumo da Fase 3-a para o checkpoint

**Status:** os 23 itens da 3-a estão concluídos no branch `v2/fase-3`, da ativação `da0a78c` até `d7043fc` (F3-0g). Este resumo prepara o `[DECISÃO]` do checkpoint da 3-a. Não houve push nem PR. O F3-0e ficou em `[!]` duas vezes (rodadas 3 e 4) e foi entregue na quinta rodada, pelas decisões 37 e 38. Executores: Claude Code (Claude Opus 5.5) e Codex. Política de decisão autônoma em vigor desde `418fc15`.

## Itens e commits

| Item | Commit | Executor | Título |
|---|---|---|---|
| F3-1a | `f4af8fd` | claude-code | fix: stop network access when importing config |
| F3-1b | `a27b0f6` | claude-code | feat: provide macro context by date from full SGS series |
| F3-P05 | `8891765` | claude-code | fix: escape OData literals for IF.data institution codes |
| F3-P01 | `554f6fe` | claude-code | fix: resolve B3 issuer by CVM code |
| F3-P04 | `cb93c6f` | claude-code | fix: report FII report failures in data risks |
| F3-P03 | `76be92e` | claude-code | fix: weight unit components in reported EPS check |
| F3-P08 | `d5556d8` | claude-code | fix: reject FII reports when every version is unreadable |
| F3-P02 | `291971b` | claude-code | fix: keep average cost on partial position reduction |
| F3-2a | `9dd62d8` | claude-code | feat: add verified SQLite backup and restore |
| F3-2b | `4701c1e` | claude-code | feat: add numbered SQLite migrations with schema version |
| F3-2a-fix | `2380f4d` | claude-code | fix: keep each backup run in its own stamped folder |
| F3-1d | `83e83d3` | claude-code | fix: keep provenance and finite results in macro by date |
| F3-2c | `82984cd` | claude-code | feat: migrate both local databases into the single store |
| F3-2d | `9ae3006` | codex | feat: store immutable analysis results by ticker, as_of, method and version |
| F3-6a | `917994e` | codex | feat: orchestrate analysis through AnalysisService with as_of |
| F3-6b | `33acf20` | codex | refactor: call AnalysisService from the Streamlit app |
| F3-6c | `c57e34b` | codex | feat: pass as_of from the service through cascade and engines |
| F3-P13 | `a8265d4` | codex | fix: use explicit as_of in the CVM series cut |
| F3-P06 | `89fcaa6` | codex+claude-code | fix: identify inferred asset class in the AI context |
| F3-0d | `9f952f7` | claude-code | feat: add a mechanical gate runner for queue items |
| F3-0e | `d1aac6e` | claude-code | feat: run the cross-family audit from the loop |
| F3-0f | `4cdd991` | claude-code | feat: add the phase closing script |
| F3-0g | `d7043fc` | claude-code | docs: record the phase 3 process rules in the phase cycle |

### Commits fora dos itens (registro, bloqueio e ajuste)

| Commit | Executor | Título |
|---|---|---|
| `da0a78c` | claude-code | chore: activate phase 3 queue |
| `f2ed7c4` | claude-code | docs: block F3-P01 pending decision on B3 issuer resolution |
| `f9af84f` | claude-code | docs: record decisions 30-32 and add regressions BUG-3-03 to BUG-3-05 |
| `2860508` | claude-code | docs: block F3-P01 again pending ISIN check rule for B3 dividends |
| `418fc15` | claude-code | docs: record autonomous decision policy, decisions 33-36 and regressions BUG-3-06 to BUG-3-10 |
| `be7a33d` | claude-code | refactor: wrap the by-date macro record docstring |
| `966c4d6` | claude-code | docs: record F3-0e as blocked after the third review rejection |
| `0d57094` | claude-code | docs: record F3-0e as blocked after the fourth review rejection |

## Testes

| Momento | Suíte | Golden SHA256 |
|---|---|---|
| Baseline de ativação (`da0a78c`, diário) | 3599 passed, 1 skipped, 8 xfailed | `500645a3263ad25e…bcc` |
| Agora (`d7043fc`) | 4186 passed, 1 skipped, 3 xfailed | `500645a3263ad25e…bcc` |

São +587 testes. Ruff CI e Ruff completo (`sentinela/methods`, `sentinela/data`, `sentinela/data/store`) estão verdes. Os números de cada item estão no diário.

## Gate da 3-a

- **Golden com `as_of` = hoje.** O SHA256 de `tests/fixtures/golden_motores.jsonl` é `500645a3263ad25e492bff56e00c9b3552b84a243136d3397f520d4a79c24bcc`, igual ao histórico e ao de ativação. `tests/test_equivalencia_motores.py` passa (4 passed, 1 skipped), no caminho padrão dos motores, sem `as_of` explícito: a referência é hoje, e desde o F3-6c o `as_of` chega à cascata e aos motores sem mudar a grade. Nenhum item regenerou o golden.
- **Banco migrado sem perda (F3-2c).** O backup verificado e a migração rodaram nos bancos reais, com saída 0 nos dois. A conferência independente, só de leitura, achou as três tabelas de `sentinela_v6.db` iguais linha a linha no `sentinela_store.db`; `sentinela.db` estava ausente. Os registros ficam fora do git, citados sem conteúdo: `outputs/f3-2c-backup/`, `outputs/f3-2c-migracao.json` e `outputs/f3-2c-conferencia.txt`. Os bancos antigos continuam no disco até o F3-9.
- **Rede no import corrigida (E-6, F3-1a).** A regressão BUG-3-01 está em PASS. A armadilha 8 do `CLAUDE.md` e a nota do `AGENTS.md` foram atualizadas neste item (DD-04, ressalva da auditoria FASE do Codex). A "Fase atual" do `AGENTS.md` não mudou.

## Xfails restantes

| Bug | Teste | Item que corrige |
|---|---|---|
| BUG-3-03 | `tests/regressao/test_bug_3_03_informe_parcial_sem_risco.py` | F3-3c-fix (decisão 36) |
| BUG-3-04 | `tests/regressao/test_bug_3_04_versao_ilegivel_fora_do_mes_final.py` | F3-3c-fix (decisão 36) |
| BUG-3-05 | `tests/regressao/test_bug_3_05_empate_ilegivel_sem_versao_pela_ordem.py` | F3-3c-fix (decisão 36) |

Os sete bugs herdados da 2C, em oito casos xfail estritos (`tests/regressao/README.md`), foram corrigidos na 3-a. Também foram corrigidos os bugs abertos durante a própria 3-a, como o BUG-3-01 (E-6) e os da auditoria FASE do Codex (BUG-3-06 a BUG-3-10). Só ficam os três destinados ao F3-3c-fix. O registro completo está em `tests/regressao/README.md`.

## Decisões provisórias e delegadas

### Provisórias

As quatro foram decididas pelo Marcos em 10/11/2026. O texto completo está em `docs/loop/pendencias.md`.

- **F3-1b, IPCA por data:** o mês M do SGS 433 passa a valer no primeiro dia de M+2 (ou na data da coleta), porque o SGS não traz a data de divulgação. Foi aceito como provisório. O F3-1c passa a usar a data real de divulgação pelo calendário do IBGE de `macro.py`.
- **F3-1b, Selic no motor de FII:** o teste ponta a ponta ligava `MacroContext(as_of).selic` ao motor de FII pelo `get_selic_atual`. Foi ratificado até o F3-6c, que trocou esse elo pelo `as_of`.
- **F3-P03:** `tests/test_lpa_unit_ponderado.py` foi criado fora da lista de arquivos do item, só com testes. Ratificado.
- **F3-P08:** os controles do levantamento da 2C ficaram em `tests/test_fii_versao_ilegivel.py`, só com testes. Ratificado.

### Delegadas (política, §1)

O Marcos ratifica ou reverte essas decisões em lote. As das classes 2 e 3 também passam pela revisão da outra família (§2). A lista foi gerada de `docs/loop/pendencias.md`, onde está o texto completo. "Conferida" quer dizer que a outra família anotou "confere" na revisão cruzada. Do Codex, só a DD-18 é de classe 2 ou 3 (classe 3), e ela já foi conferida pelo Claude Code.

| DD | Executor | Assunto | Classe | Situação |
|---|---|---|---|---|
| DD-01 | claude-code | auditoria FASE do Codex (10/11/2026), cinco bugs propostos | classe 5 e 4, desempate 4 | aberta |
| DD-02 | claude-code | ressalva da auditoria ao F3-2b: versão do banco ausente do diretório aceita em silêncio | classe 6, desempate 4 | aberta |
| DD-03 | claude-code | ressalva da auditoria ao BUG-2C-11: regressão verde sem composição | classe 6, desempate 5 | aberta |
| DD-04 | claude-code | ressalva da auditoria ao F3-1a: `CLAUDE.md` e `AGENTS.md` ainda descrevem rede no import | classe 6, desempate 4 | aberta |
| DD-05 | claude-code | F3-P01, onde a conferência da decisão 33 entra no caminho de produção | classe 2, desempate 5 | conferida pela outra família |
| DD-06 | claude-code | F3-P01, leitura da decisão 33 (b) | classe 2, desempate 1 e 6 | conferida pela outra família |
| DD-07 | claude-code | F3-P01, fixture e testes | classe 4, desempate 6 | aberta |
| DD-08 | claude-code | F3-2a-fix, "erro gera relatório separado" | classe 4, desempate 3 e 6 | aberta |
| DD-09 | claude-code | F3-2c, nome e lugar do banco único | classe 4, desempate 6 | aberta |
| DD-10 | claude-code | F3-2c, classes sem caminho | classe 1, desempate 1 e 5 | aberta |
| DD-11 | claude-code | F3-2c, conferência da migração | classe 3, desempate 1 | conferida pela outra família |
| DD-12 | codex | F3-2d, formato técnico do hash | classe 4, desempate 3 e 6 | aberta |
| DD-13 | codex | F3-6a, referência de hoje e identidade da execução | classe 4, desempate 3 e 6 | aberta |
| DD-14 | codex | revisão do F3-6a, escape de as_of na API antiga | classes 5 e 6, desempate 4 | aberta |
| DD-15 | codex | tmpfs cheio durante a verificação | classe 4, desempate 3 | aberta |
| DD-16 | codex | F3-6b, como conservar a orquestração antiga até F3-9a sem executá-la duas vezes | classe 4, desempate 3 e 6 | aberta |
| DD-17 | codex | F3-6c, ligação do serviço à cascata sem quebrar adaptadores antigos | classe 4, desempate 3 e 4 | aberta |
| DD-18 | codex | F3-6c, relógios de MacroProvider usados também para carimbar coleta | classe 3, desempate 1 e 6 | conferida pela outra família |
| DD-19 | codex | F3-6c, cenários legados injetam Selic por getter enquanto decisão 31 exige MacroContext por as_of | classe 4, desempate 5 | aberta |
| DD-20 | codex | compatibilidade do snapshot com ano_final já escolhido | classes 4 e 5, desempate 4 e 6 | aberta |
| DD-21 | codex | contexto único da classe | classes 1 e 4, desempate 1, 4 e 6 | aberta |
| DD-22 | codex | gate de ai_core sem cobertura de transporte | classe 4, desempate 4 e 6 | alcance substituído pela DD-23 |
| DD-23 | claude-code | F3-P06, alcance do gate de mutação | classe 2, desempate 4 e 6 | aberta; falta a revisão do Codex (§2) |
| DD-24 | claude-code | F3-0e, modo só de leitura do Claude Code | classe 4, desempate 1 e 6 | substituída, reprovada, não aplicada |
| DD-25 | claude-code | F3-0f como independente do `[!]` do F3-0e | classe 4, desempate 4 | aberta |
| DD-26 | claude-code | F3-0f, "Fase atual sem a fase fechada" | classe 2, desempate 6 | aberta; falta a revisão do Codex (§2) |
| DD-27 | claude-code | F3-0e, detalhes da decisão 37 | classe 4, desempate 1 e 6 | reprovada, não aplicada |
| DD-28 | claude-code | F3-0e, detalhes da decisão 38 | classe 4, desempate 1 e 6 | aberta |

Também ficam para o Marcos dois efeitos da leitura literal da decisão 33 (DD-06): a LREN3 (registros PN antigos) e todas as units passam a se abster no Bazin.

## Resíduos para o Marcos

- **Fora do git, em `outputs/`:** backups e migração do F3-2a, F3-2a-fix e F3-2c (com cópias dos bancos reais), relatórios de mutação, quebras à mão (`outputs/f3-*-quebras*.txt`), o trabalho guardado do F3-0e (`outputs/f3-0e-wip/`, `outputs/f3-0e-wip-r4/`) e os resíduos do Codex (`outputs/f3-6*-*`, `outputs/f3-p13-*`, `outputs/f3-p06-*`, `outputs/residuos-temporarios/`). Nada disso foi apagado (decisão 35).
- **Bancos:** `sentinela_v6.db` continua no disco e ainda é lido por `limpar_banco.py:32`, `auditoria.py:62` e `scripts/dossie_fase2.py:1126`, o que fica para o F3-9. O `sentinela_store.db` é o banco do app.
- **Git:** o `stash@{0}` "wip F3-2a-fix claude-code" ficou, não apagar.
- **Fora do repositório:** caches e sondas em `~/.cache/sentinela-testes-claude/` e `~/.cache/sentinela-testes-codex-*`.
- **Texto pendente:** `.claude/skills/safe-commit/SKILL.md` e o passo 10 do protocolo ainda citam só o `/review-diff` (F3-0g). `cmd_gemini` ainda diz que o fechamento é só no Codex (F3-0e). O `/tmp` tem 48 MB livres, e o export do auditor Claude tem 33 MB; aponte o `TMPDIR` para outro disco antes de rodar.
- **Processo:** `fila.py independentes` não interpreta a linha do F3-0e (DD-25). A pasta da rodada 1 do F3-2a foi apagada, o que está registrado como desvio pela decisão 35.

## O que auditar primeiro (D30)

**Codex, sobre os commits `Executor: claude-code`:**
1. F3-P01 (`554f6fe`): a identidade do emissor na B3 muda o Bazin, com abstenção de LREN3 e das units (DD-05 a DD-07).
2. F3-2c (`82984cd`) e F3-2a/F3-2a-fix (`9dd62d8`, `2380f4d`): migração dos bancos reais, `caminho_padrao` e a conferência (DD-08 a DD-11).
3. F3-1b e F3-1d (`a27b0f6`, `83e83d3`): Selic e IPCA por data, com a data de divulgação provisória (M+2).
4. F3-P02, F3-P03, F3-P04 e F3-P08: custo médio na venda parcial, LPA de unit e falhas do Informe.
5. F3-0e (`d1aac6e`): o auditor Claude só de leitura. Conferir a cópia exportada, as negações e as evidências.

**Claude (chat), sobre os commits `Executor: codex`:**
1. F3-6c (`c57e34b`): `as_of` do serviço até a cascata e os motores, com DD-17, DD-18 (conferida) e DD-19 (semente de teste nos cenários antigos).
2. F3-6a e F3-6b (`917994e`, `33acf20`): `AnalysisService` com `as_of` e o app chamando o serviço (DD-13, DD-14, DD-16).
3. F3-2d (`9ae3006`): resultados imutáveis, o hash e o desvio de cronologia declarado (DD-12).
4. F3-P13 (`a8265d4`) e F3-P06 (`89fcaa6`, com os dois executores): corte da série CVM e contexto da classe na IA (DD-20 a DD-23).
