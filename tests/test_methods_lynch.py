from datetime import date

import pytest

from sentinela.domain.enums import AssetType, Perfil, Regime
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.lynch import (
    MOTIVO_DY_NAO_CONFIAVEL,
    MOTIVO_LPA_NAO_POSITIVO,
    MOTIVO_PERFIL_RENDA,
    MOTIVO_PL_NAO_POSITIVO,
    MOTIVO_ROE_NAO_POSITIVO,
    Lynch,
    LynchParams,
)

PARAMS = LynchParams(payout_max=0.95, g_max=0.25, pl_multiplicador=1.5, pl_max=35.0)


def _inputs(
    preco=100.0, pl=15.0, roe=0.25, dy=0.02, perfil=Perfil.CRESCIMENTO, lpa="auto", **kw
):
    if lpa == "auto":
        lpa = BRL(preco / pl) if pl > 0 else BRL(0.0)
    return MethodInputs(
        as_of=date(2026, 10, 2),
        preco=BRL(preco),
        lpa=lpa,
        pl=Ratio(pl),
        roe=Ratio(roe),
        dy=Ratio(dy),
        perfil=perfil,
        **kw,
    )


def _lynch(**kw):
    return Lynch().calcular(_inputs(**kw), PARAMS)


def _v1(p, pl, roe, dy):
    """A conta da V1, na mesma ordem de operações."""
    lpa = p / pl
    payout_ratio = min((dy * p) / lpa, 0.95)
    retencao = 1 - payout_ratio
    g = roe * retencao
    g = min(g, 0.25)
    pl_justo = 1.5 * (g * 100)
    pl_justo = min(pl_justo, 35.0)
    return lpa * pl_justo


def test_formula_igual_a_da_v1():
    r = _lynch(preco=100.0, pl=15.0, roe=0.25, dy=0.02)
    assert isinstance(r, MethodResult)
    assert r.valor.valor == _v1(100.0, 15.0, 0.25, 0.02)
    assert (r.metodo, r.versao) == ("Lynch", "1.0.0")


@pytest.mark.parametrize(
    ("p", "pl", "roe", "dy"),
    [(37.19, 8.13, 0.2371, 0.0213), (12.5, 22.0, 0.31, 0.0), (80.0, 4.0, 0.9, 0.039)],
)
def test_mesma_ordem_de_operacoes_da_v1(p, pl, roe, dy):
    assert _lynch(preco=p, pl=pl, roe=roe, dy=dy).valor.valor == _v1(p, pl, roe, dy)


def test_intermediarios_nomeados():
    r = _lynch(preco=100.0, pl=15.0, roe=0.25, dy=0.02)
    lpa = 100.0 / 15.0
    payout = (0.02 * 100.0) / lpa
    assert r.obter("payout") == Ratio(payout)
    assert r.obter("g") == RateNominal(min(0.25 * (1 - payout), 0.25))
    assert r.obter("pl_justo") == Ratio(min(1.5 * (r.obter("g").valor * 100), 35.0))


def test_teto_de_payout_95():
    # dividendo (dy × preço) bem acima do LPA: payout limitado a 0,95
    r = _lynch(preco=100.0, pl=100.0, roe=0.25, dy=0.039)
    assert r.obter("payout") == Ratio(0.95)
    assert r.valor.valor == _v1(100.0, 100.0, 0.25, 0.039)


def test_teto_de_g_25():
    r = _lynch(preco=100.0, pl=10.0, roe=0.9, dy=0.0)
    assert r.obter("g") == RateNominal(0.25)
    assert r.valor.valor == _v1(100.0, 10.0, 0.9, 0.0)


def test_teto_de_pl_justo_35():
    # g = 25% → 1,5 × 25 = 37,5, acima do teto de 35
    r = _lynch(preco=100.0, pl=10.0, roe=0.9, dy=0.0)
    assert r.obter("pl_justo") == Ratio(35.0)
    assert r.valor == BRL(100.0 / 10.0 * 35.0)


def test_abaixo_dos_tetos_nada_e_limitado():
    r = _lynch(preco=100.0, pl=15.0, roe=0.25, dy=0.02)
    assert r.obter("payout").valor < 0.95
    assert r.obter("g").valor < 0.25
    assert r.obter("pl_justo").valor < 35.0


def test_perfil_renda_abstem_se():
    r = _lynch(perfil=Perfil.RENDA)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_PERFIL_RENDA


def test_dy_nao_confiavel_abstem_se():
    r = _lynch(dy_confiavel=False)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_DY_NAO_CONFIAVEL


@pytest.mark.parametrize("pl", [0.0, -5.0])
def test_pl_nao_positivo_abstem_se(pl):
    r = _lynch(pl=pl, lpa=BRL(1.0))
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_PL_NAO_POSITIVO


@pytest.mark.parametrize("lpa", [0.0, -1.0])
def test_lpa_nao_positivo_abstem_se(lpa):
    r = _lynch(lpa=BRL(lpa))
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_LPA_NAO_POSITIVO


@pytest.mark.parametrize("roe", [0.0, -0.1])
def test_roe_nao_positivo_abstem_se(roe):
    r = _lynch(roe=roe)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_ROE_NAO_POSITIVO


@pytest.mark.parametrize(
    "kw",
    [
        {"perfil": Perfil.RENDA},
        {"dy_confiavel": False},
        {"pl": 0.0, "lpa": BRL(1.0)},
        {"lpa": BRL(0.0)},
        {"roe": 0.0},
    ],
)
def test_abstencao_identifica_metodo_e_versao(kw):
    r = _lynch(**kw)
    assert isinstance(r, Abstention)
    assert (r.metodo, r.versao) == ("Lynch", "1.0.0")


@pytest.mark.parametrize("campo", ["preco", "lpa", "pl", "roe", "dy", "perfil"])
def test_insumo_ausente_abstem_se(campo):
    base = {
        "preco": BRL(100.0),
        "lpa": BRL(6.0),
        "pl": Ratio(15.0),
        "roe": Ratio(0.25),
        "dy": Ratio(0.02),
        "perfil": Perfil.CRESCIMENTO,
    }
    base[campo] = None
    r = Lynch().calcular(MethodInputs(as_of=date(2026, 10, 2), **base), PARAMS)
    assert isinstance(r, Abstention)
    assert r.motivo == f"insumo ausente: {campo}"


def test_resultado_que_estoura_para_infinito_abstem_se():
    r = Lynch().calcular(
        MethodInputs(
            as_of=date(2026, 10, 2),
            preco=BRL(1e308),
            lpa=BRL(1e308),
            pl=Ratio(1.0),
            roe=Ratio(0.9),
            dy=Ratio(0.0),
            perfil=Perfil.CRESCIMENTO,
        ),
        PARAMS,
    )
    assert isinstance(r, Abstention)
    assert r.motivo == "resultado não finito"
    assert (r.metodo, r.versao) == ("Lynch", "1.0.0")


def test_metadados():
    m = Lynch()
    assert m.nome == "Lynch"
    assert m.version == "1.0.0"
    assert m.regime is Regime.NOMINAL
    assert m.requires == ("preco", "lpa", "pl", "roe", "dy", "perfil")
    assert m.applies_to == frozenset({AssetType.STOCK, AssetType.UNIT})
    assert m.params_type is LynchParams
    assert m.assumptions
    assert all(isinstance(a, str) and a for a in m.assumptions)
