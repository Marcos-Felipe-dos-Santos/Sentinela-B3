"""BUG-2C-68: cruzamentos técnicos descrevem direção, sem ordem de negociação."""

import pandas as pd
import pytest

from technical_engine import TechnicalEngine


@pytest.mark.parametrize(
    "salto,rotulo", [(10, "Cruzamento de alta"), (-5, "Cruzamento de baixa")]
)
def test_impulso_apos_preco_constante_descreve_cruzamento(salto, rotulo):
    h = pd.DataFrame({"Close": [10.0] * 249 + [10.0 + salto]})
    r = TechnicalEngine().calcular_indicadores(h)
    # Antes do impulso as duas EMAs são10; contribuição final é α12−α26.
    linha = salto * (2 / 13 - 2 / 27)
    assert r["macd_line"] == pytest.approx(round(linha, 2))
    assert r["macd_hist"] == pytest.approx(round(linha * (1 - 2 / 10), 2))
    assert r["macd_rec"] == rotulo
    assert not any(p in r["macd_rec"].lower() for p in ("compra", "venda"))
