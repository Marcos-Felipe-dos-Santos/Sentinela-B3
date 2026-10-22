"""BUG-2B-39: a guarda de classe deve reconhecer espaços nas pontas (F2B-4)."""

import pytest

from tests.test_valuation_escopo import _processar


@pytest.mark.xfail(strict=True, reason="BUG-2B-39: corrigir no F2B-4")
def test_etf_com_espaco_nao_recebe_valor_de_acao():
    resultado = _processar(classe_ativo=" ETF")
    assert not {"fair_value", "upside", "score_final"} & set(resultado)
