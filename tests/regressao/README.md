# Testes de regressão — todo bug vira teste

Decisão do Marcos de 15/10/2026, no fechamento das auditorias externas da Fase 2A
(`docs/loop/historico/fase-2a/auditoria-externa.md`).

## Regra

1. Bug confirmado (auditoria, revisão ou uso) vira teste em `tests/regressao/` no mesmo dia,
   antes de qualquer correção. Um arquivo por bug: `test_bug_<fase>_NN_<descricao>.py`.
2. Bug ainda não corrigido fica xfail estrito com ID e item que corrige:
   `@pytest.mark.xfail(strict=True, reason="BUG-2A-NN · <sintoma> · corrige: <item>")`.
   O `xfail_strict` do `pytest.ini` faz o CI quebrar se ele passar sem a marca ser retirada.
3. A correção retira a marca, o teste fica para sempre e o registro abaixo muda para
   "corrigido".
4. Nenhum item `fix:` fecha sem o teste de regressão do bug que corrige.

Cada teste exercita o comportamento correto esperado e falha hoje pelo sintoma do bug.
Bug que não se reproduz ao escrever o teste não entra como xfail: vai para o diário do
loop com a evidência ("não reproduzido").

O CI roda a suíte com `-rxX`, que lista os bugs abertos (xfailed) em cada execução. Para ver
a falha de cada um: `python -m pytest tests/regressao -q --runxfail`.

## Registro

A evidência aponta o código no momento do registro; depois da correção a linha pode não existir.

Origem: auditoria externa da Fase 2A (`docs/loop/historico/fase-2a/auditoria-externa.md`):
Codex, modo FASE, e Gemini 4 Argon em duas passadas (1ª e 2ª). Os destinos que eram
"proposta da 2B" passaram, no F2B-36, ao item da fila da Fase 2B que corrige cada bug.
BUG-2A-19 a 23: registrados no F2B-36 (18/10/2026). BUG-2B-01 a 12: confirmados pelo levantamento do F2B-21 (`docs/decisoes/fontes-fase2b.md`, perguntas 7 e 8) e registrados no F2B-43 (19/10/2026); o item que corrige cada um é decidido pelo Marcos no marcador "Fichas da 2B, taxa e fontes".

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2A-01 | LPA, VPA, ROE, P/L ou P/VP ≤ 0 da CVM descartados no merge; o valor positivo anterior ou do cache fica; prejuízo conta como dado ausente | `market_engine.py:133` (`_is_field_missing`), `:158` (`merge_if_valid`) | Gemini 1ª (14/10), Codex (15/10) | `test_bug_2a_01_cvm_nao_positivo_descartado.py` | F2B-8 | corrigido |
| BUG-2A-02 | reserva dos controladores liberada quando a conta existe com outra descrição (`MOTIVO_SEM_CORRESPONDENCIA`), contra a D20 | `sentinela/data/controladores.py:44` (`_AUSENTE`) | Gemini 1ª (14/10) e 2ª (15/10), Codex (15/10) | `test_bug_2a_02_controladores_sem_correspondencia.py` | F2A-41 | corrigido |
| BUG-2A-03 | linha dos controladores ausente devolve o lucro consolidado mesmo com minoritários no balanço (2.03.09 ≠ 0) | `sentinela/data/controladores.py:88` (`lucro_dos_controladores`) | Codex (15/10), Gemini 2ª (15/10) | `test_bug_2a_03_controladores_ausente_com_minoritarios.py` | F2A-41 | corrigido |
| BUG-2A-04 | minoritários do balanço lidos só no modelo do setor, enquanto as outras leituras da reserva usam todos os modelos | `cvm_provider.py:124` (`lucro_controladores_com_reserva`) | Gemini 1ª (14/10), Codex (15/10) | `test_bug_2a_04_minoritarios_so_no_modelo_do_setor.py` | F2A-41 | corrigido |
| BUG-2A-05 | PL total inválido (NaN, linhas divergentes) devolve `None` sem motivo | `sentinela/data/controladores.py:106` (`pl_dos_controladores`) | Gemini 2ª (15/10) | `test_bug_2a_05_pl_total_invalido_sem_motivo.py` | F2A-41 | corrigido |
| BUG-2A-06 | P/VP NaN ou infinito sai na saída do motor de FII | `fii_engine.py:92` (`analisar`) | Gemini 1ª (14/10), Codex (15/10) | `test_bug_2a_06_pvp_nao_finito_no_fii.py` | F2A-42 | corrigido |
| BUG-2A-07 | ativo fora do índice oficial (ex.: BPAC11) recebe métodos de ação: `classe_ativo` não é preenchido e a guarda do F2A-29 não dispara | `market_engine.py:494` (`_aplicar_referencia`), `valuation_engine.py:125` | Gemini 1ª (14/10) e 2ª (15/10), Codex (15/10) | `test_bug_2a_07_fora_do_indice_recebe_metodos.py` | F2A-43 | corrigido |
| BUG-2A-08 | relatório de rastreabilidade diz que o FII sem P/VP usa 1,0 | `sentinela/reports/rastreabilidade.py:394` | Gemini 2ª (15/10) | `test_bug_2a_08_rastreabilidade_pvp_um.py` | F2A-44 | corrigido |
| BUG-2A-09 | relatório de rastreabilidade diz que o LPA da CVM é lucro ÷ ações, quando desde o F2A-36 é o LPA divulgado da espécie | `sentinela/reports/rastreabilidade.py:67` (`LIMITES`), `:233` (`_proveniencia_derivada`) | Gemini 2ª (15/10) | `test_bug_2a_09_rastreabilidade_lpa_recalculado.py` | F2A-44 | corrigido |
| BUG-2A-10 | TTM lê o lucro dos controladores sem a regra 7.2 da ficha | `cvm_provider.py:739` (`_acumulados_do_arquivo`) | Gemini 1ª (14/10), Codex (15/10) | `test_bug_2a_10_ttm_sem_regra_7_2.py` | F2B-37 | corrigido |
| BUG-2A-11 | alerta do F2A-5 compara com o LPA divulgado antes do filtro de coerência | `market_engine.py:227` (`_lpa_divulgado_comparado`) | Gemini 1ª (14/10), Codex (15/10) | `test_bug_2a_11_alerta_lpa_antes_da_coerencia.py` | F2B-14 | corrigido |
| BUG-2A-12 | FII da CVM não registra `valores_por_fonte['CVM']`: checagem cruzada do P/VP vira identidade | `market_engine.py:696` (`_buscar_cvm_fii`) | Gemini 1ª (14/10), Codex (15/10) | `test_bug_2a_12_fii_sem_valores_por_fonte.py` | F2B-16 | corrigido |
| BUG-2A-13 | FII sem `cd_cvm` recebe o risco "ticker fora da cobertura da CVM" antes da busca do Informe | `market_engine.py:748` (`_buscar_cvm`) | Gemini 1ª (14/10), Codex (15/10) | `test_bug_2a_13_fii_risco_fora_da_cvm.py` | F2B-17 | corrigido |
| BUG-2A-14 | Informe Mensal reapresentado na mesma data escolhido sem desempate pela maior `Versao` | `cvm_fii_provider.py:153` (`obter_dados_fii`) | Codex (15/10) | `test_bug_2a_14_informe_sem_desempate_por_versao.py` | F2B-38 | corrigido |
| BUG-2A-15 | DY finito mas fora de 0–25% de uma fonte posterior sobrescreve DY válido anterior | `market_engine.py:607` (merge da brapi) | Codex (15/10) | `test_bug_2a_15_dy_invalido_sobrescreve_valido.py` | F2B-39 | corrigido |
| BUG-2A-16 | ZIP vazio do COTAHIST levanta `IndexError` fora das exceções tratadas | `sentinela/data/providers/b3_cotahist.py:97` (`ler_zip`) | Gemini 2ª (15/10), Codex (15/10) | `test_bug_2a_16_cotahist_zip_vazio.py` | F2B-40 | corrigido |
| BUG-2A-17 | método `FiiNav` classifica P/VP ≤ 0 como desconto | `sentinela/methods/fii_nav.py:45` | Gemini 2ª (15/10) | `test_bug_2a_17_fii_nav_pvp_nao_positivo.py` | F2B-41 | corrigido |
| BUG-2A-18 | método `Graham` com VPA < 0 calcula raiz de negativo (número complexo) em vez de se abster | `sentinela/methods/graham.py:71` | Gemini 2ª (15/10) | `test_bug_2a_18_graham_vpa_negativo.py` | F2B-42 | corrigido |
| BUG-2A-19 | arquivos do IF.data sem a proveniência da D16 (sem o `.proveniencia.json` lateral, data da coleta e hash), e o `Capital` sem ela | `sentinela/data/providers/ifdata.py:152` (`IFDataProvider._buscar`) | Gemini 2ª (15/10), conferido pelo Claude (18/10) | `test_bug_2a_19_ifdata_sem_proveniencia.py` | F2B-44 | aberto |
| BUG-2A-20 | validade do cache do IF.data medida pelo relógio (`time.time()`), não pelo instante de referência; resposta vazia (`value: []`) gravada e reaproveitada por até 7 dias | `sentinela/data/providers/ifdata.py:159` (`IFDataProvider._buscar`) | Gemini 2ª (15/10), conferido pelo Claude (18/10) | `test_bug_2a_20_ifdata_cache_pelo_relogio.py` | F2B-44 | aberto |
| BUG-2A-21 | ROE de fonte de mercado sem piso: −21 entra como −2.100% | `sentinela/data/normalizacao.py:112` (`guardar_roe`) | Gemini 1ª (14/10), decisão C | `test_bug_2a_21_roe_sem_piso.py` | F2B-18 | corrigido |
| BUG-2A-22 | preço negativo aceito nos dois motores (`acoes/preco-negativo` sai com Graham de R$ 12,25) | `valuation_engine.py:113` e `:118` (`processar`), `fii_engine.py:61` (`analisar`) | Gemini 1ª (14/10), ressalva ao F2A-25 | `test_bug_2a_22_preco_negativo_nos_motores.py` | F2B-20 | corrigido |
| BUG-2A-23 | motor de ações converte `divida_liq_ebitda` em texto pt-BR, que nenhuma fonte entrega desde o F2A-22; os testes desse caminho só conferem `0 <= score_final <= 100` | `valuation_engine.py:278` (`processar`) | Gemini 2ª (15/10) | `test_bug_2a_23_divida_em_texto_avaliada.py` | F2B-45 | aberto |
| BUG-2B-01 | ITR sem `DVA_con` perde a DRE inteira no TTM (lucro e receita somem com os proventos) | `cvm_provider.py` (`_acumulados_do_arquivo`; `acumulados_ttm` descarta o arquivo) | F2B-21, pergunta 7 (Gemini 1ª) | `test_bug_2b_01_ttm_sem_dva_perde_a_dre.py` | a decidir no marcador | aberto |
| BUG-2B-02 | o mesmo demonstrativo é lido e guardado duas vezes, para a série e para o TTM (só custo) | `cvm_provider.py` (`parsear_demonstrativo`, chave com `include_periodo`) | F2B-21, pergunta 7 (Gemini 1ª) | `test_bug_2b_02_demonstrativo_lido_duas_vezes.py` | a decidir no marcador | aberto |
| BUG-2B-03 | HTTP 404 tentado três vezes no download (só custo) | `cvm_download.py` (`baixar_arquivo`) | F2B-21, pergunta 7 (Gemini 1ª) | `test_bug_2b_03_404_tentado_de_novo.py` | a decidir no marcador | aberto |
| BUG-2B-04 | insumo inválido vira número em vez de abstenção: Composição sem a coluna ON, ROE com lucro NaN ou PL infinito, preço infinito, unit com quantidade fracionária | `cvm_provider.py` (`composicao_do_documento`), `sentinela/data/acoes_cvm.py` (`roe_dos_controladores`, `derivar_por_acao`) | F2B-21, pergunta 8 (auditoria externa da 2A, correção 6) | `test_bug_2b_04_insumo_invalido_sem_abstencao.py` | a decidir no marcador | aberto |
| BUG-2B-05 | divergência de ações compara a classe do yfinance com o total da espécie, com mais de uma classe preferencial | `sentinela/data/acoes_cvm.py` (`divergencia_acoes`), `market_engine.py` (`_por_acao_cvm`) | F2B-21, pergunta 8 (auditoria externa da 2A, correção 6) | `test_bug_2b_05_divergencia_com_classes_preferenciais.py` | a decidir no marcador | aberto |
| BUG-2B-06 | completude penaliza banco e FII por campos que o modelo deles não tem: banco por `receita_liquida`, `margem_liquida` e `divida_liq_ebitda` (com o resto, 70%); FII também por P/L, ROE e LPA (com preço, DY, P/VP e VPA, 40%); o teste do banco identifica o banco pelo setor "Bancos" | `data_quality.py` (`DataQualityReport.completude`) | F2B-21, pergunta 8 (auditoria externa da 2A, correção 6) | `test_bug_2b_06_completude_penaliza_banco_e_fii.py` | a decidir no marcador | aberto |
| BUG-2B-07 | LPA divulgado NaN ou zero aceito como coerente (o provedor já os descarta) | `sentinela/data/acoes_cvm.py` (`divulgados_coerentes`) | F2B-21, pergunta 8 (Gemini 2ª) | `test_bug_2b_07_divulgado_nan_ou_zero.py` | a decidir no marcador | aberto |
| BUG-2B-08 | `_meses` ignora o dia: 31/01 a 01/03 conta 3 meses | `sentinela/data/series_cvm.py` (`_meses`) | F2B-21, pergunta 8 (Gemini 2ª) | `test_bug_2b_08_meses_ignora_o_dia.py` | a decidir no marcador | aberto |
| BUG-2B-09 | duas gravações simultâneas da proveniência do mesmo arquivo colidem no `.tmp` (`FileNotFoundError`) | `sentinela/data/proveniencia.py` (`registrar_arquivo`) | F2B-21, pergunta 8 (Gemini 2ª) | `test_bug_2b_09_corrida_na_proveniencia.py` | a decidir no marcador | aberto |
| BUG-2B-10 | CNPJ com espaços nas pontas não acha a entrega no índice | `sentinela/data/proveniencia.py` (`entrega_no_indice`) | F2B-21, pergunta 8 (Gemini 2ª) | `test_bug_2b_10_cnpj_com_espacos.py` | a decidir no marcador | aberto |
| BUG-2B-11 | sigla da classe preferencial da ação avulsa sem caixa alta, e `especie_da_classe("pna")` devolve `"pna"` | `sentinela/data/referencia/montagem.py` (`montar_companhias`), `sentinela/data/acoes_cvm.py` (`especie_da_classe`) | F2B-21, pergunta 8 (Gemini 2ª) | `test_bug_2b_11_classe_preferencial_minuscula.py` | a decidir no marcador | aberto |
| BUG-2B-12 | tabela de correções aceita ticker fora do formato | `sentinela/data/referencia/correcoes.py` (`validar_correcoes`) | F2B-21, pergunta 8 (Gemini 2ª) | `test_bug_2b_12_ticker_invalido_na_correcao.py` | a decidir no marcador | aberto |
