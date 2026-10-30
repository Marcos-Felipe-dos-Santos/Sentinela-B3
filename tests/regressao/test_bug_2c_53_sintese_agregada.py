"""BUG-2C-53: lentes heterogêneas não autorizam valor único ou preço substituto."""

import pytest
from test_financeiro_pre_refactor import _acao, _fii, _processar


@pytest.mark.parametrize("caso", ["tres", "duas", "uma", "zero", "fii"])
def test_sem_sintese_em_zero_uma_duas_ou_tres_lentes(caso):
    if caso == "fii":
        r = _fii()
    else:
        dados = _acao() if caso == "tres" else _acao(roe=0.08, com_dva=False)
        if caso in {"uma", "zero"}:
            dados["ipca_serie"] = None
        if caso == "zero":
            dados["proventos_b3"] = {"abstencao": "sem fonte"}
        r = _processar(dados)
    assert not {"fair_value", "upside", "score_final", "recomendacao"} & r.keys()
    valores = [l["valor"] for l in r["lentes"].values() if l["valor"] is not None]
    assert len(valores) == {"tres": 3, "duas": 2, "uma": 1, "zero": 0, "fii": 1}[caso]
    assert all(l["abstencao"] for l in r["lentes"].values() if l["valor"] is None)
