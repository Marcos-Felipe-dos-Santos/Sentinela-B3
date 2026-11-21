Auditoria da Fase 3 — Gemini (somente leitura, commit 9b0e74c)

Leitura prévia concluída: AGENTS.md, CLAUDE.md, politica-decisao-autonoma.md, backtest.md, auditoria-f3.md e diagnostico-cobertura-f3.md.

Os achados abaixo são exclusivamente novos em relação a auditoria-f3.md e diagnostico-cobertura-f3.md, ou registram discordância com evidência de código sobre diagnósticos daqueles dois arquivos.

Área A — Vazamento de futuro e corte ponto-no-tempo em analisar(ticker, as_of) e no backtest
Achado A1 — remontagem.zip_informe_em ignora leitura.informe_fii e o parâmetro modo, permitindo recuo silencioso para mês anterior quando há reapresentação após D (e vazamento de VPA/P/VP na cascata direta com as_of)
Área: A (Informe de FII / corte temporal em as_of)
Arquivo:linha:
remontagem.py:185-223
leitura.py:405-507
historico.py:125-147
rendimento_fii.py:208-263
cvm_fii_provider.py:165-204
Problema:
Em leitura.py:405-507, leitura.informe_fii e leitura._versoes_do_informe implementam as guardas de reapresentação e conflito do Informe Mensal (MOTIVO_ENTREGA_POSTERIOR quando uma referência só tem Versao > 1 entregue após D, MOTIVO_VERSAO_NAO_VISTA, MOTIVO_GERAL_EM_CONFLITO, MOTIVO_SEM_GERAL, MOTIVO_ENTREGA_ILEGIVEL e AVISO_EXPLORATORIO). Porém, remontagem.py:185-223 (zip_informe_em) não chama leitura.informe_fii nem usa o argumento modo: faz um SELECT próprio (remontagem.py:201-216) que filtra apenas leitura._antes(entrega, dia) e omite silenciosamente do ZIP qualquer (cnpj, dt_refer, versao) entregue em ou após D, sem gravar linha sentinela nem devolver motivos para riscos_dados.
Além disso, quando MarketEngine.buscar_dados_ticker_em(ticker, as_of) é chamado diretamente (fora do MotorHistorico), _buscar_cvm usa cvm.recorte_em(as_of), mas CVMFIIProvider.obter_dados_fii(cnpj, as_of=as_of) (cvm_fii_provider.py:165-196) usa as_of apenas para escolher [ano_atual, ano_atual - 1] e ordena Data_Referencia decrescente sem filtrar Data_Referencia < dia nem Data_Entrega < dia.
Cenário de falha concreto:
(a) No MotorHistorico e no backtest: Em D = 2023-06-30, um FII teve o Informe de 2023-05-01 entregue originalmente antes de D (Versao = 1), mas reapresentado na Versao = 2 em 2023-08-15 (a fonte aberta da CVM guarda apenas a última versão, DD-34). zip_informe_em descarta 2023-05-01 do ZIP. Em seguida, rendimento_fii.py:217-225 (dy_entregue_ate) e rendimento_fii.py:255-263 (avaliar) tomam final = max(meses) = 2023-04-01 (idade de 2 meses <= IDADE_MAXIMA_MESES = 3) e calculam DY e valor justo sobre a janela deslocada [2022-05..2023-04] em vez de abster com MOTIVO_ENTREGA_POSTERIOR. Já CVMFIIProvider.obter_dados_fii (cvm_fii_provider.py:187-204) não tem nem guarda de idade de 3 meses: recua para qualquer mês anterior de ano_atual ou ano_atual - 1 e calcula vpa e pvp defasados. E se modo="exploratorio" for pedido, zip_informe_em continua excluindo a versão 2 em vez de incluí-la com AVISO_EXPLORATORIO.
(b) Na cascata direta com as_of: MarketEngine().buscar_dados_ticker_em("HGLG11", datetime(2026, 3, 15, tzinfo=UTC)) lê o ZIP de 2026 e extrai valor_cota (vpa) e pvp do mês mais recente do arquivo (ex.: outubro de 2026), vazando futuro.
Severidade: bloqueante (resultado numérico errado por recuo silencioso de janela sem abstenção no histórico, modo exploratório inoperante para FII e vazamento de futuro de VPA/P/VP em obter_dados_fii).
Correção sugerida: Fazer zip_informe_em delegar a seleção por (cnpj, dt_refer) à mesma regra de leitura._versoes_do_informe / leitura.informe_fii respeitando modo, preservando no ZIP remontado (ou nos motivos devolvidos ao MotorHistorico) a indicação de que a referência mais recente até D teve entrega posterior/conflito para que rendimento_fii e obter_dados_fii se abstenham naquela referência em vez de recuar para mês anterior; e aplicar o corte _mes_encerrado + Data_Entrega < dia também em CVMFIIProvider.obter_dados_fii.
Achado A2 — Documento CVM retido no índice sem números (DD-57 / reapresentação posterior) não abstém exercicio_anual_mais_recente, _acumulados_do_arquivo (TTM) nem calcular_indicadores, recuando para período anterior
Área: A (Demonstrações CVM / corte em as_of)
Arquivo:linha:
remontagem.py:10-12 e remontagem.py:104-160
cvm_provider.py:562-579, cvm_provider.py:761, cvm_provider.py:1099-1120 e cvm_provider.py:1293-1330
series_cvm.py:336-351
Problema: O docstring de remontagem.py:10-12 estabelece o contrato: "Documento que o leitor deixa fora (versão vigente sem números na fonte aberta, conflito da carga, DD-57) continua no índice e fica sem números: a cascata o vê e se abstém dele, em vez de voltar a um documento anterior." Porém, em cvm_provider.py, apenas composicao_mais_recente (cvm_provider.py:761) lê o índice de entregas (self._entregas(zip_path)) para escolher (DT_REFER, VERSAO). Os demais leitores escolhem (DT_REFER, VERSAO) diretamente das linhas de contas (DRE_con, BPP_con, DVA_con).
Cenário de falha concreto:
No TTM (_acumulados_do_arquivo + series_cvm.ttm): Em D = 2023-11-30, uma companhia entregou o ITR do 3T2023 (2023-09-30, versão 1) em 2023-11-10, mas reapresentou a versão 2 em 2024-02-15 (ou teve conflito em conflitos_carga). O ZIP de ITR 2023 remontado por zip_cia_em traz 2023-09-30 no CSV de índice (itr_cia_aberta_2023.csv), mas sem linhas em DRE_con. Como _acumulados_do_arquivo (cvm_provider.py:1293-1330) lê só DRE_con/DVA_con e ignora self._entregas(zip_path), 2023-09-30 desaparece da lista de acumulados e series_cvm.ttm (series_cvm.py:341-350) toma encerrados[-4:] = [3T2022, 4T2022, 1T2023, 2T2023] — quatro trimestres contíguos encerrados em 2023-06-30 — calculando roe, pl e divida_liq_ebitda defasados em um trimestre sem abster.
Em exercicio_anual_mais_recente (cvm_provider.py:1099-1120): Para companhia de exercício social encerrado no próprio ano de D (ex.: 2024-03-31 entregue em maio/2024 antes de D = 2024-06-30, reapresentado após D), DRE_con de 2024 fica vazia para o CNPJ; exercicio_anual_mais_recente não consulta _entregas, não vê a entrega de 2024 e recua ano_final para 2023 (referencia.year - 1), deslocando a janela de 5 exercícios de [2020..2024] para [2019..2023].
Em calcular_indicadores (cvm_provider.py:562-579): Se a companhia tiver duas DT_REFER na DFP do mesmo ano (mudança de exercício social) e a mais recente estiver apenas no índice sem números, pd.concat([bpa_emp, bpp_emp, dre_emp]) seleciona a DT_REFER anterior do mesmo ano.
Severidade: bloqueante (resultado errado por recuo silencioso para período anterior quando o documento vigente em D foi reapresentado após D ou teve conflito de carga).
Correção sugerida: Consultar self._entregas(zip_path) em _acumulados_do_arquivo, exercicio_anual_mais_recente e calcular_indicadores: se existir no índice do arquivo (ou via recorte_em) entrega com DT_RECEB < dia cujo (DT_REFER, VERSAO) não possui linhas nas demonstrações, registrar o período como bloqueado/indisponível e abster a série/TTM/indicador em vez de recuar para períodos anteriores.
Achado A3 — BacktestPIT._estado_terminal consulta o FCA com date.max sem limitar a fim (nem a self.hoje), vazando Data_Fim_Negociacao e entregas posteriores ao horizonte T
Área: A / C (Vazamento de futuro no estado terminal do backtest)
Arquivo:linha:
backtest_pit.py:691-743
Problema: Em _estado_terminal, a linha 692 chama universo._fca_por_referencia(self.conn, date.max.isoformat()) e a linha 701 escolhe apenas a maior referencia de todos os tempos (max(por_ref)) em que (cnpj, codigo) apareceu no FCA, sem filtrar entregas até fim (T) nem verificar se data_fim <= fim. Em seguida, as linhas 739–742 definem:
python
suspensao_confirmada = (
    not preco_final_disponivel
    and deslistagem is None
    and (data_fim is not None or referencia_atual >= fim)
)
Cenário de falha concreto:
Um ativo analisado em D = 2020-06-30 com horizonte de 12 meses (fim = T = 2021-06-30) não teve negócio no pregão T (preco_final_disponivel = False). Em 2022-03-15 (9 meses depois de T), a companhia encerra a negociação (data_fim = 2022-03-15 > fim). Como data_fim > fim, deslistagem fica None (linha 738), mas data_fim is not None é True (e referencia_atual é de 2022 >= fim)! O código usa um evento de 2022 (posterior a T) para ativar suspensao_confirmada = True em 2021-06-30.
Inversamente, se a companhia tinha Data_Fim_Negociacao = 2021-04-10 (<= T) no FCA entregue até T, mas num FCA entregue anos depois (ex.: 2023) o campo Data_Fim_Negociacao veio em branco numa linha histórica, max(por_ref) sobrescreve o estado vigente em T com o FCA de 2023.
Severidade: bloqueante (vazamento de futuro após T na determinação de deslistagem e suspensão do retorno).
Correção sugerida: Cortar a leitura do FCA de _estado_terminal nas entregas disponíveis até o fechamento do horizonte (ou usar a última entrega até fim / próxima entrega anual para comprovar o encerramento ocorrido em (inicio, fim]) e nunca permitir que data_fim > fim ative suspensao_confirmada em fim.
Achado A4 — universo._informe_em não filtra _mes_encerrado(dt_refer, dia), permitindo que Data_Referencia do mês aberto ou futura desloque o corte de 6 meses de todos os FIIs em D
Área: A (Universo PIT de FIIs em as_of)
Arquivo:linha:
universo.py:80-91 e universo.py:277-289
montagem.py:334-356
Problema: Diferentemente de leitura.py:477 e remontagem.py:210 (que exigem leitura._mes_encerrado(dt_refer, dia)), universo._informe_em (universo.py:281-285) filtra apenas data_entrega < texto sem exigir que dt_refer seja um mês encerrado antes de dia.
Cenário de falha concreto: Em montagem.py:354, informe_mais_recente calcula corte = datas.max() - pd.DateOffset(months=6) usando o datas.max() global de todas as linhas lidas. Se um único fundo na tabela fii_informe_mensal tiver uma linha entregue antes de D mas com Data_Referencia futura (erro material de preenchimento na CVM, ex.: 2025-12-01 entregue em 2025-01-15) ou do próprio mês de D, datas.max() avança para essa data futura e exclui do universo em D todos os FIIs regulares cujos Informes tinham Data_Referencia até D - 1 mês.
Severidade: médio (exclusão indevida de FIIs do universo PIT por contaminação de datas.max() com dt_refer não encerrada em D).
Correção sugerida: Filtrar leitura._mes_encerrado(dt_refer, dia) em universo._informe_em (e em universo._fiis_com_informe).
Achado A5 — b3_proventos.relacao_ate lê todos os eventos_societarios sem filtrar por aprovacao < dia nem data_com < dia
Área: A (Eventos societários no Bazin histórico em as_of)
Arquivo:linha:
b3_proventos.py:670-677
proventos_b3.py:266-282
Problema: Em relacao_ate, a query das linhas 670–674 (SELECT linha_json FROM eventos_societarios WHERE emissor = ?) carrega todos os eventos societários da história do emissor, inclusive os aprovados anos depois de dia. Em seguida, proventos_b3._evento_de_acoes_na_janela (proventos_b3.py:275-281) testa if data_com is None or inicio - FOLGA_SEM_PREGAO < data_com < referencia:.
Cenário de falha concreto: Se um emissor tiver um registro em eventos_societarios aprovado em 2025 cujo lastDatePrior (data_com) veio vazio ou ilegível (data_com is None), qualquer chamada histórica analisar(ticker, as_of) em 2019, 2020 ou 2021 terá o Bazin e o DY de 12 meses abstidos por "evento societário na janela" por causa de um evento de 2025 que não existia em D.
Severidade: médio (vazamento de evento futuro causando abstenção retroativa em D).
Correção sugerida: Filtrar em relacao_ate apenas eventos societários com aprovacao < dia.isoformat() (ou data_com < dia.isoformat() quando aprovacao coincidir com a regra de publicação).
Área B — Ligação produtor→consumidor: dado gravado que nenhum leitor usa, ou teste que prova só o mock
Achado B1 — Ramo da relação B3 em fatores_acoes_b3.fatores_da_relacao e janelas_fundamentais.fatores_da_base exige coleta <= instante, rejeitando 100% dos eventos societários produzidos por relacao_ate para Graham e Lynch em qualquer as_of passado (discordância parcial com diagnostico-cobertura-f3.md)
Área: B (Produtor→consumidor desconectado no histórico + discordância com diagnóstico)
Arquivo:linha:
fatores_acoes_b3.py:92-125 e fatores_acoes_b3.py:166
janelas_fundamentais.py:79 e janelas_fundamentais.py:124-135
b3_proventos.py:670-683
test_disponibilidade_publicacao.py:295-309
diagnostico-cobertura-f3.md:377 e diagnostico-cobertura-f3.md:400
Problema:
O produtor histórico b3_proventos.relacao_ate (b3_proventos.py:670-683) carrega eventos_societarios do banco e monta {"coleta": coleta, "aprovacao_antes_de_d": True, "eventos_acoes": eventos, ...}, que chega a dados["proventos_b3"]["relacao"] no MotorHistorico.
E em fatores_acoes_b3.py:92-125, _eventos(relacao, inicio, fim, instante) já possui a lógica para validar cada evento por approvedOn < dia_limite e lastDatePrior < dia_limite.
Contudo, por conta da DD-65 (test_disponibilidade_publicacao.py:295-309), fatores_acoes_b3.fatores_da_relacao (fatores_acoes_b3.py:166) chama _coleta(relacao.get("coleta"), instante) com por_publicacao=False (e janelas_fundamentais.fatores_da_base na linha 79 chama _fonte(reconciliacao, instante) com por_publicacao=False).
Discordância com diagnostico-cobertura-f3.md:377, 400: O diagnóstico atribuiu os 44 casos de FATOR em 2025-06-30 apenas às falhas de coleta/identidade em relacao_ate e afirmou na linha 400 que recoletar os emissores faltantes na B3 destravaria Graham (fatores) e Lynch. Na realidade, mesmo para as companhias em que relacao_ate já tem coleta válida e identidade comprovada, fatores_da_relacao rejeita 100% delas em qualquer as_of passado porque relacao["coleta"] é de novembro de 2026 (> as_of)! Ou seja, "eventos_acoes" gravado por relacao_ate para reconciliar a base acionária histórica de Graham e Lynch nunca pode ser consumido em as_of passado.
Cenário de falha concreto: Companhia com coleta B3 completa (nov/2026), identidade conferida e um desdobramento 1:2 aprovado e ex-direito em 2022 (approvedOn < D, lastDatePrior < D). Ao rodar analisar(ticker, as_of=2025-06-30), a razão de ações entre 2021 e 2022 sai de (0.9, 1.1), fatores_acoes_b3.fatores_da_relacao é chamado e falha na linha 166 com "fator oficial B3 indisponível: coleta sem fuso ou posterior ao as_of", abstendo Graham e Lynch.
Severidade: bloqueante (0% das reconciliações de eventos societários de Graham e Lynch funcionam em as_of passado, tornando inútil a ligação de eventos_acoes em relacao_ate).
Correção sugerida: Em relacao_ate (ou eventos_ate), filtrar eventos_societarios até D com a mesma conferência de identidade do emissor + ISIN do pregão; e em fatores_acoes_b3.fatores_da_relacao / janelas_fundamentais.fatores_da_base, aceitar por_publicacao=True quando a relação vier de relacao_ate (aprovacao_antes_de_d=True), uma vez que _eventos (fatores_acoes_b3.py:104-106) já exige aprovado < dia_limite e data_com < dia_limite em cada evento.
Achado B2 — correcoes.csv (ler_correcoes) e identidades_fii.csv (ler_identidades_fii) não são passados por MotorHistorico nem por BacktestPIT a universo.indice_em / universo.universo_backtest
Área: B (Produtor→consumidor desconectado no histórico e no backtest)
Arquivo:linha:
historico.py:156-159
backtest_pit.py:327-334
universo.py:359-396
fontes.py:264-278
correcoes.csv:1-5
identidades_fii.csv:1-3
Problema: universo.indice_em e universo.universo_backtest aceitam correcoes e identidades_fii (e os filtram por c.data <= dia em universo.py:338-356), mas ReferenciaEm.indice (historico.py:158) e BacktestPIT._executar (backtest_pit.py:327) nunca passam ler_correcoes() nem ler_identidades_fii(), usando os defaults vazios ().
Cenário de falha concreto: Nas datas em que o FCA 2025/2026 já foi entregue (ex.: 2025-06-30):
MGLU3 recebe especie = "PN" e classe_preferencial = "PNA" no índice histórico (erro material do FCA 2025/2026 documentado em correcoes.csv:4, com data = 2025-01-01), fazendo suas janelas de Graham e Lynch absterem porque a Composição do Capital só tem ações ON;
CSNA3 ("4030" no FCA 2025/2026, correcoes.csv:2) e BPAC11 ("000000", correcoes.csv:5) caem em sem_identificacao e saem do universo elegível do backtest;
BTCI11 e TRPL11 (identidades_fii.csv:2-3) ficam fora do universo de FIIs.
Severidade: médio (perda de ativos elegíveis e erro de espécie de MGLU3 em analisar(ticker, as_of) e no backtest).
Correção sugerida: Carregar ler_correcoes() e ler_identidades_fii() por padrão em ReferenciaEm e em BacktestPIT (ou como default de universo.indice_em / universo.universo_backtest, que já filtram c.data <= dia).
Achado B3 — Série sgs_432 gravada em series_macro, indicador proventos da lente Qualidade no histórico, leitura.demonstrativo / leitura.informe_fii / leitura.modo_unico e b3_indices.mensal não têm consumidor no caminho de produção; e há testes que provam apenas o mock
Área: B (Dados/funções sem leitor de produção e testes que provam só o mock)
Arquivo:linha:
macro.py:798-843 e fii_engine.py:188-190
historico.py:256-301, qualidade_inputs.py:39-50 e qualidade.py:182
leitura.py:83-88, leitura.py:226-305 e leitura.py:448-507
b3_indices.py:139-172
test_servico_historico.py:98-139 e test_servico_historico.py:280-309
test_disponibilidade_publicacao.py:311-338
Problema e cenário de falha concreto:
Dados e funções sem consumidor em produção:
macro.gravar_series grava sgs_432 em series_macro (macro.py:798-843), mas nenhum código de produção lê sgs_432 de series_macro: FIIEngine._analisar_lentes (fii_engine.py:188-190) instancia MacroContext(as_of=...), que chama MacroProvider().serie_sgs(432, ...) via rede/cache em disco (data/macro).
MotorHistorico._buscar_proventos_b3 (historico.py:256-301) sobrescreve MarketEngine._buscar_proventos_b3 e nunca chama _calendario_proventos_b3; além disso, qualidade_inputs._provento (qualidade_inputs.py:39-50) e qualidade._linha (qualidade.py:182) exigem coleta <= instante sem por_publicacao. Como resultado, o indicador proventos da lente Qualidade tem sempre observados == 0 para qualquer as_of passado.
leitura.demonstrativo, leitura.informe_fii e leitura.modo_unico (leitura.py:83-88, 226-305, 448-507) e b3_indices.mensal (b3_indices.py:139-172) são chamados apenas por seus próprios testes unitários (remontagem.py e backtest_pit.py reimplementam a leitura/cálculo por fora).
Testes que provam só o mock / entrada sintética impossível:
Em test_servico_historico.py:280-309 (test_informe_e_dfp_compartilhados_por_ano_e_com_o_modo), o teste substitui remontagem.zip_informe_em por um mock (monkeypatch.setattr(remontagem, "zip_informe_em", informe)) e verifica apenas que o mock recebeu modo="exploratorio", ocultando que o zip_informe_em real (remontagem.py:185-223) ignora completamente o parâmetro modo (Achado A1).
Em test_disponibilidade_publicacao.py:311-330 (test_qualidade_pela_entrega_quando_coletado_depois), o teste contorna qualidade_inputs.montar e injeta documentos diretamente em Qualidade().calcular com e["distribuicao"]["coleta"] em 2026 mas mantendo e["proventos_b3"]["coleta"] no passado (2026-02-20 <= AS_OF), asserindo passado["proventos"]["observados"] == 5 para uma combinação que qualidade_inputs.py e o banco real (onde toda coleta B3 é de nov/2026) jamais produzem.
Em test_servico_historico.py:98-139 (test_data_passada_le_so_o_historico_do_banco), o único teste [e2e] do AnalysisService em data passada usa AMER3, que pertence a DISTRESSED_TICKERS (valuation_engine.py:31) e faz todas as 5 lentes absterem imediatamente por "Empresa em situação especial/distressed" antes de exercitar qualquer cálculo de lente com dados históricos.
Severidade: médio (código e dados sem ligação em produção; testes de integração que mascaram falhas reais dos consumidores).
Correção sugerida: Conectar leitura.informe_fii a zip_informe_em, b3_indices.mensal a BacktestPIT._retornos, sgs_432 de series_macro ao MotorHistorico (para FII), _calendario_proventos_b3 ao MotorHistorico._buscar_proventos_b3, e adicionar ao test_servico_historico.py um caso [e2e] com companhia não-distressed e FII não-distressed que produzam valor numérico nas lentes em as_of passado sem mocks intermediários.
Área C — Retorno total do backtest contra a ficha (backtest.md §5, decisões 41 e 42)
Achado C1 — BacktestPIT._retornos mapeia a espécie do provento apenas por {"3": "ON", "4": "PN"} e descarta silenciosamente todos os proventos quando a preferencial na B3 é PNA ou PNB, calculando retorno total falso com provento zero
Área: C (Retorno total do backtest — proventos e espécie da ação)
Arquivo:linha:
backtest_pit.py:530-553
Em contraste com proventos_b3.py:53 e proventos_b3.py:391-394
Problema: Na relação GetListedCashDividends da B3, o campo typeStock distingue "ON", "PN", "PNA" e "PNB" (proventos_b3.py:11, 53). Diversas ações preferenciais negociadas com final 4 na B3 possuem ISIN ACNPA e typeStock == "PNA" na relação da B3 (ou uma companhia tem proventos apenas em outra classe). Enquanto proventos_b3.serie_12_meses (proventos_b3.py:53, 391-394) resolve a espécie pelo ISIN (isin[6:11]: ACNPA -> PNA, ACNPB -> PNB, ACNPR -> PN) e abstém se a espécie não aparecer na relação, BacktestPIT._retornos (backtest_pit.py:530-537) faz:
python
especie_esperada = {"3": "ON", "4": "PN"}.get(sufixo)
...
if item.get("especie") != especie_esperada:
    continue
Se nenhum item tiver especie == "PN", entradas_proventos fica [] e retorno_total calcula o retorno apenas pela variação de preço, sem abster!
Cenário de falha concreto: Um papel XXXX4 com ISIN BRXXXXACNPA... e proventos registrados na B3 sob especie = "PNA" passa na conferência de identidade (conferir_emissor valida PNA contra ACNPA), entra em _retornos, tem 100% dos seus dividendos e JCP ignorados por item.get("especie") != "PN" e recebe um retorno_total numérico como se tivesse distribuído R$ 0,00 no período de 12/24/36 meses.
Severidade: bloqueante (retorno total numérico subestimado por perda silenciosa de todos os proventos de ações 4 cuja espécie na B3 é PNA/PNB).
Correção sugerida: Determinar a espécie esperada em _retornos a partir do ISIN comprovado do pregão (_ISIN_ESPECIE de proventos_b3.py:53) — ou verificar compatibilidade com o ISIN do ticker — e, quando a relação do emissor tiver proventos mas nenhum registro da espécie do ticker, verificar se a espécie consta nos ISINs antes de assumir provento zero.
Achado C2 — BacktestPIT._retornos não filtra item["natureza"] (DIVIDENDO / JRS CAP PROPRIO) ao reinvestir proventos em dinheiro
Área: C (Retorno total do backtest contra a ficha §5)
Arquivo:linha:
backtest_pit.py:535-553
Em contraste com backtest.md:37 e proventos_b3.py:46, proventos_b3.py:371-380
Problema: A ficha aprovada (backtest.md:37) define: "Os proventos em dinheiro (dividendos e JCP brutos, da tabela proventos, F3-7a) são reinvestidos no próprio ativo na data ex". Na tabela proventos, b3_proventos.gravar_proventos grava todas as linhas de cashDividends, cuja coluna natureza (corporateAction) pode conter "REST CAP DIN" (restituição de capital em dinheiro) ou outras naturezas fora de {"DIVIDENDO", "JRS CAP PROPRIO"}. Enquanto proventos_b3.serie_12_meses (proventos_b3.py:371-374) verifica natureza not in NATUREZAS_ELEGIVEIS e abstém a janela, BacktestPIT._retornos (backtest_pit.py:535-553) nunca lê item.get("natureza").
Cenário de falha concreto: Se uma companhia tiver uma restituição de capital ("REST CAP DIN") ou outro evento em cashDividends na janela (D, T], _retornos o soma e reinveste sem distinção (ou sem abster quando a natureza não é elegível).
Severidade: bloqueante (desvio da regra econômica da ficha §5 sobre a natureza dos proventos reinvestidos).
Correção sugerida: Validar item.get("natureza") em _retornos contra NATUREZAS_ELEGIVEIS = {"DIVIDENDO", "JRS CAP PROPRIO"} (abstendo o retorno quando houver natureza em dinheiro na janela cujo tratamento a ficha não especifica).
Achado C3 — BacktestPIT._retornos chama proventos_ate(..., fim + 1 dia) e abstém em sem_prova quando data_com == fim (T), rejeitando ativos com provento ex-horizonte (data_ex > T) (discordância com diagnostico-cobertura-f3.md)
Área: C (Fronteiras D e T do retorno total + discordância com diagnóstico)
Arquivo:linha:
backtest_pit.py:520-526 e backtest_pit.py:554-591
b3_proventos.py:280-299 e b3_proventos.py:620-626
diagnostico-cobertura-f3.md:381
Problema:
Em backtest_pit.py:520-526, _retornos define corte = fim + timedelta(days=1) e chama b3_proventos.proventos_ate(self.conn, raiz, corte, ...) e eventos_ate(self.conn, raiz, corte, ...).
Em proventos_ate (b3_proventos.py:620-626), todo provento com data_com < corte.isoformat() (isto é, data_com <= fim) é selecionado, e _data_ex(conn, data_com, corte) (b3_proventos.py:289) busca o primeiro pregão com data > data_com AND data < corte.isoformat().
Quando um provento tem data_com == fim (por exemplo, T = 2023-06-30, último dia útil do semestre, data clássica de data_com de JCP trimestral/semestral), não existe nenhum dia entre 2023-06-30 e 2023-07-01 (data > '2023-06-30' AND data < '2023-07-01' é sempre vazio!). Assim, _data_ex retorna None e proventos_ate coloca esse provento em sem_prova.
Em seguida, backtest_pit.py:554-562 percorre proventos_info.get("sem_prova") (sem sequer filtrar por espécie do ticker!) e testa if data_com is None or inicio <= data_com <= fim: — abstendo o ativo! Mas se data_com == fim (T), o primeiro pregão seguinte (data_ex) é necessariamente > T, logo fora do horizonte (D, T] da ficha (backtest.md:38)!
O mesmo bug ocorre para eventos_ate em backtest_pit.py:566-591 (inicio <= data_com <= fim em sem_prova, e além disso sem filtrar o isin do evento em sem_prova pelo isin_esperado da linha 569).
Discordância com diagnostico-cobertura-f3.md:381: O diagnóstico classificou os 16 casos de PROVA ("relação de proventos contém registros sem prova no horizonte") como "Decisão de escopo — FATO", quando na verdade é um bug de fronteira em corte = fim + 1 dia combinado com <= fim.
Cenário de falha concreto: Qualquer companhia que declare JCP ou dividendo com data_com no último pregão T do horizonte (ex.: 2022-06-30, 2023-06-30, 2024-06-28) tem data_ex no primeiro pregão de julho (> T), que não pertence a (D, T], mas seu retorno total em _retornos é abstido com "relação de proventos contém registros sem prova no horizonte".
Severidade: médio (abstenção falsa sistemática no fechamento de cada horizonte T quando há provento ou evento com data_com == T).
Correção sugerida: Como data_ex é estritamente posterior a data_com, apenas registros com data_com < fim (estrito) podem ter data_ex <= fim. Em sem_prova (backtest_pit.py:560, 588), usar inicio <= data_com < fim (e filtrar sem_prova pela espécie/ISIN do ticker, como feito para os itens válidos).
Achado C4 — Deslistagem e suspensão em BacktestPIT._estado_terminal e retorno_total divergem da ficha §5 quando o último negócio ocorre antes de Data_Fim_Negociacao, quando falta Data_Fim_Negociacao no FCA ou quando um ativo líquido falha o pregão T
Área: C (Deslistadas, suspensão e CDI contra a ficha §5)
Arquivo:linha:
backtest_pit.py:166-186, backtest_pit.py:223-237 e backtest_pit.py:682-744
backtest.md:40-41
Problema: Três divergências em relação à ficha §5 (backtest.md:40-41):
Exigência de cotação exatamente na data Data_Fim_Negociacao: retorno_total (backtest_pit.py:174-175, 224) define limite = deslistagem (data_fim do FCA) e exige limite in precos e limite in pregoes; se o papel não tiver negócio exatamente no dia de Data_Fim_Negociacao, abstém com "último fechamento da deslistagem indisponível". Na própria fixture oficial de deslistada do projeto (ALL, em test_universo_pit.py:316-318), o último negócio no COTAHIST é 2015-03-31 e Data_Fim_Negociacao no FCA é 2015-04-01. Pela ficha §5, a saída deve ocorrer pelo "último preço negociado" até a deslistagem, capitalizando CDI daquela data até T.
Deslistada sem Data_Fim_Negociacao no FCA vira suspensa (sem CDI e sem sair em retorno_medio_sem_deslistadas): Se uma companhia cancelou registro ou deixou de listar o código no FCA seguinte, mas seu último FCA não preencheu Data_Fim_Negociacao (data_fim is None), _estado_terminal (backtest_pit.py:735-742) deixa deslistagem = None e, quando referencia_atual >= fim, marca suspensao_confirmada = True — tratando deslistada como suspensa (0% de CDI e mantida em retorno_medio_sem_deslistadas).
Ativo ativo sem negócio no pregão T vira "suspensão sem deslistagem": Qualquer ativo que continue listado (referencia_atual >= fim) mas não tenha negócio exatamente no pregão T (not preco_final_disponivel) recebe suspensao_confirmada = True (backtest_pit.py:739-742), inflando n_suspensas e carregando preço antigo até T sem evidência de suspensão.
Cenário de falha concreto:
Ativo com Data_Fim_Negociacao = 2021-04-01 cujo último negócio no COTAHIST foi em 2021-03-31: retorno_total abstém em vez de encerrar em 2021-03-31 e aplicar o fator DI de 2021-03-31 a T.
Ativo ativo em T que negociou em T - 1 mas não teve negócio em T: entra no quintil com o preço de T - 1 e é contabilizado como suspenso (n_suspensas += 1).
Severidade: bloqueante (resultado errado para ativos sem negócio em T ou deslistados sem Data_Fim_Negociacao, e abstenção indevida para deslistadas cujo último negócio antecede Data_Fim_Negociacao).
Correção sugerida: Em caso de deslistagem comprovada até T (por Data_Fim_Negociacao <= T, saída do código na referência seguinte do FCA ou DT_CANCEL <= T no cadastro), usar o último pregão com negócio do ativo <= Data_Fim_Negociacao como data de saída na acción e início da capitalização do CDI até T; e não inferir suspensão de negociação apenas de not preco_final_disponivel and referencia_atual >= fim.
Achado C5 — BacktestPIT._grupos descarta as abstenções antes de quintis_por_modo (zerando grupo["abstencoes"] por data D) e BacktestPIT._executar cria uma lente artificial "analise" quando o serviço falha antes das lentes
Área: C (Relatório e contagens do backtest contra a ficha §§3.3 e 8)
Arquivo:linha:
backtest_pit.py:359-402, backtest_pit.py:768-770 e backtest_pit.py:918-929
backtest.md:22
Problema:
Em _grupos (backtest_pit.py:769-770), validas = [o for o in itens if o.get("abstencao") is None] remove todas as observações com abstenção antes de chamar quintis_por_modo(validas). Por isso, embora formar_quintis tenha sido escrito e testado para contar abstencoes (backtest_pit.py:67-76), no caminho real de BacktestPIT.executar o campo grupo["abstencoes"] de cada data D sai sempre {} (vazio), descumprindo a ficha §3.3 (backtest.md:22: "O relatório conta as abstenções por motivo em cada D").
Quando AnalysisService.analisar falha antes das lentes (ex.: ativo do universo sem preço antes de D), _gravar_resultados grava um único registro com metodo="analise". Em _executar (backtest_pit.py:360, 399, 835), esse registro cria uma pseudo-lente "analise" em resumo["lentes"] e o ativo deixa de ser contado no universo_elegivel e nas abstenções das lentes reais (Graham, Bazin, Lynch, Gordon, Bancos, fii).
Em _resumo_lente (backtest_pit.py:918-929), n_datas_sem_cdi e n_datas_sem_ibov só são incrementados quando _finito(dados.get("retorno_medio")) é verdadeiro, omitindo datas em que o quintil foi formado (>= 25 valores) e o benchmark faltou, mas nenhum ativo do quintil teve retorno válido.
Cenário de falha concreto: Ao executar BacktestPIT.executar([D]), relatorio["por_lente_data_horizonte"][(lente, D, h)]["estrito"]["abstencoes"] é {} para todas as lentes e datas, mesmo quando dezenas de ativos se abstiveram em D.
Severidade: médio (relatório por data D perde a contagem de abstenções exigida pela ficha §3.3 e polui resumo["lentes"] com a chave "analise").
Correção sugerida: Passar itens (incluindo as abstenções de avaliação) para quintis_por_modo em _grupos (filtrando apenas no cálculo de retorno dos que têm valor), propagar a abstenção pré-lente (metodo="analise") como abstenção das lentes aplicáveis à classe do ativo sem criar a lente "analise", e contar n_datas_sem_cdi / n_datas_sem_ibov sempre que a data tiver quintis formados e o benchmark for None.
Área D — Regra econômica alterada sem ficha; golden e testes protegidos
Achado D1 — DatabaseManager.reset_db() (exposto na UI do app.py) faz os.remove("sentinela_store.db") sem backup, apagando todo o banco histórico PIT e a tabela imutável resultados_analise
Área: D (Proteção do armazenamento único e da tabela imutável resultados_analise)
Arquivo:linha:
database.py:18-21 e database.py:160-178
app.py:541-551
unico.py:263-277
Problema: Desde o F3-2c, DatabaseManager.__init__ (database.py:20) aponta por padrão para sentinela_store.db (o banco único de 32,5 GB com todas as tabelas históricas PIT das migrações 001 a 012 e a tabela imutável resultados_analise). Porém, DatabaseManager.reset_db() (database.py:160-178) foi mantido da V1: executa os.remove(self.db_path) sem backup e chama self._init_db(), que recria apenas as 3 tabelas legadas (analises, carteira_real, fundamentals_cache) sem rodar migracoes.aplicar. Esse método continua ligado ao botão "Sim, apagar tudo" na barra lateral do Streamlit (app.py:547-548).
Cenário de falha concreto: Se o usuário clicar em "Resetar Banco" → "Sim, apagar tudo" na interface (ou se qualquer chamador invocar db.reset_db()), o arquivo sentinela_store.db inteiro (32,5 GB de backfill CVM/COTAHIST/macro/proventos, a carteira_real e a tabela somente-inserção resultados_analise) é deletado do disco sem backup e substituído por um banco vazio sem as migrações 001..012, quebrando em seguida o AnalysisService (no such table: resultados_analise).
Severidade: bloqueante (perda total de dados do banco único sem backup e destruição da tabela imutável resultados_analise).
Correção sugerida: Proibir os.remove sobre o banco único em DatabaseManager.reset_db() (ou exigir backup verificado de backup.py e limpar apenas a tabela legada analises, aplicando migracoes.aplicar na inicialização).
Verificação dos demais itens da Área D (Golden e testes protegidos)
Golden (tests/fixtures/golden_motores.jsonl) e harness (golden_motores.py:1-729): Nenhuma alteração de regra econômica sem ficha foi encontrada em valuation_engine.py, fii_engine.py ou sentinela/methods/. As guardas de disponibilidade histórica adicionadas no F3-3e (por_publicacao=True) só são ativadas quando as_of é anterior ao dia corrente em São Paulo (market_engine.py:296-297), preservando integralmente o comportamento e o golden para as_of = hoje.
Testes protegidos (tests/regressao/): As mudanças em test_bug_3_12_serie_cvm_ignora_as_of.py:1-36 (conciliado com test_bug_3_15_serie_cvm_documento_entregue_apos_corte.py:1-59 pela DD-61) e em test_bug_2c_58_cli_lentes.py:1-81 (remoção da função de CLI de auditar_recomendacoes.py no F3-9c-aud) já estão documentadas em auditoria-f3.md:83-85 e não são repetidas aqui.
O que não foi possível cobrir
Conteúdo e integridade física dos bancos SQLite (*.db), .env, logs e demais arquivos em outputs/: não verificado (proibido pelas regras desta auditoria; apenas auditoria-f3.md e diagnostico-cobertura-f3.md foram lidos em outputs/).
Execução dinâmica da suíte de testes (pytest), do mutmut e do scripts/gate.py: não verificado por execução (toda a auditoria foi conduzida por inspeção estática somente leitura, sem rodar processos que pudessem criar caches ou artefatos).
Contagens reais no banco sentinela_store.db do impacto de fatores_da_relacao (Achado B1), de ações 4 com espécie PNA/PNB (Achado C1) e de proventos com data_com == T (Achado C3): não verificado no banco real (confirmado apenas pelo código-fonte e pelos testes/fixtures abertos).