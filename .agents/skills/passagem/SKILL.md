---
name: passagem
description: Use antes de encerrar uma sessão do Sentinela B3 com trabalho não concluído, quando a cota estiver acabando, quando o Marcos for desligar o PC ou pedir para trocar de agente. Não use para fechar item concluído (isso é o diário e o commit do protocolo).
---

# Passagem

Objetivo: o próximo agente (ou você amanhã) retoma sem o Marcos recontar nada.

## 1. Conferir

```bash
git branch --show-current
git --no-pager log --oneline -3
git status --short
git check-ignore outputs/passagem.md
```
O último comando precisa imprimir o caminho (o arquivo fica fora do git). Se não imprimir, pare e avise o Marcos.

## 2. Escrever `outputs/passagem.md`

Acrescente no **topo** do arquivo (as passagens antigas ficam abaixo):

```
## Passagem — <data e hora> — <executor que sai: claude-code | codex | antigravity>
- Item: F2A-xx · <título>
- Branch e commit-base: <branch> @ <hash>
- Rodada de revisão: <0 a 3>
- Feito: <o que já está no diretório de trabalho>
- Arquivos alterados (não commitados): <lista do git status>
- Verificações rodadas e resultado: <pytest, ruff, mutmut, golden — com números>
- Falta: <próximos passos, na ordem>
- Tentativas que falharam: <o que não funcionou e por quê>
- Decisões do Marcos pendentes: <lista ou "nenhuma">
```

Só fatos verificáveis. Número sem comando que o produziu vai como "não verificado".

## 3. Memória

Se a ferramenta de handoff do `ai-memory` estiver disponível nesta sessão (MCP), registre nela o mesmo conteúdo. No Codex, lembre o Marcos de rodar `ai-memory finalize-session` ao sair.

## Nunca

- Commitar trabalho pela metade para "salvar": o commit do protocolo fecha um item inteiro.
- Colocar dado da carteira, conteúdo do `.env` ou token na passagem.
