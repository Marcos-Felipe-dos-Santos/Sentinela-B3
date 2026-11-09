"""BUG-2B-45: a falha na coleta do relatório 16 do IF.data descarta a Basileia já lida.

Revisão do F2B-32, 25/10/2026: sem rede e sem cache para a carteira, a exceção saía de
`ler_capital` e a cascata gravava "IF.data indisponível" para Basileia e inadimplência. A
falha da carteira só pode tirar a inadimplência, com o motivo.
"""

from datetime import date

import pytest
import requests

from sentinela.data.providers import ifdata
from tests.apoio_ifdata_calendario import calendario_sintetico
from tests.test_cvm_bancos import CADASTRO_BB, CAPITAL_BB


def test_falha_da_carteira_preserva_a_basileia():
    def buscar(caminho):
        if "@Relatorio='16'" in caminho:
            raise requests.ConnectionError("sem rede")
        if "IfDataCadastro" in caminho and "202606" in caminho:
            return CADASTRO_BB
        if "@Relatorio='5'" in caminho and "202606" in caminho:
            return CAPITAL_BB
        return []

    capital = ifdata.ler_capital(
        "00.000.000/0001-91",
        date(2026, 10, 13),
        buscar,
        calendario=calendario_sintetico(),
    )
    assert capital.basileia == pytest.approx(0.151297835513664)
    assert capital.inadimplencia is None
    assert capital.motivos["inadimplencia"] == "relatório 16 indisponível: sem rede"
