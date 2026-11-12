# Identidade da preferencial sem sigla no FCA (F3-P07, F2C-54)

Levantamento de 12/11/2026, feito só com leitura do banco único (`sentinela_store.db`) depois do backfill da Fase 3 (F3-7b e F3-3b-fix). Ele usa a DFP, o FCA e o COTAHIST oficiais de 2010 a 2026 já carregados, e nenhuma consulta nova à rede. O levantamento não muda nenhuma regra, e qualquer correção fica só como proposta para o checkpoint da 3-b.

## 1. A pergunta

O caso do F2C-54 é este:
- a DRE divulga o LPA de uma classe com sigla, como `PNA`;
- o FCA lista o código de negociação como "Ações Preferenciais", sem `Sigla_Classe_Acao_Preferencial`;
- `acoes_cvm._lpa_da_classe` procura a classe do FCA (nenhuma) e depois a espécie (`PN`). Sem linha `PN` na DRE, cai no recalculado ou se abstém, e nunca liga a `PNA` da DRE ao código.

Pela regra 7.9 da ficha por ação 1.1, a linha genérica `PN` vale para classes conhecidas, mas não no sentido inverso. Sem prova de identidade, o resultado é abstenção.

## 2. O que os dados mostram

Para cada referência, o levantamento cruzou:
- as linhas `Ações Preferenciais` em bolsa, com código e sem fim de negociação, do FCA da referência seguinte;
- as classes das linhas 3.99.01.xx da DRE (consolidada; sem ela, a individual) da DFP;
- a especificação e o ISIN do COTAHIST no último pregão de novembro do ano seguinte.

| Referência da DFP | FCA com sigla | Sem sigla, DRE com `PN` | Sem LPA preferencial na DRE | Sem sigla, DRE só com classe com sigla |
|---|---:|---:|---:|---:|
| 2017 | — | — | 9 | 2 (PTCA11, CGAS5) |
| 2019 | 72 | 58 | 11 | 1 (CGAS5) |
| 2021 a 2024 | — | — | 12 a 13 | 2 por ano (EKTR4, CGAS5) |
| 2025 | 54 | 46 | 14 | 1 (EKTR4) |

Nas linhas marcadas com "—", só os casos fora das duas primeiras colunas foram listados.

O caso do F2C-54 aparece em poucos códigos, e eles se resolvem de dois jeitos diferentes:

- **CGAS5 (Comgás, 61.856.571/0001-17).**
  - O FCA não traz sigla.
  - A DRE tem `ON` e `PNA`.
  - No COTAHIST, de 2010 a 2026, a especificação é sempre `PNA` (com os sufixos de evento) e o ISIN é sempre `BRCGASACNPA3`. As letras `PA` do ISIN identificam a preferencial classe A.
  - A identidade está provada por fonte oficial da B3, datada, pelo código de negociação.
- **EKTR4 (Elektro, 02.328.280/0001-97).**
  - O FCA não traz sigla.
  - A DRE tem `ON`, `PNA` e `PNB`.
  - No COTAHIST, a especificação é `PN` e o ISIN é `BREKTRACNPR7`, de preferencial sem classe.
  - Não há ligação com nenhuma das duas classes da DRE, e a abstenção continua.
- **PTCA11 (2017)** é unit e fica fora do caso.

## 3. Proposta para o checkpoint da 3-b (sem implementação)

Um item `fix:` poderia usar a especificação do COTAHIST (`precos.especificacao`, primeira palavra) e as letras 10 e 11 do ISIN do mesmo código de negociação, em pregão anterior a D, como prova da classe da preferencial sem sigla no FCA. A prova só vale se as condições abaixo forem atendidas:

1. a especificação e o ISIN apontam a mesma classe (`PNA` com `PA`, `PNB` com `PB`, e assim por diante);
2. a classe existe na DRE do documento;
3. nenhum outro código da companhia no FCA aponta a mesma classe.

Fora disso, a abstenção continua. O ticker nunca serve de prova. Hoje, a proposta resolveria um código (CGAS5): no FCA de 2026, a Comgás lista só CGAS3 (ordinária) e CGAS5 (preferencial sem sigla), então a condição 3 vale.

## 4. Achado fora do escopo, que afeta o universo da Fase 3

**O FCA aberto da CVM não tem código de negociação antes da referência de 2018.**
- Contando as linhas de `valor_mobiliario` com `Codigo_Negociacao` preenchido nos ZIPs oficiais:
  - 2011: 0 de 530;
  - 2017: 0 de 628;
  - 2018: 477 de 751.
- Até 2017, as linhas também não separam ON de PN: "Ações Preferenciais" só aparece a partir de 2018.
- As entregas da referência de 2018 vão de 30/11/2017 a 2021, quase todas entre janeiro e junho de 2018.
- O L1 (`docs/decisoes/l1-fontes-historicas.md`, §1 e §5, item 2) concluiu que o FCA "traz o código de negociação". Ele registrou a coluna no leiaute, sem medir o preenchimento por ano (a amostra baixada era o FCA de 2015, do caso da ALL), e essa conclusão não vale para os anos anteriores a 2018.

Efeito medido no universo em D (`universo.universo_em`, com o cadastro atual):

| D | Ações identificadas | Units | FII | Códigos `sem_identificacao` |
|---|---:|---:|---:|---:|
| 30/06/2016 | 0 | 0 | 0 | 415 |
| 29/12/2017 | 0 | 0 | 131 | 426 |
| 28/09/2018 | 293 | 5 | 151 | 163 |
| 28/06/2019 | 239 | 2 | 168 | 224 |
| 30/06/2022 | 360 | 6 | 365 | 188 |

O universo ponto-no-tempo, como desenhado no F3-5 (DD-50, o índice D32 montado com o FCA entregue antes de D), não tem nenhuma ação antes do primeiro semestre de 2018. A decisão 4 previa a primeira análise completa de ação em 2016, e o universo com deslistadas é o item 2 da confirmação após o L1. Os dois não se cumprem para ações entre 2016 e meados de 2018.

A queda de 2018 para 2019 (293 para 239 ações) e os 163 a 224 códigos sem identificação depois de 2018 vêm do `sem_prova` do FCA (DD-34 e DD-53, `docs/decisoes/backfill-fase3.md` §4) e dos códigos que o FCA vigente omite.

Caminhos possíveis, todos para decisão do Marcos:
- **(a)** começar o backtest de ações depois da primeira entrega do FCA de 2018, por companhia;
- **(b)** identificar o código antes de 2018 pela raiz do emissor no ISIN do COTAHIST (`BRPETRACNPR6` → `PETR`), ligada ao CNPJ pelo primeiro FCA com código e pelo cadastro (registro ativo em D). Esse caminho é exploratório: há o risco de raiz reaproveitada e ele não tem prova documental em D;
- **(c)** buscar outra fonte oficial datada que ligue o código ao CNPJ antes de 2018, como os formulários de referência (FRE), que ainda não foram medidos.

Este achado é uma condição de parada do `/goal`, passo 7: "o L1 mostrar que alguma decisão de dados (2011, universo, ...) não é cumprível".
