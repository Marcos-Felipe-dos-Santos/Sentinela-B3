"""Invariantes externos antigos também alcançam o transporte histórico."""
import pytest

import auditoria


@pytest.mark.parametrize("chave", ["valuation", "raw"])
def test_invariantes_historicas_aninhadas_nao_ocultam_numeros_invalidos(chave):
    legado = {"fair_value": float("nan"), "score_final": 200}
    esperado = ["fair_value: número não finito ou inválido", "score_final: fora de [0,100]"]
    assert auditoria.invariantes_resultado(legado) == esperado
    assert auditoria.invariantes_resultado({chave: legado}) == esperado
