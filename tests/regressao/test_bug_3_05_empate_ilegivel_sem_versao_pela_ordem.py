"""BUG-3-05: no mês final, ilegível × sem versão é decidido pela ordem do arquivo.

As duas linhas valem -inf na seleção; a primeira do arquivo vence, e o resultado alterna
entre abstenção e rendimento conforme a ordem. O correto não pode depender da ordem.
Borda registrada no F3-P08 (10/11/2026); decisão do Marcos de 10/11/2026: destino F3-3c.
"""

import pytest

from tests.test_fii_rendimento_elegivel import _avaliar, _composicao, _registros


def _final(registros):
    return max(registros, key=lambda r: r["Data_Referencia"])


@pytest.mark.xfail(strict=True, reason="BUG-3-05, corrige F3-3c")
def test_resultado_nao_depende_da_ordem_das_linhas():
    registros = _registros()
    for linha in registros:
        del linha["Versao"]
    composicoes = _composicao()
    del composicoes[0]["Versao"]
    ilegivel = {**_final(registros), "Versao": "ilegivel"}
    antes = _avaliar([ilegivel, *registros], composicoes)
    depois = _avaliar([*registros, ilegivel], composicoes)
    assert antes == depois
