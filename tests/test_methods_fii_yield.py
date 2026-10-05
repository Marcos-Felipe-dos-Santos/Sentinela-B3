from datetime import date

import pytest

from sentinela.domain.enums import AssetType, Regime
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.fii_yield import (
    MOTIVO_SELIC_LIQUIDA_ZERO,
    FiiYield,
    FiiYieldParams,
)

PARAMS = FiiYieldParams(fator_ir=0.85)


def _inputs(preco=100.0, dy=0.10, selic=0.145, vacancia=None, **kw):
    return MethodInputs(
        as_of=date(2026, 10, 2),
        preco=BRL(preco),
        dy=Ratio(dy),
        selic=RateNominal(selic),
        vacancia=None if vacancia is None else Ratio(vacancia),
        **kw,
    )


def _fii(**kw):
    return FiiYield().calcular(_inputs(**kw), PARAMS)


def test_formula_preco_vezes_dy_efetivo_sobre_selic_liquida():
    r = _fii(preco=100.0, dy=0.10, selic=0.145)
    assert isinstance(r, MethodResult)
    assert r.valor.valor == (100.0 * 0.10) / (0.145 * 0.85)
    assert (r.metodo, r.versao) == ("Bazin FII", "1.0.0")


@pytest.mark.parametrize(
    ("p", "dy", "selic", "vac"),
    [
        (37.19, 0.0913, 0.1375, None),
        (95.5, 0.11, 0.0525, 0.15),
        (12.5, 0.07, 0.145, 0.0),
    ],
)
def test_mesma_ordem_de_operacoes_da_v1(p, dy, selic, vac):
    dy_efetivo = dy * (1 - vac) if vac is not None else dy
    selic_liquida = selic * 0.85
    esperado = (p * dy_efetivo) / selic_liquida
    assert _fii(preco=p, dy=dy, selic=selic, vacancia=vac).valor.valor == esperado


def test_sem_vacancia_o_dy_efetivo_e_o_dy():
    r = _fii(dy=0.10)
    assert r.obter("dy_efetivo") == Ratio(0.10)
    assert r.obter("selic_liquida") == RateNominal(0.145 * 0.85)


def test_com_vacancia_o_dy_efetivo_cai():
    r = _fii(dy=0.10, vacancia=0.2)
    assert r.obter("dy_efetivo") == Ratio(0.10 * (1 - 0.2))
    assert r.valor.valor == (100.0 * (0.10 * (1 - 0.2))) / (0.145 * 0.85)


def test_vacancia_zero_nao_muda_o_dy():
    assert _fii(dy=0.10, vacancia=0.0).obter("dy_efetivo") == Ratio(0.10)


def test_fator_de_ir_vem_dos_parametros():
    r = FiiYield().calcular(_inputs(), FiiYieldParams(fator_ir=0.5))
    assert r.obter("selic_liquida") == RateNominal(0.145 * 0.5)
    assert r.valor.valor == (100.0 * 0.10) / (0.145 * 0.5)


def test_selic_liquida_zero_abstem_se():
    r = _fii(selic=0.0)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_SELIC_LIQUIDA_ZERO
    assert (r.metodo, r.versao) == ("Bazin FII", "1.0.0")


def test_selic_negativa_calcula_como_na_v1():
    r = _fii(selic=-0.02)
    assert isinstance(r, MethodResult)
    assert r.valor.valor == (100.0 * 0.10) / (-0.02 * 0.85)


@pytest.mark.parametrize("campo", ["preco", "dy", "selic"])
def test_insumo_ausente_abstem_se(campo):
    base = {"preco": BRL(100.0), "dy": Ratio(0.10), "selic": RateNominal(0.145)}
    base[campo] = None
    r = FiiYield().calcular(MethodInputs(as_of=date(2026, 10, 2), **base), PARAMS)
    assert isinstance(r, Abstention)
    assert r.motivo == f"insumo ausente: {campo}"


def test_vacancia_ausente_nao_e_insumo_exigido():
    assert "vacancia" not in FiiYield.requires
    assert isinstance(_fii(vacancia=None), MethodResult)


def test_resultado_que_estoura_para_infinito_abstem_se():
    r = _fii(preco=1e308, dy=0.9, selic=0.0001)
    assert isinstance(r, Abstention)
    assert r.motivo == "resultado não finito"
    assert (r.metodo, r.versao) == ("Bazin FII", "1.0.0")


def test_metadados():
    m = FiiYield()
    assert m.nome == "Bazin FII"
    assert m.version == "1.0.0"
    assert m.regime is Regime.NOMINAL
    assert m.requires == ("preco", "dy", "selic")
    assert m.applies_to == frozenset({AssetType.FII})
    assert m.params_type is FiiYieldParams
    assert m.assumptions
    assert all(isinstance(a, str) and a for a in m.assumptions)
