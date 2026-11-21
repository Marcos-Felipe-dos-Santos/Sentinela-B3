# Contrato de histórico estrito do Informe de FII e das taxas (F3-P12)

Contrato da Fase 3 para ler o Informe mensal de FII, a composição, os eventos de cota e a taxa real numa data D passada. É a base do F3-3c, que implementa o leitor, e do F3-3d, que o liga à cascata. Este item não muda produção.

Origem:
- tabela F3-P12 da fila;
- as oito regras ratificadas da F2C-47 (`docs/loop/fila.md`, seção "F2C-47");
- o adendo de 09/11 das decisões da Fase 3 (D17: modo estrito no backtest principal, reconstrução exploratória separada e rotulada);
- os números do L1 (`docs/decisoes/l1-fontes-historicas.md`).

## 1. Princípios

1. **Estrito:** numa data D vale só o que um arquivo ou documento oficial prova que existia até D. Sem prova, abstém com motivo; nunca usa um número conservador no lugar.
2. **Exploratório:** pode usar a última versão disponível. Leva o rótulo `exploratorio` e o aviso "possível reapresentação posterior não observável". Nunca se mistura com o estrito na mesma série ou no mesmo resultado (aceite do F3-3c).
3. **A data da coleta não é prova histórica** (F2C-47, regra 4). Baixar hoje um arquivo anual não prova o que ele continha em D. A prova vem das datas de entrega registradas dentro do próprio arquivo, e o hash do download só identifica o que foi lido.
4. **As regras ratificadas não mudam:**
   - vazio é diferente de zero (regra 1);
   - versão numérica elegível (regra 2; o BUG-2C-27 foi corrigido no F3-P08);
   - a entrega da composição é a do documento geral de mesma identidade, referência e versão (regra 3);
   - a idade da NTN-B continua um motivo comum (regra 5);
   - a assimetria entre FII e Gordon é mantida (regra 6);
   - a taxa do FII é do mesmo dia local e não futura (regra 7);
   - sem resposta da B3, os eventos ficam indisponíveis e não viram lista vazia (regra 8).

## 2. Informe mensal de FII (CVM)

**Fonte:** `dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{ano}.zip`, aberta desde 2016 (L1). Cada ano traz três arquivos:

| Arquivo | Chave | Data de entrega |
|---|---|---|
| `inf_mensal_fii_geral_{ano}.csv` | `CNPJ_Fundo_Classe`, `Data_Referencia`, `Versao` | `Data_Entrega` |
| `inf_mensal_fii_complemento_{ano}.csv` | a mesma | não tem |
| `inf_mensal_fii_ativo_passivo_{ano}.csv` | a mesma | não tem |

**O que a fonte guarda:** só a versão vigente de cada fundo e referência. Na amostra de 2023, baixada em 11/11/2026 (SHA-256 `954d67545e918ec2aeb6557c923d81823ae3f9a777d4fedd177a855381d372eb`), os 10.256 documentos do arquivo geral têm uma única versão e uma única `Data_Entrega` cada. É o mesmo padrão das demonstrações das companhias (L1, seção 2).

**Prova em D, no modo estrito:**
- **Documento geral:** a linha de (fundo, referência) vale em D se `Data_Entrega` é anterior ao dia local de D (São Paulo), como a `Data Base` da taxa (§5). A `Data_Entrega` não tem hora, então um documento entregue no próprio dia de D não entra. A versão é a que o arquivo traz, que é a última entregue.
- **Última entrega posterior a D:** abstém com o motivo "versão vigente em D não disponível na fonte aberta (última entrega posterior)". A versão anterior existiu, mas os números dela não estão no arquivo. É a mesma regra da DD-34.
- **Complemento e ativo/passivo:** a entrega é a do geral com a mesma (`CNPJ_Fundo_Classe`, `Data_Referencia`, `Versao`) (regra 3). Sem esse par no geral, abstém, sem inventar data própria.
- **Vazio, zero e versões:** valem as guardas atuais, aplicadas mês a mês.
  - Vazio diferente de zero (regra 1).
  - Conflito na mesma versão abstém (ficha FII 1.3).
  - Versão ilegível conta como ausência (F3-P08; os BUG-3-03 a 05 vão para o F3-3c-fix).
- **A janela de 12 meses do rendimento** só usa meses com prova em D. Mês sem prova interrompe a janela e o rendimento abstém, como hoje com a versão ilegível.
- **Primeiro ano:** o Informe é aberto desde 2016. Antes disso, abstém com "Informe aberto indisponível para a data".

**Exploratório:** usa a linha disponível mesmo que a `Data_Entrega` seja posterior a D, com o rótulo e o aviso do §1.2.

## 3. Composição do FII

A composição (ativos, imóveis, cotistas) vem do complemento e do ativo/passivo do mesmo Informe. Pela regra 3, a entrega dela é a do documento geral correspondente, e as regras de prova e abstenção são as do §2. Composição sem documento geral provado em D não entra no estrito.

## 4. Eventos de cota (B3)

**Fonte:** `sistemaswebb3-listados.b3.com.br/fundsProxy/fundsCall`. É o complemento do fundo listado, com `stockDividends` (desdobramentos e grupamentos: `label`, `lastDatePrior`, `factor`) e `cashDividends` recentes.

**O que a fonte guarda:**
- Só a consulta de hoje (um snapshot), sem a data em que cada evento foi divulgado.
- Só fundos listados hoje: a mesma limitação das companhias deslistadas no L1 (DD-35).

**Prova em D, no modo estrito:**
- **Evento conhecido em D:** um evento com `lastDatePrior` ≤ D conta, com o snapshot de hoje (hash e data) na proveniência.
- **Limitação declarada:** a B3 não traz a data de divulgação. Supõe-se que um evento com data-com até D era conhecido em D. Um evento lançado depois com data-com retroativa contraria essa suposição e não é detectável. A proveniência leva "data de divulgação do evento não observável".
- **Evento depois de D:** não conta para a continuidade em D.
- **Cobertura do snapshot:** se ele não cobre o intervalo da janela de 12 meses até D (o primeiro evento ou dado devolvido é posterior ao início da janela), a continuidade não é demonstrável. O resultado abstém com o motivo atual, "fonte de eventos de cota indisponível: continuidade não demonstrável" (`rendimento_fii.py`).
- **Sem resposta da B3:** "eventos indisponíveis" (regra 8).
- **Fundo deslistado,** sem cadastro na B3: abstém pelo mesmo motivo.

**Exploratório:** igual ao estrito. Não há versão de evento para reconstruir, só a cobertura do snapshot. O resultado exploratório leva o rótulo pelos outros insumos (Informe), e não por causa dos eventos.

## 5. Taxa real (Tesouro Direto)

**Fonte:** CSV `precotaxatesourodireto.csv` do CKAN do Tesouro Transparente, com histórico desde 31/12/2004 para a NTN-B e desde 18/07/2005 para a NTN-B Principal (L1). O arquivo é regenerado a cada dia e traz uma linha por título e `Data Base`.

**Prova em D, no modo estrito:**
- **Data-base:** vale a cesta da última `Data Base` anterior ao dia local de D (`tesouro.ler_csv`, `data_base < as_of`), com as guardas de idade atuais em dias úteis e o motivo comum de idade (regra 5).
- **Registro do FII:** é do mesmo dia local de D e não futuro (regra 7). No histórico, o "mesmo dia" é o dia de D, e não o dia da coleta.
- **Limitação declarada:** a revisão posterior de uma linha passada não é observável, porque o arquivo só traz o valor atual de cada `Data Base`. O registro leva "valores do histórico atual do Tesouro; revisão posterior não observável" na proveniência. Isso não muda o modo, porque a linha datada é a prova documental da taxa naquela data-base (DD-37).
- **D anterior ao início da série:** abstém.

**Assimetria FII e Gordon (regra 6):** o FII exige `as_of` no registro da taxa, e o Gordon só o valida quando presente. O histórico não harmoniza os dois. O leitor histórico fornece sempre o `as_of` = D, e cada consumidor aplica a própria regra.

## 6. Resumo

| Insumo | Prova de disponibilidade em D | Estrito | Exploratório | Rótulo e motivo |
|---|---|---|---|---|
| Informe, geral | `Data_Entrega` anterior ao dia de D, da versão no arquivo | Usa; com a última entrega depois de D, abstém | Usa a linha disponível | `exploratorio` e "possível reapresentação posterior não observável" |
| Informe, complemento e ativo/passivo | entrega do geral de mesma identidade, referência e versão | Como o geral; sem par, abstém | Como o geral | Idem |
| Composição | idem (regra 3) | Idem | Idem | Idem |
| Eventos de cota (B3) | `lastDatePrior` ≤ D no snapshot de hoje, com cobertura da janela | Usa; sem cobertura ou sem resposta, abstém | Igual | Motivo de continuidade não demonstrável ou de eventos indisponíveis |
| Taxa (Tesouro) | linha com `Data Base` < dia de D no CSV histórico | Usa, com a guarda de idade e o registro do mesmo dia de D | Igual | "revisão posterior não observável" na proveniência |

## 7. Para o F3-3c

- Leitor do Informe por D, com os dois modos separados e testados para nunca se misturarem. O caso de reapresentação da DD-34 é aplicado ao `Data_Entrega`.
- Teste de equivalência: com D = hoje, os mesmos insumos da cascata atual.
- O contrato da taxa e dos eventos é aplicado no F3-3d, que liga os leitores à cascata (com o BUG-3-15 das demonstrações).
- Nenhuma regra da F2C-47 muda. Mudar alguma delas é decisão do Marcos (política, §3, caso 1).
