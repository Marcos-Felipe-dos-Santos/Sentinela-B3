# Ciclo de fase e roteiro até o fim do projeto

**Status:** em vigor desde 18/10/2026. Substitui o texto da seção 7 do `docs/PLANO.md`, que agora aponta para cá.
**Base:** o que funcionou na Fase 2A: ADR-0003, auditoria por duas famílias de modelo, todo bug virando teste, ai-memory. As ferramentas estão em `docs/loop/workflow-multiagente.md`; este arquivo diz **a ordem** e **os comandos**.

## 1. As oito etapas de uma fase

| # | Etapa | Quem faz | Sai daqui | Só passa quando |
|---|---|---|---|---|
| 1 | Proposta | loop (item `levantamento` da fase anterior) | `docs/loop/fila-faseN-proposta.md` | o item está commitado |
| 2 | Revisão da proposta | Codex (DOCUMENTO), Claude no chat (consolida e prepara as decisões), Marcos | proposta corrigida, com as `[DECISÃO]` de ativação respondidas por escrito | auditoria "pode seguir" ou "pode seguir com ressalvas" |
| 3 | Ativação | Marcos | branch `v2/fase-N`, `docs/loop/fila.md`, "Fase atual" do `AGENTS.md` | commit `chore: activate phase N queue` |
| 4 | Execução | loop: Claude Code; Codex quando a cota do Claude acaba | um commit por item, diário | itens antes do `[DECISÃO]` em `[x]`, ou parada em `[!]` |
| 5 | Fichas do meio da fase | loop escreve, Codex audita (FICHA), Gemini desempata, Marcos aprova | `docs/metodologia/<lente>.md` aprovada | ficha "aprovada" e o marcador do `[DECISÃO]` trocado por `[x]` |
| 6 | Auditoria da fase | Codex (FASE) e Gemini 4 Argon no app (FASE, pelo pacote de texto) | `docs/loop/historico/fase-N/auditoria-externa.md` | todo bug confirmado virou teste (seção 4); bloqueios corrigidos ou dispensados por escrito |
| 7 | Fechamento | loop (fila de fechamento, se houver), Codex (auditoria rápida), Marcos | PR, merge commit, tag `v2-fase-N` | CI verde no PR |
| 8 | Retro de 15 minutos | Marcos e Claude no chat | ajuste numa skill, no protocolo ou neste arquivo | o ajuste está commitado |

## 2. Etapa por etapa

Nos comandos, `N` é a fase em minúsculas (`2b`, `2c`, `3`...). Todos rodam na raiz do repositório, no WSL, com a venv ativa (`source venv/bin/activate`). O `scripts/auditar.py` preenche os prompts de `docs/loop/prompts/` com a fase, a tag-base e o histórico certos, e grava a saída na pasta Downloads do Windows (ou em `outputs/auditorias/`, se ela não existir). Rodada repetida não sobrescreve: ganha `-2`, `-3`. Para só ver o prompt: `python scripts/auditar.py prompt <modo> --fase N ...`.

### Etapa 1. Proposta
Já vem pronta: o penúltimo item de cada fila é o `levantamento` que propõe a próxima.

### Etapa 2. Revisão da proposta
```bash
python scripts/auditar.py codex documento --fase N --arquivo docs/loop/fila-faseN-proposta.md
```
1. Mande o `...-relatorio.md` e a proposta ao Claude no chat. Ele confere cada achado e traz cada `[DECISÃO]` com as opções, os dados e a opção que ele escolheria, com o motivo.
2. Você decide. A proposta corrigida entra por commit seu, na `main`.
3. Decisão de método (taxa, janela, limiar, fórmula) nunca fica no texto da proposta: vira `[DECISÃO]` sua ou vai para uma ficha.
4. Se a proposta mudou muito, rode o Codex de novo com `--foco "o que mudou desde a rodada anterior: ..."`.

### Etapa 3. Ativação
```bash
git switch main && git pull && git status --short
git switch -c v2/fase-N
git mv -f docs/loop/fila-faseN-proposta.md docs/loop/fila.md
# edite à mão a seção "Fase atual" do AGENTS.md com o texto que a proposta traz
git add docs/loop/fila.md AGENTS.md
git commit -m "chore: activate phase N queue"
```

### Etapa 4. Execução
```bash
tmux attach -t loop || tmux new -s loop
ai-memory run claude
```
No Claude Code: `/retomar` e depois o `/goal` (seção 6).
- **A cota do Claude acabou:** `ai-memory run codex`, `$retomar`, `$executar-fila`. Ao sair do Codex, `ai-memory finalize-session`. Nunca dois executores ao mesmo tempo (workflow, seção 5).
- **Parou em `[!]` ou com três reprovações:** mande o trecho do diário ao Claude no chat. A sua decisão vira texto na fila, por commit seu, e o loop retoma.
- **"Para o Marcos revisar" no diário:** leia no fim de cada sessão. Bug confirmado vira teste no mesmo dia (seção 4).
- Até o checkpoint da 2B, anote cada troca de executor em `outputs/piloto-multiagente.md` (workflow, seção 8).

### Etapa 5. Fichas do meio da fase
Lente nova ou versão nova de método só entra com ficha aprovada (ADR-0003, D21).
```bash
python scripts/auditar.py codex ficha --fase N --arquivo docs/metodologia/<lente>.md
```
1. O loop escreve a ficha e para no `[DECISÃO]`.
2. Mande o relatório e a ficha ao Claude no chat; ele traz as perguntas com opções e dados.
3. Se o Codex e o autor da ficha divergirem num ponto de método, o Gemini desempata, sobre o ponto concreto: `python scripts/auditar.py gemini ficha --fase N --arquivo docs/metodologia/<lente>.md --foco "<o ponto>"`.
4. A ficha é corrigida e auditada de novo até "pode seguir"; você marca "aprovada" e troca o marcador por `[x]`.

### Etapa 6. Auditoria da fase
```bash
git push -u origin v2/fase-N
python scripts/auditar.py codex fase --fase N
python scripts/auditar.py gemini fase --fase N
```
1. Confira o CI do branch na aba **Actions** do GitHub.
2. Codex: o relatório sai em `auditoria-fase-N-codex-relatorio.md`.
3. Gemini 4 Argon, no app: anexe os `parte-NN.md` e o `git.md` da pasta `gemini-fase-N` (o script diz quantos são) e cole o texto do `00-prompt.md`. Se ele parar em "CONTINUA", escreva "continue". Copie a resposta inteira para um `.txt`.
4. Mande os dois relatórios ao Claude no chat. Ele confere cada achado no código e escreve o `auditoria-externa.md` da fase, com a lista de bugs.
5. Você decide (D30): bloqueio que a própria fase criou é corrigido numa fila de fechamento; o resto vira xfail estrito com o item de destino na proposta da próxima fase (é a dispensa por escrito).

Itens que o Codex executou (`Executor: codex` no corpo do commit) não são auditados por ele (D30): abra uma sessão nova do Claude Code em modo plano (só leitura) e cole o prompt de `python scripts/auditar.py prompt fase --fase N --foco "só os commits com Executor: codex no corpo"`. Sem cota no Codex: `agy` na cópia descartável (workflow, etapa 4).

### Etapa 7. Fechamento
1. Fila de fechamento, se houver: o primeiro item registra os bugs em `tests/regressao/`, os seguintes corrigem, o último acrescenta o fechamento ao `pr-fase-N.md` e arquiva a fila.
2. Auditoria rápida, só da fila de fechamento (`<commit>` é o anterior ao primeiro item dela):
   ```bash
   python scripts/auditar.py codex fechamento --fase N --desde <commit>
   ```
3. Push, CI verde e PR pelo navegador, com `docs/loop/historico/fase-N/pr-fase-N.md` como descrição:
   `https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/compare/main...v2/fase-N?expand=1`
4. Merge com **Create a merge commit**. Depois:
   ```bash
   git switch main && git pull
   git tag v2-fase-N && git push origin v2-fase-N
   git branch -d v2/fase-N && git push origin --delete v2/fase-N
   ```
5. Passos de operação que o `[DECISÃO]` da fase pedir (limpar cache, apagar arquivos à mão) e a "Fase atual" do `AGENTS.md`.

### Etapa 8. Retro
Três perguntas, com o Claude no chat: o que travou o loop? que achado da auditoria um teste ou uma skill teria pegado antes? o piloto multiagente ajudou? Cada resposta vira mudança numa skill, no protocolo ou neste arquivo, no mesmo dia.

## 3. Ferramentas e cotas

| Ferramenta | Usa para | Para poupar cota |
|---|---|---|
| Claude Code | executar a fila | modelos por papel: `docs/PLANO.md`, seção 9 |
| Claude no chat | conferir auditorias, preparar decisões, montar pacotes | mande arquivos, não colagens longas |
| Codex | auditar em todas as etapas; executar quando o Claude esgota | `scripts/auditar.py codex` roda em sandbox só de leitura |
| Gemini 4 Argon, no app (Google AI Pro) | auditoria da fase; desempate em ficha | só pelo pacote de texto: o app corta anexos acima de ~450 KB e não lê o zip do GitHub. Sem gasto além do plano: nada de API |
| Antigravity (`agy`) | auditor de reserva | cópia descartável do repositório |
| Jules | tarefas triviais de um arquivo (D31) | — |

## 4. Bugs e regressão

A regra completa e o registro estão em `tests/regressao/README.md`. No ciclo:
1. bug confirmado (auditoria, revisão ou uso) vira teste em `tests/regressao/` no mesmo dia, antes de qualquer correção;
2. enquanto não é corrigido: `xfail(strict=True, reason="BUG-<fase>-NN · <sintoma> · corrige: <item>")`;
3. a correção retira a marca, o teste fica para sempre e o registro diz "corrigido";
4. nenhum `fix:` fecha sem o teste do bug que corrige;
5. toda proposta de fila dá um item a cada bug aberto com destino nela.

## 5. Regras de ouro

- Uma fila, um executor por vez, um commit por item.
- Auditor de família diferente da do executor (D30).
- Decisão de método é sua, por escrito, antes do código (D21, D23).
- Memória é pista; fila, diário, ADRs e git mandam.
- Nada da carteira em arquivo versionado nem em prompt.
- Push só no `[DECISÃO]` da fase; PR só com CI verde e auditoria fechada.

## 6. O `/goal`

```
/goal Todos os itens de docs/loop/fila.md antes da linha [DECISÃO] estão marcados [x], ou algum item está [!] com o motivo registrado em docs/loop/diario.md. Leia e siga docs/loop/protocolo.md à risca. Nunca faça git push nem abra PR. Ao fechar cada item, rode cat docs/loop/fila.md e git log --oneline -3.
```

## 7. Roteiro até o fim

As datas ficam no `docs/PLANO.md`, seção 12. Esta tabela traz o que cada fase entrega, o que depende de você e a duração estimada pelo ritmo real da 2A: 69 commits de 5 a 15/10/2026, auditorias e fechamento incluídos. Cada checkpoint revê a estimativa.

| Fase | Entrega | Decisões suas | Duração estimada |
|---|---|---|---|
| **2B** | taxa real (NTN-B + prêmio); Gordon, Bazin e FII no mesmo regime; lente de bancos; `applies_to`; liquidez; BTG; os bugs abertos da 2A | para ativar: [SEÇÃO A], [LIQUIDEZ], [FICHA 1.1] e [AUDITORIA] (decididas em 18/10/2026). No meio: [TAXA] (com o g real do Gordon e dos bancos), [BAZIN], [FII], [BANCOS], [FINANCEIRAS], [BTG], [CACHE] e o destino dos bugs do levantamento | 2 a 3 semanas |
| **2C** | fundamentos normalizados, lente de qualidade, histerese, vocabulário, lentes no lugar de "valor justo", setores, fim do Markowitz | janelas por método (D25); decisões A a D da auditoria da 2A; histerese | 2 a 3 semanas |
| **3** | tempo como entrada: `as_of`, SQLite único com migrações, ponto no tempo, universo com deslistadas, backtest real | universo, profundidade, reapresentações, histórico estrito (D17, D32); backup restaurável antes da primeira migração (D29) | 3 a 4 semanas |
| **4** | operação diária: CLI, job de fechamento, agendamento, rastreabilidade v1, backup, camada de risco | canal do resumo diário, limites de concentração | 2 semanas de código e **14 dias corridos** sem falha silenciosa (gate) |
| **5** | notícias medidas: coletor do IPE e estudo de evento | janelas e referência do estudo; go ou no-go dos estágios 2 a 4 | 2 semanas |
| **6** | vitrine: varredura final, README, página de metodologia, CHANGELOG | — | 1 semana: **núcleo pronto** |
| 7 | interface FastAPI + HTMX, fim do Streamlit | — | 3 a 4 semanas |
| 8 | IA nas telas, só com o go do F5-3 | go ou no-go | — |

Somando as durações a partir de hoje, o núcleo (até a Fase 6) fecha entre o fim de fevereiro e março de 2027, dentro da linha de corte do PLANO. O caminho crítico não é o código: são as suas decisões de método (2B, 2C e 3) e o gate de calendário da Fase 4.

## 8. Próximos passos (Fase 2B)

As decisões de ativação foram tomadas em 18/10/2026, e a proposta foi revisada com a auditoria da 2A (`docs/loop/fila-fase2b-proposta.md`). Falta:
1. **Restos do `[DECISÃO]` da 2A:** `python scripts/invalidar_cache_cvm.py <tickers>` (primeiro sem `--aplicar`), apagar à mão os caches listados no F2A-13 e os `outputs/f2a41_*.json`, e trocar a "Fase atual" do `AGENTS.md` (2A concluída; 2B em revisão).
2. **Auditorias da revisão** (etapas 2 e 5):
   ```bash
   python scripts/auditar.py codex ficha --fase 2b --arquivo docs/metodologia/por-acao.md --foco "a versão 1.1: seções 7.7 a 7.10 e as mudanças nas seções 2 e 4; refaça por conta própria as contas que elas citam"
   python scripts/auditar.py codex documento --fase 2b --arquivo docs/loop/fila-fase2b-proposta.md
   ```
3. **Correções** que você aceitar dos dois relatórios (o Claude no chat consolida) e a ficha marcada "aprovada" na versão 1.1.
4. **Ativar** (etapa 3) e rodar.
