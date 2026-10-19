# Lente de bancos (P/VP justificado) — versão 0.1

**Status:** rascunho (19/10/2026, escrito pelo loop no F2B-26). O loop nunca marca ficha como aprovada; a aprovação, depois da auditoria externa em modo FICHA (D30), é do Marcos no marcador "Fichas da 2B, taxa e fontes".
**Itens que dependem:** F2B-3 (o método, `sentinela/methods/bancos.py`), F2B-32 (a ligação no motor), F2B-4 (escopo: os métodos de empresa se abstêm em banco).
**Decisões de origem:** checkpoint da Fase 0, seção 4, item 5 (lente própria com P/VP justificado pelo ROE; Basileia e inadimplência opcionais, com a limitação declarada); ADR-0003, D22 ("a lente de bancos tem derivação explícita na ficha") e D21 a D23; armadilha 17.
**Depende de:** `docs/metodologia/taxa-real.md` (F2B-22), para k real e a inflação; `docs/metodologia/gordon.md` (F2B-23), para a definição do g real; `docs/metodologia/por-acao.md`, para o VPA.
**Levantamento:** `docs/decisoes/fontes-fase2b.md` (F2B-21), pergunta 5.

Esta ficha apresenta definições, dados e opções. Nenhum parâmetro é decidido pelo texto: os da seção 7 estão marcados **[DECISÃO]**.

## 1. Fórmula e referência

**P/VP justificado = (ROE − g) ÷ (k − g); valor = P/VP justificado × VPA.**

**Derivação.** Com crescimento estável g e o ROE medido sobre o patrimônio do **começo** do período (ROE = lucro1 ÷ VPA0, a convenção da referência), o lucro do próximo ano é ROE × VPA0; o dividendo é D1 = ROE × VPA0 × (1 − b), com b a retenção; e o patrimônio cresce pelo lucro retido, g = ROE × b (crescimento fundamental). O Gordon dá P0 = D1 ÷ (k − g) = VPA0 × (ROE − ROE × b) ÷ (k − g) = VPA0 × (ROE − g) ÷ (k − g), e **P0 ÷ VPA0 = (ROE − g) ÷ (k − g)**. Com o ROE do último exercício (lucro0 ÷ VPA0, lucro e patrimônio da mesma data), a forma equivalente é P0 ÷ VPA0 = ROE × (1 − b) × (1 + g) ÷ (k − g); as duas coincidem só pela hipótese de ROE constante (seção 4 e ponto 7.6). Referência: Damodaran, *Investment Valuation*, 3ª ed., Wiley, 2012, cap. 18, "Book Value Multiples" (P/VP justificado de empresa em crescimento estável) e cap. 21 (instituições financeiras); capítulos citados de memória, a conferir.

**Regime e equivalência.** As três taxas (ROE, g e k) têm de estar no mesmo regime, convertidas pela mesma inflação π. O ROE contábil é **nominal**; no regime real, ROE real = (1 + ROE) ÷ (1 + π) − 1. Prova: com k_N = (1 + k)(1 + π) − 1, g_N = (1 + g)(1 + π) − 1 e ROE_N = (1 + ROE_r)(1 + π) − 1:
- ROE_N − g_N = (1 + π)(ROE_r − g) e k_N − g_N = (1 + π)(k − g);
- logo (ROE_N − g_N) ÷ (k_N − g_N) = (ROE_r − g) ÷ (k − g): **o mesmo P/VP nos dois regimes**.

Convertendo só k e g, e deixando o ROE nominal, os regimes divergem: no exemplo da seção 5, 1,92 contra 1,45. A conversão do ROE e a definição de g seguem a decisão do g real da [TAXA], a mesma do Gordon (ficha do F2B-23, 7.1). O teste `::test_real_e_nominal_dao_o_mesmo_pvp` do F2B-3 compara duas contas independentes (a real e a nominal), não a fórmula consigo mesma.

## 2. Insumos

| Insumo | Definição exata | Fonte | Unidade e escala | Data de referência |
|---|---|---|---|---|
| ROE | lucro ÷ PL dos controladores, pelo modelo de instituição financeira (F2A-9; contas 3.09.01 ou 3.11.01, e 2.07 ou 2.08 menos 2.07.02 ou 2.08.09, pela tabela `contas_cvm.csv`) | DFP/ITR da CVM pela cascata | razão, nominal | `DT_REFER` |
| VPA | PL dos controladores ÷ ações do mesmo documento (F2A-36; ficha por ação 1.1) | DFP/ITR da CVM | R$ por ação | `DT_REFER` |
| Payout | dividendos e JCP do exercício na DVA ÷ lucro dos controladores (F2A-7), ou o DY da cascata × preço ÷ LPA (opção 7.2) | DVA da CVM; cascata | razão | `DT_REFER` |
| k real | NTN-B + prêmio | ficha da taxa real | razão, real | data-base |
| Inflação | a da conversão | ficha da taxa real | razão | a da série |
| Basileia | índice de Basileia do conglomerado prudencial | IF.data (BCB), relatório 5 (F2A-9) | razão | última data-base do IF.data |
| Inadimplência | candidata: "carteira ativa inadimplida arrastada" ÷ total, relatório 16 do IF.data (F2B-21, pergunta 5; conceito a conferir) | IF.data | razão | data-base do IF.data |

## 3. Regime, janela e data

- **Regime real** (D22), com a conversão das três taxas pela mesma inflação (seção 1).
- **Janela:** o último documento (ROE e VPA do exercício; o TTM é do F2C-1).
- **Datas:** a Basileia é a da última data-base do IF.data, e o balanço é o da DFP; podem diferir (diário do F2A-9): ficam declaradas na proveniência. O `divida_pl` não entra (diário do F2A-9).

## 4. Hipóteses e inaplicabilidade

Abstenções (textos propostos):
- "ROE não maior que g" (ROE ≤ g): o P/VP justificado seria zero ou negativo, sem sentido econômico (o banco destrói valor com o crescimento);
- "k não maior que g" (k ≤ g): sem valor finito;
- "VPA ausente ou não positivo";
- "insumo ausente: taxa real" e "insumo ausente: inflação", sem contingência.

Limitação de sensibilidade: com k − g pequeno, o P/VP cresce sem limite antes de chegar à abstenção (BMEB4, ROE de 27%: com prêmio de 7% e g = ROE × retenção, P/VP de 50,7; F2B-21, pergunta 5); o que contém esse caso é um teto para g ou um piso para k − g (ponto 7.1).

Limitações: banco fora do índice oficial é lido como empresa (diário do F2A-9); holdings de banco ("Emp. Adm. Part. - Bancos") seguem a [FINANCEIRAS]. Hipótese: o ROE do último exercício representa o de longo prazo (ROE constante), o que torna o lucro0 ÷ VPA0 do documento igual ao lucro1 ÷ VPA0 da fórmula.

**Qualidade, fora do valor** (checkpoint, item 5): a Basileia e a inadimplência são exibidas, sem entrar no P/VP justificado.

## 5. Exemplo calculado de forma independente

**ITUB4 (Itaú Unibanco Holding S.A., CNPJ 60.872.504/0001-23)**, conta à mão, sem o código do projeto:

- **DFP 2025** (CVM, `dfp_cia_aberta_2025.zip`, `DT_REFER` 2025-12-31, `VERSAO` 2, escala MIL):
  - DRE consolidada: 3.09.01 "Atribuído a Sócios da Empresa Controladora" = 44.857.000 mil; 3.99.01.01 ON e 3.99.01.02 PN = 4,05;
  - BPP consolidado: 2.08 "Patrimônio Líquido Consolidado" = 215.076.000 mil; 2.08.09 "Participação dos Acionistas Não Controladores" = 10.575.000 mil; PL dos controladores = 204.501.000 mil;
  - DVA consolidada: 7.09.04.02 "Dividendos" = 33.704.000 mil; 7.09.04.01 "Juros sobre o Capital Próprio" = 0 (conferido no arquivo, versão 2);
  - Composição do Capital: 5.617.743 ON + 5.409.126 PN − 345 em tesouraria = 11.026.524 mil ações.
- **Preço:** COTAHIST de setembro de 2026 (`COTAHIST_M092026.ZIP`), último pregão do arquivo, 25/09/2026 (não o último dia útil do mês), ITUB4, mercado à vista: **R$ 42,13**. Só entra no P/VP de mercado, para comparação: o P/VP justificado não usa o preço.
- **Taxa:** k real = 6,8818% + 5% = **11,8818%** (NTN-B de 15/10/2026; ficha da taxa real); π = **4,4009%** (Focus 12 meses, 09/10/2026). As datas não coincidem: balanço de 31/12/2025, preço de 25/09/2026, NTN-B de 15/10/2026 e Focus de 09/10/2026; num cálculo de produção, todas ficam na proveniência.

Conta:
1. ROE = 44.857.000 ÷ 204.501.000 = **21,9349%** (nominal; lucro e PL de 2025, a mesma data, lido como lucro1 ÷ VPA0 pela hipótese de ROE constante); ROE real = 1,219349 ÷ 1,044009 − 1 = **16,7949%**.
2. VPA = 204.501.000 ÷ 11.026.524 = **R$ 18,5463**; P/VP de mercado = 42,13 ÷ 18,5463 = 2,2716.
3. payout (DVA) = 33.704.000 ÷ 44.857.000 = **75,1365%**; retenção b = **24,8635%**.
4. g real, definição (i) da ficha do Gordon: (1 + 0,219349 × 0,248635) ÷ 1,044009 − 1 = **1,0085%**.
5. P/VP justificado (real) = (0,167949 − 0,010085) ÷ (0,118818 − 0,010085) = **1,4518**; valor = 1,4518 × 18,5463 = **R$ 26,93**.
6. Conferência nominal: k_N = 16,8056%, g_N = (1,010085 × 1,044009) − 1 = 5,4537%; (0,219349 − 0,054537) ÷ (0,168056 − 0,054537) = **1,4518**, igual.
7. Só k e g convertidos, ROE nominal (o erro que a ficha evita): (0,219349 − 0,010085) ÷ (0,118818 − 0,010085) = **1,9246**.

O F2B-3 transforma este exemplo em teste (D28), com a definição de g que o Marcos escolher.

## 6. Sensibilidade

ITUB4, P/VP justificado (real = nominal, com as três taxas convertidas) por prêmio e definição de g (π = 4,4009%, NTN-B de 6,8818%). Nas colunas "inflação + x", o g nominal é π + x e o g real, (1 + π + x) ÷ (1 + π) − 1 (0; 0,9578%; 1,9157%):

| Prêmio | (i) | (ii) | inflação + 0 | inflação + 1 ponto | inflação + 2 pontos |
|---|---|---|---|---|---|
| 4% | 1,60 | 1,88 | 1,54 | 1,60 | 1,66 |
| 5% | 1,45 | 1,64 | 1,41 | 1,45 | 1,49 |
| 7% | 1,23 | 1,30 | 1,21 | 1,23 | 1,24 |

P/VP de mercado: 2,27 (preço de 25/09/2026; o levantamento traz 2,38, pelo preço do retrato do yfinance). Na pergunta 5 do F2B-21, com NTN-B de 6,88% e prêmio de 5% (g = ROE × retenção convertido / g = inflação + 1 ponto): BBAS3 0,22 / 0,16, BBDC4 0,70 / 0,69, ITUB4 1,45 / 1,45; a fórmula degenera quando ROE ≈ k (BMEB4: sem valor, k ≤ g, com prêmio de 5%; 50,7 com 7%) e com payout zero (BMGB4: g = ROE e P/VP zero pela definição ROE × b).

## 7. Parâmetros e justificativa

### 7.1 Definição de g — [DECISÃO]
ROE × retenção, convertido pela definição do g real da ficha do Gordon (7.1: (i), (ii) ou (iii)), ou inflação + x pontos. A mesma escolha do Gordon (F2B-23). O teto da (iii), ou um piso para k − g, é o que contém a singularidade perto de k = g (seção 4, BMEB4); sem ele, só a abstenção em k ≤ g.

### 7.2 Payout — [DECISÃO]
Pela DVA (F2A-7, dividendos e JCP do exercício ÷ lucro dos controladores) ou pelo DY da cascata × preço ÷ LPA. Nos bancos, o DY do yfinance diverge do declarado (F2A-16, pergunta 8).

### 7.3 VPA — [DECISÃO]
Só o da CVM (banco sem VPA se abstém; hoje PINE4 e SANB11, F2B-21) ou o de outras fontes como reserva.

### 7.4 Basileia — [DECISÃO]
Só exibida, ou alerta abaixo do mínimo regulatório, com a norma citada.

### 7.5 Inadimplência — [DECISÃO]
Pela candidata do relatório 16 do IF.data (F2B-21, pergunta 5; o conceito e o denominador a conferir), ou a limitação declarada.

### 7.6 ROE da fórmula — [DECISÃO]
O do último exercício (lucro ÷ PL do fim do período, a mesma data) lido como lucro1 ÷ VPA0, pela hipótese de ROE constante; o lucro sobre o PL do começo do exercício; ou sobre o PL médio. Muda o número: no ITUB4, o PL dos controladores de 31/12/2024 (DFP 2025, coluna do exercício anterior: 221.284.000 − 10.194.000 = 211.090.000 mil) é maior que o de 31/12/2025, e o ROE cai de 21,9349% (PL do fim) para 21,2502% (do começo) ou 21,5871% (médio).

### 7.7 Holdings de banco
Fora desta fila; se o Marcos as quiser na 2B, item novo, com ficha própria ([BANCOS]).
