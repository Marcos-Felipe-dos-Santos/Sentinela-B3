import math

import pytest

from fii_engine import FIIEngine
from sentinela.methods.base import Abstention, MethodResult


def _rendimento(p=100.0, dy=0.10, vacancia=None, selic=0.145):
    return FIIEngine()._calcular_rendimento(p, dy, vacancia, selic)


def test_valores_finitos_delegam_ao_metodo():
    r = _rendimento()
    assert isinstance(r, MethodResult)
    assert r.valor.valor == (100.0 * 0.10) / (0.145 * 0.85)


def test_vacancia_entra_no_dy_efetivo():
    r = _rendimento(vacancia=0.2)
    assert r.obter("dy_efetivo").valor == 0.10 * (1 - 0.2)


@pytest.mark.parametrize("ruim", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("campo", ["p", "dy", "vacancia", "selic"])
def test_valor_nao_finito_nao_calcula_o_metodo(campo, ruim):
    assert _rendimento(**{campo: ruim}) is None


def test_selic_zero_vira_abstencao_e_nao_excecao():
    r = _rendimento(selic=0.0)
    assert isinstance(r, Abstention)
