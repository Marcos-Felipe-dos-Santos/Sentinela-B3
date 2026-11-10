# Diário — Fase 3

Processo F3-0, bloco 1, antes da ativação da 3-a. O diário do fechamento da 2C está em `docs/loop/historico/fase-2c/diario-fechamento.md`.

### Preparação — Processo F3-0, bloco 1
- **Executor:** claude-code (Claude Opus 5.5).
- **Estado inicial:** branch `v2/fase-3` @ `09ac499` (fila do Bloco 1 montada); venv `venv/bin/python` confirmada; documentos obrigatórios do protocolo presentes. `python -m pytest -q`: 3525 passed, 1 skipped, 8 xfailed, 1 warning. Golden SHA256 `500645a3…`.

### F3-0a — feat: add a queue helper for status, next item and diary entries
- **Executor:** claude-code (Claude Opus 5.5).
- **Status:** sucesso.
- **O que foi feito:** `scripts/fila.py`, só biblioteca padrão, com os subcomandos `status`, `proximo` (saída 3 quando a próxima linha aberta é `[DECISÃO]`), `item`, `marcar`, `independentes`, `diario` e `pendencia`, sobre `docs/loop/fila.md` (`--fila`, `--diario` e `--pendencias` configuráveis). `marcar`, `item` e `independentes` falham com saída 2 para ID inexistente ou duplicado, sem tocar o arquivo. `independentes` considera os itens abertos antes do primeiro `[DECISÃO]` aberto, exclui quem cita o ID (com borda, para não confundir T-3 com T-30) e quem compartilha caminho entre crases fora de `tests/` e `docs/`, por igualdade ou prefixo de diretório. O relógio só é lido para datar a pendência (data local).
- **Dificuldades:** o Ruff completo apontou DTZ011 em `date.today()`.
- **Como resolvi:** data local por `datetime.now(UTC).astimezone().date()`.
- **Testes:** primeiro vermelhos (28 erros, script ausente). Depois 3525 → 3563 passed, 1 skipped, 8 xfailed. Mutação à mão (`scripts/` fora do mutmut, pacote §3): 20 mutações, uma por função ou ramo (`_branch`, `_item`, `_ate_decisao`, `_localizar` vazio e duplicado, `_caminhos` filtros, `_compartilham`, `_cita`, limite e próximo do `status`, `proximo`, `marcar`, `independentes`, `_anexar` separador e quebra de linha, `diario`, `pendencia` texto e cabeçalho); a primeira rodada deixou `_branch` vivo, coberto por um teste com repositório git temporário; depois, 20 de 20 mortas. Ruff CI, Ruff completo em `sentinela/methods` e `sentinela/data` e nos dois arquivos novos: verdes. Golden SHA igual.
- **Revisão 1 (`/review-diff`):** PODE COMMITAR, com pontos médios. Corrigidos: saída 1 do `proximo` e saída 2 documentadas no docstring; teste do `_branch` com `commit.gpgsign=false`; três testes de borda (CRLF no `marcar`, ID duplicado no `independentes`, diário de destino ausente). O teste de CRLF achou defeito real: `read_text` convertia `\r\n` em `\n` e o `marcar` reescreveria todas as linhas de uma fila com CRLF; corrigido lendo e gravando com `newline=""`.
- **Revisão 2 (`/review-diff`):** PODE COMMITAR, com dois pontos médios no próprio item, corrigidos: (1) fila ausente saía com traceback e código 1, o mesmo de "nada aberto", e o loop poderia concluir que a fila acabou; agora `ErroFila` e saída 2, com motivo; (2) `diario` e `pendencia` ainda convertiam CRLF; leitura e gravação passam por `_ler`/`_gravar` com `newline=""`, e o anexo segue o fim de linha que o destino já usa. O teste do `_branch` remove as variáveis `GIT_*` do ambiente. Os seis testes novos falham contra a versão anterior do script (6 failed, 32 passed) e passam na atual.
- **Resíduos:** nenhum no repositório; `outputs/diario-item.md` fica fora do git.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** `independentes` olha a dependência num sentido só, como o aceite pede: exclui quem cita o ID bloqueado, mas um item bloqueado que diga "depende do T-2" não exclui o T-2; um `[DECISÃO]` marcado `[!]` não interrompe a contagem (só o `[DECISÃO]` aberto, `[ ]`, conta como fim); a heurística de caminho de `independentes` (token entre crases com `/` ou extensão conhecida; mensagens de commit e comandos não contam) e o formato da linha de pendência (`- AAAA-MM-DD · ID · texto`).

### F3-0b — docs: read loop files by excerpt during execution
- **Executor:** claude-code (Claude Opus 5.5).
- **Status:** sucesso.
- **O que foi feito:** (1) protocolo: cada item começa com `python scripts/fila.py proximo` (saídas 3, 1 e 2 tratadas); passo 6 escreve em `outputs/diario-item.md` e anexa com `fila.py diario`; passo 7 usa `fila.py marcar`; passo 11 troca o `cat` por `fila.py status` e `git --no-pager log --oneline -3`, e o passo 5 do arquivamento troca o `cat` por `fila.py status`; passo 12 usa a saída 3. (2) Regras duras novas: pendência por `fila.py pendencia` para decisão provisória e `[!]`; leitura por trecho dos sete arquivos/pastas listados, com a exceção do item que edita a estrutura; saída de comando de dados ≤ 30 linhas; retorno do `junior-dev` ≤ 15 linhas; ideia nova em `docs/loop/ideias.md`. (3) `retomar` 1.2 e 1.3 por `fila.py status`/`proximo` e `tail -n 40`. (4) `executar-fila`: `fila.py status` ao fechar o item. (5) `review-diff`: o item é a linha alterada da fila no diff; o revisor não abre fila nem diário. (6) `/goal` do ciclo §6 sem `cat`. (7) `docs/loop/ideias.md` com a regra P4 e a entrada da seção 4 do pacote, copiada sem alteração.
- **Conferência contra o `scripts/fila.py`:** saídas 1 (nada aberto) e 3 (`[DECISÃO]` à frente) do `proximo`; saída 2 por fila ausente (todos os subcomandos de fila), ID inexistente ou duplicado (`item`, `marcar`, `independentes`) ou entrada do diário ausente (`diario`); `marcar <ID> x|!`; `diario` anexa sem imprimir; `pendencia` cria o arquivo se faltar.
- **Dificuldades:** o `fila.py` só reconhece `- [ ] **[DECISÃO] ...**`; as filas arquivadas das fases 0 a 2C fecham com `- [DECISÃO] **...**` (apontado na terceira revisão do F3-0a).
- **Como resolvi:** o protocolo fixa o formato `- [ ] **[DECISÃO] ...**` no início do ciclo por item, para a afirmação sobre `proximo` ficar verdadeira.
- **Testes:** 3563 passed, 1 skipped, 8 xfailed → igual (item documental). Golden SHA igual.
- **Revisão 1 (`/review-diff`):** NAO PODE COMMITAR só por texto: a saída 2 do `proximo` citava "ID duplicado" (só `item`, `marcar` e `independentes` checam ID) e o diário atribuía `git log` ao passo 5 do arquivamento. Corrigidos; também, pelos pontos médios: saída 2 do `marcar` no passo 7, `docs/loop/pendencias.md` no stage quando o item escreve nele (passo 8) e correção do diário por faixa no passo 9, sem rodar `fila.py diario` de novo. Reprovação só de texto: corrigida e commitada sem nova rodada (plano final da 2B, regra 5).
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** a frase do formato de `[DECISÃO]` no protocolo; a partir deste commit vale o protocolo novo. Pendências do F3-0a ainda sem destino: `independentes` ignora caminho com `:linha` e glob; `test_branch_fora_de_repositorio_nao_quebra` não limpa `GIT_*`.

### F3-0c — docs: let independent items continue after a blocked item
- **Executor:** claude-code (Claude Opus 5.5).
- **Status:** sucesso.
- **O que foi feito:** seção nova "Item bloqueado" no protocolo: `[!]` pelos casos (a), (b), (e) ou (f) registra a pendência e segue só com `python scripts/fila.py independentes <ID>`, na ordem da fila, no máximo três adiante; resumo, limpeza e arquivamento nunca rodam com `[!]` aberto; (c), (d), parada por pergunta do pacote da fase, terceira reprovação e terceira falha da verificação param como antes. Ajustados só os trechos em contradição: regra dura dos intocáveis (era "marque `[!]` e pare"), regra das perguntas (era "registro no diário e parada"), condição de parada da `executar-fila` (§3) e a etapa 4 do ciclo.
- **Conferência contra o `scripts/fila.py`:** `independentes` lista os itens abertos antes do primeiro `[DECISÃO]` aberto, na ordem da fila, excluindo quem cita o ID ou compartilha caminho fora de `tests/` e `docs/`.
- **Dificuldades:** o `/goal` do ciclo §6 termina quando "algum item está `[!]`", o que contradiz a regra P2; o item só autoriza a etapa 4 do ciclo.
- **Como resolvi:** não editei o §6; registrei a pendência em `docs/loop/pendencias.md`.
- **Testes:** 3563 passed, 1 skipped, 8 xfailed → igual (item documental). Golden SHA igual.
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** o texto do `/goal` (pendência acima).
- **Para o Marcos revisar:** a terceira falha da verificação (passo 4) continua parando o loop; o pacote não a lista entre os casos que seguem.

### Adendo — pendências do Bloco 1 (F3-0h e F3-0i na fila)
- **Executor:** claude-code (Claude Opus 5.5).
- **O que foi feito:** decisões do Marcos de 09/11/2026 anexadas como adendo ao fim de `docs/decisoes/decisoes-processo-f3-0.md`, sem alterar o texto original (SHA256 anterior `29dabe40…`; o diff só acrescenta linhas); F3-0h e F3-0i inseridos na fila antes do `[DECISÃO] Processo F3-0, bloco 1`; o cabeçalho da fila passa a dizer de onde vêm as linhas.
- **Estado:** `fila.py status`: [x] 3, [ ] 2, próximo F3-0h. A 3-a continua inativa.

### F3-0h — fix: make queue independence conservative
- **Executor:** claude-code (Claude Opus 5.5).
- **Status:** sucesso.
- **O que foi feito:** `independentes` ficou conservador em `scripts/fila.py`: conta todo caminho entre crases, menos `docs/loop/fila.md`, `docs/loop/diario.md` e `docs/loop/pendencias.md` (`_DO_LOOP`); corta o sufixo `:linha` (`:332`, `:10-20`, `:10,20`); com curinga (`*`, `?`, `[`) em qualquer lado, os dois caminhos casam quando a parte fixa de um prefixa a do outro, nos dois sentidos (superconjunto do casamento por padrão); sem curinga, igualdade ou diretório-prefixo, com ou sem barra final; o item é dependente se citar o alvo ou for citado por ele; trecho com cara de caminho que não casa com a forma reconhecida (chaves, `~`, caminho absoluto, URL) ou que o script não normaliza (segmento `.` ou `..`, ponto final) torna o item dependente, e no alvo deixa a lista vazia; qualquer `[DECISÃO]` que não esteja `[x]` encerra a contagem (`status`, `independentes`) e também faz o `proximo` sair com 3. O teste `test_branch_fora_de_repositorio_nao_quebra` limpa as variáveis `GIT_*`.
- **Teste vermelho antes da correção:** com os testes novos e o script antigo, 20 falhas (18 testes novos e dois antigos cuja expectativa mudou por decisão: `test_independentes_exclui_citacao_e_caminho_compartilhado`, em que T-6 passa a depender de T-3 por `docs/b.md` e `tests/test_y.py`, e `test_caminhos_ignoram_mensagem_de_commit_e_comando`, que passa a incluir `docs/x.md`). O teste do `_branch`, na versão antiga, falha com `GIT_DIR` apontando para o repositório e passa na nova.
- **Revisão, rodada 1:** NÃO PODE COMMITAR só pelo diário (contava 13 mutações; eram 12, com 13 execuções). Médios atendidos na rodada 2: `./x`, `x/../y` e ponto final davam falsa independência (três testes vermelhos, depois `_legivel`); o caso `scripts/x.py:10-20` não distinguia o corte do sufixo, e entraram `sentinela/data/a.py:10,20` e `test_sufixo_de_linha_cortado_deixa_o_caminho_comparavel`.
- **Mutação à mão** (`scripts/` fora do `source_paths` do mutmut): 14 mutações, todas mortas (16 execuções), cada uma contra o teste novo da regra: exclusão do loop retirada; `tests/` e `docs/` de volta aos ignorados; sem corte de `:linha` (contra os dois testes do sufixo); ponto final aceito; segmento `.` e `..` aceito; curinga que nunca casa; curinga num sentido só; raiz sem corte; diretório com barra final sem `rstrip`; citação num sentido só; candidato ilegível aceito; alvo ilegível aceito; só `[DECISÃO]` aberto encerra (dois testes); `proximo` pulando `[DECISÃO]` `[!]`. A do diretório com barra final sobreviveu na primeira rodada e ganhou o caso `sentinela/data/` no teste paramétrico.
- **Efeito na fila real:** o F3-0i cita `/goal`, que o script não interpreta, então `independentes` não lista nada para o F3-0h nem para o F3-0i. É o comportamento conservador pedido; vale para qualquer item que cite comando com barra no início.
- **Decisão provisória:** o item é `fix`, mas lista só `scripts/fila.py` e `tests/test_script_fila.py`; os testes de regressão ficaram neste arquivo, e não em `tests/regressao/` com registro no README, como pede a regra de bugs. Segui a lista de arquivos do item. Registrado em `docs/loop/pendencias.md`.
- **Testes:** 3563 passed, 1 skipped, 8 xfailed → 3594 passed, 1 skipped, 8 xfailed (+31; 26 na rodada 1 e 5 na 2). Ruff CI, Ruff completo em `sentinela/methods` e `sentinela/data`, Ruff dos dois arquivos: verdes. Golden SHA igual.
- **Resíduos:** nenhum no repositório; saídas em `outputs/f3-0h-vermelho.txt`, `outputs/f3-0h-vermelho-r2.txt` e `outputs/f3-0h-mutacao.txt`.
- **Decisões que ficaram para o Marcos:** a regra de regressão para `fix` de script (acima).
- **Para o Marcos revisar:** o `proximo` também passou a parar em `[DECISÃO]` `[!]`; o aceite falava em "contagem", e estendi ao `proximo` para não pular um checkpoint bloqueado.

### F3-0i — docs: align the goal and the blocked-item rule
- **Executor:** claude-code (Claude Opus 5.5).
- **Status:** sucesso.
- **O que foi feito:** o `/goal` do ciclo §6 termina quando todos os itens antes do `[DECISÃO]` estão `[x]`, ou o protocolo mandou parar (motivo no diário), ou não resta item executável: todo item aberto antes do `[DECISÃO]` está `[!]`, depende de um `[!]` (`python scripts/fila.py independentes <ID>`) ou ficou além do limite de três adiante. Protocolo, "Item bloqueado": um segundo `[!]` entre os independentes para o loop, sem nova busca de independentes; a terceira falha da verificação (passo 4) continua parando, também num item independente, e não abre a busca. `executar-fila` §3 ganhou as mesmas duas paradas. Saiu de `docs/loop/pendencias.md` a linha do F3-0c sobre o `/goal`; fica a do F3-0h.
- **Conferência contra o `scripts/fila.py`:** `independentes` (F3-0h) lista os itens abertos antes do primeiro `[DECISÃO]` não-`[x]`, excluindo os que citam ou são citados pelo alvo, compartilham caminho ou trazem caminho que o script não interpreta; com caminho ilegível no alvo, a lista sai vazia.
- **Dificuldades:** a lista de arquivos do item não traz `docs/loop/pendencias.md`, mas o aceite manda tirar a pendência; segui o aceite. A linha da etapa 4 na tabela do ciclo ("ou parada em `[!]`") fica fora do §6 e não foi editada.
- **Testes:** 3594 passed, 1 skipped, 8 xfailed → igual (item documental). Golden SHA igual.
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** fora do §6, a linha da etapa 4 na tabela do ciclo ("ou parada em `[!]`") e o parágrafo do `[!]` (a)/(b)/(e)/(f) da etapa 4, que não fala do segundo `[!]` nem da terceira falha num independente; com o F3-0h, um item que cita comando com barra no início (`/goal`) fica sem independentes quando é o `[!]` e nunca entra na lista de independentes de outro `[!]`.

### Segundo adendo — segunda rodada do Bloco 1 (F3-0j e F3-0k na fila)
- **Executor:** claude-code (Claude Opus 5.5).
- **O que foi feito:** decisões do Marcos de 09/11/2026 anexadas como segundo adendo ao fim de `docs/decisoes/decisoes-processo-f3-0.md`, só com acréscimo; F3-0j e F3-0k inseridos na fila antes do `[DECISÃO] Processo F3-0, bloco 1`; cabeçalho da fila atualizado. Saiu de `docs/loop/pendencias.md` a linha do F3-0h (decisão 1); as decisões 2 e 3 respondiam a observações do diário do F3-0h e do F3-0i, sem linha em `pendencias.md`, que fica só com o cabeçalho.
- **Estado:** `fila.py status`: [x] 5, [ ] 2, próximo F3-0j. A 3-a continua inativa.
