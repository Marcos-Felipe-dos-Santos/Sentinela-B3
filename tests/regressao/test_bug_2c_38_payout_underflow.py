"""BUG-2C-38: valor matematicamente positivo não pode virar payout zero."""

from decimal import Decimal

import pytest

from sentinela.data.payout_lynch import contexto


@pytest.mark.parametrize("dy,preco,lpa", [(1e-300, 1e-300, 1e300), (5e-324, 1.0, 2.0)])
def test_underflow_final_abstem_contexto_sem_inventar_zero(dy, preco, lpa):
    exato = Decimal.from_float(dy) * Decimal.from_float(preco) / Decimal.from_float(lpa)
    assert exato > 0
    r = contexto(dy, preco, lpa, confiavel=True, fonte={"fonte": "sintética"})
    assert r == {
        "abstencao": "payout contextual positivo não representável",
        "fonte": {"fonte": "sintética"},
    }


def test_zero_real_e_subnormal_representavel_continuam_validos():
    assert contexto(0.0, 1.0, 2.0, confiavel=True, fonte={})["valor"] == 0
    assert contexto(5e-324, 2.0, 1.0, confiavel=True, fonte={})["valor"] == 1e-323
