# Números por ação (LPA, VPA, ações, classes, units e escala) — versão 0.1

**Status:** rascunho
**Itens que dependem:** F2A-36 (LPA divulgado por espécie, classes e units), F2A-37 (reservas dos controladores)
**Origem no código:** F2A-3 (derivação por ação) e F2A-5 (alertas), já entregues
**Decisões de origem:** ADR-0003, D19, D20 e D21; checkpoint da Fase 0, seção 4, item 1 (revisado pela D19)

Esta ficha só apresenta definições, dados e casos. Os pontos marcados **[DECISÃO]** ficam para o Marcos; nenhum parâmetro é decidido aqui.

## 1. Fórmula e referência

| Número | Fórmula | Papel (D19) |
|---|---|---|
| **LPA divulgado** | linha 3.99.01.x da DRE consolidada, da espécie do ticker (ON, PN, PNA…), em R$ por ação | entrada dos métodos |
| **LPA recalculado** | lucro atribuído aos sócios da controladora ÷ (ON + PN − tesouraria), com as ações da Composição do Capital do **mesmo documento** (CNPJ, `DT_REFER`, `VERSAO`) | conferência contra o divulgado (F2A-5) e reserva |
| **VPA** | PL atribuído à controladora (PL consolidado − participação dos não controladores) ÷ (ON + PN − tesouraria) do fim do período | entrada dos métodos |
| **Ações para valor de mercado** | ações em circulação na data, por espécie; capitalização = Σ (preço da espécie × ações da espécie) | capitalização |
| **LPA e VPA da unit** | Σ (quantidade da espécie na unit × número da espécie), com a composição oficial do FCA (`Composicao_BDR_Unit`) | entrada dos métodos para units |

**Referência.** IAS 33 / CPC 41 (Resultado por Ação), com a mesma numeração de parágrafos:
- §9 e §10: o resultado básico por ação é o lucro atribuível aos detentores de ações ordinárias da **controladora** dividido pela média ponderada das ações ordinárias em circulação no período;
- §19 e §20: o denominador é a média ponderada das ações ordinárias em circulação no período, ajustada pelo tempo (no recalculado desta ficha, as ações em circulação são ON + PN − tesouraria do fim do período);
- §66: a entidade apresenta o resultado básico e o diluído **para cada classe** de ações ordinárias com direito diferente de participar do lucro;
- Apêndice A, §A13 e §A14: instrumentos patrimoniais participativos e ações ordinárias de duas classes (método das duas classes), que é como as companhias brasileiras com ON e PN apresentam o LPA por espécie.

Consequência: o LPA divulgado já é o número da norma (controladora, média ponderada, por classe). O recalculado difere dele por construção (ações do fim do período em vez da média ponderada; uma só divisão em vez do rateio por classe) e só serve de conferência ou de aproximação declarada.

## 2. Insumos

| Insumo | Definição exata | Fonte | Unidade e escala | Data de referência |
|---|---|---|---|---|
| LPA básico por espécie | linhas 3.99.01.01, 3.99.01.02… da DRE consolidada; a espécie vem da **descrição** (ON, PN, PNA…), não do código | DFP/ITR, `dfp_cia_aberta_DRE_con_<ano>.csv` | R$ por ação; **não** passa pela `ESCALA_MOEDA` (a linha vem marcada MIL, mas o valor já é por ação) | `DT_REFER` do documento |
| Lucro dos controladores | par (código, descrição) "Atribuído a (aos) Sócios da Empresa Controladora" (3.11.01 ou 3.09.01, conforme a estrutura da DRE, em empresas e bancos; 3.11.01 ou 3.13.01 no modelo de seguradora), pela tabela `sentinela/data/referencia/contas_cvm.csv` | DFP/ITR | R$ × `ESCALA_MOEDA` (MIL → × 1.000) | `DT_REFER` |
| PL consolidado e não controladores | "Patrimônio Líquido Consolidado" (2.03) e "Participação dos Acionistas Não Controladores" (2.03.09) | DFP/ITR, BPP consolidado | R$ × `ESCALA_MOEDA` | `DT_REFER` |
| Ações por espécie e tesouraria | `QT_ACAO_ORDIN_CAP_INTEGR`, `QT_ACAO_PREF_CAP_INTEGR`, `QT_ACAO_ORDIN_TESOURO`, `QT_ACAO_PREF_TESOURO`, `QT_ACAO_TOTAL_TESOURO` | DFP/ITR, `composicao_capital` | **sem coluna de escala**: unidade ou milhar, conforme o documento (armadilha 10) | `DT_REFER`, mesma `VERSAO` |
| Espécie do ticker | `Valor_Mobiliario` e `Sigla_Classe_Acao_Preferencial` | FCA, `valor_mobiliario` | — | `Data_Referencia` do FCA |
| Composição da unit | `Composicao_BDR_Unit` (por exemplo, "1 ON / 2 PN") | FCA | quantidade por unit | `Data_Referencia` do FCA |
| Preço | fechamento D-1 | yfinance (fluxo da V1; o COTAHIST do F2A-18 é a série oficial disponível) | R$ por ação, bruto | pregão anterior |

## 3. Regime, janela e data

- **Sem taxa:** a ficha não desconta nada; não há regime real ou nominal.
- **Janela:** um documento (o último `DT_REFER`, na maior `VERSAO`). O LPA divulgado da DFP é do exercício; no ITR, a DRE traz o trimestre e o acumulado do ano, separados pelo `DT_INI_EXERC` (F2A-16). Nenhum dos dois é TTM: os quatro trimestres são do F2A-7.
- **Data:** todos os números de um mesmo cálculo vêm do mesmo documento (CNPJ, `DT_REFER`, `VERSAO`). O VPA usa as ações do **fim do período** por definição (D19); o LPA recalculado também, e por isso é aproximação do divulgado (média ponderada). Múltiplos (P/L, P/VP) usam o preço bruto da data e as ações do mesmo documento do lucro (armadilha 11). A proveniência de cada campo (F2A-32) registra o documento, a versão e a data de entrega.

## 4. Hipóteses e inaplicabilidade

Abstenções (D19 e D20; textos que o código usa ou passará a usar):

1. **Composição do Capital ausente ou de outro documento:** sem ações, não há VPA nem LPA recalculado ("sem Composição do Capital no documento do lucro"; total de ações ≤ 0: "total de ações da Composição do Capital ≤ 0").
2. **Escala indeterminada:** sem LPA divulgado para inferir a escala das ações, ou com a razão fora da faixa, o recalculado se abstém ("escala das ações indeterminada"; D19, regra 5).
3. **Mais de uma classe preferencial com direitos distintos** (PNA, PNB…; `Sigla_Classe_Acao_Preferencial` do FCA): o recalculado comum se abstém para as preferenciais; vale só o divulgado da classe e, sem ele, o LPA da classe se abstém (D19, regra 3).

   **Regras 2 e 5 juntas (leitura proposta, a confirmar na aprovação — [DECISÃO], seção 7.4).** A regra 2 (divulgado ausente → recalculado como aproximação declarada) só se aplicaria quando outra espécie do mesmo documento traz LPA divulgado que determina a escala; sem nenhum divulgado no documento, a regra 5 deixaria a escala indeterminada e o recalculado se absteria. A outra leitura possível é tirar a escala de outra fonte (outro documento da mesma companhia). A abstenção 4 depende da escolha.

2a. **Divulgado com sinal oposto ao do lucro dos controladores:** pela regra 1 da D19, o divulgado só é a entrada dos métodos se for "coerente" (escala determinada e mesmo sinal do lucro). Com sinal oposto, não é coerente: vale o tratamento de divulgado ausente (regra 2). Caso real: a QUAL3 traz duas linhas "ON" com sinais opostos (−0,009 e 0,047; diário do F2A-3); hoje o F2A-3 não deriva LPA para ela (abstenção registrada no diário).
4. **Unit com espécie componente sem LPA divulgado:** aplica-se a regra 2 com a marca; se a regra 3 proíbe o recalculado da espécie, a unit inteira se abstém (D19, regra 4). Composição não reconhecida: abstém-se ("unit sem composição oficial (ações por unit)").
5. **PL ou lucro dos controladores não identificados, ou PL ≤ 0:** sem ROE dos controladores ("PL dos controladores não identificado no documento", "lucro dos controladores não identificado no documento", "PL dos controladores ≤ 0").
6. **Bancos:** a 2.03 não é patrimônio líquido (F2A-16: 2.07 ou 2.08); até o F2A-9 o PL e o VPA do banco se abstêm.
7. **Par (código, descrição) sem correspondência na tabela de contas:** o campo se abstém (D20, F2A-33 e F2A-38).

Reservas permitidas (D20, política aprovada com o ADR):
- **Lucro dos controladores ausente:** vale o lucro total só se a linha dos não controladores estiver ausente ou zerada.
- **PL dos controladores:** vale o PL total só se a participação dos não controladores no balanço estiver ausente ou zerada **e** o lucro dos não controladores também.
- **Valor inválido** (não numérico, NaN, infinito) nunca autoriza reserva: o campo se abstém.

**Por que a reserva é aceitável.** Sem a linha dos não controladores, a companhia não informa minoritários; tratar o consolidado como da controladora é a leitura do próprio documento. A ausência é falta de evidência, não prova de que não há minoritários (D20); por isso a reserva fica registrada na proveniência do campo.

**Onde a reserva seria usada** (levantamento só de leitura na DFP 2025 consolidada, última versão de cada companhia; script e saída em `outputs/f2a34_reservas.py` e `outputs/f2a34_reservas.json`, fora do git):
- 439 companhias com DRE e BPP consolidados (a mesma contagem para DRE ou BPP). As listas "nas 45" casam a companhia pelo código CVM do mapa, e não pelo ticker do índice: AZUL4, GOLL4 e PETZ3 estão nas 45 com código, mas fora do índice com esse ticker.
- **Lucro dos controladores ausente:** 0 (todas trazem a linha "Atribuído a Sócios da Empresa Controladora").
- **Lucro dos controladores zerado com o dos não controladores zerado ou ausente:** 105. Não é o caso "ausente" da D20; hoje o F2A-3 usa o lucro total aí (ver **[DECISÃO]** na seção 7). Nas 45 ações do mapa: KLBN11, LWSA3, PETZ3, SBSP3 e TIMS3 (o diário do F2A-3 citou KLBN11, SBSP3, PETZ3 e LWSA3; a TIMS3 também está no caso, mas não teve LPA derivado). Na KLBN11 a participação dos não controladores no balanço é de R$ 6,5 bilhões (2.03.09), ou seja, há minoritários e o lucro total os inclui.
- **PL total como PL dos controladores** (2.03.09 ausente ou zerada e lucro dos não controladores ausente ou zerado): 171 companhias fora do setor "Bancos", mais 2 bancos (BEES3 e um sem ticker no índice), em que a reserva não seria usada porque o PL do banco se abstém até o F2A-9. Nas 45 ações: AZUL4, GOLL4, LREN3, LWSA3, MGLU3, PETZ3, RECV3, SBSP3 e TIMS3.
- **PL com reserva bloqueada** (2.03.09 ausente ou zerada, mas lucro dos não controladores diferente de zero): 8; com ticker no índice: SEQL3, SBFG3, INEP3, POSI3 e MWET3/MWET4. Pela D20, o PL dos controladores se abstém nesses casos.

## 5. Exemplo calculado de forma independente

Valores lidos à mão nos CSVs publicados pela CVM (DFP 2025, `dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_2025.zip`, cópia de 8/10/2026) e no FCA 2026 (`fca_cia_aberta_2026.zip`). Nenhum código do projeto foi rodado ou importado para as contas.

### 5.1 Companhia com ON e PN — Petrobras (PETR3, PETR4)

CNPJ 33.000.167/0001-01, `DT_REFER` 2025-12-31, `VERSAO` 1, entregue em 2026-03-05 (`ID_DOC` 155122). DRE e BPP consolidados em `ESCALA_MOEDA` MIL, exercício ÚLTIMO.

| Linha | Valor no arquivo |
|---|---|
| 3.11.01 Atribuído a Sócios da Empresa Controladora | 110.129.000 (mil R$) |
| 3.11 Lucro/Prejuízo Consolidado do Período | 110.605.000 (mil R$) |
| 2.03 Patrimônio Líquido Consolidado | 417.587.000 (mil R$) |
| 2.03.09 Participação dos Acionistas Não Controladores | 1.801.000 (mil R$) |
| 3.99.01.01 ON / 3.99.01.02 PN | 8,54 / 8,54 (R$ por ação) |
| Composição do Capital: ON / PN / tesouraria | 7.442.231.382 / 5.446.501.379 / 0 |

Conta:
1. Lucro dos controladores = 110.129.000 × 1.000 = R$ 110.129.000.000.
2. Ações em circulação = 7.442.231.382 + 5.446.501.379 − 0 = 12.888.732.761.
3. LPA recalculado (unidade) = 110.129.000.000 ÷ 12.888.732.761 = **8,5446**. Na hipótese de milhar, seria 0,0085: a razão com o divulgado (8,54) é 1,0005 na unidade e 0,001 no milhar; a escala é **unidade**.
4. LPA divulgado (entrada dos métodos, D19): **8,54** para PETR3 e para PETR4. Diferença do recalculado: +0,05%.
5. PL dos controladores = (417.587.000 − 1.801.000) × 1.000 = R$ 415.786.000.000.
6. VPA = 415.786.000.000 ÷ 12.888.732.761 = **32,26**.
7. Para comparação: com o lucro consolidado (110.605.000 mil), o LPA recalculado seria 8,5816 (+0,43% sobre o dos controladores; +0,49% sobre o divulgado); com o PL consolidado, o VPA seria 32,40 (+0,43%).

### 5.2 Unit — Taesa (TAEE11)

CNPJ 07.859.971/0001-30, `DT_REFER` 2025-12-31, `VERSAO` 1, entregue em 2026-03-17 (`ID_DOC` 155448). FCA 2026: TAEE11 = "1 ON / 2 PN".

| Linha | Valor no arquivo |
|---|---|
| 3.11.01 Atribuído a Sócios da Empresa Controladora | 1.579.863 (mil R$) |
| 3.11.02 Atribuído a Sócios Não Controladores | 0 |
| 2.03 Patrimônio Líquido Consolidado | 7.608.982 (mil R$) |
| 2.03.09 Participação dos Acionistas Não Controladores | 0 |
| 3.99.01.01 ON / 3.99.01.02 PN | 1,52866 / 1,52866 (R$ por ação) |
| Composição do Capital: ON / PN / tesouraria | 590.714 / 442.783 / 0 |

Conta:
1. Lucro dos controladores = 1.579.863 × 1.000 = R$ 1.579.863.000.
2. Ações no arquivo = 590.714 + 442.783 − 0 = 1.033.497.
3. Escala das ações: na unidade, LPA = 1.579.863.000 ÷ 1.033.497 = 1.528,66 (razão com o divulgado: 1.000); no milhar, 1.579.863.000 ÷ 1.033.497.000 = **1,52866** (razão 1,0000). A Composição do Capital da Taesa está em **milhares**: são 1.033.497.000 ações.
4. LPA da unit pelo divulgado (D19, regra 4) = 1 × 1,52866 (ON) + 2 × 1,52866 (PN) = **4,58598**.
5. VPA por ação = 7.608.982.000 ÷ 1.033.497.000 = 7,3624; VPA da unit = 3 × 7,3624 = **22,087**.
6. Aqui ON e PN têm o mesmo LPA divulgado; a regra 4 só faz diferença quando as espécies têm LPA distintos.

Esses dois casos viram teste no F2A-36.

## 6. Sensibilidade

| Premissa | Alternativa | Efeito no exemplo | Efeito medido no universo |
|---|---|---|---|
| Escala das ações | trocar unidade por milhar | LPA e VPA ÷ ou × 1.000 | DFP 2025: 70 de 255 companhias determinadas em milhares (F2A-16) |
| Lucro dos controladores × consolidado | usar o consolidado | PETR: LPA recalculado +0,43% | 157 de 255 com lucros diferentes; o dos controladores fica mais perto do divulgado em 107 (68%) (F2A-16) |
| PL dos controladores × consolidado | usar o consolidado | PETR: VPA +0,4% | F2A-3 (consolidado → controladores): CSAN3 VPA 7,86 → 1,34 e ROE −0,329 → −1,833; BEEF3 VPA 1,91 → 1,33 e ROE 0,448 → 0,619; EQTL3 ROE 0,088 → 0,065; ENEV3 0,079 → 0,058; VALE3 0,063 → 0,075; SLCE3 0,100 → 0,110 |
| Ações do fim do período × média ponderada | recalculado no lugar do divulgado | PETR: +0,05% | razão recalculado ÷ divulgado nas 38 ações do mapa com razão: mediana 1,000, 4º menor 0,631, máximo 1,199 (F2A-3). A razão não isola este efeito: mistura também o lucro total usado com minoritários (KLBN11) e o arredondamento do divulgado (GOLL4, −0,001) |
| Composição da unit | dividir o PL consolidado pelo número de units (V1) | — | KLBN11: VPA da unit 11,85 → 6,43 na troca da V1 para o F2A-3; a queda mistura a composição da unit com a saída dos R$ 6,5 bi de não controladores do PL |

## 7. Parâmetros e justificativa

### 7.1 Faixa da razão para inferir a escala: [0,1; 10] — **[DECISÃO]**

O F2A-3 escolhe unidade ou milhar pela razão (LPA recalculado ÷ LPA divulgado) mais perto de 1, e só aceita a escolha se a razão cair em [0,1; 10]. As duas hipóteses diferem por 1.000, então a escolha só fica ambígua perto de 1/31,6 ou de 31,6 (a raiz de 1.000); a faixa fica dentro desse intervalo com folga.

Distribuição medida:
- **Universo da DFP 2025** (F2A-16, 255 companhias com escala determinável): razão na escala escolhida entre ≈ 0 e 19,9; p10 0,837, mediana 1,000, p90 1,051; 209 de 255 dentro de 10%; fora de [0,8; 1,25]: 28; fora de [0,5; 2]: 17; **fora de [0,1; 10]: 5** (CD_CVM 016675 ≈ 0; 004537 0,001; 018414 0,001; 024120 0,08; 023000 19,9).
- **45 ações do mapa** (F2A-3, 38 com razão): mínimo 0,142, mediana 1,000, máximo 1,199; escala MIL em 9 (ABEV3, CMIG4, CYRE3, ELET3, ENEV3, ITUB4, LREN3, MRVE3, VALE3). Sem razão: ASAI3 e NTCO3 (sem DFP consolidada 2025 nem Composição do Capital), COGN3, RECV3, TIMS3 e VIVT3 (linhas 3.99 todas zeradas) e QUAL3 (duas linhas "ON" com sinais opostos).
- **As duas distribuições não são diretamente comparáveis:** a do F2A-16 só usa lucro dos controladores e LPA positivos; a do F2A-3 aceita prejuízo com LPA do mesmo sinal (por isso o mínimo nas 45 é 0,142, da GOLL4, aqui, e 0,258, da AZUL4, no F2A-16).

**Casos dentro da faixa e longe de 1** (|razão − 1| > 10%), todos com alerta do F2A-5:

| Ticker | Razão | Escala | LPA divulgado | LPA recalculado | Leitura provável |
|---|---|---|---|---|---|
| GOLL4 | 0,142 | unidade | −0,001 | −0,00014 | LPA divulgado quase zero; razão instável |
| AZUL4 | 0,258 | unidade | 0,16 | 0,041 | classes com direitos distintos e conversões no período |
| ENEV3 | 0,604 | milhar | 1,00 | 0,604 | média ponderada × fim do período (emissão de ações) |
| CSAN3 | 0,631 | unidade | −3,892 | −2,455 | holding com prejuízo; minoritários relevantes |
| KLBN11 | 1,197 | unidade | 0,2286 | 0,2736 por ação | lucro total usado com minoritários no balanço (seção 4) |
| CYRE3 | 1,199 | milhar | 4,570 | 5,478 | média ponderada × fim do período (recompras) |

As "leituras prováveis" são hipóteses a conferir; nenhuma foi verificada no formulário da companhia.

Opções para o Marcos: manter [0,1; 10]; estreitar para [0,5; 2] (abstém GOLL4 e AZUL4 nas 45, e 17 de 255 no universo); ou abster sempre que a razão sair de [0,8; 1,25] (28 de 255). A faixa decide a escala das ações, e portanto o VPA e o recalculado; pela regra 1 da D19, decide também se o divulgado é "coerente" (escala determinada) e entra nos métodos. Estreitar a faixa tira, então, o divulgado da entrada dos métodos nas companhias que saem dela (GOLL4 e AZUL4 com [0,5; 2]), e não só o VPA. Se a escala indeterminada deve ou não derrubar o divulgado, que é por ação e não depende da escala das ações, é ponto aberto: entra na mesma decisão.

### 7.2 Controladora zerada com não controladores zerados — **[DECISÃO]**

O F2A-3 usa o lucro total quando 3.11.01 e 3.11.02 vêm zeradas (105 companhias na DFP 2025; KLBN11, LWSA3, PETZ3, SBSP3 e TIMS3 nas 45). A D20 só fala da linha **ausente**. Na KLBN11 o balanço mostra R$ 6,5 bilhões de não controladores, então o lucro total não é só da controladora; o ROE dos controladores do F2A-3 (0,213, contra 0,117 na V1) divide esse lucro total pelo PL já sem os não controladores, misturando escopos. Opções: tratar "zerada" como "ausente" e manter a reserva; aplicar a reserva só sem participação de não controladores no balanço; ou abster. O F2A-37 implementa o que for decidido.

### 7.3 Limiares de alerta (já entregues no F2A-5, sem mudança aqui)

- Ações da CVM × `sharesOutstanding` do yfinance: alerta acima de 5% (checkpoint da Fase 0, seção 4, item 1).
- LPA da cascata × LPA divulgado da mesma espécie: alerta acima de 10% (limiar que a V1 já usava). Com o F2A-36, o LPA dos métodos passa a ser o divulgado; o alerta passa a comparar o recalculado com ele.

### 7.4 Regras 2 e 5 da D19 juntas — **[DECISÃO]**

A seção 4 (abstenção 3) traz a leitura proposta: sem LPA divulgado de nenhuma espécie no documento, a escala fica indeterminada e o recalculado se abstém; com divulgado de outra espécie, o recalculado entra como aproximação declarada. A alternativa é buscar a escala em outro documento da mesma companhia. O Marcos confirma uma das duas na aprovação da ficha.
