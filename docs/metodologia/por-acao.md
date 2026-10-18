# Números por ação (LPA, VPA, ações, classes, units e escala) — versão 1.1

**Status:** versão 1.1 em revisão. Decisões do Marcos de 18/10/2026 nas seções 7.7 a 7.10, revistas no mesmo dia depois da primeira auditoria FICHA desta versão (três bloqueios: a garantia da faixa na 7.7, as companhias recuperáveis na 7.7 e a linha do BBAS3 na 7.8; mais as regras de domínio da seção 4). A segunda auditoria confirmou os três fechamentos e pediu a desigualdade exata da confirmação da 7.7, a reserva do lucro ausente alinhada ao F2A-41 e regras de domínio completas, feitos aqui. Aguarda a terceira auditoria e a aprovação (D21). A versão 1.0 foi aprovada pelo Marcos em 13/10/2026, depois da terceira auditoria externa em modo FICHA ("pode seguir para aprovação da ficha"); as versões 0.1 e 0.2 tiveram dois bloqueios cada, fechados com as decisões 7.1 a 7.6. Relatórios em `docs/loop/historico/fase-2a/auditoria-ficha-por-acao.md`. Mudança posterior exige nova versão, aprovação e auditoria (D21).
**Itens que dependem:** F2A-36 (LPA divulgado por espécie, classes e units), F2A-37 (reservas dos controladores); versão 1.1: F2B-10 (7.7), F2B-11 (7.8), F2B-12 (7.9) e F2B-13 (7.10)
**Origem no código:** F2A-3 (derivação por ação) e F2A-5 (alertas), já entregues
**Decisões de origem:** ADR-0003, D19, D20 e D21; checkpoint da Fase 0, seção 4, item 1 (revisado pela D19)

Esta ficha apresenta definições, dados e casos. As escolhas de parâmetro e de tratamento são do Marcos e estão registradas na seção 7, com data; nenhuma foi tomada pelo texto.

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

A versão 1.1 acrescenta duas atribuições que **não** são a definição da norma, e sim aproximações declaradas, com marca na proveniência: a linha agregada como LPA da espécie única (7.8) e a linha "PN" única atribuída a cada classe preferencial (7.9).

## 2. Insumos

| Insumo | Definição exata | Fonte | Unidade e escala | Data de referência |
|---|---|---|---|---|
| LPA básico por espécie | linhas 3.99.01.01, 3.99.01.02… da DRE consolidada; a espécie vem da **descrição** (ON, PN, PNA…), não do código | DFP/ITR, `dfp_cia_aberta_DRE_con_<ano>.csv` e `itr_cia_aberta_DRE_con_<ano>.csv` | R$ por ação; **não** passa pela `ESCALA_MOEDA` (a linha vem marcada MIL, mas o valor já é por ação) | `DT_REFER` do documento; no ITR, o período pelo `DT_INI_EXERC` e o `DT_FIM_EXERC`, com `ORDEM_EXERC` = ÚLTIMO. Lucro e LPA comparados na escala têm exatamente o mesmo intervalo; com trimestre e acumulado no documento, vale o acumulado do ano, o mesmo intervalo da DFP |
| Lucro dos controladores | par (código, descrição) "Atribuído a (aos) Sócios da Empresa Controladora" (3.11.01 ou 3.09.01, conforme a estrutura da DRE, em empresas e bancos; 3.11.01 ou 3.13.01 no modelo de seguradora), pela tabela `sentinela/data/referencia/contas_cvm.csv` | DFP/ITR | R$ × `ESCALA_MOEDA` (MIL → × 1.000) | `DT_REFER` |
| PL consolidado e não controladores | campos `pl_total` e `pl_nao_controladores` da tabela de contas, por modelo: 2.03 e 2.03.09 nas empresas e seguradoras; 2.07 ou 2.08, e 2.07.02 ou 2.08.09, nos bancos | DFP/ITR, BPP consolidado | R$ × `ESCALA_MOEDA` | `DT_REFER` |
| Ações por espécie e tesouraria | `QT_ACAO_ORDIN_CAP_INTEGR`, `QT_ACAO_PREF_CAP_INTEGR`, `QT_ACAO_ORDIN_TESOURO`, `QT_ACAO_PREF_TESOURO`, `QT_ACAO_TOTAL_TESOURO` | DFP/ITR, `composicao_capital` | **sem coluna de escala**: unidade ou milhar, conforme o documento (armadilha 10) | `DT_REFER`, mesma `VERSAO` |
| Lucro consolidado | campo `lucro_liquido` da tabela de contas: o par (código, descrição) de cada modelo, por exemplo 3.11 "Lucro/Prejuízo Consolidado do Período" nas empresas e 3.09 no ITUB4 | DFP/ITR | R$ × `ESCALA_MOEDA` | `DT_REFER` |
| LPA básico agregado | linha 3.99.01 sem espécie na descrição, quando a DRE não traz as linhas por espécie; zerada ou ausente, a 3.99, só com a conferência da 7.8 | DFP/ITR, `dfp_cia_aberta_DRE_con_<ano>.csv` | R$ por ação, como o LPA por espécie | `DT_REFER` |
| Ações em circulação no yfinance | `sharesOutstanding` do ticker; só confirma a escala na 7.7 e alimenta o alerta da 7.3 | yfinance | ações | data da consulta, com o valor, a fonte e o resultado da consulta (inclusive a falha) registrados na proveniência (D16) |
| Espécie do ticker | `Valor_Mobiliario` e `Sigla_Classe_Acao_Preferencial`; corrigida só pela tabela de correções, com evidência do próprio documento (7.10) | FCA, `valor_mobiliario` | — | `Data_Referencia` do FCA |
| Composição da unit | `Composicao_BDR_Unit` (por exemplo, "1 ON / 2 PN") | FCA | quantidade por unit | `Data_Referencia` do FCA |
| Preço | fechamento D-1 | yfinance (fluxo da V1; o COTAHIST do F2A-18 é a série oficial disponível) | R$ por ação, bruto | pregão anterior |

## 3. Regime, janela e data

- **Sem taxa:** a ficha não desconta nada. Os valores são nominais, na moeda da data do documento, sem atualização pela inflação.
- **Eventos societários:** desdobramento, grupamento ou bonificação entre a data do documento e o preço D-1 mudam a quantidade de ações (CPC 41, §§26 e 64). Até o tratamento de eventos (ADR-0002, D5; Fase 3), não há ajuste: o sinal é o alerta de divergência de ações contra o yfinance (7.3), e o múltiplo da data fica com essa limitação declarada (armadilha 11).
- **Janela:** um documento (o último `DT_REFER`, na maior `VERSAO`). O LPA divulgado da DFP é do exercício; no ITR, a DRE traz o trimestre e o acumulado do ano, separados pelo `DT_INI_EXERC` (F2A-16). Nenhum dos dois é TTM: os quatro trimestres são do F2A-7.
- **Data:** todos os números de um mesmo cálculo vêm do mesmo documento (CNPJ, `DT_REFER`, `VERSAO`). O VPA usa as ações do **fim do período** por definição (D19); o LPA recalculado também, e por isso é aproximação do divulgado (média ponderada). Múltiplos (P/L, P/VP) usam o preço bruto da data e as ações do mesmo documento do lucro (armadilha 11). A proveniência de cada campo (F2A-32) registra o documento, a versão e a data de entrega.

## 4. Hipóteses e inaplicabilidade

Abstenções (D19 e D20; textos que o código usa ou passará a usar):

1. **Composição do Capital ausente ou de outro documento:** sem ações, não há VPA nem LPA recalculado ("sem Composição do Capital no documento do lucro"; total de ações ≤ 0: "total de ações da Composição do Capital ≤ 0").
2. **Escala indeterminada:** sem LPA divulgado coerente de nenhuma espécie do mesmo documento para inferir a escala das ações, ou com a razão fora da faixa, a escala é indeterminada ("escala das ações indeterminada"; D19, regra 5). Abstêm-se só os números que dependem da quantidade de ações: LPA recalculado, VPA e capitalização. O **LPA divulgado não se abstém** por isso, porque já vem em R$ por ação (decisão 7.1). Duas fontes a mais para a escala, na versão 1.1: o lucro consolidado, quando o dos controladores se abstém (decisão 7.7), e a linha de LPA básico agregada, em companhia de espécie única (decisão 7.8).
3. **Mais de uma classe preferencial com direitos distintos** (PNA, PNB…; `Sigla_Classe_Acao_Preferencial` do FCA): o recalculado comum se abstém para as preferenciais; vale o divulgado da classe ou, quando a DRE traz uma só linha preferencial sem a sigla da classe, essa linha (decisão 7.9); sem nenhum dos dois, o LPA da classe se abstém (D19, regra 3).

   **Regras 2 e 5 juntas (decisão 7.4).** A regra 2 (divulgado ausente → recalculado como aproximação declarada) só se aplica quando outra espécie do **mesmo documento** traz LPA divulgado coerente que determina a escala. Sem nenhum divulgado coerente no documento, a escala é indeterminada (abstenção 2) e o recalculado se abstém. A escala nunca vem de outro documento.
4. **Unit com espécie componente sem LPA divulgado:** aplica-se a regra 2 com a marca; se a regra 3 proíbe o recalculado da espécie, a unit inteira se abstém (D19, regra 4). Composição não reconhecida: abstém-se ("unit sem composição oficial (ações por unit)").
5. **PL ou lucro dos controladores não identificados, ou PL ≤ 0:** sem ROE dos controladores ("PL dos controladores não identificado no documento", "lucro dos controladores não identificado no documento", "PL dos controladores ≤ 0").
6. **Bancos:** a 2.03 não é patrimônio líquido; o PL e o VPA vêm do modelo de instituição financeira (2.07 ou 2.08, pela tabela de contas; F2A-9).
7. **Par (código, descrição) sem correspondência na tabela de contas:** o campo se abstém (D20, F2A-33 e F2A-38).
8. **LPA divulgado incoerente (decisão 7.5):** o LPA da espécie se abstém, com alerta no relatório de qualidade, e o recalculado **não** entra no lugar. Incoerente é: (a) sinal oposto ao do lucro dos controladores ou, quando este se abstém, ao do lucro consolidado (3.11; decisão 7.6); ou (b) mais de uma linha de LPA básico para a mesma espécie com valores diferentes. Linhas repetidas com o mesmo valor contam como uma. Caso real: a QUAL3 traz na DRE consolidada duas linhas básicas "ON", −0,00895 e +0,04662, com lucro dos controladores positivo (R$ 10.665.000): é conflito de linhas (b), e uma delas também tem sinal oposto (a). Textos: "LPA divulgado com sinal oposto ao lucro dos controladores" (ou "ao lucro consolidado") e "LPA divulgado com linhas conflitantes para a espécie".
9. **Sinal não conferível (decisão 7.6):** sem lucro dos controladores e sem lucro consolidado válido no documento, o LPA divulgado se abstém ("sinal do LPA divulgado não conferível: lucro não identificado no documento").
10. **Insumo inválido (versão 1.1):** valor não numérico, NaN ou infinito em qualquer insumo desta ficha nunca vira zero, valor de outra fonte nem reserva; o número que depende dele se abstém, com o motivo. Em particular:
    - linha de LPA não finita faz a espécie se abster, mesmo com outra linha válida: é dado com problema, como as linhas conflitantes da 7.5 ("LPA divulgado inválido para a espécie");
    - quantidade de ações negativa, não finita, fracionária ou com a coluna ausente, em qualquer coluna da Composição do Capital, ou tesouraria maior que o capital da espécie, invalida a Composição ("Composição do Capital inválida"), como o total ≤ 0 da abstenção 1;
    - tesouraria total diferente da soma das espécies: vale a regra atual (o total; a soma só quando o total falta) até o levantamento da 2B conferir os casos (F2B-21, pergunta 8);
    - `sharesOutstanding` do yfinance ausente, ≤ 0 ou não finito: a confirmação da 7.7 falha, e a abstenção continua;
    - composição de unit com quantidade não inteira ou ≤ 0 é composição não reconhecida (abstenção 4).
11. **Zero (versão 1.1):** linha de LPA igual a zero conta como não informada, porque o arquivo da CVM usa zero na linha sem valor (COGN3, RECV3, VIVT3 e TIMS3 trazem todas as linhas 3.99 zeradas). Lucro, PL e VPA iguais a zero são dados.
12. **Prejuízo e PL negativo são dados (versão 1.1):** LPA negativo, prejuízo, PL e VPA negativos entram como estão (decisão do Marcos de 18/10/2026 sobre o achado 1 da auditoria da 2A). O ROE se abstém com PL ≤ 0 (abstenção 5), e cada método decide a própria aplicabilidade (o Graham com VPA ≤ 0, por exemplo).
13. **Fora do escopo:** FIIs. O VPA e o P/VP da cota vêm do Informe Mensal (F2A-11) e ficam com a ficha do FII (F2B-25).

Reservas permitidas (D20, política aprovada com o ADR, e decisão 7.2):
- **Lucro dos controladores ausente:** vale o lucro total só se não houver minoritários nem na DRE nem no balanço: a linha dos não controladores ausente ou zerada **e** a participação dos não controladores no balanço (2.03.09, ou o par do modelo) ausente ou zerada. É o que o código faz desde o F2A-41 (BUG-2A-03); a versão 1.0 deste texto pedia só a DRE.
- **Lucro dos controladores zerado com o dos não controladores zerado ou ausente, e lucro consolidado diferente de zero:** o documento não separou o lucro. Vale o lucro total só se o balanço também não mostrar minoritários (2.03.09 ausente ou zerada). Com 2.03.09 diferente de zero, o lucro dos controladores se abstém ("lucro dos controladores não separado no documento, com não controladores no balanço").
- **PL dos controladores:** vale o PL total só se a participação dos não controladores no balanço estiver ausente ou zerada **e** o lucro dos não controladores também.
- **Valor inválido** (não numérico, NaN, infinito) nunca autoriza reserva: o campo se abstém.

**Por que a reserva é aceitável.** Sem a linha dos não controladores, a companhia não informa minoritários; tratar o consolidado como da controladora é a leitura do próprio documento. A ausência é falta de evidência, não prova de que não há minoritários (D20); por isso a reserva fica registrada na proveniência do campo. As linhas 3.11.01 e 3.11.02 zeradas com lucro consolidado diferente de zero não somam o consolidado: o zero ali é falta de separação, não um valor informado, e por isso recebe o mesmo tratamento da ausência, com a conferência do balanço.

**Onde a reserva seria usada** (levantamento só de leitura na DFP 2025 consolidada, última versão de cada companhia; script e saída em `outputs/f2a34_reservas.py` e `outputs/f2a34_reservas.json`, fora do git):
- 439 companhias com DRE e BPP consolidados (a mesma contagem para DRE ou BPP). As listas "nas 45" casam a companhia pelo código CVM do mapa, e não pelo ticker do índice: AZUL4, GOLL4 e PETZ3 estão nas 45 com código, mas fora do índice com esse ticker.
- **Lucro dos controladores ausente:** 0 (todas trazem a linha "Atribuído a Sócios da Empresa Controladora").
- **Lucro dos controladores zerado com o dos não controladores zerado ou ausente:** 105. Hoje o F2A-3 usa o lucro total em todos; pela decisão 7.2, o F2A-37 o mantém só onde o balanço não mostra minoritários. Nas 45 ações do mapa: KLBN11, LWSA3, PETZ3, SBSP3 e TIMS3 (o diário do F2A-3 citou KLBN11, SBSP3, PETZ3 e LWSA3; a TIMS3 também está no caso, mas não teve LPA derivado). Na KLBN11 a participação dos não controladores no balanço é de R$ 6,5 bilhões (2.03.09): há minoritários, e o lucro total pode incluir a parte deles, que o documento não informa. Pela decisão 7.2, o lucro dos controladores da KLBN11 se abstém (e com ele o ROE e o LPA recalculado); pela decisão 7.7, a escala das ações passa a vir do lucro consolidado, e o VPA volta. O LPA divulgado segue nos métodos, com o sinal conferido contra o lucro consolidado (R$ 1.678.211.000, positivo; decisão 7.6): 0,2286 para ON e para PN, e para a unit KLBN11 = 1 × 0,2286 + 4 × 0,2286 = **1,1430** (FCA 2026, documento 155729: 1 KLBN3 + 4 KLBN4). O F2A-37 conta no diário quantas das 105 caem em cada lado.
- **PL total como PL dos controladores** (2.03.09 ausente ou zerada e lucro dos não controladores ausente ou zerado): 171 companhias fora do setor "Bancos", mais 2 bancos (BEES3 e um sem ticker no índice), em que a reserva não seria usada porque o PL do banco se abstém até o F2A-9. Nas 45 ações: AZUL4, GOLL4, LREN3, LWSA3, MGLU3, PETZ3, RECV3, SBSP3 e TIMS3.
- **PL com reserva bloqueada** (2.03.09 ausente ou zerada, mas lucro dos não controladores diferente de zero): 8; com ticker no índice: SEQL3, SBFG3, INEP3, POSI3 e MWET3/MWET4. Pela D20, o PL dos controladores se abstém nesses casos.

## 5. Exemplo calculado de forma independente

Valores lidos à mão nos CSVs publicados pela CVM (DFP 2025, `dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_2025.zip`, arquivo com SHA-256 `336a92cc2d0829b5b96adcf2550f9acd469503cbf8b8cb6a05873ddd668bc4d2`, coletado em 1/10/2026 segundo a proveniência do F2A-32; a versão 0.1 citava 8/10/2026, data da consulta, não da coleta) e no FCA 2026 (`fca_cia_aberta_2026.zip`). Nenhum código do projeto foi rodado ou importado para as contas.

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
7. Para comparação: com o lucro consolidado (110.605.000 mil), o LPA recalculado seria 8,5815 (+0,43% sobre o dos controladores; +0,49% sobre o divulgado); com o PL consolidado, o VPA seria 32,40 (+0,43%).

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

**Nota da versão 1.1 sobre o arquivo.** A primeira auditoria FICHA da 1.1 (18/10/2026) conferiu os números de Petrobras e Taesa em outra cópia da DFP 2025, com outro SHA-256 (a CVM republica o arquivo; a coleta registrada pela proveniência foi refeita em 13/10/2026). Os valores conferem nas duas cópias; o hash acima é o da coleta de 1/10/2026.

### 5.3 Casos da versão 1.1

Contas refeitas de forma independente pela auditoria externa (Codex, modo FICHA, 18/10/2026, primeira e segunda rodadas; os casos sintéticos só testam a regra), só com a biblioteca padrão sobre os CSVs da DFP 2025 e do FCA 2026, sem o código do projeto. Viram teste nos itens indicados; tolerância de 1e−6 nas contas, e os divulgados como publicados.

| Decisão | Caso | Conta | Resultado | Item |
|---|---|---|---|---|
| 7.7 | KLBN11 | ações: 6.241.478.850 − 106.051.185 (tesouraria) | 6.135.427.665 | F2B-10 |
| 7.7 | KLBN11 | razão: 1.678.211.000 (lucro consolidado) ÷ 6.135.427.665 ÷ 0,2286 | 1,1965352 (escala: unidade) | F2B-10 |
| 7.7 | KLBN11 | VPA da unit: (14.401.101 − 6.515.155) mil ÷ 6.135.427.665 × 5 | 6,4265659 | F2B-10 |
| 7.8 | BBAS3 | 3.99.01 = 0; 3.99 = 2,40; recalculado na unidade: 13.698.124.000 ÷ (5.730.834.040 − 22.370.399) = 2,3996166; razão 0,9998402 (a até 10%) | LPA 2,40 | F2B-11 |
| 7.7 | sintético (confirmação) | ações da CVM 6.135.427.665 contra `sharesOutstanding` de 6.000.000.000 (razão 1,0226) e de 6.135.428 (razão 1.000) | aceita; recusa (abstém) | F2B-10 |
| 7.7 | sintético (limites) | razões 0,1, 10 e 0,0999 | as três recusam (desigualdade estrita) | F2B-10 |
| 7.9 | USIM5 | linha básica "PN" atribuída à PNA | −2,50 | F2B-12 |
| 7.10 | MGLU3 | recalculado: 204.603.000 ÷ (775.945.010 − 1.343.449) | 0,2641397, contra o divulgado ON 0,264 | F2B-13 |

## 6. Sensibilidade

| Premissa | Alternativa | Efeito no exemplo | Efeito medido no universo |
|---|---|---|---|
| Escala das ações | trocar unidade por milhar | LPA e VPA ÷ ou × 1.000 | DFP 2025: 70 de 255 companhias determinadas em milhares (F2A-16) |
| Lucro dos controladores × consolidado | usar o consolidado | PETR: LPA recalculado +0,43% | 157 de 255 com lucros diferentes; o dos controladores fica mais perto do divulgado em 107 (68%) (F2A-16) |
| PL dos controladores × consolidado | usar o consolidado | PETR: VPA +0,4% | F2A-3 (consolidado → controladores): CSAN3 VPA 7,86 → 1,34 e ROE −0,329 → −1,833; BEEF3 VPA 1,91 → 1,33 e ROE 0,448 → 0,619; EQTL3 ROE 0,088 → 0,065; ENEV3 0,079 → 0,058; VALE3 0,063 → 0,075; SLCE3 0,100 → 0,110 |
| Ações do fim do período × média ponderada | recalculado no lugar do divulgado | PETR: +0,05% | razão recalculado ÷ divulgado nas 38 ações do mapa com razão: mediana 1,000, 4º menor 0,631, máximo 1,199 (F2A-3). A razão não isola este efeito: mistura também o lucro total usado com minoritários (KLBN11) e o arredondamento do divulgado (GOLL4, −0,001) |
| Composição da unit | dividir o PL consolidado pelo número de units (V1) | — | KLBN11: VPA da unit 11,85 → 6,43 na troca da V1 para o F2A-3; a queda mistura a composição da unit com a saída dos R$ 6,5 bi de não controladores do PL |
| Escala pelo lucro consolidado (7.7) | escala errada, nos dois sentidos | VPA e capitalização × ou ÷ 1.000 | sem confirmação, a faixa aceitaria a escala errada com o consolidado entre 100 e 10.000 vezes o dos controladores (ou entre 1/10.000 e 1/100); com a confirmação, o erro de 1.000 vezes se abstém **se** a quantidade do yfinance estiver certa e for comparável (mesma data aproximada, sem evento societário entre as duas); com o yfinance errado por fator parecido, o erro passa, e é o risco aceito |
| Linha "PN" única (7.9) | LPA próprio de cada classe preferencial | desconhecido sem a nota de resultado por ação da companhia | USIM5: −2,50 na PNA e na PNB |

## 7. Parâmetros e justificativa

### 7.1 Faixa da razão para inferir a escala: [0,1; 10] — **decidido pelo Marcos em 13/10/2026: manter**

O F2A-3 escolhe unidade ou milhar pela razão (LPA recalculado ÷ LPA divulgado) mais perto de 1, no sentido de menor `|log(razão)|` (`sentinela/data/acoes_cvm.py`), e só aceita a escolha se a razão cair em [0,1; 10]. As duas hipóteses diferem por 1.000, então a escolha só fica ambígua perto de 1/31,6 ou de 31,6 (a raiz de 1.000); a faixa fica dentro desse intervalo com folga.

Distribuição medida:
- **Universo da DFP 2025** (F2A-16, 255 companhias com escala determinável; o lucro é o dos controladores ou, em **49** delas, o lucro total, porque o levantamento usa `controladores or total` também quando a linha dos controladores vem zerada — `scripts/levantamento_fase2a.py`; contagens reproduzidas pela auditoria externa): razão na escala escolhida entre ≈ 0 e 19,9; p10 0,837, mediana 1,000, p90 1,051; 209 de 255 dentro de 10%; fora de [0,8; 1,25]: 28; fora de [0,5; 2]: 17; **fora de [0,1; 10]: 5** (CD_CVM 016675 ≈ 0; 004537 0,001; 018414 0,001; 024120 0,08; 023000 19,9).
- **45 ações do mapa** (F2A-3, 38 com razão): mínimo 0,142, mediana 1,000, máximo 1,199; escala MIL em 9 (ABEV3, CMIG4, CYRE3, ELET3, ENEV3, ITUB4, LREN3, MRVE3, VALE3). Sem razão: ASAI3 e NTCO3 (sem DFP consolidada 2025 nem Composição do Capital), COGN3, RECV3, TIMS3 e VIVT3 (linhas 3.99 todas zeradas) e QUAL3 (duas linhas "ON" conflitantes, −0,00895 e +0,04662; abstenção 8).
- **As duas distribuições não são diretamente comparáveis:** a do F2A-16 usa só LPA positivos e o lucro dos controladores com a reserva acima (49 casos com lucro total); a do F2A-3 aceita prejuízo com LPA do mesmo sinal (por isso o mínimo nas 45 é 0,142, da GOLL4, aqui, e 0,258, da AZUL4, no F2A-16).

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

Opções apresentadas: manter [0,1; 10]; estreitar para [0,5; 2] (17 de 255 fora); ou [0,8; 1,25] (28 de 255).

**Decisão (13/10/2026):**
- **Manter [0,1; 10].** A faixa só distingue unidade de milhar (fator 1.000); a qualidade do número é papel do alerta de 10% do F2A-5, não da faixa. Estreitá-la misturaria as duas funções.
- **Escala indeterminada não derruba o LPA divulgado.** Ela derruba só o que depende da quantidade de ações (recalculado, VPA, capitalização). Isso revisa a regra 1 da D19: "coerente" passa a ser "mesmo sinal do lucro dos controladores (ou do consolidado, quando aquele se abstém; 7.6) e uma única linha por espécie", sem a condição de escala (ADR-0003, revisão de 13/10/2026).
- O F2A-36 refaz a contagem fora da faixa com a política da decisão 7.2 e registra no diário; a faixa não muda por isso.

### 7.2 Controladora zerada com não controladores zerados — **decidido pelo Marcos em 13/10/2026**

O F2A-3 usa o lucro total quando 3.11.01 e 3.11.02 vêm zeradas (105 companhias na DFP 2025; KLBN11, LWSA3, PETZ3, SBSP3 e TIMS3 nas 45). A D20 só fala da linha **ausente**. Na KLBN11 o balanço mostra R$ 6,5 bilhões de não controladores: há minoritários, mas o documento não diz quanto do lucro do exercício é deles, então o lucro total pode misturar escopos. O ROE dos controladores do F2A-3 (0,213, contra 0,117 na V1) divide esse lucro total pelo PL já sem os não controladores. Opções apresentadas: tratar "zerada" como "ausente"; aplicar a reserva só sem participação de não controladores no balanço; ou abster sempre.

**Decisão:** reserva só sem participação de não controladores no balanço (2.03.09 ausente ou zerada); com ela diferente de zero, o lucro dos controladores se abstém. É a mesma conferência que a D20 já faz para o PL. A distinção entre linha ausente, linha zerada e valor inválido continua: valor inválido nunca autoriza reserva. O F2A-37 implementa.

### 7.3 Limiares de alerta (já entregues no F2A-5, sem mudança aqui)

- Ações da CVM × `sharesOutstanding` do yfinance: alerta acima de 5% (checkpoint da Fase 0, seção 4, item 1).
- LPA da cascata × LPA divulgado da mesma espécie: alerta acima de 10% (limiar que a V1 já usava). Com o F2A-36, o LPA dos métodos passa a ser o divulgado; o alerta passa a comparar o recalculado com ele.

### 7.4 Regras 2 e 5 da D19 juntas — **decidido pelo Marcos em 13/10/2026**

A seção 4 (abstenção 3) traz a leitura proposta: sem LPA divulgado de nenhuma espécie no documento, a escala fica indeterminada e o recalculado se abstém; com divulgado de outra espécie, o recalculado entra como aproximação declarada. A alternativa era buscar a escala em outro documento da mesma companhia.

**Decisão:** a escala vem só de outra espécie do **mesmo documento**. Outro documento nunca: quebraria a regra de que todos os números de um cálculo vêm do mesmo documento, e a escala da Composição do Capital pode mudar entre documentos. A regra 3 continua com precedência: o divulgado de outra espécie determina a escala, mas não autoriza o recalculado comum para preferenciais com direitos distintos.

### 7.5 LPA divulgado incoerente — **decidido pelo Marcos em 13/10/2026**

A versão 0.1 tratava divulgado incoerente como ausente (regra 2), o que a D19 não previa (bloqueio da auditoria de 13/10/2026). **Decisão:** divulgado incoerente faz o LPA da espécie se abster, com alerta, sem recalculado no lugar (seção 4, abstenção 8). Sinal trocado ou linhas conflitantes indicam dado com problema, e a reserva o esconderia.

### 7.6 Sinal do LPA divulgado quando o lucro dos controladores se abstém — **decidido pelo Marcos em 13/10/2026**

A decisão 7.2 faz o lucro dos controladores se abster em casos como a KLBN11, mas a coerência do divulgado (7.1 e 7.5) confere o sinal contra esse lucro (bloqueio da segunda auditoria). Opções apresentadas: conferir o sinal contra o lucro consolidado (3.11); ou abster também o divulgado.

**Decisão:** conferir contra o lucro consolidado (3.11, par código e descrição pela tabela do F2A-33). A proveniência do campo registra "sinal conferido pelo lucro consolidado: lucro dos controladores indisponível". Sem lucro consolidado válido, o divulgado se abstém (seção 4, abstenção 9). O sinal do consolidado pode diferir do dos controladores quando os minoritários têm resultado de sinal oposto e maior; é limitação aceita e declarada.

### 7.7 Escala pelo lucro consolidado quando o lucro dos controladores se abstém — **decidido pelo Marcos em 18/10/2026**

Pela decisão 7.2, o lucro dos controladores se abstém em 9 companhias da DFP 2025, a KLBN11 entre elas (diário do F2A-36). Sem ele, a razão da 7.1 não tem numerador: a escala fica indeterminada, e o VPA e a capitalização se abstêm, mesmo com o PL dos controladores lido. Opções apresentadas: manter a abstenção; ou inferir a escala pelo lucro consolidado (3.11).

**Decisão:** inferir pelo lucro consolidado, só para a escala, com confirmação independente.
- **A faixa não garante a escala.** A escala só escolhe entre unidade e milhar (fator 1.000). Numa hipótese simplificada (ações do fim do período iguais à média ponderada, uma só classe), a razão na escala certa vale f = lucro consolidado ÷ lucro dos controladores, que o documento não informa quando a 7.2 se aplica. A escolha erra se f passar de 31,6 (a raiz de 1.000) ou ficar abaixo de 1/31,6. A faixa [0,1; 10] da 7.1 recusa f entre 10 e 100 (e entre 1/100 e 1/10), mas **aceita a escala errada com f entre 100 e 10.000** (ou entre 1/10.000 e 1/100), porque a razão errada cai dentro dela. A primeira auditoria FICHA da 1.1 mostrou o contraexemplo; a versão anterior deste texto dizia o contrário.
- **Confirmação (decisão de 18/10/2026, depois da auditoria):** o VPA e a capitalização só voltam se, na escala escolhida, valer **0,1 < Q_CVM ÷ Q_yf < 10**, com as duas desigualdades estritas, em que:
  - Q_CVM é o total de ações em circulação da Composição do Capital (ON + PN − tesouraria); para unit, esse total dividido pelo número de ações por unit;
  - Q_yf é a `sharesOutstanding` do yfinance para o mesmo ticker, com a proveniência da seção 2.

  Um erro de escala põe a razão perto de 1.000 ou de 0,001, fora do intervalo. Os dois lados nem sempre medem a mesma coisa (o yfinance pode contar só uma espécie, ou units): é hipótese aceita, não propriedade demonstrada. Quando a razão sai do intervalo por isso, o caso se abstém, que é o lado seguro. Q_yf ausente, ≤ 0 ou não finito: a abstenção continua. O yfinance só confirma; nunca entra no cálculo. A diferença para o alerta da 7.3 (`Q_yf ÷ Q_CVM − 1` acima de 5%) é de papel: o alerta continua só alerta, e a confirmação só decide se a escala inferida pelo consolidado pode ser usada (revisão da D19 de 18/10/2026).
- **Só o documento mais recente.** A `sharesOutstanding` é de hoje e não confirma exercícios passados: nas séries de cinco anos (`series_cvm`), esses casos seguem com a escala indeterminada (histórico estrito, D17).
- O lucro consolidado nunca entra no LPA, no ROE nem no recalculado, que continua abstido sem o lucro dos controladores.
- O LPA divulgado usado na razão é o coerente pela 7.6 (sinal conferido contra o consolidado).
- A proveniência do VPA registra "escala inferida pelo lucro consolidado e confirmada pela quantidade do yfinance: lucro dos controladores indisponível (7.2)".

Efeito: das 9 companhias, 7 têm razão calculável dentro da faixa e são candidatas, sujeitas à confirmação: Sul 116 (0,532), Lifemed (0,162), Cantu (0,972), VLI (2,067), Cambuci (1,000), Mundial (1,000) e Klabin (1,197) (primeira auditoria FICHA da 1.1). Cataguases (sem LPA por espécie) e Aliperti (linhas ON e PN zeradas) seguem em abstenção. O F2B-10 registra o resultado de cada uma.

### 7.8 Linha agregada de LPA em companhia de espécie única — **decidido pelo Marcos em 18/10/2026**

O BBAS3 e o Banco Pine (62.144.175/0001-20) trazem na DRE consolidada só as linhas agregadas (3.99 e 3.99.01), sem a espécie na descrição. Pela 7.4, a escala fica indeterminada, e LPA, VPA e P/VP se abstêm (diário do F2A-36). No BBAS3, a 3.99.01 ("Lucro Básico por Ação") vem **zerada**, e o valor está na 3.99, o título do grupo: 2,40 (`docs/decisoes/fontes-fase2a.md`, seção 2). Pelo CPC 41 (§66), o LPA é apresentado por classe de ação ordinária; numa companhia com uma só espécie, o LPA básico da companhia é o dessa espécie, mas a norma não diz que o valor da 3.99 seja o básico. Opções apresentadas: manter a abstenção; tratar a 3.99.01 como o LPA da espécie única; e, depois da primeira auditoria FICHA da 1.1, aceitar também a 3.99 com conferência.

**Decisão** (a segunda parte, depois da auditoria): em companhia com uma só espécie no FCA (o BBAS3, só ON) e sem linhas de LPA por espécie na DRE:
- vale a linha de LPA básico agregada (3.99.01);
- se ela vier zerada ou ausente, vale a 3.99, **só** se o LPA recalculado na escala escolhida ficar a até 10% dela (o limiar da 7.3). Sem essa conferência, a 3.99 não entra: ela é o título do grupo e pode trazer outro número, como o diluído. No BBAS3, o F2A-3 mediu razão 1,000;
- a linha usada passa pela mesma coerência das espécies (7.5 e 7.6: sinal e linha única) e serve à escala;
- com mais de uma espécie no FCA (o Pine), a abstenção continua: a linha agregada não diz de qual classe é;
- a proveniência registra "LPA da linha agregada (3.99.01 ou 3.99, conferida pelo recalculado): companhia de espécie única no FCA".

Efeito: o BBAS3 ganha LPA divulgado (2,40), escala e VPA pelo modelo de banco; o F2B-11 conta quantas companhias da DFP 2025 trazem só a linha agregada, por número de espécies e por linha usada.

### 7.9 Linha "PN" única com mais de uma classe preferencial — **decidido pelo Marcos em 18/10/2026**

A USIM5 tem PNA e PNB no FCA, e a DRE consolidada traz uma só linha básica "PN". Pela regra 3 (seção 4, abstenção 3), a PNA se abstém; numa unit da mesma companhia, o componente PN usaria a linha "PN" (revisão do F2A-36). As duas leituras do mesmo documento divergem. Opções apresentadas: (i) a linha "PN" única vale para todas as classes preferenciais quando a DRE não as separa; (ii) a unit também se abstém nesse caso; (iii) manter a assimetria.

**Decisão: (i).**
- Quando a DRE traz uma só linha básica preferencial, sem a sigla da classe, e o FCA mostra mais de uma classe preferencial, essa linha é **atribuída** a cada classe preferencial como LPA divulgado. É uma aproximação declarada: a companhia divulgou o número das preferenciais sem separar as classes, e o CPC 41 (§66, A13 e A14) pede o número por classe quando os direitos diferem.
- Linha da classe presente e incoerente (7.5): a classe se abstém, sem recorrer à linha "PN" única.
- A regra 3 continua proibindo o recalculado comum para essas classes.
- A ação avulsa e o componente da unit seguem a mesma ordem: a linha da classe (por exemplo, "PNA") e, sem ela, a linha "PN" única. A composição da unit guarda a sigla da classe ("2 PNA").
- A proveniência registra "LPA da linha PN única, aplicado à classe <classe>".

Efeito: a USIM5 ganha LPA; o F2B-12 conta as companhias da DFP 2025 com mais de uma classe preferencial no FCA e uma só linha "PN" na DRE.

### 7.10 Espécie do FCA contradita pelo próprio documento — **decidido pelo Marcos em 18/10/2026**

O FCA 2026 (versão 1) classifica a MGLU3 como "Ações Preferenciais", e a DRE e a Composição do Capital do documento só trazem ON; o LPA usa o recalculado com marca (diário do F2A-36). Opções apresentadas: manter; ou corrigir a espécie pela tabela de correções do F2A-19.

**Decisão:** corrigir pela tabela de correções, com a regra aprovada em 5/10/2026 (evidência oficial em cada linha; correção visível na proveniência e no relatório do F1-12).
- A correção de espécie exige duas evidências do mesmo documento: a Composição do Capital (quantidade da espécie do FCA igual a zero, e a da espécie corrigida diferente de zero) e a DRE (linha de LPA só da espécie corrigida). Com uma só, a linha é rejeitada.
- Correção caso a caso, com arquivo, coluna e data; nunca automática.
- A correção vale para os documentos citados na linha da tabela (FCA e DFP, com a versão), no intervalo de datas que a linha declara. Não se estende sozinha a documentos anteriores ou posteriores (histórico estrito, D17).

Efeito: a MGLU3 passa a usar o LPA divulgado da ON; o F2B-13 registra o antes → depois e a cobertura do índice.
