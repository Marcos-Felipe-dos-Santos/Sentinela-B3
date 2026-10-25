# Diário do loop — Fase 2B, fechamento

Diário da fila de fechamento (`docs/loop/fila.md`). O diário da fase está em `docs/loop/historico/fase-2b/diario.md`.

### Ativação da fila de fechamento — 25/10/2026
- **Executor:** claude-code (claude-opus-5-5).
- **O que foi feito:** a consolidação das auditorias de fechamento (Codex "não pode seguir", Gemini "aprovado com ressalvas") copiada para `docs/loop/historico/fase-2b/auditoria-externa.md`; fila de fechamento F2B-56 a F2B-68, com um `fix:` por bloqueio (BUG-2B-37 reaberto, 46 a 50, BUG-2B-06 reaberto), a ficha FII 1.3, a contraprova D27 do F2B-54 e do F2B-2, a medição do spread, a sincronização da `CLAUDE.md` e do `docs/PLANO.md`, as ressalvas na proposta da 2C e o registro final; termina no [DECISÃO] "Fim da Fase 2B". Decisões do Marcos de 25/10/2026 aprovadas por ele (seção "Decisões do Marcos" do arquivo da auditoria).
- **Testes:** 2517 passed, 1 skipped, 14 xfailed (sem código).
- **Regressões:** os bugs da auditoria (BUG-2B-37 e 06 reabertos, 46 a 50) ganham o teste estrito em `tests/regressao/` no próprio item `fix:`, hoje, antes da correção de cada um (regra de 15/10/2026, "no mesmo dia"); até lá, o registro de BUG-2B-06 e BUG-2B-37 continua "corrigido" e muda para "reaberto" no item.
- **Revisão:** PODE COMMITAR; ajustes de texto antes do commit: modo 644 no arquivo da auditoria; o F2B-56 registra as cinco decisões no marcador; o F2B-62 cita o item 3 do marcador; a descrição do BUG-2B-37 segue a reprodução do Codex (cotas e amortização); a meta de mutação do F2B-58 inclui `sentinela/methods/`. O relatório do Codex (`auditoria-fase-2b-codex-3-relatorio.md`) fica fora do repositório, como a consolidação registra.
