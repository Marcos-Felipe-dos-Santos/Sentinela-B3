# Diário — Fase 4 (blocos 0 e 1)

Fila ativa: `docs/loop/fila.md`. Protocolo: `docs/loop/protocolo.md`. Decisões: `docs/decisoes/decisoes-fase4.md`. A fila e o diário do checkpoint da Fase 3 foram arquivados na ativação em `docs/loop/historico/fase-3/fila-checkpoint.md` e `diario-checkpoint.md`.

### ATIVACAO — chore: activate phase 4 queue
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** ativação dos blocos 0 e 1 pela decisão do Marcos de 24/11/2026, depois da segunda rodada da auditoria DOCUMENTO do Codex (`docs/loop/auditorias/documento-fase4-codex-2.md`, commit `bcb4139`). `git mv` da proposta para `docs/loop/fila.md`; a fila e o diário do checkpoint da Fase 3 (o `[DECISÃO]` dele foi resolvido pelo merge do PR #28 e pela tag `v2-fase-3`) arquivados em `docs/loop/historico/fase-3/`; a "Fase atual" do `AGENTS.md`, escrita pelo Marcos, entra neste commit sem edição do loop; o "Estado da fase", a contagem da suíte e a lista "Fases" (2C e 3 fechadas, 4 ativa nos blocos 0 e 1) do `CLAUDE.md` atualizados para a ativação.
- **Baseline reconferida:** branch `v2/fase-4`, `which python` → `venv/bin/python`; suíte 5220 passed, 1 skipped, 24 xfailed (8 do BUG-3-49, 15 do BUG-3-50, 1 do FII do E2E); Ruff CI e Ruff completo em `sentinela/data` e `sentinela/methods` limpos; golden `500645a3263ad25e…` igual ao `HEAD`; `python scripts/fila.py proximo` → F4-A00a.
- **Dificuldades:** a "Fase atual" trava o `database.py` sem exceção (o F4-A11 precisa dele) e não diz se a exceção `logging_config` cobre o bloco do `logging.basicConfig` no `config.py` (o F4-A00a precisa dele). Os dois casos estão escritos na fila, seção "Permissões".
- **Como resolvi:** nenhum código tocado; os dois pontos ficam para o Marcos antes dos itens.
- **Testes:** 5220 passed, 1 skipped, 24 xfailed → igual.
- **Resíduos:** nenhum. `stash@{0}` antigo (F3-2a-fix) segue guardado.
- **Decisões que ficaram para o Marcos:** exceção escrita para o `database.py` no F4-A11; confirmação de que a exceção `logging_config` cobre o `basicConfig` do `config.py` no F4-A00a.
- **Para o Marcos revisar:** a fila ativa (bloco 0 com 23 itens até o primeiro `[DECISÃO]`).

### F4-A00a — fix: write the application log outside the repository with rotation
- **Executor:** codex (GPT-6)
- **Status:** sucesso
- **O que foi feito:** `config.py` delega a configuração do logger raiz a `logging_config.py`. O padrão é `~/.local/state/sentinela-b3/sentinela.log`, com diretório configurável por `SENTINELA_LOG_DIR`, criação automática e abertura no primeiro registro. O handler retém três backups de 10 MiB; formato, nível INFO e saída no console foram preservados. As duas exceções autorizadas em 24/11 constam no adendo e na fila, com o `AGENTS.md` do Marcos incluído como recebido.
- **Dificuldades:** o módulo novo estava fora de `source_paths` do mutmut. A sonda por subprocesso verificou o import no gate; as sondas em processo mediram os mutantes.
- **Como resolvi:** foco local do mutmut em `logging_config.py` por `outputs/F4-A00a/mutar.py`, reaproveitando a configuração do projeto. Revisão de entrada: DD-23 contestada e encerrada antes desta sessão por acordo na DD-29; DD-89 contestada no checkpoint da Fase 3 e resolvida pela decisão 51 (BUG-3-59), com desfecho vinculado em pendências; DD-90 conferida conforme a regra de identidade ratificada no checkpoint da Fase 3.
- **Testes:** baseline de ativação 5220 passed, 1 skipped, 24 xfailed. BUG-4-01 reproduzido com xfail estrito em `outputs/F4-A00a/regressao-antes.txt`, seguido de PASS. Gate final 5224 passed, 1 skipped, 24 xfailed, Ruff CI e Ruff completo do gate limpos, golden `500645a3263ad25e…` intacto. Mutmut 56/60, 93,3%, em `outputs/F4-A00a/mutacao-r3.txt`. Busca em produção por `FileHandler` e arquivos `.log` encontrou a configuração rotativa.
- **Resíduos:** evidências locais em `outputs/F4-A00a/` e cache do mutmut em `mutants/`.
- **Decisão delegada:** decisão delegada DD-91: aplicação do aceite de log externo ao caminho configurável → resolver o caminho antes de criar a pasta e recusar destino dentro da raiz do repositório (classe 4, desempate 6; alternativas: aceitar o destino informado, que permitiria log no repositório, ou voltar em silêncio ao padrão).
- **Decisões que ficaram para o Marcos:** nenhuma sobre o item. Para negar a leitura, adicionar em `.claude/settings.json`, dentro de `permissions.deny`, a entrada `"Read(//home/marcos/.local/state/sentinela-b3/**)"`. No Codex gerenciado, adicionar em `requirements.toml` a seção `[permissions.filesystem]` com `deny_read = ["/home/marcos/.local/state/sentinela-b3"]` ou incluir o caminho na lista já existente. Se usar `SENTINELA_LOG_DIR`, aplicar as duas entradas ao diretório absoluto efetivo.
- **Para o Marcos revisar:** negação de leitura no perfil que executa cada agente.
