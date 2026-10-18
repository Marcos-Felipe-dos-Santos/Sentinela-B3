---
name: executar-fila
description: Use quando um agente que não é o Claude Code (Codex, Antigravity) for executar itens da fila do Sentinela B3, por exemplo quando a cota do Claude acabou. O Claude Code não usa esta skill; ele usa o /goal e as próprias skills.
---

# Executar a fila (fora do Claude Code)

Objetivo: fazer o mesmo que o loop do Claude Code faz, com as mesmas regras, em outro CLI.

## 0. Antes de tudo

Rode a skill `retomar`. Só siga se a classificação for A ou B.

## 1. O protocolo vale inteiro

Leia `docs/loop/protocolo.md` e siga-o à risca, item por item, na ordem da fila. Traduções para quem não é o Claude Code:

| No protocolo | O que você faz |
|---|---|
| `/review-diff` | Leia o arquivo da skill (`.claude/skills/review-diff/SKILL.md`, ou `.claude/commands/review-diff.md` se for comando) e aplique a checklist ao diff em stage. Onde ela manda acionar subagentes do Claude (`.claude/agents/`), faça a revisão numa **sessão nova e somente leitura** do seu CLI, passando o diff e a checklist. No Codex: `codex exec --sandbox read-only "<checklist da review-diff> Revise o diff em stage: git diff --cached"`. Se o Marcos avisar que o Claude tem cota, peça a ele para rodar o `/review-diff` no Claude: revisor de outra família é melhor. |
| `/safe-commit` | Leia o arquivo da skill (`.claude/skills/safe-commit/SKILL.md`, ou `.claude/commands/safe-commit.md`) e siga os passos. Não rode `git add` dentro dela; o stage é feito antes, pelo protocolo. |
| `/goal` | Esta skill. As condições de parada são as mesmas (seção 3). |

## 2. Registro do executor

- No diário, a entrada de cada item ganha a linha `**Executor:** <codex | antigravity> (<modelo>)`.
- No commit, o corpo da mensagem termina com `Executor: <codex | antigravity>`.

O checkpoint usa isso para escolher o auditor (ADR-0003, D30).

## 3. Parar quando

- todos os itens antes do primeiro `[DECISÃO]` estiverem `[x]`;
- um item ficar `[!]`, com o motivo no diário;
- um item for reprovado três vezes na revisão;
- o item precisar de rede e o seu sandbox não tiver (marque `[!]` com o motivo "precisa de rede: rodar no Claude Code ou liberar a rede só para este item");
- a cota estiver acabando: rode a skill `passagem` antes.

Ao fechar cada item, mostre `cat docs/loop/fila.md` (só o item) e `git --no-pager log --oneline -3`.

## Nunca

- `git push`, abrir PR, apagar arquivo não rastreado ou branch (remoção só por `git rm` quando o item manda).
- Ler ou alterar `.env`.
- Mudar a seção "Fase atual" do `AGENTS.md`.
- Regenerar o golden fora de item **[golden]**.
- Decidir método, taxa, janela ou limiar: isso vira `[DECISÃO]` ou `[!]`.
- Usar "recomendação", "compra", "venda" ou "alocação sugerida" em código novo.
- Colocar dado da carteira em arquivo versionado.
