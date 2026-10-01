# Protocolo do loop — Sentinela B3

Regras que o Claude Code segue em cada item de `docs/loop/fila.md`, em qualquer fase.
Este arquivo manda mais que o texto do `/goal`. Depois de qualquer compactação de contexto, releia-o antes de continuar.
O cabeçalho da fila define o branch da fase e os arquivos intocáveis.

## Ambiente

- WSL2, repositório em `~/projetos/Sentinela_B3`, venv `venv/` ativada.
- Confira com `which python`: se não apontar para `venv/bin/python`, pare — o ambiente está errado.

## Agentes

- Exploração: `scout`. Implementação: `junior-dev`. Revisão: `senior-reviewer` via `/review-diff`.
- `fable-architect` só em item de planejamento. É o que mais consome limite.

## Preparação (uma vez por sessão)

1. Trabalhe no branch indicado no cabeçalho da fila. Se ele não existir, crie a partir da `main` com `git switch -c <branch> main`. Nunca commite na `main`.
2. Confirme que existem: `CLAUDE.md`, `AGENTS.md`, `docs/PLANO.md`, `docs/adr/0001-refactor-v2.md`, `docs/adr/0002-loop-tempo-dados.md` e `docs/auditoria/2026-09-red-team.md`. Faltando algum, marque o primeiro item pendente como `[!]`, registre o motivo no diário e pare.
3. Rode `python -m pytest -q` e registre no diário o estado inicial.

## Para cada item `[ ]`, em ordem

1. **Já feito?** Confira no código e no `git log`. Se o item já foi entregue, marque `[x]`, anote "já estava feito" no diário e siga.
2. **Escopo.** Só o que o item descreve. Nenhuma correção extra "de passagem".
3. **Rito pelo tipo do item:**
   - `fix`: teste xfail provando o problema → implementação → XPASS.
   - `refactor`: comportamento idêntico; nenhum teste existente muda.
   - `feat`: teste novo primeiro, falhando pelo motivo certo, depois a implementação.
   - `docs`: valide cada afirmação contra o código; divergindo, corrija o documento, nunca o código.
   - `test`: todo teste novo precisa falhar quando o código coberto é quebrado. Confirme com `python -m mutmut run "<modulo>*"` e `python -m mutmut export-cicd-stats`.
   - `chore`: cumpra o aceite do item à risca.
   - `levantamento`: só escreve análise em `docs/` e, se o item pedir, script em `scripts/`. Não altera módulos de produção.
   - `limpeza`: remova só o que o item lista. Antes de remover, confirme por busca que nada usa o que sai. Arquivo rastreado sai com `git rm`, ou `git rm --cached` se deve continuar existindo localmente. Depois, rode de novo as ferramentas do inventário e atualize `docs/limpeza/inventario.md`.
4. **Verificação.** `python -m pytest -q` e `ruff check --select E9,F63,F7,F82 .` verdes — o mesmo gate do CI. A dívida antiga do `ruff check .` completo fica no inventário (F0-7) e é paga a partir da Fase 1. `ruff format` só nos arquivos que o item criou ou alterou. No máximo 3 rodadas de correção; na 3ª falha, marque `[!]`, registre no diário e pare o loop.
5. **Sem resíduo novo.** O item não acrescenta código comentado, import sem uso, print de depuração, arquivo temporário nem TODO sem item na fila.
6. **Diário.** Acrescente a seção do item em `docs/loop/diario.md`, no formato abaixo.
7. **Fila.** Marque o item como `[x]`.
8. **Stage.** `git add` só nos arquivos do item, no diário e na fila — nunca `git add -A` nem `git add .`. Confira com `git status --porcelain` que nada do item ficou de fora e que nada alheio entrou.
9. **Revisão.** `/review-diff`, que revisa exatamente o que está no stage — código, diário e fila. Reprovou: corrija, atualize o diário, refaça o stage e revise de novo; conta nas 3 rodadas. Na 3ª reprovação, troque o `[x]` por `[!]`, registre o motivo no diário e pare o loop.
10. **Commit.** `/safe-commit`, um único commit por item. Ele não faz stage: commita exatamente o que o `/review-diff` aprovou. Título = o Conventional Commit do item. Nunca push.
11. **Progresso.** Rode `cat docs/loop/fila.md` e `git log --oneline -3`.
12. **Próximo.** Siga para o próximo `[ ]`. Se a próxima linha for `[DECISÃO]`, pare: a fase acabou.

## Regras duras

- Nunca `git push`, abrir PR, `git reset --hard`, `git clean`, `git commit --amend`, `git add -A` ou `git add .`.
- Refactor e mudança de comportamento nunca no mesmo commit.
- Não tocar nos arquivos intocáveis do cabeçalho da fila. Se um item parecer exigir isso, marque `[!]` e pare.
- Não remover, pular (`skip`) nem enfraquecer testes para a suíte passar.
- Remoção só do que o git devolve: arquivo rastreado, com `git rm`. Arquivo não rastreado e branch nunca são apagados pelo loop — vão para a lista do Marcos no diário. Item *investigar* do inventário nunca sai sem decisão.
- Mutação sempre com a configuração do `[tool.mutmut]`, que desliga o `xfail_strict` só nessas rodadas. `mutants/` nunca entra em commit.
- Métodos de valuation não ganham rede, banco nem leitura de relógio.
- O repositório é público: dados da carteira do Marcos (posições, pesos, lista de ativos) nunca entram em arquivo versionado — nem no diário. O que usar a carteira vai para `outputs/`.
- Não fazer perguntas durante o loop. Onde a especificação dizia "me diga", "me mostre" ou "pare e me mostre o diff", escreva no diário e siga. Dúvida que muda o resultado vira `[!]`, registro no diário e parada.

## Formato do diário

    ### <ID> — <título do commit>
    - **Status:** sucesso | sucesso parcial | bloqueado
    - **O que foi feito:**
    - **Dificuldades:**
    - **Como resolvi:**
    - **Testes:** antes → depois (total, falhas, mutation score quando houver)
    - **Resíduos:** o que saiu, e o que ficou para o Marcos apagar à mão
    - **Decisões que ficaram para o Marcos:**
    - **Para o Marcos revisar:** o que merece olho humano antes de seguir

## Resumo e arquivamento da fase

O último item de toda fila fecha a fase, nesta ordem:
1. escreve `docs/loop/pr-fase-N.md` a partir do diário, com itens e commits, testes antes → depois, decisões pendentes, resíduos que ficaram para o Marcos e o que revisar primeiro;
2. registra o próprio item no diário e o marca `[x]`;
3. move com `git mv` a fila, o diário e o resumo para `docs/loop/historico/fase-N/`;
4. cria um `docs/loop/fila.md` novo só com a linha `[DECISÃO]` apontando o histórico e a proposta da próxima fila;
5. faz o stage, passa pelo `/review-diff`, commita com `/safe-commit` e roda `cat docs/loop/fila.md`.

A próxima fila nunca é ativada pelo loop: quem a coloca em `docs/loop/fila.md` é o Marcos, depois de aprovar.
