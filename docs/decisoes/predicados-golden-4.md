# Predicados do golden — Fase 4

## F4-C10 — família de Qualidade (P1 = opção B, decisão do Marcos de 25/11/2026)

- Plano: `docs/decisoes/golden-qualidade-4.md`, §4 e §5.
- Golden anterior: `tests/fixtures/golden_motores.jsonl`, SHA-256
  `1759c55f7e5995f54075cc78cf64e0ea7d0580089ec68902ee3fe153cc84b1d8`, 2291 linhas (2003 de ações
  e 288 de FII).
- Golden posterior: SHA-256 `6ad8308191a7c971e6b9e609412c49aee799b57f0b4e5af2a51117b13f361007`,
  2303 linhas.
- **Predicado aprovado:** só as linhas novas. As 2291 linhas anteriores ficam byte a byte iguais
  e na mesma ordem. As 12 novas entram depois do último caso de ações
  (`bazin_taxa_selic0.25_dy0.2501`) e antes do primeiro de FII, na ordem de `montar_casos`.
- Conferência (executor, 25/11/2026): a lista das linhas do golden posterior que já existiam no
  anterior é igual, em ordem, ao golden anterior; as linhas novas são exatamente estes 12 ids:
  `qualidade-empresa-completa`, `qualidade-banco-completo`, `qualidade-unit`,
  `qualidade-sem-lucro`, `qualidade-pl-inicial-zero`, `qualidade-sem-ebitda`,
  `qualidade-receita-zero`, `qualidade-calendario-curto`, `qualidade-relacao-abstida`,
  `qualidade-entrega-depois-do-as_of`, `qualidade-por-publicacao`, `qualidade-perimetro-misto`.
- Valores de referência: os dois casos completos têm os valores calculados à mão em
  `tests/test_qualidade_golden_valores.py`, escritos e verdes antes da geração.
