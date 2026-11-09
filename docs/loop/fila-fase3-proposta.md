# Proposta complementar da Fase 3 — pendências herdadas da 2C

**Não ativada.** Migração autorizada pelo Marcos em09/11/2026, após auditorias Gemini/Claude. Esta proposta não substitui `docs/PLANO.md` nem a fila ativa `docs/loop/fila.md`; os IDs F3-Pxx são complementos propostos ligados aos itens F3-1…F3-8 do plano. Nenhuma implementação é autorizada por este documento. Marcos decide a ativação/ordem e os arquivos liberados após o Checkpoint da2C.

Regras de execução futuras: especificação externa/decisão antes de código; um fix por bug, regressão estrita antes da produção (D27), testes integrados pelo produtor real, suíte e gates, proteção do golden por predicado aprovado e parada nas dúvidas de método. Os oito casos xfail atuais permanecem estritos e sem alteração de asserções. Migração de destino não equivale a correção.

## Destinos dos itens que ficaram fora da 2C

| Destino proposto | Origem | Contrato/aceite proposto | Ligação no PLANO |
|---|---|---|---|
| F3-P01 · identidade do emissor B3 | F2C-23, BUG-2B-29 | Código CVM do GetDetail; se recusado pela API, nome de pregão retornado pelo próprio GetDetail, sem construir à mão. ABEV3/KLBN11 com barra ligam ao emissor correto, sem homônimo/contingência numérica. Erro e relação vazia mantêm motivo; fonte/parâmetros/identidade/hash e regressão existente PASS. Não alterar método/limiar | F3-3/F3-6 |
| F3-P02 · custo médio em redução parcial | F2C-48, BUG-2B-51 | Redução parcial mantém PM; compra usa média ponderada. Preservar zeragem e excesso de redução documentados; sem carteira real. Se exigir schema/tela, separar F3-2/Fase7; teste existente PASS antes de fechar | F3-2/F3-6 |
| F3-P03 · conferência ponderada da unit | F2C-50, BUG-2C-11 | Conferir soma por componente na mesma base da unit; composição incompleta não escolhe primeira classe. Não alterar LPA dos métodos nem limiar de divergência | F3-3/F3-6 |
| F3-P04 · falha do Informe nos riscos | F2C-51, BUG-2C-12 | Conservar abstenção/motivo e propagar risco de dados; controlar sucesso e provedor sem interface; distinguir falha de fonte de erro de programação | F3-3/F3-6 |
| F3-P05 · literal OData de instituição | F2C-52, BUG-2C-13 | Duplicar apóstrofo do literal antes de codificar query, preservando Unicode/reservados/número e a identidade da instituição. Testar capital e carteira, sem rede real | F3-6 |
| F3-P06 · origem da classe no contexto IA | F2C-53, BUG-2C-14 | Identificar classe inferida, origem e motivo; classe oficial sem aviso falso; UNKNOWN sem elegibilidade inventada. Não duplicar a mesma feature em app e serviço desconectado | F3-6 |
| F3-P07 · identidade de preferencial sem sigla FCA | F2C-54 | Levantamento de fonte oficial por identidade/documento/versão para DRE PNA e FCA PN sem sigla; sem ligação comprovada, abstém, sem adivinhar pelo ticker. D19/ficha por-ação1.1; eventual fix só após prova/aceite | F3-3/F3-5 |
| F3-P08 · versão ilegível do Informe | F2C-55, BUG-2C-27 | Todos os candidatos explicitamente ilegíveis não demonstram versão numérica; regressão existente permanece aberta. Coexistência válida/ilegível e ausência legada seguem o escopo ratificado no F2C-47, sem ampliar predicado por conveniência. Fonte: domínio numérico CVM/fichaFII1.3 | F3-3/F3-6 |
| F3-P09 · atribuição ON/PN de direitos distintos | F2C-38 | Manter regra atual até decidir ficha com estatuto/FRE, fonte/data e atribuição de lucro/PL/proventos. Incluir limitação do D0 de bancos que divide o total por ações como se direitos fossem iguais e a avaliação separada da ON com várias preferenciais. Nenhuma mudança automática pelo estudo | F3-3 |
| F3-P10 · escopo de saúde/benefícios | F2C-45(i) | Mantido o critério amplo de seguradora pelas descrições BPP; HAPV3/RDOR3/SAUD3/QUAL3 conservam o comportamento documentado. Estudar regra com fonte/materialidade/segmentos antes de qualquer alteração; não escolher limiar sem decisão | F3-3/F3-6 |
| F3-P11 · modelo de leitura e fonte não demonstrada | F2C-45(ii), inclusive falta de modelo/fonte | Mantida leitura de contas pelo setor e escopo pelo BPP, com os sete tickers divergentes do levantamento como casos. Falta de modelo BPP continua abstendo métodos de ação. Qualquer substituição requer modelo documental anterior à leitura, disponibilidade/corte e controle das séries/TTM; sem contingência padrão empresa | F3-3/F3-6 |
| F3-P12 · limites temporais do Informe e da taxa | F2C-47, regras ratificadas abaixo | Integrar prova por arquivo/documento e snapshots ao histórico estrito. Não afirmar PIT pela coleta do registro mais recente. Manter políticas ratificadas atuais até especificar contrato histórico; não harmonizar FII/Gordon silenciosamente | F3-1/F3-3 |
| F3-P13 · data explícita na série CVM | date.today() de MarketEngine._serie_cvm, FC2C-66/66R | Receber data/as_of na orquestração conectada, usar o mesmo corte para série/TTM/snapshot corrente e preservar provedores antigos. Testar exercício não civil e fronteiras de dia/fuso, sem relógio/rede/banco nos cálculos. Atualmente _buscar reutiliza o ano selecionado, mas o relógio original continua real | F3-1/F3-6 |
| F3-P14 · produtor de calendário anual de proventos | FC2C-70, qualidade1.0§9 | Fonte oficial e cobertura de cinco exercícios com bordas data-com/data-ex, identidade/coleta elegíveis; produtor→qualidade_inputs→motor sem chave sintética. Distinguir ano sem distribuição de fonte/calendário ausente; nenhum ano zero presumido | F3-3/F3-4/F3-6 |
| F3-P15 · detecção de reorganizações | decisão comparabilidade09/11, FC2C-61/62 | Fonte/documentos e regra explícita para rupturas e reconciliações, antes da implementação. Enquanto não implementada, manter aviso fixo “reorganização societária no período não é detectada”; mesmo CNPJ/modelo BPP/D20 e contiguidade continuam critério operacional aprovado | F3-3/F3-4 |
| F3-P16 · reconstrução do backtest | BUG-2C-60/fechamento anterior | Backtest ponto-no-tempo sobre lentes independentes, contrato a aprovar, sem reintroduzir score agregado. Até entrega, INDISPONIVEL com motivo da2C; FORA_DO_ESCOPO apenas para abstenção real. Os CSVs antigos não constituem evidência | F3-8 |

F2C-45(iii) foi decidido e corrigido no FC2C-64: banco com lente Bancos não recebe aviso_alavancagem. Não migra como pendência. Os registros/modelos mantidos em F3-P09/10/11 não são novos defeitos corrigidos nem aprovações de outra regra econômica.

## Oito casos xfail estritos — rastreabilidade completa

| Bug / destino | Teste existente | Casos |
|---|---|---:|
| BUG-2B-29 → F3-P01 (origem F2C-23) | `tests/regressao/test_bug_2b_29_b3_nome_de_pregao_com_barra.py::test_nome_de_pregao_com_barra_traz_a_relacao_do_emissor` | 1 |
| BUG-2B-51 → F3-P02 (origem F2C-48) | `tests/test_database_posicoes.py::test_venda_parcial_preserva_preco_medio` | 1 |
| BUG-2C-11 → F3-P03 (origem F2C-50) | `tests/regressao/test_bug_2c_11_unit_conferencia_ponderada.py::test_unit_sem_divergencia_na_soma_ponderada` | 1 |
| BUG-2C-12 → F3-P04 (origem F2C-51) | `tests/regressao/test_bug_2c_12_informe_risco_ausente.py::test_falha_do_informe_preserva_motivo_nos_riscos` | 1 |
| BUG-2C-13 → F3-P05 (origem F2C-52) | `tests/regressao/test_bug_2c_13_odata_literal_codinst.py::test_codinst_e_literal_opaco`, capital e carteira | 2 |
| BUG-2C-14 → F3-P06 (origem F2C-53) | `tests/regressao/test_bug_2c_14_prompt_classe_inferida.py::test_prompt_distingue_classe_sem_fonte_oficial` | 1 |
| BUG-2C-27 → F3-P08 (origem F2C-55) | `tests/regressao/test_bug_2c_27_versao_fii_ilegivel.py::test_todas_as_versoes_ilegiveis_nao_autorizam_rendimento` | 1 |

São sete bugs em sete funções/arquivos e **oito casos**, não oito bugs novos. Não mover arquivos, remover marcas, relaxar raises ou alterar asserções na migração. Atualizar somente os destinos nos motivos/registro; a correção futura retira a marca após D27.

## F2C-47 — oito regras ratificadas em 09/11/2026

Ratificação expressa do Marcos; origem e detalhes em `docs/decisoes/fii-bordas-pendentes-2c.md`. Mantém o comportamento/escopo documentado, sem implementação adicional neste fechamento:

1. Vazio e zero continuam distintos na detecção conservadora de conflitos da mesma versão; não generalizar equivalência de células.
2. Identidade documental usa versão numérica elegível; não ampliar a política para ausência legada/coexistência além do escopo ratificado. O comportamento defeituoso de casar duas sentinelas ilegíveis, explicitamente descrito como BUG-2C-27 no levantamento, **continua aberto e destinado a F3-P08**, conforme a migração dos oito xfails pedida pelo Marcos; não é ratificado como versão numérica legítima.
3. Entrega da composição fica vinculada ao documento geral/complemento de mesma identidade, referência e versão; não inventar entrega própria.
4. Coleta conferida atualmente é a do registro mais recente; não prometer conhecimento histórico de todos os arquivos. Reconstrução/prova por documento pertence a F3-P12.
5. Motivo comum “idade da NTN-B” continua cobrindo idade inválida ou vencida, sem alterar o predicado.
6. Assimetria temporal existente FII/Gordon mantida: FII exige as_of na taxa; Gordon o valida quando presente. Não harmonizar implicitamente.
7. Registro de taxa do FII deve ser do mesmo dia local e não futuro, além das demais guardas de data-base/idade.
8. Sem resposta B3 para eventos, manter abstenção por eventos indisponíveis; não converter falha em lista vazia.

As fontes oficiais do levantamento não são prova de disponibilidade histórica. A ratificação não declara corrigido o BUG-2C-27 nem autoriza remover seu xfail: a mensagem de09/11 exige conservar e migrar os oito casos. Entrega e coleta próprias da Fase3 precisam de aceite separado, e o critério de referência numérica continua externo ao código.
