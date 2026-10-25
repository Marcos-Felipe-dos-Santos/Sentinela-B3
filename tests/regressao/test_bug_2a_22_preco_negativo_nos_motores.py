"""BUG-2A-22: preço negativo aceito nos dois motores.

O motor de ações recusa só o preço zero e o não finito (`valuation_engine.py:113` e `:118`);
o de FII, só `p == 0` e o não finito (`fii_engine.py:61`). No golden, `acoes/preco-negativo`
sai com Graham de R$ 12,25. Preço ≤ 0 deve devolver `None`, como o zero (F2A-24). Origem:
ressalva da auditoria do Gemini ao F2A-25.
"""

from unittest.mock import patch

import pytest

from fii_engine import FIIEngine
from tests.test_saidas_finitas import ACAO, FII
from valuation_engine import ValuationEngine


@pytest.mark.parametrize("motor", ["acoes", "fii"])
def test_preco_negativo_devolve_none(motor):
    if motor == "acoes":
        resultado = ValuationEngine().processar({**ACAO, "preco_atual": -10.0})
    else:
        with patch("fii_engine.get_selic_atual", return_value=0.145):
            resultado = FIIEngine().analisar({**FII, "preco_atual": -10.0})
    assert resultado is None
