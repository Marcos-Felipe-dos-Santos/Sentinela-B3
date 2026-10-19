# Rendimento do FII sobre NTN-B — versão 0.2

**Status:** rascunho revisto em 19/10/2026; aguarda auditoria FICHA pelo Claude
(D30) e aprovação do Marcos. **Decisões:** [marcador](../decisoes/marcador-2b.md).
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
| y_real | Média NTN-B escolhida na taxa-real 0.2, taxa_aplicacao, sem prêmio das ações |
| s | Mediana de 5 anos do grupo tijolo contra a mesma taxa_aplicacao e mesma definição de R e preço; constante datada, depois de recalibrada no F2B-2 |
| Tipo | Informe CVM ativo_passivo; regra de composição de universo-inicial, seção de fontes: fração >50% da soma dos ativos imobiliários identificados |
| Eventos | Cotas_Emitidas, VP e documentos oficiais de eventos da CVM/B3/administrador, disponíveis até as_of |
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

Qualquer evento de cota na janela, inclusive emissão, ou salto de escala/cota
incompatível com continuidade, causa abstenção: **não há ajuste de eventos na
2B**. Variação de Cotas_Emitidas sinaliza evento a conciliar, nunca um rendimento
artificial. Sem documentação suficiente para distinguir evento de erro ou atestar
continuidade, abster por base de cotas não demonstrada, sem criar percentual
arbitrário para o salto. Verificação cobre as 13 bases e o intervalo até o preço.
Amortização/devolução de capital não é rendimento: não somar Percentual_Amortizacao;
se positiva na janela, ou liquidação/distribuição extraordinária não recorrente
identificada, abster por fluxo não representativo. Contratos indexados não garantem
constância real da distribuição; sustentabilidade permanece hipótese declarada.

## 4. Escopo e matriz de validade

Só classe oficial FII e tipo **tijolo**. Papel (KNCR11/MXRF11/HCTR11), fundos
de fundos (CPTS11/HFOF11), tipo desconhecido/misto sem maioria: "tipo de FII
fora do escopo na 2B" ou "classificação de FII desconhecida"; aguardam 2C.
HGLG11/KNRI11 precisam ainda cumprir todas as guardas. XPML11 abstém por evento.
Ações, bancos, seguradoras, holdings, units, preferenciais, ETF, BDR e UNKNOWN
não entram: "classe fora do escopo FII". Setor ou ticker não substitui a classe.

Cada linha aplica antes das contas os motivos separados de ausente, não numérico,
NaN e infinito do registro §2.1; contexto inválido é indicado sem alterar o valor.

| Insumo | Zero | Negativo | Fora de faixa / motivo |
|---|---|---|---|
| Preço e cada VP | abstém: não positivo | abstém | unidade/base divergente: base de cota incompatível |
| Cada DY_m | válido como mês sem rendimento, se informado | abstém | >25% mensal: fora da faixa da fronteira atual; não confundir com validação de recorrência |
| DY_12m e R | abstém: rendimento anual não positivo | abstém | DY_12m>25%: rendimento não confiável; 25% é teto de domínio existente, não parâmetro de valor |
| Cotas_Emitidas | abstém: cotas não positivas | abstém | quantidade não inteira, mudança ou evento: base de cotas incompatível |
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

**Resultado operacional: abstenção.** Além do spread ainda não recalibrado,
Cotas_Emitidas passa de 33.787.575 em outubro/2025 a 42.404.675 em novembro;
depois 43.455.524 em abril/2026, 45.601.745 em maio e 45.601.713 em agosto.
A regra do Marcos exclui evento de cota, inclusive neste exemplo. A conta acima
não valida rendimento econômico contínuo nem elegibilidade do fundo.

Para teste independente da fórmula, cenário **condicional**, não resultado do
HGLG11: R=13,240529645135538184, y=74,38/1100, s=2 pp hipotéticos dão
**R$ 151,116233758550**; se s ausente ou houver evento, o teste espera abstenção.
Confronto com avisos do administrador para validar o rendimento é pendência
expressa do F2B-2; o próprio Informe não é segunda fonte independente.

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
fundos/meses antes e depois dos eventos, meses removidos, mudança da mediana,
p25/p75 e limites da amostra. Comparar 1/2/3 pp e mediana recalibrada sobre o
mesmo rendimento, sem misturar DY da cascata com Informe. Seleção só de fundos
atuais mantém viés de sobrevivência: declarar e medir cobertura; não dizer que
representa todos os listados. A composição atual não classifica todo o passado.

## 7. Parâmetros e justificativa

**Todas [DECISÃO] decididas pelo Marcos em 19/10/2026:**

| Opção da 0.1 | Decidida |
|---|---|
| 7.1 Spread | mediana de 5 anos dos tijolos; recalcular com taxa_aplicacao no F2B-2, constante datada após validação |
| 7.2 Vértice | mesma média da taxa-real 0.2, sem prêmio das ações |
| 7.3 Rendimento | Informe, declarado, reconstruído; 12 meses/13 VPs, corte por entrega e idade de 3 meses |
| 7.4 Score | inalterado na 2B, inclusive comparação existente com Selic; exceção temporária ao princípio 9 do PLANO, não misturar com fórmula de V0 |
| 7.5 Tipo | só tijolo; demais e desconhecido abstêm até 2C |
| 7.6 Vacância | sem fonte oficial; manter o tratamento atual, sem inventar ajuste ou pontuação nova |
| 7.7 P/VP | pontos e score inalterados, sem entrar no valor de rendimento |
| 7.8 Tributação | spread bruto sobre bruto, sem desconto tributário adicional |

Eventos/saltos abstêm; crescimento **real** zero explicitamente derivado.
As decisões não transformam a reconstrução do F2B-28 em fluxo validado nem
aprovam uma constante ainda não calculada. Pendências autorizadas estão na seção 6.
