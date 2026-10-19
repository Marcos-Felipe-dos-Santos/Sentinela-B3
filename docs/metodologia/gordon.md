# Gordon no regime real — versão 0.2

**Status:** rascunho revisto, 19/10/2026; aguarda auditoria FICHA pelo Claude
(D30) e aprovação do Marcos. **Executor da revisão:** Codex.
**Decisões:** [marcador 2B](../decisoes/marcador-2b.md), Marcos, 19/10/2026.
**Implementação futura:** F2B-1, com insumos de F2B-29/F2B-30 e escopo F2B-4.

## 1. Fórmula e referência

`P0 = D1_real/(k_real − g_real)`, `D1_real = D0 × (1 + g_real)`.
`p = proventos anuais dos controladores / lucro anual dos controladores`;
`b = 1 − p`; `g_N_bruto = ROE_N × b`;
`g_r_bruto = (1 + g_N_bruto)/(1 + π) − 1`;
`g_r = min(g_r_bruto, teto_PIB_real)` — **conversão primeiro, teto depois**.

D0 da DVA anual é aproximação do fluxo recorrente posicionada no fim do
exercício, na moeda-base dessa data. A hipótese é crescimento estável perpétuo,
com ROE e distribuição representativos; não se deduz sustentabilidade de um ano.
D1 nominal = D1 real × (1 + π), k_N e g_N por Fisher (inclusive o g já limitado).
Assim os denominadores diferem por (1 + π) e os dois valores presentes coincidem.

Referência consultada: Damodaran, *Investment Valuation*, **2ª ed.**, Wiley,
2002, [cap. 13, seção I, “The Gordon Growth Model”, subseções “The Model” e
“Limitations of the model”](https://pages.stern.nyu.edu/~adamodar/pdfiles/valn2ed/ch13.pdf).
O capítulo também apresenta retenção × ROE e retenção compatível com crescimento
estável. A localização correspondente na **3ª ed., 2012, cap. 13**, e Gordon e
Shapiro, *Management Science* 3(1), 1956, pp. 102–110, passagem exata,
ficam **a conferir pelo auditor**. Fisher e a composição do k: ficha taxa-real,
seção 1. O teto pelo Focus é adaptação decidida pelo Marcos, não prescrição do livro.

## 2. Insumos

| Insumo | Fonte, perímetro e unidade |
|---|---|
| Lucro, LPA e PL | CVM DFP anual consolidada, mesma versão, exercício e controladores; LPA básico da classe conforme por-acao 1.1; lucro/PL em R$ após escala, LPA já em R$/ação |
| ROE_N | lucro dos controladores do exercício / PL final dos controladores da mesma DFP; convenção histórica desta lente, não a convenção inicial da lente de bancos |
| D0 | Dividendos + JCP **bruto** da DVA, contas 7.08.04.02 e 7.08.04.01, confirmadas por descrição e perímetro; dividir por ações líquidas do mesmo documento quando o direito comum permitir |
| p | Soma da DVA / lucro dos controladores; janela anual idêntica; não DY × preço / LPA de outra janela |
| Ações / composição | CVM Composição do Capital e FCA; escala determinada pela ficha por-acao 1.1, não pela escala monetária; unit = soma dos componentes oficiais |
| k, π | ficha taxa-real 0.2; π do exercício anual convertido |
| Teto_PIB_real | BCB Olinda, ExpectativasMercadoAnuais, PIB Total, mediana, baseCalculo=0, maior ano na última pesquisa publicada; regra no registro §2.2 |
| Preço | Fechamento bruto por ação/unit do mesmo direito do D0; só comparação/upside, não cria D0 |

Payout é razão de **totais do mesmo perímetro**, evitando misturar ações de fim
do exercício com o denominador médio do LPA divulgado. LPA precisa ser positivo
e coerente, mas não é usado para fabricar payout com esses denominadores distintos.
Não usar DY de 12 meses da cascata. JCP informado como zero é zero; linha ausente
não é zero: se só um dos dois proventos existe, usar o valor existente apenas
quando a ausência do outro estiver confirmada como não ocorrência na DVA.
Sem prova, abster por proventos incompletos. Valores de terceiros não entram.
Consolidado sem atribuição verificável aos controladores: abstenção; DVA individual
ou nota pode comprovar o perímetro, sem trocar exercício nem versão silenciosamente.

## 3. Regime, janela e data

Um exercício anual completo, última DFP elegível, nunca ITR parcial/TTM. Numeradores
DVA, lucro e LPA têm início/fim idênticos; PL final é estoque nessa data. Datas,
idade máxima da DFP, preço e metadados no registro §2.2. Taxa até 5 dias úteis,
cobertura IPCA até 2 meses; Focus última edição devida/publicada. Direitos e
composição vigentes, com evidência não futura. Eventos entre a DFP e o preço
exigem compatibilização oficial ou abstenção por base de ações incompatível;
o alerta da ficha por-acao não prova que dividendos antigos continuam comparáveis.

Histórico menor que um exercício anual completo: abstenção. Distribuição
extraordinária identificada ou mudança estrutural sem reconciliação: não projetar
como recorrente, abster por fluxo não representativo. Holdings como CSAN3/GOAU4
não são automaticamente excluídas por setor, mas precisam cumprir essas guardas.

## 4. Escopo e matriz de validade

STOCK/UNIT, **modelo empresa pelas contas do BPP consolidado** (marcador,
[FINANCEIRAS]). Banco: lente própria; seguradora: sem lente nesta fase; FII,
ETF, BDR e UNKNOWN: classe fora do escopo. ITUB4/BBAS3/SANB11 não entram.
KNCR11/HGLG11 não entram. PNA/PNB ou outros direitos distintos sem atribuição
comum demonstrada (BRSR5/BRSR6/USIM5) abstêm na 2B. Unit (KLBN11/TAEE11)
exige composição e D0/LPA de cada componente com direitos compatíveis; um
componente inelegível abstém a unit. Nenhum rateio agregado inventa direito.

Cada linha abaixo recebe separadamente os motivos de ausente, não numérico,
NaN e infinito do registro §2.1. Validar **antes** de retenção/Fisher/teto.

| Insumo | Zero | Negativo | Fora de faixa / motivo específico |
|---|---|---|---|
| Preço, ações e PL | abstém: não positivo | abstém: não positivo | ações não inteiras, escala/direito desconhecidos: base inválida |
| Lucro e LPA | abstém: lucro/LPA não positivo | abstém: prejuízo/LPA não positivo | conflito de classe/perímetro: atribuição não demonstrada |
| Cada provento | válido, se explicitamente informado | abstém: provento negativo | só linha ausente: proventos incompletos; sem recorrência: fluxo não representativo |
| D0 e payout | abstém: distribuição não positiva | abstém | p > 1: payout fora de (0,1]; não truncar a 95% |
| ROE_N | abstém | abstém | exigir ROE > 0, sem mínimo de 10%; não impor máximo sem spec |
| π | válido | válido se > −1 | ≤ −1: Fisher indefinido; janela diferente: inflação incompatível |
| k_real | permitido só se k > g e k > −1 | idem | k ≤ g: desconto sem convergência |
| g_real e teto PIB | válidos | válidos se > −1 | g ≤ −1 ou g ≥ k: crescimento fora do domínio |
| Resultado / intermediário | valor zero não esperado com D0 > 0 e g > −1 | abstém: valor não positivo | não finito: resultado não finito |

Não há mais mínimo de DY de 4% nem de ROE de 10%. A ausência de teto numérico
para ROE não dispensa validade da contabilidade. Sem fonte real/PIB/inflação,
abster com o nome do insumo, sem contingência. A singularidade k → g pela direita
permanece: divulgar sensibilidade, não criar piso para k−g não autorizado.

## 5. Exemplo independente

**ABEV3**, CNPJ 07.526.557/0001-00, DFP 2025 v1, entregue 12/02/2026.
Snapshot e hashes no registro §2.3; as_of 19/10/2026 17:10 Brasília.
Janela 01/01–31/12/2025, moeda-base **R$ de 31/12/2025**.
Dados monetários em mil R$: lucro 15.503.400; PL final dos controladores
88.774.781 − 860.742 = 87.914.039; DVA dividendos 10.903.280, JCP 0 informado;
LPA básico ON 0,9926913764. Ações 15.761.639 − 145.113 = 15.616.526 milhares;
conferência de escala: lucro / ações = 0,99276 R$/ação, próximo do LPA divulgado;
a divergência é do denominador final versus médio, não prova de igualdade.

Fechamento **30/09/2026: R$ 15,36**, mercado 010, selecionado por data.
Este preço é comparação nominal de setembro com cenário na moeda-base da DFP;
não é retorno real entre essas datas nem análise estrita em setembro.

- D0 = 10.903.280 / 15.616.526 = **0,698188572797817** R$/ação.
- p = 10.903.280 / 15.503.400 = **70,328315079273%**.
- ROE_N = 15.503.400 / 87.914.039 = **17,634726121501%**.
- g_N_bruto = **5,232520371405%**.
- π=4,26% (exercício 2025); g_r_bruto=**0,932783782280%**.
- PIB Focus: pesquisa 16/10/2026, ano 2030, base 0, mediana **2%**, disponível
  no snapshot de 19/10 antes de as_of: teto não atua.
- k_r = 74,38/1100 + 0,05 = **11,761818181818%**.
- Valor = D0 × (1 + g_r)/(k_r − g_r) = **R$ 6,507516151252**.

Conferência nominal: D1_N = D0 × (1 + g_r) × 1,0426,
k_N=16,522871636364%, g_N=5,232520371405%; mesmo R$ 6,507516151252.
O antigo payout D0/LPA daria 70,3328939%, por misturar denominadores; foi
retirado da conta. É esperado independente para o núcleo matemático, não
certificação de recorrência e atribuição da DVA da Ambev: sem essa prova, a saída
operacional se abstém. Não afirmar aprovação de elegibilidade a partir do exemplo.

## 6. Sensibilidade

| Cenário, demais insumos constantes | g_real | Valor (R$) |
|---|---|---|
| Prêmio 4%, IPCA 4,26% | 0,932784% | 7,169587 |
| Prêmio 5%, IPCA 4,26% | 0,932784% | 6,507516 |
| Prêmio 7%, IPCA 4,26% | 0,932784% | 5,493018 |
| IPCA 0%, teto real 2%, prêmio 5% | 2% (teto atua) | 7,295284 |
| IPCA 6%, teto real 2%, prêmio 5% | −0,724037% | 5,551349 |

Variações de IPCA são hipóteses de sensibilidade, não substituições da série de
2025. Fronteira sintética: D1=1, k=10%; g=9%, 9,9% e 9,99% dão 100, 1.000
e 10.000; em g=10% há abstenção. Com teto Focus de 2% esses g não entram:
o cenário de fronteira apenas mostra por que validar k > g mesmo com teto.

## 7. Parâmetros e justificativa

**Decisões do Marcos de 19/10/2026 — todas [DECISÃO] decididas:**
(i) Fisher sobre ROE × retenção; teto real PIB Focus depois da conversão;
retirado GORDON_G_MAX nominal de 8%; retirados mínimos DY 4%/ROE 10%;
payout DVA em (0,1], sem truncamento a 95%; D0 e LPA na mesma DFP anual,
JCP bruto; STOCK/UNIT empresa, abstenção para classes distintas na 2B e
unit pela composição. As alternativas (ii), crescimento ROE real × retenção,
e inflação do Focus não alimentam o método. O teto é limite à extrapolação,
não demonstração de estabilidade da empresa. Pendências de referência e
comprovação do perímetro estão explicitadas; não há aprovação da ficha.
