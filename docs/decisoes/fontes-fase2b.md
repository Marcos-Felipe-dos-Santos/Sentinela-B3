# Fontes da Fase 2B — taxa real, rendimento dos FIIs, bancos e pendências da 2A

**Item:** F2B-21 (`docs/loop/fila.md`). **Script:** `scripts/levantamento_fase2b.py` (`--secao N` roda só algumas; sem `--atualizar`, usa as respostas arquivadas). **Cache:** `outputs/levantamento_cache/f2b21/` (fora do git): cada resposta HTTP tem um `.meta.json` com URL, status, instante da coleta (UTC), tipo, tamanho e SHA-256, inclusive as que falharam; cada seção grava `secao-N.json`.

**O que o script reproduz:** todos os números deste documento (fora a consulta manual à SGS citada na pergunta 2) saem de `secao-N.json` (e dos CSVs ao lado), sobre o cache arquivado: inclusive o corpo das respostas sem JSON da SGS (`corpos_sem_json`, seção 2), o registro do BTG (`registro_btg`, seção 6), os agregados e as medianas de spread (`spreads_agregados` e `fii_upside_ntnb_mais_medianas_de_spread`, seção 4), a conferência do DY do Informe (`identidade_patrimonial_entre_fundos`, seção 4) e, na seção 8, os ISINs de BTCI11 e TRPL11 no Informe e nas listas conhecidas, as leituras dos submodelos e as contas da dívida líquida. Dependências: a seção 3 lê os resultados da 1 e da 2; a 4 lê os retratos da 3 e o resultado da 1; a 5 lê os retratos da 3 (sem eles, marca o P/VP justificado como não determinado). `--atualizar` refaz as consultas HTTP, mas não renova os preços do yfinance já arquivados (a seção 3 reusa o retrato salvo). Num cache limpo, as seções refazem as consultas, e as que dependem de fonte fora do ar saem "não determinado".

**Regras do levantamento:** rede só de leitura; o script não importa `config` (as constantes da V1 são lidas pela árvore sintática de `config.py`), não usa token da brapi e não lê `.env`. Amostra: o universo inicial (`docs/decisoes/universo-inicial.md`, só os ativos "atual") e o índice oficial local (`data/referencia/indice.json`); nunca a carteira. **Nada aqui decide taxa, prêmio, vértice, spread, escopo ou limiar**: cada resposta traz a evidência e a consequência para o item afetado, e a decisão é do Marcos no marcador "Fichas da 2B, taxa e fontes".

Coletas de 19/10/2026 (UTC), salvo indicação. Os nomes de campo do Tesouro ("Taxa Compra Manha", "Taxa Venda Manha") são citados como aparecem no arquivo oficial, só neste documento (exceção em aberto da fila, decidida na [TAXA]).

---

## 1. NTN-B (F2B-1; checkpoint da Fase 0, seção 4, item 2)

| Fonte | URL | Status | Observação |
|---|---|---|---|
| API do Tesouro Direto que a V1 lê (`config._fetch_ntnb`) | `https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/service/api/treasureList.json` | **404** (HTML) | no dossiê da Fase 2, 403; segue sem resposta útil |
| Histórico de preços e taxas do Tesouro Direto (Tesouro Transparente) | `https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv` | **200** | 14.598.768 bytes, SHA-256 `f4f9b0fb…a2972`; 177.434 linhas; datas-base de **2004-12-31 a 2026-10-15** |

Colunas do histórico: `Tipo Titulo`, `Data Vencimento`, `Data Base`, `Taxa Compra Manha`, `Taxa Venda Manha`, `PU Compra Manha`, `PU Venda Manha`, `PU Base Manha` (taxas em % ao ano, real para os títulos IPCA+).

Títulos IPCA+ na última data-base (15/10/2026): NTN-B Principal = "Tesouro IPCA+"; NTN-B = "Tesouro IPCA+ com Juros Semestrais".

| Título | Vencimento | Taxa Compra Manha | Taxa Venda Manha |
|---|---|---|---|
| Tesouro IPCA+ | 15/05/2029 | 6,77 | 6,89 |
| Tesouro IPCA+ | 15/08/2032 | 6,80 | 6,92 |
| Tesouro IPCA+ | 15/05/2035 | 6,84 | 6,96 |
| Tesouro IPCA+ | 15/08/2040 | 6,73 | 6,85 |
| Tesouro IPCA+ | 15/05/2045 | 6,73 | 6,85 |
| Tesouro IPCA+ | 15/08/2050 | 6,74 | 6,86 |
| Tesouro IPCA+ com Juros Semestrais | 15/08/2030 | 6,79 | 6,91 |
| Tesouro IPCA+ com Juros Semestrais | 15/08/2032 | 6,79 | 6,91 |
| Tesouro IPCA+ com Juros Semestrais | 15/05/2035 | 6,82 | 6,94 |
| Tesouro IPCA+ com Juros Semestrais | 15/05/2037 | 6,83 | 6,95 |
| Tesouro IPCA+ com Juros Semestrais | 15/08/2040 | 6,75 | 6,87 |
| Tesouro IPCA+ com Juros Semestrais | 15/05/2045 | 6,75 | 6,87 |
| Tesouro IPCA+ com Juros Semestrais | 15/08/2050 | 6,75 | 6,87 |
| Tesouro IPCA+ com Juros Semestrais | 15/05/2055 | 6,71 | 6,83 |
| Tesouro IPCA+ com Juros Semestrais | 15/08/2060 | 6,73 | 6,85 |

Vértices candidatos (taxa de compra / de venda, % a.a., real), por título:

| Vértice | Tesouro IPCA+ | IPCA+ com Juros Semestrais | Os dois juntos |
|---|---|---|---|
| Mais perto de 10 anos (alvo 15/10/2036): 2035 no Tesouro IPCA+, 2037 no de juros semestrais | 6,84 / 6,96 (2035) | 6,83 / 6,95 (2037) | — |
| 2035 | 6,84 / 6,96 | 6,82 / 6,94 | — |
| 2045 | 6,73 / 6,85 | 6,75 / 6,87 | — |
| Mais longo (2050; 2060) | 6,74 / 6,86 | 6,73 / 6,85 | — |
| Média de 2035 em diante | 6,76 / 6,88 (4 títulos) | 6,76 / 6,88 (7 títulos) | **6,76 / 6,88** (11 títulos) |

- **`MACRO.ntnb_longa` hoje:** a API que ele lê responde 404, então a V1 cai na contingência de **7%** (`config.py:122`). A média de 2035 em diante pelo histórico do Tesouro dá 6,88% (taxa de venda) ou 6,76% (compra): 0,12 a 0,24 ponto abaixo da contingência.
- **Consequência (F2B-1, F2B-22, F2B-27, F2B-30):** há fonte oficial respondendo (o histórico do Tesouro Transparente), com data-base e as duas taxas; a API da V1 não serve. A escolha do vértice, da taxa (compra ou venda) e do prêmio é da [TAXA]; o F2B-27 precisa usar uma fonte que responda (o histórico) ou ficar `[!]`.

## 2. Inflação da conversão (F2B-1; D22)

| Série | Fonte | Status | Valor e data | Começo da série |
|---|---|---|---|---|
| IPCA 12 meses, BCB SGS 433 | `api.bcb.gov.br/dados/serie/bcdata.sgs.433/...` | 200 com página HTML "Requisição inválida!" (02:16 UTC); uma consulta manual depois, fora do script, também sem resposta (tempo esgotado em 30 s, três vezes) | **não determinado** nesta coleta | não determinado |
| IPCA acumulado em 12 meses, IBGE SIDRA (controle) | `apisidra.ibge.gov.br/values/t/1737/n1/all/v/2265/p/last` | 200 | **4,58%** (setembro de 2026) | tabela 1737 (não medido) |
| Focus, IPCA 12 meses à frente | BCB Olinda, `ExpectativasMercadoInflacao12Meses` | 200 | mediana **4,4009%** (09/10/2026, não suavizada, base de cálculo 1, 48 respondentes); 4,4757% na base 0 (132) | 2001-11-07 |
| Focus, IPCA anual, ano mais longo publicado | BCB Olinda, `ExpectativasMercadoAnuais` | 200 | **2030: 3,50%** (09/10/2026); 2026: 5,22%, 2027: 4,30%, 2028: 3,79%, 2029: 3,50% | 2000-01-03 |
| Inflação implícita no vértice da pergunta 1 | histórico do Tesouro (prefixados e IPCA+) | — | **não determinado**: exige casar prazo e tipo de fluxo (com e sem cupom); subtrair taxas de títulos diferentes daria um número sem significado | — |

- **Consequência (F2B-1, F2B-29, F2B-30):** o IPCA de 12 meses tem fonte oficial respondendo (IBGE), e o SGS 433 não respondeu nesta coleta; o Focus responde, com a expectativa de 12 meses e a de até 2030. A escolha da inflação da conversão de Fisher é da [TAXA]. Se o F2B-30 depender do SGS, ele precisa de alternativa ou de abstenção com motivo.

## 3. Matriz de sensibilidade (armadilha 5; F-11, item 3)

**Base:** as ações e FIIs "atual" do universo inicial (51 ações e units, 25 FIIs), com preço e proventos de 12 meses (ex-data de 01/10/2025 a 30/09/2026) do yfinance, arquivados no cache (para 14 tickers, coleta deste item; para os outros 62, o cache do dossiê da Fase 2, `outputs/dossie_cache/yf_*.json`, com o último fechamento do dia da coleta do dossiê, em 1/10/2026 ou depois: os preços não são todos da mesma data), e fundamentos recalculados da DFP 2025 pelo código atual (lucro e PL dos controladores, LPA divulgado e escala; já inclui o F2B-8 e a ficha 1.1). Métodos chamados pelos módulos de `sentinela/methods/` com os parâmetros da V1 (lidos da árvore de `config.py`). Arquivos: `matriz_v1.csv`, `matriz_sensibilidade.csv`, `retratos_publicos.json`.

**Limite:** não reproduz a cascata inteira nem o score do motor (o levantamento chama os métodos, não o `ValuationEngine`, que lê o `MacroContext` de `config`); por isso **a contagem por classificação agrupada (sinal positivo, neutro, sinal negativo) fica não determinada**. Ela é do "antes e depois" dos itens de taxa (F2B-1, F2B-31 e F2B-2), que rodam os motores. A NTN-B da matriz é a média das IPCA+ de 2035 em diante, taxa de venda, com e sem cupom (6,8818%; arredondada para 6,88% no texto). A mediana do upside por método está abaixo.

### V1 (Selic como taxa), mediana do upside

| Selic | Bazin (25) | Gordon (17) | Graham (22) | Lynch (1) | FII, Selic líquida (25) |
|---|---|---|---|---|---|
| 10% | −20,2% | −29,1% | +40,0% | +777% | +25,6% |
| 11% | −27,4% | −34,6% | +40,0% | +777% | +14,2% |
| 12% | −33,5% | −39,3% | +40,0% | +777% | +4,7% |
| 13% | −38,6% | −43,3% | +40,0% | +777% | −3,4% |
| 14% | −43,0% | −46,9% | +40,0% | +777% | −10,3% |
| 15% | −46,8% | −50,0% | +40,0% | +777% | −16,2% |

O Graham não depende da Selic; o Lynch só se aplica a um ativo da amostra. Entre parênteses, quantos ativos receberam o método.

### Gordon com k real = NTN-B (média de 2035 em diante, 6,88%) + prêmio

Mediana do upside, para três inflações da pergunta 2 (Focus 2030 3,50%; Focus 12 meses 4,40%; IBGE 12 meses 4,58%). Definições de g real da [TAXA]: (i) Fisher do g nominal (ROE × retenção, a fórmula da V1, **sem o teto de 8% nominal** que a V1 aplica, `GORDON_G_MAX`); (ii) ROE real × retenção (sem teto); (iii) a (i) com o teto candidato de 2% real (só um número de teste, não proposta). Parte da diferença para o Gordon da V1 vem da retirada do teto, não só do regime da taxa.

| g real | Prêmio | Inflação 3,50% | 4,40% | 4,58% |
|---|---|---|---|---|
| (i) | 4% | −8,7% | −13,9% | −15,4% |
| (i) | 5% | −14,1% | −21,7% | −23,1% |
| (i) | 7% | −28,6% | −34,2% | −35,2% |
| (ii) | 4% | +27,1% | +19,3% | +17,9% |
| (ii) | 5% | +11,1% | +5,1% | +4,0% |
| (ii) | 7% | −9,7% | −12,9% | −13,7% |
| (iii) | 4% | −17,4% | −20,9% | −22,4% |
| (iii) | 5% | −25,8% | −28,0% | −29,2% |
| (iii) | 7% | −38,3% | −38,8% | −39,7% |

De 15 a 17 ativos por célula (os que passam as guardas do Gordon). Todas as combinações (os nove vértices e as 12 inflações) estão em `matriz_sensibilidade.csv`.

- **Real × nominal (conferência de implementação, não achado):** com k e g convertidos pela mesma inflação, os dois regimes coincidem por construção (kN − gN = (1 + π)(k − g)); a diferença máxima medida, 1e−10, só confirma que o script aplica Fisher dos dois lados.
- **Viés analítico da (ii):** pelas fórmulas, g(ii) − g(i) = π(1 − b)/(1 + π), com b a retenção: a (ii) supera a (i) por construção, porque não desconta a erosão inflacionária do patrimônio retido quando o ROE contábil é nominal. O upside maior da (ii) vem dessa identidade, não do dado.
- **Misto (armadilha 1, controle; também sem o teto de 8%):** k real com g nominal dá, na mediana, **1,5 a 3,3 vezes** o valor nominal (por exemplo, 1,79 com (i), prêmio de 5% e inflação de 4,40%; 2,37 com (ii)). É o erro que a armadilha 1 descreve.

### Bazin

| Taxa | Mediana do upside (25 ativos) |
|---|---|
| Selic (V1), 10% a 15% | de −20,2% a −46,8% (tabela da V1) |
| Fixa de 6% (F-5) | +33,1% |
| k real sem crescimento, prêmio 4% (10,88%) | −26,6% |
| idem, prêmio 5% (11,88%) | −32,8% |
| idem, prêmio 7% (13,88%) | −42,5% |

### FIIs (25)

| Benchmark | Mediana do upside |
|---|---|
| Selic líquida (V1), 10% a 15% | de +25,6% a −16,2% |
| NTN-B (6,8818%) + 1 ponto | +35,5% |
| NTN-B + 2 pontos | +20,2% |
| NTN-B + 3 pontos | +8,1% |
| NTN-B + 2,25 pontos (p25 da mediana mensal, janela da série) | +16,9% |
| NTN-B + 2,75 pontos (mediana, janela da série) | +10,9% |
| NTN-B + 3,25 pontos (mediana dos últimos 5 anos) | +5,4% |
| NTN-B + 3,38 pontos (p75, janela da série) | +4,1% |

- **DY dos FIIs na matriz × na série do spread:** na matriz, o DY é o dos proventos do yfinance sobre o preço do yfinance; as medianas de spread da pergunta 4 foram medidas com o rendimento reconstruído do Informe sobre o COTAHIST. As linhas "NTN-B + medianas" combinam as duas definições.
- **Consequência (F2B-1, F2B-2, F2B-23 a F2B-25, F2B-31):** a escolha da definição de g real move a mediana do Gordon em mais de 40 pontos com o mesmo prêmio; a (ii) é a única que dá upside positivo com prêmio de 4% ou 5%, pela identidade acima. O Bazin com k real fica mais negativo que o da V1 com Selic de 10%, e o de taxa fixa de 6% vira positivo. As fichas precisam declarar o efeito de cada opção com esta matriz; a contagem por classificação agrupada, que o PLANO pede no "antes e depois", fica para os itens de taxa (F2B-1, F2B-31 e F2B-2), que rodam os motores.

## 4. DY e spread dos FIIs (F2B-2; checkpoint, seção 4, item 3)

**Fontes:** Informe Mensal de FII da CVM (`https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_AAAA.zip`), anos **2016 a 2026** no portal (2016 começa em 2016-09-01; 2026 vai até 2026-09-01); dicionário (`.../INF_MENSAL/META/meta_inf_mensal_fii.zip`) e a norma (Resolução CVM 175, anexo da 184, `resol184.docx`). Preços: COTAHIST anual da B3 (`https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_AAAAA.ZIP`), 2016 a 2026, status 200, só no levantamento.

- **Representação de `Percentual_Dividend_Yield_Mes`: razão** (0,007413 = 0,74% no mês, ALZR11, set/2026, versão 1), não percentual. A conferência foi pela coluna-irmã `Percentual_Rentabilidade_Patrimonial_Mes`: nos meses sem amortização de 2026, ela iguala VP(t) ÷ VP(t−1) − 1 lida como **razão** (erro mediano de 3,0e−7 em 21 FIIs), e não como percentual (erro de 0,0022). A conferência é da coluna-irmã, do mesmo bloco do Informe; a do próprio DY exigiria o rendimento por cota de outra fonte. O F2A-16 registrou o DY do Informe "em percentual"; o contrato do F2A-32 lê fração, e é a fração que confere.
- **Base:** a norma define o DY do mês como os rendimentos declarados por cota sobre o **valor patrimonial da cota do fim do mês anterior** (texto conferido no `resol184.docx`), e não a cotação.
- **Rendimento distribuído:** o complemento não tem campo do valor distribuído por cota; `Rendimentos_Distribuir` (ativo e passivo) é saldo de obrigação, não fluxo pago. O rendimento por cota pode ser reconstruído por DY do mês × VP do mês anterior (`fii_rendimentos_candidatos.csv`), nos meses consecutivos; primeiro mês da série: 2016-09.
- **Série do spread candidato** (DY de 12 meses sobre o preço − média das NTN-B de 2035 em diante, taxa de venda, último dia do mês): os 25 FIIs atuais do universo, de 2017-10 a 2026-09 (108 meses). Mediana mensal entre os fundos:

  | Grupo | Fundos | Mediana, últimos 5 anos (p25–p75) | Mediana, série toda (p25–p75) | Atual (set/2026) |
  |---|---|---|---|---|
  | Todos | 25 | 3,25 pp (2,93–3,77) | 2,75 pp (2,25–3,38) | 3,34 pp |
  | Tijolo | 17 | 2,65 pp (1,83–2,89) | 2,21 pp (1,72–2,72) | 2,64 pp |
  | Papel | 6 | 6,15 pp (5,59–6,97) | 5,40 pp (3,74–6,54) | 6,52 pp |

  Por fundo: `spreads_candidatos_por_fundo` e `spreads_candidatos_janelas` em `secao-4.json`. A janela de 10 anos fica limitada pela série (9 anos).
- **Limites e desvios do item:** o item pede a mediana dos FIIs listados; a amostra são só os 25 FIIs atuais do universo, com viés de sobrevivência. Tijolo e papel vêm do universo inicial, que os classificou pela composição do `ativo_passivo` (como no F2A-35), mas a de agosto de 2026, fixa para todos os meses; os outros 2 dos 25 são fundos de fundos, fora das duas linhas (têm a sua em `medianas_mensais_amostra_tipo_atual`). Também: rendimento reconstruído sem ajuste de eventos de cota (desdobramentos, emissões); um só vértice do Tesouro.
- **Selic líquida nos mesmos meses: não determinado.** A SGS 432 não respondeu nesta coleta (página "Requisição inválida!"; consulta de 2016 a 2026 recusada pela janela máxima de 10 anos).
- **Consequência (F2B-25, F2B-28, F2B-2):** o F2B-28 pode ler o DY do Informe em razão e a base patrimonial, ou reconstruir o rendimento por cota; o DY de 12 meses sobre o preço exige o preço de outra fonte. Os spreads acima são candidatos para a [FII], com os limites declarados; a definição (todos, tijolo e papel, janela) é do Marcos.

## 5. Bancos e financeiras (F2B-3, F2B-4)

### Inadimplência

IF.data (BCB Olinda), relatório 16, data-base 2026-06, conglomerado prudencial do BB (`C0080329`): status 200, 11 linhas. Linhas relevantes: "Inadimplência" (conta 148834, "Carteira ativa inadimplida arrastada") **65.383.226.229,80**; "Ativos problemáticos" (148833) 104.092.086.027,33; "Total Geral" (24454, volume de crédito das naturezas 1, 2, 3, 5 e 11 do documento 3040) 1.115.404.849.436,43. Razão no mesmo relatório: **5,86%**.

- **Consequência (F2B-3, F2B-26):** a hipótese do F2A-16 se confirma: o relatório 16 traz uma medida de inadimplência. O conceito ("carteira ativa inadimplida arrastada") e o denominador não foram conferidos contra a definição de atraso de 90 dias; a [BANCOS] decide se usa e com que denominador. Até lá, a limitação continua.

### Setores financeiros do índice

50 tickers do índice oficial em setores financeiros. Modelo pelo `BPP_con` da DFP 2025 (contas-raiz do patrimônio presentes):

| Setor (índice) | Tickers | Contas-raiz no BPP 2025 |
|---|---|---|
| Bancos | 16 | sem BPP consolidado 2025 |
| Bancos | 15 | 2.03 e 2.07 (PL em 2.07) |
| Bancos | 3 | 2.03, 2.07 e 2.08 (PL em 2.08) |
| Seguradoras e Corretoras | 4 | 2.03 |
| Emp. Adm. Part. - Intermediação Financeira | 3 | 2.03 |
| Emp. Adm. Part. - Intermediação Financeira | 3 | sem BPP consolidado 2025 |
| Emp. Adm. Part. - Seguradoras e Corretoras | 2 | 2.03 |
| Intermediação Financeira | 1 | 2.03 |
| Emp. Adm. Part. - Crédito Imobiliário | 1 | 2.03 |
| Emp. Adm. Part. - Crédito Imobiliário | 1 | sem BPP consolidado 2025 |
| Emp. Adm. Part. - Bancos | 1 | 2.03 |

Lista por ticker, com CNPJ, código CVM, segmento e as contas: `financeiros_indice` em `secao-5.json`. Hoje `contas_cvm.modelo_do_setor` põe no modelo banco só o setor "Bancos", e no de seguradora quem tem "seguradoras" no setor: as variantes "Emp. Adm. Part. - …" de intermediação, crédito imobiliário e bancos ficam no modelo empresa.

- **Consequência (F2B-4, F2B-32):** insumo da [FINANCEIRAS]. A "Emp. Adm. Part. - Bancos" usa o PL em 2.03 (modelo empresa), não em 2.07 ou 2.08.

### P/VP justificado dos bancos do universo

P/VP = (ROE − g) ÷ (k − g), com ROE, VPA e payout (dividendos + JCP da DVA ÷ lucro dos controladores, F2A-7) da DFP 2025 pelo código atual (depois do F2B-11); k = NTN-B (cada vértice da pergunta 1) + prêmio de 4%, 5% ou 7%; g = ROE × retenção (nominal convertido por Fisher, ou ROE real × retenção) ou inflação + 0, 1 e 2 pontos; regimes real e nominal. Arquivo: `bancos_pvp_candidatos.csv` (15.113 cenários).

- **Real × nominal (conferência de implementação):** coincidem por construção (ROE − gN = (1 + π)(ROE real − g)); a diferença máxima, 3,3e−9, confirma a conversão.
- **P/VP de mercado:** pelo preço do retrato da pergunta 3 (datas da coleta do yfinance, ver a base da pergunta 3). A comparação é diagnóstica da fórmula, não sinal de preço.
- Mediana com NTN-B de 6,88% e prêmio de 5% (g = ROE × retenção convertido / g = inflação + 1 ponto), contra o P/VP de mercado:

  | Ticker | ROE | Payout (DVA) | VPA | P/VP justificado | P/VP de mercado |
  |---|---|---|---|---|---|
  | BBAS3 | 7,2% | 38,1% | 33,15 | 0,22 / 0,16 | 0,70 |
  | BBDC4 | 13,3% | 61,2% | 16,87 | 0,70 / 0,69 | 1,10 |
  | BEES3 | 14,0% | 69,7% | 6,97 | 0,78 / 0,76 | 1,31 |
  | BRSR3 | 15,0% | 37,9% | 28,03 | 0,75 / 0,84 | 0,66 |
  | BRSR6 | 15,0% | 37,9% | 28,03 | 0,75 / 0,84 | 0,57 |
  | ITUB4 | 21,9% | 75,1% | 18,55 | 1,45 / 1,45 | 2,38 |
  | BMEB4 | 27,0% | 29,9% | 21,95 | sem valor (k ≤ g) / 1,89 | 2,72 |
  | BMGB4 | 12,5% | 0% | 7,77 | 0 (g = ROE) / 0,62 | 0,82 |
  | PINE4, SANB11 | — | — | — | **não determinado** (ROE, VPA positivo ou payout ausente) | — |

- **Consequência (F2B-3, F2B-26):** a fórmula é sensível a g quando ROE ≈ k (BMEB4: com prêmio de 7% e g = ROE × retenção, P/VP de 50,7) e degenera com payout zero (BMGB4: g = ROE e P/VP zero). A ficha precisa tratar k ≤ g e g ≥ ROE. Só PINE4 e SANB11 seguem sem os insumos depois do F2B-11.

## 6. BTG (F2A-39)

| Fonte | URL | Status | ISIN `BRBPACUNT006` | CNPJ 30.306.294/0001-45 |
|---|---|---|---|---|
| B3, empresas listadas, detalhe pelo código CVM 22616 | `https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetDetail/eyJjb2RlQ1ZNIjogIjIyNjE2IiwgImxhbmd1YWdlIjogInB0LWJyIn0=` | **200** (994 bytes, SHA-256 `b279b720…4441a`, 19/10/2026 02:42 UTC) | sim | sim |
| B3, cadastro de instrumentos (`tickercsv` de 16/10/2026) | `https://arquivos.b3.com.br/apinegocios/tickercsv/2026-10-16` | **404** | — | — |

No **mesmo registro** do detalhe: `"cnpj": "30306294000145"`, `"codeCVM": "22616"`, `"companyName": "BCO BTG PACTUAL S.A."` e, em `otherCodes`, `{"code": "BPAC11", "isin": "BRBPACUNT006"}` (com BPAC3 `BRBPACACNOR7` e BPAC5 `BRBPACACNPA0`).

- **Consequência (F2A-39):** a fonte oficial da B3 traz o ISIN da unit e o CNPJ juntos; o cadastro de instrumentos não respondeu. A aceitação dessa fonte como evidência da tabela de correções é a [BTG], do Marcos.

## 7. Pontos "não conferidos" da 1ª passada do Gemini

| Ponto | Resultado | Evidência | Consequência |
|---|---|---|---|
| Regex das descrições do LPA (`cvm_provider._CLASSE_NA_DESCRICAO`, `^(ON|PN[A-Z]?)$`) | **refutado** | as descrições reais das linhas 3.99.01.xx da DRE 2025 são ON, PN, PNA, PNB, PNC, PND e PNE; todas casam | nenhuma |
| Coluna `MOEDA` não validada | **refutado nos dados** | as 30.980 linhas da DRE consolidada 2025 trazem `REAL`; `parsear_demonstrativo` converte a escala, mas não confere a moeda | risco latente, sem ocorrência |
| DVA sem `try` no TTM | **confirmado** | `CVMProvider._acumulados_do_arquivo` lê `DVA_con` sem tratar arquivo ausente; a exceção sobe até `acumulados_ttm`, que descarta o arquivo inteiro, inclusive a DRE | um ITR sem DVA tira lucro e receita do TTM, em vez de só os proventos |
| Cache duplicado entre série e TTM | **confirmado** | o mesmo `DRE_con` da DFP 2025 fica duas vezes no cache de `parsear_demonstrativo` (com e sem `include_periodo`): 5,2 MB e 7,0 MB, 15.490 linhas cada | só memória; nenhum número muda |
| Nova tentativa em HTTP 404 do COTAHIST | **confirmado** | reprodução sem rede (`cvm_download` com resposta 404 sintética): 3 chamadas, espera de 1 s e 2 s | um mês que não existe custa três pedidos e 3 s; nenhum número muda |

## 8. Ressalvas da auditoria externa da 2A sem destino

| Ponto | Resultado | Evidência | Consequência |
|---|---|---|---|
| Tesouraria: `QT_ACAO_TOTAL_TESOURO` = 0 com as espécies ≠ 0 | **refutado nos dados** | nenhuma linha na Composição do Capital da DFP 2025 | nenhuma hoje |
| Versão e grupo nas linhas 3.99 | **refutado** | nenhum documento da DRE 2025 com mais de uma `VERSAO`; as 2.310 linhas 3.99 são do grupo "DF Consolidado - Demonstração do Resultado" | nenhuma |
| Código × regras de domínio da ficha 1.1 (itens 10 a 12) | **confirmado em funções, não alcançável pela cascata em parte** | `composicao_do_documento` sem a coluna `QT_ACAO_ORDIN_CAP_INTEGR` devolve ON = 0 (insumo ausente vira zero); `roe_dos_controladores(nan, 10)` devolve `(nan, None)` e com PL infinito `(0.0, None)` (insumo inválido sem abstenção); `derivar_por_acao` com preço infinito devolve P/L e P/VP infinitos; unit com 0,5 ação por unit é aceita. Prejuízo e PL negativo são tratados como dado (escala inferida com prejuízo; ROE com PL ≤ 0 se abstém), como a ficha manda | a cascata já barra preço não finito (`_as_float`), e o parser só gera quantidades inteiras; a coluna ausente e o ROE com insumo inválido seguem possíveis |
| Divergência de ações com mais de uma classe preferencial | **confirmado** | a CVM agrega PNA e PNB: USIM5, 547.818.424 − 19.609.792 = 528.208.632 contra 528.130.869 do yfinance (−0,01%, porque a PNB é pequena); BRSR5 e BRSR6 sem quantidade no yfinance | o alerta compara a classe do yfinance com o total da espécie; não determinado para BRSR5/6 |
| Completude penaliza bancos e FIIs | **confirmado** | `DataQualityReport.completude`: banco com tudo menos `divida_liq_ebitda`, `margem_liquida` e `receita_liquida` (que o modelo não preenche) fica em 70%; FII só com preço, DY e P/VP, em 30% | o selo de qualidade rebaixa banco e FII por campos que não se aplicam |
| BTCI11 e TRPL11 como UNKNOWN | **confirmado** | no índice, `cotahist:cota_de_fundo`, motivo "cota de fundo listada que não é FII do Informe Mensal nem ETF identificado"; os ISINs (`BRBTCICTF005` e `BRTRPLCTF015`) não aparecem no `Codigo_ISIN` do Informe Mensal de FII 2026; mas BTCI11 está em `FIIS_CONHECIDOS` (`config.py:51`) e TRPL11 em `UNITS_CONHECIDAS` (`config.py:57`) | o índice vence as listas, e os dois saem sem métodos; a categoria real dos fundos (cadastro de fundos da CVM) não foi consultada: não determinado |
| `divulgados_coerentes` sem guarda de NaN e zero | **confirmado na função, não alcançável pelo provedor** | NaN e 0 com prejuízo viram `LpaDivulgado(nan)` e `LpaDivulgado(0.0)`; `lpa_basico_por_classe` já descarta NaN e zero, e uma linha NaN junto de uma válida fica só a válida | risco só para outro chamador |
| Pares 3.09.01 e 3.09.02 no modelo empresa | **refutado** | a tabela de contas tem `3.09.01` e `3.09.02` no modelo empresa | nenhuma |
| Submodelos de banco (2.07/2.08) e de seguradora dando "sem correspondência" | **refutado nos dados** | os 9 bancos e as 6 seguradoras do índice com DFP consolidada 2025 leem o lucro dos controladores, o dos não controladores e o PL dos não controladores sem abstenção | risco latente: com PL em 2.08 e sem a linha 2.08.09, a 2.07.02 com outra descrição daria "sem correspondência" (que bloqueia a reserva da D20) no lugar de "linha ausente" |
| Preposição "a"/"aos" nas descrições | **refutado** | as duas formas aparecem na DRE ("Atribuído a Sócios…", "Atribuído aos Sócios…"); a tabela traz as duas, e as leituras dos controladores são feitas em qualquer modelo (F2A-41) | nenhuma |
| `series_cvm._meses` ignora o dia | **confirmado** | de 31/01/2026 a 01/03/2026 conta 3 meses | só afeta documento com início ou fim fora do mês cheio; os da CVM começam no dia 1 |
| Proventos ausentes quando só há dividendos ou só JCP | **confirmado (comportamento documentado)** | `series_cvm.proventos(10, None)` e `(None, 10)` devolvem `None` | companhia sem a linha de JCP (ou de dividendos) na DVA fica sem proventos no TTM e na série |
| `divida_liquida.medir` com subconta de 3º nível ausente | **refutado nos dados** | as contas 1.01.01, 1.01.02, 2.01.04 e 2.02.01 estão nas 427 companhias com PL consolidado na DFP 2025; sem uma delas, a medida se abstém com o motivo | nenhuma hoje |
| Corrida no arquivo temporário da proveniência | **confirmado** | duas gravações simultâneas do mesmo registro (`proveniencia.registrar_arquivo`, com a troca de nome sincronizada por barreira): `["FileNotFoundError", "gravado"]` | download concorrente do mesmo arquivo pode falhar ao gravar a proveniência |
| CNPJ com espaços em `entrega_no_indice` | **confirmado** | `" 11.111.111/0001-11 "` não casa com o CNPJ sem espaços (`None`) | entrega não encontrada se a fonte trouxer espaços |
| `classe_preferencial` sem caixa alta | **confirmado na função, refutado nos dados** | `especie_da_classe("pna")` devolve `"pna"`; a montagem não põe a sigla da ação avulsa em caixa alta (só a lista `classes_preferenciais`); nenhuma sigla minúscula no índice atual | risco latente |
| Validação de ticker na tabela de correções | **confirmado** | `validar_correcoes` aceita a linha com ticker `"INVALIDO"` | uma linha mal digitada entra no índice |

Os pontos **confirmados** das perguntas 7 e 8 viram teste de regressão no F2B-43; o destino de cada um (item novo nesta fila ou proposta da 2C) é do Marcos, no marcador. Os refutados ficam só aqui.
