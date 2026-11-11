"""BUG-3-17: último fechamento inválido do yfinance deixa fonte e data do preço erradas.

Revisão do F3-A-F3 (11/11/2026): o `_buscar_yfinance` grava `fonte_preco='yfinance'` (e a data
do fechamento) antes de saber se o último `Close` é um preço válido. Com `NaN`, a brapi
preenche o preço, mas a fonte continua `yfinance`; sem a brapi, o preço `NaN` segue com a
data desse fechamento, e o `currentPrice` do mesmo provedor é ignorado. Corrige: F3-A-F5.
"""

import pandas as pd
import pytest

from tests.test_market_engine import FakeBrapi, _engine


def _historico():
    return pd.DataFrame(
        {"Close": [20.0, float("nan")]},
        index=pd.to_datetime(["2026-11-09", "2026-11-10"]),
    )


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG-3-17 · fonte do preço fica yfinance · corrige: F3-A-F5",
)
def test_preco_da_brapi_tem_fonte_brapi(monkeypatch):
    engine = _engine(
        monkeypatch,
        info={},
        historico=_historico(),
        brapi=FakeBrapi(resposta={"preco_atual": 30.0}),
    )
    dados = engine.buscar_dados_ticker("PETR4")
    assert dados["preco_atual"] == 30.0
    assert dados["fonte_preco"] == "brapi"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG-3-17 · preço NaN com data, currentPrice ignorado · corrige: F3-A-F5",
)
def test_fechamento_nan_cede_ao_current_price_sem_data(monkeypatch):
    engine = _engine(monkeypatch, info={"currentPrice": 25.0}, historico=_historico())
    dados = engine.buscar_dados_ticker("PETR4")
    assert dados["preco_atual"] == 25.0
    assert dados["fonte_preco"] == "yfinance"
    assert "data_preco" not in dados
    assert dados["motivo_data_preco"] == "yfinance: currentPrice sem data do fechamento"
