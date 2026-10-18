---
name: retomar
description: Use ao abrir uma sessão do Sentinela B3 para continuar trabalho já começado, depois de troca de agente, cota esgotada, PC desligado ou pausa. Não use no meio de um item que você mesmo está executando nesta sessão.
---

# Retomar

Objetivo: saber exatamente onde o trabalho está **antes** de editar qualquer arquivo. Vale para Claude Code, Codex e Antigravity.

## 1. Ler, nesta ordem

1. `AGENTS.md` (seção "Multiagente") e `docs/loop/protocolo.md`.
2. `docs/loop/fila.md`: o cabeçalho e o primeiro item que não está `[x]` antes do primeiro `[DECISÃO]`.
3. `docs/loop/diario.md`: a última seção.
4. `outputs/passagem.md`, se existir (é escrito pela skill `passagem`; fica fora do git).
5. O resumo do `ai-memory`, se a sessão recebeu um. É **pista**: onde divergir do git, da fila ou do diário, valem o git, a fila e o diário.

## 2. Conferir o estado real

```bash
git branch --show-current
git --no-pager log --oneline -5
git status --short
git stash list
```

## 3. Classificar

- **A. Limpo:** `git status` vazio e o último commit fecha o último item `[x]`. Próximo passo: o primeiro item `[ ]`.
- **B. Item pela metade:** há arquivos alterados. Liste cada um e diga a qual item pertence, o que a passagem (ou a memória) diz que foi feito e o que falta. Se as mudanças não correspondem a nenhum item da fila, é o caso C.
- **C. Parar:** item `[!]`, `[DECISÃO]` à frente, mudanças que não se explicam, branch errado, ou divergência entre memória e git que muda o próximo passo.

## 4. Responder antes de agir

Escreva o bloco abaixo. Com o Marcos presente, mostre e espere o "ok" no caso B ou C. Em execução autônoma (`/goal`, `executar-fila`), grave o bloco no topo de `outputs/passagem.md` e:
- caso A: siga o protocolo;
- caso B: continue o item só se as mudanças batem com o item e com a passagem; senão guarde com `git stash push -u -m "wip <item> <executor anterior>"`, registre no diário e recomece o item;
- caso C: pare.

```
## Retomada — <data e hora> — <executor que assume>
- Branch e HEAD: <branch> @ <hash>
- Classificação: A | B | C
- Item: F2A-xx · <título>
- Já feito (com evidência): <commit, arquivos, testes>
- Falta: <próximos passos>
- Divergências memória × git/fila/diário: <lista ou "nenhuma">
- Decisões do Marcos pendentes: <lista ou "nenhuma">
```

## Nunca

- Editar antes de escrever o bloco "Retomada".
- `git push`, abrir PR, ler ou alterar `.env`, apagar arquivo não rastreado (o `stash -u` guarda, não apaga).
- Tomar decisão de método, taxa, janela ou limiar.
