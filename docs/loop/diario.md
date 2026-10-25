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
