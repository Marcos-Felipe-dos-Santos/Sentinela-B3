# Diário do loop — Fase 2B, fechamento

Diário da fila de fechamento (`docs/loop/fila.md`). O diário da fase está em `docs/loop/historico/fase-2b/diario.md`.

### Ativação da fila de fechamento — 25/10/2026
- **Executor:** claude-code (claude-opus-5-5).
- **O que foi feito:** a consolidação das auditorias de fechamento (Codex "não pode seguir", Gemini "aprovado com ressalvas") copiada para `docs/loop/historico/fase-2b/auditoria-externa.md`; fila de fechamento F2B-56 a F2B-68, com um `fix:` por bloqueio (BUG-2B-37 reaberto, 46 a 50, BUG-2B-06 reaberto), a ficha FII 1.3, a contraprova D27 do F2B-54 e do F2B-2, a medição do spread, a sincronização da `CLAUDE.md` e do `docs/PLANO.md`, as ressalvas na proposta da 2C e o registro final; termina no [DECISÃO] "Fim da Fase 2B". Decisões do Marcos de 25/10/2026 aprovadas por ele (seção "Decisões do Marcos" do arquivo da auditoria).
- **Testes:** 2517 passed, 1 skipped, 14 xfailed (sem código).
- **Regressões:** os bugs da auditoria (BUG-2B-37 e 06 reabertos, 46 a 50) ganham o teste estrito em `tests/regressao/` no próprio item `fix:`, hoje, antes da correção de cada um (regra de 15/10/2026, "no mesmo dia"); até lá, o registro de BUG-2B-06 e BUG-2B-37 continua "corrigido" e muda para "reaberto" no item.
- **Revisão:** PODE COMMITAR; ajustes de texto antes do commit: modo 644 no arquivo da auditoria; o F2B-56 registra as cinco decisões no marcador; o F2B-62 cita o item 3 do marcador; a descrição do BUG-2B-37 segue a reprodução do Codex (cotas e amortização); a meta de mutação do F2B-58 inclui `sentinela/methods/`. O relatório do Codex (`auditoria-fase-2b-codex-3-relatorio.md`) fica fora do repositório, como a consolidação registra.


### F2B-56 — docs: approve the FII sheet 1.3 on empty composition and amortization cells
- **Executor:** claude-code (claude-opus-5-5).
- **Status:** sucesso.
- **O que foi feito:** ficha `docs/metodologia/fii.md` na versão 1.3 (status, §3c e as linhas de amortização e de classificação da matriz da §4), com as decisões 3 e 4 do Marcos de 25/10/2026 e o conflito de mesma versão em qualquer campo usado; marcador com as cinco decisões da auditoria de fechamento.
- **Especificação oficial (decisão 4):** dicionário de dados da CVM do Informe Mensal (`meta_inf_mensal_fii.zip`, coletado em 25/10/2026, SHA-256 `4db505e6…48ef55`, citado por inteiro na ficha): `Percentual_Amortizacao_Cotas_Mes` é "Percentual de amortizações de cotas do Mês de Referência", domínio numérico, sem regra para o vazio. Nada em sentido contrário; sem `[!]`.
- **Testes:** sem código; 2517 passed, 1 skipped, 14 xfailed.
- **Revisão:** PODE COMMITAR; ajustes de texto: a regra geral da §4 remete à §3c; o status cita também o conflito de mesma versão; "maioria ausente" virou "sem maioria estrita"; o cabeçalho cita os itens que implementam a 1.2 e a 1.3; o marcador diz "a executar"; o aceite do F2B-61 pede a distinção entre célula vazia e `NaN` literal (a leitura padrão do pandas os iguala).
- **Desvio do safe-commit:** o script dos ajustes parou na segunda edição (o texto do status estava quebrado em outra linha), e o encadeamento commitou `ed1ebfb` só com a primeira (a remissão à §3c), porque o `set -e` vinha depois do Python. Sem `amend`; os demais ajustes, todos de texto e já aprovados na revisão, vão num commit `docs:` complementar. Desde então o `set -e` abre o comando.


### F2B-57 — fix: treat any conflicting field of a same-version FII report as a conflict
- **Executor:** claude-code (claude-opus-5-5).
- **Status:** sucesso.
- **O que foi feito:** BUG-2B-37 reaberto (auditoria de fechamento, reprodução do Codex). `rendimento_fii._por_mes` compara também `Cotas_Emitidas` e `Percentual_Amortizacao_Cotas_Mes`; `avaliar` passa a abster por conflito em qualquer mês da janela de 13 (antes, só os meses do DY e do VP pelo `rendimento_12_meses`); duas composições da maior versão do mês final com posições diferentes abstêm ("Informe com linhas conflitantes da mesma versão: AAAA-MM (composição)"), nas duas ordens, pela comparação de `fii_elegibilidade.posicoes` (função nova, pura).
- **Rito D27:** `tests/regressao/test_bug_2b_37_reaberto_conflito_em_qualquer_campo.py` com `xfail(strict=True)` antes da correção; `--runxfail`: **6 failed** pelo motivo econômico (amortização e composição: numa ordem a lente calculava, `dy` 0,12, e na outra abstinha por amortização ou por tipo papel; cotas: calculava nas duas ordens; em nenhum caso com o motivo de conflito), em `f2b57-vermelho.txt` no scratchpad. Marca retirada: PASS; registro do BUG-2B-37 com o teste do reaberto e o F2B-57.
- **Testes existentes que mudam:** nenhum.
- **Golden:** regenerado, idêntico (`git diff --exit-code`): a grade não tem linhas duplicadas.
- **1ª revisão:** PODE COMMITAR, mas com um médio que é o mesmo defeito do item: a comparação usava o número da célula, e vazio, `NaN` e texto viravam todos `None`; como o vazio vale zero (ficha 1.3) e o inválido abstém, a ordem ainda decidia (amortização `""` contra `"NaN"`, composição `""` contra `"abc"`). Corrigido no item: `fii_elegibilidade.forma` separa vazio, número e inválido, e o conflito do complemento e da composição compara por ela. Regressão estendida antes da correção (`test_vazio_e_invalido_sao_conflito_nas_duas_ordens`, xfail estrito, `--runxfail` 4 failed pelo resultado dependente da ordem, `f2b57-vermelho-2.txt`), marca retirada: PASS; mais `test_composicoes_identicas_da_mesma_versao_calculam`. Também registrado: vazio contra `"0"` na composição é conflito (conservador), e o DY e a amortização do 13º mês entram na comparação, embora a lente não os use; na reprodução original, o caso de `Cotas_Emitidas` calculava nas duas ordens (só mudava o contexto de emissões), sem o motivo de conflito. O conflito da composição sai do F2B-59, que fica com a mesma versão do complemento e as células vazias.
- **Mutação:** `sentinela.data.rendimento_fii` 413/444 (93,0%); `sentinela.data.fii_elegibilidade` 176/205 (85,9%), depois da 2ª rodada.
- **Testes:** 2517 passed, 1 skipped, 14 xfailed → 2528 passed, 1 skipped, 14 xfailed (+11 do arquivo novo; medida sem o teste não rastreado do item seguinte). Gates verdes.
- **2ª revisão:** NÃO PODE COMMITAR só pela contagem de testes (+12 no texto, +11 no diff); corrigida e commitada sem nova parada (plano final, §1, regra 5). Registrados, sem mudança: a docstring de `avaliar` não cita o conflito; vazio contra `"0"` também é conflito no complemento; falta um teste de duplicata só de formato (`"1500"` e `"1500.0"`), que `forma` já trata como igual.
- **Decisões que ficaram para o Marcos:** nenhuma.


### F2B-58 — fix: hold the FII lens to the same time cut as the real rate and the reports
- **Executor:** claude-code (claude-opus-5-5).
- **Status:** sucesso.
- **O que foi feito:** BUG-2B-46. `rendimento_fii.entradas` confere, antes da conta: a coleta do Informe (`proveniencia.data_coleta` do arquivo mais recente, com fuso, até o as_of; sem ela, "coleta do Informe não demonstrada até o as_of"); a coleta da resposta da B3 (`b3_fundo.coleta`, idem); e o registro da taxa real por `ntnb_ate` (função nova, pura): sem registro, "insumo ausente: taxa real"; abstenção do registro, "taxa real indisponível: <motivo>" (os motivos do Gordon); `as_of` do registro ausente, sem fuso ou posterior ao da análise; registro com mais de um dia (a validade do cache da taxa real); data-base não anterior ao dia do as_of; idade em dias úteis fora de [0; 5]; NTN-B não finita. A NTN-B conferida volta nas entradas (`ntnb_real`), e o motor de FII a passa ao método.
- **Rito D27:** `tests/regressao/test_bug_2b_46_fii_sem_corte_temporal.py` com `xfail(strict=True)` antes da correção; `--runxfail`: **8 failed** pelo motivo econômico (a lente calculava com o registro posterior, sem `as_of`, com data-base do dia, com 6 dias úteis, sem idade, com registro de 10 dias, e com o Informe e a B3 coletados depois do as_of), mais o controle em PASS (`f2b58-vermelho.txt` no scratchpad). Marca retirada: PASS; BUG-2B-46 registrado como corrigido.
- **Testes existentes que mudam:** `tests/test_fii_engine_rendimento.py::test_abstencoes_da_lente`, os dois casos de taxa ausente e abstida (o motivo era o do método, "insumo ausente: ntnb_real"; agora é o da fronteira, como no Gordon). Harness `tests/apoio_fii.py`: o registro sintético da taxa ganha `as_of` e `dias_uteis`, e o Informe sintético a `data_coleta`, todos antes do as_of do harness (como a cascata grava).
- **Golden:** `--onde "caso['motor'] == 'fii'"`: **1 alterado** (`fii/sem-taxa-real`, só o texto: "insumo ausente: ntnb_real" → "insumo ausente: taxa real", em `metodos_usados`), 0 incluídos, 0 removidos, 0 fora do predicado.
- **1ª revisão:** PODE COMMITAR, com médios corrigidos no item antes do commit: (a) a taxa era conferida antes do escopo, e um FII de papel sem taxa mostrava "insumo ausente: taxa real"; agora `avaliar` vem primeiro e a taxa só é conferida para o rendimento elegível (`test_escopo_vem_antes_da_taxa`, xfail estrito antes, 1 failed); (b) o limite de 5 dias úteis valia no dia do registro, com tolerância de 24 horas; agora o registro precisa ser do mesmo dia local da análise ("registro de outro dia"), o que vale com o cache por dia de `get_taxa_real` (caso novo, xfail estrito antes, 1 failed); (c) a regressão confere o motivo exato de cada caso e ganhou `as_of` sem fuso, data-base ilegível, NTN-B NaN, idade booleana e negativa, Informe sem coleta e B3 sem coleta (`f2b58-vermelho-2.txt`). Ficam registrados, sem mudança: só a coleta do arquivo mais recente do Informe é conferida (pesa só com as_of no passado); o relatório do F1-12 mostra a NTN-B do registro mesmo quando a lente a recusa (não é regressão deste item); o FII ficou mais rígido que o Gordon, que aceita registro sem `as_of`.
- **Mutação:** `sentinela.data.rendimento_fii` 498/547 (91,0%), depois da 1ª revisão; `fii_engine.py` (V1) sem medida.
- **Testes:** 2528 passed, 1 skipped, 14 xfailed → 2545 passed, 1 skipped, 14 xfailed (medida sem o teste não rastreado do item seguinte). Gates verdes.
- **2ª revisão:** PODE COMMITAR. Ficam registrados, sem mudança: a docstring de `entradas` não cita as conferências de coleta e taxa nem a chave `ntnb_real`; sem teste para `proveniencia` igual a `None` e para registro em UTC que cai no dia anterior em Brasília; o motivo "idade da NTN-B" junta idade inválida e acima de 5 dias úteis.
- **Decisões provisórias (plano final, §1, regra 3):** (1) o registro da taxa precisa ser do mesmo dia local da análise; (2) sem a resposta da B3, a abstenção continua a dos eventos indisponíveis (a coleta só é conferida quando há resposta).


### F2B-59 — fix: take the FII composition from the selected report version
- **Executor:** claude-code (claude-opus-5-5).
- **Status:** sucesso.
- **O que foi feito:** BUG-2B-47. `rendimento_fii.avaliar` usa só a composição do mês final na versão do complemento selecionado (a maior versão entregue até o as_of); antes, valia a composição de qualquer versão entregue do mês, e com o complemento na versão 2 e a composição só na 1 a lente classificava pela antiga. O conflito de composições da mesma versão já é do F2B-57. A regra das células vazias da ficha 1.3 (§3c) já era a do código (vazio pulado na soma; registro todo vazio dá base zero e "classificação de FII desconhecida"); dois testes de guarda passam a fixá-la.
- **Rito D27:** `tests/regressao/test_bug_2b_47_fii_composicao_de_outra_versao.py` com `xfail(strict=True)` antes da correção; `--runxfail`: **1 failed** pelo motivo econômico (a lente calculava `dy` 0,12 com a composição da versão 1), em `f2b59-vermelho.txt` no scratchpad. Marca retirada: PASS. Guardas sem marca (passam antes e depois): composição da versão selecionada autoriza; composição toda vazia é tipo desconhecido; vazio ao lado de posição preenchida vale zero.
- **Testes existentes que mudam:** nenhum.
- **Golden:** regenerado, idêntico (a grade usa uma versão só).
- **Mutação:** `sentinela.data.rendimento_fii` 497/546 (91,0%); `sentinela.data.fii_elegibilidade` 176/205 (85,9%).
- **Testes:** 2545 passed, 1 skipped, 14 xfailed → 2549 passed, 1 skipped, 14 xfailed. Gates verdes.
- **Revisão:** 1ª rodada reprovada por `import pytest` sem uso no teste novo (sobra da marca retirada; o `ruff check .` completo acusa F401, o gate do CI não). Removido e commitado, como a revisão indica. Registrados, sem mudança: `maior`/`da_maior` em `avaliar` ficaram redundantes depois do filtro pela versão selecionada (limpeza de refactor, para a 2C); versão ilegível nos dois lados (`-inf`) ainda casa, como já casava; a data de entrega da composição continua implícita na do complemento da mesma versão.


### F2B-60 — fix: validate every book value in the FII window
- **Executor:** claude-code (claude-opus-5-5).
- **Status:** sucesso.
- **O que foi feito:** BUG-2B-48. `rendimento_fii.avaliar` confere o valor patrimonial da cota em cada um dos 13 meses da janela, inclusive o final, que o rendimento não usa (cada DY usa o VP do mês anterior); ausente, vazio, zero, negativo, não finito ou texto abstém com "valor patrimonial da cota inválido no Informe: AAAA-MM" (`MOTIVO_VP`, novo).
- **Rito D27:** `tests/regressao/test_bug_2b_48_fii_vp_final_invalido.py` com `xfail(strict=True)` antes da correção; `--runxfail`: **7 failed** pelo motivo econômico (a lente calculava `dy` 0,12 com o VP final `None`, vazio, `"0"`, `"-1"`, `"nan"`, `"inf"` e texto), em `f2b60-vermelho.txt` no scratchpad. Marca retirada; o teste passou a conferir o motivo exato: PASS.
- **Testes existentes que mudam:** nenhum. Nos meses anteriores, o VP inválido continua abstendo, agora com o motivo novo antes do de meses incompletos (nenhum teste fixava o motivo nesse caso).
- **Golden:** `--onde "caso['motor'] == 'fii'"`: 0 alterados, 0 incluídos, 0 removidos, 0 fora do predicado.
- **Mutação:** `sentinela.data.rendimento_fii` 508/558 (91,0%).
- **Testes:** 2549 passed, 1 skipped, 14 xfailed → 2556 passed, 1 skipped, 14 xfailed. Gates verdes.
- **Revisão:** PODE COMMITAR na 1ª rodada. Registrado para a 2C: o teste só invalida o VP do mês final; um caso num mês intermediário e no 13º mês protegeria a ordem das conferências contra uma mudança de lugar (que a mutação não pega).


### F2B-61 — fix: read empty FII amortization by the sheet 1.3 rule
- **Executor:** claude-code (claude-opus-5-5).
- **Status:** sucesso.
- **O que foi feito:** BUG-2B-49. A lente já separava o vazio (amortização zero) do inválido; o defeito estava na leitura: com `dtype=str` e os `na_values` padrão do pandas, a célula vazia e o `NaN` declarado chegavam iguais (`float('nan')`), e a lente aceitava os dois como "sem amortização". `CVMFIIProvider._parsear_complemento` e `_tabela` ganham `literal` (padrão `False`, o comportamento de antes para o P/VP e o `geral`); `_linhas_do_fundo`, que alimenta a lente, lê complemento, `geral` e `ativo_passivo` com `literal=True` (`keep_default_na=False`): o vazio fica `""` e o `NaN` declarado fica `"NaN"`. Pela ficha 1.3, vazio vale zero; `NaN`, texto e negativo abstêm ("amortização inválida no Informe").
- **Especificação oficial:** conferida no F2B-56 (dicionário de dados da CVM, sem regra para o vazio).
- **Rito D27:** `tests/regressao/test_bug_2b_49_fii_amortizacao_nan_literal.py` com `xfail(strict=True)` antes da correção; `--runxfail`: **3 failed** pelo motivo do bug (o provedor devolvia `nan` no lugar do `"NaN"` declarado e no lugar do vazio), em `f2b61-vermelho.txt` no scratchpad. Marca retirada: PASS. Os quatro casos da lente pedidos no aceite (vazio vale zero; `NaN`, texto e negativo abstêm) passam antes e depois e ficam como guarda, sem marca.
- **Testes existentes que mudam:** nenhum.
- **Golden:** regenerado, idêntico (o harness monta as linhas em texto).
- **Mutação:** `cvm_fii_provider` (V1, sem meta) 445/545 (81,7%).
- **Testes:** 2556 passed, 1 skipped, 14 xfailed → 2563 passed, 1 skipped, 14 xfailed. Gates verdes.
- **Revisão:** PODE COMMITAR na 1ª rodada. Efeito do modo literal registrado: um `NaN` declarado (ou `NA`, `null`, `N/A`) numa posição da composição deixa de ser pulado como vazio e abstém por "classificação de FII desconhecida: <coluna> não numérico"; no complemento, `""` contra `"NaN"` na mesma versão vira conflito (`forma` os separa). Os dois seguem a ficha 1.3 (só o vazio é dispensado). Para a 2C: um teste fim a fim, do ZIP com `NaN` declarado até `avaliar`; trocar a terceira asserção do teste do provedor, que só confere a entrada do parametrize.
