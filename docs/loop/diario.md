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

### F4-A00 — test: run today's analysis end to end through the real market engine
- **Executor:** codex (GPT-6)
- **Status:** sucesso
- **O que foi feito:** matriz da análise do dia para ABEV3, TAEE11 e HGLG11, com serviço, cascata, coletores e motores reais. O teste reaproveita o relógio, o índice semeado e os dublês da borda do BUG-3-63. Os provedores reais leem arquivos locais remontados de recortes oficiais de DFP e Informe Mensal. O HTTP reproduz as respostas públicas da B3 para ABEV3 e HGLG11, do Tesouro e da ANBIMA. O contrato do yfinance registra preço, ações em circulação e proventos de TAEE11 com fonte e hash.
- **Dificuldades:** o registro do yfinance da unit não traz a série de fechamentos. O cenário contém uma DFP por companhia e omite o GetDetail da unit e o IPCA do Gordon.
- **Como resolvi:** o dublê do yfinance expõe somente o fechamento registrado e os proventos; a matriz exige os motivos exatos de cada abstenção. A revisão 1 identificou dublês internos dos provedores herdados da regressão. Eles foram substituídos pelos provedores reais com caches semeados e dublês de HTTP e yfinance. As lentes numéricas usam tolerância relativa de 1e-6. O FII com Informe válido e DY ausente na cascata tem um caso em xfail estrito, limitado à abstenção exata do achado 1 (F4-A01).
- **Testes:** módulo e contratos: 32 passed e 1 xfailed. A sonda do carimbo fez os casos da ação e do FII falharem ao repor o relógio da coleta em lugar do instante do clique (`outputs/F4-A00/mutante-carimbo.txt`). Nenhum módulo de produção mudou.
- **Resíduos:** evidência da sonda em `outputs/F4-A00/` e sonda no cache de testes do executor.
- **Decisões que ficaram para o Marcos:** teste manual da R1 no checkpoint.
- **Para o Marcos revisar:** a matriz e o caso em xfail do FII.

### F4-A01 — fix: read the FII yield lens from the CVM report, not the cascade dividend yield
- **Executor:** codex (GPT-6)
- **Status:** sucesso
- **O que foi feito:** na análise corrente, a lente avalia o Informe Mensal mesmo com DY ausente, zero ou inválido na cascata. Quando a lente é elegível, o DY e o DY efetivo da saída vêm das entradas do Informe. O caminho por publicação mantém o DY selecionado por `MotorHistorico._dy_do_informe`. O e2e do F4-A00 passa também com DY ausente na cascata.
- **Dificuldades:** a sonda do logging em subprocesso falhou durante a coleta da primeira mutação, com módulos de apoio instrumentados.
- **Como resolvi:** executei o mutmut 3.8 com a configuração do projeto, dois filhos e só o motor FII instrumentado, mantendo a seleção da suíte e copiando `logging_config.py` como apoio. O candidato do golden foi gerado fora do fixture versionado, com o guardião de rede da suíte, e comparado antes de ser aplicado.
- **Testes:** BUG-4-02, 1 passed e 4 xfailed antes, 7 passed depois, incluindo dois testes de preservação histórica. Regressão, e2e e equivalência em conjunto 15 passed e 1 skipped. Suíte preliminar 5241 passed, 1 skipped, 24 xfailed. Mutmut: 331/371 (89,22%) no módulo e 242/278 (87,05%) na função alterada. Golden atualizado pelo predicado (ii): 32 diferenças nos campos `dy` e `dy_efetivo` de FIIs, zero casos fora do predicado. Novo SHA256 `1103fcadbe3a745d9644c9fb98a9714052d7643132b408bb3f050bc6593d7011`.
- **Resíduos:** evidências em `outputs/F4-A01/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma sobre o item.
- **Para o Marcos revisar:** o DY de saída quando o Informe e a cascata discordam e o predicado aplicado ao golden.

### F4-A02 — fix: map every preferred class ISIN to its species
- **Executor:** codex (GPT-6)
- **Status:** sucesso
- **O que foi feito:** o mapeamento compartilhado reconhece `ACNPC` a `ACNPH` como PNC a PNH, as classes do índice oficial. As regressões passam pelo retorno total com COTAHIST e proventos produzidos pela B3 simulada, pelo fator de desdobramento e pela janela de proventos. A unit `CDAM` fica no F4-D04.
- **Dificuldades:** a primeira coleta do mutmut reaproveitou estatísticas de uma instrumentação de outro módulo.
- **Como resolvi:** limpei o cache local autorizado de mutantes e rodei a coleta completa com apenas o módulo de proventos instrumentado e dois filhos.
- **Testes:** BUG-4-03, 18 xfails estritos antes → 18 passam. Regressões e fatores juntos, 120 passam. Gate preliminar, 5259 passed, 1 skipped, 24 xfailed. Mutmut 941/974 (96,61%), com zero sem associação a testes. Golden `1103fcadbe3a745d…` intacto.
- **Resíduos:** evidências em `outputs/F4-A02/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma sobre o item.
- **Para o Marcos revisar:** os seis códigos complementares da B3 e a distinção entre as classes no retorno.

### F4-A03 — fix: exclude same-day approvals and other issuers' events from the 12-month dividends
- **Executor:** codex (GPT-6)
- **Status:** sucesso
- **O que foi feito:** proventos sem hora aprovados em D ficam fora da janela do Bazin. O filtro de eventos em ações usa a mesma fronteira de aprovação e os ISINs do emissor recebidos no bloco de proventos. Proventos aprovados em D ou depois ficam fora antes de validar os campos e de provar a cobertura temporal e por espécie.
- **Dificuldades:** o teste unitário preexistente afirmava que aprovação em D entrava na janela. A revisão 1 encontrou registros excluídos que ainda podiam causar abstenção ou demonstrar cobertura.
- **Como resolvi:** decisão delegada DD-92: teste unitário preexistente da janela aceitava aprovação no próprio D → conferir D e D+1 excluídos, com D−1 incluído como controle, no mesmo teste (classe 4, desempates 4 e 6; alternativas: mudar apenas o esperado de D ou transferir toda a cobertura ao BUG-4-04).
- **Identidade:** decisão delegada DD-93: evento sem ISIN completo e conjunto de ISINs do emissor conhecido → conservar a abstenção quando o evento ainda pode atingir a janela; excluir por identidade só um ISIN completo ausente do conjunto (classe 3, desempate 1; alternativas: tratar ISIN vazio ou incompleto como alheio, ou exigir ISIN em todo evento). Revisão cruzada pendente.
- **Testes:** BUG-4-04, 2 passed e 4 xfailed estritos antes → 6 passed. Antes da correção da revisão 1, 3 novos xfails estritos → 9 passed no BUG-4-04. Região afetada, e2e e equivalência, 133 passed e 1 skipped. Gate preliminar, 5268 passed, 1 skipped, 24 xfailed, golden `1103fcadbe3a745d…` intacto. Mutmut: 960/1000 (96,00%) no módulo e 193/196, 51/54 e 153/156 nas funções alteradas.
- **Resíduos:** evidências em `outputs/F4-A03/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** ratificação das decisões delegadas no checkpoint.
- **Para o Marcos revisar:** o motivo conservador de abstenção quando a identidade do evento não pode ser resolvida.

### F4-A00b — docs: rewrite the README for phase 4
- **Executor:** codex (GPT-6)
- **Status:** sucesso
- **O que foi feito:** README proposto pelo Marcos atualizado com a ampliação histórica da Fase 4, modo offline, selo do CI, mais de 5.000 testes e auditoria cruzada entre Claude, Codex e Gemini. A cobertura parcial e seus limites são vinculados a `docs/loop/historico/fase-3/pr-fase-3.md`, seção de cobertura por lente, com o recorte da sonda explicitado.
- **Fontes conferidas:** Gordon em `docs/metodologia/gordon.md` §1 e `docs/metodologia/taxa-real.md` §1, com `sentinela/methods/gordon.py` (`Gordon._calcular`) e `sentinela/data/taxas.py` (`calcular`). Bazin em `docs/metodologia/bazin.md` §§2 e 4, `sentinela/methods/bazin.py` (`Bazin._calcular`), `valuation_engine.py` (perfil e parâmetros) e `config.py` (`BAZIN_DY_MIN`). Lynch em `docs/metodologia/lynch.md` (decisão de 28/10 e exemplo dos quatro intervalos, com crescimento em pontos percentuais) e `sentinela/methods/lynch.py` (`Lynch._calcular`).
- **Fontes conferidas:** FII em `docs/metodologia/fii.md` §§3 e 6a, `config.py` (`FII_SPREAD_TIJOLO`) e `fii_engine.py` (`FIIEngine._calcular_rendimento`). A constante calibrada foi mantida em 25/10. Rede em `tests/conftest.py` (`_connect_bloqueado` e `_sem_rede`), com exceção de sockets Unix locais. Preço em `market_engine.py` (`_buscar_yfinance` e `_buscar_brapi`) e `brapi_provider.py` (`regularMarketPrice`). O histórico usa o COTAHIST em `sentinela/services/historico.py` (`MotorHistorico._buscar_yfinance`).
- **Dificuldades:** o preço de hoje admite contingências sem data de fechamento, e o bloqueio da suíte atua sobre `socket.connect` no processo Python de teste.
- **Como resolvi:** o README descreve a prioridade e as contingências do preço, o alcance do guardião de rede e a calibração registrada na ficha do FII. A revisão leve precisou a unidade do crescimento de Lynch e a limitação do recuo histórico, registrada no resumo da Fase 3 e no BUG-3-50.
- **Testes:** alteração documental. Conferência de links locais versionados, termos vetados e gate completo do item.
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma sobre o item.
- **Para o Marcos revisar:** afirmações metodológicas, cobertura parcial do histórico e próximos passos.

### F4-A04 — fix: keep historical real-rate reads out of the network cache
- **Executor:** codex (GPT-6)
- **Status:** sucesso
- **O que foi feito:** a leitura histórica de `get_taxa_real` volta ao banco antes de acessar o cache. A rede corrente mantém o TTL de 24 h e a invalidação pela edição do Focus. O argumento opcional `hoje` deixa o chamador determinar o corte sem consultar o relógio quando também fornece `as_of`. No produtor histórico do serviço, a data escolhida pelo serviço já leva ao `MotorHistorico`, que lê `series_macro` diretamente.
- **Dificuldades:** a auditoria descreveu abstenção histórica cacheada, mas a condição anterior já excluía abstenções. A regressão confirmou cache de registros históricos válidos e leitura de um registro de rede ao revisitar um dia passado.
- **Como resolvi:** decisão delegada DD-94: referência de hoje nas chamadas isoladas da taxa → aceitar dia explícito e manter o relógio como referência de compatibilidade quando o chamador legado omite o dia (classe 4, desempates 4 e 5; alternativas: tornar o dia obrigatório e quebrar chamadas existentes, ou manter só o relógio). O serviço histórico conserva seu leitor próprio.
- **Testes:** BUG-4-05, 1 passed e 3 xfailed estritos antes → 4 passed. Contexto macro, série histórica, relógio do serviço e taxa corrente, 92 passed. A recuperação após carga tem controle dedicado. Suíte preliminar 5272 passed, 1 skipped, 24 xfailed e golden `1103fcadbe3a745d…` intacto. Mutmut 54/58 (93,10%) em `get_taxa_real` e 283/332 (85,24%) em `config.py`, incluindo seis sem cobertura. Na mutação, a sonda de logging em subprocesso importou o checkout original para manter o mesmo teste sem instrumentação fora do runner.
- **Resíduos:** evidências em `outputs/F4-A04/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** ratificação da decisão delegada no checkpoint.
- **Para o Marcos revisar:** origem da taxa numa nova leitura histórica após carga.
