"""BUG-2C-30: Graham usa preço/P/L em vez de LPA normalizado aprovado."""

from datetime import date

import pytest

from sentinela.domain.enums import AssetType, ModeloDemonstracao, Perfil
from sentinela.domain.units import BRL, Ratio
from sentinela.methods.base import MethodInputs, MethodResult
from sentinela.methods.graham import Graham, GrahamParams


def test_graham_usa_lpa_direto_independente_do_preco_pl():
    inputs = MethodInputs(
        as_of=date(2026, 10, 20),
        preco=BRL(100),
        pl=Ratio(10),
        pvp=Ratio(2),
        vpa=BRL(20),
        lpa=BRL(3.2),
        perfil=Perfil.RENDA,
        classe_ativo=AssetType.STOCK,
        modelo=ModeloDemonstracao.EMPRESA,
    )
    r = Graham().calcular(inputs, GrahamParams())
    assert isinstance(r, MethodResult)
    assert r.valor.valor == pytest.approx(37.94733192202055)
