"""BUG-2A-21: ROE de fonte de mercado sem piso na fronteira.

`sentinela/data/normalizacao.guardar_roe` corta o ROE acima de 2, mas não tem piso: um −21,0
do yfinance (declarado em razão) entra como −2.100%. Decisão do Marcos de 18/10/2026
([AUDITORIA], decisão C): piso de −2, simétrico ao teto; abaixo dele, ausente com o motivo.
Origem: auditoria do Gemini (14/10/2026), pendência do F2A-30.
"""

import pytest

from sentinela.data import normalizacao


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2A-21 · ROE de fonte de mercado sem piso (−21 entra como −2.100%) · corrige: F2B-18",
)
def test_roe_muito_negativo_vira_ausente_com_motivo():
    valor, motivo = normalizacao.guardar_roe(-21.0)
    assert valor is None
    assert motivo
