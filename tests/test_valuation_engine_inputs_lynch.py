import math

import pytest

from sentinela.domain.units import BRL, Ratio
from valuation_engine import ValuationEngine


def _montar(**kw):
    return ValuationEngine()._montar_inputs(100.0, 10.0, 2.0, True, True, **kw)


def test_roe_e_lpa_entram_tipados():
    i = _montar(roe=0.25, lpa=10.0)
    assert i.roe == Ratio(0.25)
    assert i.lpa == BRL(10.0)


def test_sem_roe_nem_lpa_ficam_none():
    i = _montar()
    assert i.roe is None
    assert i.lpa is None


@pytest.mark.parametrize("ruim", [math.nan, math.inf, -math.inf])
def test_roe_e_lpa_nao_finitos_viram_none(ruim):
    assert _montar(roe=ruim, lpa=10.0).roe is None
    assert _montar(roe=0.25, lpa=ruim).lpa is None
    assert _montar(roe=ruim, lpa=10.0).lpa == BRL(10.0)
    assert _montar(roe=0.25, lpa=ruim).roe == Ratio(0.25)
