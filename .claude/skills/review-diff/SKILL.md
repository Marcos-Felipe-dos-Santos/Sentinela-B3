---
name: review-diff
description: Revisa o que está no stage — código, diário e fila juntos. Use sempre antes de qualquer commit.
context: fork
agent: senior-reviewer
allowed-tools: Bash(git status *), Bash(git diff *)
---

Revise o stage com foco em: $ARGUMENTS

Pré-condição: o item já está no stage (passo 8 de `docs/loop/protocolo.md`): código,
`docs/loop/diario.md` e `docs/loop/fila.md` juntos. Você não tem Bash; o estado do
repositório vem injetado abaixo. Use Read, Grep e Glob só para ler o código ao redor
e o item na fila.

## Estado do repositório

### git status --porcelain
!`git status --porcelain`

### git diff --staged --stat
!`git diff --staged --stat`

### git diff --staged
!`git diff --staged`

## Critérios

1. **Stage completo e limpo** (pelo `git status --porcelain` e pelo item marcado na fila)
   - arquivo do item não rastreado (`??`) ou com mudança fora do stage → NAO PODE COMMITAR
   - arquivo alheio ao item no stage → NAO PODE COMMITAR
   - `.env`, `__pycache__`, `*.db`, `*.log`, `outputs/` ou `mutants/` no stage → NAO PODE COMMITAR
2. **Código e testes**, arquivo por arquivo:
   - Bug lógico ou regressão?
   - Fórmula financeira correta economicamente?
   - Teste cobre o caso novo?
   - Segredo ou dado sensível acidental, incluindo dados da carteira do Marcos?
   - Linguagem sugere recomendação de investimento?
3. **Diário e fila contra o diff**
   - O stage traz a seção nova do item em `docs/loop/diario.md` e o `[x]` dele em `docs/loop/fila.md`, e nada de outro item
   - Cada afirmação do diário bate com o diff: arquivos, o que foi feito, testes antes → depois coerentes com os testes do diff, resíduos
   - Diário que descreve algo ausente do diff, ou que omite mudança relevante presente nele → NAO PODE COMMITAR
   - Nenhum dado da carteira no diário
4. Não altere arquivos

Saída:
- Veredito: PODE COMMITAR / NAO PODE COMMITAR
- Problemas críticos
- Problemas médios
- Divergências entre diário e diff
- Mensagem de commit sugerida (Conventional Commits)
