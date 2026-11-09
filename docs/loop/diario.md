# Diário complementar — fechamento da 2C (09/11/2026)

O histórico anterior permanece em `historico/fase-2c/diario.md`. Esta fila complementar é autorizada pelo Marcos após auditorias Gemini/Claude; não reativa propostas antigas nem a Fase 3.

### Ativação do fechamento
- **Executor:** codex (GPT-6).
- **Status:** sucesso documental.
- **Estado:** v2/fase-2c @ e678390, árvore limpa antes desta ativação. Passagem antiga superada pelo git. Ambiente venv confirmado; arquivos obrigatórios do protocolo presentes.
- **Decisões:** comparabilidade por contiguidade + mesmo CNPJ + modelo demonstrado no BPP + reserva D20 validada, com prova/perímetro e aviso fixo de reorganização não detectada; banco com lente sem aviso de alavancagem; F2C-38 e F2C-45(i)/(ii) mantidos e destinados à Fase3; oito regras F2C-47 ratificadas. Fonte: mensagem expressa do Marcos09/11/2026; não alegar leitura de parecer completo ausente.
- **Aceite:** fila com um fix por bug e sequência D27 estrita; integrações do produtor real; documentação/limpeza separadas; parada no Checkpoint. Não há autorização de push.
- **Testes baseline:** 3507 passed, 1 skipped, 8 xfailed, warning antigo. Sem código alterado nesta ativação.

### FC2C-61 — fix: produce comparable CVM accumulated statements
- **Executor:** codex (GPT-6).
- **Status:** sucesso.
- **D27 antes:** BUG-2C-61 registrado estrito; 1 xfailed/2 controles PASS; `--runxfail` falhou em None !=70 no lucro dos controladores (/tmp/2c61-red.txt), ANTES de editar produção.
- **O que foi feito:** produtor dos acumulados valida CNPJ comum DRE/BPP, modelo exclusivo demonstrado no BPP, D20 do lucro/PL e identidade do documento; emite perímetro por campo, critério/documento e aviso fixo de reorganização não detectada. Consumidor mantém contiguidade e recusa perímetros distintos. Contrato atualizado pela decisão09/11, sem prometer PIT.
- **Integração:** arquivos ZIP CVM sintéticos → acumulados_ttm real → ttm real, sem injetar prova: lucro70/receita140. BPP ausente, modelo incompatível e troca de CNPJ entre documentos abstêm. Marca retirada após correção.
- **Testes:** 3507→3511 passed, 1 skipped/8 xfailed, warning antigo; Ruff CI e data/methods verdes, diffcheck verde. Golden não regenerado; sem alteração de método anual ou taxas.
- **Resíduos/decisões:** nenhum novo; reorganização fica Fase3. Revisão somente leitura do stage antes do commit.

### FC2C-62 — fix: produce comparable annual quality inputs
- **Executor:** codex (GPT-6).
- **Status:** sucesso.
- **D27 antes:** BUG-2C-62 registrado estrito, 1 xfailed; `--runxfail` falhou em comparavel=False em vez de True (/tmp/2c62-red.txt) ANTES da alteração do produtor.
- **O que foi feito:** indicadores_da_serie aplica a prova documental DRE/BPP/D20 do produtor após identificar a janela, grava perímetro/evidência/aviso; transporte conserva aviso e qualidade o inclui em avisos, sem certificar ausência de reorganização. Ficha qualidade1.0 atualizada pela decisão09/11; contiguidade, fonte e PL inicial permanecem obrigatórios.
- **Integração:** cinco ZIPs DFP com comparativos BPP e índice de entregas → CVMProvider real → MarketEngine._serie_cvm real → ValuationEngine real: comparavel=True, 5 observações de ROE, média0,1 (10,12,-2,15,15 sobre PL inicial100). Nenhuma chave de prova montada no teste. Lacuna2023 mantém quatro observações e média indisponível.
- **Universo inicial novamente medido:** 51 ações/units públicas do snapshot inicial `f2c1-universo21.pkl`, SHA256 `2f9c5cc99d103af5b54ffc9b6003eb8f7939bed8807d7e20dee98ffec506c050`, as_of2026-10-28T23:34:41.882351+00:00. Produtor/Market/motor relidos ANTES e DEPOIS, mesmos ZIPs2021–2025 com hashes idênticos aos registrados em f2c2-universo-pl.json; sem rede, sem nova coleta/preço. Comparáveis0→45; médiasROE0→44; anos B3 com cobertura0→0. Comparabilidade não é completude de todos os indicadores nem qualidade econômica. Logs/JSON comparativos em /tmp/2c62-{antes,depois}.txt e /tmp/2c62-universo-{antes,depois}.json, script /tmp/2c62-universo.py. Não extrapolar para toda B3 nem alegar replay PIT.
- **Testes:** 3511→3513 passed, 1 skipped/8 xfailed, warning antigo; Ruff CI e data/methods verdes; diffcheck verde. Golden não regenerado; só quadro/prova informativa, nenhum valor individual de método recalibrado.
- **Resíduos/decisões:** nenhuma prova manual, nenhum resíduo versionado; reorganizações e calendário anual continuam Fase3. Revisão somente leitura do stage antes do commit.

### FC2C-63 — fix: preserve collected leverage abstention reasons
- **Executor:** codex (GPT-6).
- **Status:** sucesso.
- **D27 antes:** BUG-2C-63 estrito, 1xfail; --runxfail mostrou causa contábil longa versus aviso genérico “ausente” (/tmp/2c63-red.txt), antes de editar motor.
- **O que foi feito:** motor lê também alavancagem_cvm.motivos, preservando a entrada legada válida e o aviso genérico para motivo inválido/ausente. Sem cálculo, risco ou valor de lente alterado.
- **Integração:** ZIPs → CVMProvider real → _buscar_cvm real → ValuationEngine real, sem montar alavancagem_cvm no teste; motivo produzido reaparece no aviso. Regressões legadas de motivo/inteiro numérico continuam PASS.
- **Testes:** 3513→3514 passed, 1 skipped/8 xfailed, warning antigo; Ruff CI/data/methods e diffcheck verdes. Sem regeneração golden ou resíduo.
- **Decisões pendentes:** nenhuma neste item; omissão em banco é FC2C-64 separado. Revisão somente leitura antes do commit.
