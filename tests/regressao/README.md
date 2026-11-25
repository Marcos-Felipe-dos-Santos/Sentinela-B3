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
| BUG-2A-19 | arquivos do IF.data sem a proveniência da D16 (sem o `.proveniencia.json` lateral, data da coleta e hash), e o `Capital` sem ela | `sentinela/data/providers/ifdata.py:152` (`IFDataProvider._buscar`) | Gemini 2ª (15/10), conferido pelo Claude (18/10) | `test_bug_2a_19_ifdata_sem_proveniencia.py` | F2B-44 | corrigido |
| BUG-2A-20 | validade do cache do IF.data medida pelo relógio (`time.time()`), não pelo instante de referência; resposta vazia (`value: []`) gravada e reaproveitada por até 7 dias | `sentinela/data/providers/ifdata.py:159` (`IFDataProvider._buscar`) | Gemini 2ª (15/10), conferido pelo Claude (18/10) | `test_bug_2a_20_ifdata_cache_pelo_relogio.py` | F2B-44 | corrigido |
| BUG-2A-21 | ROE de fonte de mercado sem piso: −21 entra como −2.100% | `sentinela/data/normalizacao.py:112` (`guardar_roe`) | Gemini 1ª (14/10), decisão C | `test_bug_2a_21_roe_sem_piso.py` | F2B-18 | corrigido |
| BUG-2A-22 | preço negativo aceito nos dois motores (`acoes/preco-negativo` sai com Graham de R$ 12,25) | `valuation_engine.py:113` e `:118` (`processar`), `fii_engine.py:61` (`analisar`) | Gemini 1ª (14/10), ressalva ao F2A-25 | `test_bug_2a_22_preco_negativo_nos_motores.py` | F2B-20 | corrigido |
| BUG-2A-23 | motor de ações converte `divida_liq_ebitda` em texto pt-BR, que nenhuma fonte entrega desde o F2A-22; os testes desse caminho só conferem `0 <= score_final <= 100` | `valuation_engine.py:278` (`processar`) | Gemini 2ª (15/10) | `test_bug_2a_23_divida_em_texto_avaliada.py` | F2B-45 | corrigido |
| BUG-2B-01 | ITR sem `DVA_con` perde a DRE inteira no TTM (lucro e receita somem com os proventos) | `cvm_provider.py` (`_acumulados_do_arquivo`; `acumulados_ttm` descarta o arquivo) | F2B-21, pergunta 7 (Gemini 1ª) | `test_bug_2b_01_ttm_sem_dva_perde_a_dre.py` | F2B-46 | corrigido |
| BUG-2B-02 | o mesmo demonstrativo é lido e guardado duas vezes, para a série e para o TTM (só custo) | `cvm_provider.py` (`parsear_demonstrativo`, chave com `include_periodo`) | F2B-21, pergunta 7 (Gemini 1ª) | `test_bug_2b_02_demonstrativo_lido_duas_vezes.py` | F2C-13 | corrigido em 26/10/2026; leitura compartilhada entre série e TTM |
| BUG-2B-03 | HTTP 404 tentado três vezes no download (só custo) | `cvm_download.py` (`baixar_arquivo`) | F2B-21, pergunta 7 (Gemini 1ª) | `test_bug_2b_03_404_tentado_de_novo.py` | F2C-14 | corrigido em 26/10/2026; HTTP 404 encerra sem espera |
| BUG-2B-04 | insumo inválido vira número em vez de abstenção: Composição sem a coluna ON ou com tesouraria maior que a espécie, ROE com lucro NaN ou PL infinito, preço inválido apagando números independentes, LPA ilegível descartado na coleta, unit com quantidade fracionária | `cvm_provider.py` (`composicao_do_documento`), `sentinela/data/acoes_cvm.py` (`roe_dos_controladores`, `derivar_por_acao`) | F2B-21, pergunta 8 (auditoria externa da 2A, correção 6) | `test_bug_2b_04_insumo_invalido_sem_abstencao.py` | F2B-46 | corrigido |
| BUG-2B-05 | divergência de ações compara a classe do yfinance com o total da espécie, com mais de uma classe preferencial | `sentinela/data/acoes_cvm.py` (`divergencia_acoes`), `market_engine.py` (`_por_acao_cvm`) | F2B-21, pergunta 8 (auditoria externa da 2A, correção 6) | `test_bug_2b_05_divergencia_com_classes_preferenciais.py` | F2C-15 | corrigido em 26/10/2026; total PN não comparado à classe |
| BUG-2B-06 | completude penaliza banco e FII por campos que o modelo deles não tem: banco por `receita_liquida`, `margem_liquida` e `divida_liq_ebitda` (com o resto, 70%); FII também por P/L, ROE e LPA (com preço, DY, P/VP e VPA, 40%); o teste do banco identifica o banco pelo setor "Bancos" | `data_quality.py` (`DataQualityReport.completude`) | F2B-21, pergunta 8 (auditoria externa da 2A, correção 6) | `test_bug_2b_06_completude_penaliza_banco_e_fii.py` | F2B-46 | corrigido; reaberto em 25/10/2026 (a completude lia `modelo`, a cascata grava `modelo_bpp`; `test_bug_2b_06_reaberto_completude_le_o_modelo_da_cascata.py`) e corrigido no F2B-63 |
| BUG-2B-07 | LPA divulgado NaN ou zero aceito como coerente (o provedor já os descarta) | `sentinela/data/acoes_cvm.py` (`divulgados_coerentes`) | F2B-21, pergunta 8 (Gemini 2ª) | `test_bug_2b_07_divulgado_nan_ou_zero.py` | F2C-16 | corrigido em 26/10/2026; zero não informado, não finito inválido |
| BUG-2B-08 | `_meses` ignora o dia: 31/01 a 01/03 conta 3 meses | `sentinela/data/series_cvm.py` (`_meses`) | F2B-21, pergunta 8 (Gemini 2ª) | `test_bug_2b_08_meses_ignora_o_dia.py` | F2C-17 | corrigido em 26/10/2026; meses completos pelos limites declarados |
| BUG-2B-09 | duas gravações simultâneas da proveniência do mesmo arquivo colidem no `.tmp` (`FileNotFoundError`) | `sentinela/data/proveniencia.py` (`registrar_arquivo`) | F2B-21, pergunta 8 (Gemini 2ª) | `test_bug_2b_09_corrida_na_proveniencia.py` | F2C-18 | corrigido em 26/10/2026; temporário exclusivo e troca atômica |
| BUG-2B-10 | CNPJ com espaços nas pontas não acha a entrega no índice | `sentinela/data/proveniencia.py` (`entrega_no_indice`) | F2B-21, pergunta 8 (Gemini 2ª) | `test_bug_2b_10_cnpj_com_espacos.py` | F2C-19 | corrigido em 26/10/2026; trim restrito ao CNPJ |
| BUG-2B-11 | sigla da classe preferencial da ação avulsa sem caixa alta, e `especie_da_classe("pna")` devolve `"pna"` | `sentinela/data/referencia/montagem.py` (`montar_companhias`), `sentinela/data/acoes_cvm.py` (`especie_da_classe`) | F2B-21, pergunta 8 (Gemini 2ª) | `test_bug_2b_11_classe_preferencial_minuscula.py` | F2C-20 | corrigido em 26/10/2026; siglas em caixa alta sem perder a classe |
| BUG-2B-12 | tabela de correções aceita ticker fora do formato | `sentinela/data/referencia/correcoes.py` (`validar_correcoes`) | F2B-21, pergunta 8 (Gemini 2ª) | `test_bug_2b_12_ticker_invalido_na_correcao.py` | F2B-46 | corrigido |

| BUG-2B-13 | Proventos com só dividendos ou só JCP descartados | `sentinela/data/series_cvm.py` (`proventos`) | Decisão do Marcos de 19/10/2026, F2B-46 | `test_bug_2b_13_proventos_uma_rubrica.py` | F2B-46 | corrigido |
| BUG-2B-14 | CSV do Tesouro truncado gera AttributeError em data ausente e impede retorno do cache válido | `sentinela/data/providers/tesouro.py` (`ler_csv`, `baixar`) | Revisão do stage F2B-27, Codex (19/10/2026) | `test_bug_2b_14_tesouro_csv_truncado.py` | F2B-27 | corrigido |
| BUG-2B-15 | fator positivo sofre underflow e conversão nominal devolve zero para fluxo real não nulo | `sentinela/domain/units.py` (`fluxo_nominal`, `_fator_fluxo`) | Revisão do stage F2B-29, Codex (19/10/2026) | `test_bug_2b_15_fluxo_nominal_underflow.py` | F2B-29 | corrigido |
| BUG-2B-16 | corte do Tesouro usa dia UTC e aceita publicação só com data no próprio dia, em vez de America/Sao_Paulo após fim do dia | `sentinela/data/providers/tesouro.py` (`ler_snapshot`, `baixar`) | Conferência do marcador §2.2 durante F2B-29, Codex (19/10/2026) | `test_bug_2b_16_tesouro_corte_local.py` | F2B-47 | corrigido |
| BUG-2B-17 | LPA e fator de unit aceitam composição inválida ou lançam TypeError | `acoes_cvm.lpa_dos_metodos`, `market_engine._por_acao_cvm`, `series_cvm.exercicio` | Gemini FASE HEAD60e61e2; Claude; Marcos20/10/2026 | `test_bug_2b_17_unit_invalida.py` | F2B-48 | corrigido |
| BUG-2B-18 | ausência comprovada e motivos de proventos divergem entre série anual e TTM | `series_cvm.proventos`, `ttm`; `cvm_provider._acumulados_do_arquivo` | Gemini FASE HEAD60e61e2; Claude; Marcos20/10/2026 | `test_bug_2b_18_proventos_ttm.py` | F2B-48 | corrigido |
| BUG-2B-19 | coleta do download e corte de datas recusam snapshot próprio e CSV cumulativo | `providers.tesouro` | Gemini FASE HEAD60e61e2; Claude; Marcos20/10/2026 | `test_bug_2b_19_tesouro_observacao.py` | F2B-48 | corrigido |
| BUG-2B-20 | taxa/PU de aplicação zero interpretados como taxa zero em vez de sem oferta | `providers.tesouro.ler_csv` | Gemini FASE HEAD60e61e2; Marcos20/10/2026 | `test_bug_2b_20_tesouro_sem_oferta.py` | F2B-48 | corrigido |
| BUG-2B-21 | BTCI11/TRPL11 confirmados FII pela B3 viram UNKNOWN quando o ISIN não está no Informe | `referencia.montagem.montar_outros` (lacuna de enriquecimento do índice) | F2B-21, Gemini FASE, Marcos20/10/2026; evidência B3 no teste | `test_bug_2b_21_fiis_fora_do_informe.py` | F2C-21 | corrigido em 26/10/2026; identidade oficial complementar validada |

**BUG-2B-20 / F2B-48 — complemento 20/10/2026:** revisão taxa-real1.1 aprovada pelo Marcos; regressões permanentes distinguem zero econômico de sentinela, vetam aplicação inválida apenas na cesta escolhida, preservam referência sem recuo e registram exclusões. Invalidade/ausência de resgate suprime só a informação de resgate, com motivo.

| BUG-2B-22 | conflito histórico em referência não escolhida veta a cesta atual | sentinela/data/providers/tesouro.py (ler_csv) | Ressalva Gemini, aceite F2B-30, reprodução20/10/2026 | test_bug_2b_22_tesouro_conflito_cesta.py | F2B-30 | corrigido |

| BUG-2B-23 | provedor macro reúne ausência/tipo/NaN/infinito/domínio no mesmo motivo, contra marcador §2.1 | sentinela/data/providers/macro.py (_numero) | revisão1 do F2B-30,20/10/2026, antes do commit | test_bug_2b_23_macro_motivos_distintos.py | F2B-30 | corrigido |

| BUG-2B-24 | soma de taxas finitas excede o domínio de float e propaga OverflowError em vez de abstenção | sentinela/data/taxas.py (calcular) | conferência da matriz§4 no F2B-30,20/10/2026, antes do commit | test_bug_2b_24_taxa_real_soma_nao_finita.py | F2B-30 | corrigido |

| BUG-2B-25 | LPA básico agregado conflitante escolhe a primeira linha | cvm_provider.py (lpa_basico_agregado) | ressalva Gemini, aceite F2B-1,20/10/2026 | test_bug_2b_25_lpa_agregado_conflitante.py | F2B-1 | corrigido |
| BUG-2B-26 | espécie única inferida só do índice, contra Composição do Capital com ON e PN | market_engine.py (_por_acao_cvm) | ressalva Gemini, aceite F2B-1,20/10/2026 | test_bug_2b_26_especie_unica_composicao.py | F2B-1 | corrigido |
| BUG-2B-27 | reprocessamento usa DFP/composição ou contexto macro com evidência posterior ao as_of | sentinela/data/gordon_cvm.py e valuation_engine.py | revisão1 do F2B-1,20/10/2026 | test_bug_2b_27_gordon_evidencia_futura.py | F2B-1 | corrigido |
| BUG-2B-28 | valor extraordinário ilegível vira zero e deixa de impedir projeção | cvm_provider.py (gordon_do_documento) | conferência final do F2B-1,20/10/2026 | test_bug_2b_28_gordon_extraordinario_invalido.py | F2B-1 | corrigido |
| BUG-2B-29 | relação de proventos da B3 pelo nome de pregão com barra ("AMBEV S/A", "KLABIN S/A") vem vazia; o Bazin se abstém pela conferência do emissor | sentinela/data/providers/b3_proventos.py (coletar) | auditoria do Claude (chat) do F2B-48/F2B-30, sobre o F2B-31, 20/10/2026 | test_bug_2b_29_b3_nome_de_pregao_com_barra.py | F3-P01 (origem F2C-23) | corrigido (F3-P01) |
| BUG-2B-30 | `MacroProvider.registro` devolve `None` sem o motivo quando a cesta abstém ou a fonte falha; o Gordon mostrava "inflação incompatível com a janela da DFP" | sentinela/data/providers/macro.py (registro) e sentinela/data/gordon_cvm.py (entradas) | auditoria do Claude (chat) do F2B-48/F2B-30, achado 1, 20/10/2026 | test_bug_2b_30_taxa_real_sem_motivo.py | F2B-51 | corrigido |
| BUG-2B-31 | o `except` do provedor macro captura `KeyError` e `TypeError` e trata erro do código como falha da fonte | sentinela/data/providers/macro.py (registro) | mesma auditoria, ressalva 2 | test_bug_2b_31_macro_engole_erro_de_programacao.py | F2B-51 | corrigido |
| BUG-2B-32 | `data_divulgacao` do calendário do IBGE lida como UTC, e não no horário de Brasília (latente: só a data é usada) | sentinela/data/providers/macro.py (inflacao) | mesma auditoria, ressalva 3 | test_bug_2b_32_ibge_divulgacao_em_utc.py | F2B-51 | corrigido |
| BUG-2B-33 | o DY da B3 (gate, perfil e mediana do Bazin) usa o fechamento ajustado do yfinance, e a ficha pede o bruto | market_engine.py (_buscar_yfinance, _buscar_proventos_b3) | 2ª auditoria FASE do Codex, 20/10/2026 | test_bug_2b_33_bazin_gate_preco_ajustado.py | F2B-54 | corrigido |
| BUG-2B-34 | registro da relação B3 sem espécie legível é descartado: subcontagem ou falso zero | sentinela/data/proventos_b3.py (serie_12_meses) | mesma auditoria | test_bug_2b_34_provento_sem_especie_descartado.py | F2B-54 | corrigido |
| BUG-2B-35 | a conferência no yfinance só compara a soma da janela: eventos divergentes que se compensam passam | sentinela/data/proventos_b3.py (conferencia_yfinance) | mesma auditoria | test_bug_2b_35_conferencia_b3_soma_igual.py | F2B-54 | corrigido |
| BUG-2B-36 | rendimento de 12 meses do FII infinito com entradas finitas | sentinela/data/rendimento_fii.py (rendimento_12_meses) | mesma auditoria | test_bug_2b_36_rendimento_fii_nao_finito.py | F2B-54 | corrigido |
| BUG-2B-37 | duas linhas do Informe da mesma versão e valores diferentes: a primeira vence pela ordem | sentinela/data/rendimento_fii.py (_por_mes) | mesma auditoria | test_bug_2b_37_informe_conflitante_mesma_versao.py; reaberto (auditoria de fechamento, 25/10/2026: cotas, amortização e composição fora do conflito): test_bug_2b_37_reaberto_conflito_em_qualquer_campo.py | F2B-54; F2B-57 | corrigido |
| BUG-2B-38 | com D = 0 pela B3 e o yfinance sem dividendos (`{}`), a conferência diz "indisponível" | sentinela/data/proventos_b3.py (conferencia_yfinance) | revisão final do F2B-53, 21/10/2026 | test_bug_2b_38_conferencia_dy_zero.py | F2B-54 | corrigido |

| BUG-2B-39 | classe com espaço nas pontas contorna a guarda de escopo e recebe valor de ação | valuation_engine.py (processar) | revisão do F2A-29 citada na fila; reprodução no F2B-4, 21/10/2026 | test_bug_2b_39_classe_com_espacos.py | F2B-4 | corrigido |

| BUG-2B-40 | ROE nominal vira zero por underflow de valores positivos e o payout projetado divide por zero com teto ativo | sentinela/methods/bancos.py | revisão do F2B-3 antes do commit, 21/10/2026 | test_bug_2b_40_banco_roe_underflow.py | F2B-3 | corrigido |

| BUG-2B-41 | gate atribui presença zero a ticker ausente sem prova de cobertura da janela | sentinela/data/liquidez.py (avaliar) | revisão do F2A-10 antes do commit, 21/10/2026 | test_bug_2b_41_liquidez_cobertura_ausente.py | F2A-10 | corrigido |

| BUG-2B-42 | download falha com cache antigo, coletor não sinaliza mês indisponível e aplica gate à janela desatualizada | sentinela/data/providers/b3_cotahist.py (baixar_mes, HistoricoRecente.coletar) | revisão1 F2A-10, 21/10/2026 | test_bug_2b_42_liquidez_cache_antigo.py | F2A-10 | corrigido |

| BUG-2B-43 | quantidade de cotas fracionária no Informe (35% das linhas de 2026) tira o FII da lente de rendimento | sentinela/data/rendimento_fii.py (avaliar) | revisão do F2B-2 e decisão do Marcos de 25/10/2026 (ficha FII 1.2) | test_bug_2b_43_cotas_fracionarias_no_fii.py | F2B-55 | corrigido |

| BUG-2B-44 | o backtest grava "OK" para a abstenção de escopo do motor e quebra ao ler `score_final` | backtesting/backtest_engine.py (simular_analise_mensal) | revisão do F2B-4, 25/10/2026 | test_bug_2b_44_backtest_abstencao_de_escopo.py | F2B-4 | corrigido |

| BUG-2B-45 | a falha na coleta do relatório 16 do IF.data descarta a Basileia já lida | sentinela/data/providers/ifdata.py (ler_capital) | revisão do F2B-32, 25/10/2026 | test_bug_2b_45_ifdata_carteira_derruba_basileia.py | F2B-32 | corrigido |

| BUG-2B-46 | a lente de FII não confere o as_of, a data-base nem a idade do registro da NTN-B, e aceita Informe e B3 coletados depois do as_of | sentinela/data/rendimento_fii.py (entradas), fii_engine.py | auditoria de fechamento da 2B (Codex), 25/10/2026 | test_bug_2b_46_fii_sem_corte_temporal.py | F2B-58 | corrigido |

| BUG-2B-47 | composição de outra versão do Informe autoriza a lente de FII | sentinela/data/rendimento_fii.py (avaliar) | auditoria de fechamento da 2B (Codex), 25/10/2026 | test_bug_2b_47_fii_composicao_de_outra_versao.py | F2B-59 | corrigido |

| BUG-2B-48 | VP final inválido (ausente, zero, negativo, não finito, texto) não impede a elegibilidade do FII | sentinela/data/rendimento_fii.py (avaliar) | auditoria de fechamento da 2B (Codex), 25/10/2026 | test_bug_2b_48_fii_vp_final_invalido.py | F2B-60 | corrigido |

| BUG-2B-49 | amortização `NaN` declarada no Informe é lida como célula vazia e aceita como "sem amortização" (os `na_values` do pandas igualam vazio e `NaN`) | cvm_fii_provider.py (`_linhas_do_fundo`, `_parsear_complemento`, `_tabela`) | auditoria de fechamento da 2B (Codex), 25/10/2026 | test_bug_2b_49_fii_amortizacao_nan_literal.py | F2B-61 | corrigido |

| BUG-2B-50 | a abstenção do FII (lente abstida ou DY não confiável) devolve `fair_value = preço` e `upside = 0` | fii_engine.py (analisar), sentinela/reports/rastreabilidade.py | auditoria de fechamento da 2B (Codex), 25/10/2026 | test_bug_2b_50_fii_abstencao_com_numero.py | F2B-62 | corrigido; reaberto em 25/10/2026 na auditoria rápida do fechamento (Codex): o card "Valor Justo" do `app.py` convertia a ausência em R$ 0.00 (`test_bug_2b_50_reaberto_app_valor_justo_da_abstencao.py`) e corrigido no F2B-69 |

| BUG-2C-01 | complemento cadastral de FII aceita CODBDI conflitante conforme a ordem do COTAHIST | sentinela/data/referencia/montagem.py (montar_outros) | revisão interna F2C-21, 26/10/2026 | test_bug_2c_01_fii_codbdi_conflitante.py | F2C-21 | corrigido em 26/10/2026; todas as categorias do grupo devem ser 12 |

| BUG-2C-02 | leitores B3 distintos com igualdade/hash iguais compartilham dados e proveniência no cache | sentinela/data/providers/b3_proventos.py e b3_fundos.py | revisão interna F2C-26, 26/10/2026 | test_bug_2c_02_cache_identidade_leitor.py | F2C-26 | corrigido em 26/10/2026; chave por identidade com referência retida |

| BUG-2C-03 | BPP não lido/correspondente autoriza reserva | cvm_provider._acumulados_do_arquivo; seis estados reproduzidos | F2C-29/30, Codex26/10 | test_bug_2c_03_ttm_bpp_nao_demonstrado.py | F2C-30 | corrigido |

| BUG-2C-04 | Fluxos aceitos com marcador BPP de outro modelo | cvm_provider._acumulados_do_arquivo | Codex26/10, F2C-30 | test_bug_2c_04_ttm_modelo_incompativel.py | F2C-30 | corrigido |

| BUG-2C-05 | TTM subtrai perímetros distintos ou sem demonstração | series_cvm.trimestres/ttm | revisão interna F2C-30,26/10 | test_bug_2c_05_ttm_perimetros.py | F2C-30 | corrigido |

| BUG-2C-06 | Fronteira anual apaga TTM e converte erro de programação em ausência | MarketEngine._serie_cvm/_buscar_cvm; CVMProvider.calcular_indicadores/acumulados_ttm | Codex, F2C-31,26/10 | test_bug_2c_06_cvm_fronteiras_independentes.py | F2C-31 | corrigido |

| BUG-2C-07 | Seleção civil omite DFP corrente de exercício encerrado em fevereiro | CVMProvider.acumulados_ttm; MarketEngine._serie_cvm | Codex26/10, F2C-31 | test_bug_2c_07_cvm_exercicio_nao_civil.py | F2C-31 | corrigido |

| BUG-2C-08 | Download de proventos elimina indicadores anuais já lidos | CVMProvider.indicadores_da_serie | Codex26/10, F2C-31 | test_bug_2c_08_serie_dva_independente.py | F2C-31 | corrigido |
| BUG-2C-09 | Leitura da escala deixa erro de formato escapar | CVMProvider._escala_da_composicao | Codex26/10, F2C-31 | test_bug_2c_09_escala_itr_formato.py | F2C-31 | corrigido |

| BUG-2C-10 | Escala do ITR reserva lucro total sem BPP lido | CVMProvider._escala_da_composicao | Codex26/10, F2C-31 | test_bug_2c_10_escala_itr_bpp_ausente.py | F2C-31 | corrigido |


### Achados do F2C-32 (27/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-11 | Conferência da unit compara média recalculada com primeira classe em vez da soma ponderada | contratos-fronteiras-dados-2c.md | F2C-32,27/10/2026 | `test_bug_2c_11_unit_conferencia_ponderada.py` | F3-P03 (origem F2C-50) | corrigido (F3-P03) |
| BUG-2C-12 | Falha do Informe não é propagada a riscos_dados | contratos-fronteiras-dados-2c.md | F2C-32,27/10/2026 | `test_bug_2c_12_informe_risco_ausente.py` | F3-P04 (origem F2C-51) | corrigido (F3-P04) |
| BUG-2C-13 | Literal OData CodInst interpola apóstrofo sem escape | contratos-fronteiras-dados-2c.md | F2C-32,27/10/2026 | `test_bug_2c_13_odata_literal_codinst.py` | F3-P05 (origem F2C-52) | corrigido (F3-P05) |
| BUG-2C-14 | Prompt não distingue classe inferida de classe oficial | contratos-fronteiras-dados-2c.md | F2C-32,27/10/2026 | `test_bug_2c_14_prompt_classe_inferida.py` | F3-P06 (origem F2C-53) | corrigido (F3-P06) |

### Correção F2C-36 (27/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-15 | IF.data selecionado pelo setor em vez do BPP | MarketEngine._buscar_ifdata | F2C-36,27/10/2026 | `test_bug_2c_15_ifdata_modelo_bpp.py` | F2C-36 | corrigido, quatro casos permanentes |

### Achado F2C-37 (27/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-16 | Inadimplência é lida sem prova de publicação da data-base até o corte | ifdata.ler_capital | F2C-37,27/10/2026 | `test_bug_2c_16_ifdata_sem_calendario.py` | F2C-37 | corrigido, dois casos permanentes |

### Correções F2C-39 (27/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-17 | Seguradora conhecida recebe motivo de modelo desconhecido | data_quality.completude | F2C-39,27/10/2026 | `test_bug_2c_17_motivo_seguradora_qualidade.py` | F2C-39 | corrigido |
| BUG-2C-18 | Instante sem fuso recebe motivo de indisponibilidade documental | ValuationEngine.processar | F2C-39,27/10/2026 | `test_bug_2c_18_motor_asof_sem_fuso.py` | F2C-39 | corrigido |
| BUG-2C-19 | Classe vazia recebe motivo de classe fora de escopo | ValuationEngine.processar | F2C-39,27/10/2026 | `test_bug_2c_19_classe_vazia_ausente.py` | F2C-39 | corrigido |
| BUG-2C-20 | Modelo válido é recusado por caixa/espaços | ValuationEngine.processar | F2C-39,27/10/2026 | `test_bug_2c_20_caixa_modelo_bpp_motor.py` | F2C-39 | corrigido |

### Correções F2C-40 (27/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-21 | Aviso de alavancagem omite motivo CVM já informado | ValuationEngine.processar | F2C-40,27/10/2026 | `test_bug_2c_21_motivo_aviso_alavancagem.py` | F2C-40 | corrigido |
| BUG-2C-22 | Inteiro numérico é tratado como ausência/valor inválido, diferente do mesmo inteiro nativo | ValuationEngine.processar | F2C-40,27/10/2026 | `test_bug_2c_22_inteiro_numerico_alavancagem.py` | F2C-40 | corrigido |

### Correções F2C-44 (27/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-23 | Documento bancário ausente vira datas None no relatório | rastreabilidade.construir_contexto | F2C-44,27/10/2026 | `test_bug_2c_23_documento_banco_relatorio.py` | F2C-44 | corrigido |
| BUG-2C-24 | NTN-B recusada aparece como taxa da lente | rastreabilidade.construir_contexto | F2C-44,27/10/2026 | `test_bug_2c_24_taxa_recusada_relatorio_fii.py` | F2C-44 | corrigido |
| BUG-2C-25 | Limites do relatório de ação dizem Selic usada | rastreabilidade.LIMITES | F2C-44,27/10/2026 | `test_bug_2c_25_selic_usada_relatorio_acao.py` | F2C-44 | corrigido |

### Correção F2C-46 (27/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-26 | Volume inferior ao mínimo arredonda para o próprio mínimo no texto da abstenção | liquidez.avaliar | F2C-46,27/10/2026 | `test_bug_2c_26_volume_arredondado_no_minimo.py` | F2C-46 | corrigido |

### Achado F2C-47 (27/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-27 | Complemento e composição com todas as versões ilegíveis casam por -inf e produzem rendimento | Dicionário CVM / ficha FII 1.3 §3/§3c | F2C-47,27/10/2026 | `test_bug_2c_27_versao_fii_ilegivel.py` | F3-P08 (origem F2C-55) | corrigido (F3-P08) |

### Achado F2C-7 (27/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-28 | P/L negativo entra silenciosamente na média dos pares | F2C-7 exige política aprovada ou comparação indisponível | F2C-7 | `test_bug_2c_28_peers_pl_negativo.py` | F2C-7 | corrigido |

### Achado F2C-8 (27/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-29 | Auditoria fabrica valor justo/preço e upside zero em FII abstido ou com exceção | D24 e aceite F2B-67 | F2C-8 | `test_bug_2c_29_auditoria_fii_abstido.py` | F2C-8 | corrigido |

### Achados da implementação F2C-1 (28/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-30 | Grahamreconstrói lucro por preço/PLe ignora3,20direto | fichaGraham2.0aprovada | F2C-1 | test_bug_2c_30_graham_insumo_direto.py | F2C-1 | corrigido |
| BUG-2C-31 | Lynchaplica1,5ao crescimento emvezdem1 | fichaLynch2.0aprovada41,472 | F2C-1 | test_bug_2c_31_lynch_multiplicador.py | F2C-1 | corrigido |

### Achado da revisão F2C-1 (28/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-32 | Motivo da janela encobre inaplicabilidade por modelo no relatório | D24: motivo da abstenção efetiva por lente | revisão F2C-1 | `test_bug_2c_32_motivo_relatorio_janela.py` | F2C-1 | corrigido |

### Achados da revisão 2 e integração B3 do F2C-1 (28/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-33 | Motivo documental das ações perdido na janela | Fichas2.1: causa e documento explícitos | revisão2 F2C-1 | `test_bug_2c_33_motivo_acoes_janela.py` | F2C-1 | corrigido |
| BUG-2C-34 | Abstenção apaga janela/fontes/regime/aviso | D24 e fichas2.1, metadados mesmo sem valor | revisão2 F2C-1 | `test_bug_2c_34_metadados_abstencao_janela.py` | F2C-1 | corrigido |
| BUG-2C-35 | Fator oficial B3 coletado não consumido pela janela | Fichas2.1: fator existente ajusta LPA | integração F2C-1 | `test_bug_2c_35_fator_b3_janela.py` | F2C-1 | corrigido |
| BUG-2C-36 | Evento fora do par documental bloqueia fator elegível por espécie desconhecida | Datas oficiais delimitam o par antes da espécie | revisão3 F2C-1 | `test_bug_2c_36_evento_fora_janela.py` | F2C-1 | corrigido |

### Achado F2C-12 (28/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-37 | DY da cascata chegava a Lynch com perfilB3 e payout não tinha contexto comum | FichaLynch2.1, DYzero válido/preço mesma referência | F2C-12 | `test_bug_2c_37_lynch_fonte_payout.py` | F2C-12 | corrigido |
| BUG-2C-38 | Underflow final transforma payout positivo em zero | Positividade de DY×preço/LPA, aritméticaDecimal | F2C-12 | `test_bug_2c_38_payout_underflow.py` | F2C-12 | corrigido |
| BUG-2C-39 | DY ausente/bool/vazio vira zero confiável no perfil quando falta B3 | FichaLynch2.1, duas fontes inválidas não demonstram perfil | F2C-12 | `test_bug_2c_39_lynch_dy_ausente.py` | F2C-12 | corrigido |

### Achados F2C-2 (29/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-40 | Razão de ROE positiva não representável vira zero observado | Ficha qualidade1.0, positivo não é zero por underflow | revisão durante F2C-2 | `test_bug_2c_40_qualidade_razao_underflow.py` | F2C-2 | corrigido |
| BUG-2C-41 | Perímetro malformado causa TypeError no quadro | Ficha qualidade1.0, falta de evidência deve ficar parcial | revisão durante F2C-2 | `test_bug_2c_41_qualidade_metadados_invalidos.py` | F2C-2 | corrigido |
| BUG-2C-42 | Nova leitura do PL inicial deixa download fora da fronteira de falha da fonte | Série anual já lida deve ser preservada | suíte F2C-2 / BUG-2C-08 | `test_bug_2c_42_pl_inicial_falha_download.py` | F2C-2 | corrigido |
| BUG-2C-43 | Proveniência B3 não Mapping derruba o quadro de qualidade | Ficha qualidade1.0, fonte inválida deve produzir motivo por indicador | revisão F2C-2 | `test_bug_2c_43_qualidade_fonte_b3_malformada.py` | F2C-2 | corrigido |
| BUG-2C-44 | Relatório tenta tratar proveniência inválida como Mapping | Ficha qualidade1.0, causa explícita em quadro parcial | revisão F2C-2 | `test_bug_2c_44_qualidade_relatorio_fonte_invalida.py` | F2C-2 | corrigido |
| BUG-2C-45 | Valor B3 recusado não finito reaparece na fonte da saída descritiva | Fonte do indicador não deve reintroduzir valor recusado | revisão F2C-2 | `test_bug_2c_45_qualidade_provento_nao_finito.py` | F2C-2 | corrigido |
| BUG-2C-46 | Calendário anual vazio certifica zeros B3 com cobertura integral | Ausência de calendário não prova ano sem provento | pré-revisão F2C-2 | `test_bug_2c_46_calendario_vazio_nao_cobertura.py` | F2C-2 | corrigido |
| BUG-2C-47 | Registro B3 não Mapping derruba parsing da fonte anual | Fonte inválida deve preservar quadro parcial | pré-revisão F2C-2 | `test_bug_2c_47_qualidade_registros_b3_invalidos.py` | F2C-2 | corrigido |
| BUG-2C-48 | Fonte não textual certifica dados e NaN reaparece na proveniência auxiliar | Fonte documental deve ser identificada em texto e saída finita | pré-revisão F2C-2 | `test_bug_2c_48_qualidade_proveniencia_nao_textual.py` | F2C-2 | corrigido |
| BUG-2C-49 | CNPJ/modelo explicitamente conflitantes não interrompem agregação | Ficha qualidade1.0: mesma entidade/modelo | pré-revisão F2C-2 | `test_bug_2c_49_qualidade_identidade_conflitante.py` | F2C-2 | corrigido |
| BUG-2C-50 | Saneamento apaga texto legítimo da reserva D20 na fonte do PL inicial | Reserva textual de controladores.Resultado deve ser preservada | pré-revisão F2C-2 | `test_bug_2c_50_qualidade_reserva_textual.py` | F2C-2 | corrigido |

### Achado F2C-3 (29/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-51 | Score/classificação agregados substituem distância por lente | Ficha apresentação1.0, decisões28/10 e29/10 | F2C-3 | `test_bug_2c_51_score_agregado.py` | F2C-3 | corrigido |
| BUG-2C-52 | Guarda do banco abstido encobre motivos individuais das lentes já avaliadas | Causas efetivas por lente, ficha apresentação1.0 | conferência F2C-3 | `test_bug_2c_52_lentes_banco_abstido.py` | F2C-3 | corrigido |

### Achado F2C-5 (29/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-53 | Síntese única de lentes heterogêneas ou preço no lugar de método ausente | Ficha apresentação1.0/decisões28–29/10 | F2C-5 | `test_bug_2c_53_sintese_agregada.py` | F2C-5 | corrigido |
| BUG-2C-54 | Persistência da nova apresentação inventa score/rótulo padrão ou herda resíduo do cache | Apresentação1.0 sem síntese, D29 sem migração | integração F2C-5 | `test_bug_2c_54_persistencia_sintese.py` | F2C-5 | corrigido |
| BUG-2C-55 | Transporte tipado fabrica campos agregados e serviço herda síntese do cache no novo contrato | Apresentação1.0/compatibilidade de leitores | integração F2C-5 | `test_bug_2c_55_transporte_sintese.py` | F2C-5 | corrigido |
| BUG-2C-56 | Critério Bazin aparece sem DY bruto e preço/data que o fundamentam, confundindo referências distintas | Ficha apresentação1.0: hipótese, fonte e referência por lente | pré-revisão F2C-5 | `test_bug_2c_56_bazin_base_dy_visivel.py` | F2C-5 | corrigido |
| BUG-2C-57 | UI omite a causa global de quadro de qualidade parcial apesar de cinco documentos | Qualidade1.0: cobertura não é comparabilidade | pré-revisão F2C-5 | `test_bug_2c_57_ui_qualidade_parcial.py` | F2C-5 | corrigido |

### Achado F2C-4 (30/10/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-58 | Leitores CLI fabricam síntese zero ou pedem veredito para apresentação1.0 | Ficha apresentação1.0§8, lentes separadas sem sinal | inventário F2C-4 | `test_bug_2c_58_cli_lentes.py` (desde o F3-9c-aud, a invariante da linha de comando mora no apresentador das lentes do app, `test_app_mostra_lente_abstida_sem_score_ou_valor_zero`; o script `auditar_recomendacoes.py` saiu) | F2C-4 | corrigido |
| BUG-2C-59 | Invariantes históricos ignoram números inválidos no transporte valuation/raw | Invariantes externos de finitude e score[0,100], compatibilidadeF2C-4 | revisão F2C-4 | `test_bug_2c_59_invariantes_historicas.py` | F2C-4 | corrigido |
| BUG-2B-51 | venda parcial recalcula o preço médio pela média ponderada com o preço de venda (100 a R$ 10, venda de 50 a R$ 20: PM vira R$ 0,00), contra a regra do custo médio | database.py (adicionar_posicao) | auditoria rápida do fechamento (F2B-69), "Ficam para o Marcos" (xfail sem ID); registrado pós-fechamento, 25/10/2026 | tests/test_database_posicoes.py::test_venda_parcial_preserva_preco_medio (mantido nesse arquivo, fora de `tests/regressao/`) | F3-P02 (origem F2C-48) | corrigido (F3-P02) |

| BUG-2B-52 | o caminho DISTRESSED do motor de ações devolve `fair_value = preço` e `upside = 0`, números que parecem resultado sem método calculado | valuation_engine.py (processar, guarda de `DISTRESSED_TICKERS`) | auditoria rápida do fechamento (F2B-69), "Ficam para o Marcos" (fora da decisão 2 do F2B-69, card "Valor Justo"); registrado pós-fechamento, 25/10/2026 | test_bug_2b_52_distressed_valor_justo_preco.py | F2C-5 | corrigido pela apresentação separada; regressão pós-2B integrada no MERGE-MAIN-2C, XPASS estrito confirmado antes da retirada da marca |

### Achado da auditoria de fechamento 2C (09/11/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-60 | Análise pós-F2C-3 sem score agregado sai como FORA_DO_ESCOPO no backtest | Decisão Marcos 09/11/2026, opção (a): INDISPONIVEL até reconstrução na Fase 3 | auditoria Claude de fechamento 2C | `test_bug_2c_60_backtest_sem_score.py` | correção de fechamento 2C | corrigido |

### Correções da auditoria FASE (09/11/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-2C-61 | Produtor TTM não declara comparabilidade demonstrada pelos documentos | decisão Marcos09/11 opção a | auditorias Gemini/Claude | `test_bug_2c_61_ttm_produtor.py` | FC2C-61 | corrigido |
| BUG-2C-62 | Produtor anual não emite comparabilidade e impede média ROE da qualidade | decisão Marcos09/11 opção a | auditorias Gemini/Claude | `test_bug_2c_62_qualidade_produtor.py` | FC2C-62 | corrigido |
| BUG-2C-63 | Aviso perde motivo CVM transportado em alavancagem_cvm.motivos | contrato F2C-40 e decisão09/11 | auditorias Gemini/Claude | `test_bug_2c_63_alavancagem_cascata.py` | FC2C-63 | corrigido |
| BUG-2C-64 | Banco com lente aplicada recebe aviso de medida inaplicável | decisão Marcos09/11 F2C-45(iii) | auditorias Gemini/Claude | `test_bug_2c_64_banco_aviso.py` | FC2C-64 | corrigido; predicado golden autorizado em09/11/2026 |
| BUG-2C-65 | CLI do índice perde identidades FII já ligadas à cascata | identidade oficial B3 arquivada e decisão09/11 | auditorias Gemini/Claude | `test_bug_2c_65_cli_identidades_fii.py` | FC2C-65 | corrigido |
| BUG-2C-66 | Coleta corrente perde seleção do exercício anual não civil | datas publicadas CVM e decisão09/11 | auditorias Gemini/Claude | `test_bug_2c_66_exercicio_nao_civil_cascata.py` | FC2C-66 | corrigido |
| BUG-2C-67 | Evento entre espécies alheias ao ticker bloqueia fator oficial elegível | critério de componentes e decisão09/11 | auditorias Gemini/Claude | `test_bug_2c_67_eventos_outras_especies.py` | FC2C-67 | corrigido |
| BUG-2C-68 | MACD atual usa ordens de negociação no rótulo de cruzamento | vocabulário neutro obrigatório e decisão09/11 | auditorias Gemini/Claude | `test_bug_2c_68_macd_neutro.py` | FC2C-68 | corrigido |

### Destinos pós-fechamento 2C (09/11/2026)

Os sete bugs abertos em oito casos xfail estritos foram migrados à proposta não ativada `docs/loop/fila-fase3-proposta.md` (F3-P01/02/03/04/05/06/08). O oitavo caso é a segunda parametrização de BUG-2C-13. Marcas, condições e asserções preservadas; apenas destinos atualizados. F2C-54, sem xfail próprio, é F3-P07. A ratificação F2C-47 não fecha BUG-2C-27.

### Fase 3 (a partir de 10/11/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-3-01 | importar `config` chama o BCB (Selic, série 432), porque `MACRO = MacroContext()` buscava a Selic no construtor | `config.py:230` (`MacroContext.__init__`), `:305` (`MACRO`) | E-6 (auditoria red team de 9/9/2026), F3-1a | `test_bug_3_01_config_import_com_rede.py` | F3-1a | corrigido |
| BUG-3-02 | com o Informe fora do ar, `obter_rendimentos_fii` engole a falha de cada ano e devolve rendimento vazio sem risco; a falha não chega a `riscos_dados` | `cvm_fii_provider.py:278` (`obter_rendimentos_fii`) | revisão do F3-P04, 10/11/2026 | `test_bug_3_02_informe_real_fora_do_ar_sem_risco.py` | F3-P04 | corrigido |
| BUG-3-03 | ano corrente do Informe legível sem linhas do fundo e os dois anos anteriores ilegíveis: `obter_rendimentos_fii` devolve rendimento vazio sem risco | `cvm_fii_provider.py:283` (`obter_rendimentos_fii`) | revisão do F3-P04, 10/11/2026; decisão do Marcos de 10/11/2026 | `test_bug_3_03_informe_parcial_sem_risco.py` | F3-3c-fix | corrigido |
| BUG-3-04 | mês da janela antes do final só com versões ilegíveis continua dando DY e VP; a guarda do F3-P08 só olha o mês final | `sentinela/data/rendimento_fii.py:275` (`avaliar`) | F3-P08, 10/11/2026; decisão do Marcos de 10/11/2026 | `test_bug_3_04_versao_ilegivel_fora_do_mes_final.py` | F3-3c-fix | corrigido |
| BUG-3-05 | no mês final, linha com versão ilegível e linha sem versão valem as duas −inf, e a ordem do arquivo decide entre abstenção e rendimento | `sentinela/data/rendimento_fii.py:100` (`_por_mes`), `:275` | F3-P08, 10/11/2026; decisão do Marcos de 10/11/2026 | `test_bug_3_05_empate_ilegivel_sem_versao_pela_ordem.py` | F3-3c-fix | corrigido |
| BUG-3-06 | `MacroContext.registro_por_data` devolve só valor e data: fonte, coleta, hash e aviso de cache do `MacroProvider.serie_sgs` somem | `config.py:301` (`registro_por_data`) | auditoria FASE do Codex, 10/11/2026 | `test_bug_3_06_macro_perde_proveniencia.py` | F3-1d | corrigido |
| BUG-3-07 | CDI diário finito e extremo lança `OverflowError` na anualização; doze meses de IPCA extremos dão `inf` | `sentinela/data/macro_por_data.py:118` (`cdi`), `:155` (`ipca_12m`) | auditoria FASE do Codex, 10/11/2026 | `test_bug_3_07_macro_resultado_nao_finito.py` | F3-1d | corrigido |
| BUG-3-08 | `true`/`false` do JSON do SGS viram 1,0/0,0 na leitura (`float(True)`) e passam como taxa observada | `sentinela/data/macro_por_data.py:72` (`ler_sgs`) | auditoria FASE do Codex, 10/11/2026 | `test_bug_3_08_sgs_booleano_vira_taxa.py` | F3-1d | corrigido |
| BUG-3-09 | `restaurar` de uma cópia ausente cria o arquivo pelo `sqlite3.connect` e certifica banco vazio como restauração igual | `sentinela/data/store/backup.py:143` (`restaurar`), `:112` (`_backup`) | auditoria FASE do Codex, 10/11/2026 | `test_bug_3_09_restauracao_ausente_certificada.py` | F3-2a-fix | corrigido |
| BUG-3-10 | segunda execução do backup no mesmo diretório troca o `backup.json` verificado por um relatório só com o erro | `sentinela/data/store/backup.py:181` (`main`) | pendência do F3-2a; auditoria FASE do Codex, 10/11/2026; decisão 34 do Marcos | `test_bug_3_10_backup_repetido_apaga_manifesto.py` | F3-2a-fix | corrigido |
| BUG-3-11 | API pública `analyze(as_of=...)` contorna a guarda de `analisar` e mistura cascata corrente com corte passado | `sentinela/services/analyze_asset.py` (`analyze`) | revisão F3-6a, 10/11/2026, decisão 1/F3-6a | `test_bug_3_11_analyze_contorna_corte_temporal.py` | F3-6a | corrigido |
| BUG-3-12 | `_serie_cvm` usa o relógio real mesmo com `as_of` explícito na cascata; série, TTM e snapshot podem ler exercício posterior ao corte | `market_engine.py` (`_serie_cvm`, `_buscar_cvm`) | FC2C-66R, F3-P13, conferência de 10/11/2026 | `test_bug_3_12_serie_cvm_ignora_as_of.py` | F3-P13 | corrigido |
| BUG-3-13 | snapshot de provedor antigo recebe `as_of` redundante junto de `ano_final` já selecionado e lança TypeError | `market_engine.py` (`_buscar_cvm`) | aceite de compatibilidade F3-P13, conferência de 10/11/2026 | `test_bug_3_13_cvm_legado_recebe_as_of.py` | F3-P13 | corrigido |
| BUG-3-14 | golden alterado no stage, com a cópia de trabalho de volta ao `HEAD`, passa no gate sem `--golden-autorizado` | `scripts/gate.py` (`golden`: `HEAD:` contra `git hash-object` da cópia de trabalho) | auditoria cruzada da 3-a, Codex, 11/11/2026 | `test_bug_3_14_gate_golden_no_stage.py` | F3-A-F1 | corrigido |
| BUG-3-15 | a DFP recebida depois do corte (`DT_RECEB` 01/03/2024) entra na série e no lucro no corte de 31/12/2023: o corte é pelo fim do período, não pela entrega | `cvm_provider.py` (`exercicio_anual_mais_recente`), `market_engine.py` (`_serie_cvm`) | auditoria cruzada da 3-a, Claude, 11/11/2026 | `test_bug_3_15_serie_cvm_documento_entregue_apos_corte.py` | F3-3d | corrigido |
| BUG-3-16 | o preço da cascata sai sem data; o registro imutável do resultado grava `data_preco` nula | `market_engine.py` (`_buscar_yfinance`), `sentinela/services/analyze_asset.py` (`_gravar_resultados`) | auditoria cruzada da 3-a, Claude, 11/11/2026 | `test_bug_3_16_resultado_sem_data_do_preco.py` | F3-A-F3 | corrigido |
| BUG-3-17 | último fechamento `NaN` do yfinance: a fonte do preço fica `yfinance` quando a brapi preenche o preço; sem a brapi, o preço `NaN` segue com a data desse fechamento e o `currentPrice` é ignorado | `market_engine.py` (`_buscar_yfinance`, ramo de preço da `_buscar_brapi`) | revisão do F3-A-F3, 11/11/2026 | `test_bug_3_17_fechamento_invalido_do_yfinance.py` | F3-A-F5 | corrigido |
| BUG-3-18 | a Selic baixada em janelas de até 10 anos é gravada em `series_macro` com a fonte e o hash da primeira janela em todas as observações | `sentinela/data/providers/macro.py` (`gravar_series`, `_selic`) | auditoria externa do Gemini sobre 284165f..419f010, achado 1, 11/11/2026 | `test_bug_3_18_selic_com_hash_da_primeira_janela.py` | F3-A-F6 | corrigido |
| BUG-3-19 | linha duplicada do mesmo título e data-base no CSV do Tesouro dá `IntegrityError` não capturado e derruba o `gravar_series` antes das outras famílias; linha malformada de título fora da cesta derruba a família do Tesouro | `sentinela/data/providers/macro.py` (`gravar_series`, `_tesouro`) | auditoria externa do Gemini sobre 284165f..419f010, achado 2, 11/11/2026 | `test_bug_3_19_tesouro_duplicado_derruba_series.py` | F3-A-F7 | corrigido |
| BUG-3-20 | mês do SIDRA ainda não divulgado (`V = "..."`) faz a família IPCA inteira abster no `gravar_series`; o `registro_do_banco` devolve `inflacao` e `pib` sem `proveniencia` e `calendario` | `sentinela/data/providers/macro.py` (`gravar_series`, `_ipca`; `registro_do_banco`) | auditoria externa do Gemini sobre 284165f..419f010, achado 3, 11/11/2026 | `test_bug_3_20_ipca_nao_divulgado_e_registro_do_banco.py` | F3-A-F8 | corrigido |
| BUG-3-21 | no começo de janeiro, antes do primeiro Focus do ano, a edição de dezembro não é encontrada (agenda e filtro só do ano de D) e a taxa abstém | `sentinela/data/providers/macro.py` (`MacroProvider.pib`, `gravar_series._focus`, `_pib_do_banco`) | auditoria externa do Gemini sobre 284165f..419f010, achado 4, 11/11/2026 | `test_bug_3_21_focus_de_dezembro_no_inicio_de_janeiro.py` | F3-A-F9 | corrigido |
| BUG-3-22 | a cascata busca a taxa real com `datetime.now(UTC)`, não com o `as_of` pedido | `market_engine.py` (`buscar_dados_ticker`, `_buscar_taxa_real`) | auditoria externa do Gemini sobre 284165f..419f010, achado 5, 11/11/2026 | `test_bug_3_22_cascata_taxa_real_sem_as_of.py` | F3-A-F10 | corrigido |
| BUG-3-23 | linha conflitante do Tesouro gravada por uma coleta antiga (série com sufixo) continua lida depois que a coleta seguinte traz o arquivo corrigido: `_ultimas` escolhe a coleta mais recente por série e data, e o banco abstém onde o caminho histórico dá número | `sentinela/data/providers/macro.py` (`registro_do_banco`, leitura do Tesouro) | revisão do F3-A-F7, 11/11/2026 | `test_bug_3_23_conflito_fantasma_entre_coletas.py` | F3-A-F7b | corrigido |
| BUG-3-24 | companhia cujo FCA mais recente entregue não lista valor mobiliário continua no índice pelos códigos da referência anterior (`fca_mais_recente` só vê as referências com linhas): ZAMP3, PTNT3, PTNT4 e RDNI3 em 12/11/2026 | `sentinela/data/referencia/montagem.py` e `fontes.py` (índice atual), `sentinela/data/referencia/universo.py` (`_fca_em`) | comparação do F3-5, 12/11/2026 | `test_bug_3_24_fca_novo_sem_valores_mantem_o_antigo.py` | F3-5-fix | corrigido |
| BUG-3-25 | o Informe de FII de 2016 a 2020 (coluna `CNPJ_Fundo`, leiaute anterior à Resolução 175) é recusado linha a linha ("CNPJ_Fundo_Classe vazio") e o arquivo fica registrado como carregado: nenhum FII no universo em D antes de 2021 | `sentinela/data/pit/carga_cvm.py` (`_carregar_fii`) | backfill do F3-7b, 12/11/2026 | `test_bug_3_25_informe_fii_leiaute_antigo_recusado.py` | F3-3b-fix | corrigido |
| BUG-3-26 | a CVM traz a mesma chave com valores diferentes no mesmo arquivo; a carga grava o primeiro e põe o caso só no resumo (até 100), e `leitura.demonstrativo` devolve o primeiro valor sem motivo (1.360 conflitos no backfill, só 100 por arquivo listados no resumo) | `sentinela/data/pit/carga_cvm.py` (`_Tabela.gravar`), `sentinela/data/pit/leitura.py` (`demonstrativo`, `_escolha_cia`) | backfill do F3-7b, 12/11/2026 | `test_bug_3_26_conflito_da_carga_some_na_leitura.py` | F3-3b-fix | corrigido |
| BUG-3-27 | numa data passada, as guardas de coleta (escopo do BPP, DFP e composição do Gordon, fronteira do Gordon, janelas de Graham e Lynch, quadro de qualidade, Informe do FII) abstêm as lentes, porque todo dado do banco foi coletado depois de D, mesmo com a DFP entregue antes | `valuation_engine.py` (`_bpp_disponivel`), `cvm_provider.py` (`gordon_do_documento`, `composicao_mais_recente`), `sentinela/data/gordon_cvm.py` (`entradas`), `sentinela/data/janelas_fundamentais.py` (`_fonte`), `sentinela/data/fatores_acoes_b3.py` (`fatores_da_relacao`, ramo documental), `sentinela/data/providers/b3_proventos.py` (`proventos_ate`), `sentinela/methods/qualidade.py` (`_fonte`), `sentinela/data/rendimento_fii.py` (`entradas`) | revisão do F3-3d (C1), 12/11/2026; decisão 40 do Marcos | `test_bug_3_27_guarda_de_coleta_abstem_o_historico.py` | F3-3e | corrigido |

### Integração do backtest PIT — F3-8b (13/11/2026)

| ID | Sintoma | Evidência | Origem | Teste | Corrige | Estado |
|---|---|---|---|---|---|---|
| BUG-3-28 | Retorno com ajuste que subflui para zero ou inteiro não representável escapa como divisão por zero/overflow | D17/abstenção, ficha backtest§5 | revisão da implementação inicial F3-8b | `test_bug_3_28_retorno_nao_representavel.py` | F3-8b | corrigido |
| BUG-3-29 | Deslistagem posterior a T altera a marcação de suspensão e abstém o retorno até T | Ficha§5 e decisão42, horizonte fechado emT | revisão da implementação inicial F3-8b | `test_bug_3_29_deslistagem_posterior_ao_horizonte.py` | F3-8b | corrigido |
| BUG-3-30 | Carregar preço bruto pré-evento para depois de split/grupamento durante suspensão cria riqueza/perda artificial | Ficha§5/decisão42, conservação da base acionária | revisão F3-8b | `test_bug_3_30_suspensao_com_evento_em_acoes.py` | F3-8b | corrigido |
| BUG-3-31 | Dois proventos com a mesma ex são compostos sequencialmente, dando direito à fração comprada naquele fechamento | Decisão42, entrada no fechamento já ex e retorno bruto | revisão F3-8b | `test_bug_3_31_proventos_na_mesma_ex.py` | F3-8b | corrigido |
| BUG-3-32 | Caixa após deslistagem capitaliza só datas de pregão B3 e perde CDI em dia bancário com B3 fechada | SGS12 com taxa30/12/2022, COTAHIST2022 termina29/12; FatorDI DD-55 | integração F3-8b | `test_bug_3_32_cdi_em_dia_sem_pregao_b3.py` | F3-8b | corrigido |
| BUG-3-33 | Cotação terminal ausente é presumida suspensão sem prova de status e gera retorno como se o ativo permanecesse listado | ficha PIT §5; FCA `Data_Fim_Negociacao` ou status ativo no FCA para distinguir; ausência de fonte abstém | revisão da integração F3-8b | `test_bug_3_33_cotacao_ausente_nao_prova_suspensao.py` | F3-8b | corrigido |
| BUG-3-34 | Ativo do universo sem fechamento de entrada em D derruba `BacktestPIT.executar` inteiro (`KeyError: 'estado_terminal'`): a evidência do retorno abstido não trazia o estado terminal | ficha PIT §3 e §5: sem o fechamento de D, o retorno daquele ativo se abstém com motivo e os demais seguem | testes de mutação do F3-8b (claude-code), 15/11/2026 | `test_bug_3_34_ativo_sem_entrada_derruba_execucao.py` | F3-8b | corrigido |
| BUG-3-35 | Horizonte cujo mês final ainda está aberto (sem pregão observado depois dele) é tratado como completo: T vira o último pregão carregado do mês, encurtando o horizonte, e a observação conta como completa | ficha PIT §8; pendência de 12/11 (F3-7a → F3-8b): o mês fecha só com pregão observado no mês seguinte | revisão do F3-8b, rodada 1 (15/11/2026) | `test_bug_3_35_horizonte_com_mes_final_parcial.py` | F3-8b | corrigido |
| BUG-3-36 | Sem ISIN do ticker antes de D, os eventos em ações do emissor com ISIN são ignorados em silêncio; um desdobramento 2:1 faz o retorno sair −45% em vez de +10% | ficha PIT §5 (mesma base acionária); armadilha 11 | revisão do F3-8b, rodada 1 (15/11/2026) | `test_bug_3_36_evento_ignorado_sem_isin_do_ticker.py` | F3-8b | corrigido |
| BUG-3-37 | A identidade do emissor (decisão 33) abstém sem tentar o ISIN do ticker no pregão (CODISI do COTAHIST); 83 de 88 retornos da sonda do F3-8d ficavam sem número | decisão 43 do Marcos (DD-74) sobre a decisão 33 | sonda do F3-8d (15/11/2026) | `test_bug_3_37_identidade_sem_isin_do_pregao.py` | F3-8d-fix | corrigido |
| BUG-3-38 | Com a inflação da janela da DFP abstida ("IPCA ausente no banco"), Gordon e Bancos mostram "inflação incompatível com a janela da DFP" no lugar do motivo; 5 observações do Gordon na sonda do F3-8d | mesma família do BUG-2B-30 (motivo da abstenção preservado) | sonda do F3-8d e leitura do F3-8f (16/11/2026) | `test_bug_3_38_gordon_sem_motivo_da_inflacao.py` | F3-8f | corrigido |
| BUG-3-39 | Exercício da série sem data de fim faz `macro._encerramentos` levantar `TypeError`/`KeyError`, e o IPCA das janelas abstém como "erro inesperado no provedor macro", com traceback, no lugar do motivo do dado ausente | contrato de abstenção com motivo (BUG-2B-30); dado ausente é falha da fonte, não erro do código | sonda do F3-8f-col (16/11/2026) | `test_bug_3_39_encerramento_sem_data.py` | F3-8f-fix | corrigido |
| BUG-3-40 | O calendário da data ex do motor histórico (`b3_proventos.pregoes_da_data_ex`) usa os pregões guardados em `precos` sem conferir a cobertura da carga do COTAHIST; com o mês guardado incompleto, o pregão seguinte à data com falta e um provento de data ex anterior à janela de 12 meses é contado nela | a cascata abstém sem o COTAHIST lido; o calendário do banco (F3-P14b) exige a carga anual cuja geração alcança o intervalo | revisão do F3-8h (16/11/2026) | `test_bug_3_40_calendario_data_ex_incompleto.py` | F3-8h-cal | corrigido |
| BUG-3-41 | `proventos_b3.calendario_anual` exige o arquivo anual de um ano anterior ao do fim do trecho gerado em 31/12, dia sem pregão; os arquivos do banco real são gerados no último pregão (30/12), e o calendário abstém em todo trecho que atravessa a virada do ano: a qualidade de um ano inteiro e a data ex do motor histórico com início da janela entre 31/12 e 07/01 | decisão 44 do Marcos (16/11/2026): a cobertura vai até o último pregão do mês, pelo próprio COTAHIST armazenado | limite do F3-8h-cal, decisão 44 | `test_bug_3_41_cobertura_ate_o_ultimo_pregao.py` | F3-8h-cov | corrigido |
| BUG-3-42 | `CVMFIIProvider._linhas_do_fundo` só procura a coluna `CNPJ_Fundo_Classe`; o Informe de 2016 a 2020, gravado desde o BUG-3-25 e remontado em D com o cabeçalho original (`CNPJ_Fundo`), sai "sem linhas do fundo", e o rendimento e o DY do FII abstêm em toda data antes de 2021 | mesma família do BUG-3-25 (leiaute anterior à Resolução 175) | sonda do F3-8j (16/11/2026), ALMI11 em 28/06/2019 | `test_bug_3_42_informe_fii_leiaute_antigo_nao_lido.py` | F3-8j-fii | corrigido |
| BUG-3-43 | Backtest aplicava o fator de evento cujo ISIN de origem é o ticker, mas cujo `ativo_emitido` é outra espécie; CYRE3 e RENT3, D=30/06/2025, produziam retorno numérico sem reconciliação | guarda compartilhada de `sentinela/data/pit/serie_ajustada.py`, usada por `backtesting/backtest_pit.py` | auditoria C-1 da Fase 3, 16/11/2026 | `test_bug_3_43_evento_outra_especie_retorno.py` | correção C-1 | corrigido |

| BUG-3-44 | reset_db remove o banco único e resultados_analise; botão expõe exclusão total | database.py, app.py | Gemini D1, 17/11/2026 | `test_bug_3_44_reset_banco_unico.py` | F3-AUD-D1 | corrigido |

| BUG-3-45 | Retorno usa sufixo 4→PN e perde proventos PNA/PNB comprovados pelo ISIN | backtesting/backtest_pit.py | Gemini C1, 17/11/2026 | `test_bug_3_45_especie_isin_backtest.py` | F3-AUD-GC1 | corrigido |

| BUG-3-46 | Retorno reinveste naturezas de dinheiro fora de dividendos/JCP sem abstenção | backtesting/backtest_pit.py | Gemini C2, 17/11/2026 | `test_bug_3_46_natureza_provento_backtest.py` | F3-AUD-GC2 | corrigido |

| BUG-3-47 | Deslistada exige negócio no dia do fim e falta de cotação em T confirma suspensão sem prova | backtesting/backtest_pit.py | Gemini C4, 17/11/2026 | `test_bug_3_47_estado_terminal_backtest.py` | F3-AUD-GC4 | corrigido |

| BUG-3-48 | FCA terminal lê entregas posteriores a T e cache mistura horizontes | backtesting/backtest_pit.py | Gemini A3, 17/11/2026 | `test_bug_3_48_fca_terminal_apos_horizonte.py` | F3-AUD-GA3 | corrigido |

| BUG-3-49 | Informe vigente bloqueado some da remontagem e desloca a janela; VPA direto não corta mês/entrega; exploratório ignora reapresentação | remontagem.py, cvm_fii_provider.py, fronteira rendimento_fii | Gemini A1, 17/11/2026 | `test_bug_3_49_informe_fii_sem_recuo.py` | F3-AUD-GA1a/GA1b | parcial: 36 corrigidos em GA1a; 8 xfail estritos (arquivo vigente ilegível) como limitação declarada da Fase 3 (decisão 50), correção na proposta da Fase 4 (F3-10a) |

| BUG-3-50 | DFP/ITR vigente sem números no corte permite recuo silencioso do exercício, dos indicadores e do TTM | cvm_provider.py | Gemini A2, 17/11/2026 | `test_bug_3_50_periodo_cvm_vigente_sem_numeros.py` | F3-AUD-GA2a e F3-AUD-GA2b | parcial: GA2a na rodada final da decisão 49 (claude-code), com a regressão do índice ilegível na API legada; 15 xfails estritos (GA2b) como limitação declarada da Fase 3 (decisão 50), correção na proposta da Fase 4 (F3-10a) |
| BUG-3-51 | Informe de FII com mês de referência aberto ou futuro, entregue antes de D, entra no universo e desloca o corte de seis meses dos outros fundos | sentinela/data/referencia/universo.py | Gemini A4, 17/11/2026 | `test_bug_3_51_informe_fii_mes_aberto_no_universo.py` | F3-AUD-GA4 | corrigido |
| BUG-3-52 | Evento em ações aprovado em D ou depois entra na relação histórica e, sem data com, abstém o Bazin em D | sentinela/data/providers/b3_proventos.py | Gemini A5, 17/11/2026 | `test_bug_3_52_evento_em_acoes_futuro_no_historico.py` | F3-AUD-GA5 | corrigido |
| BUG-3-53 | Fator B3 da relação histórica (bloco do banco) recusado pela coleta posterior a D; Graham e Lynch abstêm em toda data passada com base incompatível | sentinela/data/fatores_acoes_b3.py, sentinela/data/janelas_fundamentais.py | Gemini B1, 17/11/2026 | `test_bug_3_53_fator_b3_da_relacao_historica.py` | F3-AUD-GB1 | corrigido |
| BUG-3-54 | Provento ou evento sem prova (ou sem data ex) com data com em T abstém o retorno, embora a ex caia depois de T | backtesting/backtest_pit.py | Gemini C3, 17/11/2026 | `test_bug_3_54_data_com_em_t_fora_do_horizonte.py` | F3-AUD-GC3 | corrigido |
| BUG-3-55 | Motor histórico e backtest montam o índice em D sem a tabela de correções e as identidades de FII (código "4030" da CSN, espécie da MGLU3) | sentinela/data/referencia/universo.py | Gemini B2, 17/11/2026 | `test_bug_3_55_correcoes_no_indice_historico.py` | F3-AUD-GB2 | corrigido |
| BUG-3-56 | Grupo de cada data do backtest sem a contagem das abstenções por motivo; análise sem lente vira a pseudo-lente "analise" | backtesting/backtest_pit.py | Gemini C5, 17/11/2026 | `test_bug_3_56_abstencoes_do_backtest_por_data.py` | F3-AUD-GC5 | corrigido |
| BUG-3-57 | Insumo `None` no Gordon (lucro, PL inicial, LPA, fator da unit, taxa, inflação, PIB) abstém com o `TypeError` genérico, sem nomear o campo | sentinela/data/gordon_cvm.py | Codex B-1, 17/11/2026 | `test_bug_3_57_gordon_nomeia_campo_ausente.py` | F3-AUD-CB1 | corrigido |
| BUG-3-58 | Relógio do sistema abaixo do serviço decide a disponibilidade por publicação (decisão 40) da análise de data passada: com o `hoje` do serviço fixo e o relógio no dia de D, as lentes abstêm por disponibilidade do BPP | market_engine.py (`_hoje_sp` em `buscar_dados_ticker` e `_buscar_cvm`) | Codex A-2, 17/11/2026 | `test_bug_3_58_relogio_abaixo_do_servico_historico.py` | F3-AUD-CA2b | corrigido |
| BUG-3-59 | Correção de espécie da MGLU3 vale no índice em D desde a referência da DFP 2025 (31/12/2025), antes da entrega (12/03/2026): ON por documento ainda não entregue | sentinela/data/referencia/correcoes.csv, universo.py | Codex C3-01, 20/11/2026 | `test_bug_3_59_correcao_pela_entrega_da_evidencia.py` | C3-01 (decisão 51) | corrigido |
| BUG-3-60 | Fator da base aceita evento em ações pela espécie do ISIN, sem provar que o ISIN é do emissor: raiz reutilizada por outro emissor reconcilia a série com o evento dele | sentinela/data/fatores_acoes_b3.py, providers/b3_proventos.py | Codex C3-03, 20/11/2026 | `test_bug_3_60_evento_de_raiz_reciclada.py` | C3-03 e C3-03b (decisão 51; o evento alheio é descartado) | corrigido |
| BUG-3-61 | Coleta mais recente com anúncio de novembro de 2026 ainda fora da relação falha a decisão 33 e torna indisponível o retorno de horizontes já encerrados | sentinela/data/proventos_b3.py, providers/b3_proventos.py | Codex C3-02, 20/11/2026 | `test_bug_3_61_identidade_ate_o_corte.py` | C3-02 (decisão 51, DD-90) | corrigido |
| BUG-3-62 | Cobertura da lente no resumo do backtest conta no universo elegível só as observações, sem os ativos elegíveis que falharam antes das lentes (`sem_lentes`) | backtesting/backtest_pit.py | Codex C3-06, 20/11/2026 | `test_bug_3_62_cobertura_com_sem_lentes.py` | C3-06 (decisão 51) | corrigido |
| BUG-3-63 | Na análise de hoje, o `as_of` é o clique e o `MarketEngine` carimba as coletas da própria execução com o relógio segundos depois: Graham, Bazin e o Rendimento do FII se abstêm por coleta posterior ao as_of (ABEV3 e HGLG11) | market_engine.py (`_buscar_proventos_b3`, `_buscar_rendimento_fii`, `_contexto_janelas`) | uso no app, 20/11/2026 (correção urgente na main, decisão do Marcos) | `test_bug_3_63_coleta_da_execucao_apos_o_as_of.py` | fix/as-of-hoje | corrigido |
| BUG-4-01 | O import de `config` instala log sem rotação no diretório atual | `config.py:15–22` | F4-A00a, adendo de 24/11 | `test_bug_4_01_log_no_repositorio.py` | F4-A00a | corrigido |
| BUG-4-02 | DY da cascata ausente ou inválido bloqueia a lente de rendimento do FII; DY divergente sobrescreve o do Informe na saída | `fii_engine.py` | Gemini, achado 1 | `test_bug_4_02_dy_do_informe_na_lente_fii.py` | F4-A01 | corrigido |
| BUG-4-03 | ISINs de PNC a PNH não são associados à classe no retorno total, no fator de eventos e na janela de proventos | `sentinela/data/proventos_b3.py` | Gemini, achado 3 | `test_bug_4_03_classes_preferenciais_no_isin.py` | F4-A02 | corrigido |
| BUG-4-04 | Janela de 12 meses inclui provento sem hora aprovado em D e é bloqueada por evento futuro ou de outro emissor | `sentinela/data/proventos_b3.py` | Gemini, achado 5 | `test_bug_4_04_corte_e_emissor_da_janela_b3.py` | F4-A03 | corrigido |
| BUG-4-05 | Cache da taxa corrente pode responder pela data passada e reter taxa antiga de series_macro após nova carga | `config.py`, `get_taxa_real` | Gemini, achado 6 | `test_bug_4_05_taxa_real_historica_sem_cache.py` | F4-A04 | corrigido |
| BUG-4-06 | Evento alheio de unit ou classe sem mapa é validado antes do descarte por identidade e impede a reconciliação | `sentinela/data/fatores_acoes_b3.py` | Gemini, achado 7 | novos casos em `test_bug_3_60_evento_de_raiz_reciclada.py` | F4-A05 | corrigido |
| BUG-4-07 | Pendência em provento ou evento de outra espécie bloqueia o retorno total do ticker | `backtesting/backtest_pit.py` | Gemini, achado 9 | `test_bug_4_07_pendencias_por_especie_no_retorno.py` | F4-A06 | corrigido |
| BUG-4-08 | A abstenção da lente de rendimento do FII elimina P/VP e Selic líquida da saída descritiva | `fii_engine.py` | Gemini, achado 2 | `test_bug_4_08_contexto_fii_com_lente_abstida.py` | F4-A07 | corrigido |
| BUG-4-09 | Encerramento de exercício não civil pode promover DFP sem comprovar DT_RECEB anterior ao corte | `cvm_provider.py`, `exercicio_anual_mais_recente` | Gemini, achado 8 | `test_bug_4_09_exercicio_anual_sem_entrega_no_corte.py` | F4-A08 | corrigido |
| BUG-4-10 | Na análise de hoje, o ZIP da CVM ou do Informe com cache vencido e o relatório do IF.data baixados pela própria execução registram o `mtime` real, depois do as_of, e as guardas rejeitam a coleta da execução | `cvm_download.py`, `sentinela/data/providers/ifdata.py`, `market_engine.py` (`buscar_dados_ticker`) | pedido do Marcos de 23/11; Gemini, achado 4 (IF.data) | `test_bug_4_10_download_da_execucao_no_as_of.py` | F4-A09 | corrigido |
| BUG-4-11 | A carteira grava posição com ticker vazio ou fora do padrão, quantidade booleana, fracionária ou zero e preço `NaN`, infinito, zero ou negativo; erro do SQLite na inclusão ou na remoção sobe até a aba Carteira | `database.py` (`adicionar_posicao`, `remover_posicao`), `app.py` (aba Carteira) | Gemini, achado 14 | `test_bug_4_11_posicao_invalida_na_carteira.py` | F4-A11 | corrigido |
| BUG-4-12 | No Bazin, evento em ações com ISIN de 12 caracteres fora do conjunto do emissor é descartado como alheio mesmo com dígito verificador inválido; um ISIN corrompido não prova outro emissor | `sentinela/data/proventos_b3.py` (`_evento_de_acoes_na_janela`) | revisão cruzada da DD-93; decisão 2 do Marcos de 25/11 | `test_bug_4_12_isin_sem_digito_verificador_no_bazin.py` | F4-A11c | corrigido |
| BUG-4-13 | A auditoria lê o banco aposentado `sentinela_v6.db` e grava o `.txt` e o `.json` no diretório corrente, com cada posição da carteira, fora de `outputs/` | `auditoria.py` (`auditar_banco`, `main`) | Gemini, achado 15; lista do Marcos de 23/11 | `test_bug_4_13_auditoria_banco_unico_e_saida.py` | F4-A12 | corrigido |
| BUG-4-14 | A auditoria roteia FII × ação pelo sufixo 11 (fora de `UNITS_CONHECIDAS`) e manda ETF e unit nova ao motor de FII, ao contrário do `app.py` | `auditoria.py` (`main`) | Gemini, achado 17 (primeira parte) | `test_bug_4_14_auditoria_classe_pelo_indice.py` | F4-A13 | corrigido |
| BUG-4-15 | Na análise de hoje, o seletor comprova o ano da DFP por uma versão entregue antes de D, mas o snapshot e a série leem a maior `VERSAO` do ZIP, inclusive a entregue em D | `cvm_provider.py` (`exercicio_e_versao_mais_recente`, `calcular_indicadores`, `indicadores_da_serie`), `market_engine.py` (`_serie_cvm`, `_buscar_cvm`) | auditoria R2 do bloco 0 (Codex, bloqueador 1) | `test_bug_4_15_versao_dfp_fora_do_corte.py` | F4-C01 | corrigido |
| BUG-4-16 | Download concorrente: a execução marcava o arquivo baixado pelo `stat` depois de publicá-lo, e CVM e IF.data usavam temporário de nome fixo; outra execução que publicasse o mesmo destino no intervalo tinha o arquivo aceito com a hora da primeira, e os dois downloads dividiam o temporário | `cvm_download.py`, `sentinela/data/providers/ifdata.py`, `sentinela/data/proveniencia.py` (`marcar_baixado`, `_lido_na_execucao`) | auditoria R2 do bloco 0 (Codex, bloqueador 2; DD-97) | `test_bug_4_16_download_concorrente_no_as_of.py` | F4-C02 | corrigido |
