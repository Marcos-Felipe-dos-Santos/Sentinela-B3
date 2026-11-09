"""BUG-2C-39: ausência simultânea não demonstra perfil de crescimento."""

import pytest

from tests.regressao.test_bug_2c_37_lynch_fonte_payout import cenario
from tests.test_janelas_fundamentais import AS_OF
from valuation_engine import ValuationEngine


@pytest.mark.parametrize("tipo", ["None", "ausente", "bool", "vazio"])
def test_sem_duas_fontes_lynch_nao_recebe_dy_zero(tipo):
    d = cenario(None, None)
    if tipo == "ausente":
        d.pop("dy")
    if tipo == "bool":
        d["dy"] = False
    if tipo == "vazio":
        d["dy"] = ""
    r = ValuationEngine().processar(d, as_of=AS_OF)
    assert "Lynch:" not in r["metodos_usados"]
    assert "Bazin:" not in r["metodos_usados"]
    j = d["janelas_fundamentais"]["lynch"]
    assert "payout_contextual" not in j
    assert "perfil não demonstrado" in j["abstencao"]


def test_dy_ausente_na_cascata_nao_tem_flag_confiavel():
    d = cenario(None, None)
    r = ValuationEngine().processar(d, as_of=AS_OF)
    assert r["dy_confiavel"] is False
