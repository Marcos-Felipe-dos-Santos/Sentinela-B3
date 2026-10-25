# Fila do loop — Fase 2B, fechamento

> **Ativa por instrução do Marcos de 25/10/2026.** Fila de fechamento da auditoria externa da 2B (`docs/loop/historico/fase-2b/auditoria-externa.md`: Codex "não pode seguir", Gemini "aprovado com ressalvas"), com as decisões do Marcos da mesma data (seção "Decisões do Marcos, 25/10/2026" daquele arquivo, aprovadas). Executada pelas regras do plano final (`docs/decisoes/plano-final-2b.md`, seção 1).

Branch: `v2/fase-2b` · Protocolo: `docs/loop/protocolo.md` · Diário: `docs/loop/diario.md` (do fechamento; arquivado com esta fila) · Histórico da fase: `docs/loop/historico/fase-2b/` · Fichas: `docs/metodologia/` · Plano final: `docs/decisoes/plano-final-2b.md`

**Regras comuns.** Cada `fix:` registra o bug em `tests/regressao/` com `xfail(strict=True)` antes da correção, mostra o vermelho com `--runxfail` pelo motivo econômico (não por importação, interface ou coleta), retira a marca depois e atualiza o registro (D27; decisão 5 de 25/10/2026). Golden: só muda dentro do predicado do item; regeneração com `GERAR_GOLDEN=1` e conferência por `scripts/golden_diff.py`. Gate da fase: `python -m pytest -q`, `ruff check --select E9,F63,F7,F82 .` e `ruff check sentinela/methods sentinela/data`. Arquivos permitidos: os que o item cita, os testes deles e o diário/fila; a seção "Fase atual" do `AGENTS.md` é do Marcos.

## Itens

- [x] **F2B-56** · docs · `docs: approve the FII sheet 1.3 on empty composition and amortization cells`
  - Decisões 3 e 4 do Marcos de 25/10/2026, na ficha `docs/metodologia/fii.md` (versão 1.3, §3c e matriz da §4):
    - **composição:** célula vazia vale zero só quando o registro de composição do fundo-mês existe, é da mesma versão do complemento selecionado e tem ao menos uma posição preenchida; registro ausente, ou todo vazio, é tipo desconhecido e abstém;
    - **amortização:** vazia dentro de um registro de complemento válido, da mesma versão, vale amortização zero (campo do formulário preenchido só quando há evento); NaN, texto ou negativo abstém. Se houver especificação oficial em sentido contrário, `[!]`.
  - Registro no marcador (`docs/decisoes/marcador-2b.md`) das cinco decisões do Marcos de 25/10/2026 da auditoria de fechamento (1: provisórias ratificadas; 2: BRSR3; 3 e 4: esta ficha; 5: D27 sem dispensa genérica).
  - **Aceite:** ficha 1.3 com status e as duas regras; nenhuma mudança de código.

- [x] **F2B-57** · fix · `fix: treat any conflicting field of a same-version FII report as a conflict` · **[golden]**
  - **BUG-2B-37 (reaberto):** o conflito de mesma versão no Informe só compara DY e valor da cota; cotas e amortização ficam fora (reprodução do Codex), e a ordem das linhas muda a elegibilidade. A correção exigida cobre também a composição.
  - Conflito em qualquer campo usado (DY, VP, cotas, amortização, composição) abstém, nas duas ordens das linhas.
  - **Aceite:** regressão estrita do reaberto (as duas ordens, para cada campo) → correção → PASS; golden `--onde "caso['motor'] == 'fii'"` (esperado 0 alterados; inclusões só se a grade ganhar o caso); mutação de `sentinela.data.rendimento_fii` ≥ 80%; gate.

- [x] **F2B-58** · fix · `fix: hold the FII lens to the same time cut as the real rate and the reports` · **[golden]**
  - **BUG-2B-46:** a lente de FII não confere o as_of, a data-base nem a idade do registro da NTN-B; a coleta do Informe e da B3 posterior ao as_of é aceita.
  - Mesmo corte do F2B-30 e do Gordon: registro da taxa com as_of ≤ análise e idade válida (data-base e dias úteis do registro); coleta e entrega do Informe e da B3 até o as_of. Sem prova, a lente abstém com o motivo.
  - **Aceite:** regressão estrita → correção → PASS; golden `--onde "caso['motor'] == 'fii'"` com a conferência de cada alteração no diário; mutação ≥ 80% nos módulos de `sentinela/data/` e `sentinela/methods/` tocados; `fii_engine.py` (V1) registrado, sem meta; gate.

- [x] **F2B-59** · fix · `fix: take the FII composition from the selected report version` · **[golden]**
  - **BUG-2B-47:** composição de outra versão, ou conflitante, autoriza a lente.
  - A composição precisa ser da mesma versão do complemento selecionado (o conflito de composições da mesma versão já é do F2B-57). Inclui a regra de células vazias da ficha 1.3 (F2B-56): vazio vale zero só em registro da mesma versão com ao menos uma posição preenchida; registro ausente ou todo vazio é tipo desconhecido.
  - **Aceite:** regressão estrita → correção → PASS; golden do FII; mutação de `sentinela.data.fii_elegibilidade` e `rendimento_fii` ≥ 80%; gate.

- [x] **F2B-60** · fix · `fix: validate every book value in the FII window` · **[golden]**
  - **BUG-2B-48:** VP final inválido (None, 0, negativo, NaN, inf) não impede a elegibilidade. Os 13 VPs são validados, inclusive o último.
  - **Aceite:** regressão estrita → correção → PASS; golden do FII; mutação ≥ 80%; gate.

- [x] **F2B-61** · fix · `fix: read empty FII amortization by the sheet 1.3 rule` · **[golden]**
  - **BUG-2B-49:** amortização ausente aceita como "sem amortização" fora das condições da ficha 1.3 (decisão 4): vazio vale zero só dentro de um registro de complemento válido da mesma versão; NaN, texto ou negativo abstém.
  - **Aceite:** regressão estrita → correção → PASS, com um caso para cada leitura: célula vazia (vale zero), literal `NaN` declarado, texto e negativo (abstêm); a leitura do CSV distingue o vazio do `NaN` literal (revisão do F2B-56); golden do FII; mutação ≥ 80%; gate.

- [x] **F2B-62** · fix · `fix: return no number when the FII lens abstains` · **[golden]**
  - **BUG-2B-50:** a abstenção do FII devolve `fair_value = preço` e `upside = 0`. Sem valor e sem upside numéricos, com o motivo; o score contextual fica como decidido em 25/10/2026 (`docs/decisoes/marcador-2b.md`, seção de 25/10/2026, item 3: 50, neutro, exceção à decisão de 19/10).
  - **Aceite:** regressão estrita → correção → PASS; golden `--onde "caso['motor'] == 'fii'"` (alterados só os casos de lente abstida, nas chaves `fair_value` e `upside`, e o que a regra vigente de rótulo derivar disso; conferência campo a campo no diário); gate.

- [x] **F2B-63** · fix · `fix: read the statement model where the cascade writes it in the completeness check`
  - **BUG-2B-06 (reaberto):** a completude lê `modelo`, e a cascata grava `modelo_bpp`: um banco completo sai com 70%. Alinhar produtor e consumidor; regressão pela saída real da cascata (dublê do provedor, `buscar_dados_ticker`), não por dicionário montado à mão.
  - **Aceite:** regressão estrita → correção → PASS; golden inalterado; mutação de `data_quality` registrada (V1, sem meta); gate.

- [x] **F2B-64** · test · `test: redo the D27 counterproof for F2B-54 and F2B-2`
  - Decisão 5 de 25/10/2026: para os testes do F2B-54 e do F2B-2 cuja falha registrada foi de importação, interface ou coleta, refazer a contraprova contra o código anterior (worktree temporária no commit pai do item) com a falha econômica, ou escrever no diário a dispensa com o motivo, caso a caso, quando a contraprova correta for impossível. Sem dispensa genérica.
  - **Aceite:** diário com a lista de testes, o commit da contraprova, a saída (ou a dispensa e o motivo); nenhum teste existente enfraquecido; gate.

- [x] **F2B-65** · levantamento · `docs: remeasure the FII spread after the closing fixes`
  - Recalibração do spread com `scripts/calibrar_spread_fii.py`, mesmo mês final (2026-09), depois dos F2B-57 a F2B-62, **só como medição**: a constante de 3,5058% não muda sem decisão do Marcos.
  - **Aceite:** ficha FII §6a com a medição (spread, quartis, fundos por mês, exclusões antes → depois); `MacroContext.FII_SPREAD_TIJOLO` inalterado; gate.

- [x] **F2B-66** · docs · `docs: sync CLAUDE.md and the plan with the phase 2B delivery`
  - `CLAUDE.md` e `docs/PLANO.md` (tabela da 2B) com o estado final: F2B-4 e F2B-32 entregues, escopo por BPP, seguradora pelo critério ampliado, liquidez, lente de bancos, FII (ficha 1.3), avisos fora de `riscos`, Selic fora do motor de ações, contagem da suíte, linhas citadas. Sem tocar a seção "Fase atual" do `AGENTS.md`; o resto do `AGENTS.md` só se contradisser a `CLAUDE.md`.
  - **Aceite:** cada linha citada conferida com `grep -n` no diário; `CLAUDE.md` e `AGENTS.md` sem contradição.

- [x] **F2B-67** · docs · `docs: add the phase 2B closing caveats to the phase 2C proposal`
  - Na `docs/loop/fila-fase2c-proposta.md`, as ressalvas não bloqueantes da auditoria: `CVMFIIProvider._preco_cotahist` sem `meses_ausentes` nem idade da cotação; `_escala_da_composicao` sem a confirmação pela `sharesOutstanding` da §7.7 (alinhar, ou documentar que a razão (0,9; 1,1) contra a DFP cumpre o papel); BUG-2B-09 (já em F2C-19); teste da DVA extraordinária no leiaute 7.09 de bancos; vocabulário legado dos motores; e os destinos 2C das decisões 1 e 2 (IF.data pelo BPP, calendário de publicação, separação da ON do BRSR3), mais os resíduos registrados nos diários do F2B-4, F2B-32, F2B-45 e F2B-5.
  - **Aceite:** cada ressalva com destino e aceite verificável na proposta; nada implementado.

- [x] **F2B-68** · docs · `docs: record the phase 2B closing and archive the closing queue`
  - Atualiza `docs/loop/historico/fase-2b/pr-fase-2b.md` com o fechamento (itens, commits, testes, golden, mutação, decisões de 25/10, spread medido); registra o item no diário e o marca `[x]`; move com `git mv` esta fila e o diário para `docs/loop/historico/fase-2b/` (`fila-fechamento.md`, `diario-fechamento.md`); `docs/loop/fila.md` volta a ter só o [DECISÃO] abaixo.
  - **Aceite:** arquivos movidos; `docs/loop/fila.md` com a linha do [DECISÃO]; cada commit citado existe no `git log`.

- [DECISÃO] **Fim da Fase 2B.** O Marcos segue o roteiro do [DECISÃO] da fila da fase (`docs/loop/historico/fase-2b/fila.md`) e do plano final, §10: revisão do resumo e do fechamento, relatórios do F1-12, índice e cache, push, auditoria rápida da fila de fechamento, PR, merge, tag `v2-fase-2b`, "Fase atual" do `AGENTS.md`, retro.
