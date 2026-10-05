from datetime import date

import pytest

from sentinela.domain.enums import AssetType, Perfil, Regime
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.gordon import (
    MOTIVO_DY_ABAIXO_DO_MINIMO,
    MOTIVO_DY_NAO_CONFIAVEL,
    MOTIVO_K_NAO_MAIOR_QUE_G,
    MOTIVO_ROE_ABAIXO_DO_MINIMO,
    Gordon,
    GordonParams,
)

PARAMS = GordonParams(
    dy_min=0.04, roe_min=0.10, g_max=0.08, premio_risco=0.07, payout_max=0.95
)


def _inputs(preco=100.0, lpa=10.0, roe=0.15, dy=0.06, selic=0.145, **kw):
    return MethodInputs(
        as_of=date(2026, 10, 2),
        preco=BRL(preco),
        lpa=None if lpa is None else BRL(lpa),
        roe=Ratio(roe),
        dy=Ratio(dy),
        selic=RateNominal(selic),
        perfil=Perfil.RENDA,
        **kw,
    )


def _gordon(**kw):
    return Gordon().calcular(_inputs(**kw), PARAMS)


def _v1(p, lpa, roe, dy, selic):
    """A conta da V1, na mesma ordem de operações. None quando k ≤ g."""
    payout_ratio_g = min((dy * p) / lpa, 0.95) if lpa > 0 else 0.5
    retencao_g = 1 - payout_ratio_g
    g = roe * retencao_g
    g = min(g, 0.08)
    k = selic + 0.07
    if k > g:
        div_prox = (dy * p) * (1 + g)
        return div_prox / (k - g)
    return None


def test_formula_igual_a_da_v1():
    r = _gordon(preco=100.0, lpa=10.0, roe=0.15, dy=0.06, selic=0.145)
    assert isinstance(r, MethodResult)
    assert r.valor.valor == _v1(100.0, 10.0, 0.15, 0.06, 0.145)
    assert (r.metodo, r.versao) == ("Gordon", "1.0.0")


@pytest.mark.parametrize(
    ("p", "lpa", "roe", "dy", "selic"),
    [
        (37.19, 4.31, 0.1873, 0.0613, 0.1375),
        (12.5, 1.1, 0.4, 0.09, 0.0525),
        (80.0, 0.5, 0.25, 0.05, 0.145),
    ],
)
def test_mesma_ordem_de_operacoes_da_v1(p, lpa, roe, dy, selic):
    assert _gordon(preco=p, lpa=lpa, roe=roe, dy=dy, selic=selic).valor.valor == _v1(
        p, lpa, roe, dy, selic
    )


def test_intermediarios_nomeados():
    r = _gordon(preco=100.0, lpa=10.0, roe=0.15, dy=0.06, selic=0.145)
    payout = (0.06 * 100.0) / 10.0
    g = min(0.15 * (1 - payout), 0.08)
    assert r.obter("payout") == Ratio(payout)
    assert r.obter("g") == RateNominal(g)
    assert r.obter("k") == RateNominal(0.145 + 0.07)
    assert r.obter("dividendo_proximo") == BRL((0.06 * 100.0) * (1 + g))


def test_g_limitado_a_8_por_cento():
    r = _gordon(roe=0.9, lpa=10.0, dy=0.06)
    assert r.obter("g") == RateNominal(0.08)


def test_g_abaixo_do_teto_nao_e_limitado():
    r = _gordon(roe=0.11, lpa=10.0, dy=0.06)
    assert r.obter("g") == RateNominal(0.11 * (1 - 0.6))
    assert r.obter("g").valor < 0.08


def test_payout_limitado_a_95_por_cento():
    r = _gordon(preco=100.0, lpa=1.0, dy=0.06)
    assert r.obter("payout") == Ratio(0.95)
    assert r.valor.valor == _v1(100.0, 1.0, 0.15, 0.06, 0.145)


@pytest.mark.parametrize("lpa", [0.0, -2.0])
def test_lpa_nao_positivo_usa_payout_de_50_por_cento(lpa):
    r = _gordon(lpa=lpa)
    assert isinstance(r, MethodResult)
    assert r.obter("payout") == Ratio(0.5)
    assert r.valor.valor == _v1(100.0, lpa, 0.15, 0.06, 0.145)


def test_o_fallback_do_lpa_esta_declarado_nas_premissas():
    assert any("LPA" in a and "50%" in a for a in Gordon.assumptions)


def test_k_igual_ou_menor_que_g_abstem_se():
    # g no teto de 8%: k = selic + 7% fica em 8% quando a selic é 1%
    r_igual = _gordon(roe=0.9, selic=0.01)
    assert isinstance(r_igual, Abstention)
    assert r_igual.motivo == MOTIVO_K_NAO_MAIOR_QUE_G
    assert _gordon(roe=0.9, selic=0.0).motivo == MOTIVO_K_NAO_MAIOR_QUE_G
    assert _gordon(roe=0.9, selic=-0.05).motivo == MOTIVO_K_NAO_MAIOR_QUE_G
    r = _gordon(roe=0.9, selic=0.0101)
    assert isinstance(r, MethodResult)
    assert r.valor.valor == _v1(100.0, 10.0, 0.9, 0.06, 0.0101)


def test_dy_no_minimo_abstem_se_e_acima_calcula():
    r = _gordon(dy=0.04)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_DY_ABAIXO_DO_MINIMO
    assert isinstance(_gordon(dy=0.0401), MethodResult)


def test_roe_no_minimo_abstem_se_e_acima_calcula():
    r = _gordon(roe=0.10)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_ROE_ABAIXO_DO_MINIMO
    assert isinstance(_gordon(roe=0.1001), MethodResult)


def test_dy_nao_confiavel_abstem_se():
    r = _gordon(dy_confiavel=False)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_DY_NAO_CONFIAVEL


def test_vale_para_qualquer_perfil():
    i = MethodInputs(
        as_of=date(2026, 10, 2),
        preco=BRL(100.0),
        lpa=BRL(10.0),
        roe=Ratio(0.15),
        dy=Ratio(0.06),
        selic=RateNominal(0.145),
        perfil=Perfil.CRESCIMENTO,
    )
    assert isinstance(Gordon().calcular(i, PARAMS), MethodResult)


@pytest.mark.parametrize(
    "kw",
    [
        {"dy_confiavel": False},
        {"dy": 0.01},
        {"roe": 0.05},
        {"roe": 0.9, "selic": 0.0},
    ],
)
def test_abstencao_identifica_metodo_e_versao(kw):
    r = _gordon(**kw)
    assert isinstance(r, Abstention)
    assert (r.metodo, r.versao) == ("Gordon", "1.0.0")


@pytest.mark.parametrize("campo", ["preco", "lpa", "roe", "dy", "selic"])
def test_insumo_ausente_abstem_se(campo):
    base = {
        "preco": BRL(100.0),
        "lpa": BRL(10.0),
        "roe": Ratio(0.15),
        "dy": Ratio(0.06),
        "selic": RateNominal(0.145),
    }
    base[campo] = None
    r = Gordon().calcular(MethodInputs(as_of=date(2026, 10, 2), **base), PARAMS)
    assert isinstance(r, Abstention)
    assert r.motivo == f"insumo ausente: {campo}"


def test_resultado_que_estoura_para_infinito_abstem_se():
    r = Gordon().calcular(
        MethodInputs(
            as_of=date(2026, 10, 2),
            preco=BRL(1e308),
            lpa=BRL(0.0),
            roe=Ratio(0.9),
            dy=Ratio(0.9),
            selic=RateNominal(0.145),
        ),
        PARAMS,
    )
    assert isinstance(r, Abstention)
    assert r.motivo == "resultado não finito"
    assert (r.metodo, r.versao) == ("Gordon", "1.0.0")


def test_metadados():
    m = Gordon()
    assert m.nome == "Gordon"
    assert m.version == "1.0.0"
    assert m.regime is Regime.NOMINAL
    assert m.requires == ("preco", "lpa", "roe", "dy", "selic")
    assert m.applies_to == frozenset({AssetType.STOCK, AssetType.UNIT})
    assert m.params_type is GordonParams
    assert all(isinstance(a, str) and a for a in m.assumptions)
