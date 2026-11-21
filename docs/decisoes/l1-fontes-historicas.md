# L1 — disponibilidade ponto-no-tempo das fontes (F3-L1)

Levantamento feito por `python scripts/levantamento_fase3.py` em 11/11/2026. A última execução foi de 14:26:55 a 14:28:28 UTC. O script só lê fontes públicas oficiais, com um pedido por vez, pausa de 0,5 s entre pedidos e até 3 tentativas com espera crescente (decisão 39).

O resumo completo, com URL, data da consulta, `Last-Modified` e SHA-256 de cada resposta, está em `data/fontes/l1/levantamento.json`. As amostras ficam em `data/fontes/l1/`. Os dois estão fora do git. Os tamanhos são os do cabeçalho `Content-Length` de cada arquivo (HEAD), e não os do índice da CVM, que arredonda.

## 1. Fontes, anos e tamanhos

| Fonte | URL oficial | Anos | Tamanho (zip) | Observações |
|---|---|---|---|---|
| DFP | `dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip` | 2010 a 2026 | 8,9 MB (2010) a 13,6 MB (2023); **175,4 MB** no total | Os arquivos anuais são regenerados: `Last-Modified` de 05/08/2024 para todos os anos, inclusive 2010. |
| ITR | `.../DOC/ITR/DADOS/itr_cia_aberta_{ano}.zip` | **2011** a 2026 | 24,6 MB (2011) a 32,7 MB (2024); **428,0 MB** | O primeiro ano aberto é 2011. |
| FCA | `.../DOC/FCA/DADOS/fca_cia_aberta_{ano}.zip` | 2010 a 2026 | 0,3 a 0,5 MB por ano; **6,6 MB** | `valor_mobiliario` traz o código de negociação e as datas de início e fim de negociação e de listagem. |
| Cadastro | `.../CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv` | **só o arquivo atual** | 1,5 MB | 2679 companhias; 1916 canceladas, das quais 667 desde 2010, com `DT_REG`, `DT_CANCEL`, `SIT` e `DT_INI_SIT`. Não há cadastro histórico por ano. |
| Informe de FII | `dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{ano}.zip` | **2016** a 2026 | 0,1 MB (2016) a 1,5 MB (2025); **9,4 MB** | O primeiro ano aberto é 2016. |
| COTAHIST anual | `bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP` | 2010 a 2026 | 10,4 MB (2010) a 92,9 MB (2026, parcial); **629,5 MB** | O de 2010 tem `Last-Modified` de 30/12/2010; o de 2026 é atualizado a cada pregão. |
| Tesouro Direto (taxas e preços) | CKAN do Tesouro Transparente, recurso `precotaxatesourodireto.csv` | 2004-12-31 a 2026-11-10 | 14,7 MB (CSV); SHA-256 `7ab877a3…` | 178.420 linhas. "Tesouro IPCA+ com Juros Semestrais" (NTN-B) desde 31/12/2004; "Tesouro IPCA+" (NTN-B Principal) desde 18/07/2005. |
| IPCA (SIDRA 1737, v63) | `apisidra.ibge.gov.br/values/t/1737/n1/all/v/63/p/all` | 1979-12 a 2026-09 | 89 KB; SHA-256 `0f180a70…` | 562 observações mensais. |
| PIB Focus | Olinda, `ExpectativasMercadoAnuais`, PIB Total | 1999-07-01 a 2026-11-06 | consulta OData | Primeira observação em 01/07/1999. |
| Selic (SGS 432) | `api.bcb.gov.br/dados/serie/bcdata.sgs.432` | 2010-01-01 a 2026-11-11 | 2 janelas de até 10 anos | 6159 observações. |
| CDI (SGS 12) | `.../bcdata.sgs.12` | 2010-01-04 a 2026-11-10 | 2 janelas | 4233 observações. |
| Ibovespa | B3, `indexStatisticsProxy/IndexCall/GetPortfolioDay` (`IBOV`, por ano) | 2010 a 2026 | um JSON por ano | De 245 a 251 fechamentos diários por ano completo; 214 em 2026 até a consulta. |
| Proventos em dinheiro | B3, `listedCompaniesProxy/CompanyCall` (`GetDetail` e `GetListedCashDividends`) | conforme a companhia | amostra na seção 4 | Só companhias listadas hoje (seção 4). |

Hashes das amostras baixadas:

| Amostra | SHA-256 | `Last-Modified` |
|---|---|---|
| `dfp_cia_aberta_2019.zip` | `bc82a1162b44686e8953b521e3424a5938b6661ff4655f832db4ea9488296a0d` | 05/08/2024 |
| `itr_cia_aberta_2020.zip` | `4ca11b431eb21aa98f813a3c18086ca600f234f5eb0dcec0c51a8641fccbca0a` | 29/12/2024 |

Os hashes de cada janela do SGS, de cada ano do Ibovespa e das duas consultas do Focus (primeira e última observação, gravadas em `data/fontes/l1/macro/`) estão no JSON. O cadastro, o FCA de 2015 e as sondas das deslistadas também estão em `data/fontes/l1/`. O cadastro e o FCA foram baixados à parte para conferir as colunas.

## 2. Reapresentações: a CVM guarda versões antigas?

**Guarda o registro de cada versão, mas não os valores das versões antigas.**

- **O que o índice registra:** o arquivo-índice de cada ano (`dfp_cia_aberta_{ano}.csv`, `itr_cia_aberta_{ano}.csv`) traz uma linha por versão entregue, com `VERSAO` e `DT_RECEB`.
- **DFP de 2019:** 671 documentos, dos quais 117 (17,4%) têm mais de uma versão, chegando a 5.
- **ITR de 2020:** 1976 documentos, dos quais 202 (10,2%) têm mais de uma versão, também até 5.
- **O que as demonstrações trazem:** BPA, BPP, DRE, DFC, DMPL, DVA e DRA consolidadas têm os valores **só da última versão**. Em cada demonstração, nenhum documento tem linhas de mais de uma versão.
  - DFP de 2019: 386 documentos na DRE consolidada. Os 88 reapresentados presentes têm só as linhas da versão mais alta do índice; nas outras demonstrações, a mesma coisa.
  - ITR de 2020: 1115 documentos. Os 150 reapresentados presentes também só têm a última versão.
  - Os números saem do script (`demonstracoes` no JSON).
- **Caso conhecido, IRB Brasil RE (CD_CVM `024180`), DFP de 2019:** o índice registra as versões 1 a 5, entregues em 18/02/2020, 30/06/2020 (as versões 2 e 3), 07/07/2020 e 18/02/2021. As demonstrações só têm os números da última.
- **Intervalo entre a primeira e a última data de entrega** dos documentos com mais de uma data distinta (`intervalo_primeira_ultima_entrega_dias` no JSON):

  | Amostra | Documentos | Mediana | p90 | Máximo | Acima de 90 dias | Acima de 365 dias |
  |---|---|---|---|---|---|---|
  | DFP de 2019 | 105 | 15 dias | 191 | 790 | 20 | 4 |
  | ITR de 2020 | 172 | 14 dias | 195 | 749 | 37 | 10 |

- **Os arquivos anuais são regenerados:** o `Last-Modified` da DFP de todos os anos é de agosto de 2024. Um download antigo não é uma foto da época.

**O que isso significa para o modo estrito (adendo de 09/11).** Numa data D, só se prova a versão cujos números o arquivo traz, que é a última. Por isso o documento entra se a última versão foi entregue até D (`DT_RECEB ≤ D`). Se a última foi entregue depois de D, o modo estrito se abstém, porque a versão vigente em D existiu mas seus números não estão na fonte aberta. O modo exploratório usa a última versão, com o aviso "possível reapresentação posterior não observável".

Na data D, o modo estrito cobre todo documento cuja última versão foi entregue até D, o que inclui os 83% a 90% sem reapresentação e os reapresentados depois da última entrega. Fica de fora só o reapresentado entre a primeira e a última entrega: em geral por duas semanas (mediana) e, em poucos casos, por mais de um ano.

## 3. Benchmarks

- **Ibovespa:** a série diária oficial da B3 cobre todos os anos desde 2010.
- **CDI:** o SGS 12 cobre desde 04/01/2010.
- **Último pregão de cada mês:** dos 203 meses comparados, 187 têm o mesmo último dia nas duas séries. Os 16 divergentes são **todos dezembros**. A B3 não negocia no último dia útil do ano, e o CDI tem observação nesse dia: por exemplo, em 2024 o Ibovespa fecha no dia 30 e o CDI no dia 31.
- **Para o F3-7:** é preciso uma regra de alinhamento, como fechar o mês no último pregão da B3 e acumular o CDI até esse mesmo dia. A regra fica como decisão delegada (classe 2) no item que a usar.
- **Lacunas:** nenhum mês sem observação em nenhuma das duas séries no intervalo.

## 4. Proventos em dinheiro (B3)

Amostra de companhias listadas hoje (`GetListedCashDividends`, todas as páginas):

| Companhia (CD_CVM) | Registros | Primeiro ano (data ex) | Anos sem registro no intervalo | Dias entre aprovação e data ex | Identidade (decisão 33) |
|---|---|---|---|---|---|
| ABEV3 (23264) | 40 | 2014 | nenhum | 4 a 54 | conferida |
| ITUB4 (19348) | 960 | 1995 | nenhum | 0 a 360 | conferida |
| TAEE11 (20257) | 297 | 2007 | nenhum | 0 a 7 | não comprovada: espécie UNT sem ISIN no GetDetail (DD-06) |
| PETR4 (9512) | 343 | 1996 | 2015, 2016, 2017 | 0 a 57 | conferida |
| LREN3 (8133) | 99 | 1996 | 2000, 2002, 2003, 2004 | −1 a 8 (2 com aprovação depois da data ex) | não comprovada: espécie PN sem ISIN (DD-06) |

- **Disponibilidade temporal:** cada registro traz a data de aprovação (`dateApproval`) e a data ex. A informação existe a partir da aprovação, que vem antes da data ex em quase todos os casos. Na LREN3, 2 registros têm a aprovação depois da data ex.
- **Lacunas:** os anos sem registro da PETR4 (2015 a 2017) coincidem com anos em que a companhia não distribuiu dividendos em dinheiro. Ano sem registro não prova ano sem distribuição (armadilha 9): a série só serve onde a identidade é conferida.

**Companhias deslistadas.** Testei quatro companhias com registro cancelado na CVM depois de 2018: Linx (23035), Cia Hering (14761), Lojas Hering (8117) e Somos Educação (22551). Nas quatro, o `GetDetail` da B3 não traz nome de pregão nem emissor, e não há como chegar à relação de proventos ("cadastro da B3 sem nome de pregão ou código do emissor"). **A B3 só devolve proventos de quem está listado hoje.**

## 5. Volume

| Componente (2010 em diante) | Bytes |
|---|---|
| CVM (DFP, ITR, FCA e Informe, todos os anos) | 619.487.974 |
| COTAHIST anual 2010–2026 | 629.470.010 |
| Tesouro (CSV histórico) | 14.677.182 |
| **Brutos (zip)** | **1.263.635.166 (1,26 GB)** |
| Teto do banco | 16.696.679.166 (16,7 GB) |
| Total projetado | 17.960.314.332 (18,0 GB) |

O teto do banco é a soma dos CSVs descompactados de uma DFP (251,5 MB) e de um ITR (730,7 MB), multiplicada pelos 17 anos desde 2010. É um teto: o banco guarda só as contas e os campos usados.

Os brutos ficam muito abaixo do limite de **100 GB** (decisão 39). O disco onde está `data/` (`/dev/sdd`, WSL) tem 1.006.797.594.624 bytes livres (`projecao.disco_livre_bytes` no JSON; cerca de 938 GiB), mais que o dobro da projeção total. **O volume não para o loop.**

## 6. Sugestões do pacote §2 contra os números medidos

| Sugestão | O que o L1 mediu | Situação |
|---|---|---|
| 1. Profundidade desde 2011, com a DFP de 2010 como abertura; primeira análise completa em 2016; FII no primeiro Informe mais 13 meses | DFP desde 2010; ITR desde **2011**; Informe de FII desde **2016**, o que põe o primeiro FII completo em 2017 | Confirmada (decisão 4). |
| 2. Universo PIT com deslistadas, pelo FCA e pelo cadastro históricos e pela presença no COTAHIST | O FCA anual traz código de negociação e datas de listagem; o cadastro existe só na versão atual, mas tem `DT_REG` e `DT_CANCEL` (667 cancelamentos desde 2010); o COTAHIST cobre de 2010 a 2026 | Confirmada para o universo. **Não se cumpre nos proventos das deslistadas** (seção 4). |
| 3. Reapresentações por `DT_RECEB ≤ as_of`; se a fonte só guarda a última versão, a última com aviso | O índice guarda versões e datas; os valores só da última; 10% a 17% dos documentos reapresentados | Cumprível como o adendo de 09/11 prevê: o modo estrito usa a última versão quando ela foi entregue até D, e se abstém nos outros casos; o exploratório usa a última com aviso. |
| 4. Macro: NTN-B pelo CSV do Tesouro desde 2004, IPCA pelo SIDRA, PIB pelo Focus, Selic pelo SGS | NTN-B desde 31/12/2004 e NTN-B Principal desde 18/07/2005; SIDRA desde 1979; Focus desde 1999; SGS 432 e 12 desde 2010 (as janelas consultadas) | Confirmada. |
| 5. Volume fora do git, com parada acima do limite | 1,26 GB de brutos; teto de 18,0 GB com o banco; 938 GiB livres | Confirmada; abaixo de 100 GB (decisão 39). |

## 7. Para o `[DECISÃO]` após o L1

Pelo passo 7 do `/goal`, o loop para nesse `[DECISÃO]` se o L1 mostrar que alguma decisão de dados não é cumprível. Profundidade, reapresentações, benchmarks, macro e volume são cumpríveis como decididos. A regra de dezembro do alinhamento fica como decisão delegada.

**Proventos em dinheiro das companhias deslistadas não são cumpríveis pela fonte decidida (B3).** O universo PIT inclui as deslistadas (sugestão 2), mas a B3 não devolve cadastro nem proventos de quem saiu da bolsa. As opções que separam os caminhos:

- **(a) Abstenção declarada.** As deslistadas ficam no universo. O Bazin e o perfil de renda se abstêm nelas, com o motivo "proventos da B3 indisponíveis para companhia deslistada", e o F3-7 mede quanto do universo isso atinge por ano.
  - Custo: viés de sobrevivência nas lentes que dependem de proventos, declarado no resultado.
- **(b) Outra fonte oficial para as deslistadas,** como dividendos declarados na DMPL da DFP (por exercício, sem data ex) ou avisos aos acionistas no IPE da CVM.
  - Custo: regra nova de dado e de data, com ficha ou decisão própria, e um item novo antes do F3-7.
- **(c) Universo de proventos só com as listadas hoje.**
  - Custo: contraria a sugestão 2 e o objetivo de evitar viés de sobrevivência.

Recomendo **(a)** agora, que fica do lado da abstenção e é reversível, e **(b)** como estudo para decisão no checkpoint da 3-b.
