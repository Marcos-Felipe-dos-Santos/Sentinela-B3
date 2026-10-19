# Taxa de desconto real (custo do capital próprio) — versão 0.1

**Status:** rascunho (19/10/2026, escrito pelo loop no F2B-22). O loop nunca marca ficha como aprovada; a aprovação, depois da auditoria externa em modo FICHA (D30), é do Marcos no marcador "Fichas da 2B, taxa e fontes".
**Itens que dependem:** F2B-27 (provedor do Tesouro), F2B-29 (insumos reais e Fisher no contrato), F2B-30 (taxa real com proveniência), F2B-1 (Gordon), F2B-3 e F2B-32 (lente de bancos), F2B-31 (Bazin, se a [BAZIN] ficar em (c)), F2B-2 (vértice da NTN-B do FII, se a [FII] usar o mesmo).
**Decisões de origem:** checkpoint da Fase 0 (`docs/decisoes/checkpoint-fase0.md`), seção 4, item 2; ADR-0002, D15; ADR-0003, D16, D21, D22 e D23.
**Levantamento:** `docs/decisoes/fontes-fase2b.md` (F2B-21), perguntas 1, 2 e 3.

Esta ficha apresenta definições, dados e opções. Nenhum parâmetro é decidido pelo texto: cada um está na seção 7, marcado **[DECISÃO]**, com as opções e o efeito.

## 1. Fórmula e referência

| Grandeza | Fórmula |
|---|---|
| **Custo do capital próprio real** | k_real = y_real + prêmio, com y_real a taxa da NTN-B do vértice escolhido (% a.a., real) |
| **Conversão real ↔ nominal (Fisher exato)** | (1 + k_nominal) = (1 + k_real) × (1 + π), com π a inflação da conversão; de volta, k_real = (1 + k_nominal) ÷ (1 + π) − 1 |

- **Taxa livre de risco real mais prêmio.** A taxa de um título público indexado à inflação é a taxa livre de risco real da moeda local, e o custo do capital próprio é ela somada a um prêmio de risco (Damodaran, *Investment Valuation*, 3ª ed., Wiley, 2012, cap. 7, "Riskless Rates and Risk Premiums": taxa livre de risco real a partir de títulos indexados e prêmio de risco do capital próprio). A forma aditiva com um prêmio único é a do checkpoint da Fase 0 (seção 4, item 2) e da `MacroContext.cost_of_equity_real` de hoje (`config.py:234`).
- **Fisher exato.** Irving Fisher, *The Theory of Interest* (1930), cap. II, "Money Interest and Real Interest": a taxa nominal compõe a real e a variação de preços multiplicativamente. A ficha usa a forma exata, nunca a aproximação aditiva (nominal ≈ real + π).
- **Consequência do regime (dossiê da Fase 2, seção 3; armadilha 1).** Com k e g convertidos pela mesma inflação, o valor de um fluxo crescente é o mesmo no regime real e no nominal (kN − gN = (1 + π)(k_real − g_real)). O que não pode é misturar: k real com g nominal superavalia (no levantamento, de 1,5 a 3,3 vezes; F2B-21, pergunta 3).

## 2. Insumos

| Insumo | Definição exata | Fonte | Unidade e escala | Data de referência |
|---|---|---|---|---|
| Taxa da NTN-B | taxa do título IPCA+ (NTN-B Principal, "Tesouro IPCA+", ou NTN-B, "Tesouro IPCA+ com Juros Semestrais") no vértice escolhido; colunas oficiais `Taxa Compra Manha` e `Taxa Venda Manha` | Tesouro Transparente, "Preço e taxa dos títulos ofertados pelo Tesouro Direto" (`precotaxatesourodireto.csv`, F2B-21, pergunta 1: status 200, de 2004-12-31 a 2026-10-15) | % a.a., real (sobre o IPCA); a ficha usa em razão (6,96% → 0,0696) | `Data Base` da linha (a mais recente: 15/10/2026 na coleta) |
| API do Tesouro Direto da V1 | `treasureList.json`, lida hoje por `config._fetch_ntnb` | tesourodireto.com.br | — | **404** na coleta (403 no dossiê): não serve de fonte |
| Inflação da conversão | uma de três definições (seção 7): IPCA de 12 meses realizado; expectativa do Focus (12 meses à frente, ou o ano mais longo); implícita no vértice | IPCA: IBGE SIDRA tabela 1737, variável 2265 (4,58% em set/2026); BCB SGS 433 sem resposta na coleta. Focus: BCB Olinda, `ExpectativasMercadoInflacao12Meses` (4,4009% em 09/10/2026) e `ExpectativasMercadoAnuais` (2030: 3,50%). Implícita: não determinada (F2B-21, pergunta 2) | razão | a da série (mês do IPCA; data do boletim Focus) |
| Prêmio de risco | número único somado à taxa real | decisão do checkpoint: base de 5%, sensibilidade de 4% e 7% | razão | fixado por versão da ficha |

## 3. Regime, janela e data

- **Regime: real** (checkpoint, item 2; D22). Os métodos que descontam fluxos (Gordon, lente de bancos e, se a [BAZIN] ficar em (c), o Bazin) recebem k_real e devem expressar g e o ROE no mesmo regime (fichas do F2B-23 e do F2B-26). A conversão de Fisher só serve para exibir o equivalente nominal ou para converter um insumo nominal (o ROE contábil, o g nominal); não muda o valor quando aplicada dos dois lados.
- **Janela:** a taxa é a da data-base mais recente do Tesouro, sem média temporal. A inflação é a da série escolhida, na data mais recente disponível.
- **Data:** a análise registra a data-base da NTN-B, a da inflação e o vértice usados (proveniência, D16). A defasagem máxima entre a data de referência da análise e a data-base da NTN-B é parâmetro (seção 7).

## 4. Hipóteses e inaplicabilidade

Abstenções (textos propostos):
1. **NTN-B indisponível:** a fonte do Tesouro não respondeu e não há cópia em cache dentro da defasagem máxima → "taxa real indisponível: NTN-B sem dado do Tesouro dentro da defasagem". **A contingência de 7% (`config.py:122`, `NTNB_LONGA_FALLBACK`) não entra** no lugar do dado (ADR-0003; contrato de método: sem insumo, abstém-se).
2. **NTN-B mais velha que a defasagem máxima** → "taxa real indisponível: NTN-B de <data-base>, além da defasagem de <N> dias úteis".
3. **Inflação indisponível** (só quando a conversão é necessária, por exemplo para converter o ROE contábil): → "inflação da conversão indisponível"; o método que dependa dela se abstém. A contingência de 5,5% (`config.py:121`, `IPCA_12M_FALLBACK`) não entra.
4. **Vértice ausente na data-base** (título do vértice não ofertado naquela data): → "vértice <x> sem taxa na data-base"; não se troca de vértice sem decisão.

Hipóteses declaradas: o prêmio é o mesmo para todas as ações (sem beta nem prêmio por setor nesta versão). A taxa do título soberano em moeda local embute risco de crédito do emissor; usá-la inteira como "livre de risco" ou descontar dela um spread de crédito soberano é o ponto 7.7 (**[DECISÃO]**), não uma hipótese desta versão.

## 5. Exemplo calculado de forma independente

Valores do levantamento (F2B-21, perguntas 1 e 2), conta à mão, sem o código do projeto:

- NTN-B: média das IPCA+ de 2035 em diante, taxa de venda, data-base 15/10/2026: (6,96 + 6,85 + 6,85 + 6,86 + 6,94 + 6,95 + 6,87 + 6,87 + 6,87 + 6,83 + 6,85) ÷ 11 = 75,70 ÷ 11 = **6,8818%**.
- Prêmio: 5% (base do checkpoint).
- k_real = 6,8818% + 5% = **11,8818%**.
- Inflação (Focus 12 meses, 09/10/2026): π = 4,4009%.
- k_nominal = 1,118818 × 1,044009 − 1 = **16,8056%**.
- De volta: 1,168056 ÷ 1,044009 − 1 = 0,118818 = 11,8818% (ida e volta sem perda).

O mesmo k_real com o IPCA de 12 meses do IBGE (4,58%) dá k_nominal = 1,118818 × 1,0458 − 1 = **17,0060%**; com o Focus de 2030 (3,50%), **15,7977%**. Para comparação, a V1 desconta hoje a k = Selic + 7% = 21,75% (Selic de 14,75%, a semente dos testes), nominal.

O F2B-30 transforma este exemplo em teste (D28), com os valores tirados daqui.

## 6. Sensibilidade

k_real (% a.a.) por vértice e prêmio, taxa de venda, data-base 15/10/2026:

| Vértice | Taxa | Prêmio 4% | Prêmio 5% | Prêmio 7% |
|---|---|---|---|---|
| Mais perto de 10 anos (2035, Tesouro IPCA+) | 6,96 | 10,96 | 11,96 | 13,96 |
| Mais perto de 10 anos (2037, juros semestrais) | 6,95 | 10,95 | 11,95 | 13,95 |
| 2045 (Tesouro IPCA+; 6,87 no de juros semestrais) | 6,85 | 10,85 | 11,85 | 13,85 |
| Mais longo (2050, Tesouro IPCA+) | 6,86 | 10,86 | 11,86 | 13,86 |
| Média de 2035 em diante (11 títulos) | 6,8818 | 10,8818 | 11,8818 | 13,8818 |
| Média de 2035 em diante, taxa de compra | 6,7618 | 10,7618 | 11,7618 | 13,7618 |

O vértice move o k em até 0,11 ponto entre as linhas da tabela (6,96 × 6,85); o tipo de taxa (compra ou venda), em 0,12 ponto; o prêmio, em 1 a 3 pontos. A inflação não move o k_real; move só o equivalente nominal (de 15,8% a 17,0% com prêmio de 5%).

Efeito nos métodos, pela matriz do F2B-21 (pergunta 3; mediana do upside nas ações atuais do universo inicial, NTN-B de 6,8818%): o Gordon real vai de +27,1% a −39,7% conforme a definição de g real, o prêmio e a inflação, nas três inflações da seção 7.4 (tabela da pergunta 3 do levantamento; com as 12 inflações do `matriz_sensibilidade.csv` do cache, até −42,7%); a escolha de g é da ficha do F2B-23; o Bazin com k real sem crescimento, de −26,6% (prêmio 4%) a −42,5% (prêmio 7%), contra −20,2% a −46,8% da V1 com Selic de 10% a 15%.

## 7. Parâmetros e justificativa

Nenhum valor abaixo está decidido: são as opções, com o efeito. A decisão é do Marcos no marcador.

### 7.1 Prêmio — [DECISÃO]
- **Já decidido no checkpoint:** base de 5%, com 4% e 7% como sensibilidade; o valor só é fixado depois da coleta da NTN-B com o Tesouro respondendo.
- **Estado da condição:** na coleta do F2B-21 (19/10/2026), a fonte histórica do Tesouro (Tesouro Transparente) respondeu; a API que a V1 lê, não. O marcador confirma se essa fonte satisfaz a condição.
- **Observação:** a `cost_of_equity_real` de hoje soma `GORDON_PREMIO_RISCO` = 7% (`config.py:159` e `:236`), o prêmio da V1 sobre a Selic, não o de 5% do checkpoint; o F2B-30 traz o prêmio da ficha.
- **Efeito:** cada ponto de prêmio move o k_real em 1 ponto (tabela da seção 6).

### 7.2 Vértice — [DECISÃO]
Opções: o mais perto de 10 anos (2035 no Tesouro IPCA+; 2037 no de juros semestrais, na data-base de 15/10/2026), 2035, 2045, o mais longo, ou a média de 2035 em diante (o critério da `ntnb_longa` de hoje, `config.py:228`). Efeito: até 0,11 ponto no k entre os vértices da tabela (seção 6). A média muda de composição quando o Tesouro lança ou retira títulos; um vértice fixo muda de prazo com o tempo.

### 7.3 Tipo de taxa — [DECISÃO]
Opções: a taxa de compra (`Taxa Compra Manha`, a que o investidor obtém ao comprar) ou a de venda (`Taxa Venda Manha`, a da recompra pelo Tesouro). Efeito: 0,12 ponto (6,76% × 6,88% na média). Junto com esta decisão, o **nome dos campos no código** (exceção em aberto na fila, seção "Vocabulário"): nomes neutros (por exemplo, `taxa_investidor` e `taxa_resgate`), com o nome oficial na proveniência, ou exceção à regra de vocabulário só para o nome técnico do título público.

### 7.4 Inflação da conversão — [DECISÃO]
Opções: IPCA de 12 meses realizado (IBGE, 4,58%; o SGS 433 da V1 não respondeu na coleta), expectativa do Focus (12 meses à frente, 4,40%; ou o ano mais longo publicado, 2030: 3,50%) ou a implícita no vértice (não determinada no F2B-21). **Prazos:** a taxa é de um título de 9 anos ou mais; o IPCA realizado e o Focus de 12 meses medem um ano só, e o Focus de 2030 é o prazo mais longo que o Focus publica. Só a implícita casa o prazo com o do vértice. Efeito: não muda o k_real; muda o equivalente nominal (seção 5) e, nas fichas do Gordon e dos bancos, a conversão do g e do ROE contábil (na definição (i) do F2B-23, o g real cai cerca de 1 ponto por ponto de inflação: com g nominal de 4,8% e π de 4,4%, a derivada é −1,048 ÷ 1,044² ≈ −0,96).

### 7.5 Defasagem máxima — [DECISÃO]
Opções: só a última data-base publicada, ou até N dias úteis, com a data exibida. Além dela, abstenção (seção 4), sem contingência. O histórico do Tesouro é publicado com atraso de alguns dias (última data-base 15/10/2026 numa coleta de 19/10/2026).

### 7.6 Fonte — [DECISÃO]
Tesouro Nacional (oficial): o histórico do Tesouro Transparente, que respondeu na coleta, e a API do Tesouro Direto, se voltar a responder. Outra fonte (por exemplo, a ANBIMA) só por decisão.

### 7.7 Risco de crédito soberano na taxa — [DECISÃO]
Opções: usar a taxa da NTN-B inteira como livre de risco real (a forma da `cost_of_equity_real` de hoje e do checkpoint), ou descontar dela um spread de crédito soberano (o ajuste de risco-país que Damodaran discute para títulos em moeda local; capítulo citado de memória, a conferir). Efeito: o spread descontado reduz o k_real ponto a ponto; sem fonte de spread levantada no F2B-21, a segunda opção exige levantamento novo.

