---
name: review-diff-leve
description: Revisa o stage de itens docs e levantamento — mesma checklist do review-diff, com o agente revisor-leve (Sonnet, somente leitura). Os demais tipos usam o review-diff.
context: fork
agent: revisor-leve
allowed-tools: Bash(git status *), Bash(git diff *)
---

Revise o stage com foco em: $ARGUMENTS

Pré-condição: o item já está no stage (passo 8 de `docs/loop/protocolo.md`): código,
`docs/loop/diario.md` e `docs/loop/fila.md` juntos. Você não tem Bash; o estado do
repositório vem injetado abaixo. O item é a linha alterada de `docs/loop/fila.md` dentro do
diff; não abra a fila nem o diário (leitura por trecho, protocolo). Use Read, Grep e Glob
só para ler o código ao redor.

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
