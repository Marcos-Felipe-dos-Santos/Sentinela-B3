# Banda neutra — proposta fora da amostra (F3-8d)

**Situação em 16/11/2026 (F3-8j, seção 6): sem número, e a amostra declarada não pode formar quintis.** Situação em 15/11/2026: sem número. Nenhuma lente teve valor em nenhuma data da sonda; nenhuma formou quintis; a banda não pode ser calibrada. Este documento registra a regra que será aplicada, a execução real, a cobertura por lente e por ano e o que falta. É **proposta** para o Marcos, sem efeito em código, ficha ou apresentação. Não é recomendação nem sugestão de carteira.

Script: `scripts/banda_neutra_fase3.py` (decisão 29). Testes: `tests/test_banda_neutra_fase3.py`, com contas à mão. Saídas da execução, fora do git: `outputs/f3-8d/sonda/` (`observacoes.json`, `proposta.json`, `resultados.db`).

## 1. Regra (ficha do backtest §9, decisão 17, DD-70)

- Por lente e por horizonte (12, 24 e 36 meses, cada um separado), só no modo estrito. Nunca como rótulo agregado.
- **Fronteira:** entre as datas D em que a lente formou quintis naquele horizonte (25 ou mais ativos com distância válida), a de posição `ceil(n/2)`, inclusiva. Cada horizonte tem a sua: pelo §8, o de 36 meses perde as datas finais e a fronteira dele cai antes (leitura de “cada um separadamente”, DD-70).
- Só entram na calibração e na validação as observações das datas com quintis; uma data com menos de 25 ativos válidos fica fora das duas metades.
- **Calibração:** observações com D até a fronteira **e** fim do horizonte até a fronteira. As que têm D na primeira metade e fim depois dela saem, e o número delas fica registrado por horizonte (`excluidas_pela_fronteira`). O script falha com erro se uma observação de calibração terminar depois da fronteira (`conferir_calibracao`).
- **Validação:** observações com D depois da fronteira.
- **Banda (DD-70):** simétrica em torno de zero; largura `b` = mediana de |distância ao preço| na calibração. A largura vem da dispersão das lentes, não do retorno (decisões da 2C §2; ficha §9: “o backtest descreve, não calibra”).
- **Estados:** “sinal positivo” (d > b), “neutro” (|d| ≤ b), “sinal negativo” (d < −b). Para cada estado, nas duas metades: contagem, retorno total médio e excesso médio sobre o CDI, sempre com o número de observações. Os retornos só descrevem os estados; nenhum parâmetro é escolhido por eles.
- Lente sem datas com quintis: abstenção, com o motivo “lente sem data com quintis formados” e a contagem das abstenções.

## 2. Execução real (DD-69)

- O banco real foi aberto só para leitura (`ATTACH ... mode=ro`). O código do backtest lê só as tabelas públicas (preços, proventos, índices, CVM PIT), nunca as da carteira. Os resultados das análises foram gravados num banco novo em `outputs/f3-8d/sonda/`.
- **Custo medido:** um ativo numa data levou 1420 s com o cache frio (1365 s na remontagem dos ZIPs da CVM, `remontagem.zip_cia_em`). Cinco ativos em 30/06/2023 levaram 4147 s com o cache quente, cerca de 14 min por ativo e data. A sonda abaixo (24 ativo-datas) levou cerca de 5,5 h.
- O universo completo teria 106 datas de fim de mês com mês fechado (31/01/2018 a 30/10/2026), com cerca de 315 elegíveis por data (30/06/2023: 167 STOCK, 142 FII, 6 UNIT). São milhares de horas, então a execução completa ficou para o F3-8j, depois do reaproveitamento da remontagem (F3-8e).
- **Sonda declarada:** último pregão de junho de 2018 a 2025 (8 datas), com o primeiro elegível de cada classe na ordem do universo (sem olhar retorno nem lente). Resultado: 231 observações (lente × ativo × horizonte); sem análise falha (`sem_analise` vazio); horizontes incompletos pelo §8: 11 em 24 meses e 22 em 36 meses.

## 3. Resultado por lente

Nas três janelas, nenhuma lente tem observação com valor e nenhuma forma quintis. As exclusões pela fronteira ficam **sem aplicação** (0 nos três horizontes), porque não há fronteira sem datas com quintis.

| Lente | Observações (12 / 24 / 36) | Com valor | Datas com quintis | Motivos (horizonte de 12 meses) |
|---|---|---|---|---|
| Graham | 16 / 14 / 12 | 0 | 0 | 10 sem Composição do Capital no documento do lucro (exercícios 2013 a 2019, primeiro ano da janela); 3 modelo banco fora do escopo; 2 modelo não demonstrado no BPP consolidado; 1 IPCA do SIDRA desligado na data passada (§11) |
| Lynch | 16 / 14 / 12 | 0 | 0 | os mesmos 10 da Composição do Capital, 3 e 2 de escopo; 1 perfil não demonstrado: DY ausente (§11) |
| Gordon | 16 / 14 / 12 | 0 | 0 | 6 base de ações incompatível ou sem evidência; 5 inflação incompatível com a janela da DFP (§11); 3 modelo banco fora do escopo; 2 modelo não demonstrado no BPP |
| Bancos | 16 / 14 / 12 | 0 | 0 | 11 modelo empresa fora do escopo; 2 base de ações sem evidência; 2 modelo não demonstrado no BPP; 1 DVA sem atribuição aos controladores |
| Bazin | 16 / 14 / 12 | 0 | 0 | 10 identidade do emissor não comprovada na coleta (6 UNT e 1 ON sem ISIN da companhia no GetDetail, 3 complemento sem proventos); 3 modelo banco; 2 modelo não demonstrado no BPP; 1 bloco pelo preço do COTAHIST não montado (§11) |
| Rendimento do FII | 8 / 7 / 6 | 0 | 0 | 8 DY ausente ou inválido (§11) |

**Retorno total (12 meses, todas as lentes):** 5 observações com retorno (ABEV3 em 30/06/2022) e 83 sem: identidade do emissor não comprovada (35 UNT e 20 ON sem ISIN da companhia no GetDetail; 20 complemento sem proventos para conferir), 8 sem coleta da relação de proventos do emissor. Mesmo uma lente com valor teria quase nenhum retorno para descrever os estados.

## 4. Cobertura por lente e por ano

Cada célula: observações de 12 meses na sonda / com valor. Os anos sem sonda (2026, e todos os outros meses) estão **não medidos**, pelo custo do §2.

| Lente | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|
| Graham | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 |
| Lynch | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 |
| Gordon | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 |
| Bancos | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 |
| Bazin | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 |
| Rendimento do FII | 1 / 0 | 1 / 0 | 1 / 0 | 1 / 0 | 1 / 0 | 1 / 0 | 1 / 0 | 1 / 0 |

Os motivos por ano, lente e horizonte estão em `outputs/f3-8d/sonda/proposta.json`, chave `cobertura`.

## 5. O que falta para haver número

**Lacunas da ficha §11, que não cabem no F3-8d (DD-71, itens novos na fila):**
- F3-8e: reaproveitar a remontagem da CVM do dia entre as análises, que é o custo do §2;
- F3-8f: IPCA de fim de exercício pelo `series_macro`, para Graham, Lynch, Gordon e Bancos;
- F3-8g: DY histórico pelos proventos da B3 e pelo COTAHIST, para o perfil, o Lynch e o FII;
- F3-8h: bloco do Bazin pelo preço do COTAHIST;
- F3-8i: taxa real histórica pelo `series_macro`;
- F3-8j: a banda refeita sobre o universo e as datas completos.

**Lacunas fora do §11, vistas na sonda (DD-72):**
- Graham e Lynch abstêm em toda data até junho de 2024, porque o primeiro exercício da janela de cinco anos (2013 a 2019) não tem Composição do Capital no documento do lucro. Isso vira o levantamento F3-8k, sobre a fonte da quantidade de ações por exercício antes de 2020. A regra do F2A-3 continua: sem as ações do mesmo documento, abstém.
- O retorno abstém na maior parte dos ativos pela conferência de identidade da decisão 33: units e ações ON sem ISIN da companhia no GetDetail, ou complemento sem proventos. Mudar a conferência é regra de identidade decidida pelo Marcos, então fica como pergunta em `docs/loop/pendencias.md`, sem item.
- 2024 e 2025: “modelo da demonstração não demonstrado no BPP consolidado” (AALR3, ABCB4), também para o F3-8k.

## 6. Reexecução do F3-8j (16/11/2026)

- **Amostra declarada antes da execução (DD-82, escrita às 14:16 UTC):** a da DD-69, ratificada pela decisão 4: último pregão de junho de 2018 a 2025 (8 datas) e o primeiro elegível de cada classe na ordem do universo (`--limite-por-classe 1`). Banco real só leitura; saída em `outputs/f3-8j/sonda/`; cerca de 2 h 47 min; 231 observações, `sem_analise` vazio.
- **Lacunas do §11 fechadas desde a sonda do F3-8f-col:** DY e bloco do Bazin pelo banco (F3-8g, F3-8h), calendário da data ex com cobertura (F3-8h-cal, F3-8h-cov) e taxa real do `series_macro` (F3-8i, já ligada). Comparação observação a observação (`outputs/f3-8j/comparacao.txt`): mesmas 231 chaves; nenhum valor ganho, perdido ou alterado; nenhum motivo de retorno mudou; no horizonte de 12 meses mudaram 4 motivos de lente:
  - Rendimento do FII, 3 datas (2022, 2024, 2025): "DY ausente ou inválido" → "tipo de FII fora do escopo na 2B: papel" (o DY do Informe agora chega à lente, F3-8g);
  - Bazin, 30/06/2022: "proventos … o bloco do Bazin pelo COTAHIST" → "DY abaixo do mínimo" (o bloco agora é montado, F3-8h).
- **Valores no horizonte de 12 meses:** Gordon 1 de 16 e Graham 1 de 16; Bancos, Bazin, Lynch e FII, nenhum. Retorno total com valor: 5 de 88 observações de 12 meses, ou seja, 1 de 24 pares ativo-data (ABEV3 em 30/06/2022, nas 5 lentes).
- **Por que não há banda, e não haverá nesta amostra:** a regra (seção 1) só usa datas em que a lente formou quintis, e `formar_quintis` exige 25 ativos com distância válida na mesma data. Com um ativo por classe, isso nunca acontece, em nenhuma lente e em nenhuma data, qualquer que seja a cobertura. Toda lente abstém com "lente sem data com quintis formados". A sonda do F3-8d já tinha esse desenho; o aceite do item se cumpre pela cobertura e pelos motivos, mas a banda só pode ser medida com amostra de 25 ou mais ativos com valor por data e lente.
- **O que trava o valor hoje, na amostra:**
  - Graham e Lynch: "sem Composição do Capital no documento do lucro" até 2024 (F3-8k) e modelo não demonstrado no BPP em 2024–2025;
  - Bazin e o retorno: a identidade do emissor da decisão 33 (15 dos 24 pares ativo-data: espécie UNT ou ON da relação sem ISIN da companhia no GetDetail, ou complemento sem proventos para conferir) e os 8 pares de FII sem coleta da relação;
  - FII: "DY ausente" de 2018 a 2021 pelo BUG-3-42 (o provedor não lê o Informe no leiaute anterior a 2021; F3-8j-fii), em 2023 só 6 linhas do Informe do fundo até D ("menos de 12 meses com DY e valor da cota do mês anterior") e "tipo papel" em 2022, 2024 e 2025; a guarda seguinte é a fonte de eventos de cota (DD-75, F3-8l).
- **Para o checkpoint:** se a falta da Composição do Capital antes de 2020 vale para todo emissor, como a sonda sugere (o motivo cita o exercício e não o ativo; não verificado no universo), nem o universo inteiro de uma data teria 25 valores em Graham ou Lynch antes de 2025. Medir a banda pede, nesta ordem, o F3-8k (ações antes de 2020), a resposta sobre a identidade da decisão 33 e uma amostra declarada com 25 ou mais ativos por data, cujo custo depende do reaproveitamento do F3-8e e ainda não foi medido.

## 7. Universo elegível de ações (F3-8j-uni, 16/11/2026)

- **Execução (DD-84):** as mesmas 8 datas da seção 6, todo o universo elegível de STOCK e UNIT (`--classes STOCK UNIT`, sem `--limite-por-classe`). Banco real só leitura; saída em `outputs/f3-8j-uni/sonda/`; de 14:57 a 19:57 (horário de Brasília), 5 h, abaixo da estimativa de 7 a 10 h registrada antes (o universo das datas antigas é menor: 75 ações em 2018 contra 173 em 2023). 13.055 observações, `sem_analise` vazio.
- **Ações por data:** 75 (2018), 86 (2019), 124 (2020), 115 (2021), 152 (2022), 173 (2023), 146 (2024), 144 (2025).
- **Valores por lente no horizonte de 12 meses** (com valor / com valor e retorno):

| Lente | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|
| Gordon | 0 | 0 | 1 / 1 | 22 / 10 | 44 / 15 | 43 / 19 | 40 / 23 | 39 / 24 |
| Graham | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 39 / 19 |
| Bancos | 0 | 0 | 0 | 0 | 0 | 3 / 0 | 1 / 0 | 3 / 0 |
| Bazin | 0 | 0 | 0 | 0 | 0 | 1 / 1 | 1 / 1 | 1 / 1 |
| Lynch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

  Por lente e ano, com os motivos e os horizontes de 24 e 36 meses: `outputs/f3-8j-uni/sonda/proposta.json` (`cobertura`).
- **Banda, por lente e horizonte:**
  - **Gordon, 12 meses: banda de 65,0%.** Datas com quintis: 2022, 2023, 2024 e 2025 (2021 tem 22 valores, abaixo de 25); fronteira em 30/06/2023; calibração com as 44 observações de 2022 (15 com retorno), 43 excluídas pela fronteira (as de 2023, que terminam em 2024), validação com 79 (2024 e 2025, 47 com retorno). Estados na calibração: 3 sinal positivo, 22 neutro, 19 sinal negativo; na validação: 1, 42 e 36. Os retornos médios por estado estão no `proposta.json` e só descrevem: com 15 retornos na calibração e 1 observação de sinal positivo na validação, não sustentam leitura nenhuma.
  - **Gordon, 24 e 36 meses:** abstém, "nenhuma observação de calibração termina até a fronteira" (3 e 2 datas com quintis; a primeira metade termina depois da fronteira).
  - **Graham, 12 meses:** abstém pelo mesmo motivo; só 2025 forma quintis (39 valores), e uma data sozinha não tem calibração. 24 e 36 meses: "lente sem data com quintis formados".
  - **Lynch, Bazin e Bancos, os três horizontes:** "lente sem data com quintis formados".
- **O que trava cada lente no universo:**
  - Graham e Lynch: "sem Composição do Capital no documento do lucro" em toda janela com exercício anterior a 2020, para todo emissor (89 em 2021, por exemplo), o que confirma no universo o que a seção 6 só supunha; a proposta da fonte está em `acoes-por-exercicio-3.md` §4, para o Marcos. Em 2025, Graham passa; Lynch ainda abstém por "perfil não demonstrado: DY comum ausente ou não confiável" (33), "fator oficial B3 indisponível" (34, a coleta da B3) e "escala das ações indeterminada" (16).
  - Bazin: "complemento da coleta não guardado para conferir o ISIN do ticker no pregão" é o primeiro motivo em todo ano (349 no horizonte de 12 meses), seguido de "sem coleta da relação de proventos do emissor" (136). A recoleta da decisão 43 cobriu só a amostra declarada; o universo não tem a relação da B3 coletada.
  - Retorno total: falta em 623 das 1.015 observações de 12 meses; motivos: "sem coleta da relação de proventos do emissor" (171), "complemento sem proventos para conferir" (130), "espécie PN da relação sem ISIN da companhia no GetDetail" (117) e "espécie UNT" (49). É a mesma coleta da B3 e a identidade da decisão 33.
  - Bancos: cerca de 9 bancos no universo por data ("modelo banco fora do escopo do método" nas outras lentes), e a lente teve valor em no máximo 3. Pela regra da seção 1, que exige 25 valores na data, a lente de bancos não forma quintis com nenhuma cobertura: é limite do número de bancos listados, não de dado.
- **Para o checkpoint (decisões do Marcos, sem efeito até lá):**
  1. A única banda medida (Gordon, 12 meses, 65,0%) vem de uma data de calibração; publicá-la ou esperar mais datas (as mensais em vez das 8 de junho, por exemplo) é decisão de amostra.
  2. Graham e Lynch antes de 2025 dependem da regra das ações antes de 2020 (F3-8k).
  3. Bazin e o retorno do universo pedem a coleta da relação de proventos da B3 para todos os emissores, fora do escopo da decisão 43 (amostra declarada); medir antes o volume, como no F3-8d-col.
  4. A lente de bancos não chega a 25 valores por data; a banda dela pede outra regra (agrupar datas, por exemplo) ou fica sem banda.

## 8. Decisões do Marcos (16/11/2026, noite)

- **Gordon, 12 meses:** os 65,0% não são adotados. Uma data de calibração com 15 observações com retorno é insuficiente. Status: **não calibrada, dados insuficientes**; o backtest segue sem banda em todas as lentes.
- **Bancos:** fora da banda até existirem as regras específicas de bancos. A regra dos 25 valores por data (seção 1) não muda.
- **Pendências de dados**, registradas em `docs/loop/pendencias.md`: as ações antes de 2020 (Graham e Lynch, `acoes-por-exercicio-3.md`) e a coleta completa da relação de proventos da B3 (faltam 623 dos 1.015 retornos de 12 meses no universo).
