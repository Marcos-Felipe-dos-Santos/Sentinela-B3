"""BUG-3-16: o registro imutável do resultado sai sem a data do preço.

Auditoria cruzada da 3-a (Claude, 11/11/2026), sobre o F3-6a: `AnalysisService` grava
`data_preco` na proveniência, mas nenhum produtor da cascata escreve o campo; o teste do
serviço só confere o valor do mock. O produtor do preço (yfinance, fechamento do histórico)
deve dizer a data do fechamento usado; o motivo explícito de ausência só vale quando a fonte
não traz a data.
Corrige: F3-A-F3.
"""

from types import SimpleNamespace

import pandas as pd
import pytest

import market_engine
from market_engine import MarketEngine


class _Ticker:
    def __init__(self, *_):
        self.info = {}

    def history(self, period=None, auto_adjust=True, timeout=None):
        indice = pd.to_datetime(["2026-11-06", "2026-11-09", "2026-11-10"])
        return pd.DataFrame({"Close": [20.0, 21.0, 22.0]}, index=indice)


@pytest.mark.xfail(
    strict=True, reason="BUG-3-16 · preço sem data no produtor · corrige: F3-A-F3"
)
def test_preco_do_historico_traz_a_data_do_fechamento(monkeypatch):
    monkeypatch.setattr(market_engine, "yf", SimpleNamespace(Ticker=_Ticker))
    motor = MarketEngine.__new__(MarketEngine)
    dados = {}
    assert motor._buscar_yfinance("TSTA3", dados)
    assert dados["preco_atual"] == 22.0
    # a fonte diz a data do fechamento: o motivo de ausência não basta aqui
    assert dados.get("data_preco") == "2026-11-10"
