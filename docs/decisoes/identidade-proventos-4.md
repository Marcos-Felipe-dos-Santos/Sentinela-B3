# Identidade dos proventos da B3 — proposta da Fase 4

**[DECISÃO] do Marcos (F4-D01b).** Proposta para auditoria FICHA. A decisão
[53](decisoes-fase4.md) fixa as exceções por causa. Cada exceção só entra no item
correspondente, depois da aprovação. Esta ficha é a referência comum para o
Bazin e o retorno total histórico.

## Fontes, identidade e corte

- O índice oficial na data fornece o código CVM do ativo. Usar o índice de D
  na análise e o vigente no corte do horizonte para o retorno. Código CVM da
  coleta ausente, divergente ou sem prova na data impede a ligação. Ticker
  atual, nome e raiz de quatro letras sozinhos não provam identidade.
- O GetDetail consultado pelo código CVM fornece nome de pregão e ISINs
  (`otherCodes`). A relação GetListedCashDividends vem pelo nome de pregão
  normalizado pela decisão 30. O complemento GetListedSupplementCompany e os
  dados da relação pertencem à mesma coleta. Erro, relação vazia ou homônimo
  rejeitado pela conferência implicam abstenção.
- O COTAHIST fornece o CODISI do próprio ticker em pregão anterior ao corte.
  Na regra da decisão 43, só acrescentar um ISIN do pregão quando sua raiz
  já estiver demonstrada pelos ISINs da companhia no GetDetail. A seção D3 disciplina a exceção quando o GetDetail não traz ISIN.
- A decisão 51 aplica o corte diário D à análise. Para retorno até T, usar
  o dia seguinte a T como corte exclusivo para anúncios, preservando a
  convenção do produtor. O corte de identidade é distinto da data ex e da
  janela econômica que decide a soma.

## Regra de base (decisão 33)

1. **(a) Espécies.** Na regra de base, cada espécie da relação (`typeStock`)
   precisa ter ISIN da companhia no GetDetail, com a extensão documental
   do pregão da decisão 43. GetDetail sem ISIN ou linha ilegível abstém.
2. **(b) Correspondência do complemento.** Comparar todos os proventos em
   dinheiro do complemento, sem recortar pela espécie ou pela janela de
   soma (DD-06). Usar a data com (`lastDatePrior` no complemento,
   `lastDatePriorEx` na relação) e o valor (`rate` e `valueCash`). A regra
   `mesmo_valor` arredonda o valor do complemento a quatro casas com empate
   para cima e aceita diferença de até 0,00005. Data com ou valor ilegíveis
   impedem a prova. Pela decisão 51, uma linha sem par com anúncio legível
   no corte ou depois não impede a identidade. Anúncio ilegível segue
   comparado. Na comparação de identidade vigente, um anúncio posterior já
   pareado pode contar como evidência, sem se tornar elegível para a soma.
3. **(c) Complemento com evidência.** Complemento vazio abstém pela regra de
   base. Mesmo após ignorar divergências posteriores ao corte, pelo menos
   um provento do complemento precisa ter par na relação (DD-90). C1 é a
   exceção para complemento efetivamente vazio. Complemento ilegível ou
   ausente não equivale a resposta válida e vazia.

### Exceções por causa e casos de aceite

Em toda linha, exercitar o caso positivo pelo produtor e repetir com código
CVM divergente e com raiz reciclada. No caso C8 (BUG-3-60), o evento de outro
emissor com a mesma raiz não muda a identidade nem o resultado; evento do
próprio emissor continua reconciliável. Preservar o tratamento vigente de
ISIN ilegível. As guardas de data ex e deduplicação permanecem.

| Causa e item | Exceção proposta | Caso positivo e controle negativo específico |
|---|---|---|
| C1 · F4-D09 | Complemento válido e vazio pode passar se o código CVM coincidir e o ISIN do ticker estiver no GetDetail. Complemento não vazio segue DD-90. | Vazio com código e ISIN corretos passa. Vazio sem ISIN próprio, homônimo da decisão 30 e complemento não vazio sem correspondência continuam abstendo. |
| C2 · F4-D06 | Aplicar (a) à espécie analisada e às componentes documentadas da unit. Espécie histórica alheia à análise não exige ISIN próprio e não entra na soma. | ON hoje com PN histórica passa para a ON. A ausência de ISIN da própria ON ou de componente exigida continua abstendo. |
| C3 · F4-D04 | Mapear `CDAM` para `UNT` e reconciliar o complemento pela seção D3 mesmo sem linha UNT na relação. No retorno total, somar os proventos das ações componentes ponderados por `acoes_por_unit` documentadas, como em `serie_12_meses`. | TAEE11/TAEE3/TAEE4 reconciliam. Exemplo sintético em uma data ex: 1 ON a R$ 1,00 mais 2 PN a R$ 0,60 resultam em R$ 2,20 por unit. Composição ou identidade de componente sem prova impede a soma. |
| C4 · F4-D05 | Com GetDetail sem ISIN, exigir que o CODISI completo do pregão anterior ao corte seja ligado historicamente ao código CVM pela prova da seção D3. | GetDetail vazio e CODISI próprio compatível passam. CODISI de raiz diferente, alheio ao ticker ou só posterior ao corte não prova a identidade. |
| C5 · F4-D07 | Aplicar a regra de C2 para PNA, PNB e PND, com o mapeamento do F4-A02. | Espécie histórica preferencial alheia deixa de bloquear. Se a classe analisada estiver sem ISIN, a guarda continua abstendo. |
| C6 · F4-D08 | Aplicar a regra de C2 à PN quando a ON já saiu do GetDetail e do COTAHIST. | PN própria passa com ON histórica na relação e sem efeito nos valores. PN própria sem ISIN continua abstendo. |
| C7 · F4-D10 | Retirar da comparação também o provento do complemento com data com posterior ao limite da análise ou do horizonte (T para o retorno), preservando o tratamento do anúncio pela decisão 51. | JCP mensal do BBDC com data com posterior a T deixa de impedir a prova. Data com em T ou anterior, sem par e com anúncio elegível, continua exigida. Anúncios posteriores continuam fora da soma e a DD-90 continua exigindo evidência. |

A regra é de identidade do emissor. A relação só passa à seleção do Bazin ou
do retorno depois dessa guarda, com as demais condições de cada método.


## D3 · Decisão do Marcos de 26/11/2026

**C3, correspondência CDAM.** Para o mesmo emissor, tipo de provento e data
com, provar a composição vigente da unit por documento oficial de
composição (FCA entregue no corte ou documento arquivado da B3). Identificar
uma distribuição única pelas linhas correspondentes de cada componente.
Calcular em decimal a soma dos valores brutos por ação multiplicados pela
quantidade de cada componente, sem arredondar parcelas. Comparar a soma
e o valor CDAM após arredondar ambos a quatro casas pelo critério de
empate para cima da DD-06. Para este par, exigir **igualdade exata** nessa
precisão. Componente ausente, divergência ou pareamento ambíguo entre
distribuições da mesma data e natureza abstém. A correspondência vale
sem linha UNT na relação. A linha CDAM e suas componentes são duas
representações da mesma distribuição. Se ambas existirem e conferirem,
contar uma vez. Provento de natureza diferente na mesma data é outra
distribuição.

**Aceite independente de TAEE11.** No recorte de 14/08/2026, a composição
1 ON + 2 PN soma o dividendo de R$ 0,08025458488 por componente em
R$ 0,24076375464 por unit. Para o JCP, R$ 0,11982485996 por componente
produz R$ 0,35947457988 por unit. Os valores conferem com as linhas
CDAM do complemento. Testar ambas as representações, divergência de
0,0001 após o arredondamento e ausência ou ambiguidade de componente.
No teste independente do retorno, usar esses fluxos e preços sintéticos
de R$ 40 na entrada, R$ 39 na data ex comum e R$ 42 em T, sem evento
em ações. Uma unit inicial vira
`1 + (0,24076375464 + 0,35947457988) / 39` units.
O retorno é o valor final dessas units dividido por 40, menos 1
(**6,61602690063%**). Repetir com a linha UNT duplicando a representação,
com o mesmo resultado. Esses preços são um oráculo sintético do teste.

**C4, vínculo histórico.** Quando a coleta a validar vem com GetDetail
vazio de ISIN, buscar uma resposta histórica oficial da B3 GetDetail
arquivada e datada, disponível no corte, cujo registro liga
`codeCVM` e `otherCodes` com o ISIN completo. A coleta histórica com
`cd_cvm` e `isins_json` pode servir quando houver prova da origem,
data e validade do vínculo no pregão consultado e ele for compatível
com o FCA/índice oficial daquele período. Juntar pelo CODISI completo
do COTAHIST e pelo código CVM provado, e conferir CNPJ quando informado.
Raiz coincidente ou o ticker sozinho são insuficientes. Vínculo ausente,
posterior ao corte, revogado ou conflitante abstém. Testar GetDetail
vazio com vínculo válido e com raiz reciclada por outro emissor, inclusive
se os dois compartilharem a mesma raiz e o ISIN histórico do alheio
estiver arquivado.

**Deslistada antes de T.** Recuperar o código no índice oficial vigente
no último pregão negociado do ativo na janela, com o CODISI da série
validado pelo mesmo vínculo histórico e conferido com o emissor
demonstrado na entrada. Usar essa identidade para a relação, mantendo
o corte do horizonte para a prova de identidade e o último pregão como
limite econômico dos proventos. A lacuna no índice em T não basta para
recusar a deslistada. Se faltar a prova histórica ou houver troca de
emissor, abster. Testar recuperação do código, raiz reutilizada após a
deslistagem e ausência de evidência da identidade antiga.
