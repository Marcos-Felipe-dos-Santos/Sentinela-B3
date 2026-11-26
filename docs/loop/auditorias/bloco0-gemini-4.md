Auditoria externa (somente leitura) do intervalo acebb0d..f110c5c na branch v2/fase-4 (commits d65be96 e f110c5c, item F4-C14).

(a) Bloqueadores

Nenhum.

Regressão do BUG-4-25: test_bug_4_25_dfp_recuo_mesma_versao_outra_referencia.py monta ZIPs sintéticos com 2025-09-30 V1 entregue em 2026-06-15 (< D) e 2025-12-31 V1 entregue em 2026-06-16 (== D), exige R$ 100 mil e 2025-09-30 V1 tanto no snapshot (L58-L64) quanto na série (L67-L73), e exige abstenção em ambos quando setembro some do demonstrativo (L76-L87).
Complemento ao BUG-4-23: test_bug_4_23_dfp_ano_anterior_fora_do_corte.py recebeu apenas a asserção aditiva assert ultimo["lucro_liquido"] == pytest.approx(LUCRO["1"] * 1_000), sem alterar nenhum literal ou asserção existente.
Propagação de (DT_REFER, VERSAO) e ausência de reescolha: cvm_provider.py devolve (ano, versao, dt_refer) em documento_anual_mais_recente; market_engine.py envia versao_final e dt_refer_final para indicadores_da_serie e os transfere via dados['_documento_dfp_final'] (removido com pop) para _buscar_cvm (L1269-L1279); cvm_provider.py filtra dre_emp por dt_refer_final e versao_final e propaga o par para BPA/BPP/DRE e consumidores subsequentes (L653-L654, L723-L726, L1322-L1366). exercicio_e_versao_mais_recente (cvm_provider.py) não tem chamadores em produção (apenas testes legados).
Escopo, golden e privacidade: nenhuma mudança de comportamento em datas passadas (_data_passada continua em exercicio_anual_mais_recente, market_engine.py) nem quando versao_final/dt_refer_final são None. SHA-256 de golden_motores.jsonl confirmado como 6ad8308191a7c971e6b9e609412c49aee799b57f0b4e5af2a51117b13f361007. Sem dados da carteira, caminhos pessoais ou vocabulário proibido nos arquivos versionados do diff.
Mutação: mutacao-resumo.txt registra _versao_comprovada 79/80 (98,75%), documento_anual_mais_recente 28/28 (100%), exercicio_e_versao_mais_recente 5/5 (100%) e 100% nos mutantes adicionais das linhas alteradas dos leitores. O único sobrevivente (_versao_comprovada__mutmut_42, confirmado em mutants/cvm_provider.py) troca fim > referencia (cvm_provider.py) por fim >= referencia; a triagem é coerente com o código, pois entregas em D ou depois já são barradas pelo corte estrito recebida < referencia (L1228).
(b) Ressalvas
Defensividade da assinatura dt_refer_final sem versao_final: em cvm_provider.py, se um chamador passar dt_refer_final com versao_final=None e a referência estiver ausente em dre_emp, df_concat fica vazio e o método pula o bloco if not df_concat.empty sem levantar erro nem filtrar BPA/BPP/DRE. Não afeta o código de produção (que sempre envia o par em market_engine.py).
Registro de mutação no diário: diario.md apenas referencia outputs/F4-C14/ (não versionado) sem transcrever os percentuais de mutação e a triagem do sobrevivente, diferentemente do registro do F4-C13 (L671-L672).
(c) Não verificado
Execução independente da suíte pytest, do mutmut e do ruff (auditoria estritamente somente leitura, sem comandos que escrevam; foram inspecionados os artefatos produzidos pelo executor em gate-final.txt, regressao-depois.txt e mutacao-resumo.txt).
(d) Veredito final

Pode seguir.