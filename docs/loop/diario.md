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
