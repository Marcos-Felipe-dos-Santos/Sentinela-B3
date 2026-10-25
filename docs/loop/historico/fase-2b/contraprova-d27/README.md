# Contraprova D27 refeita — F2B-54 e F2B-2 (F2B-64)

Decisão 5 do Marcos de 25/10/2026: contraprovas refeitas, sem dispensa genérica, para os testes
cuja falha registrada foi de importação, interface ou coleta.

**Como foi feito.** Os testes novos do commit de cada item rodaram contra o código do commit pai
(worktree temporária, `--runxfail`), e cada falha foi classificada em econômica (asserção sobre o
valor), de interface (`TypeError`, `KeyError`, `ImportError` da API nova) ou de coleta (módulo ou
classe inexistente): `f2b54.tsv` e `f2b2.tsv`, teste a teste. Para as de interface e de coleta,
os scripts rodam **a mesma entrada no commit pai e no commit do item**, pela API pública de cada
um, e a diferença entre as duas saídas é a falha econômica; o que não tem consequência de valor
recebe dispensa escrita, teste a teste, com o motivo.

Reprodução, da raiz do repositório, com a venv (a importação do `config` consulta o BCB,
armadilha 8; a Selic do cálculo é fixada por `patch`). Para cada par (commit, script):
`5c9ed55` e `7e1dfb4` com `f2b54_escala.py`; `7e1dfb4` e `7ffe016` com `f2b2_fii.py`:

    git worktree add --detach ../wt <commit>
    (cd ../wt && python ../Sentinela_B3/docs/loop/historico/fase-2b/contraprova-d27/<script> ../wt)
    git worktree remove --force ../wt

As saídas estão em `f2b54_escala.txt` e `f2b2_fii.txt` (o pai primeiro, o item depois).

## F2B-54 (commit pai `5c9ed55`, item `7e1dfb4`)

24 testes novos: 7 com falha econômica registrada no próprio item (as 6 regressões BUG-2B-33 a
38 e `tests/test_b3_proventos.py::test_sem_fechamento_bruto_abstem`), 7 que já passavam no pai
(guardam comportamento existente) e 10 de interface.

`f2b54_escala.py`, cenário 1: DFP em MIL (1.000 mil) e ITR em UNIDADE (1.010.000), e o inverso,
para a mesma base. No pai, razão 1010 e 0,00101, "base de ações incompatível"; no item, razão
1,01, compatível. Cenário 2: escala do documento recente indeterminada. O pai não tem o
parâmetro e decide como se fosse a da DFP (armadilha 10): compatível sem prova; o item abstém
("escala das ações do documento mais recente indeterminada").

| Teste | Falha no pai | Contraprova |
|---|---|---|
| `tests/test_gordon_cvm.py::test_escala_da_composicao_recente_converte_antes_da_razao` (2 casos) | `TypeError: escala_recente` | cenário 1 |
| `tests/test_gordon_cvm.py::test_escala_da_composicao_recente_indeterminada_abstem` | `TypeError: escala_recente` | cenário 2 |
| `tests/test_gordon_composicao_recente.py::test_escala_do_documento_recente_pela_regra_da_dfp` | `KeyError: 'escala'` | cenário 1 (o pai não infere a escala do documento recente e usa a da DFP) |
| `::test_escala_com_controladores_zerados_sem_minoritarios_usa_o_consolidado` | `KeyError: 'escala'` | cenário 1 |
| `::test_escala_com_moeda_em_unidade` | `KeyError: 'escala'` | cenário 1 |
| `::test_escala_do_documento_recente_indeterminada` | `KeyError: 'escala'` | cenário 2 |
| `::test_escala_sem_lucro_dos_controladores_separado_fica_indeterminada` | `KeyError: 'escala'` | cenário 2 |
| `tests/test_b3_proventos.py::test_fechamento_invalido_fica_de_fora` | `KeyError: 'fechamentos_brutos'` | o filtro de fechamento inválido já existia no pai (sobre o histórico ajustado) e passou para os fechamentos brutos; a consequência econômica nova é só a troca de série, que é o BUG-2B-33 (falha no pai pelo valor, `assert 99.0 == 100.0`) |
| `tests/test_perfil_unico.py::test_serie_valida_leva_o_aviso_fixo_fora_de_riscos` | `KeyError: 'avisos'` | **dispensa:** aviso informativo novo (ficha Bazin 1.2), fora de `riscos`, sem número nem rótulo; o pai não tinha o campo, e não há valor a contrariar |
| `tests/test_perfil_unico.py::test_avisos_da_serie_aparecem_com_o_bazin_abstendo` | `KeyError: 'avisos'` | **dispensa:** idem |

## F2B-2 (commit pai `7e1dfb4`, item `7ffe016`)

55 testes novos: 3 com falha econômica no próprio item, 1 que já passava no pai, 10 de interface
e 41 de coleta (`tests/test_fii_elegibilidade.py`, `tests/test_fii_rendimento_elegivel.py` e
`tests/test_spread_fii.py`, módulos inexistentes; `tests/test_methods_fii_yield.py`, `TypeError`
na classe de parâmetros nova). `tests/test_financeiro_pre_refactor.py::test_b_fii_compara_dy_com_a_selic_liquida_de_ir`
não é teste novo: existia no pai e foi reescrito no item, por isso entra na tabela e não na
contagem.

`f2b2_fii.py` monta a entrada no formato que a cascata grava (`informe_fii` com as linhas do
complemento e a composição, `b3_fundo` com a resposta da B3, `taxa_real` com a NTN-B): um FII de
tijolo com R de 12 meses = 12 sobre VP 100, preço 100, e cada regra aplicada sobre ele. No pai,
que não lia o Informe, a B3 nem a NTN-B, todos os cenários dão R$ 97,36 pela Selic líquida (C2
muda com ela: 282,35 / 141,18 / 94,12). No item, C1 dá 12 ÷ (7% + 3,5058%) = R$ 114,22 com
qualquer Selic; C3 dá R$ 128,95 (o exemplo da ficha com o spread aprovado; com os 2 pp do teste
do método, 151,12; o pai, com o DY da ficha, 107,43); e cada C4 abstém com o motivo da própria
regra, em `metodos_usados`: "insumo ausente: ntnb_real" (C4a), "spread indisponível" (C4b), "tipo
de FII fora do escopo na 2B: papel" (C4c), "sem maioria estrita" (C4d), "desdobramento oficial na
janela" (C4e), "fonte de eventos de cota indisponível" (C4f), "menos de 12 meses" pela entrega no
dia do as_of (C4g), "Informe mais recente com mais de 3 meses" (C4h), DY mensal negativo,
amortização na janela e cotas não positivas (C4i), "rendimento anual não positivo" (C4j),
"insumo ausente: Informe Mensal do FII" (C4k). No item, a abstenção ainda saía com
`fair_value` igual ao preço (corrigido depois, no F2B-62): ela se prova pelo motivo, não pelo
valor.

| Teste | Falha no pai | Contraprova |
|---|---|---|
| `tests/test_methods_fii_yield.py::test_preco_justo_pela_ntnb_mais_spread` | coleta | C1: pai 97,36 (Selic), item 114,22 (NTN-B + spread aprovado; com os 2 pp do teste, 12 ÷ 9% = 133,33 nesta entrada) |
| `::test_selic_liquida_nao_forma_o_preco_justo` (saiu no F2B-5 com o campo `selic`; a independência da Selic segue em `tests/test_financeiro_pre_refactor.py::test_b_fii_compara_dy_com_a_selic_liquida_de_ir`) | coleta | C2: pai 282,35 / 141,18 / 94,12 com Selic de 5%, 10% e 15%; item 114,22 nas três |
| `::test_sem_ntnb_abstem` | coleta | C4a: pai 97,36 sem NTN-B; item abstém ("insumo ausente: ntnb_real") |
| `::test_exemplo_da_ficha`, `::test_sensibilidade_da_ficha`, `::test_spread_negativo_com_taxa_positiva_calcula` | coleta | C3: pai 107,43, sem spread nem NTN-B; item 128,95 (aprovado); a ficha com 2 pp dá 151,12 |
| `::test_matriz_de_validade` | coleta | C4a e C4b (taxa e spread ausentes: o pai calcula); os casos de domínio (taxa não positiva, DY acima de 25%, preço não positivo) são da fórmula nova; o DY acima de 25% o pai já recusava |
| `tests/test_financeiro_pre_refactor.py::test_b_fii_compara_dy_com_a_selic_liquida_de_ir` (reescrito depois) | econômica no próprio item | C2 |
| `tests/test_fii_engine.py::test_fii_preco_justo_pela_ntnb_e_spread_sem_selic` | `TypeError: as_of` | C1 e C2 |
| `tests/test_fii_engine_rendimento.py::test_fii_tijolo_pela_ntnb_mais_spread` | `TypeError: as_of` | C1 |
| `::test_selic_fica_no_score_e_nao_no_preco_justo` | `TypeError: as_of` | C2 |
| `::test_abstencoes_da_lente` (taxa abstida, sem taxa, sem Informe, papel, eventos indisponíveis) | `TypeError: as_of` | C4a, C4k, C4c, C4f |
| `::test_sem_spread_abstem` | `TypeError: as_of` | C4b |
| `::test_avisos_da_conferencia_saem_com_o_resultado` | `TypeError: as_of` | **dispensa:** aviso informativo da conferência com a B3, sem efeito no valor (ficha 1.1, §3a) |
| `tests/test_fii_rendimentos.py::test_cascata_grava_o_informe_e_a_b3_fora_do_prompt`, `::test_cascata_grava_as_abstencoes` | `KeyError` | **dispensa:** registro dos dados crus na cascata, sem número; a consequência econômica é a da lente (C4) |
| `::test_provedor_traz_entrega_isin_e_composicao` | `KeyError: 'Data_Entrega'` | C4g (corte por entrega) e C4c (composição) |
| `tests/test_contratos_provedores.py::test_contrato_fundos_b3` | `ImportError` | **dispensa:** contrato D18 de provedor novo (`b3_fundos`), sem comportamento anterior |
| `tests/test_fii_elegibilidade.py::test_tipo_pela_maioria_estrita`, `::test_tipo_desconhecido_abstem`, `::test_caixa_e_renda_fixa_nao_entram_na_base`, `::test_celula_vazia_conta_como_zero` | coleta | C4c e C4d |
| `::test_resposta_invalida_e_fonte_indisponivel` | coleta | C4f |
| `::test_resposta_valida_com_listas_vazias` | coleta | **guarda:** com resposta válida e sem evento, a regra nova calcula, como o pai; não há falha econômica possível |
| `::test_evento_de_cota_na_janela_abstem` | coleta | C4e |
| `::test_conferencia_igual_em_duas_casas_sem_aviso`, `::test_conferencia_diferente_gera_aviso_com_mes_e_valores`, `::test_conferencia_ignora_outro_isin_e_avisa_mes_sem_b3`, `::test_conferencia_soma_pagamentos_do_mesmo_mes`, `::test_conferencia_sem_resposta_da_b3` | coleta | **dispensa:** a conferência com a B3 só gera aviso, sem efeito no valor nem na abstenção (ficha 1.1, §3a) |
| `tests/test_fii_rendimento_elegivel.py::test_tijolo_elegivel_soma_doze_meses`, `::test_preco_e_dy_anual` | coleta | C1 (o pai não soma o rendimento do Informe) |
| `::test_entrega_no_dia_do_as_of_ainda_nao_vale`, `::test_versao_entregue_depois_do_as_of_tira_o_mes`, `::test_entrega_ilegivel_nao_e_demonstrada` | coleta | C4g |
| `::test_informe_com_mais_de_tres_meses_abstem` | coleta | C4h |
| `::test_guardas_da_matriz` | coleta | C4i |
| `::test_so_tijolo_pela_composicao_do_mes` | coleta | C4c |
| `::test_evento_de_base_na_janela_abstem` | coleta | C4e |
| `::test_fonte_de_eventos_indisponivel_abstem` | coleta | C4f |
| `::test_rendimento_anual_zero_abstem` | coleta | C4j |
| `::test_informe_com_tres_meses_vale`, `::test_mes_sem_rendimento_vale_como_zero`, `::test_emissao_com_vp_continuo_fica_em_contexto`, `::test_evento_antes_da_janela_nao_abstem` | coleta | **guarda:** a regra nova calcula, como o pai; não há falha econômica possível (o valor é o de C1) |
| `::test_conferencia_divergente_vira_aviso_sem_abster` | coleta | **dispensa:** aviso da conferência, sem efeito no valor |

Classificação bruta, teste a teste (falha no pai e primeira linha da mensagem): `f2b54.tsv` e `f2b2.tsv`.
