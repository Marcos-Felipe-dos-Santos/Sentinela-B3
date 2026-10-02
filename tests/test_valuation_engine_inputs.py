import math

import pytest

from sentinela.domain.enums import Perfil
from sentinela.domain.units import BRL, Ratio
from valuation_engine import ValuationEngine


def _montar(p=100.0, pl=10.0, pvp=2.0, is_growth=False, pl_confiavel=True):
    return ValuationEngine()._montar_inputs(p, pl, pvp, is_growth, pl_confiavel)


def test_converte_os_dados_da_v1_em_inputs_tipados():
    i = _montar()
    assert i.preco == BRL(100.0)
    assert i.pl == Ratio(10.0)
    assert i.pvp == Ratio(2.0)
    assert i.vpa == BRL(100.0 / 2.0)
    assert i.perfil is Perfil.RENDA
    assert i.pl_confiavel is True


def test_perfil_e_flag_vem_dos_argumentos():
    i = _montar(is_growth=True, pl_confiavel=False)
    assert i.perfil is Perfil.CRESCIMENTO
    assert i.pl_confiavel is False


@pytest.mark.parametrize("ruim", [math.nan, math.inf, -math.inf])
def test_valor_nao_finito_vira_none(ruim):
    assert _montar(p=ruim).preco is None
    assert _montar(p=ruim).vpa is None
    assert _montar(pl=ruim).pl is None
    i = _montar(pvp=ruim)
    assert i.pvp is None
    assert i.vpa is None


@pytest.mark.parametrize("pvp", [0.0, -1.5])
def test_pvp_nao_positivo_da_vpa_zero_como_na_v1(pvp):
    assert _montar(pvp=pvp).vpa == BRL(0.0)


def test_vpa_que_estoura_para_infinito_vira_none():
    assert _montar(p=1e300, pvp=1e-300).vpa is None
