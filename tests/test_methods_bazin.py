from datetime import date

import pytest

from sentinela.domain.enums import AssetType, Perfil, Regime
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.bazin import (
    ALERTA_DY_ARMADILHA,
    MOTIVO_DY_ABAIXO_DO_MINIMO,
    MOTIVO_DY_NAO_CONFIAVEL,
    MOTIVO_PERFIL_CRESCIMENTO,
    Bazin,
    BazinParams,
)

PARAMS = BazinParams(dy_min=0.05, dy_armadilha=0.15, taxa_min=0.05)


def _inputs(preco=100.0, dy=0.08, selic=0.145, perfil=Perfil.RENDA, **kw):
    return MethodInputs(
        as_of=date(2026, 10, 2),
        preco=BRL(preco),
        dy=Ratio(dy),
        selic=RateNominal(selic),
        perfil=perfil,
        **kw,
    )


def _bazin(**kw):
    return Bazin().calcular(_inputs(**kw), PARAMS)


def test_formula_dy_vezes_preco_sobre_a_selic():
    r = _bazin(preco=100.0, dy=0.08, selic=0.145)
    assert isinstance(r, MethodResult)
    assert r.valor == BRL((0.08 * 100.0) / 0.145)
    assert r.obter("taxa_aplicada") == RateNominal(0.145)
    assert (r.metodo, r.versao) == ("Bazin", "1.0.0")
    assert r.alertas == ()


def test_mesma_ordem_de_operacoes_da_v1():
    dy, p, selic = 0.0713, 37.19, 0.1375
    assert _bazin(preco=p, dy=dy, selic=selic).valor.valor == (dy * p) / max(
        selic, 0.05
    )


@pytest.mark.parametrize(
    ("selic", "taxa"), [(0.03, 0.05), (0.05, 0.05), (0.0501, 0.0501), (-0.02, 0.05)]
)
def test_taxa_minima_e_o_piso_da_selic(selic, taxa):
    r = _bazin(preco=100.0, dy=0.08, selic=selic)
    assert r.obter("taxa_aplicada") == RateNominal(taxa)
    assert r.valor.valor == (0.08 * 100.0) / taxa


def test_dy_no_minimo_calcula_e_abaixo_abstem_se():
    assert isinstance(_bazin(dy=0.05), MethodResult)
    r = _bazin(dy=0.0499)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_DY_ABAIXO_DO_MINIMO


def test_dy_zero_abstem_se():
    assert _bazin(dy=0.0).motivo == MOTIVO_DY_ABAIXO_DO_MINIMO


def test_perfil_crescimento_abstem_se():
    r = _bazin(perfil=Perfil.CRESCIMENTO)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_PERFIL_CRESCIMENTO


def test_dy_nao_confiavel_abstem_se():
    r = _bazin(dy_confiavel=False)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_DY_NAO_CONFIAVEL


def test_dy_acima_de_15_por_cento_gera_alerta_mas_calcula():
    assert _bazin(dy=0.15).alertas == ()
    r = _bazin(dy=0.1501)
    assert isinstance(r, MethodResult)
    assert r.alertas == (ALERTA_DY_ARMADILHA,)
    assert r.valor.valor == (0.1501 * 100.0) / 0.145


@pytest.mark.parametrize(
    "kw",
    [{"perfil": Perfil.CRESCIMENTO}, {"dy_confiavel": False}, {"dy": 0.01}],
)
def test_abstencao_identifica_metodo_e_versao(kw):
    r = _bazin(**kw)
    assert isinstance(r, Abstention)
    assert (r.metodo, r.versao) == ("Bazin", "1.0.0")


@pytest.mark.parametrize("campo", ["preco", "dy", "selic", "perfil"])
def test_insumo_ausente_abstem_se(campo):
    base = {
        "preco": BRL(100.0),
        "dy": Ratio(0.08),
        "selic": RateNominal(0.145),
        "perfil": Perfil.RENDA,
    }
    base[campo] = None
    r = Bazin().calcular(MethodInputs(as_of=date(2026, 10, 2), **base), PARAMS)
    assert isinstance(r, Abstention)
    assert r.motivo == f"insumo ausente: {campo}"


def test_resultado_que_estoura_para_infinito_abstem_se():
    r = _bazin(preco=1e308, dy=0.9, selic=0.05)
    assert isinstance(r, Abstention)
    assert r.motivo == "resultado não finito"
    assert (r.metodo, r.versao) == ("Bazin", "1.0.0")


def test_metadados():
    b = Bazin()
    assert b.nome == "Bazin"
    assert b.version == "1.0.0"
    assert b.regime is Regime.NOMINAL
    assert b.requires == ("preco", "dy", "selic", "perfil")
    assert b.applies_to == frozenset({AssetType.STOCK, AssetType.UNIT})
    assert b.params_type is BazinParams
    assert b.assumptions
    assert all(isinstance(a, str) and a for a in b.assumptions)
