"""BUG-2A-06: P/VP NaN ou infinito sai na saída do motor de FII.

`fii_engine.FIIEngine.analisar` só troca por `None` o P/VP ≤ 0; NaN e +infinito passam o
teste e chegam à saída (furo do F2A-24). Origem: auditoria externa da Fase 2A (Gemini 1ª
passada e Codex, 15/10/2026).
"""

import math
from unittest.mock import patch

import pytest

from fii_engine import FIIEngine


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2A-06 · P/VP NaN ou infinito na saída do motor de FII · corrige: F2A-42",
)
@pytest.mark.parametrize("pvp", [math.nan, math.inf])
def test_pvp_nao_finito_vira_nulo_na_saida(pvp):
    with patch("fii_engine.get_selic_atual", return_value=0.145):
        resultado = FIIEngine().analisar(
            {"ticker": "XPML11", "preco_atual": 100.0, "dy": 0.10, "pvp": pvp}
        )
    assert resultado["pvp"] is None
