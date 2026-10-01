# Diário do loop — Fase 0

## Estado inicial
- Branch `v2/fase-0`, `which python` aponta para `venv/bin/python`.
- Arquivos obrigatórios presentes (CLAUDE.md, AGENTS.md, PLANO, ADR 0001 e 0002, auditoria).
- `python -m pytest -q`: 255 passed em 1,70 s.
- Já existiam alterações não commitadas de bootstrap (CLAUDE.md, AGENTS.md, PLANO.md, adr/) feitas antes do loop. Ficam fora dos commits dos itens, salvo quando o item as altera.

### F0-0 — docs: add red team audit with normalized finding IDs
- **Status:** sucesso
- **O que foi feito:** cada um dos 37 blocos de achado ganhou `[ID: …]` no cabeçalho (E-1 a E-22 e F-1 a F-15); a tabela de menor severidade foi renumerada para F-16 a F-30 e ordenada; referências cruzadas (F12, F25, F3, F4/F5/F9, F-24) apontam para os IDs novos; tabela "ID antigo → ID novo" no fim.
- **Dificuldades:** os blocos não tinham ID; a ordem do documento é a única fonte da numeração. Conferi E-1 a E-22 contra as referências existentes (E-10 provider FII, E-11 cloudscraper, E-12 CI, E-19 auto_adjust, E-21 migração).
- **Como resolvi:** script único que insere os IDs por posição e renumera a tabela. Antigos F-15 a F-23 viram F-16 a F-24; F-25 a F-30 não mudam; o F-24 antigo (só no Veredito) vira F-14.
- **Testes:** 255 → 255 (só documentação).
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** `CLAUDE.md`, `AGENTS.md`, `docs/PLANO.md` e os ADRs citam apenas F-25 e F-28 (PLANO), que não mudaram; nenhum deles foi alterado. A linha 18 desta fila ainda diz "o que o Veredito chama de F-24", descrição histórica que fica como está. A auditoria entra no git inteira (estava não rastreada).
  O texto de correção do F-15 sugere o rótulo "Alocação sugerida", hoje proibido pelo `CLAUDE.md`; o documento é histórico e não foi editado, e nenhum item futuro deve usar essa correção como especificação. A reordenação da tabela F-16 a F-30 não alterou o texto das linhas, mas o diff não prova isso (arquivo novo no git).
- **Bloqueio (resolvido):** o `/safe-commit` exigia `ruff check .` completo (301 erros antigos). A skill passou a usar o gate do CI (`--select E9,F63,F7,F82`), verde; o loop foi retomado sem mudar o conteúdo do item.
