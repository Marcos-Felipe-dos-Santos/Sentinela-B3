from datetime import date

import pytest

from sentinela.domain.enums import AssetType, Regime
from sentinela.domain.units import Ratio
from sentinela.methods.base import Abstention, MethodInputs, MethodResult
from sentinela.methods.fii_nav import (
    FAIXA_DESCONTO,
    FAIXA_PREMIO_ALTO,
    FAIXA_PREMIO_MODERADO,
    FiiNav,
    FiiNavParams,
)

PARAMS = FiiNavParams(premio_alto=1.15, premio_moderado=1.05, desconto=0.85)


def _nav(pvp):
    return FiiNav().calcular(
        MethodInputs(as_of=date(2026, 10, 2), pvp=Ratio(pvp)), PARAMS
    )


@pytest.mark.parametrize(
    ("pvp", "alertas"),
    [
        (2.0, (FAIXA_PREMIO_ALTO,)),
        (1.1501, (FAIXA_PREMIO_ALTO,)),
        (1.15, (FAIXA_PREMIO_MODERADO,)),
        (1.1, (FAIXA_PREMIO_MODERADO,)),
        (1.0501, (FAIXA_PREMIO_MODERADO,)),
        (1.05, ()),
        (1.0, ()),
        (0.85, ()),
        (0.8499, (FAIXA_DESCONTO,)),
        (0.5, (FAIXA_DESCONTO,)),
        (0.0, (FAIXA_DESCONTO,)),
        (-1.0, (FAIXA_DESCONTO,)),
    ],
)
def test_faixa_pelos_limites_estritos_da_v1(pvp, alertas):
    r = _nav(pvp)
    assert isinstance(r, MethodResult)
    assert r.valor == Ratio(pvp)
    assert r.alertas == alertas
    assert (r.metodo, r.versao) == ("P/VP do FII", "1.0.0")


def test_as_tres_faixas_tem_rotulos_distintos():
    assert len({FAIXA_PREMIO_ALTO, FAIXA_PREMIO_MODERADO, FAIXA_DESCONTO}) == 3


def test_limites_vem_dos_parametros():
    r = FiiNav().calcular(
        MethodInputs(as_of=date(2026, 10, 2), pvp=Ratio(1.3)),
        FiiNavParams(premio_alto=1.5, premio_moderado=1.2, desconto=0.5),
    )
    assert r.alertas == (FAIXA_PREMIO_MODERADO,)


def test_pvp_ausente_abstem_se():
    r = FiiNav().calcular(MethodInputs(as_of=date(2026, 10, 2)), PARAMS)
    assert isinstance(r, Abstention)
    assert r.motivo == "insumo ausente: pvp"
    assert (r.metodo, r.versao) == ("P/VP do FII", "1.0.0")


def test_metadados():
    m = FiiNav()
    assert m.nome == "P/VP do FII"
    assert m.version == "1.0.0"
    assert m.regime is Regime.SEM_TAXA
    assert m.requires == ("pvp",)
    assert m.applies_to == frozenset({AssetType.FII})
    assert m.params_type is FiiNavParams
    assert m.assumptions
    assert all(isinstance(a, str) and a for a in m.assumptions)
