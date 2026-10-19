# Lente de bancos — versão 0.3

**Status:** rascunho revisto em 19/10/2026; aguarda auditoria FICHA pelo Claude
(D30) e aprovação do Marcos. **Decisões:** [marcador](../decisoes/marcador-2b.md).
**Implementação futura:** F2B-3 (método), F2B-32 (motor), F2B-4 (modelo/escopo).

## 1. Fórmula, derivação e referência

`P0/B0 = (ROE − g)/(k − g)`; valor por título = múltiplo × VPA0.
A derivação começa **no nominal**: B0 é patrimônio na data-base de projeção;
`L1 = ROE_N × B0`, `D1_N = L1 × p`,
`B1 = B0 + L1 − D1_N`, portanto `g_N = ROE_N × (1−p)`.
Gordon dá `P0/B0 = ROE_N × p/(k_N−g_N) = (ROE_N−g_N)/(k_N−g_N)`.
ROE histórico é lucro anual / **PL dos controladores do início do exercício**;
usá-lo como retorno futuro sobre B0 atual é hipótese de persistência, não
igualdade entre lucro passado e futuro. VPA0 usa PL final e ações finais.

Fisher para **as três taxas**:
`ROE_r=(1+ROE_N)/(1+π)−1`, idem para k e g.
`ROE_N−g_N=(1+π)(ROE_r−g_r)` e
`k_N−g_N=(1+π)(k_r−g_r)`: o múltiplo é igual nos dois regimes.
O fluxo real é `D1_r=D1_N/(1+π)`, na moeda de B0; nos períodos seguintes,
`D_t_N=D_t_r(1+π)^t`. Não usar simplesmente ROE_r × (1−p) como g real:
a retenção é identidade contábil nominal; a correção monetária do patrimônio
não é lucro nominal distribuível.

**Teto e coerência do payout.** Calcular g_N_bruto com p observado da DVA;
converter a real e só depois limitar ao PIB Focus, como Gordon.
Se o teto não atuar, a inversa recupera exatamente g_N_bruto e o payout observado.
Se atuar, `g_N_efetivo=(1+g_r_limitado)(1+π)−1` e a identidade exige
`b_implícito=g_N_efetivo/ROE_N`, `p_implícito=1−b_implícito`.
Assim, o teto implica **menor retenção e maior distribuição projetada**, mantendo
o ROE; p observado e p implícito devem aparecer separados. Não afirmar que o
payout histórico ficou igual quando g mudou. A expressão (ROE−g)/(k−g) só
é aplicável com esse dividendo projetado compatível; se o p implícito sair de
(0,1], abster por payout projetado incompatível, sem truncar. Essa ponte é
consequência algébrica do teto e da fórmula, a conferir explicitamente na auditoria.

Fonte consultada: Damodaran, *Investment Valuation*, **2ª ed.**, Wiley, 2002,
[cap. 19, “Book Value Multiples”, seção “Price to Book Value Ratios”,
“Analysis”, pp. 6–7 do PDF](https://pages.stern.nyu.edu/~adamodar/pdfiles/valn2ed/ch19.pdf),
que distingue lucro sobre patrimônio inicial e contemporâneo. Correspondência
na **3ª ed., 2012, cap. 19**, e cap. 21 sobre financeiras, **a conferir pelo
auditor**. Não citar cap. 18 como “Book Value Multiples”. A hipótese local de
persistência e a fonte Focus do teto são adaptações, não prescrições do livro.

## 2. Insumos

| Insumo | Fonte, janela, perímetro e unidade |
|---|---|
| L0 | DRE consolidada anual, lucro dos controladores, códigos 3.09.01/3.11.01 mais descrição, conforme tabela de contas CVM; R$ |
| PL_inicial | Comparativo do BPP consolidado da mesma DFP/versão, imediatamente antes do início do exercício; PL controladores = 2.07−2.07.02 ou 2.08−2.08.09, com descrição compatível |
| PL_final | Mesmo BPP e perímetro, fim do exercício; não trocar o PL inicial por este no ROE |
| ROE_N | L0 / PL_inicial; razão anual; numerador de um exercício, denominador estoque de abertura desse exercício |
| p observado | Dividendos + JCP bruto da DVA anual dos controladores / L0; no Itaú, 7.09.04.02 e 7.09.04.01, com descrição; não aplicar esses códigos a todo banco sem conferir modelo |
| VPA0 | PL_final dos controladores / ações finais da mesma DFP; R$/ação, ou soma ponderada por componentes oficiais para R$/unit |
| k_r, π e teto PIB | taxa-real 0.3 e Gordon 0.3; IPCA do mesmo exercício anual; Focus PIB mediana, baseCalculo 0, maior ano da última pesquisa publicada |
| Preço | Só P/VP de mercado, por mesma ação/unit, não forma múltiplo justificado |
| Inadimplência | IF.data relatório 16, apenas contexto: carteira ativa inadimplida arrastada (148834) / Total Geral (24454), mesmo conglomerado, data e perímetro |

Uma linha de JCP/dividendo explicitamente zero é válida; linha ausente não vira
zero automaticamente. Com apenas um provento, aceitar soma só após comprovar
não ocorrência do outro; do contrário, abster por DVA incompleta. Excluir
participações de terceiros. **Decisão do Marcos de 19/10/2026 após auditoria
0.2:** os pares código/descrição de JCP e dividendos do modelo banco (pela tabela
de contas; no Itaú, 7.09.04.01/02) são dos controladores quando os não controladores
estão em linha própria (no Itaú, 7.09.04.04, descrição compatível), excluída da soma.
Se ausente/zerada, só usar a reserva sem evidência de minoritários na DRE/BPP,
com os mesmos critérios do F2A-41: ausência verdadeira não é sem correspondência,
e valor inválido ou conflito não autoriza reserva. Sem essa estrutura, abster:
"estrutura da DVA não permite atribuir proventos aos controladores". A estrutura
separada válida dispensa nota adicional. F2B-3 completa os pares do modelo na
tabela de contas, inclusive participação separada, sem tratá-los como já implementados.
Payout
por DY da cascata não é alternativa. VPA só CVM, escala de ações conforme
por-acao 1.1, sem reserva por fonte de mercado. Unit sem composição abstém.

## 3. Regime, janela e data

Só **DFP anual completa**. Último ITR não substitui o lucro anual nem altera a
janela; nenhuma anualização parcial ou TTM na 2B. DRE e DVA cobrem o mesmo
início/fim; BPP inicial é abertura desse intervalo, PL final e ações são fechamento.
Dados selecionados por entrega até as_of; idade máxima da DFP = último exercício
exigível no calendário oficial, regra e controles de publicação do registro §2.
NTN-B até 5 dias úteis; cobertura IPCA até 2 meses; PIB última edição devida.
Preço corrente último pregão; exemplos usam 30/09 por comparação solicitada.

Inadimplência: última data-base **publicada** até as_of, conforme calendário de
publicação do IF.data; idade máxima = última data-base devida nesse calendário,
sem preencher por relógio ou trocar de conglomerado. Sem calendário/valor válido,
mostrar "inadimplência IF.data não informada: <motivo>"; não bloquear a lente.
Conceito é o nome da conta do relatório 16, não afirmar equivalência automática
a atraso >90 dias nem a “Ativos problemáticos” (148833). **Basileia fora da 2B**.

Mudança estrutural, emissão, desdobramento ou direito de classe entre a DFP e
preço: exigir reconciliação da base por título; sem ela, abster por base não
comparável. Persistência de ROE é projeção, não reconciliação das movimentações
patrimoniais reais. Não transformar diferenças históricas em lucro retido implícito.

## 4. Escopo e matriz de validade

STOCK/UNIT com **modelo banco**, determinado pelas contas-raiz do **BPP
consolidado**: PL em 2.07/2.08, identificado por descrição e tabela do modelo.
A 2.03 isolada em banco pode ser outra rubrica: não basta encontrar seu código.
Sem BPP consolidado, sem correspondência ou contas conflitantes: abstenção,
nunca padrão empresa por setor ausente. PL em 2.03 com estrutura de empresa
vai a empresa, inclusive holding; estrutura de seguradora vai a seguradora,
sem lente nesta fase. Setor “Bancos” não substitui a demonstração.

ITUB4/BBAS3 só entram com modelo e insumos válidos. SANB11 exige composição;
BRSR5/BRSR6 exigem direito específico, sem ratear total PN como se classes
fossem iguais. Holdings CSAN3/GOAU4 e seguradoras/corretoras não são bancos por
nome: vale o BPP; sem classificação inequívoca, abster. Não chamar QUAL3 de
seguradora por aproximação de setor. USIM5 com prejuízo não ganha lente bancária.
KNCR11/HGLG11 e demais FIIs, ETF/BDR/UNKNOWN: classe fora do escopo.

Cada linha tem os motivos separados de ausente/não numérico/NaN/infinito do
registro §2.1, **antes** de Fisher, produto ou teto.

| Insumo | Zero | Negativo | Fora de faixa / motivo |
|---|---|---|---|
| PL inicial, PL final, VPA e ações | abstém: não positivo | abstém | escala, quantidade não inteira ou base incompatível: insumo inválido |
| Lucro e ROE_N | abstém: lucro não positivo | abstém: prejuízo | ausência de controladores/perímetro: atribuição não demonstrada |
| Dividendos/JCP | válido se informado | abstém | linha ausente sem prova: DVA incompleta |
| p observado e p implícito | abstém | abstém | >1: payout fora de (0,1]; sem corte em 95% |
| π | válido | válido se >−1 | ≤−1: Fisher indefinido; janela divergente: inflação incompatível |
| g e teto PIB | válidos se guardas cumpridas | válidos se >−1 | g≥ROE_r ou g≥k_r: abstenção; g≤−1 inválido |
| ROE_r e k_r | exigir ROE_r>g, k_r>g | mesma guarda, com fatores >0 | não finito ou fator≤0: taxa inválida; prejuízo nominal sempre abstém |
| Preço de comparação | sem P/VP de mercado, motivo preço não positivo | idem | inválido: sem comparação; o núcleo do múltiplo não depende do preço |
| Inadimplência contextual | válido, não ausente | não informada: fora do domínio | numerador>denominador, denominador≤0 ou razão>1: não informada, não altera valor |
| Resultado/intermediário | abstém: valor não positivo | abstém | não finito: resultado não finito |

ROE_r−g zero não prova destruição de valor: pode ser distribuição nula.
Não produzir valor positivo para prejuízo aproveitando dois sinais negativos.
Não impor piso não aprovado para k−g; a aproximação da singularidade deve ser
exibida como sensibilidade, mesmo com teto econômico.

## 5. Exemplo independente — ITUB4 recalculado

CNPJ 60.872.504/0001-23, DFP 2025 **v2**, entregue **12/02/2026**,
as_of 19/10/2026 17:10 Brasília. Janela **01/01–31/12/2025**; moeda-base de
projeção **R$ de 31/12/2025**. Hashes, arquivos e tolerância no registro §2.3.
Valores monetários em milhares de R$:

- Lucro controladores (3.09.01): **44.857.000**.
- PL inicial, comparativo 31/12/2024: **221.284.000−10.194.000=211.090.000**.
- PL final: **215.076.000−10.575.000=204.501.000**.
- DVA dividendos **33.704.000** (7.09.04.02), JCP **0 informado** (7.09.04.01),
  por código/descrição; não controladores **992.000** em linha própria 7.09.04.04,
  "Part. Não Controladores nos Lucros Retidos", excluída da soma. A estrutura
  demonstra o perímetro, sem abstenção por esse motivo; p=**75,136545020844%**.
- Ações finais: **5.617.743+5.409.126−345=11.026.524 milhares**;
  escala conferida com LPA divulgado ON/PN de 4,05 R$/ação (lucro/ações≈4,0681).
- ROE_N inicial = 44.857.000/211.090.000 = **21,250177649344%**;
  ROE_r com IPCA 2025 de 4,26% = **16,295969354828%**.
- VPA final = 204.501.000/11.026.524 = **R$ 18,546279861178**.
- g_N_bruto = ROE_N × (1−p) = **5,283528352835%**;
  g_r=**0,981707608704%**, abaixo do teto PIB de **2%** (pesquisa 16/10,
  ano 2030, mediana base 0 disponível antes de as_of). p implícito=p observado.
- y_r=74,38/1100, k_r=**11,761818181818%**, k_N=**16,522871636364%**.
- P/VP justificado = **1,420603401260**, real e nominal;
  valor = **R$ 26,346908251509** por ação.
- Fechamento COTAHIST **30/09/2026 R$ 44,28**, mercado 010;
  P/VP de mercado = **2,387540807722**. Comparação nominal de outra data,
  cenário ilustrativo, não análise histórica estrita em setembro.

A projeção nominal usa L1=ROE_N×PL_final; D1_N=L1×p. Dividindo por ações
finais e por 1+π obtém D1 real. Descontar esse fluxo reproduz R$ 26,34690825;
não usar o dividendo passado por ação como se já fosse D1.

Reconciliação histórica: PL final−inicial=**−6.589.000 mil**, mas lucro−DVA=
**11.153.000 mil**; diferença **−17.742.000 mil** em outras movimentações.
Portanto crescimento de PL observado não é ROE×retenção nesta DFP. O exemplo
projeta persistência, sem afirmar clean surplus histórico. A conta é esperado
aritmético; a DVA atende ao critério de estrutura separada, enquanto direitos
da classe e demais guardas continuam necessários à elegibilidade operacional. Não afirmar que PINE4 ou SANB11 falham especificamente por VPA:
o levantamento só registra falta agregada de ROE, VPA positivo ou payout.

## 6. Sensibilidade

| Prêmio, mesmo ROE inicial/payout/IPCA | P/VP | Valor por ação (R$) |
|---|---|---|
| 4% | 1,565858 | 29,040836 |
| 5% | 1,420603 | 26,346908 |
| 7% | 1,198289 | 22,223797 |

| Denominador histórico do ROE, controle não adotado | ROE_N | P/VP | Valor (R$) |
|---|---|---|---|
| PL inicial, escolhido | 21,250178% | 1,420603 | 26,346908 |
| PL final, hipótese de retorno contemporâneo | 21,934856% | 1,488927 | 27,614054 |
| PL médio, hipótese de retorno médio | 21,587089% | 1,453963 | 26,965603 |

Cada linha recalcula g pela mesma retenção, converte todas as taxas e explicita
uma hipótese diferente; não são convenções equivalentes. Com teto real hipotético
0,5%, p projetado sobe para **77,499952805582%** e valor=**R$ 26,013247914640**;
com teto 0%, p=**79,953108767862%**, valor=**25,695823859191**. O teto
escolhido de 2% não atua neste caso. Manter p observado enquanto se elimina g
da derivação produziria outro fluxo; não rotular como a mesma fórmula.

Fronteira sintética: ROE_r=15%, k_r=10%; g=9%, 9,9%, 9,99% dá P/VP=6,
51, 501, e g=10% abstém. O teto Focus normalmente afasta esse cenário, mas
não dispensa as guardas k>g e ROE>g, nem autoriza arredondar antes de compará-las.

## 7. Parâmetros e justificativa

**[DECISÃO] 7.1 decidida pelo Marcos em 19/10/2026:** g opção (i), depois teto
real PIB Focus, mesma fonte/base do Gordon; sem piso arbitrário de k−g.
**7.2 decidida:** payout DVA, JCP bruto, controladores, só anual, em (0,1];
estrutura separada ou reserva sem minoritários definida na seção 2, por decisão
do Marcos de 19/10/2026 após auditoria da 0.2.
**7.3 decidida:** VPA só CVM, por ação ou unit com composição.
**7.4 decidida:** Basileia fora da 2B.
**7.5 decidida:** inadimplência do IF.data apenas para leitura, conta e denominador
declarados, sem efeito no valor e sem confundir conceitos.
**7.6 decidida:** ROE sobre PL inicial; as demais convenções não são equivalentes.
**7.7/[FINANCEIRAS] decidida:** modelo pelas contas-raiz do BPP consolidado,
inclusive holdings; sem BPP consolidado, abstenção. Exigir lucro positivo,
payout em (0,1], k>g e g<ROE. A ponte do payout sob teto é exposta na seção 1
para conferência da auditoria, não premissa escondida. Referências não acessíveis
continuam marcadas; nenhuma destas decisões aprova automaticamente a ficha.
