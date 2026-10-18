---
name: verificar-entrega
description: Use para conferir se um item da fila do Sentinela B3 foi de fato entregue (commit do loop, trabalho de outro agente ou PR do Jules) antes de aceitar, marcar [x] ou fazer merge. Somente leitura.
---

# Verificar entrega

Este é o modo ITEM da auditoria externa. As regras completas estão em `docs/loop/auditoria-externa.md`; leia o arquivo antes de começar.

## Regras

- **Somente leitura.** Não edite, não faça commit, não rode nada que escreva no repositório. Para rodar testes, use o que o item manda, sem `--update`, sem regenerar golden.
- **Evidência acima de narrativa.** Diário, mensagem de commit e descrição de PR são alegações; confira cada uma no diff ou rodando um comando.
- Se você executou o item, você não pode verificá-lo. Diga isso e pare.

## Passos

1. **Escopo.** Identifique o item (`docs/loop/fila.md`) e os commits dele:
   ```bash
   git --no-pager log --oneline -10
   git --no-pager show --stat <commit>
   ```
2. **Diff existe e bate com o item** (checklist 1 da auditoria): arquivos alterados de verdade, só os permitidos pelo item, nada de script auxiliar solto.
3. **Aceite, linha por linha.** Para cada linha do **Aceite** do item: o teste existe, tem o nome pedido e passa; o xfail estrito foi retirado e está em PASS; golden inalterado quando o item manda (`git diff --exit-code <commit>~1 <commit> -- tests/fixtures/golden_motores.jsonl`).
4. **Diário bate com o código** (checklist 2) e **testes provam o que dizem** (checklist 3).
5. Itens 4 a 10 do checklist (unidades, tempo, abstenção, comportamento escondido, privacidade, vocabulário, métrica não é validade), no que se aplicar ao item.

## Resposta

No formato da auditoria externa: achados com severidade (**bloqueia**, **ressalva**, **sugestão**) e evidência `arquivo:linha`; "Recalculado por mim"; "Não verificado"; "Perguntas para o Marcos"; veredito em uma linha: "pode seguir", "pode seguir com ressalvas" ou "não pode seguir".
