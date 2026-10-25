# Critério de rendimento do Bazin — versão 1.2

**Status:** versão 1.2 aprovada pelo Marcos em 20/10/2026: distribuição extraordinária
dispensada nesta versão, com aviso fixo (§3). Versão 1.1, da mesma data: linha "D e DY" da §4
(DY = 0 com cobertura completa). A versão 1.0 foi aprovada em 19/10/2026. Auditoria FICHA do Claude
sobre a versão 0.3: **pode seguir** (D30); promovida a 1.0 sem mudança de regra
ou número, conforme registro do marcador.
**Decisões:** [marcador](../decisoes/marcador-2b.md).
**Implementação futura:** F2B-31; limpeza de constantes sem leitor no F2B-5.

## 1. Fórmula e referência

`Preço-limite do critério = D_bruto_12m / 0,06`.
`DY_bruto_12m = D_bruto_12m / preço`; relação ao critério = `DY/0,06 − 1`.
É critério de rendimento mínimo nominal fixo, **não avaliação por desconto**,
nem previsão de distribuição, nem estimativa de valor intrínseco. Não é
perpetuidade real; a alternativa k real com g=0 foi rejeitada. O preço cancela
na primeira expressão, mas continua necessário ao DY e à comparação.

Bazin, Décio, *Faça Fortuna com Ações, Antes que seja Tarde*, edição de 1992:
edição editorial completa e capítulo/seção do critério de 6% **a conferir pelo
auditor**; não foi consultado exemplar para atribuir página. A regra de 6%
foi expressamente decidida pelo Marcos em 19/10/2026. A atribuição bibliográfica
não conferida não se transforma em evidência por repetição. A fórmula do critério
é divisão aritmética; não depende da hipótese de Fisher nem da Selic.

## 2. Insumos

| Insumo | Definição, fonte e unidade |
|---|---|
| D_bruto_12m | Soma de dividendos e JCP bruto por título, com datas ex na janela (data de referência menos 12 meses, data de referência], sem duplicação; **relação de proventos em dinheiro da B3, empresas listadas**, por evento: tipo, valor bruto por ação, data ex e classe |
| Preço | Fechamento bruto na data de referência do DY, R$/ação ou R$/unit; comparação corrente conforme registro §2.2 |
| DY | Soma anterior / mesmo preço; razão anual; não adotar campo percentual sem representação comprovada |
| Taxa | 0,06 constante, não max(Selic, piso); BAZIN_TAXA_MIN sai no F2B-5 quando sem leitor |
| Modelo, classe e unit | BPP consolidado e referência oficial; composição e proventos por componente, direitos demonstrados |
| Lucro/ROE/perfil | Contexto da ficha por-acao 1.1: lucro/PL dos controladores; perfil crescimento se ROE > 20% e DY < 4%, conforme regra já existente |

**Fonte decidida pelo Marcos em 19/10/2026 após a auditoria da 0.2:** relação
de proventos em dinheiro da **B3, empresas listadas**, serviço CompanyCall:
tipo (dividendo/JCP), valor **bruto** por ação e data ex, por classe/título.
O F2B-31 confirma resposta e leiaute do serviço, identifica endpoint e campos
literais, escala, datas e cobertura, com URL, coleta, hash e contrato D18. Não
confundir essa relação com GetDetail, que sustenta a ligação cadastral do BTG.
**Se a fonte não responder, F2B-31 fica [!]**, com motivo no diário, antes de
substituir os insumos; não trocar para yfinance como fonte de cálculo.

Yfinance fica **só como conferência**, mesma classe, janela e denominador;
valor, natureza/data ex ou cobertura divergentes geram aviso com as diferenças,
sem substituir a B3. Falha da conferência gera aviso de indisponibilidade,
sem invalidar uma série B3 completa. A cascata normaliza `dividendYield`, mas
esse campo não comprova bruto/data ex: não renomeá-lo para afirmar conteúdo
inexistente. Entrada B3 incompleta/ilegível abstém com motivo; indisponibilidade
da fonte na execução do F2B-31 é bloqueio do item, não licença de reserva.
O perfil, sem ROE válido, fica "perfil não determinado", sem preencher ROE;
para DY elegível ≥5%, crescimento é logicamente impossível pela regra acima.
ROE/prejuízo não vira veto adicional ao Bazin; prejuízo com DY positivo traz
aviso "prejuízo no exercício; rendimento passado não demonstra sustentabilidade".

## 3. Regime, janela e data

Critério nominal: dinheiro na moeda de cada evento, soma retrospectiva de 12
meses sem correção monetária. Não há conversão de fluxo nem custo de capital
nesta opção. A janela de média de 5 anos fica para F2C-1, explicitada como
limitação; não apresentar 12 meses como média de 5 anos.

Aplicar publicação ≤ as_of, preço da mesma referência, datas ex e direitos por
evento; idade máxima do preço = último pregão disponível, e da série = cobertura
até essa mesma referência (nenhum mês desconhecido). Último evento pode ser
antigo legitimamente; a ausência de distribuição só é zero se a cobertura for
completa. Histórico menor que 12 meses completos ou sem prova de cobertura:
abstenção. Regras de classificação/vigência do registro §2.2. Lucro/ROE contextual
usa última DFP exigível, sem alterar a janela dos proventos nem o critério.

Evento de ações sem fator oficial ou direito de classe não reconciliado:
abstenção por base incompatível. Distribuição extraordinária: **dispensada nesta versão**
(1.2, decisão do Marcos de 20/10/2026). A relação B3 não marca o provento extraordinário, e
não há fundamento para um percentual de excepcionalidade; toda série que o Bazin usa leva o
aviso fixo "proventos de 12 meses podem incluir distribuição extraordinária, não
identificada nesta versão", fora de `riscos`. A identificação por evidência oficial fica para
a 2C. Não afirmar sustentabilidade. Mudança estrutural que
impeça comparar os títulos na janela: abstenção. Não substituir série por DVA
por competência: é outra medida e só serve ao teste aritmético separado.

## 4. Escopo e matriz de validade

STOCK/UNIT, modelo empresa pelas contas do BPP consolidado. Bancos (BBAS3,
BBDC4, SANB11), seguradoras, FIIs de papel (KNCR11) e tijolo (HGLG11), ETF,
BDR e UNKNOWN: abstenção por modelo/classe. Holdings como CSAN3 exigem
provento do próprio título, sem distribuir consolidado de terceiros. Units
KLBN11/TAEE11/ENGI11: somar componentes oficiais, todos válidos; preferenciais
BRSR5/BRSR6 e USIM5 exigem série específica de seu direito, sem rateio agregado.
Qualificação pelo modelo não é inferência por rótulo de setor.

Em **cada linha**, ausente/não numérico/NaN/infinito recebem os motivos distintos
do registro §2.1. Para contexto, informar indisponibilidade sem bloquear o critério.

| Insumo | Zero | Negativo | Fora de faixa / motivo |
|---|---|---|---|
| Preço | abstém: preço não positivo | abstém | unidade/direito divergente: preço incompatível |
| Cada provento | válido se informado ou ausência comprovada | abstém: provento negativo | data ex fora da janela: não somar; natureza/bruto desconhecidos: série inválida |
| D e DY | com cobertura completa e ao menos um registro da espécie (ou de cada componente da unit) na relação B3, em qualquer data: DY = 0 é válido, o Bazin não calcula (abaixo do gate de 5%) e o perfil usa 0; sem cobertura completa ou sem registro da espécie: abstém, e o perfil cai na cascata, com aviso (1.1, 20/10/2026) | abstém | DY >25%: não confiável; 0<DY<5%: abaixo do gate |
| Taxa fixa | abstém | abstém | diferente de 0,06: parâmetro fora da versão |
| Ações por unit | abstém para componente necessário | abstém | não inteiro/composição desconhecida: unit sem composição válida |
| Lucro/ROE contextual | válido; perfil indeterminado se não calculável | válido, aviso de prejuízo | seguir domínio da ficha por-acao 1.1; inválido não vira positivo |
| Resultado | não esperado com D>0 | abstém | não finito: resultado não finito; perfil desconhecido não cria veto |

Gate **DY ≥5%** e alerta **DY >15%** permanecem por decisão anterior mantida;
faixa de confiabilidade até 25% é distinta do alerta. Entre 5% e 6% a lente
é elegível, mas não atinge o critério. O perfil crescimento é redundante entre
os elegíveis, não razão para descartar prejuízo com distribuição positiva.

## 5. Exemplo independente

**LREN3**, CNPJ 92.754.738/0001-62; as_of 19/10/2026 17:10 Brasília.
Fechamento COTAHIST **30/09/2026 R$ 11,60**, mercado 010; hash no registro §2.3.
O retrato público do levantamento traz, na janela 01/10/2025–30/09/2026,
os eventos do yfinance: 12/12/2025 0,227784; 25/03/2026 0,222698;
24/06/2026 0,229299; 23/09/2026 0,240666 R$/título. Soma **0,920447**.
Arquivo público `yf_LREN3.json`, SHA-256
c6618cd1deef1d321f80c06ae6af0bb71d82f10b8196fc44bc0517e362f82d70.
Soma/preço = **7,934887931034%**; soma/0,06 = **R$ 15,340783333333**.

**Limite da evidência:** essa série não separa nem comprova JCP bruto. Portanto,
o exemplo valida seleção das datas e soma, mas a saída operacional **abstém**
por falta da série B3; os R$ 15,34078333 são **apenas conferência yfinance**, não
resultado da fonte escolhida para LREN3. O F2B-31 obtém os eventos da relação
B3, preserva seus valores brutos e datas ex, compara com essa conferência e
registra aviso se divergir. Esta revisão docs não consultou nem validou resposta
da relação B3; a confirmação é aceite bloqueante do F2B-31. Caso de contrato
independente, sintético: numa classe única com cobertura completa nessa mesma
janela, dividendos 0,40 em 10/12/2025 e JCP bruto 0,20 em 10/06/2026, preço
10,00 em 30/09/2026, D=0,60, DY=6%, critério=10,00; evento em 30/09/2025
fica fora e em 01/10/2026 não entra. Não atribuir esses eventos a companhia real.

Exemplo **separado por competência**, mantido para conferir escala e fórmula:
DFP Renner 2025 v2, entregue 05/03/2026; DVA JCP 834.310 mil R$, dividendos
0 informado; ações ON 1.006.845 − 24.646 = 982.199 milhares. A escala é
conferida pelo lucro 1.457.566 mil R$ e LPA divulgado de 1,4422 R$/ação da mesma DFP (lucro/ações=1,48398, diferença de denominadores), conforme por-acao 1.1, e não pelo
campo MIL monetário. D=834.310/982.199=**0,849430716179** R$/ação;
DY ilustrativo sobre 11,60=**7,322678587747%**, critério=**14,157178602978**.
Isto não substitui a soma por data ex; o esperado aritmético não certifica o insumo.
Precisão e tolerâncias no registro §2.3; nenhum cálculo importa o projeto.

## 6. Sensibilidade

Com D anual por competência de 0,849430716178696985… apenas como controle:

| Taxa do critério, cenário | Preço-limite (R$) |
|---|---|
| 5%, sensibilidade | 16,988614 |
| 6%, regra escolhida | 14,157179 |
| 7%, sensibilidade | 12,134725 |

Reduzir D em 20% reduz o preço-limite em 20%; aumentar em 20% o eleva em
20%. Com taxa fixa positiva comum, a ordenação da relação ao critério é a do
DY, não informação independente de crescimento. Selic, NTN-B, IPCA e prêmio
não mudam a conta. Não há alegação empírica de reação ao Copom nesta ficha.

## 7. Parâmetros e justificativa

**[DECISÃO] 7.1 decidida pelo Marcos em 19/10/2026:** opção (b), 6% fixos,
critério do livro; não perpetuidade real nem Selic. **[DECISÃO] 7.2 decidida:**
sai BAZIN_TAXA_MIN, sem piso substituto. Gate 5% e alerta 15% permanecem;
6% é o critério, 25% é o limite de confiabilidade do DY. **JCP bruto e prejuízo
com DY positivo decididos:** bruto, elegível com aviso. Escopo STOCK/UNIT empresa.

F2B-31 **permanece**, pois a implementação ainda usa Selic. Os testes F-5 passam
à regra fixa nesse item; o teste da mediana de três métodos também depende do
F-4/Gordon, resolvido no F2B-1, e não pode ser atribuído só ao Bazin. Pendências:
localização bibliográfica e confirmação da relação B3 de proventos em dinheiro.
**[DECISÃO] fonte decidida após auditoria da 0.2, em 19/10/2026:** B3 para
cálculo bruto por data ex; yfinance só conferência com aviso de divergência.
Se a B3 não responder no F2B-31, marcar [!] e registrar o motivo, sem reserva.
