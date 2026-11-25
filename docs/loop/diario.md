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
