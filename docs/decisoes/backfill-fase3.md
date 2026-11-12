# Backfill da Fase 3 (F3-7b)

Execução de `scripts/backfill_fase3.py` sobre o banco único `sentinela_store.db`, em 12/11/2026, das 18:45:45 às 19:58:04 UTC, com intervalo 2010–2026 (decisão 4 e parada 2). Antes de migrar, o script conferiu o backup verificado `outputs/f3-7b-backup/20261112T184534755157Z/backup.json` (política §3, caso 3): as contagens do banco eram as do backup (`analises` 6, `schema_version` 3, demais 0), e a cópia e a restauração conferiram. As migrações 004 a 009 foram aplicadas na mesma execução.

O relatório completo, com URL, bytes e SHA-256 de cada arquivo e o resumo de cada carga, está em `outputs/backfill/relatorio.json`; o estado da retomada, em `outputs/backfill/estado.json`. Os brutos estão em `data/fontes/backfill/` e o banco na raiz; os três ficam fora do git.

## 1. Como o script roda

- **Cargas, na ordem:** FCA, DFP, ITR (desde 2011), Informe de FII (desde 2016) e COTAHIST anual, ano a ano (F3-3b e F3-4a); macro (Tesouro, ANBIMA, Focus, IPCA e Selic, F3-1c); CDI do SGS 12 (F3-7a); Ibovespa da B3 por ano (F3-7a); proventos em dinheiro e eventos em ações da B3 por companhia (F3-7a e F3-4b); listagem do universo (F3-5); cobertura de proventos por ano; espaço.
- **Companhias da B3:** as ações e units do índice atual com código CVM (342), porque a B3 só devolve cadastro e relação de listadas hoje (L1 §4, DD-35).
- **Retomável e idempotente:** cada etapa concluída entra em `estado.json` e não roda de novo; a falha fica fora do estado e é tentada na execução seguinte. Cada etapa roda num `SAVEPOINT`, e a falha desfaz o que ela gravou (a do macro não: `gravar_series` grava cada família na própria transação). Arquivo da CVM lido sem nenhuma linha gravada e com recusas faz a etapa falhar e desfaz o registro do arquivo (`ArquivoRecusado`), para a próxima execução carregar de novo; essa regra e o `SAVEPOINT` por etapa entraram depois da execução real, na revisão (as 19 falhas da execução foram em `coletar`, antes de qualquer gravação), e as etapas `FII_INFORME:2016` a `2020` ficaram marcadas no `estado.json` (o F3-3b-fix as retira). As cargas já são idempotentes pelo hash do arquivo (`ja_carregado`) ou pela chave (`repetidas`).
- **Ritmo (decisão 38):** um pedido por vez, com 2 s de pausa entre os downloads da CVM e da B3; os pedidos do macro e do CDI (`MacroProvider`) saem sem pausa própria, um por vez.
- **Volume (decisão 39):** depois de cada etapa executada, o script mede os brutos e para acima de 100 GB (`VolumeExcedido`), antes da etapa seguinte.
- **Banco com dados:** só migra com o `backup.json` verificado do mesmo arquivo, com as contagens atuais iguais às do backup; banco vazio ou ausente migra sem backup.
- **Resultados de análise:** o item não produz nenhum (decisão 16): `analises` continua com 6 linhas e `resultados_analise` com 0.

## 2. Resultado por fonte e ano

441 etapas e o registro do espaço, 19 falhas (todas de proventos, seção 3, item 5). Linhas gravadas são as novas no banco; repetidas são chaves já gravadas com os mesmos dados; conflitos são chaves já gravadas com dados diferentes (a carga mantém a primeira, BUG-3-26); recusadas são linhas fora do leiaute, com o motivo no relatório.

| Etapa | Arquivo | SHA-256 (16) | Bytes | Linhas gravadas | Repetidas | Conflitos | Recusadas |
|---|---|---|---:|---:|---:|---:|---:|
| FCA:2010 | fca_cia_aberta_2010.zip | `9a9b933fa02c96f7` | 337.720 | 7.395 | 8 | 0 | 0 |
| FCA:2011 | fca_cia_aberta_2011.zip | `f5c7aaa2a4464b42` | 381.161 | 8.634 | 71 | 0 | 0 |
| FCA:2012 | fca_cia_aberta_2012.zip | `ba68b8e8c12b74fc` | 381.058 | 8.701 | 30 | 0 | 0 |
| FCA:2013 | fca_cia_aberta_2013.zip | `d62ef489d8c1208e` | 373.007 | 8.324 | 18 | 0 | 0 |
| FCA:2014 | fca_cia_aberta_2014.zip | `1f70b5e3a544535a` | 384.748 | 8.774 | 8 | 0 | 0 |
| FCA:2015 | fca_cia_aberta_2015.zip | `74326a566c405d70` | 380.898 | 8.422 | 8 | 0 | 0 |
| FCA:2016 | fca_cia_aberta_2016.zip | `229b2cfc8c0ac5e6` | 376.154 | 8.166 | 6 | 0 | 0 |
| FCA:2017 | fca_cia_aberta_2017.zip | `48127cf15d8baf4d` | 375.132 | 8.186 | 12 | 0 | 0 |
| FCA:2018 | fca_cia_aberta_2018.zip | `b20056b00927c526` | 381.642 | 8.212 | 6 | 0 | 0 |
| FCA:2019 | fca_cia_aberta_2019.zip | `09f84e5f5485217c` | 371.770 | 7.965 | 8 | 0 | 0 |
| FCA:2020 | fca_cia_aberta_2020.zip | `ccf2ac081747da9c` | 405.892 | 8.595 | 11 | 1 | 0 |
| FCA:2021 | fca_cia_aberta_2021.zip | `65ba4b0225e9b210` | 465.704 | 10.008 | 150 | 1 | 0 |
| FCA:2022 | fca_cia_aberta_2022.zip | `c30912a49163e545` | 458.295 | 9.575 | 61 | 1 | 0 |
| FCA:2023 | fca_cia_aberta_2023.zip | `04364dea9a0bfca8` | 434.052 | 8.999 | 57 | 6 | 0 |
| FCA:2024 | fca_cia_aberta_2024.zip | `469bccc738b4e71f` | 391.984 | 8.592 | 21 | 6 | 0 |
| FCA:2025 | fca_cia_aberta_2025.zip | `62877519e3543a56` | 383.613 | 8.477 | 31 | 0 | 0 |
| FCA:2026 | fca_cia_aberta_2026.zip | `b24da0981f891532` | 363.925 | 7.970 | 19 | 2 | 0 |
| DFP:2010 | dfp_cia_aberta_2010.zip | `c6a9c95c2510e8a7` | 8.900.829 | 958.700 | 0 | 0 | 0 |
| DFP:2011 | dfp_cia_aberta_2011.zip | `858423fba40124d7` | 9.225.478 | 990.526 | 0 | 0 | 0 |
| DFP:2012 | dfp_cia_aberta_2012.zip | `3aff7a726d324d29` | 9.201.737 | 974.618 | 0 | 0 | 0 |
| DFP:2013 | dfp_cia_aberta_2013.zip | `ef379ac9aab95674` | 9.171.449 | 967.239 | 0 | 0 | 0 |
| DFP:2014 | dfp_cia_aberta_2014.zip | `b8795dba13475447` | 9.079.931 | 960.861 | 0 | 0 | 0 |
| DFP:2015 | dfp_cia_aberta_2015.zip | `39a7001be9eaa91a` | 8.987.623 | 948.151 | 0 | 0 | 0 |
| DFP:2016 | dfp_cia_aberta_2016.zip | `772f06a73c5fe805` | 9.832.691 | 942.229 | 0 | 0 | 0 |
| DFP:2017 | dfp_cia_aberta_2017.zip | `1ff8185d61759e49` | 10.150.935 | 948.104 | 0 | 4 | 0 |
| DFP:2018 | dfp_cia_aberta_2018.zip | `280dcf5acd7bdb52` | 10.237.924 | 949.901 | 4 | 2 | 0 |
| DFP:2019 | dfp_cia_aberta_2019.zip | `bc82a1162b44686e` | 11.185.526 | 1.041.476 | 6 | 2 | 0 |
| DFP:2020 | dfp_cia_aberta_2020.zip | `8fb97d1887aed1e1` | 12.637.854 | 1.174.398 | 0 | 0 | 0 |
| DFP:2021 | dfp_cia_aberta_2021.zip | `64b8693b709538a0` | 13.283.026 | 1.231.072 | 2.395 | 4 | 0 |
| DFP:2022 | dfp_cia_aberta_2022.zip | `151d605dc4c2bbe3` | 13.449.824 | 1.227.359 | 20.613 | 55 | 0 |
| DFP:2023 | dfp_cia_aberta_2023.zip | `344e37b704a588b3` | 13.563.493 | 1.240.870 | 36.614 | 300 | 0 |
| DFP:2024 | dfp_cia_aberta_2024.zip | `b6a485b540728dcd` | 13.397.599 | 1.229.475 | 7.810 | 27 | 0 |
| DFP:2025 | dfp_cia_aberta_2025.zip | `a0aaf1ed8be9f7a6` | 12.863.166 | 1.174.987 | 9.782 | 174 | 0 |
| DFP:2026 | dfp_cia_aberta_2026.zip | `eda1116c24347150` | 243.348 | 19.850 | 0 | 0 | 0 |
| ITR:2011 | itr_cia_aberta_2011.zip | `11f0d8cc47bad618` | 24.581.120 | 2.959.885 | 0 | 0 | 0 |
| ITR:2012 | itr_cia_aberta_2012.zip | `f1d642a1a644e252` | 24.650.791 | 2.939.133 | 48 | 0 | 0 |
| ITR:2013 | itr_cia_aberta_2013.zip | `a336c9d5d5f2e465` | 24.514.311 | 2.915.675 | 0 | 0 | 0 |
| ITR:2014 | itr_cia_aberta_2014.zip | `c10271ea978a7da9` | 24.468.760 | 2.904.162 | 0 | 0 | 0 |
| ITR:2015 | itr_cia_aberta_2015.zip | `2755f06e74668144` | 24.295.580 | 2.889.635 | 0 | 0 | 0 |
| ITR:2016 | itr_cia_aberta_2016.zip | `3c2954a0d7e2c4c1` | 23.803.768 | 2.821.259 | 0 | 0 | 0 |
| ITR:2017 | itr_cia_aberta_2017.zip | `f2e626260461ec4e` | 24.127.956 | 2.848.793 | 1 | 5 | 0 |
| ITR:2018 | itr_cia_aberta_2018.zip | `a551278c83e5c058` | 23.460.448 | 2.691.833 | 4 | 6 | 0 |
| ITR:2019 | itr_cia_aberta_2019.zip | `dbfe1e32296563a9` | 24.435.666 | 2.832.159 | 58 | 12 | 0 |
| ITR:2020 | itr_cia_aberta_2020.zip | `4ca11b431eb21aa9` | 27.151.708 | 3.156.868 | 8 | 0 | 0 |
| ITR:2021 | itr_cia_aberta_2021.zip | `c8723d5ccd4a6e99` | 31.230.595 | 3.634.515 | 1.410 | 146 | 0 |
| ITR:2022 | itr_cia_aberta_2022.zip | `4579fe2476bc0961` | 32.329.025 | 3.739.250 | 2.098 | 8 | 0 |
| ITR:2023 | itr_cia_aberta_2023.zip | `9e6ce6cc2a978ffa` | 32.355.974 | 3.714.133 | 30.528 | 259 | 0 |
| ITR:2024 | itr_cia_aberta_2024.zip | `bdfa4c83bcc2bfac` | 32.725.967 | 3.744.230 | 46.705 | 131 | 0 |
| ITR:2025 | itr_cia_aberta_2025.zip | `d29c6e378b60f61b` | 31.684.923 | 3.633.935 | 6.448 | 6 | 0 |
| ITR:2026 | itr_cia_aberta_2026.zip | `115227a5d0872e23` | 22.183.718 | 2.501.546 | 10.582 | 202 | 0 |
| FII_INFORME:2016 | inf_mensal_fii_2016.zip | `241371adbb927981` | 58.438 | 0 | 0 | 0 | 1.104 |
| FII_INFORME:2017 | inf_mensal_fii_2017.zip | `4d24ef325dce8a53` | 417.184 | 0 | 0 | 0 | 11.148 |
| FII_INFORME:2018 | inf_mensal_fii_2018.zip | `8ecca5956b4cec26` | 480.738 | 0 | 0 | 0 | 12.861 |
| FII_INFORME:2019 | inf_mensal_fii_2019.zip | `ba542efca10362e6` | 566.497 | 0 | 0 | 0 | 14.874 |
| FII_INFORME:2020 | inf_mensal_fii_2020.zip | `aec2dbc88d324d00` | 700.568 | 0 | 0 | 0 | 18.237 |
| FII_INFORME:2021 | inf_mensal_fii_2021.zip | `d7450231a77295b9` | 869.573 | 22.704 | 0 | 0 | 0 |
| FII_INFORME:2022 | inf_mensal_fii_2022.zip | `63bd91c9042e41dc` | 1.033.449 | 26.943 | 0 | 0 | 0 |
| FII_INFORME:2023 | inf_mensal_fii_2023.zip | `954d67545e918ec2` | 1.157.803 | 30.768 | 0 | 0 | 0 |
| FII_INFORME:2024 | inf_mensal_fii_2024.zip | `1238a97aa8462bf2` | 1.346.547 | 35.928 | 0 | 0 | 0 |
| FII_INFORME:2025 | inf_mensal_fii_2025.zip | `0d9a3f50998cf1cc` | 1.522.532 | 41.026 | 8 | 0 | 0 |
| FII_INFORME:2026 | inf_mensal_fii_2026.zip | `eb9dfb6d05f3c71e` | 1.275.147 | 35.355 | 0 | 0 | 0 |
| COTAHIST:2010 | COTAHIST_A2010.ZIP | `65637311ced65ba5` | 10.385.444 | 92.293 | 0 | 0 | 0 |
| COTAHIST:2011 | COTAHIST_A2011.ZIP | `0cf67787cc1b77dd` | 10.856.136 | 96.761 | 0 | 0 | 0 |
| COTAHIST:2012 | COTAHIST_A2012.ZIP | `98771b1248a3f19b` | 11.883.689 | 97.900 | 0 | 0 | 0 |
| COTAHIST:2013 | COTAHIST_A2013.ZIP | `b6dfb0d73181a60c` | 13.300.034 | 104.716 | 0 | 0 | 0 |
| COTAHIST:2014 | COTAHIST_A2014.ZIP | `613d76f8a64c7ffb` | 13.684.612 | 106.589 | 0 | 0 | 0 |
| COTAHIST:2015 | COTAHIST_A2015.ZIP | `593f8740ec1aa87c` | 14.129.467 | 106.028 | 0 | 0 | 0 |
| COTAHIST:2016 | COTAHIST_A2016.ZIP | `ffc82a9b973cb590` | 15.715.361 | 109.435 | 0 | 0 | 0 |
| COTAHIST:2017 | COTAHIST_A2017.ZIP | `af6aaa85187c1d58` | 16.527.191 | 113.926 | 0 | 0 | 0 |
| COTAHIST:2018 | COTAHIST_A2018.ZIP | `9d66136179d98224` | 19.488.404 | 125.626 | 0 | 0 | 0 |
| COTAHIST:2019 | COTAHIST_A2019.ZIP | `5170d3f8f079c330` | 26.650.371 | 136.611 | 0 | 0 | 0 |
| COTAHIST:2020 | COTAHIST_A2020.ZIP | `86442168939b9da7` | 37.181.542 | 187.306 | 0 | 0 | 0 |
| COTAHIST:2021 | COTAHIST_A2021.ZIP | `b0d4aed17d609c7b` | 49.678.679 | 277.399 | 0 | 0 | 0 |
| COTAHIST:2022 | COTAHIST_A2022.ZIP | `a4f9015b755f797d` | 58.597.842 | 308.865 | 0 | 0 | 0 |
| COTAHIST:2023 | COTAHIST_A2023.ZIP | `ad1603788d78aaa1` | 70.216.090 | 307.936 | 0 | 0 | 0 |
| COTAHIST:2024 | COTAHIST_A2024.ZIP | `96a003d10fab0fa2` | 79.261.198 | 322.397 | 0 | 0 | 0 |
| COTAHIST:2025 | COTAHIST_A2025.ZIP | `6cc0ad851c8f605c` | 89.056.788 | 335.874 | 0 | 0 | 0 |
| COTAHIST:2026 | COTAHIST_A2026.ZIP | `dc6ba996a435c3ab` | 93.641.013 | 306.932 | 0 | 0 | 1 |
| IBOV:2010 | GetPortfolioDay 2010 | `67abfcec4edd5135` | 9.501 | 247 | 0 | 0 | 0 |
| IBOV:2011 | GetPortfolioDay 2011 | `0ee4b0a281500798` | 9.515 | 249 | 0 | 0 | 0 |
| IBOV:2012 | GetPortfolioDay 2012 | `fc1da33177002f12` | 9.494 | 246 | 0 | 0 | 0 |
| IBOV:2013 | GetPortfolioDay 2013 | `a28d2b2bc187399a` | 9.508 | 248 | 0 | 0 | 0 |
| IBOV:2014 | GetPortfolioDay 2014 | `94eb978781dc35c1` | 9.508 | 248 | 0 | 0 | 0 |
| IBOV:2015 | GetPortfolioDay 2015 | `7a5c4597859d8cec` | 9.494 | 246 | 0 | 0 | 0 |
| IBOV:2016 | GetPortfolioDay 2016 | `fc74cd50ec269291` | 9.515 | 249 | 0 | 0 | 0 |
| IBOV:2017 | GetPortfolioDay 2017 | `0b3bd3fc375f224d` | 9.494 | 246 | 0 | 0 | 0 |
| IBOV:2018 | GetPortfolioDay 2018 | `157a6d55d632e29b` | 9.487 | 245 | 0 | 0 | 0 |
| IBOV:2019 | GetPortfolioDay 2019 | `5fe2d90a9b62a001` | 9.641 | 248 | 0 | 0 | 0 |
| IBOV:2020 | GetPortfolioDay 2020 | `a26b306ab53cdf35` | 9.657 | 249 | 0 | 0 | 0 |
| IBOV:2021 | GetPortfolioDay 2021 | `4e5fec3ce7061fbb` | 9.772 | 247 | 0 | 0 | 0 |
| IBOV:2022 | GetPortfolioDay 2022 | `1df55bd464f974ca` | 9.771 | 250 | 0 | 0 | 0 |
| IBOV:2023 | GetPortfolioDay 2023 | `a9a88efd866f0327` | 9.776 | 248 | 0 | 0 | 0 |
| IBOV:2024 | GetPortfolioDay 2024 | `9d0de175cbfc6ea9` | 9.804 | 251 | 0 | 0 | 0 |
| IBOV:2025 | GetPortfolioDay 2025 | `9e2783ecd22e78c4` | 9.796 | 250 | 0 | 0 | 0 |
| IBOV:2026 | GetPortfolioDay 2026 | `5ec2fdd51575c812` | 9.496 | 215 | 0 | 0 | 0 |

Outras cargas:

| Etapa | Resultado |
|---|---|
| macro | Tesouro 119.125 linhas, ANBIMA 237, Focus 1.322, IPCA 121, Selic 10.103 |
| cdi | 10.180 taxas diárias do SGS 12 (06/03/1986 a 11/11/2026) |
| universo | 4.681 listagens (`universo`, F3-5) |
| proventos | 323 companhias com coleta: 19.170 proventos, 822 eventos em ações (140 sem fator), 1.115 registros duplicados na mesma coleta |

O Ibovespa ficou com 4.182 fechamentos, de 04/01/2010 a 11/11/2026, de 245 a 251 por ano completo.

## 3. Lacunas e falhas

1. **Informe de FII de 2016 a 2020: nada gravado (BUG-3-25).** Esses anos continuam com a coluna `CNPJ_Fundo`; de 2021 em diante a CVM republicou no leiaute da Resolução 175 (`CNPJ_Fundo_Classe`). A carga recusa cada linha ("CNPJ_Fundo_Classe vazio": 1.104 em 2016, 11.148 em 2017, 12.861 em 2018, 14.874 em 2019 e 18.237 em 2020) e o arquivo fica registrado como carregado. Sem esses anos, nenhum FII entra no universo em D antes de 2021. Destino: F3-3b-fix (DD-56), com nova execução do backfill.
2. **Conflitos da CVM invisíveis ao leitor (BUG-3-26).** 1.360 conflitos (568 nos arquivos da DFP, 775 nos do ITR e 17 nos do FCA; a divisão por tabela só se conhece pelas listas do resumo, cortadas em 100 por arquivo, e seis arquivos passam de 100); nos casos listados, a maioria é de `demonstracoes`, com 3 em `entregas` e 17 em `fca_entregas`. Exemplo: no `dfp_cia_aberta_2025.zip`, a conta 2.02 do BPP consolidado de 20.961.867/0001-10 (`ÚLTIMO`, 31/12/2025) aparece com 2.928.832 e, duas vezes, com 3.088.832; ficou o primeiro, e `leitura.demonstrativo` o devolve sem motivo. Destino: F3-3b-fix (DD-57: o documento fica fora, com motivo).
3. **COTAHIST de 2026:** uma linha recusada (1.951.926, `abertura_centavos` com espaço). Os 17 arquivos têm o ano do cabeçalho (`COTAHIST.{ano}`) igual ao do nome.
4. **Versões preservadas:** FCA de 2022, DFP de 2021 e Informe de 2021 e 2025 trazem mais de uma versão de algum documento (`so_ultima_versao` falso); nos demais, só a última, como o L1 mediu.
5. **Proventos:** 19 companhias do índice sem nome de pregão ou código de emissor no cadastro da B3 (`ValueError`; códigos CVM 3158, 6076, 8540, 8893, 11231, 11312, 19569, 20966, 21199, 21326, 22500, 22985, 24783, 25399, 25569, 25720, 25933, 26093 e 26247). Ficam fora do estado; a próxima execução tenta de novo.

## 4. Cobertura de proventos (DD-35)

Companhias do FCA provado no fim de cada ano (`universo.companhias_em`), quantas têm coleta de proventos da B3 e quantas têm a identidade do emissor conferida (decisão 33). Conta a coleta mais recente de cada emissor; só a conferida é lida por `proventos_ate`, que também exige a relação completa (total declarado igual aos registros), e nas outras as lentes de proventos se abstêm com o motivo. **A coluna é um teto:** todas as coletas são de 12/11/2026, e `proventos_ate` só lê coleta feita antes do dia de D; para qualquer D até 12/11/2026 a leitura devolve "sem coleta", e a cobertura lida hoje para 2010 a 2025 é zero. O uso de uma coleta posterior a D para a relação histórica é a decisão pendente do F3-3d (pendência do F3-7a).

| Ano (dia) | Companhias com FCA provado | `sem_prova` no FCA | Com coleta de proventos | Com identidade conferida | % conferida |
|---|---:|---:|---:|---:|---:|
| 2010 (31/12) | 388 | 102 | 204 | 75 | 19,3% |
| 2011 (31/12) | 341 | 258 | 176 | 67 | 19,6% |
| 2012 (31/12) | 318 | 318 | 158 | 59 | 18,6% |
| 2013 (31/12) | 297 | 380 | 147 | 60 | 20,2% |
| 2014 (31/12) | 398 | 189 | 205 | 84 | 21,1% |
| 2015 (31/12) | 401 | 191 | 210 | 87 | 21,7% |
| 2016 (31/12) | 405 | 208 | 212 | 87 | 21,5% |
| 2017 (31/12) | 411 | 225 | 217 | 87 | 21,2% |
| 2018 (31/12) | 393 | 284 | 208 | 85 | 21,6% |
| 2019 (31/12) | 380 | 316 | 202 | 89 | 23,4% |
| 2020 (31/12) | 396 | 350 | 212 | 89 | 22,5% |
| 2021 (31/12) | 374 | 456 | 195 | 84 | 22,5% |
| 2022 (31/12) | 505 | 255 | 300 | 133 | 26,3% |
| 2023 (31/12) | 500 | 249 | 300 | 133 | 26,6% |
| 2024 (31/12) | 501 | 257 | 307 | 135 | 26,9% |
| 2025 (31/12) | 505 | 252 | 315 | 137 | 27,1% |
| 2026 (12/11) | 502 | 241 | 316 | 138 | 27,5% |

Das 323 companhias com coleta, 185 têm a identidade não comprovada: 98 por "complemento sem proventos para conferir", 43 por espécie PN sem ISIN da companhia no `GetDetail`, 9 por UNT, 7 por PNA, 7 por `GetDetail` sem ISIN e o resto por outras espécies. A diferença entre "companhias" e "com coleta" são as deslistadas e as companhias com registro sem ação listada hoje (DD-35).

A coluna `sem_prova` veio de consulta avulsa a `universo.companhias_em` no banco (só leitura), fora do relatório do script. **`sem_prova`** são as companhias cuja versão vigente do FCA em D foi entregue sem conteúdo no arquivo aberto (a CVM só guarda a última versão: DD-34 e DD-53); ficam fora do universo estrito naquele dia. O salto de 2021 (374) para 2022 (505) vem daí: as versões com valores das referências de 2021 saíram em 2022.

## 5. Espaço

| Medida | Bytes | Projeção do L1 |
|---|---:|---:|
| Brutos (`data/fontes/backfill/`) | 1.266.475.352 (1,27 GB) | 1.263.635.166 (1,26 GB) |
| Banco (`sentinela_store.db`, com WAL e SHM) | 32.413.622.272 (32,4 GB) | 17.960.314.332 com os brutos (18,0 GB) |

Os brutos ficaram na projeção e muito abaixo de 100 GB (decisão 39); o banco ficou cerca de 1,9 vez acima da projeção do L1 só para o banco (18,0 GB menos 1,26 GB de brutos, 16,7 GB), que subestimou as demonstrações (ITR com 2,5 a 3,7 milhões de linhas por ano). O disco tem 903 GB livres.

## 6. Como repetir

```bash
python -m sentinela.data.store.backup outputs/<pasta> sentinela_store.db      # backup verificado
python scripts/backfill_fase3.py --banco sentinela_store.db --backup outputs/<pasta>/<carimbo>/backup.json
```

Com o banco já carregado, o backup é obrigatório. A execução só refaz as etapas fora do `estado.json`.
