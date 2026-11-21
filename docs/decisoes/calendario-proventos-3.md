# Calendário anual de proventos para a lente de qualidade — contrato (F3-P14a)

**Status:** levantamento do executor (claude-code, 12/11/2026), para o F3-P14b. Origem:
FC2C-70, ficha de qualidade 1.0 §9 (`docs/metodologia/qualidade.md`), linha F3-P14 da tabela
de pendências da fila. Não muda regra econômica: a lente de qualidade 1.0 continua igual e só
passa a receber o calendário que hoje nenhum produtor de produção grava.

## 1. O consumidor e a chave

O consumidor é `sentinela/data/qualidade_inputs.py` (`_provento`), chamado por
`valuation_engine.py` (`qualidade_inputs.entradas(dados, instante)`), que alimenta
`sentinela/methods/qualidade.py` (indicador `proventos`, regularidade por exercício). A chave é
`dados["calendario_proventos_b3"]`, um mapeamento com:

| Campo | Conteúdo | Conferência do consumidor (código atual) |
|---|---|---|
| `fonte` | texto não vazio que identifica os arquivos oficiais | não vazio |
| `coleta` | instante ISO com fuso | `coleta ≤ as_of` |
| `inicio` | data ISO do primeiro dia coberto | `inicio ≤ início do exercício − 7 dias` |
| `fim` | data ISO do último dia coberto | `fim ≥ fim do exercício + 7 dias` |
| `pregoes` | lista de datas ISO dos pregões no intervalo | não vazia, com pregão até o início e depois do fim do exercício, e algum dentro dele |

O mesmo consumidor exige a relação da B3 (`dados["proventos_b3"]`, já produzida pela cascata
para o Bazin) com proveniência e coleta até o `as_of`, e passa os pregões a
`proventos_b3.serie_12_meses(..., pregoes=...)`, que acha a data ex de cada provento (o pregão
seguinte à data com) e soma o bruto da janela do exercício. Nada disso muda no F3-P14b.

## 2. Fonte oficial: o COTAHIST guardado

O calendário de pregões da B3 sai do próprio COTAHIST (B3, série histórica de cotações),
já guardado no banco único pelo F3-4a (`precos`, com fonte, coleta e hash por linha, e
`cargas_cotahist`, com o arquivo, o hash e a data de geração do trailer):

- **Pregão** = data com pelo menos um negócio no mercado à vista (`tipo_mercado = 010`) nos
  arquivos carregados. É a mesma definição de pregão da liquidez (2B) e do `cotacoes_ate`.
- **Cobertura:** o ano Y está coberto quando há uma carga do arquivo anual `COTAHIST_A{Y}` com
  data de geração depois de 31/12/Y (o arquivo foi gerado com o ano encerrado). O ano corrente
  (arquivo anual parcial, regenerado a cada pregão) só cobre até a data de geração da carga
  usada; como o último exercício precisa de 7 dias depois de 31/12, ele só fica coberto em
  janeiro do ano seguinte, com o arquivo do ano novo. Sem essa prova, o calendário não é montado e o motivo diz qual ano falta. Não se
  infere pregão por dia da semana nem se completa lacuna.
  **Decisão 44 do Marcos (16/11/2026, BUG-3-41):** a cobertura vai até o último pregão do mês,
  pelo próprio COTAHIST armazenado, não até o último dia do calendário. O arquivo anual gerado no
  último pregão de dezembro guardado (30/12, por exemplo; 31/12 não tem pregão) cobre o ano
  inteiro. Pela leitura delegada DD-81 (`docs/loop/pendencias.md`), vale também para qualquer
  trecho que termina no último dia de um mês. Limite: se só
  há a carga que parou antes do último pregão real e nenhuma outra carga guarda pregão depois
  dela no mês, o banco não distingue os dois casos.
- **Cinco exercícios com as bordas:** do início do primeiro exercício menos 7 dias até o fim
  do último mais 7 dias (a exigência atual do consumidor), ou seja, seis anos civis de
  COTAHIST para cinco exercícios encerrados em 31/12. O L1 mostrou o COTAHIST anual de 2010 a
  2026 (`docs/decisoes/l1-fontes-historicas.md` §1); a carga longa é a do F3-7b.
- **Proveniência do calendário:** `fonte` = os arquivos e hashes das cargas usadas; `coleta`
  = a maior coleta entre elas; `inicio` e `fim` = o intervalo provado.

## 3. Bordas data com e data ex

A relação da B3 traz a data com (`lastDatePriorEx`); a data ex é o pregão seguinte
(`proventos_b3`, comentário do módulo). Um provento com data com no fim de dezembro tem data
ex no primeiro pregão de janeiro, e por isso o calendário vai 7 dias além do fim do exercício
(e começa 7 dias antes do início, para o provento cuja data com cai no último pregão do ano
anterior). Os 7 dias são os do consumidor e os de `proventos_b3.FOLGA_SEM_PREGAO`, que o produtor reutiliza; cobrem o recesso de fim de ano: no L1, todos os 16 meses em que o último
pregão da B3 difere do último dia útil são dezembros (§3 do L1).

## 4. Identidade e coleta elegíveis

- **Identidade do emissor:** a da decisão 33 (`proventos_b3.conferir_emissor`): falha é
  abstenção com o motivo, como no Bazin.
- **Companhia deslistada:** a B3 não devolve a relação (L1 §4); a lente se abstém com o motivo
  da DD-35. O calendário existir não muda isso.
- **Coleta até o `as_of`:** o consumidor recusa calendário e relação coletados depois do
  `as_of`. Com `as_of` = hoje, a carga do COTAHIST e a coleta da relação são anteriores e
  passam. **Limite para o F3-3d:** com `as_of` passado, os pregões anteriores a D são fato
  público em D, mas a carga (e a coleta da relação) é posterior; o consumidor atual abstém.
  Tratar dado reconstruído depois de D no modo estrito é decisão do F3-3d (pergunta 1 da
  auditoria da 3-a e DD-34), não deste contrato; até lá, histórico abstém com motivo.

## 5. Ano sem distribuição contra fonte ausente

O descritor conta exercícios com provento bruto positivo. Um exercício só vale **zero** quando
tudo abaixo está provado; senão, o exercício fica sem valor, com o motivo, e o quadro mostra a
cobertura N/5 sem penalidade:

1. o calendário cobre o exercício com as bordas (seção 2);
2. a relação da B3 está completa (`total`, que a cascata já grava em `dados["proventos_b3"]`, `market_engine.py:937`, igual ao número de registros lidos) e a identidade
   do emissor foi conferida;
3. a espécie do ticker tem registro na relação (`MOTIVO_ESPECIE_SEM_REGISTRO` em
   `proventos_b3`), regra já aprovada para o Bazin ("série completa sem provento conta como
   DY zero, exigindo registro da espécie").

Ausência de resposta, falha de coleta, calendário sem cobertura, identidade não conferida ou
companhia deslistada nunca viram zero: cada uma tem o seu motivo. Nenhum ano zero é presumido.

## 6. Para o F3-P14b

- **Produtor:** uma função em `sentinela/data/proventos_b3.py` que lê do banco único os
  pregões e as cargas do COTAHIST e devolve o mapeamento da seção 1 para o intervalo pedido, ou
  o motivo (ano sem carga anual encerrada, ano corrente além da data de geração, banco sem
  preços). Pura no cálculo; a leitura do banco fica numa função separada, como no
  `b3_cotahist.cotacoes_ate`.
- **Ligação:** `market_engine.py` grava `dados["calendario_proventos_b3"]` quando houver série
  CVM de cinco exercícios e a relação da B3, com o intervalo dos exercícios mais as bordas, a
  partir do banco único; sem banco ou sem cobertura, a chave fica ausente e o motivo do
  consumidor aparece, como hoje.
- **Testes:** vermelho antes; produtor real → `qualidade_inputs` → motor com o COTAHIST no
  leiaute oficial; ano sem distribuição demonstrado (zero) contra ano sem cobertura (motivo);
  calendário sem a borda de 7 dias; ano corrente além da geração; nenhuma chave sintética no
  teste integrado.
- **Golden:** a grade atual não tem o calendário; se o golden mudar porque o calendário passou
  a existir, é `[!]` (d), sem regenerar (como diz o item).
- **Regra econômica nova:** nenhuma. O contrato usa as regras aprovadas (qualidade 1.0 §2 e §7,
  Bazin 2.0.0 para a data ex e o zero com registro da espécie, decisão 33 e DD-35). O F3-P14b
  não fica `[!]` (a).
