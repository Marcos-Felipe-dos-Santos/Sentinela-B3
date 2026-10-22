"""BUG-2B-40: lucro e PL positivos podem produzir ROE zero por underflow."""

from sentinela.domain.units import BRL, RateReal
from sentinela.methods.base import Abstention
from tests.test_methods_bancos import _calcular


def test_roe_zero_por_underflow_abstem_antes_do_teto():
    resultado = _calcular(
        lucro_anual_controladores=BRL(1e-308),
        pl_inicial_controladores=BRL(1e308),
        teto_pib_real=RateReal(-0.1),
    )
    assert isinstance(resultado, Abstention)
    assert "ROE nominal não positivo" in resultado.motivo
