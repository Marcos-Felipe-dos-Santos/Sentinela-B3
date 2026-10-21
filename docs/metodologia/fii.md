# Rendimento do FII sobre NTN-B — versão 1.1

**Status:** versão 1.1 aprovada pelo Marcos em 20/10/2026, com a conferência pelo
rendimento oficial da B3 e a regra dos eventos de cota da seção 3a. A versão 1.0 foi
aprovada em 19/10/2026. Auditoria FICHA do Claude
sobre a versão 0.3: **pode seguir** (D30); promovida a 1.0 sem mudança de regra
ou número, conforme registro do marcador.
**Decisões:** [marcador](../decisoes/marcador-2b.md).
**Implementação futura:** F2B-2; F2B-28 fornece reconstrução inicial, ainda sem
todas as guardas temporais, de eventos e de atualidade desta ficha.

## 1. Fórmula e referência

`V0 = R_real / (y_real + s)`, com **crescimento real zero**.
Derivação: para q=y_real+s>0 e fluxo real anual constante a partir de t=1,
`V0 = soma[t=1..∞] R_real/(1+q)^t = R_real/q`.
Moeda-base t=0: fim do último mês do Informe usado. A soma retrospectiva é
tratada, por hipótese, como aproximação desse fluxo anual futuro em moeda-base.
Somar valores nominais passados e posicioná-los nessa data é aproximação
explicitada, não prova de atualização contratual nem de sustentabilidade real.
Não há ajuste intramensal pelo IPCA neste proxy; se ele não for representativo,
abster por fluxo não recorrente ou evento, em vez de afirmar fluxo real observado.

Na representação nominal coerente, `R_N,t = R_real × (1+π)^t`,
`1+q_N=(1+q)(1+π)` e `g_N=π`; a soma descontada dá o mesmo V0. O regime
real não autoriza esquecer a transformação dos fluxos (D22). O π de um cenário
de conferência seria o IPCA da mesma janela anual do Informe, conforme taxa-real;
nenhuma inflação Focus é necessária à fórmula real de crescimento zero.

Referência consultada para o desconto de fluxo estável: Damodaran,
*Investment Valuation*, **2ª ed.**, Wiley, 2002,
[cap. 13, seção I, “The Gordon Growth Model”, “The Model”](https://pages.stern.nyu.edu/~adamodar/pdfiles/valn2ed/ch13.pdf).
Correspondência na **3ª ed., 2012, cap. 13: a conferir pelo auditor**.
A perpetuidade acima é derivada, não atribuição de que a NTN-B mais spread
seja taxa universal de FII. Essa taxa é decisão do Marcos. Base do DY: Resolução
CVM 184, Anexo K, Suplemento I, item 7.2, nota 3, conferida na cópia oficial
`resol184.docx` do levantamento: rendimentos **declarados** por cota sobre VP
do fim do mês anterior; não confundir com fluxo pago nem com cotação.

## 2. Insumos

| Insumo | Fonte, unidade e construção |
|---|---|
| DY_m | Informe CVM complemento, Percentual_Dividend_Yield_Mes em razão mensal, não %; maior versão elegível por mês |
| VP_m | Valor_Patrimonial_Cotas em R$/cota do fim do mês; 13 meses para reconstruir 12 rendimentos |
| R | soma de DY_m × VP_(m−1), 12 meses consecutivos, R$/cota na mesma base de cotas |
| Preço | COTAHIST/cascata, R$/cota, mesmo direito; DY_12m=R/preço |
| y_real | Média NTN-B escolhida na taxa-real 0.3, taxa_aplicacao, sem prêmio das ações |
| s | Mediana de 5 anos do grupo tijolo contra a mesma taxa_aplicacao e mesma definição de R e preço; constante datada, depois de recalibrada no F2B-2 |
| Tipo | Informe CVM ativo_passivo; regra de composição de universo-inicial, seção de fontes: fração >50% da soma dos ativos imobiliários identificados |
| Eventos | Cotas_Emitidas, VP e documentos oficiais de eventos da CVM/B3/administrador, disponíveis até as_of; critério de abstenção pela §3a (B3, `fundsCall`) |
| P/VP, Selic e vacância | Só contexto/score existente; não entram em R nem em V0 |

Classificação: recebíveis (CRI/CRA, LCI/LCA, letras hipotecárias, LIG) = papel;
imóveis, terrenos, direitos reais, participações imobiliárias = tijolo; cotas de
FII = fundos de fundos. Denominador é a soma desses grupos, sem caixa/renda
fixa; declarar a fração sobre ativos investidos, não sobre patrimônio total.
Aplicar à composição do mesmo mês do último Informe elegível. Grupo sem maioria
estrita, base zero, dados inválidos ou composição não disponível: desconhecido,
abstenção. A amostra de agosto/2026 não prova o tipo nos cinco anos anteriores.

## 3. Regime, janela e data

Doze meses civis consecutivos até o último mês elegível, com VP do mês anterior
ao primeiro: **13 VPs**. Selecionar cada mês pela maior versão numérica **entregue
até as_of**; sem entrega demonstrada não escolher a versão atual como se histórica.
Maior versão empatada e conflitante abstém. Informe mais recente até **3 meses
civis** antes de as_of, medidos pelo mês de referência; sem deslocar a janela
para esconder buraco. A composição usada na classificação tem a mesma idade
máxima e o mesmo corte. Preço último pregão; NTN-B até 5 dias úteis; publicação,
calendário e datas conforme registro §2. Não anualizar história curta.

**Decisão do Marcos de 19/10/2026 após auditoria da 0.2:** quanto à base de
cotas, abster apenas com **desdobramento ou grupamento**, ou salto de **VP por
cota incompatível com a continuidade**. Não há ajuste desses eventos na 2B.
**Emissão com VP contínuo é aceita** e registrada como contexto, com mês,
quantidades e VP antes/depois. Alteração de Cotas_Emitidas sozinha não é veto:
o rendimento é reconstruído por cota, não pelo total emitido. Conferir a série
dos 13 VPs e documentos oficiais de eventos, sem criar percentual arbitrário
como limite de salto (pela §3a, o critério de abstenção é o evento oficial; a série
de VPs fica como contexto). Um dado inválido ou continuidade não demonstrável ainda
abstém por base incompatível; não confundir falta de prova com emissão constatada.
Verificação cobre as 13 bases e o intervalo até o preço.
Amortização/devolução de capital não é rendimento: não somar Percentual_Amortizacao;
se positiva na janela, ou liquidação/distribuição extraordinária não recorrente
identificada, abster por fluxo não representativo. Contratos indexados não garantem
constância real da distribuição; sustentabilidade permanece hipótese declarada.

## 3a. Revisão 1.1 — conferência oficial e eventos de cota (Marcos, 20/10/2026)

- **Rendimento oficial da B3 é conferência.** A B3 publica o rendimento por cota e mês
  (`fundsProxy/fundsCall/GetListedSupplementFunds`, `cashDividends`: `rate`, `relatedTo`,
  `lastDatePrior`). Ele é comparado, mês a mês, com o rendimento reconstruído do Informe
  (DY_m × VP_(m−1)). Divergência gera aviso com os meses e as diferenças, **sem
  abstenção**; o valor continua o do Informe. Levantamento de 20/10/2026: HGLG11,
  setembro/2026, B3 R$ 1,17 por cota contra R$ 1,170289 reconstruídos.
- **Eventos de cota.** Decisão sobre a proposta do diário do F2B-2 (20/10/2026) para a regra
  "salto de VP incompatível, sem percentual arbitrário" da §3: o critério de abstenção pela
  base de cotas é o evento oficial. Desdobramento ou grupamento oficial na janela (13 bases e
  o intervalo até o preço) abstém; a fonte de eventos indisponível também abstém
  ("continuidade não demonstrável"). Não há limite percentual de variação de VP. Onde as §3 a
  §7 dizem "salto de VP incompatível", vale este critério. Emissão com VP contínuo segue
  aceita, em contexto.
- **Complemento decidido pelo Marcos em 20/10/2026.** (a) A conferência compara o
  rendimento reconstruído, arredondado a duas casas, com o valor da B3: igual é conferido,
  diferente gera aviso; sem tolerância percentual. (b) A lista de eventos vazia só vale como
  "sem evento" se a resposta da B3 for válida (sucesso e estrutura esperada); erro ou
  formato inesperado é fonte indisponível, e o FII se abstém.
- **XPML11**, o caso de controle: a anomalia observada não é desdobramento, e sim DY
  mensal negativo declarado no Informe (−5,8778% em 01/2026), e a guarda de DY_m negativo
  da seção 4 a abstém.

## 4. Escopo e matriz de validade

Só classe oficial FII e tipo **tijolo**. Papel (KNCR11/MXRF11/HCTR11), fundos
de fundos (CPTS11/HFOF11), tipo desconhecido/misto sem maioria: "tipo de FII
fora do escopo na 2B" ou "classificação de FII desconhecida"; aguardam 2C.
HGLG11/KNRI11 precisam ainda cumprir todas as guardas. XPML11 é caso de
controle de salto de VP/desdobramento/grupamento, conforme a evidência do evento (pela §3a, a
evidência observada é DY mensal negativo, não evento de cota);
emissão, isoladamente, não é motivo de exclusão.
Ações, bancos, seguradoras, holdings, units, preferenciais, ETF, BDR e UNKNOWN
não entram: "classe fora do escopo FII". Setor ou ticker não substitui a classe.

Cada linha aplica antes das contas os motivos separados de ausente, não numérico,
NaN e infinito do registro §2.1; contexto inválido é indicado sem alterar o valor.

| Insumo | Zero | Negativo | Fora de faixa / motivo |
|---|---|---|---|
| Preço e cada VP | abstém: não positivo | abstém | unidade/base divergente: base de cota incompatível |
| Cada DY_m | válido como mês sem rendimento, se informado | abstém | >25% mensal: fora da faixa da fronteira atual; não confundir com validação de recorrência |
| DY_12m e R | abstém: rendimento anual não positivo | abstém | DY_12m>25%: rendimento não confiável; 25% é teto de domínio existente, não parâmetro de valor |
| Cotas_Emitidas | abstém: cotas não positivas | abstém | quantidade não inteira: dado inválido; desdobramento/grupamento ou salto de VP incompatível: abstém; emissão com VP contínuo: contexto, sem veto |
| Amortização | válida sem amortização | abstém: dado inválido | positiva: devolução de capital na janela, abstenção |
| Cada posição da classificação | válido | abstém | soma zero, maioria ausente ou fração >1: tipo desconhecido |
| y_real | válido | válido se >−1 e q>0 | ≤−1 ou fonte/idade inválida: taxa indisponível |
| s | zero matematicamente válido, só se mediana comprovada | permitido se mediana comprovada e q>0 | não recalibrado/sem versão: spread indisponível |
| q=y+s | abstém: taxa não positiva | abstém | não finito: taxa inválida |
| Resultado/intermediário | abstém com R>0 | abstém | não finito: resultado não finito |

Não impor fator de 0,85: **spread bruto sobre benchmark bruto**, com a diferença
tributária já na série. Não extrapolar isenção individual; a calibração observada
não é parecer tributário. Sem spread validado não há valor numérico operacional.

## 5. Exemplo independente

**HGLG11**, CNPJ 11.728.688/0001-47, janela 01/10/2025–30/09/2026,
moeda-base de cenário **R$ de 30/09/2026**, as_of 19/10/2026 17:10 Brasília.
Complementos CVM 2025/2026; hashes completos no registro §2.3. Seleção por maior
versão numérica nos snapshots — demonstração aritmética, sem presumir as entregas
históricas ainda não conciliadas. Valores abaixo preservam a precisão publicada:

| Mês | Versão | DY_m | VP_(m−1), R$ |
|---|---|---|---|
| 2025-10 | 1 | 0,006769 | 162,498293155102 |
| 2025-11 | 1 | 0,005901 | 162,238906796951 |
| 2025-12 | 1 | 0,006635 | 165,789388949214 |
| 2026-01 | 1 | 0,006604 | 166,576588317915 |
| 2026-02 | 1 | 0,006610 | 166,408892392171 |
| 2026-03 | 1 | 0,006637 | 165,744203362955 |
| 2026-04 | 2 | 0,006477 | 165,712610785485 |
| 2026-05 | 1 | 0,006607 | 166,490023171738 |
| 2026-06 | 1 | 0,006626 | 166,003651097124 |
| 2026-07 | 1 | 0,007023 | 166,603102910645 |
| 2026-08 | 2 | 0,007027 | 166,431221117306 |
| 2026-09 | 1 | 0,007052 | 165,951408188109 |

VP final de setembro/2026: 165,476630173739 (13º VP).
Soma dos produtos exatos = **R$ 13,240529645135538184/cota**.
Fechamento COTAHIST **30/09/2026 R$ 147,95**, mercado 010:
DY=**8,949327235644%**. Não usar 25/09 só por ser última linha física.

**Continuidade conferida nos 13 VPs dos snapshots:** nas emissões apontadas,
a quantidade aumenta, mas o VP por cota mantém a escala em R$; não ocorre a
multiplicação/divisão de VP de um desdobramento/grupamento.

| Emissão, contexto | Cotas antes → depois | VP anterior → atual, R$/cota | Variação do VP |
|---|---|---|---|
| nov/2025 | 33.787.575 → 42.404.675 | 162,238906796951 → 165,789388949214 | +2,188428301423% |
| abr/2026 | 42.404.675 → 43.455.524 | 165,712610785485 → 166,490023171738 | +0,469132905799% |
| mai/2026 | 43.455.524 → 45.601.745 | 166,490023171738 → 166,003651097124 | −0,292132864990% |

Na série inteira, variações mensais de VP vão de −0,399431196050% a
+2,188428301423%, sem salto de escala aparente; essa faixa é evidência do
exemplo, **não limiar novo de elegibilidade**. Em agosto/2026, a quantidade cai
32 cotas (45.601.745 → 45.601.713), enquanto VP varia −0,288295024200%:
registrar a alteração como contexto, sem inferir desdobramento/grupamento de uma
mudança no total. Sob a nova regra, **as emissões não causam abstenção do HGLG11**.
A leitura mensal não substitui os documentos de eventos nem comprova por si as
datas de entrega de cada versão: tais guardas continuam exigidas em produção.

O rendimento reconstruído permanece **13,240529645135538184 R$/cota** e
DY **8,949327235644%**. Sem a constante de spread recalibrada no F2B-2, ainda
não há valor operacional; esse motivo é distinto da emissão, agora aceita.

Para teste independente da fórmula, cenário **condicional**, não resultado do
HGLG11: R=13,240529645135538184, y=74,38/1100, s=2 pp hipotéticos dão
**R$ 151,116233758550**; emissão com VP contínuo preserva essa conta.
Se s estiver ausente, houver desdobramento/grupamento ou salto de VP incompatível,
o teste espera abstenção.
Confronto com avisos oficiais para validar o rendimento: pela §3a, é a conferência com o
rendimento oficial por cota da B3, com aviso; o próprio Informe não é segunda fonte
independente.

## 6. Sensibilidade e recalibração

Mesma definição de R em todos os cenários condicionais acima:

| Spread hipotético | Valor aritmético (R$) |
|---|---|
| 1 pp | 170,585414 |
| 2 pp | 151,116234 |
| 3 pp | 135,635897 |

Nenhum desses é a constante escolhida. Os **2,65 pp da 0.1 não são reutilizados**:
foram medidos com taxa_resgate e eventos sem ajuste. Não é correto acrescentar
0,12 pp à mediana antiga: o diferencial histórico e as exclusões variam por mês.

**Pendência autorizada no F2B-2:** usar scripts/levantamento_fase2b.py como base
para recalcular 60 meses encerrados no último mês elegível. Em cada mês: R de
12 meses/fechamento do mês − média da taxa_aplicacao da última data-base elegível
até esse fechamento; mediana entre os tijolos elegíveis, depois mediana das 60
medianas mensais (mesmo peso por mês). Reconstruir disponibilidade, versões,
classificação e eventos à época, inclusive as bases anteriores às janelas.
Mês sem fundos válidos é lacuna, não zero; sem 60 medianas válidas contíguas,
spread indisponível, sem reduzir janela silenciosamente. Publicar número de
fundos/meses antes e depois das exclusões por desdobramento/grupamento ou salto
de VP incompatível (critério da §3a), emissões contínuas mantidas como contexto, meses removidos, mudança da mediana,
p25/p75 e limites da amostra. Comparar 1/2/3 pp e mediana recalibrada sobre o
mesmo rendimento, sem misturar DY da cascata com Informe. Seleção só de fundos
atuais mantém viés de sobrevivência: declarar e medir cobertura; não dizer que
representa todos os listados. A composição atual não classifica todo o passado.

## 6a. Registro da calibração do spread (F2B-2, 21/10/2026)

Executada por `scripts/calibrar_spread_fii.py --mes-final 2026-09`, pelas regras da seção 3
do plano final da 2B (`docs/decisoes/plano-final-2b.md`), sobre os arquivos do levantamento
do F2B-21 (`outputs/levantamento_cache/f2b21/`: Informes de 2019 a 2026, COTAHIST anuais de
2020 a 2026 e o histórico do Tesouro, SHA-256 abaixo) e a resposta da B3 (`fundsCall`) de
cada fundo candidato, coletada em 21/10/2026.

- **Spread: 3,5058% ao ano** (0,03505842448151178), mediana das 60 medianas mensais de
  outubro/2021 a setembro/2026. p25 3,1700%; p75 3,7734%. Constante datada em
  `MacroContext.FII_SPREAD_TIJOLO`, com o registro em `FII_SPREAD_CALIBRACAO`; sem
  recalibração em execução.
- **Observação de cada mês:** a lente em produção num as_of no dia seguinte ao último pregão
  do mês: linhas do Informe entregues até esse pregão, Informe de até 3 meses, guardas da §4,
  tijolo pela composição do mês final, sem desdobramento ou grupamento da B3 na janela;
  liquidez do F2A-10 (presença ≥ 80% e volume mediano ≥ R$ 100 mil em 63 pregões); preço
  bruto do COTAHIST no último pregão do mês em que o fundo negociou; NTN-B pela média da
  taxa de aplicação da cesta da taxa real (NTN-B e NTN-B Principal a partir de 2035) na
  última data-base até o pregão (5,66% em outubro/2021; 7,15% em setembro/2026).
- **Fundos por mês:** mínimo 30, mediana 36, máximo 41 (2.162 fundos-mês válidos).
- **População e cobertura:** 1.712 fundos no Informe; 454 ligados a um ticker pelo ISIN do
  `geral` igual ao do COTAHIST (mercado à vista, final 11); 175 sem ISIN no Informe, 1.046
  sem ticker no COTAHIST e 37 com ISIN em mais de um ticker, fora. Só fundos com Informe e
  negociação no período entram: o viés de sobrevivência que sobra não é medido além dessa
  contagem.
- **Exclusões, somadas nos 60 meses (fundo-mês):** sem negócio na janela de liquidez 8.782;
  tipo fora do escopo 4.842; liquidez abaixo do mínimo 3.133; menos de 12 meses 2.247; cotas
  emitidas inválidas 1.757 (quantidade não inteira, pela linha "Cotas_Emitidas" da §4); DY
  mensal negativo 1.320; rendimento anual não positivo 1.035; amortização na janela 685;
  Informe sem meses 389; Informe com mais de 3 meses 236; classificação desconhecida 182;
  DY acima de 25% 168; amortização inválida 150; fonte de eventos indisponível 111; linhas
  conflitantes 21; desdobramento 19; grupamento 1.
- **Sensibilidade (não é a constante):** com as cotas fracionárias arredondadas, em vez de
  inválidas, o spread seria 3,5124% (p25 3,1738%, p75 3,7345%; 30 a 44 fundos por mês).
- **Medianas mensais (%, fundos):** 2021-10 2,24 (30); 2021-11 3,13 (32); 2021-12 2,68 (35);
  2022-01 2,31 (37); 2022-02 2,82 (39); 2022-03 3,20 (36); 2022-04 2,80 (37); 2022-05 2,72
  (37); 2022-06 2,99 (39); 2022-07 2,44 (38); 2022-08 2,02 (37); 2022-09 2,50 (34); 2022-10
  2,52 (36); 2022-11 3,27 (36); 2022-12 3,50 (35); 2023-01 3,51 (33); 2023-02 3,52 (30);
  2023-03 3,83 (30); 2023-04 3,51 (35); 2023-05 3,65 (36); 2023-06 3,52 (37); 2023-07 3,50
  (38); 2023-08 3,57 (36); 2023-09 3,42 (40); 2023-10 3,49 (39); 2023-11 3,44 (36); 2023-12
  3,50 (35); 2024-01 3,18 (39); 2024-02 3,30 (37); 2024-03 3,26 (38); 2024-04 3,58 (35);
  2024-05 3,47 (33); 2024-06 3,63 (35); 2024-07 3,98 (34); 2024-08 3,70 (32); 2024-09 3,97
  (33); 2024-10 4,09 (36); 2024-11 3,60 (33); 2024-12 3,73 (37); 2025-01 4,76 (41); 2025-02
  4,45 (39); 2025-03 2,80 (38); 2025-04 3,14 (39); 2025-05 3,39 (37); 2025-06 4,11 (35);
  2025-07 3,72 (37); 2025-08 3,35 (36); 2025-09 2,72 (38); 2025-10 3,24 (40); 2025-11 3,97
  (41); 2025-12 3,76 (39); 2026-01 3,65 (37); 2026-02 3,71 (39); 2026-03 3,88 (37); 2026-04
  3,81 (36); 2026-05 4,27 (36); 2026-06 4,47 (32); 2026-07 4,13 (33); 2026-08 4,62 (33);
  2026-09 4,66 (34).
- **SHA-256 das fontes** (os arquivos que o script lê):
  - `fii_anual_2019.resposta`: `ba542efca10362e6ab5a49b56add4374748f6f4eb81c0a2bedb107d144e385b9`
  - `fii_anual_2020.resposta`: `aec2dbc88d324d002517e96cc2cf74f404bfe038c1a254f6935ef0af5c411ba5`
  - `fii_anual_2021.resposta`: `d7450231a77295b9f8a0daac94510062912f6ca8335b0dedc48571123526de0b`
  - `fii_anual_2022.resposta`: `9ef1736d79eba7a0cbc1091bdb124ee8a196050df78dcf310d87f6f6a0d6d65c`
  - `fii_anual_2023.resposta`: `0eab13e3e8ea63d54288fb4ab26898c64ce8cbc6aa15a9ae9f159eae7e8a65bd`
  - `fii_anual_2024.resposta`: `2ff3ed063302576ef206097ab7978eb529d3e3c07d43869e3f9eba34fc37e3b5`
  - `fii_anual_2025.resposta`: `0413308766b306a557bc19fa00fb5dd0ed63f8f3dffe760ee59c59682b0750ca`
  - `fii_anual_2026.resposta`: `eac25b77664933c8b79a19056ea51c591f23e7fdc1c0c101a978d83d87f22fbb`
  - `cotahist_anual_2020.resposta`: `86442168939b9da7b3cc1ec1662c333ee5ab4c75f2be1865b5bf55ba4c52168f`
  - `cotahist_anual_2021.resposta`: `b0d4aed17d609c7ba615a23320c2fd513b580a251ae7d884a5015ef8a3fe4705`
  - `cotahist_anual_2022.resposta`: `a4f9015b755f797d9c08b0d13f19dbfab18a6c75f379c0271a1cf1b5f6323cd8`
  - `cotahist_anual_2023.resposta`: `ad1603788d78aaa1de806498572277f1d9443f88ae116452751b5800cb23523e`
  - `cotahist_anual_2024.resposta`: `96a003d10fab0fa2ace0c64cdc2b892b4c111adf9da8e538aa0b28437bd2a172`
  - `cotahist_anual_2025.resposta`: `6cc0ad851c8f605ca30418acac48be81f1767f6ed05b4f563772d06ae448047d`
  - `cotahist_anual_2026.resposta`: `1a78ad7f46ced05c723a5b09089e48378dfc5b7fe9cb6558cbcae569c66e51ad`
  - `tesouro_historico.resposta`: `f4f9b0fb9a1850da4cbca47d5b896464c04b21b302cf591de178726a426e2972`

## 7. Parâmetros e justificativa

**Todas [DECISÃO] decididas pelo Marcos em 19/10/2026:**

| Opção da 0.1 | Decidida |
|---|---|
| 7.1 Spread | mediana de 5 anos dos tijolos; recalcular com taxa_aplicacao no F2B-2, constante datada após validação |
| 7.2 Vértice | mesma média da taxa-real 0.3, sem prêmio das ações |
| 7.3 Rendimento | Informe, declarado, reconstruído; 12 meses/13 VPs, corte por entrega e idade de 3 meses |
| 7.4 Score | inalterado na 2B, inclusive comparação existente com Selic; exceção temporária ao princípio 9 do PLANO, não misturar com fórmula de V0 |
| 7.5 Tipo | só tijolo; demais e desconhecido abstêm até 2C |
| 7.6 Vacância | sem fonte oficial; manter o tratamento atual, sem inventar ajuste ou pontuação nova |
| 7.7 P/VP | pontos e score inalterados, sem entrar no valor de rendimento |
| 7.8 Tributação | spread bruto sobre bruto, sem desconto tributário adicional |

**Complemento decidido pelo Marcos em 19/10/2026:** desdobramento/grupamento
ou salto de VP incompatível abstêm (critério operacional na §3a, 20/10/2026); emissão com VP contínuo é aceita, em contexto.
Crescimento **real** zero explicitamente derivado.
As decisões não transformam a reconstrução do F2B-28 em fluxo validado nem
aprovam uma constante ainda não calculada. Pendências autorizadas estão na seção 6.
