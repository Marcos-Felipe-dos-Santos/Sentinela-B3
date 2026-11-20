# Diário — fim da Fase 3

Diário da Fase 3 arquivado pelo F3-10b em `docs/loop/historico/fase-3/diario.md`. Fila ativa: `docs/loop/fila.md` (F3-10c e o checkpoint).

### F3-10c — docs: update the README for the end of phase 3
- **Executor:** claude-code (Opus 5.5).
- **Status:** README atualizado no formato da evolução V1 → V2 de 18/11 (commit `0f6cc0b`).
- **Mudanças:** status (Fase 3 concluída na branch de desenvolvimento, em revisão antes do merge); linha da Fase 3 na tabela de entregas (o que a fase entregou, a cobertura medida pela sonda final e as limitações declaradas com destino na Fase 4), com o link para o resumo arquivado no lugar dos links de `resumo-3a`, `resumo-3b` e da fila ativa, que o F3-10b moveu; contagem do gate de 19/11 (5.181 passed, 1 skipped, 24 xfailed estritos, todos limitações declaradas); a Fase 4 em "Próximos passos" com a herança da Fase 3 e o link da proposta.
- **Conferido:** cada número contra o `pr-fase-3.md` e a tabela de cobertura (Gordon até 44 por data em 2022, Bazin até 15 em 2025, Graham só em 2025, FII sem número); a Fase 4 contra o PLANO §6 e a proposta; sem linguagem de recomendação nem dado da carteira.
- **Verificações:** sem código tocado; gate do stage.
- **Revisão (`/review-diff-leve`): PODE COMMITAR**, rodada 1, sem médios bloqueantes (o README omite o Lynch de 2025, 1 ação, e o retorno do FII sem ligação, ambos no resumo).


### C3-01 — fix: date the MGLU3 species correction by the DFP delivery
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** decisão 51 (revisão da DD-89): a linha da tabela de correções vale no índice em D pela entrega ou publicação comprovada da evidência, anterior a D. A `data` da MGLU3 passou de 2025-12-31 (referência da DFP 2025) para 2026-03-12, a `DT_RECEB` da versão 1 conferida no índice do ZIP local (`data/fontes/backfill/dfp/dfp_cia_aberta_2025.zip`, ID_DOC 155314); o `arquivo` da linha cita a `DT_RECEB`. Docstrings de `universo.referencias_em` e `correcoes.py` com o novo critério. Regressão BUG-3-59 em 11, 12 e 13/03/2026 (PN, PN, ON) e na data da linha. Na BUG-3-55, o dia "depois da MGLU" foi de 02/03 para 13/03/2026: a asserção antiga (ON em 02/03) era o próprio vazamento.
- **Dificuldades:** as outras linhas não mudam de data. CSNA3, TRXF11 e BPAC11 são correções de código: só agem quando o código defeituoso já aparece num documento entregue antes de D (o FCA ou o Informe com o defeito), então a data da referência não antecipa nada. BPAC11 e as identidades de FII usam datas de conferência ou arquivamento, posteriores à publicação (conservador).
- **Como resolvi:** só a linha da MGLU3 muda, como a decisão manda; a análise das demais linhas fica na docstring.
- **Testes:** 5181 passed, 1 skipped, 24 xfailed → 5185 passed, 1 skipped, 24 xfailed. Vermelho antes da correção em `outputs/c3/c3-01-vermelho.log` (3 falhas: espécie ON em 11 e 12/03 e a data da linha). Mutação: nenhuma função mudou (só a tabela e docstrings), sem mutante novo a medir.
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** a análise de que as correções de código não antecipam evidência (docstring de `referencias_em`).
