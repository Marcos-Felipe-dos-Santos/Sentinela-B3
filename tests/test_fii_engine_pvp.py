import math

import pytest

import fii_engine
from fii_engine import FIIEngine
from sentinela.methods.base import MethodResult
from sentinela.methods.fii_nav import (
    FAIXA_DESCONTO,
    FAIXA_PREMIO_ALTO,
    FAIXA_PREMIO_MODERADO,
)


def test_pontos_por_faixa_sao_os_da_v1():
    assert fii_engine._PONTOS_PVP == {
        FAIXA_PREMIO_ALTO: -15,
        FAIXA_PREMIO_MODERADO: -7,
        FAIXA_DESCONTO: 10,
    }


@pytest.mark.parametrize(
    ("pvp", "alertas"),
    [
        (1.16, (FAIXA_PREMIO_ALTO,)),
        (1.15, (FAIXA_PREMIO_MODERADO,)),
        (1.05, ()),
        (0.85, ()),
        (0.84, (FAIXA_DESCONTO,)),
    ],
)
def test_faixa_usa_os_limites_do_macro_context(pvp, alertas):
    r = FIIEngine()._faixa_pvp(pvp)
    assert isinstance(r, MethodResult)
    assert r.alertas == alertas


@pytest.mark.parametrize("ruim", [math.nan, math.inf, -math.inf])
def test_pvp_nao_finito_nao_calcula_a_lente(ruim):
    assert FIIEngine()._faixa_pvp(ruim) is None
