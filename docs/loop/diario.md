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
