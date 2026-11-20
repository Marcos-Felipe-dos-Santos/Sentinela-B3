Auditoria Completa de Fechamento da Fase 3 (Gemini — Somente Leitura)
Branch / Commit auditado: v2/fase-3, HEAD 766d01a59aacac457f8d9d6e7933fc16c3bc7305 (intervalo pós-auditoria: 9b0e74c..766d01a, 30 commits).
Leitura prévia concluída: AGENTS.md, CLAUDE.md, README.md, politica-decisao-autonoma.md, backtest.md, pr-fase-3.md, resumo-3a.md, resumo-3b.md, fase-3-gemini.md e fase-3-codex.md.
Tarefa 1 — Verificação dos Achados da Auditoria Anterior (A1 a A5, B1 a B3, C1 a C5, D1)
Achado	Status em HEAD (766d01a)	Resumo da verificação
A1 (BUG-3-49)	corrigido (GA1a) + limitação declarada (GA1b, 8 xfail estritos)	Seleção ponto-no-tempo, manifesto de bloqueios, corte de Data_Referencia e Data_Entrega e vedação de recuo mensal corrigidos; CSV complemento/geral do ano vigente presente porém vazio ou malformado está em xfail(strict=True) (F4-H02).
A2 (BUG-3-50)	corrigido parcial (GA2a) + limitação declarada (GA2b, 15 xfail estritos)	Apenas o caso de CSV ausente/ilegível no exercício final de calcular_indicadores (por_publicacao=True) e a preservação de anos recentes quando DFP antiga falha foram corrigidos; o recuo de período quando a versão vigente em D está no índice sem números na fonte aberta (reapresentação > D ou conflito DD-57) e a escolha pela maior VERSAO em vez da última DT_RECEB < D ficaram em xfail(strict=True) (F4-H01).
A3 (BUG-3-48)	corrigido	Entregas do FCA terminal cortadas em T (fim + 1 dia exclusivo), cache indexado por horizonte fim e remoção do uso de data_fim > fim para inferir suspensão.
A4 (BUG-3-51)	corrigido	universo._geral_antes filtra leitura._mes_encerrado(dt_refer, dia) antes de calcular o corte de 95 dias e antes de listar FIIs em tickers_em.
A5 (BUG-3-52)	corrigido	b3_proventos.relacao_ate exclui de eventos_societarios qualquer evento com approvedOn >= dia legível.
B1 (BUG-3-53)	corrigido	fatores_acoes_b3.relacao_por_publicacao e janelas_fundamentais.fatores_da_base dispensam coleta <= D quando o bloco traz as duas marcas históricas (disponibilidade_por_publicacao e aprovacao_antes_de_d), mantendo aprovacao < D e data_com < D.
B2 (BUG-3-55)	corrigido	universo.indice_em aplica por padrão referencias_em(dia), carregando correcoes.csv e identidades_fii.csv filtradas por data de evidência < dia (DD-89).
B3 (F3-AUD-E2E)	corrigido (ação E2E e leitura.informe_fii) + limitação declarada (FII E2E, 1 xfail estrito) + não corrigido (5 subitens em F4-H09)	leitura.informe_fii foi ligada a zip_informe_em e há teste E2E real para ABEV3 (Gordon numérico); FII E2E está em xfail(strict=True) (F4-H03); sgs_432 em series_macro, _calendario_proventos_b3 no MotorHistorico, leitura.demonstrativo, leitura.modo_unico e b3_indices.mensal seguem sem consumidor (F4-H09).
C1 (BUG-3-45)	corrigido	BacktestPIT._retornos deriva a espécie a partir de ESPECIE_DO_ISIN.get(isin[6:11]) (ON, PN, PNA, PNB, etc.) em vez do sufixo "3"/"4".
C2 (BUG-3-46)	corrigido	BacktestPIT._retornos verifica item.get("natureza") not in NATUREZAS nos proventos da janela e da espécie do ticker e abstém quando há natureza fora da ficha.
C3 (BUG-3-54)	corrigido	BacktestPIT._retornos usa inicio <= data_com < corte_com (corte_com = fim_ativo), excluindo data_com == T nos três laços de sem_prova e ex is None.
C4 (BUG-3-47)	corrigido	retorno_total encerra o papel no último negócio <= Data_Fim_Negociacao e capitaliza CDI a partir desse pregão; _estado_terminal não presume mais suspensão sem prova.
C5 (BUG-3-56)	corrigido (itens 1 e 2) + não corrigido (item 3 e denominador de cobertura, em F4-H07)	_grupos agora contabiliza as abstenções por data D e _executar separa metodo == "analise" em sem_lentes; n_datas_sem_ibov/n_datas_sem_cdi quando todos os retornos do quintil são None e o denominador de cobertura em _resumir não foram alterados (F4-H07).
D1 (BUG-3-44)	corrigido	DatabaseManager.reset_db não remove mais o arquivo SQLite e lança RuntimeError; botão destrutivo removido de app.py.
Detalhamento item a item (Tarefa 1)
A1 (BUG-3-49) — corrigido (GA1a) + limitação declarada (GA1b)
Parte corrigida (GA1a, commit 2ea5f2a):
Código:
sentinela/data/pit/remontagem.py (zip_informe_em): delega a seleção por (CNPJ_Fundo, Data_Referencia) a leitura.informe_fii(conn, cnpj, as_of, modo=modo, ano=ano) (linha 207), isola os diretórios de saída por destino / dia.isoformat() / modo (linha 217) e grava sentinela_informe_pit.json com dia, modo e motivos dos meses bloqueados (linhas 224–226).
sentinela/data/pit/leitura.py (_versoes_com_numeros e informe_fii): exige presença da seção complemento na versão escolhida (MOTIVO_SEM_NUMEROS quando ausente, linhas 455–457), corta Data_Referencia em mês encerrado (_mes_encerrado, linha 482), bloqueia no modo "estrito" quando a maior versão tem Data_Entrega >= D (MOTIVO_ENTREGA_POSTERIOR, linhas 500–507) e rotula _pit_exploratorio="1" e _pit_dia no modo "exploratorio" quando usa reapresentação entregue em/após D (DD-88, linhas 512–516).
cvm_fii_provider.py (_montar_proveniencia, _recorte_informe, _bloqueio_informe), cvm_fii_provider.py (obter_dados_fii) e cvm_fii_provider.py (obter_rendimentos_fii): preserva a Data_Entrega da versão selecionada na proveniência (linhas 135–138), aplica o corte temporal mesmo na leitura de ZIP direto sem manifesto (linhas 177–207), impede recuo ao mês anterior quando o Informe vigente ou qualquer mês da janela de 13 meses está bloqueado ou tem conflito/ausência de Valor_Patrimonial_Cotas, Patrimonio_Liquido ou Cotas_Emitidas (linhas 214–229 e 301–315). Em sentinela/data/rendimento_fii.py (_disponivel_no_corte), dy_entregue_ate aceita a linha exploratória somente quando registro["_pit_dia"] == dia.isoformat().
Teste que prova: tests/regressao/test_bug_3_49_informe_fii_sem_recuo.py (36 casos passando, cobrindo MotorHistorico, CVMFIIProvider direto, isolamento entre "estrito" e "exploratorio", VPA histórico, composição de carteira e proveniência).
Parte em limitação declarada (GA1b, commit 508c5ae, decisão 50):
Quando o CSV complemento ou geral do ano vigente existe no ZIP mas está vazio ou malformado (cvm_fii_provider.py), _linhas_do_fundo devolve None ou listas vazias sem erro, permitindo recuo de obter_dados_fii ao ano anterior e omitindo o ano de lacunas em obter_rendimentos_fii.
Testes xfail estritos: tests/regressao/test_bug_3_49_informe_fii_sem_recuo.py (test_secao_vigente_ilegivel_nao_recua_ao_ano_anterior, 8 casos com @pytest.mark.xfail(strict=True)), destino F4-H02 em docs/loop/fila-fase4-proposta.md.
A2 (BUG-3-50) — corrigido parcial (GA2a) + limitação declarada (GA2b)
Parte corrigida (GA2a, commit ee90214):
Código: cvm_provider.py e cvm_provider.py (calcular_indicadores). Antes de concluir a leitura dos três CSVs (numeros_lidos = True, linha 552), se ocorrer KeyError/OSError/ValueError/pd.errors.ParserError: (i) quando ano == ano_final e getattr(self, "por_publicacao", False) é verdadeiro (CVMProviderEm e _Recorte), verifica em self._entregas(zip_path) se há entrega da companhia para aquele exercício e, se houver, propaga OSError (linhas 735–750), que market_engine.py converte em abstenção de serie_cvm; (ii) para ano < ano_final, registra aviso e preserva os exercícios recentes legíveis, fazendo apenas a janela de 5 exercícios que contém o ano faltante abster em sentinela/data/janelas_fundamentais.py.
Teste que prova: tests/regressao/test_bug_3_50_periodo_cvm_vigente_sem_numeros.py, linhas 395–453 e linhas 568–759 (11 casos passando).
Parte em limitação declarada (GA2b, commit 508c5ae, decisão 50):
O núcleo do Achado A2 original não foi alterado no código: quando os CSVs existem no ZIP remontado ou recortado, mas a versão vigente em D da companhia está no índice sem linhas numéricas nos CSVs (reapresentação posterior a D ou retenção por conflitos_carga DD-57), exercicio_anual_mais_recente (cvm_provider.py), calcular_indicadores (cvm_provider.py) e _acumulados_do_arquivo / acumulados_ttm (cvm_provider.py) continuam recuando para o exercício, referência ou trimestre anterior; além disso, a seleção de versão continua usando max(VERSAO) entre entregas < D em vez da última DT_RECEB < D, e uma linha ilegível de outra companhia no índice ainda engole o any(...) em cvm_provider.py.
Testes xfail estritos: tests/regressao/test_bug_3_50_periodo_cvm_vigente_sem_numeros.py, linhas 300–393, linhas 456–566 e linhas 761–787 (15 casos com @pytest.mark.xfail(strict=True)), destino F4-H01 em docs/loop/fila-fase4-proposta.md.
A3 (BUG-3-48) — corrigido
Código: backtesting/backtest_pit.py e linhas 738–784 (_estado_terminal). O corte de entregas do FCA mudou de date.max.isoformat() para corte = date.fromordinal(fim.toordinal() + 1).isoformat() (linhas 740–741, incluindo entregas até o fim do dia T e excluindo entregas após T), o cache self._fca_tickers[fim] passou a ser indexado por horizonte fim (linhas 738 e 752) e foi removida a inferência de suspensão a partir de data_fim > fim ou referencia_atual >= fim.
Teste que prova: tests/regressao/test_bug_3_48_fca_terminal_apos_horizonte.py (4 testes passando).
A4 (BUG-3-51) — corrigido
Código: sentinela/data/referencia/universo.py (_geral_antes e _fiis_com_informe) e linhas 290–296 (_informe_em). _geral_antes exige leitura._mes_encerrado(dt_refer, dia) (linha 94) em todas as linhas do Informe com Data_Entrega < dia, tanto para o corte de 95 dias de _informe_em quanto para a presença do FII em tickers_em.
Teste que prova: tests/regressao/test_bug_3_51_informe_fii_mes_aberto_no_universo.py (4 testes passando).
A5 (BUG-3-52) — corrigido
Código: sentinela/data/providers/b3_proventos.py (relacao_ate) e linhas 698–705 (_aprovado_em_d_ou_depois). relacao_ate descarta da lista eventos_societarios qualquer evento com approvedOn legível >= dia, preservando eventos com approvedOn ilegível para abstenção conservadora na janela da data_com.
Teste que prova: tests/regressao/test_bug_3_52_evento_em_acoes_futuro_no_historico.py (3 testes passando).
B1 (BUG-3-53) — corrigido
Código: sentinela/data/fatores_acoes_b3.py (relacao_por_publicacao), linhas 179–181 (fatores_da_relacao) e sentinela/data/janelas_fundamentais.py (fatores_da_base). Quando o bloco de entrada vem da relação histórica por publicação (dados["disponibilidade_por_publicacao"] is True e dados["proventos_b3"]["aprovacao_antes_de_d"] is True), a guarda coleta <= D é dispensada e a prova temporal dos pares documentais permanece em _fator_do_par (aprovacao < dia e data_com < dia em sentinela/data/fatores_acoes_b3.py).
Teste que prova: tests/regressao/test_bug_3_53_fator_b3_da_relacao_historica.py (5 testes passando).
B2 (BUG-3-55) — corrigido
Código: sentinela/data/referencia/universo.py (referencias_em e indice_em). Quando correcoes ou identidades_fii são None, indice_em carrega automaticamente referencias_em(dia), filtrando correcoes.csv e identidades_fii.csv por data de evidência < dia (DD-89). Isso conecta tanto ReferenciaEm.indice (sentinela/services/historico.py) quanto universo_backtest (sentinela/data/referencia/universo.py).
Teste que prova: tests/regressao/test_bug_3_55_correcoes_no_indice_historico.py (6 testes passando).
B3 (F3-AUD-E2E) — corrigido parcial + limitação declarada parcial + não corrigido nos demais subitens
Ligação de leitura.informe_fii em produção: corrigido em sentinela/data/pit/remontagem.py (zip_informe_em) e provado em tests/regressao/test_bug_3_49_informe_fii_sem_recuo.py.
Teste E2E de ação não-distressed pelos produtores reais (sem mocks intermediários): corrigido em tests/test_servico_historico.py (test_acao_nao_distressed_tem_lente_numerica_pelo_servico, que roda AnalysisService.analisar("ABEV3", as_of=date(2022, 3, 31)) sobre banco_publico e verifica valor e distância finitos em Gordon).
Teste E2E de FII não-distressed pelos produtores reais: limitação declarada com @pytest.mark.xfail(strict=True) em tests/test_servico_historico.py (test_fii_nao_distressed_tem_lente_numerica_pelo_servico), com destino em F4-H03 (docs/loop/fila-fase4-proposta.md).
Demais desconexões listadas em B3 (sgs_432 gravada em series_macro sem leitor; _calendario_proventos_b3 ausente em MotorHistorico._buscar_proventos_b3 deixando proventos.observados == 0 na Qualidade histórica; leitura.demonstrativo, leitura.modo_unico e b3_indices.mensal sem chamador em produção): não corrigido na Fase 3 (transferidos sem xfail para F4-H09 em docs/loop/fila-fase4-proposta.md).
C1 (BUG-3-45) — corrigido
Código: backtesting/backtest_pit.py e linhas 569–581 (_retornos). Importa ESPECIE_DO_ISIN de sentinela/data/proventos_b3.py e deriva especie_esperada = ESPECIE_DO_ISIN.get(isin[6:11]), cobrindo PNA (ACNPA), PNB (ACNPB), PNC, PND, ON e PN, e abstendo se o ISIN não tiver espécie mapeada.
Teste que prova: tests/regressao/test_bug_3_45_especie_isin_backtest.py (2 casos parametrizados passando para PNA e PNB).
C2 (BUG-3-46) — corrigido
Código: backtesting/backtest_pit.py e linhas 596–600 (_retornos). Importa NATUREZAS = ("DIVIDENDO", "JRS CAP PROPRIO") de sentinela/data/proventos_b3.py e, se qualquer provento da espécie do ticker com inicio < ex <= fim_ativo tiver item.get("natureza") not in NATUREZAS, abstém com "natureza de provento não prevista na ficha".
Teste que prova: tests/regressao/test_bug_3_46_natureza_provento_backtest.py (5 casos passando).
C3 (BUG-3-54) — corrigido
Código: backtesting/backtest_pit.py e linhas 607, 622 e 632 (_retornos). Usa inicio <= data_com < corte_com (corte_com = fim_ativo), excluindo data_com == T (cuja data_ex cai após T) nos laços de relacao["sem_prova"], eventos_lidos["sem_prova"] e eventos_lidos["eventos"] com ex is None.
Teste que prova: tests/regressao/test_bug_3_54_data_com_em_t_fora_do_horizonte.py (4 testes passando).
C4 (BUG-3-47) — corrigido
Código:
backtesting/backtest_pit.py (retorno_total): quando deslistagem is not None, coleta os pregões negociados em [inicio, min(deslistagem, fim)], define limite = dentro[-1][0] (o último negócio até Data_Fim_Negociacao), reinveste proventos apenas em (inicio, limite] e capitaliza o CDI diário em [limite, fim).
backtesting/backtest_pit.py (_retornos): limita fim_ativo ao último pregão negociado <= deslistagem para não bloquear o retorno por eventos societários posteriores à saída do papel.
backtesting/backtest_pit.py (_estado_terminal): suspensao_confirmada passa a ser sempre False (sem fonte de suspensão comprovada no banco), fazendo falta de negócio em T sem deslistagem abster na linha 183–184 em vez de manter preço com 0% de retorno.
Teste que prova: tests/regressao/test_bug_3_47_estado_terminal_backtest.py (3 testes passando).
C5 (BUG-3-56) — corrigido (itens 1 e 2) + não corrigido (item 3 e denominador de cobertura)
Parte corrigida (commit 10e89ea):
backtesting/backtest_pit.py (_grupos): passa todas as observações da lente/data (com e sem abstencao) para quintis_por_modo(itens), populando grupo["abstencoes"] por data D e registrando o grupo mesmo quando 100% dos ativos da lente se abstêm naquela data.
backtesting/backtest_pit.py (_executar): separa metodo == "analise" (METODO_SEM_LENTE) na lista sem_lentes e em resumo["abstencoes_antes_das_lentes"], removendo a pseudo-lente "analise" de observacoes, grupos e resumo["lentes"].
Teste que prova: tests/regressao/test_bug_3_56_abstencoes_do_backtest_por_data.py (4 testes passando).
Parte não corrigida (transferida para F4-H07 em docs/loop/fila-fase4-proposta.md):
Em backtesting/backtest_pit.py (_resumir), n_datas_sem_ibov e n_datas_sem_cdi continuam condicionados a _finito(dados.get("retorno_medio")), omitindo datas com quintis formados quando todos os retornos dos ativos do quintil são None.
Em backtesting/backtest_pit.py (_resumir), universo_elegivel = len(itens) continua não somando ao denominador da lente os ativos de sem_lentes aplicáveis àquela classe de ativo.
D1 (BUG-3-44) — corrigido
Código: database.py (DatabaseManager.reset_db) lança RuntimeError("Reset destrutivo desativado: o banco único deve ser preservado.") sem apagar o arquivo; app.py removeu o botão "Resetar Banco" / "Sim, apagar tudo".
Teste que prova: tests/regressao/test_bug_3_44_reset_banco_unico.py (2 testes passando).
Tarefa 2 — Auditoria dos Commits 9b0e74c..HEAD

Nenhum achado novo de severidade bloqueante foi introduzido nos 30 commits de 9b0e74c..HEAD (além das limitações já declaradas e travadas com xfail(strict=True) em A1/GA1b e A2/GA2b). Abaixo está a auditoria nas quatro frentes solicitadas e as ressalvas de severidade Fase 4.

1. Vazamento de futuro
Correções verificadas no intervalo:
BUG-3-58 (F3-AUD-CA2b, commit 2170e22): market_engine.py (_data_passada, chamado nas linhas 537 e 1173) e sentinela/services/historico.py (MotorHistorico._data_passada) eliminaram a leitura do relógio do sistema (_hoje_sp()) abaixo de AnalysisService: toda análise que entra pelo MotorHistorico (onde AnalysisService já decidiu dia < self.hoje em sentinela/services/analyze_asset.py) aplica disponibilidade_por_publicacao = True, provado em tests/regressao/test_bug_3_58_relogio_abaixo_do_servico_historico.py.
Cortes temporais do FCA terminal (BUG-3-48), do Informe de FII no universo (BUG-3-51) e dos eventos societários em ações (BUG-3-52) verificados conforme a Tarefa 1.
Ressalvas identificadas (Severidade: Fase 4):
Contaminação retroativa de datas passadas pela coleta mais recente da B3 (F3-3D-COL, commit 0ec4cf7, destino F4-H08): Em sentinela/data/providers/b3_proventos.py (proventos_ate) e linha 646 (relacao_ate), quando por_publicacao=True, o código seleciona max(anteriores) entre todas as coletas do emissor no banco (incluindo coletas feitas anos depois de D) e valida _identidade_com_o_pregao (linhas 490–524) apenas nessa última coleta, sem filtrar os proventos do complemento por lastDatePrior < dia. Na recoleta de 19/11/2026 (0ec4cf7), anúncios de novembro/2026 presentes no complemento e ainda ausentes da relação GetListedCashDividends fizeram a prova de identidade da coleta de 19/11 falhar e invalidaram retroativamente todas as datas passadas D (2018 a 2025) daqueles emissores (derrubando 265 retornos de 12 meses na sonda final, conforme registrado em pr-fase-3.md), mesmo quando o banco já continha uma coleta anterior íntegra. Como o efeito é abstenção (perda de cobertura declarada, não número errado nem uso de provento futuro), a severidade é Fase 4 (F4-H08).
Data de evidência em correcoes.csv para MGLU3 (BUG-3-55 / DD-89, commit b0a2c5c): Em sentinela/data/referencia/universo.py (referencias_em), o filtro usa date.fromisoformat(c.data) < dia. Para MGLU3 (sentinela/data/referencia/correcoes.csv), a coluna data foi preenchida com 2025-12-31 (DT_REFER da DFP 2025, e não a DT_RECEB de entrega da DFP em 2026). Para uma consulta com D entre 2026-01-01 e a entrega da DFP 2025, a correção baseada na DFP 2025 é aplicada antes da entrega do demonstrativo (antecipação já anotada em diario.md). Como nenhuma data da sonda de validação da Fase 3 (2018–2025) cai em 2026, a severidade é Fase 4.
2. Retorno total contra a ficha §5 (docs/metodologia/backtest.md)
Correções verificadas no intervalo:
BUG-3-43 (commit 9b0e74c): backtesting/backtest_pit.py e sentinela/data/pit/serie_ajustada.py (evento_emite_mesmo_papel) abstêm com MOTIVO_OUTRA_ESPECIE quando bonificação/desdobramento/grupamento emite ativo de outro ISIN (CYRE3, RENT3), provado em tests/regressao/test_bug_3_43_evento_outra_especie_retorno.py.
Espécie derivada do ISIN (BUG-3-45), natureza dos proventos (BUG-3-46), estado terminal e CDI a partir do último negócio (BUG-3-47), corte do FCA em T (BUG-3-48) e exclusão de data_com == T (BUG-3-54) verificados conforme a Tarefa 1.
Ressalvas identificadas (Severidade: Fase 4):
Ausência de filtro por espécie/ISIN nos laços de sem_prova e ex is None: Em backtesting/backtest_pit.py (relacao["sem_prova"]), linhas 617–624 (eventos_lidos["sem_prova"]) e linhas 626–638 (eventos_lidos["eventos"] quando ex is None), a abstenção por registro sem data-ex na janela inicio <= data_com < corte_com não filtra pela espécie/ISIN do ticker analisado, podendo abster conservadoramente uma classe por evento sem prova de outra classe do mesmo emissor.
Deslistagem sem Data_Fim_Negociacao preenchida no FCA: Quando um ativo foi deslistado antes de T sem Data_Fim_Negociacao no FCA vigente, _estado_terminal (backtesting/backtest_pit.py) devolve deslistagem=None, suspensao_confirmada=False e retorno_total (linhas 183–184) agora abstém com "estado terminal sem prova de suspensão ou deslistagem" (não produz mais retorno errado de 0% como antes do BUG-3-47).
3. Ligação produtor → consumidor
Ligações entregues e verificadas no intervalo:
remontagem.zip_informe_em → leitura.informe_fii → sentinela_informe_pit.json → CVMFIIProvider._recorte_informe (BUG-3-49).
b3_proventos.relacao_ate → MotorHistorico._buscar_proventos_b3 → fatores_acoes_b3.fatores_da_relacao → janelas_fundamentais.entradas (BUG-3-53).
correcoes.csv / identidades_fii.csv → universo.referencias_em → universo.indice_em → ReferenciaEm e universo_backtest (BUG-3-55).
AnalysisService._gravar_resultados (metodo="analise") → BacktestPIT._executar (sem_lentes) → scripts/banda_neutra_fase3.py (BUG-3-56).
sentinela/data/gordon_cvm.py e linhas 182–207 (BUG-3-57, commit 082f7b1): motivo de abstenção do Gordon passa a nomear os campos específicos ausentes na DFP, provado em tests/regressao/test_bug_3_57_gordon_nomeia_campo_ausente.py.
Desconexão estrutural na lente FiiYield no histórico (Severidade: Fase 4, destino F4-H03):
Em sentinela/services/historico.py (MotorHistorico._buscar_rendimento_fii), o motor histórico sempre preenche dados["b3_fundo"] = {"abstencao": "complemento da B3 do fundo: fonte só disponível como consulta corrente; desligada na data passada"}.
Em seguida, sentinela/data/rendimento_fii.py (avaliar) exige fii_elegibilidade.resposta_b3_valida(b3, codigo) para descartar eventos de cota e, como b3_fundo vem com "abstencao", toda avaliação histórica da lente FiiYield se abstém incondicionalmente na linha 337 com MOTIVO_EVENTOS_INDISPONIVEIS, independentemente do Informe Mensal estar completo no banco. Isso está coberto pelo xfail(strict=True) de tests/test_servico_historico.py (F4-H03).
Demais produtores ainda sem consumidor em produção (Severidade: Fase 4, destino F4-H09): sgs_432 em series_macro, _calendario_proventos_b3 no MotorHistorico, leitura.demonstrativo, leitura.modo_unico e b3_indices.mensal (ver B3 na Tarefa 1).
4. Regra econômica mudada sem ficha
Nenhuma regra econômica ou fórmula de método foi alterada sem ficha.
Nenhum arquivo em sentinela/methods/, valuation_engine.py, fii_engine.py ou portfolio_engine.py foi modificado em 9b0e74c..HEAD.
Quando a investigação de TGMA3 (F3-AUD-CB2, commit fb62f4c, diario.md) identificou que a abstenção do VPA 2024 decorre da regra D20 (2.03.09 == 0 no BPP consolidado com 3.11.02 != 0 na DRE), o executor manteve a regra intacta e encaminhou a decisão metodológica para a Fase 4 (F4-H05 em docs/loop/fila-fase4-proposta.md). O mesmo ocorreu com a ligação do FRE 2010–2019 (F4-H04, linha 23).
Tarefa 3 — Conferência do README.md e do Resumo da Fase contra o Código

Confrontei README.md, pr-fase-3.md, resumo-3a.md e resumo-3b.md com o código em HEAD.

O que confere com o código
Os números da suíte em README.md e pr-fase-3.md batem com a contagem real dos xfail(strict=True) no código: 24 xfails estritos no total (8 em test_bug_3_49_informe_fii_sem_recuo.py, 15 em test_bug_3_50_periodo_cvm_vigente_sem_numeros.py e 1 em test_servico_historico.py).
A tabela de cobertura por data e por lente em pr-fase-3.md, as limitações declaradas (linhas 227–234) e os resíduos documentais em arquivos travados (linhas 235–241) retratam com fidelidade o estado do código.
Imprecisões ou omissões identificadas (Severidade: Fase 4)
Descrição atenuada do BUG-3-50 (GA2b) em README.md:
O README.md resume a limitação como "documento vigente ilegível na CVM e no Informe de FII". No código, o que permanece aberto nos 15 xfail estritos de test_bug_3_50_periodo_cvm_vigente_sem_numeros.py (e está melhor descrito em pr-fase-3.md) é mais amplo do que arquivo CSV corrompido/ilegível: abrange qualquer período CVM (DFP ou ITR, anual, indicadores ou TTM) cuja versão vigente em D foi reapresentada depois de D (ficando no índice sem linhas numéricas nos CSVs abertos) ou retida por conflitos_carga (DD-57), além da escolha pela maior VERSAO em vez da última DT_RECEB < D, situações em que cvm_provider.py ainda recua silenciosamente ao período anterior.
Omissão de Lynch, Bancos e retorno total do FII no resumo de cobertura de README.md:
O texto diz: "com cobertura parcial nas oito datas anuais de 2018 a 2025 (Gordon em até 44 ações por data, Bazin em até 15, Graham só em 2025 e a lente do FII sem número)". Omite que Lynch produziu valor em apenas 1 ação em 2025 (e 0 de 2018 a 2024), Bancos em no máximo 3 ações por data (2023–2025, 0 de 2018 a 2022) e que o retorno total do FII no backtest também não está ligado (F3-8l, 0 retornos válidos em todas as datas). Esses números constam na tabela de pr-fase-3.md, mas não no README.md.
Demonstração de "as_of = hoje reproduz o resultado atual" em pr-fase-3.md:
A primeira linha da tabela de condições de saída em pr-fase-3.md:10 apresenta o SHA256 do golden (500645a3263ad25e…bcc) como demonstração de que as_of = hoje reproduz o resultado atual, sem repetir a ressalva registrada em resumo-3a.md e resumo-3b.md de que o harness do golden roda com AS_OF_GORDON = 20/10/2026 fixo (a equivalência para as_of = hoje é testada pelos testes de AnalysisService, não pelo hash do golden).
Causa da cobertura 0 na lente Rendimento do FII (pr-fase-3.md e diario.md):
Em diario.md, a cobertura 0/40 (0) a 0/150 (0) da linha Rendimento do FII é atribuída a "retorno do FII sem ligação, F3-8l". Na realidade, o primeiro número (0/150) conta quantos FIIs tiveram valor calculado pela lente (antes do cálculo de retorno), e ele é 0 porque MotorHistorico._buscar_rendimento_fii (sentinela/services/historico.py) desliga b3_fundo em toda data passada (F4-H03), fazendo rendimento_fii.avaliar abster sempre com MOTIVO_EVENTOS_INDISPONIVEIS.
O que não foi coberto ("não verificado")

Por restrição explícita da auditoria (somente leitura estática e proibição de abrir bancos, .env, logs e outputs/):

Conteúdo real do banco SQLite (data/sentinela.db e *.db) e dos artefatos gerados em outputs/ (como outputs/backtest_fase3.json e outputs/banda_neutra_fase3.md): não verificado diretamente (os números da sonda foram conferidos apenas contra o código dos scripts e contra os registros em docs/loop/historico/fase-3/).
Arquivos .env e logs de execução: não verificado.
Execução dinâmica de pytest, mutmut e scripts/gate.py: não verificado por execução (verificados estaticamente os códigos de produção e os arquivos de teste em tests/).