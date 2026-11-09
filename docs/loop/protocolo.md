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

Cada item começa com `python scripts/fila.py proximo`, que imprime só a linha do próximo item `[ ]`. Saída 3: a próxima linha aberta é `[DECISÃO]`; pare (passo 12). Saída 1 (nada aberto) ou 2 (fila ausente): registre no diário e pare. O `[DECISÃO]` de toda fila é escrito `- [ ] **[DECISÃO] ...**`; é o único formato que o `scripts/fila.py` reconhece.

1. **Já feito?** Confira no código e no `git log`. Se o item já foi entregue, marque `[x]`, anote "já estava feito" no diário e siga.
2. **Escopo.** Só o que o item descreve. Nenhuma correção extra "de passagem".
3. **Rito pelo tipo do item:**
   - `fix`: teste xfail provando o problema → implementação → marca retirada → PASS.
   - `refactor`: comportamento idêntico; nenhum teste existente muda.
   - `feat`: teste novo primeiro, falhando pelo motivo certo, depois a implementação.
   - `docs`: valide cada afirmação contra o código; divergindo, corrija o documento, nunca o código.
   - `test`: todo teste novo precisa falhar quando o código coberto é quebrado. Confirme com `python -m mutmut run "<modulo>*"` e `python -m mutmut export-cicd-stats`.
   - `chore`: cumpra o aceite do item à risca.
   - `levantamento`: só escreve análise em `docs/` e, se o item pedir, script em `scripts/`. Não altera módulos de produção.
   - `limpeza`: remova só o que o item lista. Antes de remover, confirme por busca que nada usa o que sai. Arquivo rastreado sai com `git rm`, ou `git rm --cached` se deve continuar existindo localmente. Depois, rode de novo as ferramentas do inventário e atualize `docs/limpeza/inventario.md`.
4. **Verificação.** `python -m pytest -q` e `ruff check --select E9,F63,F7,F82 .` verdes — o mesmo gate do CI. Também verde, e bloqueante, o `ruff check` com as regras completas em `sentinela/methods/` e `sentinela/data/`, só nos diretórios que existirem (o ruff falha com E902 em caminho inexistente). Fora desses diretórios, a dívida antiga do `ruff check .` completo fica no inventário (F0-7) e é paga a partir da Fase 1. `ruff format` só nos arquivos que o item criou ou alterou. No máximo 3 rodadas de correção; na 3ª falha, marque `[!]`, registre no diário e pare o loop.
5. **Sem resíduo novo.** O item não acrescenta código comentado, import sem uso, print de depuração, arquivo temporário nem TODO sem item na fila.
6. **Diário.** Escreva a seção do item, no formato abaixo, em `outputs/diario-item.md` (fora do git) e anexe-a com `python scripts/fila.py diario outputs/diario-item.md`, sem abrir o diário.
7. **Fila.** `python scripts/fila.py marcar <ID> x` (ou `!`); ele altera exatamente a linha do item. Saída 2 (ID inexistente ou duplicado): o arquivo fica intacto; registre no diário e pare.
8. **Stage.** `git add` só nos arquivos do item, no diário e na fila, e em `docs/loop/pendencias.md` quando o item escreveu nele (a linha nova é parte do item) — nunca `git add -A` nem `git add .`. Confira com `git status --porcelain` que nada do item ficou de fora e que nada alheio entrou.
9. **Revisão.** `/review-diff`, que revisa exatamente o que está no stage — código, diário e fila. Reprovou: corrija, atualize a seção do item no diário sem abri-lo inteiro (localize com `grep -n "^### <ID>" docs/loop/diario.md` e edite só essa faixa; não rode `fila.py diario` de novo, que duplicaria a seção), refaça o stage e revise de novo; conta nas 3 rodadas. Na 3ª reprovação, troque o `[x]` por `[!]`, registre o motivo no diário e pare o loop.
10. **Commit.** `/safe-commit`, um único commit por item. Ele não faz stage: commita exatamente o que o `/review-diff` aprovou. Título = o Conventional Commit do item. Nunca push.
11. **Progresso.** Rode `python scripts/fila.py status` e `git --no-pager log --oneline -3`.
12. **Próximo.** Siga para o próximo `[ ]` com `python scripts/fila.py proximo`. Se ele sair com 3 (`[DECISÃO]` à frente), pare: a fila acabou.

## Regras duras

- Nunca `git push`, abrir PR, `git reset --hard`, `git clean`, `git commit --amend`, `git add -A` ou `git add .`.
- Refactor e mudança de comportamento nunca no mesmo commit.
- Não tocar nos arquivos intocáveis do cabeçalho da fila. Se um item parecer exigir isso, marque `[!]` (caso (b)) e siga a seção "Item bloqueado".
- Não remover, pular (`skip`) nem enfraquecer testes para a suíte passar.
- Remoção só do que o git devolve: arquivo rastreado, com `git rm`. Arquivo não rastreado e branch nunca são apagados pelo loop — vão para a lista do Marcos no diário. Item *investigar* do inventário nunca sai sem decisão.
- Mutação sempre com a configuração do `[tool.mutmut]`, que desliga o `xfail_strict` só nessas rodadas. `mutants/` nunca entra em commit.
- Métodos de valuation não ganham rede, banco nem leitura de relógio.
- O repositório é público: dados da carteira do Marcos (posições, pesos, lista de ativos) nunca entram em arquivo versionado — nem no diário. O que usar a carteira vai para `outputs/`.
- Não fazer perguntas durante o loop. Onde a especificação dizia "me diga", "me mostre" ou "pare e me mostre o diff", escreva no diário e siga. Dúvida que muda o resultado vira `[!]` e registro no diário; se o loop para ou segue, diz a seção "Item bloqueado".
- Toda decisão provisória e todo `[!]` ganham também uma linha em `docs/loop/pendencias.md`: `python scripts/fila.py pendencia <ID> "<texto>"`. O Marcos revisa esse arquivo uma vez por dia.
- Leitura por trecho: não abrir inteiros `docs/loop/fila.md`, `docs/loop/diario.md`, `docs/loop/fila-fase*-proposta.md`, `docs/PLANO.md`, `docs/decisoes/predicados-golden-2c.md`, `docs/loop/historico/**` nem `tests/fixtures/golden_motores.jsonl`. Consulta por `grep -n` e faixa de linhas; estado e próximo item pelo `scripts/fila.py`. Exceção: o item que manda editar a estrutura de um desses arquivos.
- Comando ou script de dados imprime no máximo 30 linhas no contexto; o restante vai para `outputs/`.
- O retorno do `junior-dev` ao orquestrador tem no máximo 15 linhas: arquivos, testes antes → depois, pendências.
- Ideia nova não entra em fila ativa: vai para `docs/loop/ideias.md` e só é avaliada num checkpoint.

## Item bloqueado

Os casos são os do plano final da 2B (`docs/decisoes/plano-final-2b.md` §1.4).

- Item marcado `[!]` pelos casos (a) regra econômica não prevista, (b) arquivo fora das permissões, (e) fonte oficial indisponível ou (f) bug que exige decisão de destino: registre a pendência (`python scripts/fila.py pendencia <ID> "<motivo>"`) e o motivo no diário, e siga só com os itens de `python scripts/fila.py independentes <ID>`, na ordem da fila, no máximo três adiante. Esgotados esses três, ou a lista, pare.
- Item de resumo, de limpeza ou de arquivamento nunca roda com `[!]` aberto: chegando a ele, pare.
- Param o loop como antes: `[!]` pelo caso (c) teste que só passaria enfraquecido ou (d) golden fora do predicado; parada por pergunta prevista no pacote da fase; terceira reprovação na revisão (passo 9); terceira falha da verificação (passo 4).

## Bugs e regressão

Decisão do Marcos de 15/10/2026. Registro e detalhe em `tests/regressao/README.md`.

1. Bug confirmado (auditoria, revisão ou uso) vira teste em `tests/regressao/` no mesmo dia, antes de qualquer correção.
2. Bug ainda não corrigido fica xfail estrito com ID e item que corrige; o `xfail_strict` do `pytest.ini` faz o CI quebrar se ele passar sem a marca ser retirada.
3. A correção retira a marca, o teste fica para sempre e o registro muda para "corrigido".
4. Nenhum item `fix:` fecha sem o teste de regressão do bug que corrige.

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
5. faz o stage, passa pelo `/review-diff`, commita com `/safe-commit` e roda `python scripts/fila.py status`.

A próxima fila nunca é ativada pelo loop: quem a coloca em `docs/loop/fila.md` é o Marcos, depois de aprovar.

<!-- multiagente 14/10/2026 -->
## Troca de executor (14/10/2026)

1. **Retomar.** Quem assume a fila roda a skill `retomar` antes de qualquer edição.
2. **Passagem.** Quem sai com item pela metade roda a skill `passagem`. Se a cota acabou sem aviso, quem assume reconstrói pelo `git status`, pelo diário e pela memória, nessa ordem de autoridade.
3. **Registro.** A entrada do diário de cada item traz `**Executor:** <claude-code | codex | antigravity> (<modelo>)`, e o corpo do commit termina com `Executor: <ferramenta>`.
4. **Revisão do item.** Valem as mesmas três rodadas. Revisor de outra família quando houver cota; senão, sessão nova e somente leitura do mesmo CLI.
5. **Um executor por vez.** Nunca dois agentes escrevendo no branch da fase ao mesmo tempo.
