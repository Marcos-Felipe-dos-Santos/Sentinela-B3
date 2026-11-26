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
- **Decisões que ficaram para o Marcos:** nenhuma sobre o item. Para negar a leitura, adicionar em `.claude/settings.json`, dentro de `permissions.deny`, a entrada `"Read(//home/<usuário>/.local/state/sentinela-b3/**)"`. No Codex gerenciado, adicionar em `requirements.toml` a seção `[permissions.filesystem]` com `deny_read = ["/home/<usuário>/.local/state/sentinela-b3"]` ou incluir o caminho na lista já existente. Se usar `SENTINELA_LOG_DIR`, aplicar as duas entradas ao diretório absoluto efetivo.
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

### F4-A05 — fix: discard other issuers' events before checking their species
- **Executor:** codex (GPT-6)
- **Status:** sucesso
- **O que foi feito:** um ISIN legível ausente do conjunto do emissor permite descartar o evento antes da data com e da conversão de espécie. O evento próprio ainda precisa ter espécie demonstrada. O caso de ISIN ilegível continua conservador, com o tratamento legado preservado.
- **Dificuldades:** o BUG-3-60 protegido tem um código de 12 caracteres sem dígito verificador correto. O comprimento sozinho o confundiria com um ISIN legível.
- **Como resolvi:** decisão delegada DD-95: legibilidade do ISIN para descarte antecipado → exigir a estrutura e o dígito verificador da ISO 6166, mais ausência no conjunto do próprio emissor (classe 3, desempates 1 e 5; alternativas: aceitar só comprimento, ou exigir espécie mapeada antes do descarte). Fonte: diretrizes ISO 6166 da ANNA, https://anna-web.org/identifiers/. Revisão cruzada pendente.
- **Testes:** BUG-4-06, 14 passed e 2 xfailed estritos antes → 16 passed no arquivo protegido, com adição exclusiva dos novos casos. Teste focado dos fatores e regressões, 116 passed. Suíte preliminar 5275 passed, 1 skipped, 24 xfailed. Golden `1103fcadbe3a745d…` intacto. Mutmut 530/570 (92,98%) no módulo, 124/147 em `_fator_do_par` e 38/39 em `_isin_legivel`.
- **Resíduos:** evidências em `outputs/F4-A05/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** ratificação da decisão delegada no checkpoint.
- **Para o Marcos revisar:** descarte da unit alheia e preservação da abstenção para evento próprio sem espécie.

### F4-A06 — fix: filter unproven dividends and events by the ticker's species in backtest returns
- **Executor:** codex (GPT-6)
- **Status:** sucesso
- **O que foi feito:** o retorno de um ticker com identidade demonstrada ignora pendências de proventos de outra espécie e pendências de eventos de outro ISIN. Permanecem as abstenções por pendência do próprio papel, informação ausente ou impossível de comparar e os cortes de horizonte existentes.
- **Dificuldades:** havia três ramos que podiam abster antes da conferência de identidade: provento sem prova, evento sem prova e evento sem data ex.
- **Como resolvi:** apliquei o filtro de identidade aos três ramos e preservei os motivos que já descreviam cada abstenção. Na revisão 1, mantive também a abstenção quando a espécie ou o ISIN chegam com espaços nas extremidades ou em branco.
- **Testes:** BUG-4-07, 12 passed e 3 xfailed estritos antes → 15 passed. Revisão 1: seis casos novos de espaços em xfail estrito antes → 21 passaram no BUG-4-07. Retornos e regressões focadas, 91 passed. Suíte preliminar 5296 passed, 1 skipped, 24 xfailed. Golden `1103fcadbe3a745d…` intacto. Mutmut 2087/2180 (95,73%) no módulo e 479/494 (96,96%) em `_retornos`.
- **Resíduos:** evidências em `outputs/F4-A06/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma sobre o item.
- **Para o Marcos revisar:** os controles de ITUB3 para pendências da PN, da ON e de identidade ausente.

### F4-A07 — fix: keep the FII price-to-book context when the yield lens abstains
- **Executor:** codex (GPT-6)
- **Status:** sucesso
- **O que foi feito:** P/VP e Selic líquida usam o mesmo cálculo de contexto descritivo na saída com valor e na saída com abstenção, conforme a ficha do FII 1.3 §3. A lente continua sem número e sem distância quando se abstém. A faixa do P/VP continua reservada ao F4-A07b.
- **Dificuldades:** as saídas de abstenção retornavam antes do bloco de contexto.
- **Como resolvi:** a saída final recebe o contexto quando a análise ainda não o incluiu. O P/VP inválido e a Selic não finita ficam sem número. O método de rendimento e os motivos de abstenção foram preservados. Na revisão 1, o teste com a fonte corrente proibida demonstrou o acesso adicional na abstenção histórica.
- **Decisão delegada:** DD-96: Selic líquida no contexto novo de uma abstenção histórica → manter P/VP e Selic líquida nula quando o motor histórico não demonstra Selic, sem consultar SGS corrente (classe 2, desempates 1 e 4; alternativas: consultar a fonte corrente, ou ampliar a fronteira histórica antes do F4-H09). Revisão cruzada pendente.
- **Testes:** BUG-4-08, 4 xfails estritos antes → 4 passam. Revisão 1: xfail estrito da fonte corrente histórica → 5 passam. Golden atualizado pelo predicado do item em 81 casos de FII abstidos, somente para acrescentar `pvp` e `selic_liquida`, com zero casos fora do predicado. Suíte preliminar 5301 passed, 1 skipped, 24 xfailed. Mutmut 355/396 (89,65%) no módulo, 32/33 em `analisar`, 29/32 em `_contexto_descritivo` e 222/256 em `_analisar_lentes`. Novo SHA256 `1759c55f7e5995f54075cc78cf64e0ea7d0580089ec68902ee3fe153cc84b1d8`.
- **Resíduos:** evidências em `outputs/F4-A07/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma sobre o item. A ficha da faixa P/VP tem decisão própria no bloco 1.
- **Para o Marcos revisar:** o contexto de FII de papel, fundo de fundos e Informe ausente.

### F4-A08 — fix: require the annual filing delivered before the reference date
- **Executor:** codex (GPT-6) até a mutação; claude-code (Opus 5.5) na retomada, mutação, gate, revisão e commit
- **Status:** sucesso
- **O que foi feito:** a promoção do exercício não civil exige uma DFP identificada por CNPJ, referência e versão no índice, com `DT_RECEB` anterior ao corte. Entrega em D ou posterior mantém o exercício anterior. Um ZIP sem índice gera a abstenção explícita “DFP sem índice de entregas”.
- **Dificuldades:** o BUG-2C-66 e dois casos equivalentes exigiam selecionar 2026 usando ZIPs sintéticos sem índice, o que bloqueou a primeira rodada.
- **Como resolvi:** na decisão de 24/11, Marcos autorizou completar o índice sintético no formato oficial da CVM em `test_ultimo_exercicio_nao_civil_chega_ao_motor` (BUG-2C-66) e nos casos fevereiro e março de `test_exercicio_anual_e_periodo_completo_encerrado` (`tests/test_cvm_fronteiras_2c.py`). As três fixtures passaram a demonstrar `DT_RECEB` anterior ao corte e preservam todas as asserções.
- **Testes:** BUG-4-09, 1 passed e 3 xfailed estritos antes → 4 passed. Região focada, 27 passed. Gate preliminar, 5305 passed, 1 skipped, 24 xfailed. Golden `1759c55f7e5995f5…` igual. A primeira medição reaproveitou estatísticas de outro módulo e foi descartada. Rodada limpa (claude-code, `mutants/` apagado antes) em `exercicio_anual_mais_recente`: 80/88 = 90,9%. Dos oito sobreviventes, quatro mostravam casos faltando (período incompleto entregue; `continue` trocado por `break` nas linhas sem prova). Dois testes novos na regressão BUG-4-09 matam os quatro, conferidos com o mutante aplicado à mão. Os outros quatro são equivalentes: o padrão `None` do `getattr` no 404, já existente, e o corte `fim ≤ referência`, implícito em `DT_RECEB < referência`. Regressão BUG-4-09 com 6 casos. Gate final no stage (claude-code): 5307 passed, 1 skipped, 24 xfailed, Ruff verde, golden `1759c55f7e5995f5…` igual; o aviso de arquivos fora da linha do item cobre as três fixtures autorizadas e a regressão nova.
- **Resíduos:** evidências em `outputs/F4-A08/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma sobre o item.
- **Para o Marcos revisar:** a abstenção explícita por ZIP sem índice e a seleção só após o dia de entrega.

### F4-A09 — fix: count a download of this run as available at today's as_of
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** o `MarketEngine` abre `proveniencia.coleta_da_execucao` só na análise de hoje, com o instante da execução, `min(as_of, relógio)` do BUG-3-63. O `baixar_arquivo` (ZIP da CVM e do Informe) e o `_buscar` do IF.data marcam o arquivo que acabaram de baixar. Para esse arquivo, com o mesmo `mtime` e tamanho, o `registrar_arquivo`, leitura de todas as guardas de coleta, devolve a coleta no instante da execução, e só dentro dela. O arquivo e o registro lateral guardam o `mtime` real. O cache de outra execução depois do as_of continua barrado. Numa data passada, ou sem as_of, nada muda.
- **Dificuldades:** a revisão 1 aprovou o primeiro desenho, mas apontou que carimbar o `mtime` deixava o instante adiantado no cache compartilhado. Uma análise concorrente com as_of entre o carimbo e o download real aceitaria o arquivo. Isso é vazamento de futuro e foi corrigido no próprio item (decisão 48). Os dublês dos testes usam `baixar_arquivo(url, destino)` com dois argumentos, o que impede mudar a assinatura.
- **Como resolvi:** a leitura da execução fica num ponto só, em `sentinela/data/proveniencia.py` (DD-97). O arquivo não está na lista do item, mas está no F4-A10 e não é travado. O instante chega por `ContextVar`, sem mudar assinaturas. `cvm_provider.py` e `cvm_fii_provider.py`, listados no item, não precisaram mudar: os dois baixam pelo `baixar_arquivo` e registram pelo `registrar_arquivo`. Em produção, o `IFDataProvider` do motor não tem calendário de publicação, e a inadimplência continua abstida por “calendário oficial de publicação IF.data indisponível”. Por isso, o cenário de banco roda com o calendário sintético dos testes.
- **Decisão delegada:** DD-97, em `docs/loop/pendencias.md`. Revisão cruzada pendente.
- **Testes:** BUG-4-10 (`tests/regressao/test_bug_4_10_download_da_execucao_no_as_of.py`), com o `MarketEngine.buscar_dados_ticker` real, as etapas fora do teste inertes e o relógio do motor 3 s depois do clique.
  - Correção, quatro casos: ZIP da CVM vencido, Informe vencido, IF.data do banco e outra execução lendo o mesmo ZIP pela hora real. Os três primeiros nasceram xfail estritos (`outputs/F4-A09/regressao-antes.txt`). O quarto, acrescentado na revisão, falha no HEAD e no primeiro desenho (`regressao-antes-r2.txt`).
  - Guardas, quatro casos, verdes antes e depois: ZIP de outra execução depois do as_of; data passada; IF.data de outra execução com a fonte fora do ar, com o texto exato “inadimplência IF.data não informada: coleta não demonstrada até o as_of”; e a lente Bancos igual com e sem a coleta. O último só compara abstenções, porque o dublê da CVM não fornece DVA, PL nem base acionária. Ele prova que o IF.data não muda a saída da lente nesse caminho, mas não a prova com número.
  - Contagem: de 4 passed e 3 xfailed para 8 passed. Região afetada: 313 passed.
  - Mutação, rodada limpa com o desenho final (`mutants/` apagado antes; `outputs/F4-A09/mutacao-r2.txt`):
    - código novo: `marcar_baixado` 7/7; `_lido_na_execucao` 18/19. O sobrevivente formata o instante em outro fuso e mantém o mesmo instante.
    - `registrar_arquivo`, 72/93 = 77,4%. Os 21 sobreviventes estão no código anterior ao item: 20 em parâmetros do temporário e do JSON lateral (`encoding`, `dir`, `prefix`, `suffix`, `delete`, `indent`, `ensure_ascii`) e o mutante 16 na comparação do motivo. Sem os 20 equivalentes de formato, 72/73 = 98,6%.
    - `buscar_dados_ticker`, 180/216 = 83,3%.
    - `baixar_arquivo`, 60/93; sem os 22 mutantes de mensagem de log, 60/71 = 84,5%.
    - `IFDataProvider._buscar`, 46/68; sem os 5 de log, 46/63 = 73,0%. Sem mais 11 equivalentes (`utf-8`/`UTF-8`, `encoding=None` com locale UTF-8, `ensure_ascii` com o JSON relido igual, sufixo `.TMP`), 46/52 = 88,5%. Os sobreviventes restantes (`timeout`, `chunk_size`, `stream`, `parents` do `mkdir`, texto do `ValueError`) são de código anterior ao item.
  - Gate no stage: 5315 passed, 1 skipped, 24 xfailed, Ruff verde, golden `1759c55f7e5995f5…` igual. O aviso de arquivo fora da linha do item cobre `sentinela/data/proveniencia.py` (DD-97) e a regressão nova.
- **Resíduos:** evidências em `outputs/F4-A09/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma sobre o item. A inadimplência em produção depende de um calendário oficial de publicação do IF.data, que não existe (L7).
- **Para o Marcos revisar:** a leitura por execução na proveniência (DD-97) e a marcação do COTAHIST baixado hoje, sem efeito.

### F4-A10 — feat: record the click instant and the actual download time in provenance
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** na análise de hoje, a proveniência de cada coleta da execução traz dois instantes rotulados: `as_of_analise`, o clique, e `baixado_em`, o instante real do download.
  - **Arquivos** (ZIP da CVM, Informe e relatórios do IF.data): o `registrar_arquivo`, lido dentro de `proveniencia.coleta_da_execucao`, devolve um `ProvenienciaDaExecucao` para o arquivo que a própria execução baixou. É uma subclasse com os dois campos, em que `baixado_em` é o `mtime` real, preservado desde o F4-A09. O registro gravado ao lado do arquivo continua um `Proveniencia`, sem os campos novos, e o cache de outra execução não os ganha.
  - **B3** (relação de proventos e complemento do fundo): o `MarketEngine` mede o relógio logo depois da consulta e grava os dois campos ao lado da `coleta`.
  - **Guardas:** continuam lendo só a coleta da execução (`data_coleta` e `coleta`), e nenhum valor de lente muda.
- **Dificuldades:** `tests/test_proveniencia.py::test_registro_tem_todos_os_campos` fixa o conjunto de campos do registro gravado. Acrescentar os campos ao `Proveniencia` mudaria esse contrato.
- **Como resolvi:** os campos ficam numa subclasse que só existe na leitura da execução. O esquema do registro persistido e o teste existente ficam intactos. Numa data passada, ou sem as_of, nada muda.
- **Testes:** `tests/test_proveniencia_dois_instantes.py`, com 7 testes e o relógio fixo dos arranjos BUG-3-63 e BUG-4-10. Cobre B3 da ação, B3 do fundo, ZIP da CVM (no registro do arquivo e no do documento, via `do_documento` e `para_dict`), Informe, IF.data de banco (com `baixado_em` igual ao `mtime` de cada relatório e a inadimplência no contexto) e o cache de outra execução sem os campos. Os seis primeiros falhavam antes pelo campo ausente (`outputs/F4-A10/testes-antes.txt`). O sétimo, da data passada sem os campos na B3, entrou na revisão 1 e mata o mutante `_as_of_analise = as_of` sem o `if hoje`, conferido à mão. Depois, 7 passed. Suíte: 5322 passed, 1 skipped, 24 xfailed. Mutação (`mutants/` apagado antes; `outputs/F4-A10/mutacao.txt`): `_lido_na_execucao` 21/22, com o sobrevivente equivalente de fuso de formatação; `_instantes_da_consulta` 10/10; `_buscar_rendimento_fii` 95/99 = 96,0%; `_buscar_proventos_b3` 158/169 = 93,5%. Gate no stage: 5322 passed, 1 skipped, 24 xfailed, Ruff verde, golden `1759c55f7e5995f5…` igual. Revisão 1: PODE COMMITAR; os três médios de cobertura de teste foram fechados antes do commit. Ressalva baixa mantida: na B3, `baixado_em` é o fim da consulta, que pode vir do cache em memória da mesma coleta. O stage leva também a linha do F4-A09 em `docs/loop/pendencias.md`, com as ressalvas baixas da revisão 2 do item anterior.
- **Resíduos:** evidências em `outputs/F4-A10/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** os nomes dos rótulos (`as_of_analise` e `baixado_em`) e a subclasse só de leitura.

### F4-A08 (ressalva) — test: complete the delivery index in the negative annual-period fixtures
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** decisão 1 do Marcos de 25/11. Os três casos negativos de `test_exercicio_anual_e_periodo_completo_encerrado` (`tests/test_cvm_fronteiras_2c.py`) recebem no índice de entregas a mesma linha dos positivos, com `DT_RECEB` 2026-06-15, anterior ao corte de 26/10/2026. As asserções não mudam. Desde o F4-A08 eles passavam por falta de entrega e não pela regra de período que testam.
- **Testes:** 5 passed nos casos parametrizados. Mutação manual em `cvm_provider.exercicio_anual_mais_recente` (`outputs/F4-A08/mutacao-manual-negativos.txt`): sem `fim > referencia`, falha o caso 2026-01-01..2026-12-31; sem `_meses(inicio, fim) != 12`, falham 2026-01-01..2026-09-30 e 2025-03-02..2026-02-28; sem a regra inteira, falham os três. Código de produção intocado.
- **Resíduos:** evidência em `outputs/F4-A08/`.
- **Decisões que ficaram para o Marcos:** nenhuma. A ressalva do F4-A08 em `docs/loop/pendencias.md` está fechada.

### Registro — docs: queue the ISIN check alignment and note a process deviation
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** decisões 2 e 3 do Marcos de 25/11.
  - Decisão 2 (DD-93): a validação do ISIN com dígito verificador no `proventos_b3` entra na fila em dois itens, F4-A11b e F4-A11c, logo depois do F4-A11. O pedido era de um item, mas exige mover `_isin_legivel` para `proventos_b3` (o `fatores_acoes_b3` já importa `proventos_b3`, e o inverso criaria ciclo), e mover é refactor. Refactor e mudança de comportamento não podem ir no mesmo commit. A observação da DD-93 em `docs/loop/pendencias.md` aponta para os itens.
  - Decisão 3: **desvio de processo.** O commit `bf73c5a` (`docs: record the cross-review of delegated decisions DD-93, DD-95 and DD-96`) foi feito sem o `/review-diff-leve` que o protocolo exige para itens `docs`. O conteúdo é só documentação (as três revisões cruzadas em `pendencias.md`), e não houve reabertura.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-A11 — fix: validate tickers and prices before storing portfolio positions
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-11 (achado 14 do Gemini).
  - `database.adicionar_posicao` valida a entrada antes de abrir o banco, por `_posicao_valida`. O ticker passa por `sentinela.domain.ticker.validar` (lista permitida). A quantidade é inteira, não nula e não booleana. O preço é real, finito e positivo, também na redução. Entrada inválida levanta `ValueError` com o motivo, sem gravar linha.
  - `adicionar_posicao` e `remover_posicao` tratam `sqlite3.Error` como `salvar_analise`: registram no log e devolvem `False`; sem erro, `True`. A gravação ficou em `_gravar_posicao`, com o corpo anterior sem mudança.
  - Aba Carteira (`app.py`): mostra o motivo do `ValueError` ou o erro do banco, e só diz "Salvo!" ou "removido" quando gravou. Esquema e dados intactos.
- **Dificuldades:**
  - `tests/test_database_posicoes.py` usava `TST3`, que fica fora do padrão da B3 e passa a ser recusado.
  - `tests/test_app_analysis_service.py` fixa por hash todo o trecho de renderização do `app.py`, inclusive a aba Carteira.
- **Como resolvi:**
  - Em `test_database_posicoes.py` (na lista do item), o ticker virou `TSTA3`, e o caso de quantidade zero passa a exigir `ValueError`, continuando sem gravar.
  - O hash `RENDER_ANTERIOR` foi atualizado com comentário datado (DD-98). O `git diff app.py` tem só os dois blocos da aba Carteira.
- **Decisão delegada:** DD-98, em `docs/loop/pendencias.md`. Falta a revisão cruzada.
- **Testes:**
  - BUG-4-11 (`tests/regressao/test_bug_4_11_posicao_invalida_na_carteira.py`): 15 casos nasceram xfail estritos (`outputs/F4-A11/regressao-antes.txt`): ticker vazio, só espaços, sem dígito, fora do padrão; quantidade `True`, 2,5 e zero; preço `NaN`, infinito, zero, negativo e `True`; redução com preço `NaN`; erro SQLite simulado na inclusão e na remoção. Depois da revisão de mutação entraram a mensagem de cada `ValueError`, o retorno `True` e a remoção bem-sucedida, que apaga só o ticker normalizado. Agora são 17 passed.
  - Suíte: 5339 passed, 1 skipped, 24 xfailed.
  - Mutação (`mutants/` apagado antes; `outputs/F4-A11/mutacao-r2.txt`): `_posicao_valida` 17/17; `adicionar_posicao` 16/16; `remover_posicao` 12/14, com os dois sobreviventes de maiúsculas e minúsculas no SQL; `_gravar_posicao` 42/55. Os 13 sobreviventes de `_gravar_posicao` são equivalentes: 8 de maiúsculas e minúsculas no SQL, 2 de chave do `sqlite3.Row` (que ignora maiúsculas e minúsculas) e 3 de `qtd == 0`, que não chega mais ali. Nas quatro funções tocadas, 87/102 = 85,3%. Na primeira rodada (`mutacao.txt`), `remover_posicao` estava em 3/14 por falta de teste da remoção bem-sucedida.
- **Resíduos:** evidências em `outputs/F4-A11/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma. O tratamento do erro SQLite na remoção só exigiu a mensagem no `app.py`; nada foi adiado.
- **Para o Marcos revisar:** a DD-98 (hash da renderização) e o `ValueError` como contrato da entrada inválida.

### F4-A11b — refactor: share the ISIN check digit validation from the dividends boundary
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** decisão 2 do Marcos de 25/11, primeira parte. `_isin_legivel` saiu de `sentinela/data/fatores_acoes_b3.py` e virou `proventos_b3.isin_legivel`, com o mesmo corpo (estrutura e dígito verificador, ISO 6166). O `fatores_acoes_b3` a chama por `pb.isin_legivel`, e o `import re` foi junto. Nenhum teste mudou e nenhum comportamento mudou: o `proventos_b3` ainda não usa a função, o que fica para o F4-A11c.
- **Testes:** suíte com 5339 passed, 1 skipped, 24 xfailed, igual ao HEAD. Mutação (`mutants/` apagado antes; `outputs/F4-A11b/mutacao.txt`): `isin_legivel` 38/39. O sobrevivente (`total -=` em vez de `+=`) é equivalente, porque a soma negada também é múltipla de 10 nos mesmos casos.
- **Resíduos:** evidências em `outputs/F4-A11b/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-A11c — fix: require a valid ISIN check digit before discarding a dividend-boundary event as foreign
- **Executor:** claude-code (Opus 5.5)
- **Status:** [!] — parada da política §3 (teste protegido)
- **O que foi feito:** a correção foi tentada no diretório de trabalho e revertida: `if isins and isin not in isins and isin_legivel(isin)`, no lugar do teste de 12 caracteres, em `proventos_b3._evento_de_acoes_na_janela`. A suíte deu 1 failed e 5338 passed. Só falha `tests/regressao/test_bug_4_04_corte_e_emissor_da_janela_b3.py::test_evento_de_outro_emissor_da_mesma_especie_fica_fora`.
- **Dificuldades:** o ISIN "de outro emissor" da fixture, `BRALHEACNOR0`, tem dígito verificador inválido. Pela regra pedida ele é ilegível, e o evento conserva a abstenção em vez de ser descartado. Manter o teste exige trocar o literal por `BRALHEACNOR9`, o único dígito válido, com a asserção igual. O arquivo é regressão protegida.
- **Decisões que ficaram para o Marcos:** autorizar a troca desse literal na BUG-4-04, como no precedente do F4-A08. Com a autorização, o item segue: regressão xfail estrita (ISIN alheio de 12 caracteres com dígito inválido conserva a abstenção), correção, mutação e commit. Patch da tentativa em `outputs/F4-A11c/correcao-tentativa.patch`.

### F4-A11c (retomada) — fix: require a valid ISIN check digit before discarding a dividend-boundary event as foreign
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-12, decisão do Marcos de 25/11 que resolveu o `[!]`. `proventos_b3._evento_de_acoes_na_janela` só descarta como alheio o ISIN fora do conjunto do emissor quando `isin_legivel` o confirma (estrutura e dígito verificador), a mesma função do `fatores_acoes_b3`. ISIN de 12 caracteres com dígito inválido é ilegível e conserva a abstenção, pela DD-93. Efeito colateral conservador: um ISIN alheio que chegue em minúsculas ou com espaço também passa a abster, como no `fatores_acoes_b3`. As duas linhas de `pendencias.md` (o `[!]` resolvido e as ressalvas do F4-A11 enviadas ao bloco 2) foram atualizadas.
- **Dificuldades:** a fixture da regressão protegida BUG-4-04 usava como ISIN "de outro emissor" o `BRALHEACNOR0`, que tem **dígito verificador inválido**. Ela passava pelo teste antigo de 12 caracteres, e com a regra nova virava ilegível.
- **Como resolvi:** com a autorização do Marcos, só esse literal foi trocado por `BRALHEACNOR9`, o único dígito válido. A asserção ficou igual.
- **Testes:**
  - Mutação manual (`outputs/F4-A11c/mutacao-manual-filtro.txt`): sem o filtro de emissor, falham o teste da BUG-4-04 com o literal novo e o caso do ISIN alheio legível. O teste confere "outro emissor", e não "ISIN ilegível".
  - Regressão BUG-4-12 (`tests/regressao/test_bug_4_12_isin_sem_digito_verificador_no_bazin.py`): ISIN alheio com dígito inválido (`…R0`, `…R1` e um com minúsculas) abstém, com o motivo "evento em ações na janela sem reconciliação" e o rótulo do evento, sem descarte silencioso. Esses 3 nasceram xfail estritos (`outputs/F4-A11c/regressao-antes.txt`). Junto, o ISIN alheio legível continua descartado, e o ISIN do emissor continua abstendo.
  - Suíte: 5344 passed, 1 skipped, 24 xfailed.
  - Mutação (`mutants/` apagado antes; `outputs/F4-A11c/mutacao.txt`): `_evento_de_acoes_na_janela` 50/53 = 94,3%. Os três sobreviventes estão no código anterior: dois `continue` → `break` (aprovação futura e espécie) e o padrão `"XXXX"` do ISIN ausente, que é equivalente.
- **Resíduos:** evidências em `outputs/F4-A11c/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma. As ressalvas (1) e (2) do F4-A11 vão para o bloco 2, por decisão de 25/11.

### F4-A12 — fix: read the single store and write audit output under outputs
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-13 (achado 15 do Gemini).
  - `auditoria.auditar_banco` lê `unico.caminho_padrao()`. Com só os bancos antigos no disco, o `RuntimeError` dele vira erro no relatório, sem ler o banco antigo nem criar o único.
  - O `.txt` e o `.json` vão para `outputs/auditoria/`, relativo ao diretório corrente, como o banco. Assim a regressão protegida BUG-2C-29, que faz `chdir` para o `tmp_path`, continua gravando fora do repositório.
  - A carteira sai só como contagem (`{"posicoes": N}` no JSON e "N posições" no texto). Com `--com-carteira`, o texto e o JSON (`itens`) trazem as posições, ainda em `outputs/`.
  - O `DB_PATH` saiu. `meta.db_path` diz "banco único", e `banco.arquivo` traz o caminho lido.
  - Efeito colateral do `caminho_padrao()`: sem nenhum banco no diretório corrente, a auditoria cria o único pelo esquema das migrações. Num banco único existente, aplica as migrações pendentes, como o app. Antes ela só lia (ressalva em `pendencias.md`).
- **Testes:**
  - Regressão BUG-4-13 (`tests/regressao/test_bug_4_13_auditoria_banco_unico_e_saida.py`): banco único temporário em `tmp_path`, sob o `--basetemp` do executor e fora do `/tmp`, com duas posições fictícias e `main()` em `--db-only`. Ela confere os dois arquivos: nenhum relatório no diretório corrente, só a contagem, e nenhum ticker ou preço no texto e no JSON. Com a flag, as posições aparecem. Os 2 casos nasceram xfail estritos (`outputs/F4-A12/regressao-antes.txt`).
  - Casos novos em `tests/test_auditoria_contrato.py`: banco único ausente com banco antigo vira erro, sem criar o único; carteira vazia registra contagem zero.
  - Suíte: 5348 passed, 1 skipped, 24 xfailed.
- **Mutação:** não rodou (`outputs/F4-A12/mutacao.txt`). O `auditoria.py` está em `also_copy` no `[tool.mutmut]`: é copiado, mas não instrumentado. Ele é um script, não módulo de cálculo nem de fronteira, e o mínimo de 80% não se aplica. Mudar a configuração do mutmut fica fora deste item.
- **Resíduos:** evidências em `outputs/F4-A12/`.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** o nome da flag `--com-carteira`.

### F4-A13 — fix: classify assets in the audit script by the official index
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-14 (achado 17 do Gemini, primeira parte). O roteamento FII × ação de `auditoria.main` usa `AssetClassifier().is_fii(ticker, dados)`, como o `app.py`. A classe vem de `dados['classe_ativo']`, depois do índice local e por fim das listas fixas; ticker terminado em 11 sem dado oficial fica `UNKNOWN`. A heurística do sufixo e do `quote_type` `MUTUALFUND` saiu, e o aviso do perfil FII não cita mais o `quoteType`.
- **Testes:**
  - Regressão BUG-4-14 (`tests/regressao/test_bug_4_14_auditoria_classe_pelo_indice.py`), com o arranjo da BUG-2C-29 e o `main()` real. BOVA11 com classe ETF, uma unit fora de `UNITS_CONHECIDAS` (TSTA11, classe UNIT) e um ticker 11 sem classe oficial não chamam o `FIIEngine`; os dois primeiros vão ao valuation de ações (o ETF se abstém pela classe; a unit segue o escopo de STOCK e UNIT). O caso sem classe oficial traz `quote_type` `MUTUALFUND`, para provar também a saída do segundo ramo da heurística antiga. Esses 3 nasceram xfail estritos (`outputs/F4-A13/regressao-antes.txt`). O FII com classe oficial continua no motor de FII.
  - Suíte: 5352 passed, 1 skipped, 24 xfailed.
- **Mutação:** não se aplica, como no F4-A12. O `auditoria.py` está em `also_copy` e não é instrumentado pelo mutmut; os xfails acima mostram a falha da regra antiga.
- **Resíduos:** evidências em `outputs/F4-A13/`.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-A14 — refactor: reuse the technical engine in the audit script
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** achado 17 do Gemini, segunda parte. A partir de 30 pregões, `auditoria.auditar_tecnica` delega o momento do RSI e a tendência a `TechnicalEngine().calcular_indicadores`, o motor do app. Ele compara o RSI e as médias sem arredondar, pela mesma regra do script, e o rótulo do momento perde o complemento do motor (`split`), que tem "(Oportunidade)" e "(Alto Risco)". Abaixo de 30 pregões o motor devolve valores neutros, e o script mantém o próprio momento; a tendência fica "Indefinida", como já ficava sem média de 50 pregões. O RSI e as médias exibidos continuam calculados no script.
- **Dificuldades:** na revisão 1, a primeira versão delegava também o RSI e as médias. A revisão viu que o motor arredonda pelo NumPy (`round` sobre `np.float64`), que diverge do arredondamento do texto: a média de uma série constante em 16,055 sai 16,06 no motor e 16,05 no script, como conferido. Além disso, o motor devolve 0 no lugar de média indisponível. A delegação só vale onde a saída é idêntica (aceite), então ela ficou restrita ao momento e à tendência.
- **Testes:**
  - Caracterização nova, `tests/test_auditoria_tecnica.py`, escrita e verde no código anterior (`outputs/F4-A14/caracterizacao-antes.txt`, 18 passed). Ela fixa o registro (em JSON, que preserva `NaN`) e o SHA-256 do texto sem cores para séries de 0, 1, 14, 29, 30, 31, 49, 50, 199, 200 e 260 pregões, preços constantes (40 e 260), queda (RSI 0), média em empate decimal (16,055 × 60) e `NaN` no último fechamento. Depois da delegação, passa sem mudar.
  - Um teste amarra o limiar `PREGOES_MOTOR_TECNICO` ao do motor (neutro abaixo, calculado a partir dele).
  - Nenhum teste existente mudou. Suíte: 5370 passed, 1 skipped, 24 xfailed.
- **Mutação:** não se aplica, como no F4-A12. O `auditoria.py` está em `also_copy` e não é instrumentado.
- **Resíduos:** gerador e saídas da caracterização em `outputs/F4-A14/`.
- **Decisões que ficaram para o Marcos:** nenhuma. Fica a ressalva de vocabulário: o motor técnico ainda emite "Sobrevendido (Oportunidade)" e "Sobrecomprado (Alto Risco)" (`technical_engine.py`), fora deste item (linha em `pendencias.md`).

### F4-A15 — docs: align agent and project instructions with the code after phase 3
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** achado 16 (parte confirmada), pedido do Marcos de 23/11 e F4-H11. Cada frase foi conferida contra o código:
  - **Camadas:** o `app.py` analisa por `AnalysisService.analisar(ticker, as_of)` desde o F3-6b (`app.py:262-272`), e o serviço devolve o `AnalysisResult` de `domain/models.py`. `AnalysisService.analyze` é só a compatibilidade da API antiga. Só `sentinela/repositories/` segue sem leitor de produção (busca por import: só testes e `vulture_whitelist.py`). Corrigido no `CLAUDE.md` e no `AGENTS.md`.
  - **`BRAPI_TOKEN`:** sai a frase de que ele falta no `.env.example` (conferido pelo Marcos em 23/11; o loop não lê `.env*`). Fica só a leitura em `brapi_provider.py:64`, conferida.
  - **Passo 10 do fluxo de dados:** sem o "cache SQLite (7d)", que saiu no F3-9b (`market_engine.py:636`). O passo agora é só `fundamentos_incompletos`.
  - **`data_quality.py`:** a docstring do módulo dizia que o `market_engine` não preserva valores pré-merge. Ele os guarda em `valores_por_fonte` (`market_engine.py:331`), e os checks 2 e 3 só rodam entre fontes diferentes (`_mesma_fonte`). A docstring agora descreve isso e a origem do LPA e do VPA da CVM (controladores e Composição do Capital do mesmo documento, LPA divulgado nos métodos). A docstring de `validacao_cruzada` foi ajustada. Nenhum código mudou.
  - **`tests/test_contratos_import.py`:** só a docstring, sem a frase de que o `config` faz rede no import (não faz desde o F3-1a).
  - **Contagem da suíte:** 5370 passed, 1 skipped, 24 xfailed, na seção "Estado da fase" do `CLAUDE.md` (data de 25/11), no comando da suíte e no cabeçalho do `AGENTS.md`, fora da "Fase atual". O `AGENTS.md` ainda trazia a contagem de 09/11 e contradizia o `CLAUDE.md`. A "Fase atual" não foi tocada.
- **Testes:** suíte com 5370 passed, 1 skipped, 24 xfailed; só docstrings e textos mudaram.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-A15b — docs: retire Jules from the work split
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** adendo do Marcos de 24/11, item 2 (o Jules sai em 31/12/2026). O Jules sai da divisão de trabalho, e os tickets triviais da D31 e o coletor do IPE (F5-1) passam ao Codex. Arquivos alterados:
  - `CLAUDE.md`: o cabeçalho cita "Codex e outros", e a seção "Divisão com o Jules" virou "Divisão de trabalho", com a coluna "Codex, por ticket" e a nota datada.
  - `AGENTS.md`: só o cabeçalho, fora da "Fase atual".
  - `docs/PLANO.md`: F5-1 com "Codex"; Fase 7 com "nunca por ticket externo"; seção 8 com nota datada, a coluna de tickets passando ao Codex e os arquivos travados valendo para ticket externo; linha de risco "ticket externo e loop no mesmo arquivo".
  - ADR 0003: só uma nota datada na D31.
  - `docs/loop/workflow-multiagente.md` e `docs/loop/ciclo-de-fase.md`: sai a linha do Jules como executor, entra a nota datada, e o Codex recebe os tickets da D31.
- **Dificuldades:** a busca por "Jules" fora dos históricos ainda acha menções sem data em arquivos fora da lista do item: `docs/loop/auditoria-externa.md` e a descrição da skill `verificar-entrega`.
- **Como resolvi:** respeitei a lista de arquivos e registrei as duas em `docs/loop/pendencias.md`, para item próprio. As linhas de itens concluídos do PLANO e as ADRs antigas são registro histórico e não mudaram. O `CLAUDE.md` e o `AGENTS.md` não se contradizem.
- **Testes:** suíte com 5370 passed, 1 skipped, 24 xfailed; só documentação.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-A16 — chore: drop the unused debt-to-equity indicator
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** achado 11 do Gemini. A busca por `divida_pl` nos `.py` confirma que nenhum código de produção a lê: o `market_engine` só a cita num comentário, dizendo que não a mapeia. A chave e o cálculo saíram de `CVMProvider.calcular_indicadores`, junto com a menção na docstring.
- **Asserções removidas, com o motivo:** as três afirmavam o valor ou a ausência da chave removida.
  - `tests/test_cvm_provider.py`: `divida_pl == (passivo − PL)/PL`.
  - `tests/test_contas_cvm_consumidores.py`: `divida_pl is None` no banco e o valor na Petrobras. As outras asserções dos dois testes, inclusive PL, ROE e margem, ficam.
- **O que não mudou:** `tests/test_market_engine.py` e `tests/test_market_engine_acoes_cvm.py` não têm asserção sobre a chave, só dublês que a carregam; ficam intactos. `tests/test_financeiro_pre_refactor.py` (seção B, `_CVM_TO_MARKET`) também não muda e continua verde.
- **Testes:** suíte com 5370 passed, 1 skipped, 24 xfailed. A contagem é igual porque nenhum teste saiu, só asserções. Golden igual.
- **Mutação:** não se aplica. O item só remove código, e não há linha nova a mutar.
- **Resíduos:** saídas do inventário em `outputs/F4-A16/`; entrada nova em `docs/limpeza/inventario.md`.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-A17 — chore: remove duplicated lens checks in FII engine tests
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** achado 13 do Gemini. Saíram as duas chamadas consecutivas idênticas de `verificar_lentes`, uma em `tests/test_fii_engine.py` e outra em `tests/test_fii_engine_rendimento.py`. Em `tests/test_fii_engine_pvp.py`, as chamadas seguidas recebem argumentos diferentes (`resultado`, `_analisar(pvp=1.0)`, `negativo`, `_analisar(pvp=0.8)`) e ficam. Nenhuma asserção distinta mudou.
- **Testes:** os três arquivos têm 27 passed antes e depois. Suíte com 5370 passed, 1 skipped, 24 xfailed.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-A18 — chore: drop retired manual maps from mutation and stale vulture exceptions
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** achado 18 do Gemini.
  - `cvm_fii_map.py` e `cvm_ticker_map.py` saem do `source_paths` do mutmut. Os testes ainda os importam, então entram no `also_copy`, copiados sem mutar. Uma rodada curta de mutação (`outputs/F4-A18/mutacao-sonda.txt`) roda limpa e repete os 38/39 do F4-A11b.
  - No `vulture_whitelist.py`, saem os comentários do F3-6 "ainda desconectada" e "sem chamador até o F3-6", trocados pelo estado atual: camada ligada desde o F3-6b, `with_warning` sem chamador de produção.
- **Dificuldades:** o aceite cita `max_age_days` como exceção sem alvo, mas ele ainda tem alvo: os dublês de `buscar_fundamentos_cache` em `tests/test_market_engine.py:77` e `:453`. Sem a exceção, o vulture acusa as duas linhas, e o aceite exige "sem achado novo".
- **Como resolvi:** a exceção fica, com o motivo aqui e no inventário.
- **Testes:** vulture e deptry rodados de novo, com saída igual à de antes (`outputs/F4-A18/`). Suíte com 5370 passed, 1 skipped, 24 xfailed.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-A19 — docs: plan quality coverage in the motor golden
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** levantamento do achado 12 em `docs/decisoes/golden-qualidade-4.md`, sem regenerar nada. A contagem sobre o golden (`1759c55f7e5995f5…`) corrige a leitura do achado:
  - 1924 dos 2003 casos de ações já têm cinco exercícios observados (identidade do `enriquecer_janelas`).
  - Os cinco indicadores estão vazios em todos os 9620 exercícios. O golden fixa só os motivos de abstenção, nenhum valor.
  - O documento lista os insumos que faltam (seis números por exercício, identidade e o `calendario_proventos_b3`) e as opções (A) enriquecer o apoio comum, (B) família nova de 12 casos e (C) lacuna declarada.
  - Para a (B), recomendada, traz os casos, os arquivos de uma futura regeneração e o predicado: as 2291 linhas antigas ficam idênticas e só entram as novas.
- **Decisões que ficaram para o Marcos:** P1, no checkpoint do bloco 0. Sem decisão, vale (c), a lacuna declarada.

### F4-A20 — chore: remove the author's local paths from tracked files
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** adendo 2, item 7.
  - Os caminhos pessoais do Windows e do WSL do autor viraram descrições genéricas (`<Downloads do Windows>`, `<pasta do usuário no Windows>`, `/home/<usuário>/`) em `docs/decisoes/ressalva-cotahist-fii-2c.md`, `docs/loop/pendencias.md`, `docs/loop/resumo-2c-a.md` e `docs/loop/historico/fase-2b/fila.md`. Nos dois comandos de `docs/loop/workflow-multiagente.md`, viraram `/mnt/c/Users/<usuário>/Downloads`.
  - O `git grep` também achou `docs/loop/diario.md`, nas entradas de negação de leitura do Claude Code e do Codex, e esse arquivo foi tratado igual. Só o caminho mudou, sem mudar o sentido.
  - Em `scripts/auditar.py`, a pasta fixa do Windows saiu. O destino é `--saida`; senão, a variável `SENTINELA_AUDITORIA_DESTINO`; senão, `outputs/auditorias/`. A frase sobre o destino em `docs/loop/ciclo-de-fase.md` acompanha.
  - Para manter a saída no Downloads, o Marcos define `SENTINELA_AUDITORIA_DESTINO=/mnt/c/Users/<usuário>/Downloads`.
- **Testes:** três casos novos em `tests/test_script_auditar.py`: o padrão, a variável com o `--saida` tendo precedência, e a variável vazia voltando ao padrão. Os 46 do arquivo passam. Ao fim, `git grep -n -I -i -E 'wsl[$]|/home/marco[s]|C:.Users.marco[s]|/mnt/c/Users/marco[s]'` não acha nada nos arquivos versionados. Suíte com 5373 passed, 1 skipped, 24 xfailed.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** definir a variável no ambiente, se quiser a saída no Downloads.

### [DECISÃO] Checkpoint do bloco 0 — pedido de auditoria R2
- **Executor:** claude-code (Opus 5.5)
- **Status:** parada no `[DECISÃO]`; a auditoria ainda não rodou
- **Intervalo:** `769e385..d5bf7de` (de `chore: activate phase 4 queue`, exclusivo, até o F4-A20). São 30 commits: 20 com `Executor: claude-code`, 10 com `Executor: codex` e nenhum sem a linha.
- **Auditoria cruzada (decisão 23; seleção por autoria), uma rodada por família:**
  - Commits do claude-code, auditados pelo Codex: `python scripts/auditar.py codex fase --fase 4 --desde 769e385`.
  - Commits do codex, auditados pelo Claude: `python scripts/auditar.py claude fase --fase 4 --desde 769e385`.
  - Cada família audita só os commits da outra. O claude-code não audita o próprio trabalho.
- **Saída:** `outputs/auditorias/`, ou a pasta de `SENTINELA_AUDITORIA_DESTINO` (F4-A20). O veredito e o caminho do relatório entram no diário por um commit `docs:` próprio, fora do intervalo auditado.
- **Decisões do Marcos neste checkpoint:**
  - P1, a regeneração da Qualidade no golden (`docs/decisoes/golden-qualidade-4.md`, recomendação (B); sem decisão, vale (c)).
  - Liberar o bloco 1, que começa a contar o prazo de 2 semanas.
  - A nota do F4-A18 sobre a exceção `max_age_days`.
- **Revisões cruzadas pendentes, pelo codex:** DD-97 (F4-A09) e DD-98 (F4-A11).

### Checkpoint do bloco 0 — resultado da R2 e fila curta
- **Executor:** claude-code (Opus 5.5)
- **Status:** registro
- **Auditoria R2:**
  - Codex: veredito "não pode seguir", com quatro bloqueadores (versão da DFP, download concorrente, ISIN inválido por espécie no Bazin e OHLC parcial na auditoria técnica) e ressalvas. Relatório salvo sem edição em `docs/loop/auditorias/bloco0-codex.md`.
  - Claude (chat), sobre os 10 commits do codex: sem bloqueador, com uma observação (provento sem `dateApproval` legível). Registro em `docs/loop/auditorias/bloco0-claude-chat.md`.
- **Decisões do Marcos (25/11):**
  - Fila curta F4-C01 a F4-C09, cada `fix:` com teste vermelho antes.
  - P1 = opção (B), no F4-C10, com o predicado aprovado.
  - `max_age_days` ratificado.
  - Depois da fila, a segunda rodada só do diff, pela outra família de quem corrigiu. Se limpa, o checkpoint é marcado e o bloco 1 liberado.
- **Nota:** o relatório do Codex tem links com o caminho local do autor, e o `git grep` do F4-A20 volta a achá-lo. Foi mantido sem edição, por instrução do Marcos (pendência registrada).

### F4-C01 — fix: carry the delivered DFP version into today's snapshot and series
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-15, bloqueador 1 da R2 do bloco 0.
  - `CVMProvider.exercicio_e_versao_mais_recente` devolve o exercício e a versão comprovados no corte: a maior `VERSAO` (com o `DT_REFER` mais recente) entre as linhas anuais encerradas com `DT_RECEB < D`, por corte diário, sem hora. Sem exercício do ano comprovado, devolve o ano anterior com versão `None`, e a leitura dele segue a regra antiga. O `exercicio_anual_mais_recente` delega e devolve só o ano.
  - `calcular_indicadores(..., versao_final=)` restringe o último exercício a essa versão antes de escolher, e `indicadores_da_serie` a repassa, só quando há versão, para os dublês antigos continuarem valendo.
  - Na análise de hoje, `MarketEngine._serie_cvm` usa o seletor novo e guarda a versão em `dados['_versao_dfp_final']`, que o snapshot de `_buscar_cvm` retira e consome. Numa data passada, o seletor antigo continua: o recorte por entrega (F3-3d) já tira as versões de D, e a regressão protegida BUG-3-50 substitui o seletor antigo.
- **Testes:** regressão BUG-4-15 (`tests/regressao/test_bug_4_15_versao_dfp_fora_do_corte.py`), com V1 (entregue em 15/06, lucro 100 mil) e V2 (entregue em D = 16/06, lucro 900 mil) no mesmo ZIP.
  - Três casos nasceram xfail estritos (`outputs/F4-C01/regressao-antes.txt`): o seletor devolve (2026, "1"); o snapshot e a série leem a V1; a cascata de hoje, com o relógio do motor em D, grava o lucro da V1. Antes da correção, a cascata lia 900 mil.
  - O controle confirma que, sem versão, a API antiga continua lendo a V2.
  - Suíte: 5377 passed, 1 skipped, 24 xfailed.
  - Mutação (`mutants/` apagado antes; `outputs/F4-C01/mutacao.txt`): `exercicio_e_versao_mais_recente` 99/102 = 97,1%; `exercicio_anual_mais_recente` 5/5; `calcular_indicadores` 498/545 = 91,4%; `indicadores_da_serie` 212/245 = 86,5%; `_serie_cvm` 210/239 = 87,9%. Os sobreviventes das linhas novas ou movidas são de código anterior: texto de exceção, `getattr` do 404, `fim >= referencia` equivalente no corte diário, inicializações.
- **Revisão 1 (PODE COMMITAR, com médios):** o médio 1 podia dar resultado errado e foi fechado antes do commit (decisão 48). Se a versão comprovada sumiu do arquivo, por exemplo num novo download entre o seletor e o snapshot (DD-34), `calcular_indicadores` levanta `ValueError` e o exercício se abstém, em vez de ler as outras versões. O mesmo vale sem a coluna `VERSAO`. Entraram dois testes: versão ausente abstém, e a cascata retira a chave interna. O ternário encadeado do `_serie_cvm` virou `extra_serie`. Suíte: 5379 passed, 1 skipped, 24 xfailed. Mutação refeita nas duas funções alteradas (`outputs/F4-C01/mutacao-r2.txt`): `calcular_indicadores` 501/549 = 91,3%; `_serie_cvm` 208/235 = 88,5%. A linha da BUG-4-15 foi acrescentada em `tests/regressao/README.md`. Limite conhecido, em `pendencias.md`: o TTM de hoje (`acumulados_ttm`) ainda agrupa todas as versões; a janela contábil casa pela versão da série e, sem ela, fica sem valor.
- **Resíduos:** evidências em `outputs/F4-C01/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma. A pergunta 1 do relatório (admitir entrega em D com hora oficial) ficou no padrão pedido: corte diário, sem hora.

### F4-C02 — fix: give each download its own temporary file and record its content hash
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-16, bloqueador 2 da R2 do bloco 0, que corrige a DD-97.
  - O download da CVM (`cvm_download.baixar_arquivo`) e o do IF.data (`IFDataProvider._buscar`) gravam num temporário próprio (`<destino>.<uuid>.tmp`).
  - `proveniencia.marcar_baixado(caminho, sha256)` registra o hash dos bytes que a própria execução escreveu, calculado durante a gravação, e não o `stat` depois de publicar.
  - `_lido_na_execucao` só dá a coleta da execução ao arquivo cujo hash atual é igual ao marcado. Se outra execução publicou o mesmo destino no intervalo, o registro volta à hora real.
  - Na falha (404 ou erro final), `_limpar_temporarios` remove o temporário do download e o de nome fixo deixado por versões anteriores. Isso mantém intacto `tests/test_cvm_download.py::test_404_preserva_cache_antigo_e_limpa_temporario`, que semeia esse resto.
- **Testes:** regressão BUG-4-16 (`tests/regressao/test_bug_4_16_download_concorrente_no_as_of.py`). A execução A roda dentro de `coleta_da_execucao`, e a B num contexto vazio, intercalada por dublês de `os.replace`/`Path.replace` e do corpo da resposta, com bytes distintos.
  - CVM: B publica entre a publicação e a marcação de A, e A não aceita o arquivo de B. Num download intercalado ao meio, A termina com os próprios bytes e sem temporário sobrando.
  - IF.data: a mesma interferência, e temporários distintos entre dois downloads.
  - Os 4 casos nasceram xfail estritos. Na primeira versão, o caso da CVM passava por um motivo errado (B achava o cache válido e não baixava). Corrigido, ele foi conferido vermelho no código anterior e verde no novo (`outputs/F4-C02/regressao-antes-final.txt`).
  - O controle confirma que o download sequencial da própria execução continua no as_of.
  - Suíte: 5384 passed, 1 skipped, 24 xfailed.
- **Mutação** (`mutants/` apagado antes; `outputs/F4-C02/mutacao.txt`):
  - `marcar_baixado` 5/5; `_lido_na_execucao` 24/25 (o sobrevivente é o fuso de formatação, equivalente); `_limpar_temporarios` 5/5.
  - `baixar_arquivo` 75/108, ou 75/86 = 87,2% sem os 22 mutantes de log.
  - `IFDataProvider._buscar` 50/69, ou 50/64 = 78,1% sem os 5 de log, e 50/56 = 89,3% sem os 8 equivalentes de codificação (`utf-8`/`UTF-8`/`None`, `ensure_ascii`), já que o hash é do que foi gravado. Os demais sobreviventes são de código anterior (`timeout`, `chunk_size`, `stream`, `parents`).
- **Revisão 1 (PODE COMMITAR):** o IF.data passa a remover o próprio temporário também na falha (`try/finally`), como a CVM. Saiu um dublê de relógio que nenhum teste usava. O limite da janela entre a conferência e a releitura do ZIP pelo consumidor foi declarado em `pendencias.md`. A mutação do `_buscar` não foi refeita depois do `try/finally`, que só limpa o temporário.
- **Resíduos:** evidências em `outputs/F4-C02/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-C01 a F4-C03 — andamento da fila curta
- **F4-C01** (`5aebcf1`) e **F4-C02** (`b2785ad`) concluídos (seções acima).

### F4-C03 — fix: never discard a stock event by species from an unreadable ISIN
- **Executor:** claude-code (Opus 5.5)
- **Status:** [!] — parada da política §3 (teste protegido)
- **O que foi feito:**
  - A regressão BUG-4-17 foi escrita e conferida: com o alvo ON, um ISIN ilegível de aparência PNA ou PN, com ou sem conjunto do emissor, liberava o DY, e os 4 casos nasceram xfail estritos (`outputs/F4-C03/regressao-antes.txt`).
  - A correção é uma linha: a espécie só vem de ISIN legível. Ela foi aplicada, rodada e revertida.
- **Dificuldades:** com a correção, a suíte deu 7 failed. Seis são da regressão protegida BUG-4-03, que usa os ISINs sintéticos `BRTESTACNP{C..H}0`, com dígito verificador inválido, esperando o descarte por espécie. O sétimo é `tests/test_proventos_b3.py` (`BRXXXXACNPR1`).
- **Decisões que ficaram para o Marcos:** autorizar a troca só dos dígitos verificadores nesses literais, pelos válidos listados em `pendencias.md`, com as asserções iguais. Com a autorização, o item segue: a regressão volta de `outputs/F4-C03/` para `tests/regressao/`, aplica-se `outputs/F4-C03/correcao-tentativa.patch`, trocam-se os literais e seguem-se a mutação, o gate, a revisão e o commit.

### F4-C03 (retomada) — fix: never discard a stock event by species from an unreadable ISIN
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-17, bloqueador 3 da R2 do bloco 0, depois da autorização do Marcos de 25/11. Em `proventos_b3._evento_de_acoes_na_janela`, a espécie só vem de ISIN legível (`isin_legivel`). ISIN ilegível nunca descarta o evento por espécie e, dentro da janela, abstém com o motivo do evento.
- **Dificuldades:** as fixtures tinham **dígito verificador inválido**: os ISINs sintéticos `BRTESTACNP{C..H}0` da regressão protegida BUG-4-03 e `BRXXXXACNPR1` de `tests/test_proventos_b3.py`.
- **Como resolvi:** pela autorização, só os dígitos foram trocados, com as asserções iguais. No BUG-4-03, um mapa `DIGITO` dá C8, D6, E4, F1, G9 e H7 nos dois testes que montam o literal. Em `test_proventos_b3.py`, `BRXXXXACNPR0`.
- **Testes:**
  - Mutação manual (`outputs/F4-C03/mutacao-manual-especie.txt`): sem o descarte por espécie, falham os seis casos do BUG-4-03 e o de `test_proventos_b3.py`. Eles testam a espécie, e não o ISIN ilegível.
  - Regressão BUG-4-17 (`tests/regressao/test_bug_4_17_isin_invalido_outra_especie_bazin.py`): ISINs ilegíveis de aparência PNA e PN, com e sem conjunto do emissor, abstêm com o motivo do evento. Esses 4 nasceram xfail estritos (`outputs/F4-C03/regressao-antes.txt`). Os controles seguem: ISIN legível de PNA, sem conjunto do emissor, descartado pela espécie (corrigido na revisão 1, porque o arranjo do BUG-4-04 descartava pelo emissor), e ISIN do emissor da mesma espécie abstendo. A falha da mesma família nos fatores foi registrada em `pendencias.md`.
  - Suíte: 5390 passed, 1 skipped, 24 xfailed.
  - Mutação (`outputs/F4-C03/mutacao.txt`): `_evento_de_acoes_na_janela` 53/56 = 94,6%. Os três sobreviventes são do código anterior: dois `continue` → `break` e o `"XXXX"` equivalente.
- **Resíduos:** evidências em `outputs/F4-C03/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma.

### Caminhos locais nos relatórios copiados (decisão 2 do Marcos de 25/11/2026)
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:**
  - Em `docs/loop/auditorias/bloco0-codex.md`, os 40 links com o caminho local do autor viraram caminhos relativos ao repositório. O topo ganhou a linha "Editado só para remover caminhos locais do autor (25/11/2026)", e nada mais mudou.
  - A regra entrou em `docs/loop/protocolo.md`: toda cópia versionada de relatório passa por essa limpeza.
  - `scripts/auditar.py` passa a anexar a todo prompt a instrução de citar arquivos por caminho relativo à raiz do repositório (`CAMINHOS_RELATIVOS`).
  - A pendência foi fechada, e o `git grep -n -I -i -E 'wsl[$]|/home/marco[s]|C:.Users.marco[s]|/mnt/c/Users/marco[s]'` voltou a zero.
- **Testes:** `tests/test_script_auditar.py` ganhou o caso do prompt das três famílias com a instrução. Suíte de 5390 para 5393 passed, 1 skipped, 24 xfailed. Os links relativos à raiz não navegam no GitHub a partir de `docs/loop/auditorias/`; a decisão pediu caminhos relativos à raiz, e a privacidade era o objetivo.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-C04 — fix: keep the audit technical report when High or Low is invalid
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-18, bloqueador 4 da R2 do bloco 0. `auditoria.auditar_tecnica` passa ao `TechnicalEngine` só a coluna `Close`. O momento e a tendência que o script usa dependem só dela, e o relatório nunca usou `High` e `Low`. Assim o ATR do motor não roda, e um `High` ou `Low` inválido não quebra mais o relatório, que volta a ser o de antes do `e29ade6`.
- **Testes:**
  - Regressão BUG-4-18 (`tests/regressao/test_bug_4_18_auditoria_tecnica_ohlc_parcial.py`): com 60 fechamentos, `High` textual, e `High` e `Low` textuais, o relatório (registro e texto) é igual ao da mesma série só com `Close`. Esses 2 casos nasceram xfail estritos, com `TypeError` (`outputs/F4-C04/regressao-antes.txt`).
  - Os controles com `High` e `Low` válidos ou `Low` ausente, que já passavam, ficam.
  - A caracterização do F4-A14 segue verde.
  - Suíte: 5397 passed, 1 skipped, 24 xfailed.
- **Mutação:** não se aplica. O `auditoria.py` está em `also_copy` e não é instrumentado; os xfails acima mostram a falha anterior.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-C05 — fix: store integral NumPy quantities as integers and reject non-finite average prices
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-19, ressalvas da R2 sobre o F4-A11. `database.py` foi tocado com a autorização do Marcos no checkpoint de 25/11.
  - Depois de validada, a entrada de `adicionar_posicao` vira `int` e `float` nativos do Python, e a quantidade do NumPy é gravada como `INTEGER`.
  - Em `_gravar_posicao`, uma média ponderada não finita levanta `ValueError` dentro da transação. A transação é desfeita e a posição anterior fica, e a aba Carteira já mostra o `ValueError`. A docstring cita os dois casos.
- **Testes:**
  - Regressão BUG-4-19 (`tests/regressao/test_bug_4_19_carteira_tipos_e_media.py`): `np.int64`, `np.int32` e `np.uint16` gravados como `integer`, com redução posterior funcionando; e duas compras de 2 a `1e308` rejeitadas na segunda, com a posição de 2 a `1e308` intacta. Esses 4 casos nasceram xfail estritos (`outputs/F4-C05/regressao-antes.txt`).
  - O controle com `np.float64` como preço segue aceito.
  - A fila previa dois arquivos de regressão. Juntei os dois achados num só (BUG-4-19), porque são do mesmo método e da mesma ressalva da R2.
  - Suíte: 5402 passed, 1 skipped, 24 xfailed.
- **Mutação** (`outputs/F4-C05/mutacao.txt`): `adicionar_posicao` 19/19; `_gravar_posicao` 45/58, com os mesmos 13 equivalentes do F4-A11 (8 de maiúsculas e minúsculas no SQL, 2 de chave do `sqlite3.Row`, 3 de `qtd == 0`). A guarda nova foi morta.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-C06 — fix: keep the original download instant when the B3 relation comes from cache
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-20, ressalva da R2 sobre o F4-A10.
  - O `coletar` da relação de proventos (`b3_proventos`) e o do complemento do fundo (`b3_fundos`) registram `obtida_em`, o instante real da consulta à fonte, só quando de fato a consultam. O cache em memória devolve esse instante original. Na `Relacao` é um campo `compare=False`; no registro do fundo, uma chave que o motor retira antes de gravar `b3_fundo`.
  - O instante vem do relógio do motor (`relogio=`), passado por `MarketEngine._coletar_b3` só quando o provedor aceita o argumento. Os dublês antigos seguem valendo, e o teste do F4-A10 continua com o relógio do motor.
  - `_instantes_da_consulta` grava `baixado_em = obtida_em`. Sem ele, o fim da chamada, como antes.
  - `b3_fundos.py` ficou fora da lista literal do item, mas o aceite fala em "B3" e o fundo tinha o mesmo defeito. Na revisão 1, as docstrings dos dois provedores passaram a dizer que só `obtida_em` lê o relógio, e o teste passou a afirmar que a primeira análise consultou a fonte.
- **Testes:**
  - Regressão BUG-4-20 (`tests/regressao/test_bug_4_20_hora_download_b3_em_cache.py`), no arranjo do BUG-3-63: a mesma análise repetida com o relógio 30 s adiante não faz nova chamada à B3 e preserva `baixado_em` igual ao da primeira, na relação de proventos e no complemento do fundo. Os 2 casos nasceram xfail estritos (`outputs/F4-C06/regressao-antes.txt`).
  - Suíte: 5404 passed, 1 skipped, 24 xfailed.
- **Mutação** (`outputs/F4-C06/mutacao-resumo.txt`): `_coletar_b3` 11/13; `_instantes_da_consulta` 10/11; `b3_fundos.coletar` 37/38; `b3_proventos.coletar` 28/29. Os sobreviventes são `aceita = None` (equivalente), `aceita = True` no ramo de assinatura não introspectável e o fuso do relógio de reserva, `now(None)`, que os testes não alcançam porque o motor sempre passa o relógio.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-C07 — fix: inspect the store read-only and hide analysed tickers in the audit by default
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-21, ressalva da R2 sobre o F4-A12 e pergunta 2 do relatório.
  - `auditoria.auditar_banco` deixa de chamar `unico.caminho_padrao()`, que cria e migra. Sem o `sentinela_store.db` no diretório corrente, registra o erro e não cria o arquivo. Com ele, abre só para leitura (`mode=ro`), sem migrar.
  - A seção "Análises salvas" sai só como contagem (`{"quantidade": N}` e "N análise(s)"). Com `--com-analises`, a lista detalhada (`itens`) aparece, como a carteira com `--com-carteira`. A docstring e o uso do script acompanham.
- **Decisão delegada:** DD-99. O caso `test_carteira_vazia_registra_contagem_zero`, do F4-A12, passa a criar o banco antes, com a asserção igual (`docs/loop/pendencias.md`).
- **Testes:**
  - Regressão BUG-4-21 (`tests/regressao/test_bug_4_21_auditoria_inspecao_sem_migrar.py`): sem banco, nada é criado; num banco sem as tabelas das migrações, o esquema não muda; sem a opção, nenhum ticker de análise no relatório; com ela, a lista aparece. Os 4 casos nasceram xfail estritos (`outputs/F4-C07/regressao-antes.txt`).
  - A regressão BUG-4-13 e os casos novos do F4-A12 seguem verdes.
  - Revisão 1 (PODE COMMITAR, com médios fechados antes do commit):
    - Um banco existente sem as tabelas `carteira_real` e `analises` vira erro no relatório, sem migrar e sem cair.
    - O relatório registra só o nome `sentinela_store.db`, sem o caminho local.
    - A docstring restringe a promessa à seção do banco: no modo completo, o `MarketEngine` ainda abre o banco do app.
    - Entraram três testes: abertura com `?mode=ro`, banco sem tabelas, e nome no relatório. O texto impresso sem ticker de análise também passou a ser conferido.
  - Suíte: 5411 passed, 1 skipped, 24 xfailed.
- **Mutação:** não se aplica (`auditoria.py` em `also_copy`).
- **Decisões que ficaram para o Marcos:** nenhuma. A DD-99 aguarda a revisão cruzada.

### F4-C08 — test: pin the abstention for dividends without a readable approval date
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso, sem mudança de código (DD-100)
- **O que foi feito:** a observação da auditoria do Claude (chat) não se reproduziu. Nos caminhos que somam proventos, o provento na janela sem `dateApproval` legível já leva à abstenção:
  - `serie_12_meses` e `entradas`, com `MOTIVO_DISPONIBILIDADE`;
  - `relacao_ate`, que só retira da relação os aprovados em D ou depois, de modo que o ilegível chega à série;
  - o backtest, pelo `sem_prova` do `proventos_ate`.

  O item vira um teste de caracterização que fixa a abstenção, e o título do commit passa de `fix:` a `test:`.
- **Testes:** `tests/test_provento_sem_aprovacao.py`, com 7 casos: aprovação vazia, nula, ausente, com data impossível, com texto e em formato ISO abstêm com o motivo; fora da janela, nada muda. Na mutação manual sem a guarda (`outputs/F4-C08/caracterizacao.txt`), os 6 casos de abstenção falham. Suíte: 5418 passed, 1 skipped, 24 xfailed. O teste fixa o caminho de `entradas`; `relacao_ate` e o backtest foram conferidos na leitura do código, sem trava própria neste item. A linha da fila guarda a definição original (`fix:`, arquivos previstos); o commit sai como `test:`.
- **Decisões que ficaram para o Marcos:** a DD-100 aguarda a revisão cruzada. Se o auditor tiver um caso concreto, ele vira item novo.

### F4-C09 — docs: distinguish missing provenance in data quality and test bank leverage fields
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** ressalvas da R2 sobre o F4-A15 e o F4-A16.
  - A docstring do módulo `data_quality.py` distingue os casos. Os checks de P/L e P/VP derivados deixam de rodar só quando se comprova a mesma fonte (identidade). Sem a proveniência registrada, a origem não está demonstrada e o check roda, como `_mesma_fonte` faz. Fontes distintas comprovadas também rodam.
  - `test_banco_sem_pl_na_2_03_nao_gera_patrimonio_nem_alavancagem` volta a conferir o que o nome promete: `divida_liq_ebitda` e `div_liq_patrimonio` ausentes no banco, cada um com seu motivo. Os valores foram conferidos antes de afirmar.
- **Testes:** suíte com 5418 passed, 1 skipped, 24 xfailed. Nenhum código de produção mudou.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-C09 (complemento) — docs: rewrap the data quality module docstring
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** no `14029b7`, uma linha da docstring do módulo `data_quality.py` emendou no texto seguinte e passou de 110 caracteres. O parágrafo foi só requebrado, sem mudar o texto.
- **Decisões que ficaram para o Marcos:** nenhuma.

### F4-C10 — test: add a quality family to the motor golden
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** P1 = opção (B), pela decisão do Marcos de 25/11. O golden dos motores ganha a família de Qualidade de `docs/decisoes/golden-qualidade-4.md` (§4 e §5):
  - `tests/apoio_qualidade.py`: completa a `serie_cvm` do `enriquecer_janelas` (2021 a 2025) com os seis números por exercício, CNPJ, modelo e perímetro. Acrescenta à relação da B3 um provento por ano em 10/06, fora da janela de 12 meses do Bazin, e o calendário de pregões. As 12 variantes do §4 saem por parâmetro.
  - `tests/golden_motores.py`: `_acoes_qualidade()` depois de `_acoes_taxa_bazin()`, e um gancho em `executar` para os casos com a chave `qualidade`.
  - `tests/test_qualidade_golden_valores.py`: os valores dos dois casos completos (empresa e banco), calculados à mão e verdes antes da geração. ROE de 0,10 a 0,14, média 0,12, desvio √0,0002 = 1,4142 p.p.; margem de 0,12 a 0,16; alavancagem 0,5; proventos 1,1, 1,2, 1,3, 1,0 e 1,5. No banco, margem e alavancagem saem "não aplicável ao modelo banco".
  - Os outros 10 casos se comportam como o plano descreve:
    - unit com proventos 3× (1 ON + 2 PN);
    - abstenção só do indicador e do ano afetados (sem lucro, PL inicial zero, sem EBITDA, receita zero);
    - proventos de 2025 abstidos pelo calendário curto, e todos abstidos com a relação abstida;
    - cobertura 4/5 com a entrega depois do as_of;
    - 5/5 por publicação;
    - `comparavel = False` com o perímetro misto.
- **Conferência antes de gerar:** as saídas dos 10 casos foram lidas contra `qualidade._janela` e `_fonte`. A entrega em 21/10 é posterior ao dia de D (20/10), então o exercício sai da janela; a coleta por publicação vale mesmo depois do as_of. Na revisão 1, o teste do banco passou a afirmar também os lucros e a cobertura 5/5, e o provento de 2020 ganhou comentário. A coleta anterior à entrega na variante de entrega foi para `pendencias.md`.
- **Golden:** pelo predicado aprovado, as 2291 linhas antigas ficaram byte a byte iguais e na mesma ordem, e entraram só as 12 novas. O SHA passou de `1759c55f…` para `6ad83081…`, registrado em `docs/decisoes/predicados-golden-4.md`. Evidências em `outputs/F4-C10/`: o golden anterior e os dois SHAs.
- **Dificuldades:** `tests/test_analysis_service_as_of.py` (`_entrada_golden`) repete o montador de entradas do golden e passou a falhar no primeiro caso de Qualidade.
- **Como resolvi:** acrescentei o mesmo gancho, sem mudar nenhuma asserção. O arquivo não estava na lista do §5.
- **Testes:** suíte de 5418 para 5420 passed, 1 skipped, 24 xfailed. Os 12 casos novos rodam dentro dos testes existentes do golden.
- **Mutação:** não se aplica. O item só acrescenta casos de teste e apoio, sem código de produção.
- **Decisões que ficaram para o Marcos:** nenhuma.

### Checkpoint do bloco 0 — pedido da segunda rodada da R2
- **Executor:** claude-code (Opus 5.5)
- **Status:** parada no `[DECISÃO]` do checkpoint do bloco 0; a segunda rodada ainda não rodou
- **Fila curta concluída:** F4-C01 a F4-C10, mais a limpeza de caminhos dos relatórios (decisão 2 do Marcos de 25/11) e o requebro da docstring do F4-C09.
- **Segunda rodada (regra de rodadas: só o diff; só bloqueador reabre):** intervalo `2eac281..6a71281`, só commits do claude-code, auditados pela outra família, o codex: `python scripts/auditar.py codex fase --fase 4 --desde 2eac281`.
- **Revisão cruzada formal pedida ao codex nesta rodada** (decisão 3 do Marcos de 25/11): marcar "confere" ou "contesta" em `docs/loop/pendencias.md` para:
  - DD-97, já com a correção do F4-C02;
  - DD-98, o hash da renderização no F4-A11;
  - DD-99, o caso de contrato da auditoria no F4-C07;
  - DD-100, a caracterização sem mudança de código no F4-C08.
- **Depois:** se a rodada vier limpa, marcar o checkpoint do bloco 0 e liberar o bloco 1.

### F4-C11 — fix: never take a stock event species from an unreadable ISIN in the share factors
- **Executor:** claude-code (Opus 5.5)
- **Status:** [!] — parada da política §3 (teste protegido)
- **O que foi feito:** decisão do Marcos de 25/11, item entrado antes da segunda rodada. Em `fatores_acoes_b3._fator_do_par`, um ISIN ilegível fora do conjunto do emissor, dentro da janela de reconciliação, era descartado pela espécie ou pelo descarte legado do C3-03b. A correção de duas linhas o faz abster com "espécie do evento em ações não demonstrada", o mesmo motivo do C3-03b para ISIN não atribuível. Ela foi aplicada, rodada e revertida.
  - Regressão BUG-4-22: um evento próprio mais um alheio ilegível na janela (`BRALHEACNPA0` e `BRALHEACNOR0`). Os 2 casos nasceram xfail estritos (`outputs/F4-C11/regressao-antes.txt`) e passam com a correção. O controle mostra que o alheio legível continua descartado.
- **Dificuldades:** a leitura estrita (nenhum ISIN ilegível dá espécie) derruba 49 testes, pelas fixtures com ISINs próprios de dígito inválido, inclusive cinco regressões protegidas. Adotei a leitura restrita ao defeito da pendência: só o ISIN ilegível fora do conjunto do emissor. Mesmo assim, caem dois casos da regressão protegida BUG-3-60, cujo ISIN "do outro emissor", `BRLRENACNPR9`, tem dígito inválido.
- **Decisões que ficaram para o Marcos:**
  - Autorizar a troca só desse dígito (`BRLRENACNPR8`), com as asserções iguais.
  - Confirmar a leitura restrita da regra.
- **Nota de processo:** um patch com nome errado, que eu mesmo tinha acabado de criar em `outputs/`, foi apagado (`rm`). Era arquivo não rastreado; o correto fica em `outputs/F4-C11/`.

### Checkpoint do bloco 0 — pedido da segunda rodada da R2 (atualização)
- **Executor:** claude-code (Opus 5.5)
- **Status:** atualização do pedido de `57ef435`
- **O que mudou:** o F4-C11 entra antes da segunda rodada, por decisão do Marcos de 25/11, e está em `[!]`. A segunda rodada cobre o intervalo desde `2eac281` até o commit do F4-C11, quando ele sair: `python scripts/auditar.py codex fase --fase 4 --desde 2eac281`. A revisão cruzada formal pedida continua a mesma: DD-97, DD-98, DD-99 e DD-100. O Marcos aceitou o F4-C08 fechado por caracterização (DD-100), registrado em `pendencias.md`.

### F4-C11 (retomada) — segunda parada
- **Executor:** claude-code (Opus 5.5)
- **Status:** [!] — parada da política §3 (teste protegido)
- **O que foi feito:** com as decisões do Marcos de 25/11, a correção e a regressão BUG-4-22 foram aplicadas e o literal trocado por `BRLRENACNPR8`. Um dos dois casos do BUG-3-60 continuou falhando: `BRLRENACNPR8` é o ISIN real da PN da própria Lojas Renner (fixture oficial da B3). Todo ISIN legível com o corpo `BRLRENACNPR` tem esse dígito, então o "outro emissor" passa a ser o próprio emissor. Tudo foi revertido.
- **Alternativa conferida:** `BRLRE2ACNPR6`, legível, PN e com outro código de emissor. Com a correção, o BUG-3-60 passa inteiro; sem os dois descartes por emissor, os dois casos do outro emissor falham, como pede a condição de mutação manual do Marcos (`outputs/F4-C11/alternativa-BRLRE2ACNPR6.txt`).
- **Registros das decisões de 25/11:**
  - A leitura restrita foi confirmada. A diferença em relação ao Bazin e o motivo estão em `pendencias.md`: nos fatores, a pertença ao conjunto do emissor já prova a identidade; no Bazin, o conjunto pode faltar e a espécie decide o descarte.
  - A unificação dos dígitos das fixtures próprias ficou como pendência para o bloco 2.
  - O `rm` foi aceito como desvio.
- **Decisões que ficaram para o Marcos:** autorizar `BRLRE2ACNPR6` no lugar de `BRLRENACNPR8` como `ISIN_DO_OUTRO` do BUG-3-60, com as asserções iguais.

### F4-C11 (conclusão) — fix: never take a stock event species from an unreadable ISIN in the share factors
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-22, pelas decisões do Marcos de 25/11. Em `fatores_acoes_b3._fator_do_par`, um evento em ações na janela de reconciliação com ISIN ilegível **fora** do conjunto do emissor abstém com "espécie do evento em ações não demonstrada", pelo `pb.isin_legivel`, sem duplicar. O ISIN do conjunto do emissor tem a identidade provada pela pertença (leitura confirmada; a diferença em relação ao Bazin está em `pendencias.md`).
- **Fixture protegida:** `ISIN_DO_OUTRO` do BUG-3-60 passou de `BRLRENACNPR9` (dígito inválido) a `BRLRE2ACNPR6`, com as asserções iguais. O `BRLRENACNPR8`, autorizado antes, é o **ISIN real da PN da própria Renner** (fixture oficial da B3): todo ISIN legível com o corpo `BRLRENACNPR` tem esse dígito, e por isso ele não serve como "outro emissor".
- **Testes:**
  - Regressão BUG-4-22 (`tests/regressao/test_bug_4_22_isin_ilegivel_nos_fatores.py`): evento próprio mais um alheio ilegível na janela (`BRALHEACNPA0` e `BRALHEACNOR0`) abstém. Os 2 casos nasceram xfail estritos (`outputs/F4-C11/regressao-antes.txt`). O controle confirma que o alheio legível continua descartado.
  - Mutação manual (`outputs/F4-C11/alternativa-BRLRE2ACNPR6.txt`): com a correção, os 16 casos do BUG-3-60 passam; sem os dois descartes por emissor, os dois casos do outro emissor falham.
  - Suíte: 5423 passed, 1 skipped, 24 xfailed.
  - Mutação (`outputs/F4-C11/mutacao.txt`): `_fator_do_par` 130/154 = 84,4%. Os sobreviventes são do código anterior: chaves de deduplicação, textos de erro, guardas do fator acumulado e `continue` → `break`.
- **Resíduos:** evidências em `outputs/F4-C11/` e cache de mutação em `mutants/`.
- **Decisões que ficaram para o Marcos:** nenhuma. A segunda rodada da R2 (`python scripts/auditar.py codex fase --fase 4 --desde 2eac281`) passa a incluir este commit.

### Checkpoint do bloco 0 — resultado da segunda rodada da R2
- **Executor:** claude-code (Opus 5.5)
- **Status:** registro
- **Auditoria:** Codex, segunda rodada só do diff (`2eac281..f681c56`), com veredito "não pode seguir". O relatório está em `docs/loop/auditorias/bloco0-codex-2.md`, conferido para caminhos locais (nenhum, porque o auditor já citou caminhos relativos).
  - Bloqueios: (1) a versão da DFP se perde quando o seletor recua para o exercício anterior; (2) a CVM pode consumir o ZIP de outra execução depois da conferência do hash.
  - Os bloqueios do Bazin e do relatório técnico estão fechados.
- **Revisões cruzadas:** DD-97 contestada, com a regra atualizada pelo Marcos; DD-98 e DD-99 conferem; a DD-100 já tinha o aceite do Marcos.
- **Decisões do Marcos (25/11):** F4-C12 e F4-C13 na fila. As ressalvas vão para `pendencias.md`, para o bloco 2. Depois, a terceira rodada só sobre o diff dos dois itens, com o comando exato entregue ao Marcos antes de rodar.

### F4-C12 — fix: carry the proven DFP version when the selector falls back to the previous year
- **Executor:** claude-code (Opus 5.5)
- **Status:** sucesso
- **O que foi feito:** BUG-4-23, bloqueio 1 da segunda rodada da R2.
  - `CVMProvider.exercicio_e_versao_mais_recente` cobre também o recuo. Sem exercício do ano corrente comprovado, inclusive quando o ZIP do ano dá 404, procura no ZIP do exercício anterior a maior versão com `DT_RECEB < D`. Sem versão comprovada, levanta `ValueError` ("DFP do exercício anterior (...) sem versão entregue antes do corte"): a série se abstém e o snapshot fica sem CVM (`cvm_disponivel = False`).
  - A busca passou para `_versao_comprovada(arquivo, cd_cvm, referencia, ano)`, com o mesmo laço, agora parametrizado pelo ano, e o tratamento do 404 para `_dfp_do_ano`.
  - `exercicio_anual_mais_recente`, que devolve só o ano e serve às datas passadas (que leem pelo recorte do F3-3d), mantém a regra: sem exercício do ano comprovado, o anterior.
- **Testes:**
  - Regressão BUG-4-23 (`tests/regressao/test_bug_4_23_dfp_ano_anterior_fora_do_corte.py`), com corte em 16/06/2026 e o exercício 2025 com V1 entregue em 15/06 (R$ 100 mil) e V2 em 16/06 (R$ 900 mil). O seletor devolve (2025, "1"), e a cascata de hoje lê a V1 no snapshot e na série (antes, R$ 900 mil). Sem versão comprovada, abstém. Esses 3 casos nasceram xfail estritos (`outputs/F4-C12/regressao-antes.txt`).
  - O controle confirma que a API só do ano continua recuando.
  - Revisão 1: entraram dois testes, a cascata de hoje sem versão comprovada (`cvm_disponivel = False`, série abstida com o motivo, sem lucro) e o recuo com o ZIP do ano em 404. O efeito sazonal apontado pela revisão foi para decisão do Marcos em `pendencias.md`: de janeiro até a entrega da DFP do ano anterior, a análise de hoje fica sem CVM.
  - Suíte: 5429 passed, 1 skipped, 24 xfailed.
- **Mutação** (`outputs/F4-C12/mutacao-resumo.txt`): `exercicio_e_versao_mais_recente` 28/28; `exercicio_anual_mais_recente` 19/19; `_versao_comprovada` 79/80; `_dfp_do_ano` 15/17. Os sobreviventes, `getattr` sem padrão no 404 e `fim >= referencia`, que é equivalente no corte diário, são do código movido.
- **Decisões que ficaram para o Marcos:** uma, o efeito sazonal de janeiro a março na análise de hoje, em `pendencias.md`.

### F4-C13 — fix: only use the run's collection time for the bytes the consumer actually read
- **Executor:** codex (GPT-6)
- **Status:** sucesso
- **O que foi feito:** BUG-4-24, bloqueio 2 da segunda rodada da R2. O download da CVM mantém sob `.execucao` o ZIP privado da execução em um diretório por SHA-256, criado antes da troca atômica do destino compartilhado e associado ao destino após a publicação bem-sucedida. No caminho de cache válido, a execução continua usando sua cópia, quando existe. A cópia usa hardlink com fallback para cópia física, substitui a cópia privada anterior do mesmo conteúdo e remove diretórios com mais de 24 horas. O COTAHIST também pode receber a cópia privada porque usa o mesmo downloader; ele usa o hash do ZIP, sem coleta adiantada da proveniência. A data real continua no registro persistido.
- **IF.data:** o retorno recém-baixado já vinha da memória e a checagem do BUG-4-16 recusava a substituição no momento do download. A retomada reproduziu outro intercalamento, no cache fresco e no antigo: B é lido, A (marcado pela execução) é republicado antes do registro, e a coleta podia ser adiantada para B. O hash dos bytes lidos ou serializados segue até o registro no mesmo chamado. A proveniência devolvida por `capital` usa o registro produzido na leitura, em contexto próprio do chamado. Se esse registro tiver outro hash, o IF.data abstém com o motivo da troca.
- **DD-97 (decisão do Marcos de 25/11):** a coleta adiantada só vale para os bytes consumidos. O hash marcado deve bater com o registrado, o do arquivo e o consumido quando informado. Na divergência entre a marca e os bytes consumidos, vale a coleta real correspondente e a guarda normal decide, inclusive por abstenção.
- **Revisão cruzada:** DD-97 contestada no desenho anterior e atualizada pela decisão de 25/11; DD-98 confere (SHA do trecho renderizado no pai e em `c21306d`, com mudanças só na Carteira); DD-99 confere (banco vazio criado pelo teste, asserção preservada, e BUG-4-21 cobre o banco ausente). DD-100 já aceita pelo Marcos.
- **Regressão:** os três casos vermelhos originais constam de `outputs/F4-C13/regressao-antes.txt`. Os dois intercalamentos adicionais do IF.data ficaram xfail estritos contra o provedor anterior (`regressao-ifdata-antes.txt`). Os testes finais também verificam o controle sem troca, a remoção da cópia prévia no fallback, o limite estrito de 24 horas e a continuação da limpeza quando uma remoção falha.
- **Resíduos:** evidências locais em `outputs/F4-C13/` e cache do mutmut em `mutants/`.
- **Para o Marcos revisar:** a abstenção sazonal do F4-C12 e a vinculação por arquivo privado da CVM estão registradas para ratificação no checkpoint.
- decisão delegada DD-101: efeito sazonal na análise de hoje de companhia com exercício civil → manter a abstenção explícita da série e do snapshot CVM enquanto a DFP do exercício anterior não tiver versão com entrega comprovada antes do corte. A Qualidade perde essa série no período (classe 1, desempate 1; alternativa: recuar até o último exercício comprovado, o que muda a seleção). Provisória, para ratificação do Marcos no checkpoint.
- decisão delegada DD-102: identidade dos bytes consumidos da CVM → oferecer ao leitor o caminho privado por execução e SHA-256 do ZIP validado antes da publicação atômica. A proveniência confere o SHA-256 desse mesmo arquivo. Hardlink, com cópia quando indisponível; uma troca no destino compartilhado ou outro conteúdo baixado na mesma execução preserva os caminhos já entregues. Esta é a garantia por construção adotada no lugar de recalcular o hash em cada parser (classe 3, desempates 4 e 6; alternativas: passar os bytes e o hash por cada leitor ou abster diante de troca detectada). Revisão cruzada pela outra família e ratificação no checkpoint.
- **Revisão 1:** encontrou dois problemas. O caminho privado agora distingue conteúdos baixados na mesma execução, e o IF.data abstém quando os bytes lidos e os registrados divergem. Os três casos foram confirmados em xfail estrito contra o stage da primeira revisão (`outputs/F4-C13/regressao-revisao-antes.txt`).
- **Revisão 2:** confirmou os intercalamentos da primeira rodada e identificou que a coleta e o hash podiam vir de duas versões do caminho. O registro novo usa o mtime e o hash do mesmo descritor aberto. O teste intercala a troca na abertura e ficou xfail estrito contra o stage anterior (`outputs/F4-C13/regressao-revisao-2-antes.txt`). A limpeza por idade e a substituição de cópia do mesmo hash podem interromper a leitura; diante da indisponibilidade do ZIP, vale a abstenção permitida pelo aceite.
- **Revisão 3:** confirmou o vínculo entre mtime e hash e observou que uma publicação mal-sucedida podia deixar o caminho privado selecionado. O contexto agora só seleciona a cópia se a publicação terminar. Uma regressão confirma que, após a falha, a próxima chamada lê o cache público publicado pela outra execução. O teste ficou xfail estrito contra o stage anterior (`outputs/F4-C13/regressao-publicacao-antes.txt`).
- **Gate:** 5442 passaram, 1 pulado e 24 xfail esperados, incluindo o [e2e] de hoje e a equivalência. Ruff do CI e Ruff completo nos diretórios do protocolo passaram. Os arquivos alterados não acrescentam diagnósticos ao Ruff completo. Golden igual ao HEAD (SHA-256 `6ad8308191a7c971…`).
- **Triagem do mutmut:** em `baixar_arquivo` (82/115), os 33 sobreviventes são das linhas anteriores ao item. 22 alteram só logs; o 18 estende um laço que já encerra na tentativa final; o 53 muda só a mensagem de erro do ZIP; os demais exercitam timeout, streaming, tamanho dos blocos e validação CRC, fora da mudança da coleta. Em `_buscar` (71/92), cinco alteram só logs (51–55); o 5 muda o texto de erro legado e 20–21 mudam só o texto de erro novo. `UTF-8` e `utf-8` são equivalentes (34, 62, 81). Nos mutantes novos 11 e 13 a passagem do hash à proveniência é omitida, mas a checagem independente do hash que volta com o registro ainda valida o vínculo ou abstém. Timeout, diretório e escapamento JSON são legados (39, 42, 65, 67, 69, 76, 78, 79). O mutante 35 omitia o hash no cache válido e sobrevivia na rodada anterior. O controle sem troca entrou e matou esse mutante, que causava abstenção indevida (`outputs/F4-C13/mutante-buscar-35-controle.txt`).
- **Mutação:** os alvos da proveniência ficaram acima de 80%: `marcar_baixado` 36/36, `caminho_da_execucao` 8/8, `_limpar_copias_antigas` 8/8, `_lido_na_execucao` 28/31 (90,3%); `_registrar` do IF.data 28/30 (93,3%). Execução com dois filhos em `outputs/F4-C13/mutacao-codex-publicacao.txt`, com a edição de cada sobrevivente em `mutacao-triagem-codex.txt`.

### F4-C14 — fix: preserve the proven DFP reference and version in both readers
- **Executor:** claude-code
- **Status:** sucesso
- **O que foi feito:** BUG-4-25, bloqueio da terceira rodada da R2 do bloco 0. O seletor carrega exercício, versão e referência da DFP cuja entrega foi comprovada. Snapshot e série encaminham o mesmo par versão/referência para a leitura. A DRE deve conter o documento selecionado. Se ele estiver indisponível, o snapshot fica sem CVM e a série anual registra a abstenção. As interfaces anteriores de seleção por ano e por ano/versão continuam disponíveis.
- **Regressão [e2e]:** ZIPs sintéticos montados em memória, com parser e índice reais. No corte de 16/06/2026, ambos liam os R$ 900 mil de dezembro entregue em D e continuavam usando dezembro quando a DRE de setembro ficava indisponível. Os quatro xfails estritos foram confirmados antes da correção, inclusive com execução separada das asserções, em `outputs/F4-C14/`. Depois da correção, os quatro casos passam sem marca e verificam a referência de setembro, a versão 1, os R$ 100 mil e a abstenção quando a DRE comprovada some.
- **Complemento ao teste protegido BUG-4-23:** foi acrescentada apenas a asserção do lucro da linha de 2025 na série, preservando os literais e as asserções existentes.
- **Verificação:** gate, mutação com dois filhos e revisão do diff, com evidências em `outputs/F4-C14/`. Golden com SHA-256 `6ad8308191a7c971e6b9e609412c49aee799b57f0b4e5af2a51117b13f361007`.
- **Decisão delegada DD-101:** mantém a abstenção enquanto faltar prova de entrega anterior ao corte para a DFP do exercício anterior. A sonda do bloco 1 vai medir por data e companhia os quadros de Qualidade indisponíveis (`pendencias.md`).

### Checkpoint do bloco 0 — 26/11/2026
- **Executor:** codex
- **Status:** bloco 0 encerrado, sem bloqueador pendente na R2. O Gemini, de outra família que o executor registrado do F4-C14, deu «Pode seguir» na quarta rodada (`docs/loop/auditorias/bloco0-gemini-4.md`, intervalo `acebb0d..f110c5c`). A terceira rodada (`outputs/auditorias/auditoria-fase-4-codex-3-relatorio.md`) detectou a perda de referência corrigida no F4-C14. A revisão do Claude (chat) sobre o F4-C13 ficou sem bloqueador e recomendou a ratificação da DD-102.
- **Decisão do Marcos:** DD-97, DD-98, DD-99, DD-100, DD-101 e DD-102 ratificadas. Mantida a abstenção sazonal da DD-101. A sonda F4-D15 mede os quadros de Qualidade indisponíveis por data de análise e companhia, destacando essa causa. P1 já executado no F4-C10.
- **Bloco 1:** liberado em 26/11/2026 com duas semanas, até 10/12/2026. As três ressalvas do Gemini 4 ficam no bloco 2, em `pendencias.md`.

### F4-D01 — proposta da ficha FII 1.4
- **Executor:** codex
- **Status:** redação entregue. A fila para no [DECISÃO] do Marcos, antecipado conforme pedido de 26/11/2026.
- **Escopo:** proposta de continuidade histórica pelo Informe Mensal da CVM e COTAHIST, opções do P2 e P/VP descritivo. A ficha distingue a banda de VP medida no L2 da proposta de limiar de preço a validar.
- **Pendente:** preparar F4-D01b a F4-D01d quando o Marcos liberar a retomada, fazer a auditoria FICHA conjunta e obter aprovação escrita da ficha e do P2. Implementação na ordem já prevista na fila.
