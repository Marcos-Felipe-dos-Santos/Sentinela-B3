# Taxa de desconto real — versão 1.1

**Status:** aprovada pelo Marcos em 20/10/2026, revisão 1.1 (D21).
A auditoria FICHA do Claude com **pode seguir** cobriu a versão 0.3, promovida
à 1.0 em 19/10/2026. A revisão 1.1 incorpora a decisão de oferta do F2B-48;
não atribui ao auditor uma conferência desta revisão ainda não realizada.
**Decisões:** Marcos, 19 e 20/10/2026; [registro do marcador](../decisoes/marcador-2b.md).
**Dependências:** F2B-27, F2B-29, F2B-30, F2B-1, F2B-2, F2B-3 e F2B-32.
Aprovação documental registrada; implementação nos itens da fila, ainda não entregue.

## 1. Fórmula e referência

`y_real = soma(taxa_aplicacao dos títulos elegíveis) / quantidade de títulos`.
`k_real = y_real + 0,05`, para ações elegíveis. A NTN-B integral contém risco
Brasil; os 5 pontos são prêmio das ações sobre o título, sem spread soberano
separado. É benchmark composto, não título único nem taxa soberana sem risco.

Fisher exato: `1 + k_N = (1 + k_r)(1 + π)` e
`k_r = (1 + k_N)/(1 + π) − 1`. A identidade usa uma mesma inflação constante
do cenário. Com moeda-base em t=0,
`CF_N,t = CF_r,t × (1 + π)^t`, logo
`CF_N,t/(1 + k_N)^t = CF_r,t/(1 + k_r)^t`.
Somar os dois lados demonstra igualdade dos valores presentes. Converter só
k e g, mantendo artificialmente iguais os primeiros fluxos, não a demonstra.

Referências: Fisher, *The Theory of Interest*, Macmillan, 1930, cap. II,
“Money Interest and Real Interest”: localização na edição e passagem **a conferir
pelo auditor**. Damodaran, *Investment Valuation*, 3ª ed., Wiley, 2012,
cap. 7, “Riskless Rates and Risk Premiums”, seção sobre taxas reais e risco
soberano **a conferir pelo auditor**. A composição brasileira é decisão do
Marcos, não consequência atribuída aos livros. D22 fundamenta a coerência de
regimes exigida pelo projeto; a prova algébrica acima independe da edição.
O Claude confirmou em 19/10/2026 os títulos dos capítulos de Fisher e Damodaran
na auditoria da 0.2; páginas e passagens específicas continuam não conferidas.
O registro do marcador identifica a auditoria da 0.3, com veredito "pode seguir".
Páginas e passagens específicas permanecem na lista de pendências atribuídas.

## 2. Insumos

| Insumo | Fonte e definição | Unidade |
|---|---|---|
| y_real | CSV Tesouro Transparente, fontes-fase2b §1; títulos com nome exato Tesouro IPCA+ ou Tesouro IPCA+ com Juros Semestrais e vencimento ≥ 01/01/2035 | Taxas do CSV em % a.a., dividir por 100 |
| taxa_aplicacao | Coluna literal `Taxa Compra Manha`; única usada na média | razão real anual |
| taxa_resgate | Coluna literal `Taxa Venda Manha`; proveniência/contexto, não média | razão real anual |
| Prêmio | Constante versionada 0,05, só das ações; 0,04/0,07 apenas sensibilidade | razão anual |
| π | IPCA SIDRA 1737 na janela contábil convertida; variável 2265 só para 12 meses completos, ou produto da 63/razão da 2266 | razão acumulada na janela anual |
| Datas, nomes, vencimentos, calendário | Fonte oficial e metadados de publicação/coleta; contratos comuns do registro §2 | datas com fuso e versão |

Selecionar a maior Data Base elegível ≤ as_of; reunir todos os títulos das duas
famílias nessa data, um por tipo/vencimento. Peso igual, sem ponderação por
prazo, estoque ou duration. A referência é escolhida antes de excluir títulos
sem oferta. Par de aplicação com taxa e PU ambos zero sai da cesta, com contagem
na proveniência; se todos saírem, abster por cesta vazia sem trocar de data.
Linha inválida da cesta escolhida não sai silenciosamente da média:
abster o benchmark inteiro. Duplicata idêntica conta uma; conflitante abstém.
A API do Tesouro Direto da V1 não é fonte alternativa. Falta de fonte não vira
7% nem inflação de 5,5% de contingência.

## 3. Regime, janela e data

Regras de publicação e idade, incluindo calendário, no registro §2.2: NTN-B
até 5 dias úteis; cobertura do IPCA até mês no máximo dois meses anterior a
as_of; inflação calculada na mesma janela do fluxo/ROE convertido. Deflação
é válida se π > −1. FII usa y_real com spread próprio, sem prêmio das ações.
Bazin de 6% não depende desta taxa nem da Selic.

A taxa comum não autoriza método: STOCK/UNIT dependem de modelo, classe e
controladores; ITUB4/BBAS3 vão à lente de bancos; SANB11/KLBN11 exigem composição;
BRSR5/BRSR6/USIM5 exigem direitos; CSAN3/holdings e prejuízos seguem guardas da
lente; seguradoras não ganham lente nesta fase. HGLG11/tijolo segue ficha FII;
KNCR11/papel e fundos de fundos abstêm. A taxa em si não é por ação nem por cota.

## 4. Matriz de validade e abstenção

Para **cada insumo abaixo**, ausência, não numérico, NaN e infinito têm os quatro
motivos distintos do registro §2.1, antes de qualquer limite ou conta.

| Insumo | Zero | Negativo | Fora de faixa / outro impedimento |
|---|---|---|---|
| Taxa de aplicação com PU > 0 | zero econômico válido | válida se > −1 | ≤ −1: taxa real sem fator positivo; escala não comprovada: unidade inválida |
| Par de aplicação: taxa = 0 e PU = 0 | sem oferta: excluir e contar na proveniência | não se aplica | todos os elegíveis sem oferta: cesta vazia, sem usar data anterior |
| PU de aplicação | com taxa ≠ 0: linha inválida, cesta abstém; com taxa = 0: sem oferta | linha inválida, cesta abstém | ausente, não numérico, NaN ou infinito: linha inválida, cesta abstém |
| Taxa/PU de resgate | taxa = 0 com PU > 0: válido; ambos zero: sem oferta informativa | taxa > −1 com PU > 0: válida; PU negativo: inválido | taxa ≠ 0 com PU = 0, taxa ≤ −1, ausência, não numérico, NaN ou infinito: taxa_resgate ausente, motivo na proveniência; aplicação segue |
| Prêmio das ações | finito matematicamente, mas não é parâmetro aprovado | inválido | Diferente de 0,05 em produção: parâmetro fora da versão; sensibilidade identificada à parte |
| π | válido | deflação válida se > −1 | ≤ −1: Fisher indefinido; outra janela: inflação incompatível |
| Quantidade de títulos | inválido: cesta vazia | inválido | não inteiro ou linhas conflitantes: cesta inválida |
| Datas/publicação | não se aplica numericamente | não se aplica | futura, idade excedida ou disponibilidade não demonstrada: motivo temporal específico |
| CF e moeda-base | zero válido | válido na identidade, consumidor define elegibilidade | sem moeda/data ou regimes diferentes: fluxo incompatível |
| k_N, k_r e resultado | taxa zero válida na identidade | > −1 válido na identidade | fator ≤ 0 ou não finito: resultado inválido; consumidor exige taxa de desconto admissível |

A taxa de aplicação zero com PU positivo é expressamente válida: a expressão
“só um dos dois zerado” significa aqui taxa não zero com PU zero. O par de
resgate nunca entra na média; sua invalidade ou ausência de oferta abstém apenas
a informação de resgate, com taxa_resgate ausente e motivo na proveniência.
Os quatro motivos comuns de ausência/não numérico/NaN/infinito aplicam-se a cada
campo do par; o efeito depende do par, conforme a tabela.

A identidade não garante convergência de perpetuidade: cada consumidor valida
k > g e seu próprio fluxo. Uma taxa real negativa admissível como observação
não é substituída nem basta para dar valor ao método.

## 5. Exemplo independente

Snapshot, hashes e as_of no registro §2.3. Taxas de aplicação em 15/10/2026:

| Família | Vencimentos e respectivas taxas (% a.a.) |
|---|---|
| IPCA+ | 15/05/2035: 6,84; 15/08/2040: 6,73; 15/05/2045: 6,73; 15/08/2050: 6,74 |
| IPCA+ com Juros Semestrais | 15/05/2035: 6,82; 15/05/2037: 6,83; 15/08/2040: 6,75; 15/05/2045: 6,75; 15/08/2050: 6,75; 15/05/2055: 6,71; 15/08/2060: 6,73 |

Os 11 títulos têm PU positivo nos dois pares; excluídos sem oferta = **0**
na proveniência desta cesta. As 14 linhas sem oferta do arquivo arquivado são
Prefixado com Juros Semestrais, vencimento 01/01/2021, datas de 2010 (diário
F2B-48), portanto nenhuma pertence à cesta de 15/10/2026.

Exemplos sintéticos da matriz, na mesma data-base: taxa 0%/PU 100 permanece como
zero econômico; taxa 0%/PU 0 sai e incrementa excluídos; taxa 6%/PU 0 ou PU −1
abstém a cesta de aplicação. Se esse último par for somente de resgate, a taxa
de aplicação permanece, taxa_resgate fica ausente e o motivo é registrado.
Se todos os elegíveis forem 0%/PU 0, não há média nessa data, mesmo que exista
oferta na data anterior.

Soma = 74,38%; média = **6,761818181818…%** (6,76% apenas na apresentação).
k_real = **11,761818181818…%**. Para converter a DFP 01/01–31/12/2025,
IPCA = 4,26%, publicado 09/01/2026:
k_N = `(1 + 74,38/1100 + 0,05) × 1,0426 − 1`
= **16,522871636364…%**. A inversa recupera k_real com precisão Decimal;
usar o número impresso arredondado não é volta sem perda.

Teste separado de fluxos, sintético: moeda-base em t=0, D0=1, k_r=10%,
g_r=2%, π=4%. D1 real=1,02, D1 nominal=1,0608, k_N=14,4%, g_N=6,08%.
`1,02/0,08 = 1,0608/0,0832 = 12,75`. Os próximos fluxos seguem a mesma
conversão. Esta ficha não usa preço; as consumidoras usam fechamento de
30/09/2026, com a distinção temporal do registro, não preço inventado para taxa.

## 6. Sensibilidade

| Prêmio das ações | k_real sobre a média escolhida | k_N com IPCA 2025 |
|---|---|---|
| 4% | 10,76181818% | 15,48027164% |
| 5% (base) | 11,76181818% | 16,52287164% |
| 7% | 13,76181818% | 18,60807164% |

Usar taxa_resgate elevaria a média a 6,88181818%, diferença de 0,12 pp:
comparação de fonte, não alternativa em produção. A composição por título varia
com as ofertas; não afirmar duration constante. Para mesmo k_real de base,
π=0%, 4,26% e −1% dão k_N=11,76181818%, 16,52287164% e 10,6442%,
respectivamente. A inflação muda a representação nominal, não o k real.

## 7. Parâmetros e justificativa

Todas as opções [DECISÃO] da 0.1 estão **decididas pelo Marcos em 19/10/2026**:

| Opção da 0.1 | Decidida | Justificativa/efeito |
|---|---|---|
| 7.1 Prêmio | 5% das ações sobre NTN-B; 4%/7% sensibilidade | composição explícita, sem dupla contagem soberana |
| 7.2 Vértice | média das duas famílias, vencimentos ≥ 2035 | benchmark composto reproduzível |
| 7.3 Tipo e campos | taxa_aplicacao; taxa_resgate contextual | correspondência literal na seção 2 |
| 7.4 Inflação | IPCA da janela contábil; Focus excluído | casar numerador, denominador e regime; deflação admitida |
| 7.5 Defasagem | 5 dias úteis; cobertura IPCA até 2 meses | idade e disponibilidade são guardas diferentes |
| 7.6 Fonte | CSV Tesouro Transparente | API V1 sai; sem contingência silenciosa |
| 7.7 Risco soberano | já na NTN-B integral | nenhum spread soberano adicional |

Moeda-base e conversão dos fluxos completam D22. Pendência bibliográfica
explicitamente marcada na seção 1 e preservada como pendência não bloqueante.

**Revisão 1.1 — [DECISÃO] decidida pelo Marcos em 20/10/2026 (D21):**
a matriz distingue zero econômico de sentinela sem oferta, registra exclusões,
veta taxa não zero com PU zero e limita a invalidade de resgate à informação
de resgate. Motivação: as 14 sentinelas verificadas no F2B-48.
