"""Rendimento do FII 2.0.0: NTN-B real + spread, crescimento real zero (ficha FII 1.1, §1 e §4)."""

from datetime import date

import pytest

from sentinela.domain.enums import AssetType, Regime
from sentinela.domain.units import BRL, RateReal, Ratio
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.fii_yield import FiiYield, FiiYieldParams

# F2B-4: classe oficial FII (sem BPP de companhia).
ESCOPO = {"classe_ativo": AssetType.FII}

PARAMS = FiiYieldParams(spread=0.02)


def _inputs(preco=100.0, dy=0.10, ntnb=0.07, **kw):
    return MethodInputs(
        **ESCOPO,
        as_of=date(2026, 10, 19),
        preco=BRL(preco),
        dy=Ratio(dy),
        ntnb_real=None if ntnb is None else RateReal(ntnb),
        **kw,
    )


def _fii(params=PARAMS, **kw):
    return FiiYield().calcular(_inputs(**kw), params)


def test_preco_justo_pela_ntnb_mais_spread():
    # V0 = R ÷ (y_real + s), R = preço × DY de 12 meses (ficha, §1).
    r = _fii(preco=100.0, dy=0.10, ntnb=0.07)
    assert isinstance(r, MethodResult)
    assert r.valor.valor == pytest.approx(100.0 * 0.10 / (0.07 + 0.02))
    assert r.obter("taxa") == RateReal(0.07 + 0.02)
    assert r.obter("spread") == RateReal(0.02)
    assert r.obter("rendimento_12m") == BRL(100.0 * 0.10)


def test_sem_ntnb_abstem():
    r = _fii(ntnb=None)
    assert isinstance(r, Abstention)
    assert r.motivo == "insumo ausente: ntnb_real"


def test_exemplo_da_ficha():
    # Ficha FII 1.1, §5, cenário condicional: R = 13,240529645135538184 (HGLG11, preço
    # COTAHIST de 30/09/2026 R$ 147,95, DY 8,949327235644%), y = 74,38/1100, s = 2 pp.
    preco = 147.95
    dy = 13.240529645135538184 / preco
    r = _fii(preco=preco, dy=dy, ntnb=74.38 / 1100)
    assert r.valor.valor == pytest.approx(151.116233758550, abs=1e-9)


@pytest.mark.parametrize(
    ("spread", "valor"), [(0.01, 170.585414), (0.02, 151.116234), (0.03, 135.635897)]
)
def test_sensibilidade_da_ficha(spread, valor):
    preco = 147.95
    r = FiiYield().calcular(
        _inputs(preco=preco, dy=13.240529645135538184 / preco, ntnb=74.38 / 1100),
        FiiYieldParams(spread=spread),
    )
    assert r.valor.valor == pytest.approx(valor, abs=1e-6)


@pytest.mark.parametrize(
    ("kw", "params", "motivo"),
    [
        ({}, FiiYieldParams(spread=None), "spread indisponível"),
        ({}, FiiYieldParams(spread=float("nan")), "spread indisponível"),
        ({"ntnb": -1.0}, PARAMS, "taxa indisponível: NTN-B real fora do domínio"),
        ({"ntnb": -0.02}, PARAMS, "taxa não positiva"),
        ({"ntnb": -0.05}, PARAMS, "taxa não positiva"),
        ({"dy": 0.0}, PARAMS, "rendimento anual não positivo"),
        ({"dy": -0.01}, PARAMS, "rendimento anual não positivo"),
        ({"dy": 0.2501}, PARAMS, "rendimento não confiável"),
        ({"preco": 0.0}, PARAMS, "preço não positivo"),
        (
            {"preco": 1e308, "dy": 0.2, "ntnb": -0.019999},
            PARAMS,
            "resultado não finito",
        ),
    ],
)
def test_matriz_de_validade(kw, params, motivo):
    r = _fii(params=params, **kw)
    assert isinstance(r, Abstention)
    assert r.motivo == motivo
    assert (r.metodo, r.versao) == ("Rendimento do FII", "2.1.0")


def test_spread_negativo_com_taxa_positiva_calcula():
    # Ficha, §4: spread negativo é permitido se a mediana for comprovada e q > 0.
    r = _fii(params=FiiYieldParams(spread=-0.01), ntnb=0.07)
    assert r.valor.valor == pytest.approx(100.0 * 0.10 / 0.06)


def test_metadados():
    m = FiiYield()
    assert m.nome == "Rendimento do FII"
    assert m.version == "2.1.0"
    assert m.regime is Regime.REAL
    assert m.requires == ("preco", "dy", "ntnb_real")
    assert m.applies_to == frozenset({AssetType.FII})
    assert m.params_type is FiiYieldParams
    assert m.assumptions
    assert all(isinstance(a, str) and a for a in m.assumptions)
