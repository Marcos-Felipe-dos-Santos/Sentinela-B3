# Auditoria cruzada da 3-b: commits `Executor: codex` (claude-code, 13/11/2026)

**Passo 6 do `/goal`.** No checkpoint de metade, cada família audita os itens da outra, em modo FASE, só lendo o código, sem nenhuma alteração.

**Escopo:** o intervalo `1eb01f0..5f87185` do branch `v2/fase-3`. Ele vai do fechamento do checkpoint da 3-a até o HEAD desta sessão.

## Resultado

`git log 1eb01f0..5f87185 --grep "Executor: codex"` não devolve nenhum commit. Os 44 commits do intervalo são todos `Executor: claude-code`:
- a 3-b inteira até aqui: L1, macro histórico, F3-3, F3-4, F3-5, F3-7, F3-3b-fix e F3-3d, os estudos P07, P09, P10, P11, P14 e P15;
- as correções da auditoria do Gemini (F3-A-F6 a F3-A-F10).

Não há item da outra família para esta auditoria, e por isso ela não tem achados.

## O que fica para a outra família

A auditoria cruzada dos commits `Executor: claude-code` da 3-b cabe ao Codex quando ele retomar, no mesmo modo FASE e no mesmo intervalo. Para essa auditoria, os pontos de maior risco são:
- `e654cba` · F3-3d, a ligação do histórico ao serviço:
  - o recorte pela entrega (DD-61) muda as asserções do `test_bug_3_12`;
  - a remontagem dos ZIPs vem do banco (DD-62);
  - o motor histórico funciona sem fontes correntes;
  - todas as lentes se abstêm numa data passada, e por isso o F3-3e está `[!]`.
- `1ec90ed` · F3-3b-fix: a tabela `conflitos_carga` e a releitura do banco real.
- `8685525` · F3-7b: o backfill sobre o banco real, com backup verificado.
- `c4bd010` e `852aa86` · F3-5 e F3-5-fix: o universo ponto-no-tempo e a DD-60, que deixa sem código no FCA as ações anteriores a 2018.
- As decisões delegadas DD-34 a DD-63, da família claude-code, que estão sem a marca "confere" ou "contesta" do Codex (política §2).

## Estado do checkpoint

O item `[DECISÃO]` do checkpoint da 3-b vem depois do F3-B-R, que é o resumo da metade. Os dois esperam a resposta do Marcos ao F3-3e `[!]`, porque um item de resumo não roda com `[!]` aberto (protocolo, "Item bloqueado").
