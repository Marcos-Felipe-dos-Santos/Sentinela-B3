# Ficha do backtest ponto-no-tempo (F3-F1)

**Status:** proposta para aprovação do Marcos (`[DECISÃO] Ficha do backtest aprovada`, depois da auditoria FICHA pela família Codex). Nada desta ficha vira código antes da aprovação. A ficha detalha o pacote §6 (`docs/decisoes/decisoes-fase3.md`) e as decisões 6, 7 e 17 de 09/11 sem mudá-las, e fixa os números (D21).

## 1. O que o backtest é e o que não é

- **É** uma descrição educacional do passado, **por lente** (Graham, Bazin, Lynch, Gordon, Bancos e FII), de como os ativos com maior e menor distância entre o valor da lente e o preço se comportaram depois. Não existe score nem classificação agregada.
- **Não é** estratégia, carteira, indicação de ativo, ranking de compra ou previsão. Os quintis descrevem o passado. Nenhuma tela, relatório ou texto pode apresentá-los como sugestão, alocação ou "melhores ativos".
- **Sem otimização sobre o resultado:** as lentes entram como aprovadas, com as versões vigentes, e nenhum parâmetro de lente é ajustado pelo backtest.

## 2. Dados e modo

- **Histórico estrito** (D17, adendo de 09/11, decisão 40): em cada data D, só o que foi publicado antes do dia de D (`DT_RECEB`, `Data_Entrega`, pregão, aprovação dos proventos) chega à lente, pelo `AnalysisService.analisar(ticker, as_of=D)` do F3-3d com o motor histórico. É o histórico que alimenta o **backtest principal**.
- **Modo exploratório**, se for rodado, sai em relatório separado e rotulado ("possível reapresentação posterior não observável"). Nunca se mistura ao estrito: nem na mesma série, nem no mesmo quintil, nem no mesmo gráfico.
- **Período:**
  - **Ações e units:** de D0 = último pregão do primeiro mês completo depois da primeira entrega do FCA com código de negociação (primeiro semestre de 2018, DD-60) até o último mês completo antes da execução. **Ponto de decisão na aprovação da ficha:** a decisão 4 previa a primeira análise de ação em 2016, mas o FCA aberto não tem código de negociação antes da referência de 2018 (F3-P07). A ficha propõe o início em 2018 para ações. As alternativas (b) e (c) do estudo F3-P07 §4 dependem do Marcos.
  - **FII:** de D0 = 13 meses depois do início do Informe aberto (decisão 4, primeiro ano do Informe mais 13 meses), ou seja, o fim de fevereiro de 2017.
- **Datas de rebalanceamento:** o último pregão de cada mês, pelo calendário guardado em `precos` (DD-36).

## 3. Universo e elegibilidade em cada D

1. Universo ponto-no-tempo em D (`universo.universo_backtest`, F3-5): ações, units e FIIs listados em D, incluindo os que depois foram deslistados, com o filtro de liquidez da própria data. A liquidez segue a regra vigente: nos 63 pregões, presença de pelo menos 80% e volume mediano diário de pelo menos R$ 500 mil para ações e units, ou R$ 100 mil para FII.
2. Para cada lente, entram só os ativos em que a lente devolve **valor** em D, com a distância ao preço da apresentação 1.0: `distância = 100 × (valor / preço − 1)`.
3. **Abstenções:** o ativo em que a lente se abstém fica fora dos quintis daquela lente e daquela data. O relatório conta as abstenções por motivo em cada D. Abstenção nunca vira distância zero.
4. **Preço em D:** o fechamento bruto do último pregão antes do dia de D, o mesmo que a lente usou.

## 4. Quintis

- Para cada lente e cada D, os elegíveis são ordenados pela distância, da maior para a menor. **Q1** reúne as maiores distâncias, com o preço mais abaixo do valor da lente; **Q5**, as menores.
- **Cortes:** com n elegíveis, o ativo de posição i (1 a n) vai para o quintil `ceil(5 × i / n)`. Os quintis ficam com tamanhos que diferem em no máximo 1.
- **Empates de distância:** a ordem entre empatados é pelo código de negociação, em ordem alfabética, para ser reprodutível. Se um empate atravessa um corte, o relatório informa quantos empates atravessaram.
- **Poucos ativos:** com **menos de 25 elegíveis** (5 por quintil), a lente não forma quintis naquela data. O relatório mostra só a contagem, a mediana do retorno dos elegíveis e o motivo "menos de 25 ativos elegíveis".
- Os pesos dentro do quintil são **iguais**. Não há ponderação por valor de mercado nem por liquidez.

## 5. Retorno total (decisão 6)

- **Bruto, antes de impostos.** Os proventos em dinheiro (dividendos e JCP brutos, da tabela `proventos`, F3-7a) são **reinvestidos no próprio ativo na data ex**, ao fechamento da data ex na série ajustada só por eventos em ações (F3-4c). Essa série não desconta proventos, o que evita a contagem dupla. Assim, o provento por ação dividido por esse fechamento dá a fração de ação comprada.
- **Preço:** a série ajustada por eventos em ações do F3-4c (desdobramentos, grupamentos e bonificações, com os fatores oficiais da B3). O retorno de preço vem dela, e o múltiplo usa o bruto (armadilha 11).
- **Horizontes:** 12, 24 e 36 meses depois de D, até o último pregão do mês de D mais h.
- **Deslistagem:** o ativo vale o último preço negociado, mais os proventos com data ex até ali. Daí até o fim do horizonte, o valor rende CDI. Como **contexto descritivo**, sem mudar a regra, o relatório separa as deslistadas pelo motivo (OPA, falência ou recuperação judicial, cancelamento voluntário), quando o motivo estiver no cadastro da CVM.
- **Suspensão sem deslistagem:** o ativo fica com o último preço até voltar a negociar. O relatório conta esses casos.
- **Retorno do quintil:** a média simples dos retornos totais dos ativos do quintil, com pesos iguais na data D.

## 6. Benchmarks (decisão 7)

- **Ibovespa:** a série histórica oficial da B3 (`benchmarks`, série `IBOV`, F3-7a), no fechamento do último pregão do mês. É índice de retorno total, coerente com o JCP bruto.
- **CDI:** a série SGS 12, capitalizada dia a dia na convenção do Fator DI (DD-55): as taxas do fechamento anterior, inclusive, ao fechamento do mês, exclusive. Mês sem a taxa de algum pregão fica sem fator, com motivo (`b3_indices.mensal`).
- Os dois ficam alinhados no último pregão do mês (DD-36). Em cada D e horizonte, o relatório mostra o retorno do Ibovespa e do CDI no mesmo período do quintil.

## 7. O que o relatório mostra

Por lente, horizonte e modo (estrito; exploratório à parte, se rodado), mostra:
- **por quintil:**
  - a mediana, o primeiro e o terceiro quartis e a média do retorno total entre as datas D;
  - a fração de datas em que o quintil superou o Ibovespa e a fração em que superou o CDI. O denominador são as datas com o quintil formado e o benchmark com fator no horizonte; as datas sem fator do CDI saem, e o relatório diz quantas;
- **número de ativos:** por quintil e por data (mínimo, mediana e máximo) e quantas datas formaram quintis;
- **dispersão:** o intervalo interquartil do retorno dentro de cada quintil, na mediana das datas;
- **efeito das deslistadas:** o retorno com e sem os ativos deslistados no horizonte, e a contagem por motivo;
- **abstenções por motivo** e cobertura da lente: a fração do universo elegível com valor;
- a diferença Q1 − Q5, **como descrição**, nunca como "retorno de estratégia".

Nenhum título, legenda ou rótulo do relatório chama um quintil de "melhores ativos", "oportunidade", "carteira" ou equivalente. Os quintis são nomeados só pela posição (Q1 a Q5) e pela regra de ordenação.

Nenhum número sai sem a contagem de observações ao lado.

## 8. Janela final e observações incompletas

- Uma observação (lente, ativo, D) só entra no horizonte h se D mais h meses for anterior ou igual ao último pregão guardado. Sem isso, a observação fica fora **daquele** horizonte e entra nos outros que couberem.
- O relatório informa, por horizonte, a última data D com horizonte completo.

## 9. Calibração e banda neutra (decisão 17)

- O backtest descreve, não calibra.
- A banda neutra (F3-8d) usa só a **primeira metade** das datas D, com a segunda como validação fora da amostra.
- A fronteira é a data D do meio da série de datas em que a lente formou quintis. Com n datas, ela é a de posição `ceil(n / 2)`, e a primeira metade vai até ela, inclusive.
- Fica fora da calibração toda observação cujo horizonte (12, 24 ou 36 meses, **cada um separadamente**) termine depois da fronteira.
- O resultado é só **proposta** para o Marcos.

## 10. Casos de teste independentes (D28)

O F3-8a escreve os testes antes do código, com números calculados à mão, sem chamar o código do backtest:

1. **Quintis:** 25 ativos com distâncias distintas vão para 5 quintis de 5. 27 ativos ficam com tamanhos 5/5/6/5/6 pela fórmula `ceil(5 × i / n)`. Um empate no corte entre Q1 e Q2 é resolvido pelo código.
2. **Menos de 25 elegíveis:** sem quintis, com o motivo.
3. **Retorno total com JCP:** preço 10, JCP bruto 0,50 com data ex no mês 3 e preço ajustado de 9,80 na data ex. O reinvestimento compra 0,05102 de ação, e o retorno de 12 meses com o preço final de 11 é calculado à mão.
4. **Desdobramento 1:2 no horizonte:** o retorno pela série ajustada é igual ao do bruto corrigido pelo fator.
5. **Deslistagem no mês 7:** o último preço, depois o CDI dos meses 7 a 12 pela convenção do Fator DI, calculado à mão.
6. **CDI com um pregão sem taxa:** o mês fica sem fator e a observação sai do horizonte, com motivo.
7. **Janela final:** uma observação com 12 meses completos e 24 incompletos entra só em 12.
8. **Estrito e exploratório:** a mesma data, com uma reapresentação posterior, dá quintis diferentes nos dois modos, e o relatório os separa.
9. **Fronteira da calibração:** uma observação de 24 meses que termina depois da fronteira fica fora, e a de 12 meses da mesma data fica dentro.

## 11. O que ainda impede números (registrado em `docs/loop/pendencias.md`)

Antes do F3-8b dar números, precisam estar ligados no histórico:
- o DY, para FII e Lynch;
- a montagem do Bazin pelo preço do COTAHIST;
- o IPCA de fim de exercício pelo `series_macro`, para Graham e Lynch;
- a taxa real com as séries carregadas, para Gordon e Bancos.

O backtest roda com as lentes que tiverem valor e informa a cobertura de cada uma. Uma lente sem valor em nenhuma data aparece como "sem observações", com os motivos.
