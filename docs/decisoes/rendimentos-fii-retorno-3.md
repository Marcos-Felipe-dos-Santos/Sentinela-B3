# Rendimentos do FII no retorno total histórico: levantamento (F3-8l)

**Situação em 16/11/2026:** levantamento, sem código de produção. Pedido pela DD-75. Até o Marcos decidir a regra, o retorno do FII abstém com o motivo atual, "sem coleta da relação de proventos do emissor": `BacktestPIT._retornos` lê a relação de companhias da B3 pela raiz do ticker, e fundo não tem essa relação. Não é recomendação nem sugestão de carteira.

Saídas, fora do git: `outputs/f3-8l/levantamento.py` e `levantamento.txt` (banco real, só leitura, tabelas públicas: `fii_informe_linhas`, `precos`, `proventos`, `proventos_coletas`, `eventos_societarios`).

## 1. Fontes oficiais e o que o banco guarda

| Fonte | O que traz | Histórico guardado |
|---|---|---|
| B3, `GetListedCashDividends` (relação de proventos de companhias, tabela `proventos`) | provento por ação com data com | nenhum registro dos emissores da amostra nem do HGLG: o serviço é de companhias |
| B3, `GetListedSupplementFunds` (`b3_fundos.py`, `cashDividends`) | rendimento por cota (`rate`), data com (`lastDatePrior`), pagamento, mês de referência (`relatedTo`), ISIN | não é guardado no banco; o serviço só devolve os meses recentes (no contrato do HGLG de 21/10/2026: 21 registros, de 31/10/2025 a 30/09/2026) |
| CVM, Informe Mensal (`fii_informe_linhas`) | por mês de referência: `Percentual_Dividend_Yield_Mes`, `Valor_Patrimonial_Cotas`, `Percentual_Amortizacao_Cotas_Mes`, `Data_Entrega` por versão | de 09/2016 a 10/2026, 1.743 CNPJs, todas as versões |

O complemento da B3 para fundos não serve à série de 2018 a 2025: ele não tem histórico. A única fonte oficial guardada com os rendimentos desse período é o Informe.

## 2. O Informe: valor, data e disponibilidade

- **Valor por cota do mês M:** o Informe não traz o valor distribuído. A reconstrução é a do `rendimento_fii` (F2B-28, base da Resolução CVM 175): DY do mês M × valor patrimonial da cota do fim do mês M−1.
- **Data com:** o Informe não traz. No contrato do HGLG, os 12 meses do ISIN da cota (`BRHGLGCTF004`) têm data com no último pregão do mês de referência (30/09, 31/08, 31/07, 30/06, 29/05, 30/04, 31/03, 27/02 e 30/01/2026, 30/12, 28/11 e 31/10/2025). Os registros de outros ISINs (`BRHGLGR...`) são recibos de subscrição, fora da cota. Um caso só não basta como regra.
- **Disponibilidade:** a primeira entrega de cada mês sai com mediana de 14 a 15 dias depois do fim do mês, de 2016 a 2026; de 92% a 96% chegam em até 30 dias e de 95% a 99% em até 90 dias.
- **Amortização:** o Informe traz `Percentual_Amortizacao_Cotas_Mes` em separado. O retorno total do FII precisaria dela também; não foi medida aqui.

## 3. Cobertura

**Amostra declarada (DD-69), horizonte de 12 meses depois de D, meses com rendimento reconstruído:** 12 de 12 em todas as datas de 2018 a 2024 (AEFI11 em 2018, ALMI11 em 2019, ALZR11 em 2020, AFCR11 em 2021, AFHI11 em 2022 e AAZQ11 em 2023 e 2024). Em 2025, o AAZQ11 tem 2 de 12: o Informe do fundo no banco termina em 08/2025.

**Universo de fundos negociados na data (ISIN `BR....CTF`):**

| Data | Fundos | Com CNPJ pelo ISIN do Informe | Com os 12 meses do horizonte |
|---|---|---|---|
| 2018-06-29 | 125 | 100 | 93 |
| 2019-06-28 | 158 | 124 | 117 |
| 2020-06-30 | 215 | 172 | 156 |
| 2021-06-30 | 296 | 214 | 190 |
| 2022-06-30 | 373 | 248 | 225 |
| 2023-06-30 | 409 | 266 | 237 |
| 2024-06-28 | 442 | 286 | 253 |
| 2025-06-30 | 502 | 297 | 241 |

Os fundos sem CNPJ pelo ISIN incluem os que não entregam o Informe de FII (o ISIN `CTF` também é de outros fundos listados), e a ligação pelo ISIN não foi conferida com o índice oficial do F2A-1. O número dá a ordem de grandeza, não o universo elegível.

## 4. Conferência entre as duas fontes (HGLG, 10/2025 a 09/2026)

Informe (DY × VP do mês anterior) contra o `rate` da B3 do ISIN da cota, mês a mês: 10 de 12 meses iguais a ±0,1%. Os outros dois divergem: novembro de 2025 (Informe 0,9574 contra B3 1,10; razão 0,870) e abril de 2026 (1,0733 contra 1,10; razão 0,976). Uma explicação possível é a emissão de cotas no mês, que muda a base do DY; não verificado. A conferência cobre um fundo e um ano, porque a B3 não tem histórico para mais.

## 5. Proposta para a decisão do Marcos (sem efeito até lá)

1. **Fonte:** o Informe Mensal da CVM, só fonte oficial, com o valor por cota reconstruído como no `rendimento_fii` (DY de M × VP de M−1), a maior versão entregue até a leitura e o conflito de mesma versão abstendo, como na ficha FII 1.3.
2. **Data ex:** o pregão seguinte ao último pregão do mês de referência, pelo calendário do COTAHIST guardado (decisão 44). É inferência pelo costume observado no HGLG, não dado da fonte; a alternativa sem inferência é contar o rendimento pelo mês de referência dentro do horizonte. A escolha é do Marcos.
3. **Disponibilidade:** o retorno é medido depois do fim do horizonte. Proposta: o Informe dos meses do horizonte entregue até 90 dias depois do fim; sem entrega, abstém com o mês faltante.
4. **Amortização:** fica fora até ser medida e decidida; enquanto isso, o retorno do FII declara a limitação ou abstém no mês com amortização diferente de zero.
5. **Conferência:** onde houver coleta do complemento da B3 (meses recentes), comparar com o Informe e registrar a divergência, sem trocar a fonte.
6. **Ligação:** item seguinte, com a regra escrita, teste vermelho antes e a sonda mostrando quantos retornos de FII passam a ter valor.
