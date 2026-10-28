"""BUG-2C-27: sentinela de versão ilegível não demonstra identidade documental.

Dicionário CVM do Informe Mensal: Versao numérica inteira; ficha FII 1.3 §3,
maior versão numérica elegível e mesma versão da composição (§3c).
"""

import pytest

from sentinela.data import rendimento_fii as rf
from tests.test_fii_rendimento_elegivel import _avaliar, _composicao, _registros


@pytest.mark.xfail(strict=True, reason="BUG-2C-27: proposta F2C-55 na 2C-b")
def test_todas_as_versoes_ilegiveis_nao_autorizam_rendimento():
    registros = _registros()
    composicoes = _composicao()
    for linha in [*registros, *composicoes]:
        linha["Versao"] = "ilegivel"
    assert isinstance(_avaliar(registros, composicoes), rf.Abstencao)
