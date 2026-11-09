"""BUG-2C-31: multiplicador legado 1,5 contraria m=1 aprovado em28/10."""

from datetime import date

import pytest

from sentinela.domain.enums import AssetType, ModeloDemonstracao, Perfil
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.base import MethodInputs, MethodResult
from sentinela.methods.lynch import Lynch, LynchParams


def test_lynch_exemplo_independente_aprovado():
    inputs = MethodInputs(
        as_of=date(2026, 10, 20),
        preco=BRL(30),
        pl=Ratio(10),
        roe=Ratio(0.2),
        dy=Ratio(0),
        lpa=BRL(2.0736),
        perfil=Perfil.CRESCIMENTO,
        classe_ativo=AssetType.STOCK,
        modelo=ModeloDemonstracao.EMPRESA,
        crescimento_lpa=RateNominal(0.2),
    )
    r = Lynch().calcular(inputs, LynchParams())
    assert isinstance(r, MethodResult)
    assert r.valor.valor == pytest.approx(41.472)
