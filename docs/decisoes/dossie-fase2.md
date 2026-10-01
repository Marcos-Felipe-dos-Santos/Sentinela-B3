# Dossiê de decisão da Fase 2

**Não é consultoria financeira.** Upside, fair value e classificações aqui são saídas mecânicas dos métodos da V1 sob revisão metodológica.

**Gerado por** `scripts/dossie_fase2.py` em 2026-10-01 (F0-6). Amostra: os tickers dos mapas atuais (50 ações, 30 FIIs), **nunca** a carteira.
Rede só para leitura: CVM (DFP, FCA, Informe Mensal de FII), Tesouro Direto, Banco Central (SGS, IF.data) e yfinance. Nenhum módulo de produção foi alterado.
Este documento **não decide nada**: reúne os números para as decisões D-* e os itens da Fase 2 (A, B e C) do `docs/PLANO.md`.

**Achados principais (detalhe nas seções):**
- **Mapa manual ticker → CD_CVM desalinhado** (seção 0): quase todas as entradas apontam para outra empresa; não estava na auditoria de 9/9.
- **Escala da quantidade de ações** (seção 1): parte das empresas informa a Composição do Capital em milhares, sem coluna de escala no CSV.
- **Selic dirige Bazin e Gordon** (seção 2) e o regime misto de taxas multiplica o fair value do Gordon por 1.6× a 1.8× só pela mistura real/nominal (seção 3).
- **Cobertura** (seção 7): o cadastro oficial permite mapear as ações listadas e os FIIs automaticamente; o ticker do FII sai do ISIN.

> Limites conhecidos: (1) a NTN-B é o **fallback do código** (o Tesouro Direto falhou), e as seções 2, 3, 4 e 6 dependem dela; (2) o DY é de bases diferentes — seções 2 e 3 usam o `dividendYield` do yfinance via `_normalizar_dy` (armadilha 4), seções 4 e 5 usam proventos dos últimos 12 meses ÷ preço; (3) a seção 5 recalcula Graham e Bazin sem as travas de entrada da V1 (limites de P/L e P/VP, piso de P/L, separação crescimento × renda); (4) o FCA lido é só o do ano corrente, então ticker "sem negociação ativa" pode ser entrega pendente; (5) o IF.data só foi testado com os relatórios 5 e 8, sem uma chamada de controle; (6) a seção 2 recalcula com k real só o Gordon (seção 3) e o FII (seção 4), não Bazin nem Graham por método.
>
> O yfinance é fonte não oficial e o `sharesOutstanding` dele é o objeto de teste do E-1; os números de mercado mudam a cada execução (a Selic, a NTN-B e os preços são os do dia da geração).

## 0. Mapa manual ticker → CD_CVM

Para cada um dos 50 tickers do mapa manual (`cvm_ticker_map.py`), comparei o `CD_CVM` do mapa com o oficial (código de negociação ativo no FCA → CNPJ → cadastro da CVM). Resultado: **1 batem**; **11** têm o ticker sem negociação ativa no FCA (troca de código, incorporação ou saída da bolsa) ou com o código da empresa certa: não dá para afirmar erro, e o nome da empresa do código deve ser julgado à mão; **38 apontam para outra empresa** ou para código inexistente. Na V1 isso atribui os fundamentos da CVM (lucro, PL, ROE) de uma empresa a outro ticker, sem alerta: o resultado sai com a mesma cara de dado oficial. Esta falha não está na auditoria de 9/9 (o E-1 trata do escopo das ações, não do código da empresa).

**Código do mapa de outra empresa (38):**

| Ticker | CD_CVM no mapa | Empresa a que esse código pertence | CD_CVM oficial | Empresa oficial do ticker |
|---|---|---|---|---|
| VALE3 | 19348 | ITAÚ UNIBANCO HOLDING S.A. | 4170 | VALE S.A. |
| ITUB4 | 1384 | BANCO ALFA DE INVESTIMENTO S.A. | 19348 | ITAÚ UNIBANCO HOLDING S.A. |
| BBDC4 | 5258 | RAIA DROGASIL S.A. | 906 | BANCO BRADESCO S.A. |
| ABEV3 | 906 | BANCO BRADESCO S.A. | 23264 | AMBEV S.A. |
| B3SA3 | 4170 | VALE S.A. | 21610 | B3 S.A. - BRASIL, BOLSA, BALCÃO |
| WEGE3 | 14311 | COMPANHIA PARANAENSE DE ENERGIA COPEL | 5410 | WEG SA |
| RENT3 | 21610 | B3 S.A. - BRASIL, BOLSA, BALCÃO | 19739 | LOCALIZA RENT A CAR SA |
| BBAS3 | 6050 | FINANCIADORA BCN SA CFI | 1023 | BANCO DO BRASIL S.A. |
| SUZB3 | 18660 | CPFL ENERGIA SA | 13986 | SUZANO S.A. |
| RADL3 | 14109 | RANDONCORP S.A. | 5258 | RAIA DROGASIL S.A. |
| LREN3 | 21490 | ALUPAR INVESTIMENTO S/A | 8133 | LOJAS RENNER SA |
| RAIL3 | 17566 | ARGOLIS HOLDINGS S.A. | 17450 | RUMO S.A. |
| HAPV3 | 23264 | AMBEV S.A. | 24392 | HAPVIDA PARTICIPAÇÕES E INVESTIMENTOS S.A. |
| GGBR4 | 20036 | BRASILAGRO CIA BRAS DE PROP AGRICOLAS | 3980 | GERDAU S.A. |
| EQTL3 | 18112 | COMPANHIA DE BEBIDAS DAS AMÉRICAS-AMBEV | 20010 | EQUATORIAL S.A. |
| VIVT3 | 19313 | AES ELPA SA | 17671 | TELEFÔNICA BRASIL S.A. |
| TOTS3 | 14664 | SCHULZ SA | 19992 | TOTVS S.A |
| MGLU3 | 24295 | VIBRA ENERGIA S/A | 22470 | MAGAZINE LUIZA SA |
| CMIG4 | 14010 | PREDILETO ALIMENTOS SA | 2453 | CIA ENERG MINAS GERAIS - CEMIG |
| CSAN3 | 20885 | BANCO VOITER S.A. | 19836 | COSAN S.A. |
| HYPE3 | 12130 | COMPANHIA PARAIBUNA DE METAIS | 21431 | HYPERA S/A |
| KLBN11 | 21202 | VIX LOGÍSTICA S/A | 12653 | KLABIN S.A. |
| ASAI3 | 23892 | CONCESSIONÁRIA BR-040 S.A. | 25372 | SENDAS DISTRIBUIDORA S.A. |
| SBSP3 | 23337 | SCCI - SECURITIZADORA DE CRÉDITOS IMOBILIÁRIOS S.A. | 14443 | CIA SANEAMENTO BÁSICO ESTADO SÃO PAULO |
| TIMS3 | 21067 | MOURA DUBEUX ENGENHARIA S/A | 24929 | TIM S.A. |
| ENEV3 | 19712 | GODOI SECURITIES - CIA SECURITIZADORA DE CREDITOS IMOBILIARIOS | 21237 | ENEVA S.A. |
| LWSA3 | 22187 | PRIO S.A. | 24910 | LWSA S/A |
| RECV3 | 24414 | DASS NORDESTE CALÇADOS E ARTIGOS ESPORTIVOS S.A. | 25780 | PETRORECÔNCAVO S.A. |
| USIM5 | 8133 | LOJAS RENNER SA | 14320 | USINAS SID DE MINAS GERAIS S.A.-USIMINAS |
| COGN3 | 23124 | COMPANHIA FERRÍFERA BRASILEIRA S.A. | 17973 | COGNA EDUCAÇÃO S.A. |
| CYRE3 | 14435 | BOMPREÇO BAHIA SA | 14460 | CYRELA BRAZIL REALTY S.A.EMPREEND E PART |
| MRVE3 | 11312 | OI S.A. - EM RECUPERAÇÃO JUDICIAL | 20915 | MRV ENGENHARIA E PARTICIPAÇÕES S/A |
| GOAU4 | 7278 | (código inexistente no cadastro) | 8656 | METALURGICA GERDAU SA |
| SLCE3 | 11541 | (código inexistente no cadastro) | 20745 | SLC AGRICOLA SA |
| BRML3 | 21539 | REP REAL ESTATE PARTNERS DESENV IMOB SA | 19909 | BR MALLS PARTICIPAÇOES S.A. |
| BEEF3 | 23906 | NASA SECURITIZADORA S.A. | 20931 | MINERVA S/A |
| DESK3 | 23256 | CONSULT SECURITIZADORA S/A | 26026 | DESKTOP S.A |
| QUAL3 | 12300 | IPIRANGA PETROQUIMICA SA | 22497 | QUALICORP CONSULTORIA E CORRETORA DE SEGUROS S.A. |

**Sem negociação ativa no FCA, a julgar pelo nome (11):**

| Ticker | CD_CVM no mapa | Empresa a que esse código pertence | CD_CVM oficial | Empresa oficial do ticker |
|---|---|---|---|---|
| BRFS3 | 4983 | (código inexistente no cadastro) | None | n/d |
| JBSS3 | 22470 | MAGAZINE LUIZA SA | None | n/d |
| CSNA3 | 4308 | CIMENTO TUPI SA | None | n/d |
| EMBR3 | 18376 | ISA ENERGIA BRASIL S.A. | None | n/d |
| CPLE6 | 15300 | RUMO MALHA NORTE S.A. | None | n/d |
| ELET3 | 18074 | ALBAE PARTICIPACOES SA | None | n/d |
| NTCO3 | 24104 | CONCESSIONÁRIA DA RODOVIA MG-050 S.A. | None | n/d |
| AZUL4 | 22616 | BANCO BTG PACTUAL S/A | None | n/d |
| GOLL4 | 19569 | GOL LINHAS AEREAS INTELIGENTES SA | None | n/d |
| PETZ3 | 24040 | GAIA CRED SECURITIZADORA DE CRÉDITOS FINANCEIROS S.A. | None | n/d |
| SOMA3 | 22977 | FERREIRA GOMES ENERGIA S.A. | None | n/d |

Todo o restante deste dossiê usa o **mapeamento oficial** (FCA), e não o mapa manual, para não propagar o erro.

## 1. E-1 — ações da CVM × `sharesOutstanding`

Amostra: 38 das 50 ações com Composição do Capital da CVM e `sharesOutstanding` do yfinance. Ações da CVM = ON + PN − tesouraria. **Escala (armadilha 10):** o CSV não traz coluna de escala e **9 empresas** informam a quantidade em milhares (fator ≈ 1000 contra o yfinance); aqui elas foram multiplicadas por 1000 antes de comparar. Sem esse ajuste a divergência dessas empresas seria de ~100.000%.

- A escala é inferida (razão yfinance/CVM entre 100 e 5000), e o yfinance é o objeto do teste: empresas com divergência acima de 5% **sem** reescala (PETR4, BBDC4, GGBR4, HYPE3, KLBN11, SBSP3, USIM5, GOAU4) podem ter escala em milhares não detectada; para elas, LPA e VPA das seções seguintes podem estar errados por fator 1000.
- Divergência acima de 5% (já na escala corrigida): **10 de 38** (26%).
- Empresas com ON e PN (a menor classe com mais de 2% do total, para não contar golden share): **9**; destas, 8 divergem mais de 5%.
- Efeito no LPA, VPA e P/L: lucro e PL da CVM são da companhia inteira; dividir pelas ações de uma classe só muda LPA e VPA por `ações totais ÷ ações da classe` e o P/L na proporção inversa. A coluna *Efeito* é `LPA com yfinance ÷ LPA com ações totais − 1`: positivo = LPA inflado, negativo = LPA subestimado.

| Ticker | Ações CVM (mi) | Ações yfinance (mi) | Divergência | ON+PN | Efeito no LPA/VPA | Escala em milhares (inferida, não lida) |
|---|---|---|---|---|---|---|
| SBSP3 | 700 | 3,517 | 402.2% | não | -80.1% | não |
| KLBN11 | 6,135 | 1,215 | -80.2% | sim | 405.0% | não |
| PETR4 | 12,889 | 5,447 | -57.7% | sim | 136.6% | não |
| USIM5 | 1,231 | 528 | -57.1% | sim | 133.1% | não |
| ITUB4 | 11,027 | 5,404 | -51.0% | sim | n/d | sim |
| BBDC4 | 10,577 | 5,287 | -50.0% | sim | 100.1% | não |
| GGBR4 | 1,975 | 1,245 | -37.0% | sim | 58.7% | não |
| GOAU4 | 1,325 | 836 | -36.9% | sim | 58.5% | não |
| CMIG4 | 2,861 | 1,904 | -33.4% | sim | 50.2% | sim |
| HYPE3 | 633 | 704 | 11.2% | não | -10.1% | não |

## 2. Taxas: Selic de 10% a 15% e k real

Entradas: 35 ações com CVM oficial (último DFP, ações da Composição do Capital na escala corrigida; preço da própria ticker, aproximação para duas classes), yfinance (preço, DY) e o `ValuationEngine` real, com `get_selic_atual` substituída por cada valor da grade (mesma ideia da fixture do F0-2). **Mediana do upside implícito de cada método** (n = ações em que o método calcula; o upside final conta só as ações com pelo menos um método).

| Selic | Graham | Bazin | Lynch | Gordon | Upside final | Classificação (agrupada) |
|---|---|---|---|---|---|---|
| 10.00% | 63.9% (n=16) | -20.7% (n=13) | 672.6% (n=3) | -27.7% (n=9) | -10.5% (n=21) | alto risco 1, neutro/outros 16, sinal negativo 10, sinal positivo 8 |
| 10.50% | 63.9% (n=16) | -24.5% (n=13) | 672.6% (n=3) | -30.7% (n=9) | -14.7% (n=21) | alto risco 1, neutro/outros 16, sinal negativo 10, sinal positivo 8 |
| 11.00% | 63.9% (n=16) | -27.9% (n=13) | 672.6% (n=3) | -33.4% (n=9) | -18.5% (n=21) | alto risco 1, neutro/outros 16, sinal negativo 11, sinal positivo 7 |
| 11.50% | 63.9% (n=16) | -31.0% (n=13) | 672.6% (n=3) | -35.9% (n=9) | -20.8% (n=21) | alto risco 1, neutro/outros 15, sinal negativo 12, sinal positivo 7 |
| 12.00% | 63.9% (n=16) | -33.9% (n=13) | 672.6% (n=3) | -38.3% (n=9) | -21.9% (n=21) | alto risco 1, neutro/outros 15, sinal negativo 12, sinal positivo 7 |
| 12.50% | 63.9% (n=16) | -36.5% (n=13) | 672.6% (n=3) | -40.5% (n=9) | -23.0% (n=21) | alto risco 1, neutro/outros 14, sinal negativo 13, sinal positivo 7 |
| 13.00% | 63.9% (n=16) | -39.0% (n=13) | 672.6% (n=3) | -42.6% (n=9) | -24.0% (n=21) | alto risco 1, neutro/outros 14, sinal negativo 13, sinal positivo 7 |
| 13.50% | 63.9% (n=16) | -41.3% (n=13) | 672.6% (n=3) | -44.7% (n=9) | -24.9% (n=21) | alto risco 1, neutro/outros 14, sinal negativo 13, sinal positivo 7 |
| 13.75% | 63.9% (n=16) | -42.3% (n=13) | 672.6% (n=3) | -45.8% (n=9) | -25.3% (n=21) | alto risco 1, neutro/outros 14, sinal negativo 13, sinal positivo 7 |
| 14.00% | 63.9% (n=16) | -43.4% (n=13) | 672.6% (n=3) | -46.9% (n=9) | -26.6% (n=21) | alto risco 1, neutro/outros 14, sinal negativo 13, sinal positivo 7 |
| 14.50% | 63.9% (n=16) | -45.3% (n=13) | 672.6% (n=3) | -48.9% (n=9) | -29.4% (n=21) | alto risco 1, neutro/outros 14, sinal negativo 14, sinal positivo 6 |
| 15.00% | 63.9% (n=16) | -47.2% (n=13) | 672.6% (n=3) | -50.7% (n=9) | -31.9% (n=21) | alto risco 1, neutro/outros 14, sinal negativo 14, sinal positivo 6 |

Leitura: o Graham e o Lynch não dependem da Selic (colunas constantes); Bazin e Gordon andam com ela, e o upside final acompanha o ciclo — a nota muda sem que o negócio mude (armadilha 5). A coluna Lynch tem poucos casos e valores extremos: trate como sinal de problema de insumo (DY e preço do yfinance misturados com LPA da CVM), não como resultado. Os rótulos da V1 aparecem agrupados (sinal positivo, neutro, sinal negativo); o upside é saída mecânica do método, não recomendação.

**Taxa real.** NTN-B longa = 7.00% (**valor de fallback do código**: Falha NTN-B Tesouro Direto: 403 Client Error: Forbidden for url: https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/service/api/t), IPCA 12m = 4.22% (BCB SGS 433), Selic = 13.75%.

| Prêmio | k real (NTN-B + prêmio) | k nominal equivalente | k atual (Selic + 7%) |
|---|---|---|---|
| 4% | 11.00% | 15.69% | 20.75% |
| 5% | 12.00% | 16.73% | 20.75% |
| 7% | 14.00% | 18.81% | 20.75% |

## 3. Gordon: regime atual × opção A × opção B

Elegíveis ao Gordon na amostra (DY confiável > 4% e ROE > 10%): **9**. Coluna: mediana do upside implícito do método; última coluna: casos em que `k ≤ g` e o método não calcula.

| Regime | Elegíveis | Mediana do upside | k ≤ g |
|---|---|---|---|
| Regime atual: k = Selic + 7%, g nominal | 9 | -45.9% | 0 |
| Misto (k real, g nominal) — o erro da armadilha 1; prêmio 4% | 9 | 70.1% | 0 |
| Opção A: k e g reais (g − IPCA); prêmio 4% | 9 | -18.0% | 0 |
| Opção B: tudo nominal (k = (1+k real)(1+IPCA) − 1); prêmio 4% | 9 | -18.4% | 0 |
| Misto (k real, g nominal) — o erro da armadilha 1; prêmio 5% | 9 | 39.6% | 0 |
| Opção A: k e g reais (g − IPCA); prêmio 5% | 9 | -25.6% | 0 |
| Opção B: tudo nominal (k = (1+k real)(1+IPCA) − 1); prêmio 5% | 9 | -25.9% | 0 |
| Misto (k real, g nominal) — o erro da armadilha 1; prêmio 7% | 9 | -2.3% | 0 |
| Opção A: k e g reais (g − IPCA); prêmio 7% | 9 | -37.2% | 0 |
| Opção B: tudo nominal (k = (1+k real)(1+IPCA) − 1); prêmio 7% | 9 | -37.5% | 0 |

**Quanto vale o erro de mistura.** Razão do fair value do regime misto contra (i) a opção B com o mesmo prêmio, que isola o erro de mistura real/nominal, e (ii) o regime atual, que soma o erro e a troca do nível da taxa (mediana por ação):

| Prêmio | Misto ÷ opção B (só a mistura) | Misto ÷ regime atual (mistura + nível) |
|---|---|---|
| 4% | 1.84× | 2.75× |
| 5% | 1.72× | 2.33× |
| 7% | 1.56× | 1.79× |

Observação algébrica: com `g` deflacionado pelo quociente de Fisher, as opções A e B dão exatamente o mesmo valor (a diferença `k − g` e o fator `1 + g` escalam por `1 + IPCA`). Na tabela, A usa `g − IPCA` (subtração simples, a aproximação mais comum), por isso difere de B. O resultado que importa é o do regime **misto**, que reproduz o erro da armadilha 1.

## 4. FII: Selic líquida × spread sobre a NTN-B

Selic = 13.75%, Selic líquida (× 0,85) = 11.69%; NTN-B longa nominal = (1 + 7.00%) × (1 + IPCA 4.22%) − 1 = 11.52%. DY = proventos dos últimos 12 meses ÷ preço (yfinance, sem ajuste de vacância). Colunas de upside: `DY ÷ taxa − 1`, com o preço cancelando no fair value (F-9). Assimetria: a Selic líquida já desconta 15% de IR e a NTN-B nominal está bruta, então parte da diferença de nível entre as colunas é tributária, não de spread. Upside é saída mecânica do método; um DY muito alto (como o de alguns FIIs abaixo) costuma indicar risco, não oportunidade.

- 26 dos 30 FIIs do mapa com preço e proventos no yfinance (sem cotação no yfinance: BCFF11, CVBI11, IRDM11, MALL11; ticker possivelmente encerrado ou renomeado); **10** têm DY acima da Selic líquida.

| FII | DY 12m | P/VP | Upside vs Selic líquida | NTN-B + 1% | NTN-B + 2% | NTN-B + 3% |
|---|---|---|---|---|---|---|
| ALZR11 | 10.1% | n/d | -13.6% | -19.3% | -25.3% | -30.4% |
| BRCR11 | 11.9% | 0.48 | 1.7% | -5.1% | -12.1% | -18.1% |
| BTLG11 | 9.7% | 0.93 | -17.2% | -22.7% | -28.4% | -33.4% |
| CPTS11 | 14.3% | n/d | 22.7% | 14.6% | 6.1% | -1.2% |
| GTWR11 | 13.9% | n/d | 18.7% | 10.8% | 2.6% | -4.5% |
| HCTR11 | 25.8% | n/d | 120.6% | 105.9% | 90.7% | 77.6% |
| HFOF11 | 11.3% | n/d | -3.3% | -9.7% | -16.4% | -22.2% |
| HGBS11 | 10.7% | 0.88 | -8.5% | -14.6% | -20.9% | -26.4% |
| HGLG11 | 9.1% | 0.93 | -22.3% | -27.5% | -32.9% | -37.5% |
| HGRU11 | 9.5% | n/d | -18.3% | -23.7% | -29.4% | -34.2% |
| HSML11 | 10.4% | n/d | -10.9% | -16.9% | -23.0% | -28.3% |
| JSRE11 | 9.4% | 0.56 | -19.8% | -25.1% | -30.6% | -35.4% |
| KNCR11 | 13.5% | 1.04 | 15.2% | 7.6% | -0.4% | -7.2% |
| KNRI11 | 8.4% | 0.97 | -27.7% | -32.5% | -37.5% | -41.8% |
| MXRF11 | 13.1% | 0.92 | 12.4% | 4.9% | -2.8% | -9.5% |
| PVBI11 | 7.6% | n/d | -34.6% | -39.0% | -43.5% | -47.4% |
| RBRF11 | 6.8% | n/d | -42.0% | -45.9% | -49.9% | -53.3% |
| RBRP11 | 9.1% | n/d | -21.7% | -26.9% | -32.3% | -37.0% |
| RCRB11 | 9.7% | 0.63 | -16.8% | -22.3% | -28.1% | -33.0% |
| RECR11 | 14.5% | n/d | 24.4% | 16.1% | 7.5% | 0.1% |
| TRXF11 | 15.5% | n/d | 32.3% | 23.5% | 14.4% | 6.5% |
| VISC11 | 9.6% | n/d | -17.9% | -23.3% | -29.0% | -33.9% |
| VRTA11 | 14.4% | 0.77 | 23.6% | 15.4% | 6.9% | -0.5% |
| XPCI11 | 13.7% | n/d | 17.5% | 9.7% | 1.6% | -5.4% |
| XPLG11 | 10.7% | n/d | -8.6% | -14.7% | -21.0% | -26.5% |
| XPML11 | 10.9% | n/d | -6.6% | -12.8% | -19.2% | -24.8% |
| Mediana | 10.7% | 0.90 | -8.6% | -14.7% | -21.0% | -26.4% |

Leitura: trocar a Selic líquida por um spread sobre a NTN-B muda o nível de todos os fair values de uma vez e não muda a ordem entre os fundos — a ordem vem só do DY. O P/VP (âncora patrimonial) continua fora do valor.

## 5. Cinco anos × último ano

Amostra: 35 ações com pelo menos 3 anos de CVM com lucro e PL (3 a 5 anos usados por ação, de 5 possíveis); ações constantes = as atuais; dividendos por ação por ano-calendário, com anos sem pagamento contados como zero e o "último ano" sendo os 12 meses até hoje. As fórmulas de Bazin, Lynch e Gordon são recalculadas aqui com os parâmetros do `MacroContext` e a Selic de hoje; o "cinco anos" troca LPA, ROE e DY pela média do período.

| Método | Ações em que calcula nos dois casos | Mediana da variação do valor |
|---|---|---|
| Graham | 29 | -2.6% |
| Bazin | 9 | 1.7% |
| Lynch | 1 | -21.8% |
| Gordon | 7 | -8.9% |

O LPA médio difere do último ano em mais de 25% em **14** das 35 ações.

## 6. Bancos

Bancos da amostra (setor CVM contendo "Banco"): **3**: ITUB4, BBDC4, BBAS3. Sem lucro ou PL utilizáveis nas contas genéricas, fora da tabela: ITUB4.

**Fonte oficial.** O IF.data do Banco Central (Olinda, serviço `IFDATA`) publica Resumo, Ativo, Passivo, DRE, Informações de Capital (índice de Basileia, relatório 5) e carteira por nível de risco (relatório 8, base da inadimplência). Estado das chamadas nesta execução: 202512/rel.5: HTTP 500; 202512/rel.8: HTTP 500; 202509/rel.5: HTTP 500; 202509/rel.8: HTTP 500; 202506/rel.5: HTTP 500; 202506/rel.8: HTTP 500. Nenhuma das chamadas aos relatórios 5 e 8 retornou HTTP 200 (status na lista acima); o catálogo `ListaDeRelatorio` lista os dois, então a fonte existe, mas a disponibilidade da API não foi confirmada. Repetir a coleta antes de depender dela.

**Atenção ao ROE:** a V1 calcula lucro e PL com as contas genéricas da CVM (3.11 e 2.03), as mesmas para bancos (F-13). Para banco o resultado não é confiável: um ROE muito abaixo do divulgado pelo próprio banco, ou ausente, indica conta errada, não resultado ruim.

**P/VP justificado** = (ROE − g) ÷ (k − g), com ROE do último DFP, g = IPCA + 1% (nominal) e k = taxa real (NTN-B 7.00% + prêmio) levada a nominal. ROE = lucro ÷ PL da CVM; P/VP = preço ÷ (PL ÷ ações totais da CVM). **A tabela abaixo não é confiável** (contas genéricas aplicadas a banco, F-13): ROE muito baixo ou muito alto é o sintoma; ela mostra o método, não serve para decidir.

| Banco | ROE | P/VP | P/VP justificado (prêmio 5%) | P/VP justificado (prêmio 7%) |
|---|---|---|---|---|
| BBDC4 | 5.4% | 0.44 | 0.02 | 0.01 |
| BBAS3 | 43.4% | 3.40 | 3.32 | 2.81 |

## 7. Cobertura e classe do ativo

- **Companhias abertas com ação, preferencial ou unit negociada em bolsa** (FCA 2026): 366 empresas, **482 tickers** com o código de negociação oficial da CVM — dá para montar `ticker ↔ CNPJ ↔ CD_CVM` automaticamente, contra **50** no mapa manual (cobertura atual ≈ 10%).
- **FIIs listados em bolsa** (Informe Mensal da CVM, `Mercado_Negociacao_Bolsa = S`): **710** fundos, contra **30** no mapa manual. O CNPJ e o segmento (`Segmento_Atuacao`, 10 valores distintos) vêm da CVM; o ticker não vem. Regra testada: letras 3–6 do ISIN + "11" acertou 27 de 27 FIIs do mapa atual (100%) — serve de ponto de partida, não de regra final. Este script não consulta a B3: uma lista de fundos da B3 seria a fonte alternativa do ticker (não avaliada).
- **Units** (terminam em 11): 10 no FCA; o classificador atual trata como FII as que não estão em `UNITS_CONHECIDAS`: **2** (BRBI11, IGTI11).
- **ETFs e BDRs:** a regra do classificador é só o sufixo, então o resultado vale para qualquer ticker desses tipos. Exemplos conhecidos (não é contagem exaustiva: o script não consulta fonte de ETF ou BDR com ticker):

| Ticker | Tipo real | Classe atribuída |
|---|---|---|
| BOVA11 | ETF de índice | FII |
| IVVB11 | ETF de índice | FII |
| HASH11 | ETF de cripto | FII |
| AAPL34 | BDR | STOCK |
| MSFT34 | BDR | STOCK |
| TAEE11 | unit | UNIT |
| KLBN11 | unit | UNIT |
| HGLG11 | FII | FII |

## 8. Perguntas que o Marcos precisa responder

0. **Mapa manual (novo, seção 0):** a maioria dos `CD_CVM` do `cvm_ticker_map.py` aponta para outra empresa. Antes de qualquer item da Fase 2A, você autoriza corrigir o mapa já na Fase 1 (ou até antes, como item de `fix:`), em vez de esperar o mapa automático do F2A-1? Enquanto isso não acontece, os fundamentos CVM da V1 estão trocados entre tickers.
1. **E-1 (F2A-3):** quando as ações da CVM e do yfinance divergirem mais de 5%, o caminho é usar sempre as ações da Composição do Capital (ON + PN − tesouraria) ou abster-se do LPA/VPA derivado? E, com duas classes, o preço de qual classe entra no P/L?
2. **Taxa de desconto (F2B-1):** qual prêmio sobre a NTN-B (a tabela da seção 2 mostra 4%, 5% e 7%) e qual regime para o Gordon: tudo real ou tudo nominal? (A seção 3 mostra que, bem feitos, dão o mesmo valor; o regime misto é o que não pode existir.) A NTN-B usada pode ser o fallback do código (a seção 2 diz qual): repita a coleta com o Tesouro Direto disponível antes de fixar o prêmio.
3. **FII (F2B):** o fair value do FII passa a comparar o DY com a NTN-B mais spread (qual spread?) ou com a Selic líquida, mantendo o P/VP só como contexto? A seção 4 mostra que o spread desloca o nível e não a ordem.
4. **Janela (F2A-7/F2C-1):** média de 5 anos de LPA e dividendos para todos os métodos, ou só para os cíclicos? A seção 5 mostra o tamanho do efeito.
5. **Bancos (F2B-3):** a lente de bancos usa P/VP justificado pelo ROE (seção 6) e Basileia/inadimplência do IF.data? A API de capital e risco não respondeu; vale tolerar essa dependência?
6. **Cobertura (F2A-1):** o mapa automático parte do FCA da CVM (ações e units) e do Informe Mensal (FIIs); para o ticker dos FIIs, aceita a regra do ISIN com validação manual ou prefere uma fonte da B3?
7. **Classe (F2A-1):** units, ETFs e BDRs entram na V2 como classes próprias (com métodos próprios) ou ficam fora do escopo?
