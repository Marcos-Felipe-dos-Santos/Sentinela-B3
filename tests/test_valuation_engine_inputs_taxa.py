import math

import pytest

from sentinela.domain.units import RateNominal, Ratio
from valuation_engine import ValuationEngine


def _montar(**kw):
    return ValuationEngine()._montar_inputs(100.0, 10.0, 2.0, False, True, **kw)


def test_dy_e_selic_entram_tipados():
    i = _montar(dy=0.08, selic=0.145, dy_confiavel=False)
    assert i.dy == Ratio(0.08)
    assert i.selic == RateNominal(0.145)
    assert i.dy_confiavel is False


def test_sem_dy_nem_selic_ficam_none_e_dy_confiavel_comeca_verdadeiro():
    i = _montar()
    assert i.dy is None
    assert i.selic is None
    assert i.dy_confiavel is True


@pytest.mark.parametrize("ruim", [math.nan, math.inf, -math.inf])
def test_dy_e_selic_nao_finitos_viram_none(ruim):
    assert _montar(dy=ruim, selic=0.1).dy is None
    assert _montar(dy=0.08, selic=ruim).selic is None
    assert _montar(dy=0.08, selic=ruim).dy == Ratio(0.08)


def test_selic_negativa_e_zero_passam():
    assert _montar(selic=-0.02).selic == RateNominal(-0.02)
    assert _montar(selic=0.0).selic == RateNominal(0.0)
