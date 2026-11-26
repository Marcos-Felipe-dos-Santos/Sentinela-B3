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
  já estiver demonstrada pelos ISINs da companhia no GetDetail. C4 disciplina
  a exceção quando o GetDetail não traz ISIN.
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
| C3 · F4-D04 | Mapear `CDAM` para `UNT`. No retorno total, somar os proventos das ações componentes ponderados por `acoes_por_unit` documentadas, como em `serie_12_meses`. | TAEE11/TAEE3/TAEE4 reconciliam. Exemplo sintético em uma data ex: 1 ON a R$ 1,00 mais 2 PN a R$ 0,60 resultam em R$ 2,20 por unit. Composição ou identidade de componente sem prova impede a soma. |
| C4 · F4-D05 | Com GetDetail sem ISIN, aceitar o ISIN do próprio pregão anterior ao corte se o código CVM coincidir na data e a raiz do ISIN for a do emissor. | GetDetail vazio e CODISI próprio compatível passam. CODISI de raiz diferente, alheio ao ticker ou só posterior ao corte não prova a identidade. |
| C5 · F4-D07 | Aplicar a regra de C2 para PNA, PNB e PND, com o mapeamento do F4-A02. | Espécie histórica preferencial alheia deixa de bloquear. Se a classe analisada estiver sem ISIN, a guarda continua abstendo. |
| C6 · F4-D08 | Aplicar a regra de C2 à PN quando a ON já saiu do GetDetail e do COTAHIST. | PN própria passa com ON histórica na relação e sem efeito nos valores. PN própria sem ISIN continua abstendo. |
| C7 · F4-D10 | Retirar da comparação também o provento do complemento com data com posterior ao limite da análise ou do horizonte (T para o retorno), preservando o tratamento do anúncio pela decisão 51. | JCP mensal do BBDC com data com posterior a T deixa de impedir a prova. Data com em T ou anterior, sem par e com anúncio elegível, continua exigida. Anúncios posteriores continuam fora da soma e a DD-90 continua exigindo evidência. |

A regra é de identidade do emissor. A relação só passa à seleção do Bazin ou
do retorno depois dessa guarda, com as demais condições de cada método.
