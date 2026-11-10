# Pendências do loop

Uma linha por decisão provisória ou `[!]` (pacote F3-0, P3).

- 2026-11-09 · F3-0h · caminho com ponto final dentro das crases é ignorado pelo independentes; sem ocorrência na fila nem na proposta em 09/11; avaliar no checkpoint da 3-a
- 2026-11-10 · F3-1b · decisão provisória: IPCA (SGS 433) por data conta o mês M a partir do primeiro dia de M+2, ou a partir da data da coleta; o SGS não traz a data de divulgação
- 2026-11-10 · F3-1b · decisão provisória: o teste ponta a ponta liga MacroContext(as_of).selic ao motor de FII pelo get_selic_atual que o motor lê, porque fii_engine.py só entra no F3-6c
- 2026-11-10 · F3-P01 · [!] caso (f): a B3 recusa o emissor por código em GetListedCashDividends e o GetDetail só devolve o nome com barra ('AMBEV S/A', 'KLABIN S/A'), que traz relação vazia; só 'AMBEV SA' (nome montado à mão) liga ao emissor atual, e 'AMBEV' cai num homônimo de 2000-2013. Decidir a forma da correção do BUG-2B-29
