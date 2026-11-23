Resumo Executivo da Auditoria (V2 — Fases 1 a 3, v2-fase-3)

Auditoria estática somente leitura das Fases 1 a 3 contra as 12 fichas metodológicas (docs/metodologia/), excluindo achados já registrados nas auditorias anteriores e nas heranças F4-H01 a F4-H16 (docs/loop/fila-fase4-proposta.md).

Contagem por severidade: 4 críticos, 11 médios, 3 baixos (18 achados no total).
Destaques críticos:
Quebra da análise corrente (dia == hoje) via AnalysisService.analisar / app.py: MarketEngine.buscar_dados_ticker_em carimba coletas da B3, SIDRA (IPCA), IF.data e CVM com datetime.now(UTC) após o as_of capturado na borda, fazendo as guardas anti-lookahead (coleta <= as_of, com por_publicacao=False hoje) absterem Graham, Bazin, Qualidade (proventos), Rendimento do FII e IF.data.
Teste do Terminal (test_app_analysis_service.py) só prova o Mock: Mock() não passa em _has_explicit_method("buscar_dados_ticker_em"), testando buscar_dados_ticker (sem as_of) em vez do caminho real de produção.
Guarda legada em FIIEngine.analisar: exige dados["dy"] (vindo do yfinance/brapi no caminho corrente) antes de ler o Informe Mensal da CVM e sobrescreve o DY da saída com o da cascata.
Vazamento PIT em proventos_b3.serie_12_meses: usa aprovacao > dia_as_of (aceitando provento sem hora aprovado no próprio dia D) e não filtra approvedOn nem isins_emissor em _evento_de_acoes_na_janela.
Achados Detalhados (em ordem de prioridade)
Achado 1 — Guarda legada de dados["dy"] bloqueia a lente Rendimento do FII antes do Informe CVM e polui a saída
Área: 1. Fidelidade às fichas / 3. Abstenção
Arquivo:linha: fii_engine.py, fii_engine.py, fii_engine.py, market_engine.py, market_engine.py
Problema: A ficha fii.md (v1.3, §§2–3) determina que o dividendYield do yfinance e da brapi não entra na lente Rendimento do FII, cujo único insumo de distribuição são os 12 meses do Informe Mensal da CVM. Na cascata corrente (MarketEngine.buscar_dados_ticker), _buscar_rendimento_fii preenche dados["informe_fii"] e dados["b3_fundo"], mas mantém em dados["dy"] o valor do yfinance/brapi (diferente do MotorHistorico._dy_do_informe em historico.py). Em FIIEngine.analisar (fii_engine.py), o motor valida dy, dy_confiavel = _normalizar_dy(dados.get("dy", 0)) e, se dy == 0 or not dy_confiavel, aborta na linha 155 com "DY ausente ou inválido" antes de chamar self._calcular_rendimento (linha 173). Quando não aborta, grava no dicionário final (linhas 208-209) "dy" e "dy_efetivo" vindos do yfinance/brapi em vez de dados["rendimento_fii_cvm"]["dy"].
Cenário de falha concreto: AnalysisService.analisar("HGLG11", as_of_hoje) → MarketEngine.buscar_dados_ticker("HGLG11") → _buscar_yfinance (info.get("dividendYield") vem None no Yahoo e BRAPI_TOKEN está desligado) → _buscar_rendimento_fii (coleta 13 meses válidos do Informe CVM em dados["informe_fii"]) → FIIEngine.analisar(dados, as_of=as_of_hoje) → dados.get("dy", 0) é 0 → linha 153 (if dy == 0 or not dy_confiavel:) retorna abstenção "DY ausente ou inválido" sem avaliar o Informe Mensal já coletado.
Severidade: crítico
Correção sugerida: Remover a guarda if dy == 0 or not dy_confiavel: de FIIEngine.analisar antes de _calcular_rendimento(dados, p, instante) (ou derivar dados["dy"] na cascata corrente via rendimento_fii.entradas / dy_entregue_ate, como faz MotorHistorico._dy_do_informe), de modo que a elegibilidade e o "dy" reportado dependam exclusivamente do Informe Mensal da CVM.
Achado 2 — Lente P/VP do FII (FiiNav) é calculada e descartada em FIIEngine.analisar
Área: 1. Fidelidade às fichas / 4. Ligação produtor→consumidor
Arquivo:linha: fii_engine.py, fii_engine.py, fii_nav.py, rastreabilidade.py
Problema: Em fii_engine.py, if pvp is not None: self._faixa_pvp(pvp, as_of=instante) chama _FII_NAV.calcular(...) e descarta o MethodResult devolvido. Os alertas de faixa (FAIXA_PREMIO_ALTO, FAIXA_PREMIO_MODERADO, FAIXA_DESCONTO) definidos em FiiNav nunca entram no retorno de FIIEngine.analisar, e até no relatório de rastreabilidade são suprimidos (rastreabilidade.py: if inst.nome != "P/VP do FII" else []). Além disso, quando a lente Rendimento do FII se abstém (fii_engine.py ou L176), FIIEngine.analisar retorna cedo sem incluir pvp nem selic_liquida no resultado (contrariando fii.md, §3, onde um FII de papel/híbrido abstido na lente de rendimento ainda tem P/VP e contexto descritivos).
Cenário de falha concreto: FIIEngine().analisar(dados_fii_papel_com_pvp_080, as_of=as_of) → _calcular_rendimento devolve Abstention("tipo de FII fora do escopo na 2B: papel") → fii_engine.py:176 retorna imediatamente sem resultado["pvp"], sem resultado["selic_liquida"] e sem chamar _faixa_pvp. Mesmo para FII de tijolo com pvp=1.20, _faixa_pvp(1.20) na linha 200 produz MethodResult(..., alertas=(FAIXA_PREMIO_ALTO,)) cujo valor de retorno é ignorado.
Severidade: médio
Correção sugerida: Preservar pvp e selic_liquida como contexto descritivo mesmo quando Rendimento do FII se abstém, e expor a faixa/alerta de FiiNav no contexto descritivo do resultado (ou aposentar formalmente _faixa_pvp se a decisão da Fase 2C for manter apenas o número bruto pvp).
Achado 3 — proventos_b3.ESPECIE_DO_ISIN omite ACNPC (PNC) e ACNPD (PND)
Área: 1. Fidelidade às fichas / 3. Abstenção
Arquivo:linha: proventos_b3.py, montagem.py, fatores_acoes_b3.py, backtest_pit.py
Problema: O FCA e o índice oficial reconhecem classes preferenciais PN[A-H] (montagem.py), mas ESPECIE_DO_ISIN em proventos_b3.py contém apenas {"ACNOR": "ON", "ACNPR": "PN", "ACNPA": "PNA", "ACNPB": "PNB"}. (Nota: discordância com evidência em relação a checkpoint-3-gemini.md, que deu PNC e PND como cobertos pelo BUG-3-45).
Cenário de falha concreto:
Em BacktestPIT._retornos (backtest_pit.py): para qualquer ativo com ISIN BR....ACNPC. ou BR....ACNPD., ESPECIE_DO_ISIN.get(isin[6:11]) retorna None e a linha 589 abstém o retorno total com "espécie do ticker não mapeada para proventos brutos", mesmo sem proventos no período.
Em fatores_acoes_b3._fator_do_par (fatores_acoes_b3.py) e proventos_b3._evento_de_acoes_na_janela (proventos_b3.py): se uma companhia tiver evento societário em classe PNC/PND, ESPECIE_DO_ISIN.get(isin[6:11]) é None e derruba também o cálculo das ações ON/PN da mesma companhia com "espécie do evento em ações não demonstrada".
Severidade: médio
Correção sugerida: Incluir "ACNPC": "PNC", "ACNPD": "PND" (e demais classes ACNPE..ACNPH previstas no padrão ISIN da B3 e em _CLASSE_PREFERENCIAL_NO_TEXTO) em proventos_b3.ESPECIE_DO_ISIN.
Achado 4 — Leituras de datetime.now(UTC) em MarketEngine após o as_of da borda fazem AnalysisService.analisar (app.py) abster as lentes no dia atual
Área: 2. Vazamento de futuro (relógio abaixo da borda) / 3. Abstenção
Arquivo:linha: app.py, analyze_asset.py, analyze_asset.py, market_engine.py, market_engine.py, market_engine.py, market_engine.py, market_engine.py, market_engine.py, ifdata.py
Problema: Quando AnalysisService.analisar(ticker, as_of) é chamado para o dia de hoje (dia == self.hoje, como em app.py:261-272 onde as_of = datetime.now(UTC) é capturado antes de iniciar a busca de dados), AnalysisService._executar (analyze_asset.py) detecta _has_explicit_method(mercado, "buscar_dados_ticker_em") == True e chama MarketEngine.buscar_dados_ticker_em(ticker, as_of) → buscar_dados_ticker(ticker, as_of=as_of). Como as_of é de hoje, _data_passada(as_of) (market_engine.py) é False, deixando disponibilidade_por_publicacao desligado (False). Em seguida, durante buscar_dados_ticker, o MarketEngine lê datetime.now(UTC) do relógio do sistema (segundos após as_of) para carimbar as coletas em:
_buscar_rendimento_fii (market_engine.py): provedor.coletar(cnpj, ticker, datetime.now(UTC)) → grava dados["b3_fundo"]["coleta"] > as_of;
_buscar_proventos_b3 (market_engine.py): agora = datetime.now(UTC); provedor.coletar(cd_cvm, agora) → grava dados["proventos_b3"]["coleta"] > as_of;
buscar_dados_ticker (market_engine.py): self._contexto_janelas(dados, as_of, coletado_em=datetime.now(UTC)) → MacroProvider().ipca_serie(exercicios, coletado_em) (L863) → grava dados["ipca_serie"]["coleta"] > as_of;
IFDataProvider.capital (ifdata.py) e downloads de ZIP da CVM (cvm_download.py): gravam data_coleta (datetime.now(UTC) ou mtime do arquivo recém-baixado) > as_of. Logo após, os consumidores (janelas_fundamentais.entradas, proventos_b3.entradas, qualidade_inputs._provento, rendimento_fii.entradas e valuation_engine._texto_inadimplencia) exigem coleta <= as_of (pois por_publicacao é False), rejeitando todas as coletas recém-feitas como "posteriores ao as_of"!
Cenário de falha concreto: No Terminal do Streamlit (app.py), o usuário clica em "Analisar" para ABEV3 (ou HGLG11):
t0 = as_of = datetime.now(UTC) (app.py:261).
MarketEngine.buscar_dados_ticker("ABEV3", as_of=t0) roda yfinance/CVM (~2s) e em t1 = t0 + 2s coleta proventos da B3 (market_engine.py:919) e IPCA do SIDRA (market_engine.py:587) com coleta = t1.isoformat().
janelas_fundamentais.entradas(dados, t0) (janelas_fundamentais.py) vê ipca["coleta"] (t1) > t0 e abstém Graham com "IPCA de fim de exercício indisponível: coleta sem fuso ou posterior ao as_of".
ValuationEngine.processar(dados, as_of=t0) → proventos_b3.entradas(dados, t0) (proventos_b3.py) vê bloco["coleta"] (t1) > t0 e abstém Bazin e Qualidade (proventos) com "relação de proventos da B3 sem data de coleta até o corte".
Para HGLG11, FIIEngine.analisar(dados, as_of=t0) → rendimento_fii.entradas(dados, t0) (rendimento_fii.py) vê b3["coleta"] (t1) > t0 e abstém Rendimento do FII com "complemento da B3 do fundo com coleta ausente, inválida ou posterior ao as_of".
Severidade: crítico
Correção sugerida: Na cascata corrente para o dia de hoje (dia == self.hoje), propagar o instante as_of da borda para os coletores (provedor.coletar(..., as_of), _contexto_janelas(dados, as_of) sem coletado_em=datetime.now(UTC), referencia.indice(as_of), cotahist.coletar(as_of)), eliminando as chamadas a datetime.now(UTC) dentro de MarketEngine e IFDataProvider.
Achado 5 — proventos_b3.serie_12_meses aceita provento aprovado no próprio dia D (aprovacao == dia_as_of) e não filtra approvedOn nem isins_emissor em eventos societários
Área: 2. Vazamento de futuro
Arquivo:linha: proventos_b3.py, proventos_b3.py, b3_proventos.py, b3_proventos.py
Problema: A ficha do Bazin (bazin.md, §3) determina que uma data sem hora na fonte B3 só entra após o fim daquele dia em Brasília (aprovacao < dia_as_of). O leitor do banco único (b3_proventos.proventos_ate na linha 627 e _aprovado_em_d_ou_depois na linha 742) descarta aprovacao >= dia. Porém, proventos_b3.serie_12_meses (proventos_b3.py) usa if aprovacao > dia_as_of: continue, permitindo que um provento com dateApproval == dia_as_of (sem hora) entre na soma de 12 meses. Além disso, _evento_de_acoes_na_janela (proventos_b3.py) não verifica approvedOn (deixando eventos aprovados em D ou depois bloquearem a janela quando serie_12_meses é chamada sem relacao_ate) nem filtra por isins_emissor (ao contrário de fatores_acoes_b3.py).
Cenário de falha concreto: ValuationEngine._insumos_bazin(dados, as_of) (valuation_engine.py) → proventos_b3.entradas(dados, as_of) (proventos_b3.py) → serie_12_meses(..., dia_as_of=dia_as_of): quando dados["proventos_b3"] vem de MarketEngine._buscar_proventos_b3 (market_engine.py:942-959), um registro com dateApproval igual ao dia local de as_of e lastDatePriorEx anterior passa pela linha 383 (aprovacao > dia_as_of é False) e é somado em d_bruto_12m.
Severidade: crítico
Correção sugerida: Em proventos_b3.serie_12_meses (proventos_b3.py), trocar if aprovacao > dia_as_of: por if aprovacao >= dia_as_of:. Em _evento_de_acoes_na_janela (proventos_b3.py), ignorar eventos com ler_data(evento.get("approvedOn")) >= dia_as_of e filtrar por isins_emissor quando presente.
Achado 6 — config.get_taxa_real lê datetime.now(UTC) para escolher entre banco e rede e compartilha _taxa_real_cache sem chave de banco
Área: 2. Vazamento de futuro
Arquivo:linha: config.py, config.py
Problema: Em config.py, get_taxa_real(as_of=..., janela=...) chama agora = datetime.now(UTC) e define passado = _dia_sp(instante) < _dia_sp(agora) pelo relógio do sistema. Além disso, o cache global _taxa_real_cache usa apenas (janela, _dia_sp(instante)) como chave e calcula idade = (instante - coleta).total_seconds() (onde coleta é o instante da primeira chamada que preencheu o cache, e não o relógio de expiração). Se get_taxa_real for chamado para uma data passada (janela, D) antes da carga de series_macro (ou com outro banco), a abstenção {"abstencao": "series_macro sem NTN-B até a data"} fica presa em _taxa_real_cache[(janela, D)] e é devolvida em chamadas subsequentes no mesmo processo.
Cenário de falha concreto: Chamada 1: get_taxa_real(as_of=datetime(2022, 3, 31, 15, tzinfo=UTC), janela=j) com series_macro vazio grava (instante, {"abstencao": "series_macro sem NTN-B até a data"}) em _taxa_real_cache[(j, date(2022, 3, 31))] (config.py). Chamada 2 (após carregar series_macro no banco): get_taxa_real(as_of=datetime(2022, 3, 31, 18, tzinfo=UTC), janela=j) calcula idade = 10800 (0 <= idade < 86400) na linha 178 e retorna a abstenção em cache da linha 179 sem consultar o banco.
Severidade: médio
Correção sugerida: Não cachear leituras históricas de series_macro (_taxa_real_do_banco) no cache de TTL de rede _taxa_real_cache, e receber a referência de hoje (ou usar exclusivamente macro.registro_do_banco no caminho histórico).
Achado 7 — fatores_acoes_b3._fator_do_par valida espécie do ISIN antes de descartar ISIN de outro emissor (raiz reciclada)
Área: 3. Abstenção
Arquivo:linha: fatores_acoes_b3.py
Problema: Em fatores_acoes_b3._fator_do_par, o filtro if isin not in isins: continue (adicionado no BUG-3-60 para ignorar eventos de outro emissor que usou a mesma raiz de 4 letras no passado) foi colocado nas linhas 114–119, depois da validação de espécie nas linhas 106–108 (classe = pb.ESPECIE_DO_ISIN.get(isin[6:11]); if classe is None: raise ValueError("espécie do evento em ações não demonstrada")).
Cenário de falha concreto: janelas_fundamentais.entradas(dados, as_of) (janelas_fundamentais.py) → fatores_da_relacao (fatores_acoes_b3.py) → _fator_do_par: se a relação de eventos da raiz de 4 letras trouxer um evento de outro emissor cujo isinCode seja de unit/certificado (BR....UNT... ou BR....CDA...) ou classe ACNPC, pb.ESPECIE_DO_ISIN.get(isin[6:11]) é None na linha 106 e levanta ValueError("espécie do evento em ações não demonstrada") na linha 108 antes de chegar ao if isin not in isins: continue da linha 116, abstendo indevidamente Graham e Lynch.
Severidade: médio
Correção sugerida: Mover o bloco if isins is not None: ... if isin not in isins: continue (linhas 114–119) para imediatamente após a validação de formato do isin (linha 105), antes de consultar ESPECIE_DO_ISIN.
Achado 8 — CVMProvider.exercicio_anual_mais_recente não verifica DT_RECEB < referencia para exercício social não civil
Área: 2. Vazamento de futuro / 3. Abstenção
Arquivo:linha: cvm_provider.py, market_engine.py, market_engine.py
Problema: CVMProvider.exercicio_anual_mais_recente(cd_cvm, referencia) seleciona fim.year quando encontra na DRE_con um exercício de 12 meses com fim.year == referencia.year and fim <= referencia (cvm_provider.py), sem verificar se o documento foi entregue antes de referencia (DT_RECEB < referencia).
Cenário de falha concreto: Companhia com exercício social encerrado em 31/03/2026 e DFP entregue em 15/06/2026. Se CVMProvider (sem _Recorte, por exemplo via MarketEngine._serie_cvm quando _recorte_em não é ativado ou em chamada direta a _serie_cvm com as_of = 2026-05-01) consulta exercicio_anual_mais_recente(cd_cvm, date(2026, 5, 1)), fim (2026-03-31) <= referencia (2026-05-01) é verdadeiro e a função retorna ano_final = 2026. Em seguida, calcular_indicadores(cd_cvm, anos=1, ano_final=2026) lê a DFP de 2026 (entregue apenas em 15/06/2026) para os múltiplos correntes (roe, lpa, vpa, pl, pvp), enquanto gordon_do_documento e janelas_fundamentais se abstêm na guarda de data_entrega < dia em vez de usar o exercício vigente em 01/05/2026 (2025).
Severidade: médio
Correção sugerida: Em exercicio_anual_mais_recente, conferir no índice de entregas (self._entregas(arquivo)) se a DFP do exercício encerrado em referencia.year possui DT_RECEB < referencia.isoformat() antes de retornar fim.year.
Achado 9 — BacktestPIT._retornos não filtra sem_prova nem eventos sem data_ex pela espécie/ISIN do ticker (ausente de fila-fase4-proposta.md)
Área: 3. Abstenção
Arquivo:linha: backtest_pit.py, backtest_pit.py, serie_ajustada.py
Problema: Em BacktestPIT._retornos:
Nas linhas 613–621, o laço for item in relacao.get("sem_prova", []): bloqueia o retorno se qualquer item de sem_prova do emissor cair em [inicio, corte_com), sem filtrar item.get("especie") == especie_esperada (um provento sem prova de PN bloqueia o retorno da ON).
Nas linhas 629–650, os laços for evento in eventos_lidos["sem_prova"]: e if ex is None: bloqueiam o retorno sem filtrar evento.get("isin") == isin — ao contrário de serie_ajustada.serie_do_banco (serie_ajustada.py), que já filtra e.get("isin") == isin tanto em eventos quanto em sem_prova. (Nota: apontado na revisão do checkpoint 3, mas omitido das heranças F4-H01 a F4-H16 em docs/loop/fila-fase4-proposta.md).
Cenário de falha concreto: BacktestPIT.executar → _retornos("ITUB3", ...) (isin = "BRITUBACNOR0"): se b3_proventos.eventos_ate devolver um evento em sem_prova (ou sem data_ex) exclusivo da preferencial BRITUBACNPR3 no horizonte [D, T), as linhas 629–650 abstêm o retorno de ITUB3 com "evento em ações sem prova no horizonte".
Severidade: médio
Correção sugerida: Filtrar relacao["sem_prova"] por item.get("especie") in (None, "", especie_esperada) e eventos_lidos["sem_prova"] / ex is None por isin is None or evento.get("isin") in (None, "", isin) (e registrar a herança na fila da Fase 4).
Achado 10 — test_app_analysis_service.py usa Mock() para MarketEngine e testa um caminho que não roda em produção
Área: 4. Ligação produtor→consumidor / 5. Qualidade dos testes
Arquivo:linha: test_app_analysis_service.py, test_app_analysis_service.py, analyze_asset.py, analyze_asset.py
Problema: Em AnalysisService._executar (analyze_asset.py), o serviço decide entre mercado.buscar_dados_ticker_em(ticker_norm, as_of) e mercado.buscar_dados_ticker(ticker_norm) usando self._has_explicit_method(mercado, "buscar_dados_ticker_em"). Em produção (app.py), market é instância de MarketEngine, que possui buscar_dados_ticker_em em vars(MarketEngine), portanto app.py sempre chama buscar_dados_ticker_em(ticker, as_of). Já em test_app_analysis_service.py, mercado é um unittest.mock.Mock() genérico sem buscar_dados_ticker_em em mercado.__dict__, fazendo _has_explicit_method retornar False e o teste exigir na linha 273 mercado.buscar_dados_ticker.assert_called_once_with("TSTA3")!
Cenário de falha concreto: O teste de integração do Terminal (test_terminal_chama_entrada_temporal_e_persiste_uma_vez) passa 100% verde provando a chamada a buscar_dados_ticker("TSTA3") no Mock, enquanto em produção o clique no botão "Analisar" de app.py chama buscar_dados_ticker_em("TSTA3", as_of) e sofre o bug descrito no Achado 4.
Severidade: crítico
Correção sugerida: Configurar o dublê de MarketEngine em test_app_analysis_service.py com buscar_dados_ticker_em explícito (ou create_autospec(MarketEngine)) e incluir um teste fim-a-fim de AnalysisService.analisar para dia == hoje com MarketEngine real (fontes HTTP mockadas na borda).
Achado 11 — CVMProvider.calcular_indicadores calcula e grava divida_pl sem nenhum consumidor
Área: 4. Ligação produtor→consumidor / 8. Arquitetura e dívida
Arquivo:linha: cvm_provider.py, cvm_provider.py, cvm_provider.py, market_engine.py
Problema: CVMProvider.calcular_indicadores continua calculando ind["divida_pl"] = (passivo_total - pl) / pl (cvm_provider.py) em todos os anos e companhias, embora a métrica tenha sido aposentada no F2A-8 (F-12) e removida de _CVM_TO_MARKET. Nenhum consumidor no repositório lê divida_pl.
Cenário de falha concreto: A cada chamada de calcular_indicadores (inclusive nos 5 exercícios de indicadores_da_serie), ind["divida_pl"] é computado e armazenado no dicionário de retorno sem nunca ser lido.
Severidade: médio
Correção sugerida: Remover a chave morta divida_pl de CVMProvider.calcular_indicadores (ajustando o teste de caracterização em test_cvm_provider.py se necessário).
Achado 12 — Golden (golden_motores.jsonl) exercita Qualidade sempre com 0 observações nos 5 indicadores
Área: 5. Qualidade dos testes
Arquivo:linha: golden_motores.py, apoio_janelas.py, golden_motores.jsonl
Problema: Em apoio_janelas.py (usado por enriquecer_gordon em toda a grade de ações de golden_motores.py), os 5 exercícios sintéticos de serie_cvm["exercicios"] contêm apenas lpa e vpa, sem lucro_controladores, pl_inicial_controladores, lucro_liquido, receita_liquida, divida_liquida, ebitda nem calendario_proventos_b3. Como resultado, em todos os casos do golden_motores.jsonl, o quadro saida["qualidade"] tem "observados": 0 e valores null para todos os 5 indicadores (roe, lucros, margem_consolidada, alavancagem e proventos).
Cenário de falha concreto: Se uma regressão alterar qualquer fórmula numérica de Qualidade (por exemplo, trocar desvio padrão populacional por amostral em qualidade.py, ou inverter divida_liquida / ebitda), test_acoes_iguais_ao_golden em test_equivalencia_motores.py passará sem detectar nenhuma diferença.
Severidade: médio
Correção sugerida: Quando houver regeneração autorizada do golden na Fase 4, enriquecer casos da grade com insumos contábeis completos de 5 anos (lucro_controladores, pl_inicial_controladores, lucro_liquido, receita_liquida, divida_liquida, ebitda e calendario_proventos_b3) para que o golden proteja também os valores numéricos de Qualidade.
Achado 13 — Chamadas duplicadas consecutivas a verificar_lentes(result) em testes de FIIEngine
Área: 5. Qualidade dos testes
Arquivo:linha: test_fii_engine.py, test_fii_engine.py, test_fii_engine_pvp.py, test_fii_engine_rendimento.py
Problema: Durante a remoção de score_final na Fase 2C, antigas asserções de score/recomendação foram substituídas mecanicamente por chamadas a verificar_lentes(...), deixando chamadas idênticas duplicadas em linhas consecutivas (verificar_lentes(result) seguido imediatamente de verificar_lentes(result) nas linhas 44–45 de test_fii_engine.py e 81–82 de test_fii_engine_rendimento.py).
Cenário de falha concreto: A segunda chamada consecutiva executa exatamente as mesmas asserções sobre o mesmo dicionário sem acrescentar cobertura.
Severidade: baixo
Correção sugerida: Remover as linhas duplicadas de verificar_lentes nos três arquivos de teste.
Achado 14 — DatabaseManager.adicionar_posicao não valida ticker pela allowlist da B3 nem finitude do preço
Área: 6. Segurança e operação
Arquivo:linha: database.py, app.py
Problema: Enquanto MarketEngine, BrapiProvider, SentinelaAI e rastreabilidade validam o ticker com sentinela.domain.ticker.normalizar/validar (^[A-Z0-9]{4}(?:[3456]|11)$), DatabaseManager.adicionar_posicao (database.py) faz apenas ticker = ticker.upper().strip(), aceitando string vazia, texto fora do padrão da B3 ou preco não finito (NaN/inf) ou <= 0 em chamadas diretas à API do banco. Além disso, adicionar_posicao e remover_posicao não capturam sqlite3.Error (diferente de salvar_analise na linha 142).
Cenário de falha concreto: Na aba Carteira (app.py), se o usuário clicar em "Salvar" com o campo "Ticker" em branco ("") ou com um texto inválido ("INVALIDO"), db.adicionar_posicao("", 1, 0.01) grava uma linha com ticker = "" em carteira_real, e em seguida o loop das linhas 486–489 tenta buscar cotação para "" a cada recarregamento da aba.
Severidade: médio
Correção sugerida: Validar ticker com sentinela.domain.ticker.validar(ticker) (ou normalizar) e exigir isinstance(qtd, int) and not isinstance(qtd, bool) and qtd != 0 e math.isfinite(preco) and preco > 0 (quando qtd > 0) em DatabaseManager.adicionar_posicao.
Achado 15 — auditoria.py lê o banco legado sentinela_v6.db e grava dados da carteira real na raiz do repositório em vez de outputs/
Área: 6. Segurança e operação
Arquivo:linha: auditoria.py, auditoria.py, auditoria.py, auditoria.py
Problema: auditoria.py define DB_PATH = "sentinela_v6.db" (linha 62) em vez de sentinela.data.store.unico.caminho_padrao() (sentinela_store.db). Além disso, auditar_banco() (linhas 469–485) lê todas as posições de carteira_real e main() (linhas 689–707) grava auditoria_YYYYMMDD_HHMMSS.txt e .json no diretório de trabalho atual (raiz do projeto) em vez de outputs/, onde ficam todos os demais artefatos sensíveis (rastreabilidade, backup, backfill, banda_neutra_fase3).
Cenário de falha concreto: Ao rodar python auditoria.py, o script ignora o banco único sentinela_store.db migrado na Fase 3 (lendo sentinela_v6.db antigo ou falhando se já removido) e cria dois arquivos com as posições reais da carteira diretamente na raiz do workspace.
Severidade: baixo
Correção sugerida: Usar unico.caminho_padrao() em auditoria.py, gravar a saída dentro de outputs/auditoria/ e omitir (ou mascarar sob flag explícita) os dados individuais de carteira_real.
Achado 16 — Documentação desatualizada ou contraditória com o código em README.md, AGENTS.md, CLAUDE.md, data_quality.py e test_contratos_import.py
Área: 7. Documentação contra o código
Arquivo:linha: README.md, README.md, README.md, AGENTS.md, CLAUDE.md, data_quality.py, data_quality.py, test_contratos_import.py
Problema:
README.md ainda documenta a arquitetura da V1: cita fundamentus_scraper.py e portfolio_engine.py (arquivos que não existem mais), score único 0-100 com recomendação, Markowitz 40/60, Python 3.10+ e banco sentinela_v6.db.
AGENTS.md e CLAUDE.md afirmam que BRAPI_TOKEN "falta no .env.example", mas .env.example já declara BRAPI_TOKEN=.
AGENTS.md e CLAUDE.md afirmam que sentinela/services/ está "implementada, não conectada" ao app.py, quando app.py já usa AnalysisService.analisar desde o item F3-6b.
data_quality.py e L38-L39 afirmam que market_engine.py não preserva valores pré-merge e que lpa/vpa da CVM dependem de sharesOutstanding do yfinance, quando o próprio módulo lê valores_por_fonte (data_quality.py) e lpa/vpa vêm da DRE e Composição do Capital da CVM.
test_contratos_import.py diz no docstring que config "faz rede no import", comportamento eliminado no F3-1a.
Cenário de falha concreto: Um executor ou usuário que siga AGENTS.md:166 / CLAUDE.md:59 assumirá que AnalysisService não roda no app.py, ou que o projeto aceita Python 3.10 (README.md:3) embora o código use sintaxe PEP 695 (class CacheCopia[T]: em cache_leitura.py, exclusiva do Python 3.12+).
Severidade: médio
Correção sugerida: Atualizar README.md, AGENTS.md, CLAUDE.md e os docstrings de data_quality.py e test_contratos_import.py para refletir o estado real pós-Fase 3.
Achado 17 — auditoria.py classifica FII pelo sufixo '11' e duplica cálculos de TechnicalEngine
Área: 8. Arquitetura e dívida
Arquivo:linha: auditoria.py, auditoria.py, asset_classifier.py
Problema: Em auditoria.py, o roteamento FII vs. Ação ainda usa a regra legada '11' in ticker and 'SA' not in ticker and ticker not in UNITS_CONHECIDAS (com o comentário "idêntico ao app.py", que já usa AssetClassifier.is_fii(ticker, dados) em app.py). Isso viola a regra arquitetural (F2A-20 / Armadilha 14) de nunca inferir classe pelo sufixo 11. Além disso, auditar_tecnica (auditoria.py) recalcula manualmente RSI, MA50 e MA200 em vez de delegar a TechnicalEngine.calcular_indicadores.
Cenário de falha concreto: Ao rodar python auditoria.py BOVA11 (ETF) ou uma Unit nova terminada em 11 fora de UNITS_CONHECIDAS, auditoria.py:657 classifica o ativo como is_fii = True pelo sufixo '11' e o envia ao FIIEngine, enquanto app.py e AnalysisService o classificam pelo índice oficial (AssetClassifier).
Severidade: médio
Correção sugerida: Substituir a heurística das linhas 650–662 de auditoria.py por AssetClassifier().is_fii(ticker, dados) e reutilizar TechnicalEngine().calcular_indicadores(hist) em auditar_tecnica.
Achado 18 — Mapas manuais aposentados (cvm_fii_map.py, cvm_ticker_map.py) em [tool.mutmut] source_paths e comentários obsoletos em vulture_whitelist.py
Área: 8. Arquitetura e dívida
Arquivo:linha: pyproject.toml, cvm_fii_map.py, cvm_ticker_map.py, vulture_whitelist.py
Problema: cvm_fii_map.py e cvm_ticker_map.py não têm mais leitor em produção desde o F2A-31, mas permanecem em source_paths do [tool.mutmut] (pyproject.toml). Em vulture_whitelist.py, permanecem exceções e comentários de código já removido ou já conectado (_.max_age_days de buscar_fundamentos_cache, removido no F3-9b, e o comentário "ainda desconectada; o F3-6 liga ao app").
Cenário de falha concreto: Uma varredura global do mutmut gera mutantes em cvm_fii_map.py e cvm_ticker_map.py (dicionários estáticos sem uso em produção), e vulture_whitelist.py mascara max_age_days que já não existe mais em test_market_engine.py.
Severidade: baixo
Correção sugerida: Retirar cvm_fii_map.py e cvm_ticker_map.py de source_paths no pyproject.toml (ou movê-los para also_copy até sua remoção definitiva) e limpar _.max_age_days e o comentário do F3-6 em vulture_whitelist.py.
O que não foi coberto (não verificado)

Por restrição estrita das regras da auditoria (somente leitura e proibição de abrir .env, *.db, *.log e outputs/):

Conteúdo e integridade dos bancos locais (sentinela_store.db, sentinela_v6.db, sentinela.db) e artefatos em outputs/: não verificado (proibido abrir *.db e outputs/).
Presença ou validade de chaves em .env e conteúdo de sentinela.log / tests/sentinela.log: não verificado (proibido abrir .env e *.log).
Execução dinâmica da suíte pytest e score de mutação (mutmut) em tempo real: não verificado (auditoria estática somente leitura, sem escrita de caches ou artefatos de execução).

(A tarefa em segundo plano de listagem de arquivos concluiu sem impacto nos achados; o relatório completo da auditoria está na mensagem acima.)