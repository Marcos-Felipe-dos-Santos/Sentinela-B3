"""Lynch2.0: sem oráculoV1, CAGR já normalizado na fronteira documental."""

from datetime import date

import pytest

from sentinela.domain.enums import AssetType, ModeloDemonstracao, Perfil, Regime
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.lynch import Lynch, LynchParams


def _inputs(**kw):
    return MethodInputs(
        as_of=date(2026, 10, 20),
        **{
            "classe_ativo": AssetType.STOCK,
            "modelo": ModeloDemonstracao.EMPRESA,
            "lpa": BRL(2.0736),
            "crescimento_lpa": RateNominal(0.2),
            "perfil": Perfil.CRESCIMENTO,
            **kw,
        },
    )


def _lynch(**kw):
    return Lynch().calcular(_inputs(**kw), LynchParams())


def test_exemplo_independente_aprovado_m_1():
    r = _lynch()
    assert isinstance(r, MethodResult)
    assert r.valor.valor == pytest.approx(41.472)
    assert r.obter("g") == RateNominal(0.2)
    assert r.obter("pl_justo") == Ratio(20)
    assert (r.metodo, r.versao) == ("Lynch", "2.1.0")


@pytest.mark.parametrize(
    "g,multiplo,valor",
    [(0.1, 10, 20.736), (0.2, 20, 41.472), (0.25, 25, 51.84), (0.4, 25, 51.84)],
)
def test_sensibilidade_e_teto_de_g(g, multiplo, valor):
    r = _lynch(crescimento_lpa=RateNominal(g))
    assert r.valor.valor == pytest.approx(valor)
    assert r.obter("pl_justo") == Ratio(multiplo)


@pytest.mark.parametrize("dy", [0, 0.03, 0.25])
@pytest.mark.parametrize("pl", [-1, 0, 100])
def test_payout_e_multiplos_nao_reduzem_cagr_no_metodo(dy, pl):
    r = _lynch(
        preco=BRL(30), dy=Ratio(dy), pl=Ratio(pl), roe=Ratio(-1), dy_confiavel=False
    )
    assert r.valor.valor == pytest.approx(41.472)


@pytest.mark.parametrize("campo", ["lpa", "crescimento_lpa", "perfil"])
def test_insumo_ausente_abstem_se(campo):
    r = _lynch(**{campo: None})
    assert isinstance(r, Abstention)
    assert r.motivo == f"insumo ausente: {campo}"


@pytest.mark.parametrize("lpa", [-5, 0])
def test_lpa_nao_positivo_abstem_se(lpa):
    r = _lynch(lpa=BRL(lpa))
    assert isinstance(r, Abstention)
    assert r.motivo == "LPA não positivo"


@pytest.mark.parametrize("g", [-0.2, 0])
def test_crescimento_nao_positivo_nao_fabrica_preco_zero(g):
    r = _lynch(crescimento_lpa=RateNominal(g))
    assert isinstance(r, Abstention)
    assert r.motivo == "CAGR não positivo"


def test_perfil_renda_abstem_se():
    r = _lynch(perfil=Perfil.RENDA)
    assert isinstance(r, Abstention)
    assert r.motivo == "perfil renda"


def test_resultado_que_estoura_para_infinito_abstem_se():
    r = _lynch(lpa=BRL(1e308))
    assert isinstance(r, Abstention)
    assert r.motivo == "resultado não finito"
    assert (r.metodo, r.versao) == ("Lynch", "2.1.0")


def test_metadados():
    m = Lynch()
    assert m.regime is Regime.NOMINAL
    assert m.requires == ("lpa", "crescimento_lpa", "perfil")
    assert m.applies_to == frozenset({AssetType.STOCK, AssetType.UNIT})
    assert m.params_type is LynchParams
    assert m.assumptions
