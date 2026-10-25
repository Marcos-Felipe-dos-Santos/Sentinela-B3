"""BUG-2B-48: VP final inválido não impede a elegibilidade do FII.

Auditoria de fechamento da 2B (Codex, 25/10/2026): o rendimento usa o VP do mês anterior a
cada DY, e o VP do mês final da janela não é conferido. A ficha (§2 e §4) pede os 13 VPs
válidos, inclusive o último.
"""

import pytest

from sentinela.data import rendimento_fii as rf
from tests.test_fii_rendimento_elegivel import _avaliar, _registros


@pytest.mark.parametrize("vp", [None, "", "0", "-1", "nan", "inf", "abc"])
def test_vp_final_invalido_abstem(vp):
    registros = _registros()
    registros[-1] = {**registros[-1], "Valor_Patrimonial_Cotas": vp}
    r = _avaliar(registros)
    assert r == rf.Abstencao(f"{rf.MOTIVO_VP}: 2026-09"), r
