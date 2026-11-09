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
