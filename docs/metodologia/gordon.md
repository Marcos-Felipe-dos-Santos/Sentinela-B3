# Gordon no regime real — versão 0.1

**Status:** rascunho (19/10/2026, escrito pelo loop no F2B-23). O loop nunca marca ficha como aprovada; a aprovação, depois da auditoria externa em modo FICHA (D30), é do Marcos no marcador "Fichas da 2B, taxa e fontes".
**Itens que dependem:** F2B-1 (Gordon no regime real), F2B-29 (insumos reais no contrato); a definição do g real vale também para a lente de bancos (ficha do F2B-26; F2B-3 e F2B-32).
**Decisões de origem:** checkpoint da Fase 0, seção 4, itens 2 (taxa real) e 4 (janela do Gordon: dividendo dos últimos 12 meses); ADR-0002, D15; ADR-0003, D21 a D23; auditoria externa da 2A, correção 1 (o g real não pode ser decidido pelo texto).
**Depende de:** `docs/metodologia/taxa-real.md` (F2B-22), para k real e a inflação da conversão.
**Levantamento:** `docs/decisoes/fontes-fase2b.md` (F2B-21), pergunta 3.

Esta ficha apresenta definições, dados e opções. Nenhum parâmetro é decidido pelo texto: os da seção 7 estão marcados **[DECISÃO]**.

## 1. Fórmula e referência

**Valor = D1 ÷ (k − g)**, com D1 = D0 × (1 + g), no **regime real**: k é o custo do capital próprio real (ficha da taxa real) e g é o crescimento real dos dividendos.

- **Referência:** o modelo de crescimento de Gordon (Gordon, M. J., *The Investment, Financing, and Valuation of the Corporation*, Irwin, 1962; e Gordon e Shapiro, "Capital Equipment Analysis: The Required Rate of Profit", *Management Science*, 1956), na forma do modelo de desconto de dividendos com crescimento estável de Damodaran (*Investment Valuation*, 3ª ed., Wiley, 2012, cap. 13, "Dividend Discount Models"), com g = ROE × taxa de retenção como crescimento fundamental. Capítulos citados de memória, a conferir.
- **V1 (Gordon 1.1.0, `sentinela/methods/gordon.py`):** D0 = DY × preço; payout = min(DY × preço ÷ LPA, `GORDON_PAYOUT_MAX` = 95%); g = ROE × (1 − payout), limitado a `GORDON_G_MAX` = 8%; k = Selic + `GORDON_PREMIO_RISCO` = 7%; tudo **nominal**.
- **O que muda:** k passa a ser o real (NTN-B + prêmio); g passa a ser real, por uma das três definições da seção 7.1. O resto da forma (D0, payout, D1 e as guardas) fica.

## 2. Insumos

| Insumo | Definição exata | Fonte | Unidade e escala | Data de referência |
|---|---|---|---|---|
| Preço | fechamento bruto do pregão | cascata (yfinance, D-1); no exemplo, o COTAHIST da B3 | R$ por ação | pregão de referência |
| DY | dividendos e JCP de 12 meses ÷ preço | cascata (yfinance e brapi, pela fronteira de `sentinela/data/normalizacao.py`); a janela de 12 meses do checkpoint (item 4) pela série oficial é do F2C-1 e fica declarada como limitação | razão | a do provedor |
| LPA | o LPA dos métodos (D19: divulgado da classe do ticker; ficha por ação 1.1) | DFP/ITR da CVM pela cascata | R$ por ação | `DT_REFER` do documento |
| ROE | lucro ÷ PL dos controladores (D20; ficha por ação 1.1) | DFP/ITR da CVM pela cascata | razão, **nominal** (contábil) | `DT_REFER` |
| k real | NTN-B do vértice + prêmio | ficha da taxa real | razão, real | data-base da NTN-B |
| Inflação | a da conversão | ficha da taxa real | razão | a da série |

## 3. Regime, janela e data

- **Regime real** (checkpoint, item 2; D22). O ROE contábil e o g = ROE × retenção são **nominais**; para entrar no regime real precisam de conversão, e a forma da conversão é a decisão 7.1. Misturar k real com g nominal é a armadilha 1: no exemplo da seção 5 dá R$ 11,05 contra R$ 6,35 (1,74 vez); no universo inicial, de 1,5 a 3,3 vezes o valor nominal, que por Fisher é igual ao real (F2B-21, pergunta 3).
- **Equivalência:** com k e g convertidos pela mesma inflação (Fisher), o valor é o mesmo no regime real e no nominal (seção 5).
- **Janela:** D0 é o dividendo de 12 meses (DY × preço); o lucro e o PL são os do último documento.
- **Data:** proveniência de cada insumo (D16), inclusive a data-base da NTN-B e a da inflação.

## 4. Hipóteses e inaplicabilidade

Abstenções da 1.1.0, que ficam (textos de `gordon.py`): "DY não confiável"; "DY abaixo do mínimo" (DY ≤ `GORDON_DY_MIN` = 4%); "ROE abaixo do mínimo" (ROE ≤ `GORDON_ROE_MIN` = 10%); "LPA não positivo"; "k não maior que g"; "resultado não finito".

Novas:
- **taxa real indisponível** (NTN-B sem dado dentro da defasagem; ficha da taxa real, seção 4): "insumo ausente: taxa real"; sem contingência;
- **inflação indisponível** (as três definições de g a usam): "insumo ausente: inflação da conversão".

Hipóteses: crescimento estável e perpétuo; o payout de 12 meses representa o de longo prazo; o ROE do último documento representa o retorno sobre o lucro retido.

## 5. Exemplo calculado de forma independente

**ABEV3 (Ambev S.A., CNPJ 07.526.557/0001-00)**, com os valores dos arquivos oficiais, conta à mão (sem o código do projeto):

- **DFP 2025** (CVM, `dfp_cia_aberta_2025.zip`, `DT_REFER` 2025-12-31, `VERSAO` 1, escala MIL):
  - DRE consolidada: 3.11.01 "Atribuído a Sócios da Empresa Controladora" = 15.503.400 mil; 3.99.01.01 "ON" (LPA básico) = **0,9926913764**;
  - BPP consolidado: 2.03 = 88.774.781 mil; 2.03.09 (não controladores) = 860.742 mil; PL dos controladores = 87.914.039 mil;
  - DVA consolidada: 7.08.04.02 "Dividendos" = 10.903.280 mil; 7.08.04.01 "Juros sobre o Capital Próprio" = 0 (conferido no arquivo: a linha existe e está zerada na versão 1);
  - Composição do Capital: 15.761.639 ON − 145.113 em tesouraria = 15.616.526 (mil ações; a escala confere com o LPA: 15.503.400 ÷ 15.616.526 = 0,99276, contra 0,99269 divulgado).
- **Preço:** COTAHIST de setembro de 2026 (`COTAHIST_M092026.ZIP`, SHA-256 `f164e177…85b1c`), último pregão do arquivo, 25/09/2026, ABEV3, mercado à vista: **R$ 15,32**.
- **Taxa:** NTN-B, média das IPCA+ de 2035 em diante, venda, 15/10/2026: 6,8818% (ficha da taxa real, seção 5); prêmio de 5%: **k real = 11,8818%**. Inflação, Focus 12 meses de 09/10/2026: **π = 4,4009%**.

Conta:
1. D0 = 10.903.280 ÷ 15.616.526 = **R$ 0,698189** por ação; DY = 0,698189 ÷ 15,32 = **4,5574%** (o exemplo usa os dividendos do exercício na DVA no lugar do DY da cascata).
2. ROE = 15.503.400 ÷ 87.914.039 = **17,6347%** (nominal).
3. payout = DY × preço ÷ LPA = 0,698189 ÷ 0,9926914 = **70,3329%**; retenção b = **29,6671%**.
4. g nominal = ROE × b = **5,2317%** (abaixo do teto de 8% da V1).
5. Por definição de g real (seção 7.1):
   - (i) g = (1 + 0,052317) ÷ 1,044009 − 1 = **0,7958%**; D1 = 0,698189 × 1,007958 = 0,703745; valor = 0,703745 ÷ (0,118818 − 0,007958) = **R$ 6,35**;
   - (ii) ROE real = 1,176347 ÷ 1,044009 − 1 = 12,6760%; g = 0,126760 × 0,296671 = **3,7606%**; valor = 0,698189 × 1,037606 ÷ (0,118818 − 0,037606) = **R$ 8,92**;
   - (iii) com teto de 2% real (número de teste, não proposta): sobre a (i), o g (0,7958%) já está abaixo do teto, valor = **R$ 6,35**; sobre a (ii), o teto age: g = 2%, valor = 0,698189 × 1,02 ÷ (0,118818 − 0,02) = **R$ 7,21**.
6. **Conferência de regime:** k nominal = 1,118818 × 1,044009 − 1 = 16,8056%; g nominal pela (i) = 5,2317%; valor nominal = 0,698189 × 1,052317 ÷ (0,168056 − 0,052317) = **R$ 6,35**, igual ao real.
7. **Misto (armadilha 1, controle):** k real com g nominal: 0,698189 × 1,052317 ÷ (0,118818 − 0,052317) = **R$ 11,05**.
8. **V1** (Selic 14,75%, k = 21,75%, g = 5,2317%): 0,698189 × 1,052317 ÷ (0,2175 − 0,052317) = **R$ 4,45**.

O F2B-1 transforma este exemplo em teste (D28), com a definição de g que o Marcos escolher.

## 6. Sensibilidade

ABEV3, valor (R$) por prêmio, inflação e definição de g, NTN-B de 6,8818%:

| Prêmio | Inflação | (i) | (ii) | (i) com teto 2% | (ii) com teto 2% | Misto |
|---|---|---|---|---|---|---|
| 4% | 3,50% (Focus 2030) | 7,71 | 10,64 | 7,71 | 8,02 | 13,00 |
| 4% | 4,40% (Focus 12 meses) | 6,98 | 10,17 | 6,98 | 8,02 | 13,00 |
| 4% | 4,58% (IPCA 12 meses) | 6,85 | 10,09 | 6,85 | 8,02 | 13,00 |
| 5% | 3,50% | 6,95 | 9,28 | 6,95 | 7,21 | 11,05 |
| 5% | 4,40% | 6,35 | 8,92 | 6,35 | 7,21 | 11,05 |
| 5% | 4,58% | 6,24 | 8,85 | 6,24 | 7,21 | 11,05 |
| 7% | 3,50% | 5,81 | 7,39 | 5,81 | 5,99 | 8,49 |
| 7% | 4,40% | 5,38 | 7,16 | 5,38 | 5,99 | 8,49 |
| 7% | 4,58% | 5,30 | 7,11 | 5,30 | 5,99 | 8,49 |

Preço de referência: R$ 15,32; V1: R$ 4,45. Na ABEV3, o teto de 2% só age sobre a (ii): o g da (i) fica abaixo dele em todas as linhas (no máximo 1,67%).

No universo inicial (F2B-21, pergunta 3; mediana do upside, 15 a 17 ações): (i) de −8,7% a −35,2%; (ii) de +27,1% a −13,7%; (iii) de −17,4% a −39,7%, nas três inflações e nos três prêmios; a (iii) do levantamento é só a (i) com teto de 2%. A (i), a (ii) e o misto do levantamento foram medidos **sem** o teto de 8% da V1.

**Viés da (ii):** g(ii) − g(i) = π(1 − b) ÷ (1 + π). A (ii) supera a (i) por construção sempre que há inflação e payout: supõe que o patrimônio existente acompanha a inflação sem retenção, e só a retenção gera crescimento real; a (i) supõe que o crescimento nominal ROE × b já é todo o crescimento dos dividendos, e que ele é corroído pela inflação. No exemplo, π(1 − b) ÷ (1 + π) = 0,044009 × 0,703329 ÷ 1,044009 = 2,9648 pontos, a diferença entre 3,7606% e 0,7958%.

## 7. Parâmetros e justificativa

### 7.1 Definição do g real — [DECISÃO]
Opções (auditoria externa da 2A, correção 1; [TAXA]):
- **(i)** g real = (1 + ROE × b) ÷ (1 + π) − 1: o crescimento nominal fundamental convertido por Fisher; dividendos crescem menos que a inflação sempre que ROE × b < π. ABEV3: R$ 6,35.
- **(ii)** g real = ROE real × b, com ROE real = (1 + ROE) ÷ (1 + π) − 1: só a retenção gera crescimento real, e o patrimônio é preservado em termos reais. ABEV3: R$ 8,92.
- **(iii)** a (i) ou a (ii) com teto de crescimento real de longo prazo, com a fonte do teto (por exemplo, o crescimento real de longo prazo do PIB; fonte não levantada no F2B-21). ABEV3: igual à (i) com teto de 2%.

A mesma escolha vale para a lente de bancos (ficha do F2B-26).

### 7.2 Teto de g no regime real — [DECISÃO]
Hoje 8% **nominal** (`GORDON_G_MAX`, `config.py`). Opções: um teto real (por exemplo, o da (iii)), o teto nominal convertido por Fisher, ou nenhum. Mudar a constante muda as ids do golden que a usam: o item declara o `--par` de cada id renomeada.

### 7.3 DY e ROE mínimos — [DECISÃO]
Hoje `GORDON_DY_MIN` = 4% e `GORDON_ROE_MIN` = 10%, ambos sobre números nominais. Opções: manter, ou expressar o ROE mínimo em termos reais. Mudar uma delas muda ids do golden (o item declara o `--par`).

### 7.4 Payout máximo — [DECISÃO]
Hoje `GORDON_PAYOUT_MAX` = 95%. Opções: manter, ou derivar do teto de g. Com payout de 95%, a retenção mínima é 5%.

### 7.5 Dividendo de base — [DECISÃO]
Opções: o DY da cascata × preço (a V1), ou os dividendos e JCP do último exercício na DVA ÷ ações (o exemplo), até a série oficial de 12 meses do F2C-1. ABEV3: DY de 5,49% pelo retrato público do yfinance do F2B-21 (proventos com data ex de 01/10/2025 a 30/09/2026 sobre o preço do retrato; `outputs/levantamento_cache/f2b21/retratos_publicos.json`, fora do git) contra 4,56% pela DVA de 2025.
