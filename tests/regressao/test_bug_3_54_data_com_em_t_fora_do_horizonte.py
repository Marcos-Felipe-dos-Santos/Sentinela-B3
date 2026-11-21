"""BUG-3-54 (Gemini C3): a data com em T fica fora do horizonte do retorno.

A ficha (docs/metodologia/backtest.md, §5, decisão 42) conta os proventos e eventos com data
ex em (D, T]. A data ex é o pregão seguinte à data com; com a data com em T, a ex cai depois
de T, fora do horizonte. `BacktestPIT._retornos` lia as fontes até o dia seguinte a T e
abstinha quando o registro sem prova (ou o evento sem data ex) tinha a data com em T, que
`proventos_ate` não consegue provar por não haver pregão entre T e o corte.

Mesmo arranjo do F3-8b (`test_backtest_pit_retornos.py`): banco e fontes substituídos, com
a regra de `_retornos` real e as contas à mão da ficha.
"""

from datetime import date

import pytest
from test_backtest_pit_retornos import BASE, T, _executar, _Fontes

VESPERA = date.fromordinal(T.toordinal() - 1)  # a ex pode ser T: segue abstendo
MOTIVO_PROVENTO = "relação de proventos contém registros sem prova no horizonte"


def test_provento_sem_prova_com_data_com_em_t_nao_abstem(monkeypatch):
    _Fontes(monkeypatch, sem_prova=[{"data_com": T.isoformat()}])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] is None
    assert retorno["retorno"] == pytest.approx(0.1)  # 11 / 10 − 1, sem provento


def test_evento_sem_prova_com_data_com_em_t_nao_abstem(monkeypatch):
    _Fontes(monkeypatch, eventos_sp=[{"data_com": T.isoformat()}])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] is None
    assert retorno["retorno"] == pytest.approx(0.1)


def test_evento_sem_data_ex_com_data_com_em_t_nao_abstem(monkeypatch):
    _Fontes(
        monkeypatch,
        eventos=[{"isin": "BRABEVACNOR1", "data_com": T.isoformat(), "data_ex": None}],
    )
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] is None
    assert retorno["retorno"] == pytest.approx(0.1)


def test_data_com_na_vespera_de_t_segue_abstendo(monkeypatch):
    """Controle: com a data com antes de T, a ex pode ser T, dentro do horizonte."""
    _Fontes(monkeypatch, sem_prova=[{"data_com": VESPERA.isoformat()}])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] == MOTIVO_PROVENTO
    _Fontes(monkeypatch, eventos_sp=[{"data_com": VESPERA.isoformat()}])
    retorno, *_ = _executar(monkeypatch, BASE)
    assert retorno["abstencao"] == "evento em ações sem prova no horizonte"
    _Fontes(
        monkeypatch,
        eventos=[
            {"isin": "BRABEVACNOR1", "data_com": VESPERA.isoformat(), "data_ex": None}
        ],
    )
    retorno, *_ = _executar(monkeypatch, BASE)
    assert (
        retorno["abstencao"] == "evento em ações sem data ex demonstrada no horizonte"
    )
