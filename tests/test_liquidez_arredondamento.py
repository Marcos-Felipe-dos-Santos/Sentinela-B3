"""Controles nos dois lados do limite; a regra numérica de liquidez não muda."""

import math

import pytest

from sentinela.data.liquidez import avaliar
from tests.test_liquidez_gate import _bloco


@pytest.mark.parametrize("minimo", [100_000.0, 500_000.0])
@pytest.mark.parametrize("acrescimo", [0.0, 0.001, None])
def test_volume_no_minimo_ou_acima_continua_admitido(minimo, acrescimo):
    volume = (
        math.nextafter(minimo, math.inf) if acrescimo is None else minimo + acrescimo
    )
    assert (
        avaliar(_bloco(0.8, volume), janela=63, presenca_min=0.8, volume_min=minimo)
        is None
    )


@pytest.mark.parametrize("minimo", [100_000.0, 500_000.0])
@pytest.mark.parametrize("acrescimo", [0.0, 0.001])
def test_presenca_insuficiente_nao_inventa_volume_inferior(minimo, acrescimo):
    resultado = avaliar(
        _bloco(0.79, minimo + acrescimo), janela=63, presenca_min=0.8, volume_min=minimo
    )
    assert "presença de 79,0%" in resultado["abstencao"]
    assert "volume mediano de <" not in resultado["abstencao"]


@pytest.mark.parametrize(
    ("minimo", "texto"),
    [
        (100_000.0, "R$ 99.999,99"),
        (500_000.0, "R$ 499.999,99"),
    ],
)
def test_volume_distinto_em_centavos_preserva_valor(minimo, texto):
    resultado = avaliar(
        _bloco(0.8, minimo - 0.01), janela=63, presenca_min=0.8, volume_min=minimo
    )
    assert f"volume mediano de {texto} nos últimos" in resultado["abstencao"]
