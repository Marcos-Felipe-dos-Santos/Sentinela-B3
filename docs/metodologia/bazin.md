# Taxa do Bazin — versão 0.1

**Status:** rascunho (19/10/2026, escrito pelo loop no F2B-24). O loop nunca marca ficha como aprovada; a aprovação, depois da auditoria externa em modo FICHA (D30), é do Marcos no marcador "Fichas da 2B, taxa e fontes".
**Itens que dependem:** F2B-31 (se a [BAZIN] ficar em (b) ou (c)); F2B-5 (a `selic` sai do contrato só se nenhum método a exigir); F2C-5 (lentes, na opção (d)).
**Achado de origem:** F-5 da auditoria red team (`docs/auditoria/2026-09-red-team.md`); armadilha 5 (colapso metodológico).
**Decisões de origem:** checkpoint da Fase 0, seção 4, itens 2 e 4 (janela do Bazin: dividendos médios de 5 anos); ADR-0003, D21 a D23.
**Depende de:** `docs/metodologia/taxa-real.md` (F2B-22), na opção (c).
**Levantamento:** `docs/decisoes/fontes-fase2b.md` (F2B-21), pergunta 3.

Esta ficha apresenta as quatro opções da [BAZIN], cada uma com a fórmula, o regime, a referência e o efeito. Nenhuma é escolhida pelo texto.

## 1. Fórmula e referência

**Forma comum:** preço justo = D ÷ taxa, com D o dividendo por ação de referência (D = DY × preço).

- **Referência:** Décio Bazin, *Faça Fortuna com Ações, Antes que seja Tarde* (1992): o preço teto é o que garante dividendo de pelo menos 6% ao ano sobre o preço pago (capítulo citado de memória, a conferir). É um rendimento mínimo exigido, sem modelo de crescimento.
- **V1 (Bazin 1.0.1, `sentinela/methods/bazin.py:65`):** taxa = máx(Selic, `BAZIN_TAXA_MIN` = 5%); valor = DY × preço ÷ taxa. O preço cancela: o valor é D ÷ taxa, e o upside, DY ÷ taxa − 1; a nota acompanha a Selic (F-5; armadilha 5).

| Opção | Taxa | Regime | Referência |
|---|---|---|---|
| (a) manter a Selic | máx(Selic, 5%) | nominal | V1 |
| (b) taxa fixa | 6% (o rendimento mínimo do Bazin original) | nominal, sem ajuste | Bazin (1992) |
| (c) k real sem crescimento real | k real = NTN-B + prêmio (ficha da taxa real) | real (D0 constante em termos reais: Gordon com g real = 0) | Gordon com g = 0; ficha da taxa real |
| (d) adiar para o F2C-5 (lentes) | a da (a) até lá | nominal | — |

Em todas: o gate de DY de 5% (`BAZIN_DY_MIN`) e o alerta de armadilha acima de 15% (`BAZIN_DY_ARMADILHA`) ficam; o perfil crescimento continua fora.

## 2. Insumos

| Insumo | Definição exata | Fonte | Unidade e escala | Data de referência |
|---|---|---|---|---|
| DY | dividendos e JCP de 12 meses (pela data ex) ÷ preço; a janela de 5 anos do checkpoint (item 4) é do F2C-1 e fica declarada como limitação | cascata (yfinance e brapi, pela fronteira de `sentinela/data/normalizacao.py`) | razão | a do provedor |
| Preço | fechamento bruto | cascata (D-1); no exemplo, o COTAHIST | R$ por ação | pregão |
| Selic (a e d) | meta Selic | BCB SGS 432 (`config.get_selic_atual`) | razão | a da série |
| k real (c) | NTN-B do vértice + prêmio | ficha da taxa real | razão, real | data-base da NTN-B |
| Perfil | crescimento quando ROE > `ROE_CRESCIMENTO_MIN` (20%) **e** DY < `DY_CRESCIMENTO_MAX` (4%), as duas ao mesmo tempo e estritas (`valuation_engine.py:195`); renda no resto | motor | — | — |

## 3. Regime, janela e data

- **(a) e (d):** nominal; a taxa muda com o Copom (contra o princípio 9 do PLANO: a nota não deve seguir o ciclo de juros).
- **(b):** a taxa fixa de 6% é a do livro, sem regime declarado; sobre um dividendo nominal, funciona como um rendimento nominal mínimo, estável no ciclo.
- **(c):** regime real, coerente com o Gordon (D22): o dividendo é tratado como perpetuidade constante em termos reais (g real = 0), descontado pelo k real.
- **Janela:** a do DY de 12 meses (a de 5 anos é do F2C-1). **Data:** a do preço e a da taxa, na proveniência (D16).

## 4. Hipóteses e inaplicabilidade

Abstenções da 1.0.1, que ficam em todas as opções: "perfil crescimento", "DY não confiável", "DY abaixo do mínimo" (DY < 5%), "resultado não finito". Alerta: "DY acima do limite de armadilha" (DY > 15%).

Novas, por opção:
- (a) e (d): Selic indisponível segue o comportamento de hoje (contingência `SELIC_FALLBACK`, E-6 no F3-1);
- (b): nenhuma (taxa constante);
- (c): "insumo ausente: taxa real" (NTN-B indisponível ou além da defasagem; ficha da taxa real), sem contingência.

Hipótese em todas: o dividendo de 12 meses representa o dividendo sustentável; JCP entra pelo valor bruto declarado (antes do IR retido na fonte).

## 5. Exemplo calculado de forma independente

**LREN3 (Lojas Renner S.A., CNPJ 92.754.738/0001-62)**, conta à mão, sem o código do projeto:

- **DFP 2025** (CVM, `dfp_cia_aberta_2025.zip`, `DT_REFER` 2025-12-31, `VERSAO` 2, escala MIL): DVA consolidada, 7.08.04.01 "Juros sobre o Capital Próprio" = 834.310 mil; 7.08.04.02 "Dividendos" = 0; Composição do Capital: 1.006.845 ON − 24.646 em tesouraria = 982.199 mil ações.
- **Preço:** COTAHIST de setembro de 2026 (`COTAHIST_M092026.ZIP`), último pregão do arquivo, 25/09/2026, LREN3, mercado à vista: **R$ 11,12**.
- D = 834.310 ÷ 982.199 = **R$ 0,849430** por ação; DY = 0,849430 ÷ 11,12 = **7,6388%** (passa o gate de 5%; abaixo do alerta de 15%). Perfil renda: o DY de 7,64% já é maior que 4%, então a regra de crescimento não se aplica, qualquer que seja o ROE.
- **Definição do D no exemplo:** é o JCP do exercício de 2025 declarado na DVA (competência), não os proventos de 12 meses pela data ex que a cascata entrega (seção 2). A fórmula é a mesma; o teste que vier deste exemplo (F2B-31) deve passar o DY como insumo, sem esperar que o provedor o reproduza.

| Opção | Taxa | Valor (R$) | Upside sobre R$ 11,12 |
|---|---|---|---|
| (a) Selic de 14,75% | 14,75% | 0,849430 ÷ 0,1475 = **5,76** | −48,2% |
| (b) taxa fixa | 6% | 0,849430 ÷ 0,06 = **14,16** | +27,3% |
| (c) k real, prêmio 4% | 10,8818% | 0,849430 ÷ 0,108818 = **7,81** | −29,8% |
| (c) k real, prêmio 5% | 11,8818% | 0,849430 ÷ 0,118818 = **7,15** | −35,7% |
| (c) k real, prêmio 7% | 13,8818% | 0,849430 ÷ 0,138818 = **6,12** | −45,0% |
| (d) | a da (a) | **5,76** | −48,2% |

Os F2B-31 (se a opção for (b) ou (c)) transformam este exemplo em teste (D28).

## 6. Sensibilidade

Mediana do upside no universo inicial (F2B-21, pergunta 3; 25 ações com Bazin):

| Opção | Mediana do upside |
|---|---|
| (a) Selic de 10% | −20,2% |
| (a) Selic de 12% | −33,5% |
| (a) Selic de 15% | −46,8% |
| (b) 6% | +33,1% |
| (c) prêmio 4% | −26,6% |
| (c) prêmio 5% | −32,8% |
| (c) prêmio 7% | −42,5% |

Pelo preço cancelar, o upside de cada ativo é DY ÷ taxa − 1, e a taxa é uma só para todos os ativos em qualquer opção: a ordem dos ativos é sempre a do DY. O que muda entre as opções é o nível e a estabilidade no tempo: na (a), o nível segue cada reunião do Copom; na (b), fica parado; na (c), segue a NTN-B do vértice, que reage menos ao Copom que a Selic, mas não fica parada. Nesta data-base (15/10/2026), a (c) com prêmio de 5% equivale à (a) com Selic de 11,88%.

## 7. Parâmetros e justificativa

### 7.1 Opção da taxa — [DECISÃO]
- **(a) manter a Selic:** os testes que o F2B-7 marcou com o F-5 (`test_b_mediana_de_tres_metodos_pela_selic`, `test_b_media_de_dois_metodos_pela_selic`, `test_b_bazin_no_limite_de_5_por_cento_pela_selic`) seguem como quebra esperada; a nota segue o Copom; o F-5 fica aberto; o F2B-31 sai da fila, e o F2B-5 não tira a `selic` do contrato.
- **(b) taxa fixa (6%):** âncora estável no ciclo; os três testes marcados com o F-5 viram no F2B-31; a justificativa do 6% é a do livro (D23 pede a justificativa escrita).
- **(c) k real sem crescimento real:** coerente com o Gordon (g real = 0) e com a taxa real da fase; os testes do F-5 viram no F2B-31; depende da taxa real (abstenção sem ela).
- **(d) adiar para o F2C-5:** a Selic fica como taxa do Bazin até lá, e o F2B-5 não tira a `selic` do contrato; o F2B-31 sai da fila.

### 7.2 Piso da taxa (opção (a)) — [DECISÃO]
Hoje `BAZIN_TAXA_MIN` = 5%. Só faz sentido na (a) e na (d); na (b) e na (c), o piso sai ou fica sem efeito. Sair a constante é do F2B-5, se o F2B-31 for feito.

### 7.3 Gate e alerta — já decididos
O gate de DY de 5% e o alerta de armadilha acima de 15% ficam em todas as opções ([BAZIN]).
