# Rendimento do FII contra a NTN-B — versão 0.1

**Status:** rascunho (19/10/2026, escrito pelo loop no F2B-25). O loop nunca marca ficha como aprovada; a aprovação, depois da auditoria externa em modo FICHA (D30), é do Marcos no marcador "Fichas da 2B, taxa e fontes".
**Itens que dependem:** F2B-28 (DY do Informe Mensal), F2B-2 (rendimento do FII contra NTN-B + spread).
**Achado de origem:** F-9 da auditoria red team (`docs/auditoria/2026-09-red-team.md`): o preço justo do FII é só DY ÷ Selic líquida, sem âncora patrimonial; armadilha 5.
**Decisões de origem:** checkpoint da Fase 0, seção 4, item 3 (NTN-B + spread, com o spread pela mediana histórica; Selic líquida e P/VP como contexto); ADR-0003, D21 a D23.
**Depende de:** `docs/metodologia/taxa-real.md` (F2B-22), para a NTN-B e o vértice.
**Levantamento:** `docs/decisoes/fontes-fase2b.md` (F2B-21), perguntas 3 e 4.

Esta ficha apresenta definições, dados e opções. Nenhum parâmetro é decidido pelo texto: os da seção 7 estão marcados **[DECISÃO]**.

## 1. Fórmula e referência

**Preço justo = preço × DY ÷ (NTN-B + spread) = R ÷ (NTN-B + spread)**, com R o rendimento por cota de 12 meses.

- **O preço cancela** (armadilha 5): o preço justo é o rendimento capitalizado a uma taxa, e o upside é DY ÷ (NTN-B + spread) − 1. A ordem entre os FIIs é a do DY; a taxa muda o nível.
- **Referência:** é a forma de uma perpetuidade sem crescimento (o valor de um fluxo constante é o fluxo dividido pela taxa: o modelo de dividendos com crescimento g = 0, na forma da ficha do Gordon, `docs/metodologia/gordon.md`, seção 1), com a taxa exigida = taxa real do título público + um spread que representa o prêmio histórico dos FIIs sobre ele (checkpoint, item 3). A comparação do rendimento do FII com a NTN-B, e não com a Selic, segue o regime real da fase (D22): o rendimento de um FII de tijolo tende a ser corrigido por índices de preço nos contratos de aluguel.
- **V1 (`sentinela/methods/fii_yield.py`):** preço justo = DY × preço ÷ (Selic × `FII_FATOR_IR` = 0,85), a Selic líquida de IR; com vacância informada, o DY vira DY × (1 − vacância), caminho hoje inerte (o motor passa `None`); o P/VP entra só no score (F-9).

## 2. Insumos

| Insumo | Definição exata | Fonte | Unidade e escala | Data de referência |
|---|---|---|---|---|
| Rendimento de 12 meses (R) | soma dos rendimentos por cota dos 12 últimos meses | duas opções (7.3): o Informe Mensal da CVM pelo F2B-28 (`Percentual_Dividend_Yield_Mes`, **em razão**, sobre o VP da cota do mês anterior; F2B-21, pergunta 4) ou a cascata (DY do yfinance e da brapi × preço) | R$ por cota | o último mês do Informe ou a do provedor |
| Preço | fechamento bruto | cascata (D-1); no exemplo, o COTAHIST | R$ por cota | pregão |
| NTN-B | a do vértice | ficha da taxa real | razão, real | data-base do Tesouro |
| Spread | prêmio do DY de 12 meses dos FIIs sobre a NTN-B | série do F2B-21 (pergunta 4), por definição e janela (7.1) | razão | a da versão da ficha, ou recalculada (7.1) |
| Selic líquida (contexto) | Selic × 0,85 | BCB SGS 432 | razão | a da série |
| P/VP (contexto) | preço ÷ VP da cota | Informe Mensal (F2A-11) | razão | último Informe |

## 3. Regime, janela e data

- **Regime:** a NTN-B é real; o rendimento do FII é tratado como fluxo que acompanha a inflação (contratos de aluguel corrigidos por índice de preço). **Limite (F-9):** os FIIs de papel indexados ao CDI têm rendimento que segue o juro nominal, não a inflação; para eles a comparação com a NTN-B mistura regimes (ponto 7.5).
- **Tributação:** o rendimento do FII é isento de IR para pessoa física nas condições da lei; a NTN-B paga IR. A V1 compara com a Selic **líquida**; a NTN-B + spread é bruta, e o spread histórico já embute essa diferença na medida em que foi medido contra a taxa bruta (ponto para a [FII]).
- **Janela:** rendimento de 12 meses (soma dos meses); spread pela janela da 7.1.
- **Data:** a do último Informe, a do preço e a data-base da NTN-B, na proveniência (D16).

## 4. Hipóteses e inaplicabilidade

Abstenções:
- "DY ausente ou não confiável" (DY zero ou ausente, ou fora de 0 a 25% ou não finito, pelo invariante dos motores). Na V1 esse caso não é abstenção: `fii_engine.py:78` devolve preço justo igual ao preço, score 50 e NEUTRO; o método novo passa a se abster, como pede o contrato de método;
- "insumo ausente: NTN-B" (sem dado dentro da defasagem; ficha da taxa real), sem contingência;
- "insumo ausente: spread" (sem a constante da versão da ficha, ou sem a série, se recalculado);
- com o Informe (F2B-28): menos de 12 meses no Informe → abstenção, com o motivo.

Hipóteses: o rendimento dos 12 últimos meses é sustentável; o spread histórico é estável o bastante para servir de taxa exigida; sem ajuste de vacância, como hoje na prática (sem fonte oficial, F2A-23; ponto 7.6).

## 5. Exemplo calculado de forma independente

**HGLG11 (CSHG Logística FII, CNPJ 11.728.688/0001-47)**, tijolo, conta à mão, sem o código do projeto:

- **Informe Mensal de FII** (CVM, `inf_mensal_fii_complemento_2025.csv` e `_2026.csv`, maior `Versao` de cada mês): rendimento do mês = `Percentual_Dividend_Yield_Mes` (razão) × `Valor_Patrimonial_Cotas` do mês anterior.

  | Mês | DY do mês | VP do mês anterior | Rendimento (R$/cota) |
  |---|---|---|---|
  | 2025-10 | 0,006769 | 162,498293 | 1,099951 |
  | 2025-11 | 0,005901 | 162,238907 | 0,957372 |
  | 2025-12 | 0,006635 | 165,789389 | 1,100013 |
  | 2026-01 | 0,006604 | 166,576588 | 1,100072 |
  | 2026-02 | 0,006610 | 166,408892 | 1,099963 |
  | 2026-03 | 0,006637 | 165,744203 | 1,100044 |
  | 2026-04 (versão 2) | 0,006477 | 165,712611 | 1,073321 |
  | 2026-05 | 0,006607 | 166,490023 | 1,100000 |
  | 2026-06 | 0,006626 | 166,003651 | 1,099940 |
  | 2026-07 | 0,007023 | 166,603103 | 1,170054 |
  | 2026-08 (versão 2) | 0,007027 | 166,431221 | 1,169512 |
  | 2026-09 | 0,007052 | 165,951408 | 1,170289 |

  R = soma = **R$ 13,240530** por cota.
- **Preço:** COTAHIST de setembro de 2026 (`COTAHIST_M092026.ZIP`), último pregão do arquivo, 25/09/2026 (não o último dia útil do mês), HGLG11, mercado à vista: **R$ 147,86**. DY de 12 meses = 13,240530 ÷ 147,86 = **8,9548%**.
- **NTN-B:** 6,8818% (média das IPCA+ de 2035 em diante, venda, data-base 15/10/2026; ficha da taxa real). As datas não coincidem: rendimento até setembro de 2026, preço de 25/09/2026 e NTN-B de 15/10/2026; num cálculo de produção, as três ficam na proveniência.
- **Preço justo** = 13,240530 ÷ (0,068818 + spread):

  | Spread | Taxa | Preço justo (R$) | Upside sobre R$ 147,86 |
  |---|---|---|---|
  | 1 ponto | 7,8818% | 167,99 | +13,6% |
  | 2 pontos | 8,8818% | 149,07 | +0,8% |
  | 3 pontos | 9,8818% | 133,99 | −9,4% |
  | 2,7452 (mediana mensal, todos, série 2017-10 a 2026-09; 2,75 arredondado) | 9,6270% | 137,54 | −7,0% |
  | 3,2466 (idem, últimos 5 anos; 3,25 arredondado) | 10,1284% | 130,73 | −11,6% |
  | 2,2071 (mediana mensal, tijolo, série; 2,21 arredondado) | 9,0889% | 145,68 | −1,5% |
  | 2,6455 (idem, tijolo, últimos 5 anos; 2,65 arredondado) | 9,5273% | 138,98 | −6,0% |
  | V1: Selic líquida, 14,75% × 0,85 (a Selic de contingência da V1, `SELIC_FALLBACK`, que é também a semente dos testes) | 12,5375% | 105,61 | −28,6% |

As medianas entram na conta com quatro casas (série do F2B-21, `spreads_agregados` em `scripts/levantamento_fase2b.py`, seção 4; o documento `docs/decisoes/fontes-fase2b.md` as mostra com duas); com o valor arredondado, o preço justo muda nos centavos (2,75 pontos dão R$ 137,47). O F2B-2 transforma este exemplo em teste (D28), com o spread que o Marcos escolher, fixado com as casas da constante decidida.

## 6. Sensibilidade

No universo inicial (F2B-21, pergunta 3; mediana do upside dos 25 FIIs atuais, com o DY do retrato do yfinance e NTN-B de 6,8818%): +35,5% com 1 ponto, +20,2% com 2, +8,1% com 3; +16,9% com 2,25 pontos (p25 da série), +10,9% com 2,75 (mediana da série), +5,4% com 3,25 (mediana de 5 anos), +4,1% com 3,38 (p75 da série). A V1 (Selic líquida) vai de +25,6% (Selic de 10%) a −16,2% (15%).

Pelo preço cancelar, o spread desloca o nível e não a ordem (dossiê da Fase 2, seção 4). Por grupo, a mediana do spread é de 2,21 pontos (tijolo) a 5,40 (papel) na série, e de 2,65 a 6,15 nos últimos 5 anos: um spread único trata papel e tijolo com a mesma taxa exigida.

O vértice não é quantificado aqui: o spread do F2B-21 só existe contra a média de 2035 em diante, e outro vértice exige medi-lo de novo (7.2).

Limites da série (F2B-21): só os 25 FIIs atuais do universo (sobrevivência); tipo pela composição de agosto de 2026, fixa; a cesta da NTN-B de 2035 em diante muda de prazo ao longo dos anos (de cerca de 18 anos em 2017 a 9 hoje); o DY da série vem do Informe e do COTAHIST, e o da matriz do universo, do yfinance.

## 7. Parâmetros e justificativa

### 7.1 Spread — [DECISÃO]
- **Definição:** mediana dos FIIs (todos), por tipo (tijolo e papel), ou por fundo.
- **Janela:** 5 anos, 10 anos (a série do F2B-21 tem 9) ou a série inteira.
- **Atualização:** constante datada, revista por versão da ficha; ou recalculada a cada análise, o que exige as séries em produção (Fase 3).
- Efeito no exemplo: de R$ 130,73 (3,25 pontos) a R$ 145,68 (2,21 pontos); 1 ponto de spread muda o preço justo em cerca de 10%.

### 7.2 Vértice — [DECISÃO]
O mesmo da taxa real (ficha do F2B-22, 7.2) ou outro. O spread do F2B-21 foi medido contra a média de 2035 em diante; trocar o vértice exige medir de novo.

### 7.3 Rendimento — [DECISÃO]
O do Informe (F2B-28; oficial, em razão, sobre o VP do mês anterior, reconstruído em R$ por cota) ou o da cascata (yfinance e brapi). No HGLG11: 8,95% pelo Informe e COTAHIST; o do retrato do yfinance do F2B-21 é outra medida (proventos pela data ex sobre o preço do retrato).

### 7.4 Benchmark do score — [DECISÃO]
Hoje ±20 pontos pela Selic líquida. Opções: (a) manter a Selic líquida, e a nota segue o ciclo (contra o princípio 9 do PLANO); (b) o mesmo benchmark do preço justo (NTN-B + spread); (c) a Selic só exibida, como contexto.

### 7.5 Papel e tijolo — [DECISÃO]
Benchmark único (NTN-B + spread) ou o papel indexado ao CDI comparado com o CDI (F-9). Sem a separação, um FII de papel com DY alto por CDI alto parece barato contra a NTN-B.

### 7.6 Vacância — [DECISÃO]
Sem fonte oficial (F2A-23). Opções: o risco "vacância não informada" na saída, ou nada.

### 7.7 P/VP — [DECISÃO]
Contexto, pelo checkpoint. Os pontos de score das faixas da V1 (`FiiNav`) ficam ou saem; se saírem, a asserção do score em `test_b_fii_nao_considera_o_patrimonio_no_fair_value` muda no F2B-2 (marcador, passo 6). Qualquer que seja a decisão, o F2B-2 muda outras asserções de `tests/test_financeiro_pre_refactor.py` (marca `f9_fii_selic`): o `fair_value == 110,0` do mesmo teste, que é 100 × 0,0935 ÷ (0,10 × 0,85), pela Selic líquida; e `test_b_fii_compara_dy_com_a_selic_liquida_de_ir`, conforme a 7.4.

### 7.8 Tributação — [DECISÃO]
O rendimento do FII é isento para pessoa física, e a NTN-B paga IR; a V1 compara com a Selic líquida. Opções: comparar com a NTN-B bruta mais um spread medido contra a taxa bruta (o F2B-21), ou com a NTN-B líquida de IR, o que exige definir a alíquota e medir o spread de novo.
