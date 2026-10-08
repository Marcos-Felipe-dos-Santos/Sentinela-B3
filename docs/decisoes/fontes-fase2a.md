# Levantamento das fontes oficiais da Fase 2A (F2A-16)

Gerado em 8/10/2026 por `scripts/levantamento_fase2a.py`, que grava os números em `outputs/levantamento_fase2a.json` (fora do git) e guarda os downloads em `outputs/levantamento_cache/`. Rede só de leitura (CVM, B3, Banco Central, yfinance). O script não importa `config`, não usa token da brapi, não lê `.env`, banco nem carteira. A amostra vem dos mapas públicos do código. Nenhum módulo de produção foi alterado, e este documento não decide nada novo.

Arquivos lidos:
- FCA 2026, DFP 2025, ITR 2026 e Informe Mensal de FII 2026 (CVM);
- COTAHIST de julho, agosto e setembro de 2026 (B3), 65 pregões;
- Registro de fundos e classes (CVM) e IF.data (Banco Central, Olinda).

## 1. FCA (F2A-1, F2A-3)

**Colunas de `valor_mobiliario`:** `CNPJ_Companhia`, `Data_Referencia`, `Versao`, `ID_Documento`, `Nome_Empresarial`, `Valor_Mobiliario`, `Sigla_Classe_Acao_Preferencial`, `Classe_Acao_Preferencial`, `Codigo_Negociacao`, `Composicao_BDR_Unit`, `Mercado`, `Sigla_Entidade_Administradora`, `Entidade_Administradora`, `Data_Inicio_Negociacao`, `Data_Fim_Negociacao`, `Segmento`, `Data_Inicio_Listagem`, `Data_Fim_Listagem`.

**Valores de `Valor_Mobiliario`** (964 linhas): Ações Ordinárias 406, Debêntures 309, Ações Preferenciais 155, Nota Comercial 41, **Units 12**, Valor Mobiliário Não Registrado 11, Bônus de Subscrição 8, Debêntures Conversíveis 6, CRI 4, Certificados de depósito 4+1, Letras Financeiras 3, CRA 2, Título de Investimento Coletivo 1, **BDRs 1**. `Mercado`: Bolsa 530, Balcão Organizado 278, Balcão Não-Organizado 94.

**ISIN:** não há coluna de ISIN no FCA.

**Composição das units:** `Composicao_BDR_Unit` é **texto livre** e está preenchida em 11 das 12 units ("1 ON / 2 PN", "1 ON E 2 PN", "1 ação ordinária e 4 ações preferenciais", "1 KLBN3 + 4 KLBN4", "1 PN + 3 Recibos de Subscrição"). Não é número. Uma das 12 não tem código de negociação (Oliveira Trust), e duas têm código fora do formato: o BTG Pactual (`000000`) e a Rodobens (`RBNS`, sem o dígito).

**Códigos de negociação fora do formato de ticker** (quatro caracteres alfanuméricos, o primeiro letra, e um ou dois dígitos, depois de maiúsculas e sem espaços; aceita `B3SA3` e `tgma3`): **54 de 535** códigos preenchidos. Exemplos: `0`, `00`, `000000`, `4030` (a CSN, que é o próprio CD_CVM), `1545-8`, `ADR`, `B3`, `BNPA3B` (sufixo de uma letra), `RBNS`.

**Códigos sem data de fim que não negociaram no COTAHIST** (jul–set/2026, mercado à vista): dos 432 códigos de ações e units em Bolsa, no formato de ticker e sem `Data_Fim_Negociacao`, **68 não têm nenhuma cotação** no trimestre. Dos mapas públicos do código, só **BRML3**. Outros exemplos: AESO3, APTI3, BBML3, BPAR3, CELP3, CRDE3.

**Consequência.**
- F2A-1: o FCA sozinho não dá a classe nem o ticker confiável. Com o critério da fila (código sem data de fim), entram 68 códigos que não tiveram nenhum negócio em jul–set/2026 (entre eles BRML3, do mapa público), e há 54 códigos preenchidos que não seguem o formato de ticker, entre eles o `4030` da CSN, que é o CD_CVM. O COTAHIST dá a informação de negociação recente; usá-la como filtro seria regra nova e fica para o Marcos decidir.
- F2A-3: a composição de unit é texto livre ("1 ON / 2 PN", "1 KLBN3 + 4 KLBN4"); um parser precisa reconhecer esses padrões, e o que não reconhecer cai no caso "unit sem composição oficial" da fila.

## 2. Escala da Composição do Capital (F2A-3, F2A-5; armadilha 10)

**Fatos do arquivo (DFP 2025).**
- O CSV da Composição do Capital **não tem coluna de escala**: só `QT_ACAO_ORDIN_CAP_INTEGR`, `QT_ACAO_PREF_CAP_INTEGR`, `QT_ACAO_TOTAL_CAP_INTEGR` e as três de tesouraria.
- A linha 3.99 da DRE **passa pela `ESCALA_MOEDA`**: 2.253 das 2.303 linhas 3.99 trazem `MIL`. Mas o valor está em R$ por ação (ITUB4, 3.99.01: 8,10). A escala monetária **não se aplica** a essas linhas. Aplicar o fator de 1.000 (como o `parsear_demonstrativo` faz com qualquer conta) multiplicaria o LPA por 1.000.
- O LPA básico vem **por espécie**: 3.99.01.01 (ON), 3.99.01.02 (PN) e as de PNA a PND (3.99.01.03 e seguintes). Em alguns casos a linha 3.99.01 está zerada e só a 3.99 e as de espécie têm valor (BBAS3: 3.99 = 2,40, 3.99.01 = 0).
- **Lucro e PL atribuídos aos controladores:** lucro em 3.11.01 (433 empresas) ou 3.09.01 (modelo de banco do ITUB4); PL total em 2.03 (439 empresas) e participação dos não controladores em 2.03.09 (426 empresas). O PL dos controladores é 2.03 − 2.03.09.

**Regra aplicada** (a da fila): a escala (1 ou 1.000) que aproxima lucro atribuído aos controladores ÷ ações (ON + PN − tesouraria) do LPA básico da ON (ou da PN, se não há ON).

**Ações do mapa regenerado** (45; a tabela do dossiê só lista as 10 com maior divergência, então a amostra de 38 não é reconstituível; o confronto usa o mapa inteiro): a regra determina **31 de 45**.
- Escala 1.000 em **8**: ABEV3, CMIG4, CYRE3, ELET3, ENEV3, ITUB4, LREN3, VALE3.
- Razão LPA calculado ÷ divulgado: p10 0,963, mediana 1,000, p90 1,029; 27 de 31 dentro de 10%.
- Não determinadas (14), com o motivo que o script registra: lucro dos controladores ≤ 0 (CSAN3, GOLL4, HAPV3, LWSA3, MRVE3, USIM5); sem LPA básico em 3.99.01.01 nem em 3.99.01.02 (BBAS3, COGN3, RECV3, VIVT3); sem linha de Composição do Capital (ASAI3, NTCO3); LPA ≤ 0 (QUAL3); sem lucro nas contas procuradas (TIMS3). No universo, as 439 empresas com DRE perdem 184 pelos mesmos motivos: lucro ≤ 0 (124), sem LPA na ON nem na PN (54), LPA ≤ 0 (3) e sem lucro nas contas procuradas (3). ASAI3 e NTCO3 nem aparecem na DFP 2025 consolidada, por isso não estão no universo.

**Confronto com o dossiê.** O texto do dossiê diz que 9 empresas informam em milhares, mas a tabela dele lista só duas com a marca (CMIG4 e ITUB4); as duas batem com a regra. A regra aponta mais **seis** (ABEV3, CYRE3, ELET3, ENEV3, LREN3 e VALE3) que não estão na tabela; podem ser algumas das 7 que o dossiê contou e não listou, e isso não é verificável com o documento. Nenhuma das duas marcadas deixou de ser confirmada.

**Universo da DFP 2025** (255 empresas determinadas): 70 em milhares. Razão calculado ÷ divulgado, já na escala escolhida: p10 0,837, mediana 1,000, p90 1,051, mínimo ≈ 0 e máximo 19,9; 209 de 255 dentro de 10%. Fora de [0,8; 1,25]: 28; fora de [0,5; 2]: 17; fora de [0,1; 10]: 5. Os piores casos (CD_CVM, razão): 016675 (≈ 0), 004537 (0,001), 018414 (0,001), 023000 (19,9), 024120 (0,08). Nas 45 ações do mapa: mínimo 0,258 (AZUL4), máximo 1,199; fora de [0,5; 2]: só a AZUL4. Em 157 das 255 o lucro total é diferente do dos controladores, e nessas o lucro dos controladores fica **estritamente** mais perto do LPA divulgado em 107 (68%); nas 45 ações do mapa, em 24 de 26. As demais 98 não têm minoritários (os dois lucros coincidem) e não entram na comparação. O indício é favorável, não conclusivo; o fundamento é a definição do LPA, que pertence ao acionista controlador (CPC 41).

**O que separa as duas escalas.** As hipóteses (unidade ou milhar) dão razões que diferem por 1.000, então a escolha só é ambígua quando a razão na escala escolhida chega perto de 1/31,6 ou de 31,6 (a raiz de 1.000). Nos dados, a razão escolhida fica entre ≈ 0 e 19,9, e 250 de 255 empresas ficam em [0,1; 10]. O limiar de "escala indeterminada" do F2A-3 (por exemplo, abster-se fora de [0,5; 2], o que cortaria 17 de 255) **não foi determinado aqui**: é uma escolha do item, e a tabela acima é o insumo. A regra do script sempre escolhe uma das duas escalas; "31 de 45 determinadas" quer dizer que havia lucro positivo, LPA e ações para calcular, e não que a escolha foi testada contra um limiar.

**Consequência.**
- F2A-3: a escala não está no arquivo; a fila já manda inferi-la pelo LPA divulgado. Os insumos medidos: a linha 3.99 não deve passar pela `ESCALA_MOEDA`, o LPA de referência é o da espécie (3.99.01.01 ou .02), e o lucro dos controladores aproxima o LPA melhor que o consolidado. Em 14 das 45 ações do mapa a regra não tem como calcular (motivos acima), e em 54 empresas do universo a causa é a falta do LPA por espécie.
- F2A-5: o LPA divulgado é uma referência independente do mesmo documento.
- As armadilhas 3 (dual-class) e 10 (escala) se confirmam nos dados; a 11 (desdobramento) não foi medida aqui.

## 3. DFP e ITR (F2A-7, F2A-8)

**Passivo (DFP 2025, 439 empresas no consolidado; as contagens são de empresas com a conta e `VL_CONTA` diferente de zero).**
- Circulante: 2.01.04 Empréstimos e Financiamentos (391); 2.01.04.01 Empréstimos (331); 2.01.04.02 **Debêntures** (188); 2.01.04.03 **Financiamento por Arrendamento** (135).
- Não circulante: 2.02.01 (396); 2.02.01.01 (316), 2.02.01.02 Debêntures (194), 2.02.01.03 Arrendamento (135).
- **Instabilidade abaixo do 3º nível:** 2.01.04.03.01 "Passivo de arrendamento" só em 43 empresas, e 2.02.01.02.02 passa a ser "Passivos de Contratos de Resseguros" (modelo de seguradora). O 4º nível não é estável.
- **Arrendamento fora do grupo de empréstimos:** 194 empresas têm linha com "arrend" ou "leasing" e valor diferente de zero fora de 2.01.04 e 2.02.01, nas contas de Outras Obrigações (por exemplo 2.01.05.02.07, 2.02.02.02.03). O documento não mostra se é o mesmo valor já contado em 2.x.04.03 ou outro.

**Ativo.** 1.01.01 Caixa e Equivalentes (430 empresas) e 1.01.02 Aplicações Financeiras (271). Em 1.01.02 há 1.01.02.01 a .03 (valor justo no resultado, no outro resultado abrangente, custo amortizado).

**DVA.**
- 7.04.01 **Depreciação, Amortização e Exaustão** com valor em 410 empresas; a descrição é a mesma em 427 linhas e duas empresas usam "Outros" no código.
- 7.08.04.02 Dividendos com valor em 168 empresas e 7.08.04.01 Juros sobre o Capital Próprio em 79 (as demais têm a linha zerada).

**ITR 2026.**
- Datas de referência: 30/06 e 31/03 (mais 60 linhas de 31/05).
- No 1º trimestre (410 empresas), 407 têm dois `DT_INI_EXERC` distintos na conta 3.11: um do ÚLTIMO e um do PENÚLTIMO. No 2º trimestre (409 empresas), 403 têm quatro: o acumulado (`DT_INI_EXERC` em 01/01) e o trimestre (1º dia do trimestre), cada um para ÚLTIMO e PENÚLTIMO; 6 têm dois. O 3º trimestre **não foi observado**: o ITR 2026 só tem 31/03 e 30/06.
- A **Composição do Capital vem no ITR** (1.269 linhas, mesmas colunas da DFP, sem escala).

**Consequência.**
- F2A-8: os grupos 2.01.04 e 2.02.01 trazem empréstimos, debêntures e arrendamento no 3º nível, estáveis; o 4º nível não. Caixa e aplicações estão em 1.01.01 e 1.01.02. O fato a pesar: 194 empresas lançam arrendamento também em Outras Obrigações. Bancos e seguradoras usam outro modelo de contas (pergunta 4).
- F2A-7: no 2º trimestre o trimestre do ITR se separa pelo `DT_INI_EXERC` das linhas de cada `ORDEM_EXERC`, e a DVA 7.04.01 é a conta de D&A (410 empresas com valor).

## 4. Bancos e seguradoras (F2A-8, F2A-9)

**Setores** (`SETOR_ATIV` do cadastro): Bancos 115, Seguradoras e Corretoras 24, Emp. Adm. Part. - Intermediação Financeira 16, Intermediação Financeira 10, Emp. Adm. Part. - Seguradoras e Corretoras 6, Crédito Imobiliário 6, Emp. Adm. Part. - Crédito Imobiliário 5, Emp. Adm. Part. - Bancos 1.

**Bancos ativos com DFP 2025: 12.**
- PL consolidado: conta **2.07** em 9 e **2.08** em 3. Nenhum usa 2.03.
- Lucro dos controladores: **3.11.01** em 9 e **3.09.01** em 3.
- BBAS3 (2.07; 3.11 e 3.11.01), BBDC4 (2.07; 3.11 e 3.11.01) e ITUB4 (2.08; **3.09** e 3.09.01; não existe 3.11).
- Nos bancos, a conta 2.03 é "Provisões" (BBAS3, BBDC4) ou "Passivos Financeiros ao Custo Amortizado" (ITUB4).

A V1 (`cvm_provider._CONTAS`) lê o PL em `2.03` e o lucro em `3.11`. Nos bancos, o PL sai errado (provisões, ou o passivo financeiro) em **12 de 12**, e o lucro sai vazio no ITUB4.

**Consequência.**
- F2A-9: o código fixo não serve aos bancos. Nos 12 ativos, o PL está em 2.07 ou 2.08 e o lucro dos controladores em 3.11.01 ou 3.09.01; a descrição ("Patrimônio Líquido Consolidado", "Atribuído … Controladora") é o que se repete.
- F2A-8: nos bancos a conta 2.03 não é o patrimônio líquido e o passivo não tem os grupos 2.01.04 e 2.02.01 da empresa comum; a seguradora não foi medida.

## 5. IF.data (F2A-9)

**Chamada de controle:** `IfDataValores(AnoMes=202512, TipoInstituicao=1, Relatorio='1')` com `CodInst=C0080329` (Banco do Brasil, conglomerado prudencial) devolveu **10 linhas**: ativo total, PL, lucro líquido, carteira de crédito, patrimônio de referência, índice de imobilização e **índice de Basileia (0,1513)**.

**Relatórios (TipoInstituicao=1).**
- 202412: 1 a 6 (Resumo, Ativo, Passivo, Resultado, Informações de Capital, Segmentação).
- 202509 e 202512: também 7, 9 a 14 e 16 (carteira de crédito por indexador, região, clientes e operações, PF, PJ por CNAE, PJ por modalidade, PJ por porte, por carteira de instrumentos).
- **Capital (Basileia):** relatório **5**, colunas "Índice de Capital Principal", "Índice de Capital Nível I", "Índice de Basileia" e o patrimônio de referência.
- **Carteira por nível de risco: não encontrada.** Os relatórios 8, 15 e 17 a 30 não devolvem linhas nas três datas testadas (2024-12, 2025-09 e 2025-12); os nomes dos relatórios existentes (1 a 7, 9 a 14 e 16) não têm "risco" no título. **Não determinado** se ela existe com outro tipo de instituição ou outra data. Hipótese não verificada: a Resolução CMN 4.966 substituiu a classificação de risco AA–H pelas fases de perda esperada em 2025, e o relatório 16 (por carteiras de instrumentos) pode ser o sucessor; isso muda o que o F2A-9 deve pedir.

**Como achar a instituição.** `IfDataCadastro` traz `CnpjInstituicaoLider` (os 8 primeiros dígitos do CNPJ) e `CodInst`. Para o BB, o filtro devolve 8 linhas: o banco (`Td=I`) e os conglomerados (`Td=C`, "BB" e "BB - PRUDENCIAL"). Os relatórios de capital estão no `CodInst` do **conglomerado prudencial** (`C0080329`), e não no da instituição.

**Consequência.** F2A-9: o IF.data atende o capital (Basileia) a partir do CNPJ, em duas chamadas (cadastro e relatório 5). A carteira por nível de risco não tem relatório conhecido; o item que a pedir fica sem fonte até a existência dela ser confirmada.

## 6. COTAHIST (F2A-1, F2A-26)

**Download real:** `https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_M092026.ZIP` (HTTP 200, 10.052.445 bytes), arquivo `COTAHIST_M092026.TXT`. O layout de 245 posições do F2A-18 bateu com o arquivo real. Contagem de linhas: **366.221 registros 01**, 1 header (00) e 1 trailer (99).

**Mercado à vista (010), setembro:** 30.576 registros, 21 pregões, **1.993 códigos**. Por grupo (pelo `CODBDI` e `ESPECI`): BDRs 966, ações 377, FIIs 349, outros fundos 259, units 13, outros 29.

| Papel | `CODBDI` | `ESPECI` |
|---|---|---|
| Ações | 02 (lote padrão), 07, 08 | `ON`, `PN`, `PNA`, `PNB`... com sufixo de nível (`ON      NM`, `PN      N1`, `ON      N2`) |
| Units | 02 | `UNT`, `UNT     N1`, `UNT     N2` (13 códigos) |
| Cotas de FII | 12 | `CI`, `CI  ER`, `CI  ES`, `CI  EA`, `CI  ERA`... |
| Cotas de outros fundos (ETF, FIAGRO, etc.) | 14 e 13 | `CI`, `CI  ER`, `CI *` |
| BDRs | 34, 35, 36 | `DRN`, `DRE`, `DR1`, `DR2`, `DR3` (com sufixos `ED`, `EB`) |
| Direitos, recibos | 10, 22, 58 | `DIR ORD NM`, `BNS ORD NM`, `CPA...` |

ETFs conhecidos (BOVA11, IVVB11, SMAL11, GOLD11) estão no `CODBDI` 14 com `ESPECI` `CI`, igual aos demais fundos fora de FII.

**Dado oficial que separa ETF de outro fundo:** existe na CVM. No registro de classes (`registro_classe.csv`), `Tipo_Classe` = "Classes de Cotas de Fundos **FIIM**" (256 classes) reúne os fundos de índice (IT NOW, iShares). Os demais tipos: FIF 26.721, FIDC 5.381, FIP 2.518, FII 1.537, FIAGRO 377. **Mas** o COTAHIST traz o ISIN e o registro traz o CNPJ da classe, sem ISIN: a junção entre eles **não está determinada** aqui.

**Consequência.**
- F2A-1: o COTAHIST separa ação, unit, FII, BDR e outro fundo por `CODBDI` e `ESPECI`; o sufixo 11 sozinho não decide (armadilha 14). O ETF só se distingue de outro fundo listado com a segunda fonte e uma ponte de ISIN que não foi determinada.
- F2A-26: o mercado à vista tem volume, negócios e quantidade por código e dia.

## 7. Informe Mensal de FII (F2A-1, F2A-2)

**Colunas do `inf_mensal_fii_geral`:** `CNPJ_Fundo_Classe`, `Codigo_ISIN`, `Segmento_Atuacao`, `Mercado_Negociacao_Bolsa` (S/N), `Mercado_Negociacao_MBO`, `Mercado_Negociacao_MB`, `Entidade_Administradora_BVMF`, `Tipo_Fundo_Classe`, `Mandato`, `Tipo_Gestao`, entre outras.

**Cobertura.** 1.399 fundos no informe (710 com negociação em bolsa). Segmentos: Multicategoria 662, Outros 360, Logística 103, Residencial 87, Escritórios 72, Shoppings 70, Hospital 19, Varejo 12, Hotel 11, Educacional 2; 1 vazio.

**Junção pelo ISIN do COTAHIST:** dos **382** FIIs negociados à vista em jul–set/2026, **318 casam (83,2%)** com o informe pelo ISIN e **64 não casam** (por exemplo AFHF11, APXU11, AQPA11, BLUE11, DAYM11).

**Regra do ISIN (reserva):** ticker = posições 3 a 6 do ISIN + `11`. Nos 382 FIIs do COTAHIST, as quatro letras concordam em 382 (o script calcula as duas contagens); com o sufixo `11`, em **376** (os outros 6 têm outro sufixo, como 12 ou 13). A conferência só pôde ser feita onde o ticker já é conhecido; nos 64 sem informe a regra não foi testada contra uma fonte independente.

**Mapa manual de FIIs (30):** 27 têm o CNPJ no informe e 25 negociaram no trimestre. Fora dos listados em bolsa no período: **BCFF11, CVBI11, IRDM11, MALL11 e RBRF11**; desses, **BCFF11, IRDM11 e RBRF11** nem aparecem no informe pelo CNPJ do mapa. Os três sem CNPJ no informe são os que ficaram fora dos 27 que o dossiê (seção 7) conferiu pela regra do ISIN.

**Consequência.**
- F2A-1: o ISIN é a chave FII ↔ informe, com 83% de cobertura direta; os 17% restantes (64 fundos) não têm CNPJ nem segmento por essa via. A regra do ISIN dá o ticker, não o CNPJ.
- F2A-2: o segmento sai de `Segmento_Atuacao` (10 valores, dos quais "Multicategoria" e "Outros" são 73% dos fundos do informe).

## 8. Representação do DY e do ROE (F2A-4, F2A-30)

**yfinance 0.2.66**, em 10 tickers públicos:
- `dividendYield` vem em **percentual** (PETR4: 6,74). Os proventos dos últimos 12 meses ÷ preço dão 0,0674. Em PETR4, KLBN11, SUZB3 e RENT3 o percentual bate com o cálculo (diferença abaixo de 0,2 ponto); em WEGE3 (3,02 contra 3,91%) e ABEV3 (4,58 contra 5,30%) ele fica abaixo.
- **Diverge** em ITUB4 (1,82 contra 6,31%), BBAS3 (0,57 contra 2,71%) e BBDC4 (1,04 contra 5,72%): o yfinance devolve outro número. VALE3 (6,35 contra 8,16%) diverge menos.
- `trailingAnnualDividendYield` vem em **fração** (0,0681 em PETR4) e fica mais perto do cálculo nos bancos (ITUB4 0,0586 contra 0,0631).
- `returnOnEquity` do yfinance contra lucro consolidado ÷ PL consolidado da DFP 2025 (não é o ROE dos controladores, e o PL é o do fim do exercício, sem média, o que também explica parte das diferenças em KLBN11 e SUZB3): ITUB4 0,215 contra 0,213, BBDC4 0,138 contra 0,134 e ABEV3 0,184 contra 0,180 (diferença de até 1 ponto); PETR4 0,303 contra 0,265, VALE3 0,041 contra 0,063 e BBAS3 0,105 contra 0,087; e **KLBN11 0,037 contra 0,117, SUZB3 0,176 contra 0,306, WEGE3 0,308 contra 0,365 e RENT3 0,130 contra 0,073** (mais de 5 pontos). Três de dez concordam; quatro divergem muito.

**brapi:** **não determinado.** A documentação pública é renderizada por JavaScript e o HTML não traz os campos; a chamada sem token devolve só a cotação, sem os campos fundamentalistas. A leitura do código (`brapi_provider._percent_to_decimal`) assume que o valor pode vir em fração ou em percentual.

**Informe Mensal.** `Percentual_Dividend_Yield_Mes` é o rendimento do mês em %. Só registro.

**Consequência.**
- F2A-4: na versão instalada o `dividendYield` do yfinance é percentual, e a regra `>1` de `_normalizar_dy` o lê como tal; em bancos o número divergiu do cálculo por proventos. Um valor percentual abaixo de 1 (BBAS3: 0,57) seria lido como fração e rejeitado pela regra `>0,25`. A escolha da fonte do DY é do item.
- F2A-30: o ROE do yfinance diverge em mais de 5 pontos do lucro ÷ PL da CVM em 4 de 10 tickers (e o cálculo aqui usa o consolidado, não os controladores).

## 9. Liquidez (insumo da [LIQUIDEZ])

Mercado à vista, 65 pregões (jul–set/2026), último pregão 30/9. Volume financeiro e negócios por dia, somados por código; dia sem negócio conta zero; presença = dias com negócio ÷ pregões da janela. Só entram ativos com ao menos um negócio na janela.

| Grupo | Janela | Ativos | Mediana do volume mediano (R$/dia) | Mediana de negócios/dia |
|---|---|---|---|---|
| Ações | 21 | 377 | 837.319 | 362 |
| Ações | 63 | 390 | 569.904 | 284 |
| Units | 21 | 13 | 42.756.045 | 5.654 |
| Units | 63 | 13 | 36.230.619 | 4.771 |
| FIIs | 21 | 349 | 31.695 | 45 |
| FIIs | 63 | 382 | 17.059 | 28,5 |

**Ativos abaixo do volume diário mediano** (janela de 63 pregões; entre parênteses, a de 21):

| Grupo | < R$ 100 mil | < R$ 500 mil | < R$ 1 milhão | < R$ 5 milhões |
|---|---|---|---|---|
| Ações (390) | 157 (145) | 190 (180) | 203 (191) | 252 (231) |
| Units (13) | 4 (4) | 4 (4) | 4 (4) | 5 (5) |
| FIIs (382) | 241 (209) | 303 (273) | 323 (292) | 368 (331) |

**Ativos abaixo da presença** (63 pregões; 21 entre parênteses):

| Grupo | < 80% | < 90% | < 95% |
|---|---|---|---|
| Ações | 87 (74) | 98 (78) | 105 (82) |
| Units | 2 (2) | 3 (2) | 3 (2) |
| FIIs | 133 (96) | 140 (105) | 150 (114) |

**Consequência.** O universo listado é dominado por papéis pouco líquidos: com o piso de R$ 1 milhão por dia, ficam de fora 203 de 390 ações e 323 de 382 FIIs. Isso informa a [LIQUIDEZ] (F2B), mas não a decide; o F2A-26 só mede.

## Limites deste levantamento

- Os números de setembro/2026 (COTAHIST) e de 2025 (DFP) mudam a cada mês e a cada exercício; o script os refaz.
- A pergunta 2 usa o mapa regenerado de 45 ações, não a amostra de 38 do dossiê, que não é reconstituível (a tabela do dossiê só lista as 10 maiores divergências).
- O IF.data foi testado só com o Banco do Brasil e só no tipo de instituição 1.
- Não foi medido o item 11 das armadilhas (desdobramento entre demonstração e preço).
- O F2A-2 depende da espécie de controle acionário "do cadastro ou do FCA", e nenhuma das nove perguntas a trata. `Especie_Controle_Acionario` existe no `fca_cia_aberta_geral` (coluna lida de passagem), mas seus valores e cobertura não foram medidos; o F2A-2 parte daí.
- A contagem por empresa na pergunta 3 é por conta com valor diferente de zero na DFP 2025; empresa sem a linha ou com linha zerada não entra.
