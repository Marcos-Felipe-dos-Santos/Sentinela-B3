# Detecção de reorganizações societárias (F3-P15, FC2C-61/62)

Levantamento e regra proposta de 12/11/2026. A base são os dados oficiais já guardados no banco único (DFP, FCA e eventos da B3; só leitura) e o cadastro atual da CVM (`data/fontes/cad_cia_aberta.csv`). Não houve rede.

Até o Marcos aprovar a regra no checkpoint da 3-b, nada muda. Continuam valendo o aviso fixo "reorganização societária no período não é detectada" e o critério operacional aprovado: mesmo CNPJ, mesmo modelo de BPP, D20 e contiguidade. A implementação vira item da 3-c ou da Fase 4.

## 1. Fontes medidas

| Fonte | O que traz | Datada? | Cobertura |
|---|---|---|---|
| Eventos em ações da B3 (`eventos_societarios`, complemento da companhia) | Rótulos `INCORPORACAO` (8), `CIS RED CAP` (87), `CIS RED CAP QTD` (2), `REST CAP ACOES` (5), `REST CAP C/ RED` (1), além de desdobramento, grupamento e bonificação | Sim: data com e aprovação | Só companhias listadas hoje (L1 §4) |
| Cadastro da CVM (`MOTIVO_CANCEL`, `DT_CANCEL`) | 666 cancelamentos desde 2010: 63 "elisão por incorporação" e 3 "incorporação" (42 desde 2016) | Sim: data do cancelamento | Só o arquivo atual. Diz quem saiu, mas não quem incorporou |
| FCA, código de negociação × CNPJ (2018 a 2026) | Nenhum código de ação real mudou de CNPJ; só aparecem os marcadores "0000" e "N/A" | Sim: entrega | Só desde a referência de 2018 (F3-P07) |
| Comparativo reapresentado na DFP seguinte (PENÚLTIMO da DFP de Y+1 contra o ÚLTIMO da DFP de Y) | Lucro (3.11 da DRE consolidada) e PL (2.03 do BPP consolidado) | Sim: a entrega da DFP de Y+1 | Todas as companhias com DFP |
| Fatos relevantes do IPE da CVM | Assunto "reorganização", "incorporação" ou "cisão", com a data | Sim | Não carregado: o coletor é o F5-1 da Fase 5 |

O comparativo reapresentado aparece em 4% a 7% dos pares (companhia × conta) a cada ano. A tabela usa diferença acima de 0,5% do valor:

| DFP de Y | Pares | Reapresentados | Lucro | PL | % |
|---|---:|---:|---:|---:|---:|
| 2015 | 615 | 33 | 17 | 16 | 5,4 |
| 2016 | 620 | 32 | 14 | 18 | 5,2 |
| 2017 | 616 | 43 | 17 | 26 | 7,0 |
| 2018 | 620 | 35 | 14 | 21 | 5,6 |
| 2019 | 716 | 46 | 19 | 27 | 6,4 |
| 2020 | 815 | 41 | 21 | 20 | 5,0 |
| 2021 | 865 | 45 | 28 | 17 | 5,2 |
| 2022 | 876 | 56 | 36 | 20 | 6,4 |
| 2023 | 875 | 34 | 19 | 15 | 3,9 |
| 2024 | 839 | 34 | 15 | 19 | 4,1 |

Reapresentação não prova reorganização: pode ser erro, mudança de política contábil ou operação descontinuada. Mas ela é o sinal oficial e datado de que os números de Y deixaram de ser comparáveis com os de Y+1.

## 2. Casos públicos no histórico

- **Grupo de Moda Soma** (CD_CVM 25011): cancelado em 31/07/2024 por incorporação, na combinação com a Arezzo&Co.
- **Enauta Participações** (22365): cancelada em 01/11/2024 por incorporação.
- **Natura &Co Holding** (24783): cancelada em 01/07/2025 por incorporação. É o inverso da reorganização de 2019/2020, quando o código NATU3 deu lugar ao NTCO3, emitido por outro CNPJ.
- **GOL** (19569): cancelada em 01/04/2026.
- Os códigos CVM 24783 e 19569 também estão entre as 19 companhias sem cadastro na B3 no backfill do F3-7b (`docs/decisoes/backfill-fase3.md` §3).

Em todos os casos com novo emissor, o código novo nasce com outro CNPJ. Por isso, o critério "mesmo CNPJ" já corta a série da companhia nova: a reorganização não passa despercebida pelo CNPJ. O que escapa é a incorporação recebida pelo mesmo CNPJ (a incorporadora), que muda o perímetro sem mudar o CNPJ. É o caso da **Azzas 2154** (ex-Arezzo&Co, 16.590.234/0001-76), que incorporou a Soma em 2024:
- o código passou de ARZZ3 (FCA de 2023) para AZZA3 (FCA de 2024), com o mesmo CNPJ;
- o PL consolidado foi de 2,93 bilhões (DFP de 2023) para 7,72 bilhões (DFP de 2024);
- a quantidade de ações na Composição do Capital foi de 110.989.206 para 206.489.813;
- o comparativo da DFP de 2024 repete os números de 2023 sem reapresentação, e a B3 não tem evento da companhia guardado.

Nesse caso, os critérios 1 e 2 abaixo não detectam nada. Só a variação da quantidade de ações detecta (critério 4).

## 3. Regra proposta (para aprovação)

Para uma janela de cinco exercícios ou de TTM com o mesmo CNPJ, mesmo modelo de BPP e D20 (critério atual), a regra proposta marca **ruptura** quando, num documento entregue antes de D, ocorrer:

1. **Evento da B3:** `INCORPORACAO`, `CIS RED CAP`, `CIS RED CAP QTD`, `REST CAP ACOES` ou `REST CAP C/ RED`, da companhia, com data com dentro da janela (vale só para listadas hoje);
2. **Reapresentação:** o comparativo reapresentado do lucro (3.11) ou do PL (2.03) difere do ÚLTIMO do ano anterior em mais que a tolerância de arredondamento. O limiar fica para o Marcos; os 0,5% acima servem só de medida;
3. **Fato relevante do IPE** com assunto de reorganização, incorporação ou cisão, quando o F5-1 existir;
4. **Ações emitidas sem evento:** a quantidade de ações da Composição do Capital, entre dois documentos entregues antes de D, varia além do que explicam os fatores da B3 (desdobramento, grupamento e bonificação, com data com entre os dois), com a escala do documento resolvida (`acoes_cvm.inferir_escala`). Limiar a decidir: 2022 contra 2021 na Azzas, com 99.631 contra 110.186.077, é mudança de escala, não de quantidade.

Os efeitos propostos são estes:
- Com ruptura pelos critérios 1, 3 ou 4, a janela é cortada na ruptura. A série antes dela não entra, e a lente que precisa da janela se abstém, com o motivo "reorganização societária no período".
- Com ruptura só pelo critério 2, a reconciliação usa o comparativo reapresentado, que é o número que a própria companhia declara comparável, entregue antes de D. No modo estrito do leitor (F3-3c: só documentos entregues antes de D), se a DFP com o comparativo reapresentado ainda não tinha sido entregue em D, nada se sabe da reapresentação, e a regra não se aplica naquele D. Se foi entregue e o comparativo não puder ser lido, a lente se abstém. O aviso passa de fixo a específico ("comparativo reapresentado em <data>").
- Sem nenhum critério, o aviso fixo continua, porque a ausência de sinal não prova a ausência de reorganização (pelo cadastro, a incorporação recebida não é atribuível).

As regras 2 e 4 usam dados que já estão no banco. A regra 1 depende da relação da B3, que só cobre as listadas hoje. A regra 3 depende do F5-1.
