"""BUG-2C-64: decisão Marcos09/11 F2C-45(iii), alavancagem inaplicável ao banco."""

import pytest
from apoio_bancos import enriquecer_bancos

from tests.test_valuation_bancos import BANCO, _processar


def test_banco_com_lente_nao_recebe_aviso_de_alavancagem():
    r = _processar(enriquecer_bancos(BANCO))
    assert r["lentes"]["Bancos"]["valor"] == pytest.approx(26.346908251509)
    assert "aviso_alavancagem" not in r
