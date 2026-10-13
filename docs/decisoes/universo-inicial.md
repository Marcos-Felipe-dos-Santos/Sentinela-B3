# Universo inicial

**Status:** aprovado pelo Marcos em 13/10/2026, com as decisões da seção final (sucessores, classes do Banrisul, critério de "atual" e BTG). Auditoria externa de 13/10/2026: `docs/loop/historico/fase-2a/auditoria-ficha-por-acao.md`, seção 4.
**Origem:** ADR-0003, D32 · item F2A-35 de `docs/loop/fila.md`

Só ativos de mapas públicos do código (`cvm_ticker_map.py`, `cvm_fii_map.py`) e do índice oficial do F2A-1; nada vem da carteira.

## Fontes desta lista

- **Classe:** índice oficial do F2A-1 (`indice.json`, gerado em 8/10/2026 a partir do FCA 2025 e 2026, do cadastro de companhias, do Informe Mensal de FII 2025 e 2026 e do COTAHIST de jul–set/2026).
- **CNPJ:** do índice; para as ações fora dele, do cadastro de companhias da CVM (`cad_cia_aberta.csv`, cópia de 8/10/2026) pelo código CVM do mapa; para os FIIs fora dele (BCFF11, IRDM11, RBRF11), de `cvm_fii_map.py`.
- **Tipo de FII:** composição da carteira no `inf_mensal_fii_ativo_passivo` de agosto de 2026, como fração da soma de recebíveis (CRI/CRA, LCI/LCA, letras hipotecárias e LIG: "papel"), de imóveis, terrenos, direitos reais e participações em sociedades imobiliárias ("tijolo") e de cotas de outros FIIs ("fundo de fundos"); o tipo é o que passa de 50%. A base não inclui caixa nem renda fixa: num fundo com muito caixa, as frações descrevem só a parte investida em ativos imobiliários. O `Mandato` do Informe vem vazio nos 27 fundos com Informe Mensal de agosto de 2026 (BCFF11, IRDM11 e RBRF11 não têm Informe de 2026).
- **Situação** (critério operacional do universo inicial, aprovado pelo Marcos em 13/10/2026; **não** é o denominador da cobertura da D32, que segue abaixo). Vale para ações, units e FIIs; a auditoria externa conferiu os 73 atuais da versão anterior. "atual" = ticker presente no índice, fora da lista de casos históricos da D32 e com pelo menos 100 negócios no mercado à vista no COTAHIST de jul–set/2026 (as ações entram no índice pelo FCA, sem exigir negociação; os FIIs, pelo Informe e pelo COTAHIST); "histórico" = fora do índice, sem negócio no período, ou um dos cinco FIIs que `docs/decisoes/fontes-fase2a.md` (seção 7) registra fora da listagem em bolsa no período (BCFF11, CVBI11, IRDM11, MALL11 e RBRF11). Os históricos servem para testar abstenção e histórico estrito e não contam no denominador atual.

### Ações do mapa (45)

| Ticker | CNPJ | Classe (índice) | Motivo | Situação |
|---|---|---|---|---|
| ABEV3 | 07.526.557/0001-00 | STOCK | mapa regenerado no F1-15 | atual |
| ASAI3 | 06.057.223/0001-71 | STOCK | mapa regenerado no F1-15 | atual |
| AZUL4 | 09.305.994/0001-29 | fora do índice | mapa regenerado no F1-15; AZUL S.A. (09.305.994/0001-29, ativa); o índice traz AZUL3 no lugar de AZUL4 | histórico |
| B3SA3 | 09.346.601/0001-25 | STOCK | mapa regenerado no F1-15 | atual |
| BBAS3 | 00.000.000/0001-91 | STOCK | mapa regenerado no F1-15; caso difícil: banco (F2A-16) | atual |
| BBDC4 | 60.746.948/0001-12 | STOCK | mapa regenerado no F1-15; caso difícil: banco (F2A-16) | atual |
| BEEF3 | 67.620.377/0001-14 | STOCK | mapa regenerado no F1-15 | atual |
| BRML3 | 06.977.745/0001-91 | STOCK | mapa regenerado no F1-15; BR Malls na Categoria B desde 2/2/2023 (cadastro), sem negócio no COTAHIST de jul–set/2026 | histórico |
| CMIG4 | 17.155.730/0001-64 | STOCK | mapa regenerado no F1-15 | atual |
| COGN3 | 02.800.026/0001-40 | STOCK | mapa regenerado no F1-15 | atual |
| CSAN3 | 50.746.577/0001-15 | STOCK | mapa regenerado no F1-15; caso difícil: holding com minoritários relevantes | atual |
| CYRE3 | 73.178.600/0001-18 | STOCK | mapa regenerado no F1-15 | atual |
| DESK3 | 08.170.849/0001-15 | STOCK | mapa regenerado no F1-15 | atual |
| ELET3 | 00.001.180/0001-26 | fora do índice | mapa regenerado no F1-15; AXIA ENERGIA S.A., antiga Eletrobras (00.001.180/0001-26, ativa); o índice traz AXIA3 e AXIA7 | histórico |
| ENEV3 | 04.423.567/0001-21 | STOCK | mapa regenerado no F1-15 | atual |
| EQTL3 | 03.220.438/0001-73 | STOCK | mapa regenerado no F1-15 | atual |
| GGBR4 | 33.611.500/0001-19 | STOCK | mapa regenerado no F1-15 | atual |
| GOAU4 | 92.690.783/0001-09 | STOCK | mapa regenerado no F1-15 | atual |
| GOLL4 | 06.164.253/0001-87 | fora do índice | mapa regenerado no F1-15; GOL (06.164.253/0001-87): registro cancelado em 2026-04-01 no cadastro; o índice traz GOLL54 | histórico |
| HAPV3 | 05.197.443/0001-38 | STOCK | mapa regenerado no F1-15 | atual |
| HYPE3 | 02.932.074/0001-91 | STOCK | mapa regenerado no F1-15 | atual |
| ITUB4 | 60.872.504/0001-23 | STOCK | mapa regenerado no F1-15; caso difícil: banco (F2A-16) | atual |
| JBSS3 | 02.916.265/0001-60 | fora do índice | mapa regenerado no F1-15; JBS SA (02.916.265/0001-60, ativa no cadastro); nenhuma ação dela no índice | histórico |
| KLBN11 | 89.637.490/0001-45 | UNIT | mapa regenerado no F1-15; caso difícil: unit do índice | atual |
| LREN3 | 92.754.738/0001-62 | STOCK | mapa regenerado no F1-15 | atual |
| LWSA3 | 02.351.877/0001-52 | STOCK | mapa regenerado no F1-15 | atual |
| MGLU3 | 47.960.950/0001-21 | STOCK | mapa regenerado no F1-15 | atual |
| MRVE3 | 08.343.492/0001-20 | STOCK | mapa regenerado no F1-15; caso difícil: DFP reapresentada (F2A-32) | atual |
| NTCO3 | 32.785.497/0001-97 | STOCK (só no FCA 2025) | mapa regenerado no F1-15; Natura &Co Holding com registro cancelado em 1/7/2025 por incorporação (cadastro), sem negócio no COTAHIST de jul–set/2026; a NATU3 (71.673.990/0001-77) está no índice | histórico |
| PETR4 | 33.000.167/0001-01 | STOCK | mapa regenerado no F1-15 | atual |
| PETZ3 | 18.328.118/0001-09 | fora do índice | mapa regenerado no F1-15; Pet Center (18.328.118/0001-09): registro cancelado em 2026-05-14 no cadastro | histórico |
| QUAL3 | 11.992.680/0001-93 | STOCK | mapa regenerado no F1-15 | atual |
| RADL3 | 61.585.865/0001-51 | STOCK | mapa regenerado no F1-15 | atual |
| RAIL3 | 02.387.241/0001-60 | STOCK | mapa regenerado no F1-15 | atual |
| RECV3 | 03.342.704/0001-30 | STOCK | mapa regenerado no F1-15 | atual |
| RENT3 | 16.670.085/0001-55 | STOCK | mapa regenerado no F1-15 | atual |
| SBSP3 | 43.776.517/0001-80 | STOCK | mapa regenerado no F1-15 | atual |
| SLCE3 | 89.096.457/0001-55 | STOCK | mapa regenerado no F1-15 | atual |
| SUZB3 | 16.404.287/0001-55 | STOCK | mapa regenerado no F1-15 | atual |
| TIMS3 | 02.421.421/0001-11 | STOCK | mapa regenerado no F1-15 | atual |
| TOTS3 | 53.113.791/0001-22 | STOCK | mapa regenerado no F1-15 | atual |
| USIM5 | 60.894.730/0001-05 | STOCK | mapa regenerado no F1-15 | atual |
| VALE3 | 33.592.510/0001-54 | STOCK | mapa regenerado no F1-15 | atual |
| VIVT3 | 02.558.157/0001-62 | STOCK | mapa regenerado no F1-15 | atual |
| WEGE3 | 84.429.695/0001-11 | STOCK | mapa regenerado no F1-15 | atual |

### FIIs do mapa (30)

| Ticker | CNPJ | Classe (índice) | Tipo pela carteira (Informe Mensal de ago/2026) | Situação |
|---|---|---|---|---|
| ALZR11 | 28.737.771/0001-85 | FII | tijolo (recebíveis 0%, imóveis 82%, cotas de FII 18%) | atual |
| BCFF11 | 11.026.627/0001-38 | fora do índice | sem Informe Mensal de 2026 | histórico |
| BRCR11 | 08.924.783/0001-01 | FII | tijolo (recebíveis 0%, imóveis 91%, cotas de FII 9%) | atual |
| BTLG11 | 11.839.593/0001-09 | FII | tijolo (recebíveis 2%, imóveis 93%, cotas de FII 5%) | atual |
| CPTS11 | 18.979.895/0001-13 | FII | fundo de fundos (recebíveis 23%, imóveis 0%, cotas de FII 77%) | atual |
| CVBI11 | 28.729.197/0001-13 | FII | papel (recebíveis 79%, imóveis 0%, cotas de FII 21%) | histórico |
| GTWR11 | 23.740.527/0001-58 | FII | tijolo (recebíveis 0%, imóveis 100%, cotas de FII 0%) | atual |
| HCTR11 | 30.248.180/0001-96 | FII | papel (recebíveis 93%, imóveis 0%, cotas de FII 7%) | atual |
| HFOF11 | 18.307.582/0001-19 | FII | fundo de fundos (recebíveis 0%, imóveis 0%, cotas de FII 100%) | atual |
| HGBS11 | 08.431.747/0001-06 | FII | tijolo (recebíveis 1%, imóveis 84%, cotas de FII 15%) | atual |
| HGLG11 | 11.728.688/0001-47 | FII | tijolo (recebíveis 0%, imóveis 99%, cotas de FII 1%) | atual |
| HGRU11 | 29.641.226/0001-53 | FII | tijolo (recebíveis 1%, imóveis 95%, cotas de FII 4%) | atual |
| HSML11 | 32.892.018/0001-31 | FII | tijolo (recebíveis 0%, imóveis 98%, cotas de FII 2%) | atual |
| IRDM11 | 28.830.325/0001-10 | fora do índice | sem Informe Mensal de 2026 | histórico |
| JSRE11 | 13.371.132/0001-71 | FII | tijolo (recebíveis 0%, imóveis 89%, cotas de FII 11%) | atual |
| KNCR11 | 16.706.958/0001-32 | FII | papel (recebíveis 93%, imóveis 0%, cotas de FII 7%) | atual |
| KNRI11 | 12.005.956/0001-65 | FII | tijolo (recebíveis 4%, imóveis 96%, cotas de FII 0%) | atual |
| MALL11 | 26.499.833/0001-32 | FII | tijolo (recebíveis 0%, imóveis 85%, cotas de FII 15%) | histórico |
| MXRF11 | 97.521.225/0001-25 | FII | papel (recebíveis 74%, imóveis 13%, cotas de FII 13%) | atual |
| PVBI11 | 35.652.102/0001-76 | FII | tijolo (recebíveis 0%, imóveis 91%, cotas de FII 9%) | atual |
| RBRF11 | 27.529.279/0001-51 | fora do índice | sem Informe Mensal de 2026 | histórico |
| RBRP11 | 21.408.063/0001-51 | FII | tijolo (recebíveis 2%, imóveis 88%, cotas de FII 10%) | atual |
| RCRB11 | 03.683.056/0001-86 | FII | tijolo (recebíveis 0%, imóveis 100%, cotas de FII 0%) | atual |
| RECR11 | 28.152.272/0001-26 | FII | papel (recebíveis 91%, imóveis 6%, cotas de FII 3%) | atual |
| TRXF11 | 28.548.288/0001-52 | FII | tijolo (recebíveis 3%, imóveis 84%, cotas de FII 13%) | atual |
| VISC11 | 17.554.274/0001-25 | FII | tijolo (recebíveis 0%, imóveis 99%, cotas de FII 1%) | atual |
| VRTA11 | 11.664.201/0001-00 | FII | papel (recebíveis 91%, imóveis 0%, cotas de FII 9%) | atual |
| XPCI11 | 28.516.301/0001-91 | FII | papel (recebíveis 94%, imóveis 0%, cotas de FII 6%) | atual |
| XPLG11 | 26.502.794/0001-85 | FII | tijolo (recebíveis 0%, imóveis 97%, cotas de FII 3%) | atual |
| XPML11 | 28.757.546/0001-00 | FII | tijolo (recebíveis 1%, imóveis 79%, cotas de FII 20%) | atual |

### Casos difíceis fora dos mapas

| Ticker | CNPJ | Classe (índice) | Motivo | Situação |
|---|---|---|---|---|
| BEES3 | 28.127.603/0001-78 | STOCK | banco ativo com DFP (F2A-16) | atual |
| BRSR6 | 92.702.067/0001-96 | STOCK | banco ativo com DFP (F2A-16) | atual |
| BMEB4 | 17.184.037/0001-10 | STOCK | banco ativo com DFP (F2A-16) | atual |
| PINE4 | 62.144.175/0001-20 | STOCK | banco ativo com DFP (F2A-16) | atual |
| BMGB4 | 61.186.680/0001-74 | STOCK | banco ativo com DFP (F2A-16) | atual |
| SANB11 | 90.400.888/0001-42 | UNIT | banco ativo com DFP (F2A-16) e unit do índice; composição 1 ON + 1 PN | atual |
| TAEE11 | 07.859.971/0001-30 | UNIT | unit do índice; composição 1 ON + 2 PN | atual |
| ENGI11 | 00.864.214/0001-06 | UNIT | unit do índice; composição 1 ON + 4 PN | atual |
| BRBI11 | 10.739.356/0001-03 | UNIT | unit do índice; composição 1 ON + 2 PN | atual |
| IGTI11 | 60.543.816/0001-93 | UNIT | unit do índice; composição 1 ON + 2 PN | atual |
| BRSR3 | 92.702.067/0001-96 | STOCK | Banrisul ON; incluída em 13/10/2026 para a regra 3 da D19; 1.687 negócios à vista em jul–set/2026 | atual |
| BRSR5 | 92.702.067/0001-96 | STOCK | Banrisul PNA; incluída em 13/10/2026 para a regra 3 da D19; só 25 negócios à vista em jul–set/2026, abaixo do critério | histórico (caso de teste das classes) |

Contagens do Banrisul (COTAHIST, registros tipo 01, mercado 010, jul–set/2026) da auditoria externa de 13/10/2026: BRSR3 1.687, BRSR5 25, BRSR6 222.902. A classe das preferenciais (PNA, PNB) vem do FCA (`Sigla_Classe_Acao_Preferencial`, documento 156166), porque o índice do F2A-1 guarda só `especie: PN`. A BRSR5 fica histórica pelo critério de negócios, mas continua no universo como caso de teste da regra 3 da D19.

### Sucessores (decisão de 13/10/2026)

| Ticker | CNPJ | Classe (índice) | Motivo | Situação |
|---|---|---|---|---|
| AZUL3 | 09.305.994/0001-29 | STOCK | sucessora de AZUL4 no índice; mesmo CNPJ; 34.747 negócios à vista em jul–set/2026 | atual |
| AXIA3 | 00.001.180/0001-26 | STOCK | sucessora de ELET3 (AXIA Energia, antiga Eletrobras); mesmo CNPJ; 1.968.451 negócios | atual |
| NATU3 | 71.673.990/0001-77 | STOCK | sucessora de NTCO3 no índice, mas com **outro CNPJ**: entra como emissor novo, sem continuidade histórica com a NTCO3; 739.313 negócios | atual |

AZUL4, ELET3 e NTCO3 continuam como históricos. Contagens de negócios da auditoria externa de 13/10/2026.

## Casos difíceis pedidos pela D32 e onde estão

| Caso | Onde |
|---|---|
| 12 bancos ativos do F2A-16 (cadastro: setor "Bancos", situação ativa, com BPP consolidado na DFP 2025) | BBAS3, BBDC4 e ITUB4 (mapa); BEES3, BRSR6, BMEB4, PINE4, BMGB4 e SANB11 (acima); Daycoval, RCI e BTG Pactual S/A nas exclusões |
| Units do índice: KLBN11, SANB11, TAEE11, ENGI11, BRBI11, IGTI11 | KLBN11 (mapa); as outras cinco acima |
| Holding com minoritários relevantes | CSAN3 (mapa) |
| Empresa com reapresentação de DFP (F2A-32) | MRVE3 (mapa): DFP 2021 e 2022 reapresentadas em 6/7/2023 |
| FIIs de papel e de tijolo | no mapa: papel HCTR11, KNCR11, MXRF11, RECR11, VRTA11, XPCI11 (e CVBI11, histórico); tijolo, 18 (MALL11 entre eles, histórico); fundo de fundos, CPTS11 e HFOF11 |

Nos bancos e units com mais de um ticker no índice (BEES3/BEES4, BRSR3/BRSR5/BRSR6, BMEB3/BMEB4, PINE3/PINE4, SANB3/SANB4/SANB11), a lista leva um ticker por companhia (aprovado em 13/10/2026), **exceto o Banrisul**, que entra com as três classes (BRSR3, BRSR5 e BRSR6): é o caso real de preferenciais com direitos distintos (PNA e PNB) que a regra 3 da D19 precisa testar. Ficam fora da verificação inicial: BEES4, BMEB3, PINE3, SANB3 e SANB4.

## Exclusões

| Ativo | CNPJ | Motivo |
|---|---|---|
| Banco Daycoval S.A. | 62.232.889/0001-90 | banco ativo com DFP (F2A-16), emissor de Categoria B no cadastro (sem ação em bolsa) |
| Banco RCI Brasil S.A. | 62.307.848/0001-15 | banco ativo com DFP (F2A-16), emissor de Categoria B no cadastro (sem ação em bolsa) |
| Banco BTG Pactual S/A | 30.306.294/0001-45 | banco ativo com DFP (F2A-16), Categoria A, listado em bolsa (BPAC11: 1.695.828 negócios em jul–set/2026), mas **fora do índice por lacuna do F2A-1**: o FCA traz o código "000000" (unit "1 ON E 2 PNA") e o índice o descartou como código fora do formato de ticker. Exclusão provisória, aprovada em 13/10/2026. O F2A-39 ficou bloqueado sem fonte oficial que ligue ISIN e CNPJ; a correção foi para a 2B |

## Contagem (depois da deduplicação)

- Base nominal: 45 ações + 30 FIIs = 75.
- Ações: 38 atuais + 7 históricas (AZUL4, BRML3, ELET3, GOLL4, JBSS3, NTCO3, PETZ3).
- FIIs: 25 atuais + 5 históricos (BCFF11, CVBI11, IRDM11, MALL11, RBRF11).
- Casos difíceis fora dos mapas: 11 atuais (7 tickers de bancos, sendo 2 do Banrisul e o SANB11 também unit, e 4 units) e 1 histórico (BRSR5). Nenhum repete ticker ou companhia dos mapas.
- Sucessores: 3 atuais (AZUL3, AXIA3, NATU3).
- **Total: 77 atuais + 13 históricos = 90 ativos**; 3 exclusões.
- O universo é a amostra verificada, não o total de listados: a cardinalidade do denominador da D32 é medida pelo índice do F2A-1, no mesmo snapshot, quando houver afirmação numérica de cobertura.

## Denominador da cobertura e critério de ampliação (D32, citados do ADR-0003)

- **Denominador da cobertura do índice:** "pares (CNPJ, código) ativos no FCA mais recente e FIIs listados em bolsa no Informe Mensal, como o F2A-1 já mede; toda exclusão tem motivo listado."
- **Critério de ampliação:** "um grupo novo entra no universo quando todos os seus casos difíceis passam pela verificação do item (números conferidos contra a fonte e abstenções com motivo), sem divergência sem explicação. O gate de cobertura do PLANO passa a citar este denominador."
- Até a Fase 3 (D17), nenhum texto promete histórico para qualquer data.

## Decisões do Marcos (13/10/2026)

- Critério de "atual" aprovado como critério operacional do universo inicial.
- Sucessores AZUL3, AXIA3 e NATU3 incluídos como atuais; NATU3 como emissor novo.
- Um ticker por companhia, exceto o Banrisul (três classes).
- BTG: exclusão provisória; a correção do índice foi para a 2B (F2A-39 bloqueado em 13/10/2026 sem fonte oficial que ligue ISIN e CNPJ).

## Pontos levantados no F2A-35 (registro)

- Sete das 45 ações ficam históricas: cinco fora do índice com o ticker do mapa (AZUL4 → AZUL3; ELET3 → AXIA3; GOLL4 com registro cancelado e GOLL54 no índice; PETZ3 com registro cancelado; JBSS3 sem ação no índice) e duas no índice, mas sem negócio no período (BRML3, Categoria B; NTCO3, incorporada, com a NATU3 como sucessora no índice). Entrar com os sucessores (AZUL3, AXIA3, NATU3) como atuais é decisão de escopo, não feita aqui.
- O BTG Pactual (banco e unit, BPAC11) fica fora por lacuna do índice do F2A-1 (código "000000" no FCA). Corrigir o índice não é escopo deste item; o caso vai para a decisão do Marcos (item novo na fila ou correção na tabela de correções do F2A-19).
- CVBI11 e MALL11 estão no índice, mas ficam históricos pela D32 (fora da listagem em bolsa no período medido pelo F2A-16).
