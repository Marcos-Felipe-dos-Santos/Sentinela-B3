# Workflow multiagente: Claude Code, Codex e Gemini

**Status:** proposto em 14/10/2026. Vale quando o Marcos fizer o commit deste arquivo junto com a revisão da D30 (ADR-0003, "Revisões").
**Inspiração:** o fluxo de Fabio Akita (Akita's AI Lair, `ai-memory`, `my-skills`), adaptado às regras do Sentinela: fila única, rito `fix` com PASS, golden, fichas metodológicas e auditoria externa.

## 1. Princípios

1. **Uma fila.** `docs/loop/fila.md` é a única lista de trabalho. Nenhuma ferramenta tem plano próprio.
2. **Um executor por item.** Nunca dois agentes escrevendo ao mesmo tempo. A troca acontece num ponto controlado, com passagem.
3. **Evidência acima de narrativa.** "Feito" é diff, testes e aceite conferidos, não o relato do agente (`docs/loop/auditoria-externa.md`).
4. **Auditor de outra família.** Quem audita um item nunca é da mesma família de modelo que o executou (ADR-0003, D30).
5. **Memória é pista, não autoridade.** O `ai-memory` ajuda a retomar. Fila, diário, ADRs e o git sempre prevalecem.
6. **Comece simples.** Cada ferramenta entra numa etapa própria, com um teste de que funcionou. Ferramenta que não ajudar no piloto sai.

## 2. Papéis

| Ferramenta | Assinatura | Papel principal | Papel de reserva | Não faz |
|---|---|---|---|---|
| **Claude Code** (Opus 5.5) | Claude Pro | executor do loop (`/goal`) | auditor dos itens executados pelo Codex | auditar o próprio trabalho no checkpoint |
| **Codex CLI** | ChatGPT Plus | auditor externo (modos FASE, PR, DOCUMENTO, FICHA) | executor quando a cota do Claude acaba | auditar item que ele mesmo executou |
| **Gemini 4 Argon, no app do Gemini** | Google AI Pro | pesquisa (CPC, manuais da CVM, layout da B3) e segunda opinião em fichas metodológicas | desempate quando Claude e Codex divergem | escrever no repositório (o app não tem acesso a ele) |
| **Antigravity CLI** (`agy`) | Google AI Pro | terceiro auditor, quando Codex executou e o Claude está sem cota | — | executar itens da fila (fica para depois do piloto) |
| **Jules** | Google AI Pro | tickets triviais com especificação completa e arquivo único (D31) | — | cálculo, valores de referência numéricos |

Sobre o Gemini 4 Argon (conferido em 14/10/2026):
- no plano Pro, está disponível **só no app do Gemini** (e no AI Mode da busca);
- no Antigravity (desktop e CLI), o Argon exige o **AI Ultra**. Com o Pro, o `agy` usa os modelos que o plano liberar: confira com `agy models`;
- o Gemini CLI deixou de atender contas Pro em 18/6/2026. O substituto é o Antigravity CLI.

## 3. O que cada ferramenta lê

| Arquivo | Claude Code | Codex | Antigravity CLI |
|---|---|---|---|
| `AGENTS.md` | via `CLAUDE.md` | sim, sozinho | sim, sozinho |
| `CLAUDE.md` | sim, sozinho | não | não |
| `.claude/skills/<nome>/SKILL.md` | sim (`/nome`) | não | não |
| `.agents/skills/<nome>/SKILL.md` | por link simbólico em `.claude/skills/` | sim (`$nome`) | lê o arquivo quando o pedido citar o nome |
| memória do `ai-memory` | hooks e MCP | hooks e MCP (sem hook de fim de sessão) | MCP, se o `ai-memory setup` detectar |

Skills compartilhadas, em `.agents/skills/` (versionadas):
- **`retomar`**: abre uma sessão de trabalho já começado. Lê fila, diário, passagem e git; classifica o estado; só então age.
- **`passagem`**: registra, antes de sair, o que foi feito, o que falta e o que está pela metade, em `outputs/passagem.md` (fora do git).
- **`verificar-entrega`**: confere um item, commit ou PR contra o aceite, somente leitura. É o modo ITEM da auditoria externa.
- **`executar-fila`**: o loop para quem não é o Claude Code. Segue o `protocolo.md` e traduz `/review-diff` e `/safe-commit` para o CLI em uso.

As skills do Claude (`/review-diff`, `/safe-commit`) continuam onde estão; a `executar-fila` manda os outros agentes lerem e seguirem esses mesmos arquivos.

## 4. Montagem, etapa por etapa

Faça uma etapa por vez. Cada uma termina com um teste. Se o teste falhar, pare e mande a saída.

### Etapa 0. Estado do repositório

```bash
cd ~/projetos/Sentinela_B3
git --no-pager log --oneline -6
git status --short
grep -c "^- \[!\]" docs/loop/fila.md
```
- O `grep` tem que dar **0**. Se der 1, aplique antes o `adiar_f2a39.py` (o bloqueio do F2A-39).
- O `git status` tem que estar vazio, ou só com o que você sabe explicar.

### Etapa 1. Regras e skills no repositório

O pacote traz este arquivo, as quatro skills e o script `instalar_multiagente.py`, que:
- cria os links `.claude/skills/<nome>` → `.agents/skills/<nome>`;
- acrescenta a seção "Multiagente" ao fim do `AGENTS.md` e um ponteiro no `CLAUDE.md`;
- acrescenta a seção "Troca de executor" ao `protocolo.md`;
- registra a revisão da D30 no ADR-0003.

```bash
python3 -m zipfile -e /mnt/c/Users/marcos/Downloads/sentinela-multiagente.zip .
python3 instalar_multiagente.py && rm instalar_multiagente.py
git status --short
```
**Teste:** abra o Claude Code e digite `/`: `retomar`, `passagem`, `verificar-entrega` e `executar-fila` aparecem na lista. No Codex, `/skills` lista as quatro.

Commit (é a sua aprovação do workflow e da revisão da D30):
```bash
git add AGENTS.md CLAUDE.md docs/loop/protocolo.md docs/adr/0003-validade-dados-metodo-auditoria.md docs/loop/workflow-multiagente.md .agents/skills .claude/skills
git commit -m "docs: add multi-agent workflow, shared skills and per-item auditor rule"
```
Se o `git add` reclamar de `.claude/skills` ignorado pelo `.gitignore`, tire esse caminho do comando: os links ficam só na sua máquina, o que basta.

### Etapa 2. ai-memory (piloto)

```bash
curl -fsSL https://github.com/akitaonrails/ai-memory/releases/latest/download/install.sh | sh
ai-memory --version
ai-memory setup
ai-memory install-hooks --capture-mode allowlist --apply
git status --short
```
**Pare** se o `git status` mostrar arquivo do repositório alterado pelo instalador.

Marcador do projeto, fora do git (o repositório é público):
```bash
cat > .ai-memory.toml <<'EOF'
workspace = "marcos"
project = "sentinela-b3"
drop_subagent_captures = "true"

[capture]
ignore_paths = ["outputs/**", "data/**", "mutants/**", ".env"]
EOF
echo ".ai-memory.toml" >> .git/info/exclude
git status --short
```
**Teste:** o `git status` não mostra o `.ai-memory.toml`. Depois, `ai-memory run claude`, uma pergunta qualquer, sair, e `ai-memory run codex` perguntando "onde a gente parou?": a resposta cita a sessão anterior.

Regras de uso:
- o `ignore_paths` filtra arquivos lidos pelo agente, **não o texto que você digita**: nunca cole a carteira em prompt deste projeto;
- a memória fica em `~/.local/share/ai-memory` (ou o diretório que o `setup` indicar), fora do repositório;
- no Codex, ao terminar uma sessão, rode `ai-memory finalize-session` (ele não tem hook de fim de sessão);
- nunca use `--yolo`.

### Etapa 3. Codex como executor de reserva

O Codex já está instalado (nvm no WSL). Confira o login pela assinatura, não por chave de API:
```bash
codex --version
codex login
```
Escolha entrar com a conta do ChatGPT.

Perfil de executor em `~/.codex/config.toml` (acrescente ao fim; a auditoria continua usando `--sandbox read-only` explicitamente):
```toml
[profiles.executor]
sandbox_mode = "workspace-write"
approval_policy = "on-request"
```
- `workspace-write` deixa o Codex escrever só no repositório, sem rede. Item que precisar baixar dado da CVM ou da B3 vai parar: nesse caso, rode esse item com o Claude, ou libere a rede só para ele.
- `on-request` faz o Codex pedir sua aprovação quando quiser sair da sandbox. Para rodar sem você, troque por `"never"` depois que o piloto der certo.

**Teste (piloto da troca):** com o loop do Claude rodando um item, interrompa com `Esc` (simulando a cota esgotada). Abra outra janela do tmux:
```bash
ai-memory run codex
```
Se o `ai-memory run` não aceitar o perfil, use `codex --profile executor` direto. Dentro do Codex:
```
$retomar
```
Confira se o bloco "Retomada" acerta o item, o que já estava feito e o que falta. Depois:
```
$executar-fila
```

### Etapa 4. Gemini: Antigravity CLI e app

```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
agy --version
agy
```
No primeiro `agy`, faça o login com a conta do Google AI Pro. Depois:
```bash
agy models
```
Anote no diário qual modelo o Pro libera (o Argon não deve aparecer).

O `agy` não tem modo somente leitura documentado. Como auditor, ele roda numa **cópia descartável** do repositório:
```bash
git worktree add --detach /tmp/sentinela-auditoria HEAD
cd /tmp/sentinela-auditoria
agy -p "Leia docs/loop/auditoria-externa.md e siga-o no modo <MODO> sobre <escopo>. Não edite arquivos." > ~/auditoria-agy.txt 2>&1
cd ~/projetos/Sentinela_B3
git worktree remove --force /tmp/sentinela-auditoria
cp ~/auditoria-agy.txt /mnt/c/Users/marcos/Downloads/
```
A cópia não tem `data/` (fora do git). Se a auditoria precisar recalcular com os arquivos da CVM, copie só os arquivos necessários para dentro dela.

**App do Gemini (Argon):** não acessa o repositório. Anexe os arquivos (a ficha, o trecho do diário, o CSV recortado) e faça uma pergunta específica. A resposta entra no histórico como "segunda opinião (Gemini 4 Argon, app)", nunca direto numa decisão.

### Etapa 5 (opcional). Painel de cotas: ai-usagebar

Mostra, numa janela do terminal, quanto resta da cota do Claude, do Codex e do Antigravity, e quando renova. Lê as credenciais dos CLIs por endpoints não documentados: pode quebrar numa atualização dos fornecedores.
```bash
curl https://sh.rustup.rs -sSf | sh
source ~/.cargo/env
cargo install ai-usagebar
ai-usagebar-tui
```
Deixe numa janela própria do tmux.

### Etapa 6 (depois do piloto). ai-jail

Isola o agente: o projeto fica gravável, mas `~/.ssh`, outros projetos e tokens do shell ficam fora; a rede fica fechada, exceto a API do agente. Não protege o `.env` de dentro do projeto (essa proteção continua sendo a regra de negação do Claude Code). Só vale a pena quando o loop rodar sem você por muitas horas. Para os itens que baixam dados, a rede precisa ser liberada por host (`--allow-host dados.cvm.gov.br` e o host do COTAHIST da B3). Teste com `ai-jail ai-memory run claude` num item de documentação antes de usar num item de código.

### Fica de fora

- **ghpending:** lista PRs e issues de vários repositórios. Com um repositório só, `gh pr list` resolve.
- **tclock:** relógio de terminal. Não muda nada no fluxo.
- **Copiar as skills do `my-skills`:** o próprio Akita avisa que são dele. As nossas quatro skills seguem a ideia (procedimento repetido, tirado de erro real), com as regras do Sentinela.

## 5. Rotina diária

**Janelas do tmux (sessão `loop`):** 0 = executor; 1 = shell (git, auditorias); 2 = `ai-usagebar-tui`, se instalado.

### Começo do dia
```bash
tmux attach -t loop || tmux new -s loop
cd ~/projetos/Sentinela_B3 && git status --short
ai-memory run claude
```
No Claude Code: `/retomar`, conferir o bloco "Retomada" e então o `/goal` de sempre.

### A cota do Claude acabou
1. Não abra outro executor enquanto o Claude ainda estiver escrevendo.
2. Na janela 1: `ai-memory run codex` (ou `codex --profile executor`).
3. `$retomar`. Leia o bloco "Retomada". Se o item pela metade não fizer sentido, peça para o Codex guardar com `git stash push -u -m "wip <item>"` e recomeçar o item.
4. `$executar-fila`.

### A cota do Claude voltou
1. Deixe o Codex terminar o item em andamento (ou pedir `$passagem` e parar).
2. Saia do Codex e rode `ai-memory finalize-session`.
3. `ai-memory run claude`, `/retomar`, `/goal`.

### O loop parou (`[!]`, `[DECISÃO]` ou três reprovações)
Igual a hoje: você lê o diário, decide, e as mudanças de documento entram por commit seu.

### Fim do dia
Se o executor estiver no meio de um item e você for desligar o PC: peça `/passagem` (Claude) ou `$passagem` (Codex) antes de fechar.

## 6. Passagem de trabalho

Formato de `outputs/passagem.md` (a skill `passagem` escreve; a `retomar` lê):

```
## Passagem — <data e hora> — <executor que sai>
- Item: F2A-xx · <título>
- Branch e commit-base: <branch> @ <hash>
- Rodada de revisão: <0 a 3>
- Feito: <o que já está no diretório de trabalho>
- Arquivos alterados (não commitados): <lista>
- Verificações rodadas e resultado: <pytest, ruff, mutmut, golden>
- Falta: <próximos passos>
- Tentativas que falharam: <o que não funcionou e por quê>
- Decisões do Marcos pendentes: <lista ou "nenhuma">
```

## 7. Revisão e auditoria

| Quem executou o item | Revisão do item (protocolo, até 3 rodadas) | Auditoria externa (checkpoint) |
|---|---|---|
| Claude Code | `/review-diff` (subagentes do Claude) | Codex |
| Codex | Claude `/review-diff`, se houver cota; senão sessão nova do Codex, somente leitura | Claude Code; sem cota, `agy` na cópia descartável |

- O diário registra `**Executor:**` em cada item, e o commit leva `Executor: <ferramenta>` no corpo. É assim que o checkpoint sabe quem audita o quê.
- Fichas metodológicas: auditoria FICHA pelo Codex (ou pelo Claude, se o Codex escreveu a ficha). Se o auditor e o autor divergirem num ponto de método, o Gemini 4 Argon dá a segunda opinião no app, sobre a divergência concreta, não sobre a ficha inteira.

## 8. Piloto

Duas semanas, ou até o checkpoint da 2A, o que vier primeiro. Anote em `outputs/piloto-multiagente.md` (fora do git), a cada troca de executor:
- quanto tempo até o novo agente fazer a primeira ação útil;
- quantas vezes você precisou recontar contexto;
- se o bloco "Retomada" acertou o item e o estado;
- divergências entre memória e git.

No checkpoint da 2A, decida: manter o `ai-memory`, manter só a passagem por arquivo, ou ajustar as skills.

## 9. O que não fazer

- Dois executores no mesmo item, ou ao mesmo tempo no mesmo branch.
- Auditor da mesma família no checkpoint.
- `--yolo`, `--dangerously-skip-permissions` ou `approval_policy = "never"` antes do piloto dar certo.
- Jules em item de cálculo ou com valor de referência numérico.
- Colar dado da carteira em qualquer prompt deste projeto.
- Tratar uma resposta da memória como decisão: decisão está em ADR, ficha ou fila.

## 10. Kaizen

Toda falha de processo vira mudança numa skill, no protocolo ou neste arquivo, no mesmo dia, por commit seu. É a parte do método do Akita que mais rende: "cada linha dessas skills é cicatriz".

## Fontes

- ai-memory: https://github.com/akitaonrails/ai-memory e https://aimemory.sh/pt-br/
- Akita's AI Lair (ferramentas e fluxo): https://ailair.akitaonrails.com/pt-br
- Skills do Akita: https://akitaonrails.com/2026/09/17/falando-um-pouco-sobre-minhas-skills-de-ia/
- Combinar modelos no mesmo projeto: https://akitaonrails.com/2026/04/18/llm-benchmarks-parte-2-multiplos-modelos/
- ai-jail: https://aijail.io/pt-br/
- ai-usagebar: https://github.com/akitaonrails/ai-usagebar
- Skills no Codex: https://learn.chatgpt.com/docs/build-skills
- Gemini CLI → Antigravity CLI: https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/
- Antigravity CLI, modo headless: https://antigravity.google/docs/cli/headless
- Gemini 4 Argon no app: https://blog.google/innovation-and-ai/products/gemini-app/gemini-4-argon-availability/ e https://9to5google.com/2026/10/13/gemini-app-4-argon/
