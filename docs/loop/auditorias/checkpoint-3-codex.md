# Auditoria do checkpoint da Fase 3 — Codex

Modo FASE, restrito aos 21 commits com `Executor: claude-code` em `9b0e74c..766d01a`, no branch `v2/fase-3`. A comparação com a sonda anterior usa apenas os resultados exportados como referência de contagem. **Veredito: não pode seguir como histórico estrito validado.**

## Achados

### C3-01 — A espécie da MGLU3 é corrigida antes da entrega da DFP

- **Commit** `b0a2c5c`.
- **Arquivo e linha** `sentinela/data/referencia/universo.py:375`, `sentinela/data/referencia/correcoes.csv:4`, `sentinela/data/referencia/montagem.py:269` e `tests/regressao/test_bug_3_55_correcoes_no_indice_historico.py:64`.
- **Problema** — A DD-89 foi ratificada, mas seu critério de data conflita com o corte de publicação da ficha do backtest §2. A linha usa a referência de 31/12/2025 como início de vigência. O índice do ZIP oficial local da DFP 2025 registra entrega da versão 1 em **12/03/2026**.
- **Cenário de falha** — Em 02/03/2026 a montagem já troca PN por ON com a evidência dessa DFP. A regressão exige ON justamente nessa data. A antecipação altera a identidade de espécie entregue à análise histórica e pode mudar a seleção de proventos e a lente.
- **Severidade** — **Bloqueante**, por vazamento de futuro.
- **Correção sugerida** — Rever a DD-89 com o Marcos. Vincular cada correção à entrega ou publicação comprovada de sua evidência e exigir que seja anterior a D. Cobrir 11, 12 e 13/03/2026, inclusive o dia da entrega.

### C3-02 — Coleta de novembro torna retornos de horizontes passados indisponíveis

- **Commits** `0ec4cf7` e `4e82941`.
- **Arquivo e linha** `sentinela/data/providers/b3_proventos.py:553`, `sentinela/data/providers/b3_proventos.py:570`, `backtesting/backtest_pit.py:559` e `docs/loop/historico/fase-3/diario.md:1999`.
- **Problema** — A recoleta tornou observável o efeito do A-1 já registrado. A validação da identidade da coleta mais recente roda antes do corte dos proventos. Uma divergência entre relação e complemento em novembro de 2026 decide se é possível medir um horizonte já encerrado.
- **Cenário de falha** — CURY3 em 30/06/2023, horizonte de 12 meses, tinha retorno na sonda anterior e passou a abster por dividendo de 13/11/2026 ausente da relação. Foram 115 observações de 12 meses afetadas por identidade, 85 de 24 meses e 65 de 36 meses. Os registros anteriores podem continuar gravados, mas a seleção torna seus retornos indisponíveis.
- **Severidade** — **Bloqueante**, por dado futuro determinar a disponibilidade do retorno reportado.
- **Correção sugerida** — Resolver o F4-H08 com decisão explícita sobre seleção e validação de versões. Testar que, mantendo as evidências até T, anexar uma coleta posterior com divergência referente a evento posterior a T preserva o retorno daquele horizonte, ou que a saída recebe rótulo compatível com o uso de evidência posterior.

### C3-03 — Fator histórico aceita um evento pela espécie, sem provar o vínculo ao papel

- **Commits** `4bb3270` e `7fd3cc2`.
- **Arquivo e linha** `sentinela/data/providers/b3_proventos.py:672`, `sentinela/data/fatores_acoes_b3.py:85`, `sentinela/data/fatores_acoes_b3.py:102` e `sentinela/data/fatores_acoes_b3.py:178`.
- **Problema** — A nova autorização para consumir a relação coletada depois de D permite que Graham e Lynch obtenham fator de um conjunto de eventos selecionado apenas pela raiz. O consumidor confere se o ISIN recebido é igual ao emitido e se sua espécie serve à lente. Falta provar que esse ISIN corresponde ao papel analisado, ou a um componente da sua unit, no período da reconciliação. A razão residual confere escala, mas não prova identidade.
- **Cenário de falha** — A raiz é reutilizada por outro emissor. Um evento ON 1:2 desse outro emissor, com aprovação e data com dentro dos cortes e ISIN recebido igual ao emitido, é aceito para reconciliar uma série ON cuja quantidade subiu de 100 para 200 por outra causa. O residual é 1. O LPA anterior é dividido por 2 e pode alimentar Graham e Lynch com ajuste indevido. Cenário verificado por leitura da cadeia de condições, sem ocorrência identificada na sonda.
- **Severidade** — **Bloqueante**, por resultado errado.
- **Correção sugerida** — Exigir vínculo documental do evento ao emissor e ao ISIN histórico do papel ou componente, com abstenção se o vínculo não puder ser estabelecido. Cobrir a reciclagem de raiz com dois emissores e eventos de mesma espécie em teste passando pelo produtor.

### C3-04 — Uma linha inválida do índice da DFP cancela a abstenção do exercício entregue

- **Commits** `ee90214` e `508c5ae`.
- **Arquivo e linha** `cvm_provider.py:736` e `tests/regressao/test_bug_3_50_periodo_cvm_vigente_sem_numeros.py:761`.
- **Problema** — O novo `any` converte o código CVM dentro de uma guarda para a iteração inteira. Uma linha inválida de outra companhia pode interromper a busca antes da entrega válida da companhia analisada. O erro é absorvido e o caminho segue com retorno parcial.
- **Cenário de falha** — A DRE do exercício final está ausente e o índice contém primeiro um código CVM vazio, seguido da entrega relevante. Com dois exercícios solicitados, a série pode retornar apenas o anterior quando deveria sinalizar a indisponibilidade do exercício final. O xfail adicionado no próprio commit demonstra a mesma falha com um exercício solicitado: esperava a abstenção explícita e recebe resultado vazio. A limitação já está declarada no GA2b pela decisão 50.
- **Severidade** — **Bloqueante**, por resultado errado no caminho que recua silenciosamente.
- **Correção sugerida** — Resolver no F4-H01. Validar cada linha antes de testar a entrega e distinguir índice sem prova de índice que comprova entrega sem números. Manter a regressão do código vazio antes da entrega válida.

### C3-05 — A comparação da sonda atribui ao horizonte de 12 meses perdas de três horizontes

- **Commits** `4e82941`, `63f3068` e `e645fd9`.
- **Arquivo e linha** `docs/loop/historico/fase-3/diario.md:1999`, `docs/loop/fila-fase4-proposta.md:27` e `docs/loop/historico/fase-3/pr-fase-3.md:233`.
- **Problema** — Os 620 retornos perdidos, os 250 ganhos e os 265 perdidos por identidade somam observações de 12, 24 e 36 meses. O resumo e o F4-H08 atribuem os 265 a 12 meses.
- **Cenário de falha** — Ao dimensionar o F4-H08 pela métrica publicada de 12 meses, o leitor toma 265 como perdas por identidade. O cruzamento dos JSONs dá 115 nesse horizonte, em 23 pares distintos de ticker e data, replicados pelas cinco lentes de ações e units. Dessas 115 observações, 12 tinham lente com valor na sonda final.
- **Severidade** — **Bloqueante**, por resultado quantitativo errado no relatório do checkpoint.
- **Correção sugerida** — Publicar perdas, ganhos e motivos por horizonte, com o total dos três rotulado. Identificar a unidade como observação de lente e informar quantas ainda tinham valor na lente.

### C3-06 — A taxa reportada de cobertura exclui ativos que falham antes das lentes

- **Commits** `10e89ea`, `4e82941` e `e645fd9`.
- **Arquivo e linha** `backtesting/backtest_pit.py:407`, `backtesting/backtest_pit.py:475`, `outputs/f3-3d-sonda/cobertura.py:6` e `docs/loop/historico/fase-3/pr-fase-3.md:28`.
- **Problema** — O backtest conserva a análise sem lente em `sem_lentes`, mas o cálculo publicado como universo da lente conta apenas as linhas em `observacoes`. A ficha §7 pede a fração do universo elegível com valor. O F4-H07 já registra a lacuna.
- **Cenário de falha** — Em 2018, a tabela apresenta 40 FIIs. A mesma exportação lista três FIIs elegíveis sem análise com lente nessa data. Para a cobertura dos FIIs elegíveis, o denominador é 43. Como o numerador é zero, a fração nessa amostra continua zero, mas a contagem publicada do universo está errada. Com numerador positivo, a fração também seria superestimada.
- **Severidade** — **Bloqueante**, por contagem errada no indicador de aceite.
- **Correção sugerida** — Medir cobertura pelo universo elegível aplicável a cada lente, usando o estado anterior às lentes e o horizonte completo. Conservar os motivos separados e recalcular a tabela a partir da saída corrigida.

### C3-07 — O teste do FII falha antes de provar a ligação que o título anuncia

- **Commit** `1fb7b8a`.
- **Arquivo e linha** `tests/test_servico_historico.py:362`, `tests/test_servico_historico.py:374`, `tests/test_servico_historico.py:381` e `market_engine.py:566`.
- **Problema** — O xfail declarado carrega só o Informe. Sem COTAHIST, a cascata retorna antes de buscar o Informe para a lente. A asserção aceita qualquer falha por ausência de lente ou abstenção e a docstring atribui o resultado exclusivamente à falta de dados. O teste da ação passa pela cadeia real, mas seu critério de finitude e positividade mede operacionalidade e não valida o número da lente.
- **Cenário de falha** — Remover a ligação do produtor de rendimento ao consumidor do FII preservaria a falha esperada. O mesmo xfail ocorreria ainda que toda a ligação estivesse correta.
- **Severidade** — **Fase 4**.
- **Correção sugerida** — No F4-H03, carregar dados públicos completos para uma data, verificar as etapas intermediárias no teste e conferir o valor esperado com cálculo independente. Se a primeira barreira faltar durante a preparação, exigir o motivo exato em um teste específico dessa barreira.

## Conferências e limites

- Cruzei os dois JSONs de observações pela chave ticker, lente, D e horizonte. A sonda final contém **15.292** observações, **5.976** delas a 12 meses. Nas chaves em comum, perdas e ganhos foram **235/100** em 12 meses, **205/75** em 24 meses e **180/75** em 36 meses. A soma reproduz **620/250**. Para identidade, a soma é **115 + 85 + 65 = 265**.
- Conferi o `DT_RECEB` da MGLU3 no índice da DFP local. O golden e os dois arquivos de testes protegidos comparados estão idênticos entre a base e o HEAD. `git diff --check` passou.
- A inspeção dos testes foi estática. Não reexecutei pytest, mutação, recoleta, restauração de backup ou a sonda. Os exemplos sintéticos de falha são deduções do código. Não medi a incidência do C3-03 na produção.
