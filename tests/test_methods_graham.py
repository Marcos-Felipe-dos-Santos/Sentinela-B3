import math
from datetime import date

import pytest

from sentinela.domain.enums import AssetType, Perfil, Regime
from sentinela.domain.units import BRL, Ratio
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.graham import (
    MOTIVO_NAO_FINITO,
    MOTIVO_PL_NAO_CONFIAVEL,
    Graham,
    GrahamParams,
)

PARAMS = GrahamParams(
    pl_limite=25.0, pl_piso=7.0, pvp_limite_renda=2.5, pvp_limite_crescimento=3.0
)


def _inputs(preco=100.0, pl=10.0, pvp=1.5, perfil=Perfil.RENDA, **kw):
    vpa = BRL(preco / pvp) if pvp is not None and pvp > 0 else None
    return MethodInputs(
        as_of=date(2026, 10, 2),
        preco=BRL(preco),
        pl=Ratio(pl) if pl is not None else None,
        pvp=Ratio(pvp) if pvp is not None else None,
        vpa=vpa,
        perfil=perfil,
        **kw,
    )


def _graham(**kw):
    return Graham().calcular(_inputs(**kw), PARAMS)


def test_formula_raiz_de_22_5_lpa_ajustado_vpa():
    r = _graham(preco=100.0, pl=10.0, pvp=2.0)
    assert isinstance(r, MethodResult)
    lpa, vpa = 100.0 / 10.0, 100.0 / 2.0
    assert r.valor == BRL(math.sqrt(22.5 * lpa * vpa))
    assert r.obter("lpa_ajustado") == BRL(10.0)
    assert r.obter("pl_aplicado") == Ratio(10.0)
    assert (r.metodo, r.versao) == ("Graham", "1.0.0")


def test_mesma_ordem_de_operacoes_da_v1():
    p, pl, pvp = 37.19, 8.13, 1.07
    esperado = (22.5 * (p / max(pl, 7.0)) * (p / pvp)) ** 0.5
    assert _graham(preco=p, pl=pl, pvp=pvp).valor.valor == esperado


def test_piso_de_pl_7_vale_so_para_o_lpa_ajustado():
    abaixo = _graham(preco=70.0, pl=3.0, pvp=1.0)
    assert abaixo.obter("pl_aplicado") == Ratio(7.0)
    assert abaixo.obter("lpa_ajustado") == BRL(70.0 / 7.0)
    no_piso = _graham(preco=70.0, pl=7.0, pvp=1.0)
    assert no_piso.obter("pl_aplicado") == Ratio(7.0)
    acima = _graham(preco=70.0, pl=7.5, pvp=1.0)
    assert acima.obter("pl_aplicado") == Ratio(7.5)


@pytest.mark.parametrize("pl", [25.0, 24.99])
def test_pl_no_limite_ou_abaixo_calcula(pl):
    assert isinstance(_graham(pl=pl), MethodResult)


def test_pl_acima_do_limite_abstem_se():
    r = _graham(pl=25.01)
    assert isinstance(r, Abstention)
    assert r.motivo == "P/L acima do limite"


@pytest.mark.parametrize(
    ("perfil", "limite"), [(Perfil.RENDA, 2.5), (Perfil.CRESCIMENTO, 3.0)]
)
def test_limite_de_pvp_depende_do_perfil(perfil, limite):
    assert isinstance(_graham(pvp=limite, perfil=perfil), MethodResult)
    r = _graham(pvp=limite + 0.01, perfil=perfil)
    assert isinstance(r, Abstention)
    assert r.motivo == "P/VP acima do limite"


def test_pvp_entre_os_dois_limites_so_calcula_em_crescimento():
    assert isinstance(_graham(pvp=2.8, perfil=Perfil.CRESCIMENTO), MethodResult)
    assert isinstance(_graham(pvp=2.8, perfil=Perfil.RENDA), Abstention)


@pytest.mark.parametrize("pl", [0.0, -3.0])
def test_pl_nao_positivo_abstem_se(pl):
    r = _graham(pl=pl)
    assert isinstance(r, Abstention)
    assert r.motivo == "P/L ou P/VP não positivo"


@pytest.mark.parametrize("pvp", [0.0, -1.0])
def test_pvp_nao_positivo_abstem_se(pvp):
    r = Graham().calcular(
        MethodInputs(
            as_of=date(2026, 10, 2),
            preco=BRL(100.0),
            pl=Ratio(10.0),
            pvp=Ratio(pvp),
            vpa=BRL(0.0),
            perfil=Perfil.RENDA,
        ),
        PARAMS,
    )
    assert isinstance(r, Abstention)
    assert r.motivo == "P/L ou P/VP não positivo"


def test_pl_nao_confiavel_abstem_se_mesmo_dentro_dos_limites():
    r = _graham(pl_confiavel=False)
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_PL_NAO_CONFIAVEL


def test_pl_nao_confiavel_tem_prioridade_sobre_os_limites():
    assert _graham(pl=30.0, pl_confiavel=False).motivo == MOTIVO_PL_NAO_CONFIAVEL


@pytest.mark.parametrize("campo", ["pl", "pvp", "vpa", "perfil", "preco"])
def test_insumo_ausente_abstem_se(campo):
    base = {
        "preco": BRL(100.0),
        "pl": Ratio(10.0),
        "pvp": Ratio(1.5),
        "vpa": BRL(66.0),
        "perfil": Perfil.RENDA,
    }
    base[campo] = None
    r = Graham().calcular(MethodInputs(as_of=date(2026, 10, 2), **base), PARAMS)
    assert isinstance(r, Abstention)
    assert r.motivo == f"insumo ausente: {campo}"


def test_metadados():
    g = Graham()
    assert g.nome == "Graham"
    assert g.version == "1.0.0"
    assert g.regime is Regime.SEM_TAXA
    assert g.requires == ("preco", "pl", "pvp", "vpa", "perfil")
    assert g.applies_to == frozenset({AssetType.STOCK, AssetType.UNIT})
    assert g.params_type is GrahamParams
    assert len(g.assumptions) >= 1
    assert all(isinstance(a, str) and a for a in g.assumptions)


@pytest.mark.parametrize(
    "kw",
    [
        {"pl_confiavel": False},
        {"pl": 0.0},
        {"pl": 30.0},
        {"pvp": 2.6},
    ],
)
def test_abstencao_identifica_metodo_e_versao(kw):
    r = _graham(**kw)
    assert isinstance(r, Abstention)
    assert (r.metodo, r.versao) == ("Graham", "1.0.0")


def test_resultado_que_estoura_para_infinito_abstem_se():
    r = Graham().calcular(
        MethodInputs(
            as_of=date(2026, 10, 2),
            preco=BRL(1e300),
            pl=Ratio(10.0),
            pvp=Ratio(1.0),
            vpa=BRL(1e300),
            perfil=Perfil.RENDA,
        ),
        PARAMS,
    )
    assert isinstance(r, Abstention)
    assert r.motivo == MOTIVO_NAO_FINITO
    assert (r.metodo, r.versao) == ("Graham", "1.0.0")
