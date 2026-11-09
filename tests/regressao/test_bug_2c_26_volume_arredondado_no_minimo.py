"""BUG-2C-26: volume estritamente inferior não deve ser mostrado como igual ao mínimo."""

import math

import pytest

from sentinela.data.liquidez import avaliar
from tests.test_liquidez_gate import _bloco


@pytest.mark.parametrize(
    ("minimo", "limite_texto"),
    [
        (100_000.0, "R$ 100.000,00"),
        (500_000.0, "R$ 500.000,00"),
    ],
)
@pytest.mark.parametrize("distancia", [0.001, 0.000001, None])
def test_volume_abaixo_nao_parece_igual_ao_minimo(minimo, limite_texto, distancia):
    volume = (
        math.nextafter(minimo, -math.inf) if distancia is None else minimo - distancia
    )
    resultado = avaliar(
        _bloco(0.8, volume), janela=63, presenca_min=0.8, volume_min=minimo
    )
    assert f"volume mediano de < {limite_texto} nos últimos" in resultado["abstencao"]
    assert f"mínimo: 80,0% e {limite_texto}" in resultado["abstencao"]
