# Diário do loop — Fase 2A

**Estado inicial (preparação):** branch `v2/fase-2a`, `which python` → `venv/bin/python`, documentos obrigatórios presentes. `python -m pytest -q`: 685 passed, 1 skipped, 2 xfailed.

### F2A-15 — chore: add golden diff tool for scoped regeneration
- **Status:** sucesso
- **O que foi feito:** `scripts/golden_diff.py` compara o golden do `HEAD` (`git show`) ou de `--base` com o da árvore de trabalho, por (motor, id): lista alterados, incluídos e removidos. `--onde` avalia a expressão (com `caso`, `entrada`, `saida_antiga`, `saida_nova`) só nos alterados e sai com 1 se algum falhar. `--par ANTIGO=NOVO` pareia removidos e incluídos e mostra a diferença campo a campo. Sem dependência nova; não roda o gerador nem altera o golden.
- **Dificuldades:** `eval` com escopo local não enxerga as variáveis dentro de geradores (`any(... for ...)`).
- **Como resolvi:** as variáveis do predicado vão no dicionário de globals do `eval`, com builtins restritos a uma lista curta.
- **Testes:** 685 passed, 1 skipped, 2 xfailed → 691 passed, 1 skipped, 2 xfailed (6 novos em `tests/test_golden_diff.py`, incluindo os 3 do aceite). Rodado sem mudança no golden: 0 alterados, 0 incluídos, 0 removidos.
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** o `eval` do `--onde` é ferramenta de desenvolvimento, para expressões escritas por quem roda o script.

### F2A-17 — refactor: cache parsed CVM statements per file
- **Status:** sucesso
- **O que foi feito:** `CVMProvider.parsear_demonstrativo` virou um invólucro com memoização por processo; o corpo antigo passou, sem mudança, para `_parsear_sem_cache`. A chave é (caminho resolvido, `mtime_ns`, tamanho, tipo, `include_cd_cvm`, `include_versao`). Há trava por chave (duas threads não leem o mesmo arquivo), limite de 32 entradas (LRU) e devolução de cópia, para que quem recebe o DataFrame não suje o cache. Exceção não entra no cache. Sem Parquet nem dependência nova. O DataFrame guardado já é o filtrado, só com as colunas de saída.
- **Dificuldades:** a primeira versão apagava travas de chaves que ainda não estavam no cache, o que permitiria leitura duplicada.
- **Como resolvi:** as travas não são removidas, e a chave da trava não leva `mtime` nem tamanho: o dicionário cresce só com o número de pares (arquivo, tipo, flags), que é pequeno e não aumenta a cada download.
- **Testes:** 691 passed, 1 skipped, 2 xfailed → 697 passed, 1 skipped, 2 xfailed. Seis novos em `tests/test_cvm_provider_cache.py` (os dois do aceite, mais concorrência, flags, exceção e limite), com fixture que limpa o cache entre testes. Revisão: o teste de concorrência agora força sobreposição (pausa de 0,1 s na leitura) e, com a trava removida à mão, falha; o de exceção confere que `_read_raw`/busca são tentados de novo. Nenhum teste existente mudou (`git diff --cached --name-status -- tests/` só mostra `A`); golden sem diferença.
- **Medida** (`calcular_indicadores(4170, anos=5)`, ZIPs 2021–2025 já em `data/cvm/`, download desligado, dois processos separados): antes, 2,43 s na primeira chamada e 2,35 s na segunda; depois, 2,46 s e 0,03 s. Pico de memória do processo: 376 MB → 324 MB. A diferença de memória não é ganho do item: são execuções separadas, e o cache só acrescenta DataFrames retidos.
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** o cache vive até o fim do processo; um ZIP trocado no disco com mesmo `mtime` e tamanho não seria detectado (improvável).
