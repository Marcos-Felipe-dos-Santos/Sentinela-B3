# Marcador da Fase 2B — decisões de 19/10/2026

**Autor das decisões:** Marcos. **Registro:** Codex, em 19/10/2026.
**Estado:** cinco fichas **1.0, aprovadas pelo Marcos em 19/10/2026**, após
veredito **pode seguir** da auditoria FICHA do Claude sobre a 0.3 (D30).
A promoção muda somente versão/status, sem regra ou número de cálculo.
Marcador liberado; execução retoma no F2B-46, sem push. As pendências atribuídas
na seção 4 continuam em vigor.

## 1. Decisões tomadas

| Ponto | Decisão do Marcos de 19/10/2026 | Efeito na fila |
|---|---|---|
| [TAXA] — decidida | Média aritmética, com peso igual por título/vencimento, das NTN-B Principal e NTN-B com cupom, vencimentos a partir de 2035; última data-base não futura | F2B-27 e F2B-30 |
| [TAXA] — decidida | CSV do Tesouro Transparente; `taxa_aplicacao` corresponde a `Taxa Compra Manha`; `taxa_resgate` a `Taxa Venda Manha`. A API da V1 sai | F2B-27; remoção da API no F2B-5 |
| [TAXA] — decidida | Prêmio de 5 pontos percentuais das ações sobre a NTN-B integral; risco Brasil já no título; nenhum spread soberano adicional | F2B-30, Gordon e bancos; não se aplica ao FII |
| [TAXA] — decidida | IPCA acumulado na janela contábil convertida, SIDRA 1737; Focus excluído da inflação; deflação permitida se 1 + π > 0 | F2B-29 e F2B-30 |
| [TAXA] — decidida | NTN-B até 5 dias úteis; último mês publicado do IPCA até 2 meses antes; só publicações até as_of, nunca data-base futura | F2B-27 e F2B-30 |
| [TAXA] — decidida | Converter taxas e fluxos; CF_nominal,t = CF_real,t × (1 + π)^t; declarar moeda-base | Todas as fichas de desconto |
| g — decidida | Opção (i): Fisher sobre ROE nominal × retenção; depois teto real pelo PIB do ano mais longo do Focus; sai GORDON_G_MAX de 8% nominal | F2B-1 e F2B-3 |
| Gordon — decidida | D0 e payout da DVA dos controladores da última DFP anual, mesma janela do LPA, JCP bruto; payout fora de (0,1] abstém; sem corte em 95%, DY 4% ou ROE 10%; ROE > 0 e k > g | F2B-1 |
| Gordon — decidida | STOCK/UNIT, modelo empresa; classes distintas abstêm na 2B; unit pela composição oficial; ROE sobre PL inicial dos controladores | F2B-1 e F2B-4 |
| [BAZIN] — decidida | Opção (b), rendimento mínimo fixo de 6%, como critério; sai BAZIN_TAXA_MIN. JCP bruto; prejuízo com DY positivo elegível com aviso; STOCK/UNIT, empresa; proventos brutos por data ex da relação B3, yfinance só conferência | F2B-31 permanece: é ele que retira a Selic do Bazin |
| [FII] — decidida | Apenas tijolo; papel, mistos sem classificação inequívoca, fundos de fundos (CPTS11/HFOF11) e classificação desconhecida abstêm até 2C | F2B-2 e F2B-4 |
| [FII] — decidida | Mediana dos últimos 5 anos do grupo tijolo contra taxa_aplicacao; 2,65 pp não é a constante aprovada, pois usou taxa_resgate | Recalibração pendente no F2B-2 |
| [FII] — decidida | Informe: maior versão entregue até as_of; 12 meses consecutivos, 13 VPs; desdobramento/grupamento ou salto de VP incompatível abstém; emissão com VP contínuo é contexto; Informe até 3 meses | F2B-2 completa as guardas que o F2B-28 ainda não entrega |
| [FII] — decidida | Perpetuidade de crescimento real zero; spread bruto sobre bruto, sem novo fator tributário; score e pontos de P/VP inalterados na 2B | F2B-2; exceção temporária ao princípio 9 do PLANO para o score |
| [BANCOS] — decidida | ROE sobre PL inicial dos controladores; payout DVA; VPA CVM; só DFP anual; g pela opção (i), limitado após Fisher | F2B-3 e F2B-32 |
| [BANCOS] — decidida | Prejuízo, payout fora de (0,1], k ≤ g ou g ≥ ROE: abstenção | F2B-3 |
| [BANCOS] — decidida | Inadimplência IF.data apenas para leitura, com conceito; Basileia fora da 2B | F2B-32; F2B-44 continua necessário para a proveniência do IF.data |
| [FINANCEIRAS] — decidida | Opção (c): modelo pelas contas-raiz do BPP consolidado; PL em 2.07/2.08 indica banco; sem BPP consolidado, abstenção | F2B-4; sai o padrão empresa por ausência de setor |
| [BTG] — decidida | Aceito GetDetail da B3, CVM 22616, CNPJ e ISIN BRBPACUNT006 no mesmo registro | F2A-39 permanece |

A identificação da B3 está em fontes-fase2b, seção 6: CNPJ
30.306.294/0001-45, otherCodes BPAC11/BRBPACUNT006, coleta de
19/10/2026 02:42 UTC. É evidência para a tabela de correções, não inferência por ticker.

### 1.1 Revisão 0.3 — decisões após auditoria do Claude, 19/10/2026

Relatório recebido: `auditoria-ficha-2b-v0.2-claude-relatorio.md`, referente ao
commit 62c160b, SHA-256 `92bf5573b30c25264930d9f71fc15bf05baa7826a0ed55af98be799be1a7a762`; veredito da 0.2:
**não pode seguir**. As decisões abaixo corrigem a interpretação da 0.2 e
substituem as condições incompatíveis dela, sem marcar fichas como aprovadas.

| Achado | Decisão do Marcos de 19/10/2026 aplicada na 0.3 |
|---|---|
| Bloqueia 1, FII | Quanto à base de cotas, abster só com desdobramento/grupamento ou salto de VP por cota incompatível com continuidade. Emissão com VP contínuo é aceita, como contexto. A alteração do total emitido não basta como veto. HGLG11 tem VP contínuo nas emissões de nov/2025, abr/2026 e mai/2026, conferido na ficha §5; mantém-se a pendência de spread no F2B-2. |
| Bloqueia 2, DVA | JCP/dividendos da DVA consolidada, por código e descrição (7.08.04.01/02 em empresa; pares do banco na tabela), são dos controladores com participação dos não controladores em linha própria, excluída da soma; ausente/zerada só autoriza reserva sem evidência de minoritários, nos termos do F2A-41, nunca com dado inválido/conflitante ou sem correspondência. Sem essa estrutura, abster. Ambev tem 485.033 mil em 7.08.04.04 e Itaú 992.000 mil em 7.09.04.04: não abstêm por perímetro. F2B-1/F2B-3 completam o mapeamento necessário, sem implementação neste commit. |
| Bloqueia 3, Bazin | Fonte: relação de proventos em dinheiro da B3, empresas listadas, tipo, valor bruto por ação e data ex. Yfinance só conferência, com aviso de divergência. F2B-31 confirma que o serviço responde e o leiaute; se não responder, [!] com motivo, sem reserva por yfinance. |
| Ressalva 4, Gordon | ROE sobre PL inicial dos controladores, como bancos. ABEV3: comparativo 31/12/2024 da DFP 2025 v1, 99.580.514−938.375=98.642.139 mil R$; ROE 15,716812466932%, g real 0,386958636840%, valor R$ 6,161748819933. Sensibilidade e reprodução atualizadas. |
| Ressalva 5, Focus | Consulta original de PIB reforçada em §2.3 com data, instante de gravação conhecido, URL, filtro, resposta bruta preservada e SHA-256; pesquisa 16/10/2026, ano 2030, base 0, mediana 2%. Não confundir pesquisa com publicação ou gravação local. |

O Claude confirmou os capítulos de Fisher (II) e Damodaran 3ª ed. (7, 13, 19,
21) e a referência de Gordon/Shapiro (1956, pp. 102–110); páginas dos livros
não foram conferidas. Localização do critério de 6% em Bazin continua declarada
como limitação, aceita pelo relatório como tal, sem página inventada. A próxima
auditoria FICHA das cinco **0.3 é do Claude**, D30; aprovação continua com Marcos.

### 1.2 Aprovação das cinco fichas — Marcos, 19/10/2026

Auditoria FICHA: **Claude**, sobre o commit **19d46ac**, fichas 0.3.
Relatório `auditoria-ficha-2b-v0.3-claude-relatorio.md`, SHA-256
`47c904f7a46b6c9b70370f6045431b5f125742b2a0aace56056f29adea7452d4`. Veredito: **pode seguir**;
os cinco achados da rodada anterior foram fechados e as contas conferiram.

**Aprovação expressa do Marcos em 19/10/2026:** taxa-real, Gordon, Bazin,
FII e bancos promovidas de 0.3 a **1.0**, com status aprovado, **sem mudar
regra nem número**. Cumprida a etapa 5 de ciclo-de-fase.md, D21/D30;
o marcador da fila passa a [x] e o loop retoma no F2B-46 (etapa 4).

**Pendências não bloqueantes preservadas:** F2B-2 recalibra o spread;
F2B-31 confirma a relação de proventos B3 (sem resposta, [!]); F2B-1/F2B-3
mapeiam os pares da DVA na tabela de contas; referências mantêm as páginas e
a localização da regra de 6% de Bazin não conferidas. A aprovação não declara
essas tarefas entregues nem muda suas condições de abstenção/bloqueio.

## 2. Contratos comuns da revisão 0.3

Estas regras são especificação documental para os itens futuros; não descrevem uma
implementação já concluída. D16/D17: registrar referência, entrega/publicação,
coleta, versão, URL, hash e unidade. Selecionar primeiro por disponibilidade até
`as_of`, depois pela referência e pela maior versão numérica. Sem prova de
publicação, abstenção: "disponibilidade histórica não demonstrada". Uma coleta
posterior não prova disponibilidade anterior. Conflitos na mesma chave/versão
abstêm; duplicatas idênticas contam uma vez. Referência futura é recusada antes de
qualquer conta. Dados desconhecidos nunca viram zero.

### 2.1 Validade comum, aplicada a cada linha das matrizes das fichas

| Caso, nesta precedência | Resultado e motivo |
|---|---|
| Ausente (None, campo/linha inexistente, vazio) | Abstenção: "insumo ausente: <nome>" |
| Não numérico, booleano ou escala/unidade indeterminada | Abstenção: "insumo inválido: <nome>, tipo ou unidade"; não inferir unidade pela magnitude |
| NaN | Abstenção: "insumo inválido: <nome>, NaN" |
| +infinito ou −infinito | Abstenção: "insumo inválido: <nome>, infinito" |
| Zero | Regra explícita da linha da ficha; nunca equivale a ausente |
| Negativo | Regra explícita da linha da ficha; não substituir por reserva positiva |
| Fora da faixa ou conflito | Abstenção: "insumo fora do domínio: <nome>, <regra>" |
| Resultado/intermediário não finito | Abstenção: "resultado não finito: <etapa>"; nenhum número na saída |

Validar antes de soma, divisão, Fisher, min ou teto; limite não pode esconder NaN
ou infinito. Nos motivos de zero/negativo, usar "insumo fora do domínio: <nome>,
<condição da matriz>". Campos contextuais inválidos produzem "<nome> não informado:
<motivo>" e não impedem a lente, salvo se a ficha os declarar essenciais.

### 2.2 Tempo, moeda e idade

- `as_of` é instante com fuso America/Sao_Paulo; dado só com data, sem horário,
  entra conservadoramente depois do fim desse dia. Toda comparação registra o fuso.
- Dias úteis da NTN-B: calendário oficial de negociação/liquidação do Tesouro,
  com fins de semana e feriados nacionais; contar dias úteis em (data-base, as_of].
  Sem calendário comprovado, não atestar a idade. Não confundir TTL do cache com idade.
- IPCA: janela de meses civis entre início e fim do exercício convertido. Para
  exercício janeiro–dezembro, variável 2265 em dezembro; para outra janela,
  produto das variações mensais (variável 63) ou razão de números-índice (2266).
  Não usar o IPCA recente de outra janela no lugar. A verificação de atualidade
  exige cobertura da série até um mês no máximo dois meses anterior a as_of;
  o ponto de dezembro usado para converter a DFP anual continua sendo dezembro.
  Assim, atualidade da fonte e janela da conversão são verificadas separadamente.
- DFP: maior exercício anual completo disponível e exigível no calendário CVM,
  versão entregue até as_of. Idade máxima é um ciclo anual mais o prazo oficial
  de entrega da DFP; decorrido o prazo do exercício seguinte, a DFP anterior não
  serve. Para emissor nacional de exercício de 12 meses, teto de 15 meses
  (12 + até 3 meses), antecipado quando a entrega seguinte já for exigível:
  [Resolução CVM 80, art. 30, II, a](https://conteudo.cvm.gov.br/export/sites/cvm/legislacao/resolucoes/anexos/001/resol080consolid.pdf).
  Registrar o prazo/calendário usado; sem demonstrá-lo, abster por idade
  indeterminada. ITR não substitui nem anualiza essa janela.
- Preço: para resultado corrente, último pregão encerrado antes de as_of (idade
  máxima: um pregão disponível). Exemplos abaixo usam deliberadamente 30/09/2026
  como preço de comparação fixo solicitado, com macro de outubro. São cenários
  ilustrativos, não reconstruções históricas estritas em setembro nem resultado
  corrente em outubro. Falta de pregão não autoriza usar a última linha física.
- Classificação, composição, eventos e direitos: última evidência oficial vigente
  até as_of; idade máxima é a vigência documentada, não um número arbitrário de
  dias. Sem confirmação de vigência ou com mudança estrutural não conciliada,
  abster. Índice e setor não substituem BPP nem direito de classe.
- Focus PIB: BCB Olinda, `ExpectativasMercadoAnuais`, `Indicador = PIB Total`,
  `baseCalculo = 0` (respondentes nos últimos 30 dias, em vez da base recente 1), `Mediana` em %,
  convertida uma vez para razão. Selecionar a última data de pesquisa comprovadamente
  publicada até as_of; nessa data, maior ano de `DataReferencia`. Não escolher
  silenciosamente a primeira linha nem mesclar bases. Série anual sem parâmetro
  de suavização; não usar a série de inflação de 12 meses. Idade máxima: a última
  edição devida pelo calendário de divulgação do BCB, sem tolerância adicional;
  nova edição devida mas indisponível causa abstenção. O teto pode ser zero ou
  negativo se > −1; não é substituído por 2% fixos nem pelo teto nominal de 8%.
  A janela de 30 dias está identificada na nota de respondentes do
  [Focus/BCB](https://www.bcb.gov.br/content/focus/focus/R20251024.pdf);
  a seleção operacional fixa expressamente a base 0 do recurso anual.

Moeda-base de cada exemplo é o real da data final do exercício ou da janela do
Informe, conforme indicado. Fluxos anuais agregados são posicionados no fim do
período: aproximação explícita, sem afirmar ajuste intramensal por data de pagamento.
Usar inflação realizada dessa janela como conversor constante das projeções é
hipótese de cenário, não expectativa estimada de inflação futura. Se atualizar a
moeda-base até outra data, atualizar todos os fluxos e valores pela mesma razão
de índices; não atualizar apenas o denominador ou apenas o preço de comparação.

### 2.3 Evidência dos exemplos e precisão

Contas refeitas com Python padrão (`csv`, `zipfile`, `decimal`, `json`, `hashlib`),
sem importar o projeto, Decimal com 45 algarismos. Percentuais entram como razões;
intermediários permanecem sem arredondamento; centavos e percentuais nas tabelas
são só apresentação. Tolerância aritmética futura: absoluto de R$ 0,000001 e
1e−10 para razões, calculando dos insumos brutos, nunca das células arredondadas.
Isto não elimina a incerteza econômica nem a precisão limitada dos dados publicados.

| Snapshot público | Identificação e disponibilidade observada |
|---|---|
| Tesouro CSV, base 15/10/2026 | SHA-256 f4f9b0fb9a1850da4cbca47d5b896464c04b21b302cf591de178726a426e2972; coleta 19/10, conforme fontes-fase2b §1 |
| DFP 2025, CVM | data/cvm/dfp_2025.zip; SHA-256 9fa64012518d104b7ceb294648331bf852bf4014b1ac141a67976823ce2b278d; coleta 13/10/2026 18:48 UTC |
| COTAHIST_M092026.ZIP, B3 | SHA-256 f164e17727b4eee2ac8e74c0188feb41fdedc64b2c49311c7cad9f6e81c85b1c; seleção por data, ticker e mercado 010 |
| Informe 2025, CVM | SHA-256 0413308766b306a557bc19fa00fb5dd0ed63f8f3dffe760ee59c59682b0750ca |
| Informe 2026, CVM | SHA-256 eac25b77664933c8b79a19056ea51c591f23e7fdc1c0c101a978d83d87f22fbb; coleta 19/10/2026 03:04 UTC |
| IPCA 2025 | [SIDRA 1737, variável 2265, dezembro](https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2265/p/202512): 4,26%; publicado em 09/01/2026, conforme [IBGE](https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/45612-ipca-vai-a-0-33-em-dezembro-e-fecha-o-ano-em-4-26) |
| Atualidade IPCA | setembro/2026, publicado 09/10/2026; variável 2265 = 4,58%, só controle da cobertura, sem substituir 4,26% do exercício de 2025 |
| Focus PIB | [consulta Olinda](https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais?$format=json&$filter=Indicador%20eq%20'PIB%20Total'&$orderby=Data%20desc&$top=100), obtida em 19/10/2026 antes de 20:08 UTC; SHA-256 d0fb1e1bd19dbf7cbac8a70d4c3b60daf9d1fcf5cdb6fafb6972b135c3fb6081; Data 16/10/2026, ano 2030, base 0, mediana 2,0000% |

**Registro explícito da consulta Focus PIB (complemento da 0.3, 19/10/2026):**

- Serviço BCB Olinda `ExpectativasMercadoAnuais`; requisição original:
  `$format=json&$filter=Indicador%20eq%20'PIB%20Total'&$orderby=Data%20desc&$top=100`,
  na URL da linha Focus acima. A resposta contém ambas as bases; seleção explícita
  `baseCalculo=0`, `Data=2026-10-16`, maior `DataReferencia=2030`.
- Consulta em **19/10/2026**; a cópia original foi gravada em
  **2026-10-19T20:07:43.009903+00:00**, conforme mtime do arquivo da consulta,
  antes do as_of de 20:10 UTC. É evidência de disponibilidade observada, não
  horário de publicação pelo BCB nem instante da pesquisa.
- SHA-256 da **resposta bruta completa**, antes de filtrar: `d0fb1e1bd19dbf7cbac8a70d4c3b60daf9d1fcf5cdb6fafb6972b135c3fb6081`.
  Cópia preservada para conferência local em
  `outputs/levantamento_cache/f2b21/focus_pib_ficha03.resposta` (cache público,
  fora do git). O hash não é o de um JSON reserializado ou apenas da linha selecionada.
- Registro selecionado: `Indicador=PIB Total`, `Data=2026-10-16`,
  `DataReferencia=2030`, `baseCalculo=0`, `Mediana=2.0000` (%),
  `numeroRespondentes=72`. Teto em razão **0,02**, não constante substituta
  para uma consulta futura indisponível. Não atualizar a resposta para fingir
  que é a mesma coleta histórica.

`as_of` dos cenários: **19/10/2026 20:10 UTC (17:10 de Brasília)**.
O snapshot atesta disponibilidade até esse instante, não desde a data de pesquisa.
DFP Ambev v1 entregue em 12/02/2026; Itaú v2 em 12/02/2026; Renner v2 em
05/03/2026 (índice do próprio ZIP). Entregas de versões do Informe e eventos não
foram integralmente conciliados: exemplos que dependem delas são diagnósticos
aritméticos e devem abster na saída operacional enquanto faltar a evidência.

## 3. Destino dos bugs do F2B-43

**Decisão do Marcos de 19/10/2026:** novo F2B-46, antes do F2B-27, para
BUG-2B-01 (ITR sem DVA), BUG-2B-04 (domínio inválido, incluindo coluna de ações
inexistente e ROE), BUG-2B-06 (completude por modelo/classe), BUG-2B-12 (ticker
inválido) e proventos com apenas dividendos ou apenas JCP. Os quatro IDs já têm
regressões; o último sintoma ainda precisa de regressão própria antes da correção.
O F2B-46 deve conferir o próximo ID livre no registro e criá-la; não atribuir um
ID existente a outro sintoma. O BUG-2B-04 inclui preço infinito e quantidade
fracionária de unit, além dos exemplos nomeados: manter a cobertura do contrato 1.1.

Para a proposta da 2C (F2B-34): BUG-2B-02 (cache duplicado), 03 (três tentativas
em 404), 05 (alerta PNA/PNB), 07 (divulgados_coerentes), 08 (_meses), 09 (corrida
da proveniência), 10 (CNPJ com espaços), 11 (caixa da classe), e BTCI11/TRPL11
(ainda sem regressão própria; registrar antes de corrigir). Não mover nem enfraquecer
xfails neste commit documental; F2B-46 e F2B-34 atualizam o destino no registro
quando executados. Não confundir encaminhamento com bug corrigido.

## 4. Pendências para a auditoria e os itens executores

- Conferência bibliográfica onde consta "a conferir pelo auditor". A revisão
  distingue fonte consultada de edição não acessível; não inventa páginas.
- F2B-2: recalibrar o spread com taxa_aplicacao, excluindo desdobramento/grupamento ou
  salto de VP incompatível e mantendo emissão com VP contínuo em contexto; documentar
  amostra, cobertura, exclusões, sobrevivência, classificação temporal e efeito
  dos meses removidos. Sem constante validada, a lente se abstém.
- F2B-31: confirmar a relação B3 de proventos em dinheiro e seu leiaute; sem resposta,
  marcar [!]; yfinance só conferência com aviso de divergência. Comprovar JCP bruto
  e janela por data ex; campo agregado sem essa
  garantia não basta. A DVA anual do exemplo não prova provento por data ex.
- F2B-1/F2B-3: aplicar a regra operacional de estrutura separada da DVA ou reserva
  sem minoritários da §1.1; sem estrutura, abstenção; conferir direitos. Nos bancos, conferir a ponte
  entre patrimônio, retenção e payout quando o teto de crescimento atuar.
- Auditoria FICHA da 0.3 concluída pelo Claude, "pode seguir"; aprovação expressa
  do Marcos em 19/10/2026 e promoção documental a 1.0 registradas na seção 1.2.
  Nenhum método é implementado pela aprovação; as pendências acima continuam atribuídas.

## 5. Reprodução aritmética mínima (Python padrão)

Os quocientes abaixo usam os valores brutos das seções 5 das fichas. A seleção
nos CSVs usa CNPJ, DT_REFER, VERSAO numérica, ORDEM_EXERC e par código/descrição;
o COTAHIST usa data, ticker, mercado 010 e fator de cotação. Não selecionar pela
ordem física. Este bloco reproduz o núcleo; a admissibilidade temporal e por
classe continua independente da conta.

```python
from decimal import Decimal as D, getcontext
getcontext().prec = 45
pi = D("0.0426")
y = sum(map(D, ["6.84", "6.73", "6.73", "6.74", "6.82", "6.83",
                "6.75", "6.75", "6.75", "6.71", "6.73"])) / D(1100)
k = y + D("0.05")
kn = (1 + k) * (1 + pi) - 1
# Gordon: payout por totais; ROE sobre PL inicial; D0 por ações finais.
lucro, pl, proventos, acoes = map(D, ["15503400", "98642139", "10903280", "15616526"])
p = proventos / lucro
roe = lucro / pl
g = min((1 + roe * (1 - p)) / (1 + pi) - 1, D("0.02"))
d0 = proventos / acoes
vg = d0 * (1 + g) / (k - g)
vgn = (d0 * (1 + g) * (1 + pi)) / (kn - ((1 + g) * (1 + pi) - 1))
assert abs(vg - vgn) < D("1e-35")
# Bancos: PL inicial para ROE, final para VPA.
roe_n = D(44857000) / D(211090000)
p = D(33704000) / D(44857000)
g = min((1 + roe_n * (1 - p)) / (1 + pi) - 1, D("0.02"))
roe_r = (1 + roe_n) / (1 + pi) - 1
vpa = D(204501000) / D(11026524)
pvp = (roe_r - g) / (k - g)
gn = (1 + g) * (1 + pi) - 1
p_projetado = 1 - gn / roe_n
assert abs(p_projetado - p) < D("1e-35")  # teto inativo neste caso
assert abs(pvp - (roe_n - gn) / (kn - gn)) < D("1e-35")
# Bazin: exemplo por competência, só controle da divisão.
d_bazin = D(834310) / D(982199)
# FII: soma exata dos produtos da tabela, cenário condicional.
r_fii = D("13.240529645135538184")
print(y, k, kn, vg, pvp, pvp * vpa, d_bazin / D("0.06"),
      r_fii / (y + D("0.02")))
```
