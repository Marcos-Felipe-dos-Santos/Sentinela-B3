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

### FC2C-64 — fix: omit inapplicable leverage notices for banks
- **Executor:** codex (GPT-6).
- **Status:** bloqueado no gate; correção local, não commitada e não entregue.
- **D27 antes:** BUG-2C-64 estrito → xfail; --runxfail falhou na presença indevida de aviso_alavancagem, após confirmar valor Bancos26,346908251509 (/tmp/2c64-red.txt), antes de editar produção.
- **O que foi feito localmente:** resultado de banco omite aviso de medida não aplicável; nenhum cálculo/valor de lente alterado. Empresa conserva o aviso e causa coletada conforme integração FC2C-63. Marca retirada após PASS da regressão corrigida.
- **Teste anterior atualizado por decisão:** ramo banco da regressão BUG-2C-21 agora exige ausência do aviso e mantém controle numérico Bancos26,35; ramo empresa e controles legados intactos. Substituição exigida pela decisão explícita F2C-45(iii) de09/11.
- **Gate real:** 3514 passed / 1 failed / 1 skipped / 8 xfailed, warning antigo. Única falha: tests/test_equivalencia_motores.py::test_acoes_iguais_ao_golden,40casos bancários. Ruff CI/data/methods e diffcheck verdes. Não declarar suíte verde nem entrega; nenhum golden/harness/comparador alterado.
- **Predicado mínimo preparado ANTES de qualquer atualização da fixture:** nos2291casos, apenas40 saídas de ações com chave banco, lente Bancos.valor não nulo e aviso_alavancagem presente perderiam SOMENTE essa chave. Entradas/IDs/ordem/valores individuais e demais chaves intactos;2251casos ficam iguais. Conferência independente executou todos os casos com o motor atual e comprovou igualdade exata após essa única remoção, com o comparador existente. Proposta local /tmp/2c64-golden-proposto.patch e predicado/40IDs em /tmp/2c64-predicado.json; fixture protegida inalterada. Script /tmp/2c64-predicado.py.
- **Motivo da parada:** AGENTS.md lista tests/fixtures/golden_motores.jsonl entre os proibidos e manda parar/reportar quando a tarefa exigir mudança; executar-fila proíbe regeneração fora de item [golden]. A autorização atual especifica a mudança do aviso, mas não libera essa fixture. Fila marcada[!], itens65–72 não iniciados.
- **Falta:** autorização específica para adicionar [golden] ao FC2C-64 e aplicar exclusivamente o predicado documentado, sem regenerar harness/grade nem alterar comparação; depois suíte/gates, revisão somente leitura e único commit fix, continuar65–72 atéCheckpoint. Sem push.

### FC2C-64 — desbloqueio autorizado e verificação do predicado (09/11/2026)
- **Executor:** codex (GPT-6).
- **Autorização expressa:** Marcos09/11 libera exclusivamente retirar aviso_alavancagem dos40casos enumerados de modelo banco com lente Bancos; demais2251casos idênticos byte a byte. Predicado preparado anteriormente, aplicado agora sem gerador/harness/comparador.
- **Conferência antes do commit:** fixture antes igual aos bytes de HEAD; depois40linhas alteradas apenas por retirar o campo autorizado, igualdade JSON exata para todo o restante de cada caso;2251linhas conservadas byte a byte, IDs/entradas/ordem intactos. SHA256 antes: `f2efc3245ebf65820e4bdfd937d5262379abb308c6a3bf3e04553dc627f52ec6`; depois: `500645a3263ad25e492bff56e00c9b3552b84a243136d3397f520d4a79c24bcc`.
- **IDs autorizados e alterados (40):**
  - `banco-roe0.05-payout0.25-vpa18.5463`
  - `banco-roe0.05-payout0.25-vpa37.0926`
  - `banco-roe0.05-payout0.5-vpa18.5463`
  - `banco-roe0.05-payout0.5-vpa37.0926`
  - `banco-roe0.05-payout0.75-vpa18.5463`
  - `banco-roe0.05-payout0.75-vpa37.0926`
  - `banco-roe0.05-payout1.0-vpa18.5463`
  - `banco-roe0.05-payout1.0-vpa37.0926`
  - `banco-roe0.1-payout0.25-vpa18.5463`
  - `banco-roe0.1-payout0.25-vpa37.0926`
  - `banco-roe0.1-payout0.5-vpa18.5463`
  - `banco-roe0.1-payout0.5-vpa37.0926`
  - `banco-roe0.1-payout0.75-vpa18.5463`
  - `banco-roe0.1-payout0.75-vpa37.0926`
  - `banco-roe0.1-payout1.0-vpa18.5463`
  - `banco-roe0.1-payout1.0-vpa37.0926`
  - `banco-roe0.15-payout0.25-vpa18.5463`
  - `banco-roe0.15-payout0.25-vpa37.0926`
  - `banco-roe0.15-payout0.5-vpa18.5463`
  - `banco-roe0.15-payout0.5-vpa37.0926`
  - `banco-roe0.15-payout0.75-vpa18.5463`
  - `banco-roe0.15-payout0.75-vpa37.0926`
  - `banco-roe0.15-payout1.0-vpa18.5463`
  - `banco-roe0.15-payout1.0-vpa37.0926`
  - `banco-roe0.2125-payout0.25-vpa18.5463`
  - `banco-roe0.2125-payout0.25-vpa37.0926`
  - `banco-roe0.2125-payout0.5-vpa18.5463`
  - `banco-roe0.2125-payout0.5-vpa37.0926`
  - `banco-roe0.2125-payout0.75-vpa18.5463`
  - `banco-roe0.2125-payout0.75-vpa37.0926`
  - `banco-roe0.2125-payout1.0-vpa18.5463`
  - `banco-roe0.2125-payout1.0-vpa37.0926`
  - `banco-roe0.3-payout0.25-vpa18.5463`
  - `banco-roe0.3-payout0.25-vpa37.0926`
  - `banco-roe0.3-payout0.5-vpa18.5463`
  - `banco-roe0.3-payout0.5-vpa37.0926`
  - `banco-roe0.3-payout0.75-vpa18.5463`
  - `banco-roe0.3-payout0.75-vpa37.0926`
  - `banco-roe0.3-payout1.0-vpa18.5463`
  - `banco-roe0.3-payout1.0-vpa37.0926`
- **Gate após liberação:**3515 passed / 1 skipped / 8 xfailed, warning antigo; Ruff CI/data/methods e diffcheck verdes. Diff da fixture inspecionado:40linhas removidas/40adicionadas, somente a chave autorizada; demais2251linhas byte a byte. Bloqueio resolvido, item concluído após revisão; sem push.

### FC2C-65 — fix: enrich the reference CLI with official fund identities
- **Executor:** codex (GPT-6).
- **Status:** sucesso.
- **D27 antes:** BUG-2C-65 estrito→xfail; --runxfail falhou BTCI11 UNKNOWN != FII na entrada real do módulo (/tmp/2c65-red.txt), antes de editar produção.
- **O que foi feito:** CLI e cascata compartilham montagem a partir das mesmas Fontes, com identidades_fii e corte/falha já existentes. Não duplica coleta, não adivinha classe pelo sufixo.
- **Integração:** runpy na entrada equivalente a python -m sentinela.data.referencia → montagem real → índice salvo/lido: BTCI11/TRPL11 FII. Fontes tabulares sintéticas, identidades B3 arquivadas reais, sem chave de classe montada no teste. Ausência de arquivo e identidade futura mantêm UNKNOWN. Retirada da entrada de módulo já importada apenas no teste simula processo novo e evita warning do runpy.
- **Testes:** 3515→3518 passed,1skip/8xfail; gates CI/data/methods/diff verdes. Três warnings de runpy observados na primeira suíte foram eliminados pela simulação de módulo frio; controles focados3PASS sem warning. Gate final da safe-commit registra o total final. Nenhum golden alterado neste item.
- **Resíduos/decisões:** nenhum novo; revisão somente leitura antes do commit.

### FC2C-66 — fix: select the latest completed fiscal year in CVM collection
- **Executor:** codex (GPT-6).
- **Status:** sucesso.
- **D27 antes:** BUG-2C-66 estrito→xfail; --runxfail confirmou lucro15 do exercício2025 no lugar do77 do exercício encerrado emfevereiro2026 (/tmp/2c66-red.txt), antes de editar MarketEngine.
- **O que foi feito:** _buscar_cvm passa ano_final do seletor documental já existente a calcular_indicadores. Provedor sem seletor conserva assinatura anterior; nada muda no default do provedor ou em método de cálculo. Consulta de seleção reutiliza o cache de leitura; não cria fonte/contingência financeira.
- **Integração:** ZIP CVM não civil março2025–fevereiro2026, seletor/calcular_indicadores/_buscar_cvm reais e saída atéValuationEngine; lucro77 e referência2026-02-28 preservados. Sem ano_final montado na entrada. Série com lacunas continua parcial, não se inventa continuidade na transição do exemplo.
- **Testes:**3518→3519PASS/1skip/8xfail, warning antigo; Ruff CI/data/methods e diffcheck verdes. Nenhum golden alterado.
- **Decisões/resíduos:** relógio real em _serie_cvm e no chamador de seleção fica com destino Fase3/FC2C-71; não alterar política temporal neste fix. Revisão somente leitura antes do commit.

### FC2C-67 — fix: ignore unrelated share event species
- **Executor:** codex (GPT-6).
- **Status:** sucesso.
- **D27 antes:** BUG-2C-67 estrito→2xfail/2controlesPASS; --runxfail produziu2falhas por “evento em espécie distinta sem reconciliação” para PN→PNA/PNB alheias à ON (/tmp/2c67-red.txt), antes da produção.
- **O que foi feito:** _fator_do_par ignora somente quando ambas espécies conhecidas estão fora dos componentes. Espécie desconhecida mantém recusa, evento envolvendo componente mantém exigência de reconciliação; não inventa fator nem dispensa evento oficial do componente.
- **Testes:**104PASS nos fatores+regressão; suíte3519→3523PASS/1skip/8xfail, warning antigo. Fator oficial2 e quatro bases acumuladas conferidos por aritmética; controles PN→ON e ON→PN abstêm. Ruff CI/data/methods/diff verdes; nenhum golden alterado.
- **Resíduos/decisões:** nenhum novo; revisão somente leitura antes do commit.

### FC2C-68 — fix: use neutral MACD crossover descriptions
- **Executor:** codex (GPT-6).
- **Status:** sucesso.
- **D27 antes:** BUG-2C-68 estrito→2xfail; --runxfail confirmou rótulos de ordem de negociação em vez de “Cruzamento de alta/baixa” (/tmp/2c68-red.txt), antes da produção. A primeira execução do teste novo encontrou a precisão de saída em2casas; ajustado o esperado à representação publicada ANTES de qualquer alteração de produção, e repetido o vermelho pelo motivo correto.
- **O que foi feito:** apenas os dois textos de cruzamento mudaram no produtor técnico. Fórmulas, limiares e todos os valores numéricos intactos. App já transporta tech_data para dados.tech e o exibe diretamente na tabela técnica (linhas283/289/416), sem remapear macd_rec; não precisou de mudança paralela.
- **Testes:** impulso positivo/negativo após249preços constantes, EMAα12−α26 e histograma(1−α9) conferidos aritmeticamente, rótulos neutros;3523→3525PASS/1skip/8xfail, warning antigo; Ruff CI/data/methods/diff verdes. Nenhum golden alterado.
- **Resíduos/decisões:** nenhum novo; revisão somente leitura antes do commit.

### FC2C-66R — chore: reuse the selected CVM fiscal year
- **Executor:** codex (GPT-6).
- **Status:** sucesso; resíduo do próprio FC2C-66 removido antes de concluir a fila.
- **Achado:** Ruff completo após66 marcou162contra161anteriores: a chamada duplicada de date.today gerou DTZ011 novo. Gate CI estava verde, mas não basta conservar dívida nova.
- **O que foi feito:** _serie_cvm devolve o ano já selecionado no mesmo corte; _buscar_cvm o reutiliza. Sem segunda leitura de relógio/seletor, sem introduzir outra política temporal. Fonte que não demonstra seleção não vira ano padrão silencioso; interface antiga sem seletor preservada. Docstring atualizada. Nenhum número, fixture ou teste alterado.
- **Testes:**44PASS da série+regressão66;3525PASS/1skip/8xfail, warning antigo; Ruff CI/data/methods/diff verdes. Ruff completo162→161achados, mesma dívida anterior. Chore de limpeza/lint, não novo bug econômico nem teste sem spec.
- **Resíduos/decisões:** date.today original da série permanece destinado à Fase3. Revisão somente leitura antes do commit.

### FC2C-69 — chore: remove unused aggregate score constants
- **Executor:** codex (GPT-6).
- **Status:** sucesso.
- **O que foi feito:** removidas12constantes sem nenhuma leitura, confirmadas por Vulture e busca por palavra inteira em todos os .py rastreados, incluindo testes/scripts, e dentro do próprio config. Lista integral e exceções em docs/limpeza/inventario.md. Retirados dois cabeçalhos vazios e identificados cenários históricos nos comentários, sem reformatar o arquivo.
- **Exceções demonstradas:** ROE_PENALIDADE_MAX ainda lida pela grade protegida; REC_UPSIDE_COMPRA pela asserção de compatibilidade existente. Não eliminadas leituras/testes para tornar a constante artificialmente “sem leitor”. Quatro LYNCH só de scripts históricos; GRAHAM e DY_PERCENTUAL_THRESHOLD também pela grade. Todas documentadas, sem efeito de score/valor atual. TTLs com leitor interno preservados.
- **Testes/inventário:**3525PASS/1skip/8xfail, warning antigo; Vulture global60%30→18achados (12removidos), Ruff completo161→161; CI/data/methods/diff verdes. Nenhuma fórmula, _normalizar_dy, teste ou golden alterado. Limpeza autorizada, não tarefa de teste.
- **Resíduos/decisões:** apenas exceções com leitores, explícitas no inventário; nenhuma dependência/arquivo novo. Revisão somente leitura antes do commit.

### FC2C-70 — docs: disclose the missing annual dividend calendar producer
- **Executor:** codex (GPT-6).
- **Status:** sucesso documental pela alternativa autorizada, sem ligar fonte incompleta à cascata.
- **Levantamento:** busca global confirma calendario_proventos_b3 apenas consumido em qualidade_inputs e construído em testes, sem produtor de produção. A coleta de liquidez recente não demonstra calendário integral de cinco exercícios/bordas, nem disponibilidade no as_of. Ligação exige contrato/fonte/cobertura temporal, destinada a F3-P14 na proposta da Fase3.
- **O que foi feito:** ficha qualidade1.0§9 e texto do relatório explicitam descritor sem produtor, calendário anual sem cobertura e integração Fase3; indisponibilidade não representa anos sem distribuição. Relatório também mostra o aviso fixo de reorganização não detectada, já emitido no quadro. Somente documentação/template, sem regra de cálculo, fonte ou rede nova.
- **Validação:** renderização real com contexto existente conferiu os dois limites e proventos observados0 sem inventar ano zero; suíte3525PASS/1skip/8xfail, warning antigo, gates CI/data/methods/diff verdes. Nenhuma asserção ou golden alterados; não se trata de nova tarefa de teste.
- **Resíduos/decisões:** produtor completo fica explicitamente Fase3, não entregue implicitamente. Revisão somente leitura antes do commit.
