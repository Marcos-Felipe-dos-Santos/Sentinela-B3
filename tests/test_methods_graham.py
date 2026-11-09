"""Graham2.0 aprovado: exemplo independente e retirada explícita dos limitesV1."""

from datetime import date

import pytest

from sentinela.domain.enums import AssetType, ModeloDemonstracao, Perfil, Regime
from sentinela.domain.units import BRL, Ratio
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.graham import Graham, GrahamParams

ESCOPO = {"classe_ativo": AssetType.STOCK, "modelo": ModeloDemonstracao.EMPRESA}


def _inputs(**kw):
    return MethodInputs(
        as_of=date(2026, 10, 20), **{**ESCOPO, "lpa": BRL(3.2), "vpa": BRL(20), **kw}
    )


def _graham(**kw):
    return Graham().calcular(_inputs(**kw), GrahamParams())


def test_formula_externa_da_ficha_2_0():
    r = _graham()
    assert isinstance(r, MethodResult)
    assert r.valor.valor == pytest.approx(37.94733192202055)
    assert r.obter("lpa_medio_normalizado") == BRL(3.2)
    assert r.obter("vpa_final") == BRL(20)
    assert (r.metodo, r.versao) == ("Graham", "2.1.0")


@pytest.mark.parametrize("pl", [-10, 0, 3, 7, 25, 80, 1000])
@pytest.mark.parametrize("pvp", [0, 1, 2.5, 2.8, 3, 10])
def test_multiplos_nao_tem_piso_nem_guardas(pl, pvp):
    r = _graham(preco=BRL(100), pl=Ratio(pl), pvp=Ratio(pvp), pl_confiavel=False)
    assert isinstance(r, MethodResult)
    assert r.valor.valor == pytest.approx(37.94733192202055)


@pytest.mark.parametrize("perfil", [None, Perfil.RENDA, Perfil.CRESCIMENTO])
def test_perfil_nao_altera_o_referencial(perfil):
    assert _graham(perfil=perfil).valor.valor == pytest.approx(37.94733192202055)


@pytest.mark.parametrize("campo", ["lpa", "vpa"])
@pytest.mark.parametrize("valor", [-1, 0])
def test_insumo_nao_positivo_abstem_se(campo, valor):
    r = _graham(**{campo: BRL(valor)})
    assert isinstance(r, Abstention)
    assert "≤ 0" in r.motivo
    assert (r.metodo, r.versao) == ("Graham", "2.1.0")


@pytest.mark.parametrize("campo", ["lpa", "vpa"])
def test_insumo_ausente_abstem_se(campo):
    r = _graham(**{campo: None})
    assert isinstance(r, Abstention)
    assert r.motivo == f"insumo ausente: {campo}"


def test_resultado_que_estoura_para_infinito_abstem_se():
    r = _graham(lpa=BRL(1e308), vpa=BRL(1e308))
    assert isinstance(r, Abstention)
    assert r.motivo == "resultado não finito"


def test_metadados_e_sem_rede_relogio_ou_parametro_legado():
    g = Graham()
    assert g.version == "2.1.0"
    assert g.regime is Regime.SEM_TAXA
    assert g.requires == ("lpa", "vpa")
    assert g.applies_to == frozenset({AssetType.STOCK, AssetType.UNIT})
    assert g.params_type is GrahamParams
    assert g.assumptions
    assert _graham().valor.valor == _graham().valor.valor


@pytest.mark.parametrize(
    "classe,modelo",
    [(AssetType.FII, None), (AssetType.STOCK, ModeloDemonstracao.BANCO)],
)
def test_escopo_preservado(classe, modelo):
    assert isinstance(_graham(classe_ativo=classe, modelo=modelo), Abstention)
