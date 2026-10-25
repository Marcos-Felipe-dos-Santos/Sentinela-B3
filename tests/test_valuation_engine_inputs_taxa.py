import math

import pytest

from sentinela.domain.enums import AssetType, ModeloDemonstracao
from sentinela.domain.units import Ratio
from valuation_engine import ValuationEngine

# F2B-4: o motor só monta os insumos depois da guarda de classe e modelo.
ESCOPO = {"classe": AssetType.STOCK, "modelo": ModeloDemonstracao.EMPRESA}


def _montar(**kw):
    return ValuationEngine()._montar_inputs(
        100.0, 10.0, 2.0, False, True, **ESCOPO, **kw
    )


def test_dy_entra_tipado():
    i = _montar(dy=0.08, dy_confiavel=False)
    assert i.dy == Ratio(0.08)
    assert i.dy_confiavel is False


def test_sem_dy_fica_none_e_dy_confiavel_comeca_verdadeiro():
    i = _montar()
    assert i.dy is None
    assert i.dy_confiavel is True


@pytest.mark.parametrize("ruim", [math.nan, math.inf, -math.inf])
def test_dy_nao_finito_vira_none(ruim):
    assert _montar(dy=ruim).dy is None
