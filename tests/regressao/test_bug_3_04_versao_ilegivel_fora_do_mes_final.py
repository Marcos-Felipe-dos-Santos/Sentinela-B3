"""BUG-3-04: mês da janela, fora do final, só com versão ilegível ainda entra no rendimento.

A guarda do F3-P08 (BUG-2C-27) só olha o mês final; a ficha FII 1.3 §3 vale por mês, e um
mês anterior só com versões explicitamente ilegíveis continua dando DY e VP. Borda
registrada no F3-P08 (10/11/2026); decisão do Marcos de 10/11/2026: destino F3-3c-fix (decisão 36).
"""

import pytest

from sentinela.data import rendimento_fii as rf
from tests.test_fii_rendimento_elegivel import _avaliar, _composicao, _registros


@pytest.mark.xfail(strict=True, reason="BUG-3-04, corrige F3-3c-fix")
def test_mes_anterior_so_com_versao_ilegivel_abstem():
    registros = _registros()
    alvo = next(r for r in registros if r["Data_Referencia"] == "2026-05-01")
    alvo["Versao"] = "ilegivel"
    resultado = _avaliar(registros, _composicao())
    assert resultado == rf.Abstencao(f"{rf.MOTIVO_VERSAO_ILEGIVEL}: 2026-05")
