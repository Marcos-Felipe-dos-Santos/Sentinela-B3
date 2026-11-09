"""BUG-2C-51: apresentação aprovada não autoriza score/classificação agregados."""

import pytest
from test_financeiro_pre_refactor import _acao, _fii, _processar


@pytest.mark.parametrize("tipo", ["acao", "fii"])
def test_sem_score_ou_classificacao_e_com_distancia_por_lente(tipo):
    r = _processar(_acao()) if tipo == "acao" else _fii()
    assert "score_final" not in r
    assert "recomendacao" not in r
    assert r["lentes"]
    for lente in r["lentes"].values():
        assert "regime" in lente and "janela" in lente
        assert "sinal" not in lente and "rotulo" not in lente
        if lente["valor"] is not None:
            assert lente["distancia_ao_preco_pct"] == pytest.approx(
                100 * (lente["valor"] / 100 - 1)
            )
        else:
            assert lente["abstencao"] and lente["distancia_ao_preco_pct"] is None
