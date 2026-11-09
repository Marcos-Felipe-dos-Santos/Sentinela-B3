"""BUG-2C-37: Lynch recebia DY da cascata mesmo com perfil pela B3."""

from unittest.mock import patch

import pytest

from tests.apoio_bazin import enriquecer_bazin
from tests.apoio_janelas import enriquecer_janelas
from tests.test_janelas_fundamentais import AS_OF
from valuation_engine import ValuationEngine


def cenario(dy_b3, dy_cascata, roe=0.25):
    d = enriquecer_bazin(
        {
            "ticker": "TST3",
            "preco_atual": 30.0,
            "dy": dy_b3,
            "roe": roe,
            "pl": 15.0,
            "pvp": 2.0,
            "classe_ativo": "STOCK",
            "modelo_bpp": "empresa",
            "lpa": 2.0736,
            "vpa": 20.0,
        }
    )
    d = enriquecer_janelas(d, crescimento=0.2)
    d.update(preco_atual=100.0, dy=dy_cascata)
    if dy_b3 is None:
        d.pop("proventos_b3")
    return d


@pytest.mark.parametrize(
    "dy_b3,dy_cascata,dy_esperado,preco",
    [(0.0, 0.05, 0.0, 30.0), (0.02, 99.0, 0.02, 30.0), (None, 0.02, 0.02, 100.0)],
)
def test_payout_e_perfil_compartilham_fonte_sem_reter_cagr(
    dy_b3, dy_cascata, dy_esperado, preco
):
    d = cenario(dy_b3, dy_cascata)
    motor = ValuationEngine()
    avaliar = motor._avaliar_metodos
    recebido = []

    def capturar(*args, **kwargs):
        recebido.append(args[-1])
        return avaliar(*args, **kwargs)

    with patch.object(motor, "_avaliar_metodos", capturar):
        motor.processar(d, as_of=AS_OF)
    assert recebido[0].dy.valor == dy_esperado
    r = d["janelas_fundamentais"]["lynch"]["payout_contextual"]
    assert r["valor"] == pytest.approx(dy_esperado * preco / 2.0736)
    assert r["dy"] == dy_esperado and r["preco_referencia"] == preco
    assert d["janelas_fundamentais"]["lynch"]["crescimento_lpa"] == pytest.approx(0.2)
    assert ("cascata" in r["fonte"]["fonte"]) is (dy_b3 is None)
